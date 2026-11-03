"""MySQL 数据库操作（线程安全）。

改进点：
- 所有操作通过一把锁串行化 + ping(reconnect=True)，
  解决 pymysql 单连接跨线程池/事件循环线程共享导致游标错乱的问题；
- bbox 用 JSON 序列化（旧实现存 Python repr 字符串，无法解析）；
- 增加 count_history，/history 的 total 不再是 len(本页记录)；
- 用 logging 替代 print。
"""
import json
import logging
import os
import threading
from typing import Dict, List, Optional

import pymysql

logger = logging.getLogger("db")


class Database:
    """MySQL 数据库操作"""

    def __init__(self):
        self.config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "3306")),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_NAME", "gesture_qa"),
            "charset": "utf8mb4",
            "cursorclass": pymysql.cursors.DictCursor,
            "autocommit": False,
        }
        self.connection = None
        self._lock = threading.Lock()

    def connect(self):
        """建立数据库连接（失败抛异常，由调用方决定降级策略）"""
        if not self.config["password"]:
            raise RuntimeError(
                "未设置 DB_PASSWORD 环境变量：请复制根目录 .env.example 为 .env "
                "并填入你的 MySQL 密码")
        self.connection = pymysql.connect(**self.config)
        logger.info("数据库已连接: %s:%s/%s",
                    self.config["host"], self.config["port"], self.config["database"])

    def _ensure_connected(self):
        """确保连接有效（长空闲后被 MySQL 断开时自动重连）。调用者须持锁。"""
        if self.connection is None:
            self.connect()
            return
        try:
            self.connection.ping(reconnect=True)
        except pymysql.Error as e:
            logger.warning("数据库连接失效(%s)，尝试重连", e)
            self.connection = None
            self.connect()

    def _execute(self, sql: str, params=None, fetch: Optional[str] = None):
        """在锁内执行一条 SQL。fetch: 'all' | 'one' | None"""
        try:
            with self._lock:
                self._ensure_connected()
                with self.connection.cursor() as cursor:
                    cursor.execute(sql, params or ())
                    if fetch == "all":
                        rows = cursor.fetchall()
                    elif fetch == "one":
                        rows = cursor.fetchone()
                    else:
                        rows = None
                    self.connection.commit()
                    return rows
        except pymysql.Error as e:
            logger.error("SQL 执行失败: %s | sql=%s", e, sql.strip()[:120])
            try:
                with self._lock:
                    if self.connection:
                        self.connection.rollback()
            except Exception:
                pass
            return None

    def save_detection(self, object_name: str, object_class: str,
                       confidence: float, bbox,
                       question: str = None, answer: str = None,
                       image_path: str = None) -> int:
        """保存一次检测/问答记录，返回新记录 id（失败返回 -1）"""
        bbox_json = json.dumps(bbox, ensure_ascii=False) if not isinstance(bbox, str) else bbox
        sql = """
            INSERT INTO history
            (object_name, object_class, confidence, bbox, question, answer, image_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        try:
            with self._lock:
                self._ensure_connected()
                with self.connection.cursor() as cursor:
                    cursor.execute(sql, (
                        object_name, object_class, confidence,
                        bbox_json, question, answer, image_path
                    ))
                    self.connection.commit()
                    return cursor.lastrowid
        except pymysql.Error as e:
            logger.error("保存检测记录失败: %s", e)
            try:
                with self._lock:
                    if self.connection:
                        self.connection.rollback()
            except Exception:
                pass
            return -1

    def update_object_stats(self, object_name: str, object_class: str):
        """更新物品统计（UPSERT）"""
        sql = """
            INSERT INTO detected_objects (object_name, object_class, detect_count)
            VALUES (%s, %s, 1)
            ON DUPLICATE KEY UPDATE
                detect_count = detect_count + 1,
                last_seen = CURRENT_TIMESTAMP
        """
        self._execute(sql, (object_name, object_class))

    def get_history(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """获取历史记录（bbox 字段解析回列表）"""
        rows = self._execute(
            "SELECT * FROM history ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s",
            (limit, offset), fetch="all") or []
        for r in rows:
            if isinstance(r.get("bbox"), str):
                try:
                    r["bbox"] = json.loads(r["bbox"])
                except (json.JSONDecodeError, TypeError):
                    r["bbox"] = None
        return rows

    def count_history(self) -> int:
        """历史记录总数"""
        row = self._execute("SELECT COUNT(*) AS n FROM history", fetch="one")
        return int(row["n"]) if row else 0

    def get_latest_detection(self) -> Optional[Dict]:
        """获取最新一次检测"""
        return self._execute("SELECT * FROM history ORDER BY id DESC LIMIT 1",
                             fetch="one")

    def is_connected(self) -> bool:
        with self._lock:
            if self.connection is None:
                return False
            try:
                self.connection.ping(reconnect=False)
                return True
            except Exception:
                return False

    def close(self):
        with self._lock:
            if self.connection:
                try:
                    self.connection.close()
                finally:
                    self.connection = None
