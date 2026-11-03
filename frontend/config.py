"""前端配置：统一从项目根 .env 读取，不再散落硬编码。"""
import os

from dotenv import load_dotenv

FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(FRONTEND_DIR)
load_dotenv(dotenv_path=os.path.join(ROOT_DIR, ".env"))

BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.getenv("BACKEND_PORT", "8000")
BACKEND_HTTP = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
BACKEND_WS = f"ws://{BACKEND_HOST}:{BACKEND_PORT}/ws/process"

# 采集/发送帧率与 JPEG 质量（原为硬编码 10 FPS / q70）
TARGET_FPS = int(os.getenv("FRONTEND_FPS", "10"))
FRAME_JPEG_QUALITY = int(os.getenv("FRAME_JPEG_QUALITY", "70"))
WS_TIMEOUT = 5

# ADB（手机摄像头 USB 模式）路径，可选依赖
ADB_PATH = os.path.join(ROOT_DIR, "res", "platform-tools", "adb.exe")
