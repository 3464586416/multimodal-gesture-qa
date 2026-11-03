-- ============================================================
-- 手势指示多模态问答系统 - 数据库初始化脚本
-- 在 Navicat Premium 中直接运行即可（可重复执行，不会清空已有数据）
-- ============================================================

CREATE DATABASE IF NOT EXISTS gesture_qa
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE gesture_qa;

-- 检测/问答历史记录表
CREATE TABLE IF NOT EXISTS history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '检测时间',
    object_name VARCHAR(100) NOT NULL COMMENT '物品名称',
    object_class VARCHAR(50) COMMENT 'COCO类别',
    confidence FLOAT COMMENT '检测置信度(0-1)',
    bbox VARCHAR(255) COMMENT '边界框坐标 JSON [x1,y1,x2,y2]',
    question TEXT COMMENT '用户提问',
    answer TEXT COMMENT 'AI回答',
    image_path VARCHAR(255) COMMENT '截图相对路径 uploads/xxx.jpg',
    KEY idx_history_created (created_at),
    KEY idx_history_object (object_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='手势指向物品检测历史记录';

-- 检测到的物品统计表
CREATE TABLE IF NOT EXISTS detected_objects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    object_name VARCHAR(100) NOT NULL UNIQUE COMMENT '物品名称',
    object_class VARCHAR(50) COMMENT 'COCO类别',
    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '首次检测时间',
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最近检测时间',
    detect_count INT DEFAULT 0 COMMENT '累计检测次数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='检测到的物品统计';

-- 注意：旧版脚本此处为 DROP TABLE IF EXISTS，重复执行会清空历史数据，已移除。
-- 如确需重置数据，请手动执行：DROP TABLE history; 后重新运行本脚本。
