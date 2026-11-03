"""MJPEG over HTTP 拉流源（手机摄像头专用）。

不依赖 OpenCV/FFmpeg 的 HTTP 解包：IP Webcam 等 App 的 multipart 头
（boundary 带分号、双 Content-Type 行等）经常让 FFmpeg 解析失败而黑屏。
这里直接扫描 JPEG 的 SOI(FFD8)/EOI(FFD9) 标记切帧，对任何不规范
boundary 都免疫。

重连策略分级：
- 永久性错误（URL 不合法/缺协议头）-> 抛 MjpegError，调用方停止并提示，
  绝不无限重试刷日志；
- 网络性错误（断流/超时/拒绝连接）-> 指数退避重连，重复日志限流。
"""
import logging
import re
import threading
from urllib.parse import urlparse

import cv2
import numpy as np
import requests

logger = logging.getLogger("mjpeg")

SOI = b"\xff\xd8"
EOI = b"\xff\xd9"
MAX_PARTIAL = 4 * 1024 * 1024   # 半帧缓冲上限，防止流损坏时内存膨胀

# host:adb端口:服务端口 —— 用户常把 adb devices 里的 15555 也粘进来
_ADB_DOUBLE_PORT_RE = re.compile(r"^(?P<host>[^:@]+):\d{2,5}:(?P<port>\d{2,5})$")


def normalize_stream_url(raw: str) -> str:
    """
    纠正手机视频地址的常见输入错误：
    - 缺协议头:  "10.0.0.5:8081/video"          -> "http://10.0.0.5:8081/video"
    - ADB 双端口: "10.33.31.139:15555:8081/video" -> "http://10.33.31.139:8081/video"
      （15555 是 ADB 调试端口，不是视频端口）
    """
    url = (raw or "").strip()
    if not url:
        return url
    if "://" not in url:
        url = "http://" + url
    parsed = urlparse(url)
    m = _ADB_DOUBLE_PORT_RE.match(parsed.netloc)
    if m:
        url = parsed._replace(netloc=f"{m.group('host')}:{m.group('port')}").geturl()
    return url


def validate_stream_url(url: str):
    """返回错误说明（None = 合法）。"""
    try:
        p = urlparse(url)
        _ = p.port   # 访问 .port 属性：非法端口（如多个冒号）在此抛 ValueError
    except ValueError:
        return f"地址端口不合法: {url}"
    if p.scheme not in ("http", "https"):
        return f"需要 http/https 地址: {url}"
    if not p.hostname:
        return f"缺少主机地址: {url}"
    if p.port in (15555, 5555):
        return (f"{p.hostname}:{p.port} 是 ADB 调试端口，不是视频端口。\n"
                f"IP Webcam 视频端口一般是 8080/8081，"
                f"或走 ADB 转发用 http://localhost:端口/video")
    return None


class MjpegError(RuntimeError):
    """永久性流错误（重试无意义）"""


def iter_jpeg_frames(chunk_iter):
    """
    纯函数：给定 bytes 分块迭代器，yield 解码出的 BGR 帧 (np.ndarray)。
    解不出完整帧的残缺数据自动丢弃（imdecode 返回 None 时跳过）。
    """
    buf = b""
    for chunk in chunk_iter:
        if not chunk:
            continue
        buf += chunk
        while True:
            i = buf.find(SOI)
            if i < 0:
                buf = buf[-8:]
                break
            j = buf.find(EOI, i + 2)
            if j < 0:
                buf = buf[i:]
                if len(buf) > MAX_PARTIAL:
                    logger.warning("MJPEG 缓冲超限，丢弃未完成的帧")
                    buf = b""
                break
            jpeg = buf[i:j + 2]
            buf = buf[j + 2:]
            frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
            if frame is not None:
                yield frame


class MjpegSource:
    """requests 流式下载 + iter_jpeg_frames 解析，断线自动重连（带退避与日志限流）。"""

    def __init__(self, url: str, on_reconnect=None, timeout: float = 8.0,
                 max_attempts: int = 10):
        self.url = url
        self.on_reconnect = on_reconnect
        self.timeout = timeout
        self.max_attempts = max_attempts
        self._session = requests.Session()
        self._stop_evt = threading.Event()

    def stop(self):
        self._stop_evt.set()
        try:
            self._session.close()
        except Exception:
            pass

    @property
    def stopped(self) -> bool:
        return self._stop_evt.is_set()

    def _interruptible_sleep(self, seconds: float) -> bool:
        """返回 True 表示等待期间收到停止信号。"""
        return self._stop_evt.wait(seconds)

    def frames(self):
        """
        生成器：持续产出 BGR 帧；stop() 后结束。
        URL 永久非法时抛 MjpegError（首次 next() 即抛）。
        """
        url = normalize_stream_url(self.url)
        err = validate_stream_url(url)
        if err:
            raise MjpegError(f"手机视频地址无效：{err}")
        if url != self.url:
            logger.info("视频地址已自动纠正: %s -> %s", self.url, url)

        attempts = 0
        while not self.stopped:
            try:
                resp = self._session.get(url, stream=True,
                                         timeout=(5, self.timeout))
                resp.raise_for_status()
                if attempts > 0 and self.on_reconnect:
                    self.on_reconnect()   # 断流后重连成功
                attempts = 0
                for frame in iter_jpeg_frames(resp.iter_content(chunk_size=16384)):
                    if self.stopped:
                        break
                    yield frame
                resp.close()
                if self.stopped:
                    break
                raise requests.ConnectionError("流提前结束")
            except (requests.exceptions.MissingSchema,
                    requests.exceptions.InvalidSchema,
                    requests.exceptions.InvalidURL) as e:
                raise MjpegError(f"手机视频地址无效：{e}")
            except requests.RequestException as e:
                if self.stopped:
                    break
                attempts += 1
                # 日志限流：只报第 1 次和最终失败
                if attempts == 1:
                    logger.warning("MJPEG 流中断(%s)，正在重连…", e)
                if attempts >= self.max_attempts:
                    logger.error("MJPEG 重连 %d 次仍失败(%s)，停止拉流。"
                                 "请检查手机 IP Webcam 是否运行、地址/端口是否正确",
                                 attempts, e)
                    raise MjpegError(f"无法连接 {url}，请确认手机端 IP Webcam 已启动")
            if self._interruptible_sleep(min(0.5 * attempts, 3.0)):
                break
