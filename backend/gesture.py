"""MediaPipe 手部关键点检测 + 指向手势识别模块。

改进点：
- RunningMode.VIDEO 启用帧间跟踪（比逐帧 IMAGE 模式更快更稳，时间戳保证单调递增）；
- 不再在输入帧上原地绘制（绘制职责归前端 overlay.py）；
- 手势判定逻辑抽到 geometry.is_pointing（纯函数，可单测）；
- 输出 21 个关键点像素坐标，供前端绘制完整手部骨架。
"""
import logging
import os
import time

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from geometry import is_pointing

logger = logging.getLogger("gesture")

_MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
              "hand_landmarker/float16/1/hand_landmarker.task")
_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
_MODEL_PATH = os.path.join(_MODEL_DIR, "hand_landmarker.task")


def _ensure_model():
    """本地模型缺失时才联网下载。"""
    if os.path.exists(_MODEL_PATH):
        return
    os.makedirs(_MODEL_DIR, exist_ok=True)
    logger.info("本地未找到手部模型，开始下载: %s", _MODEL_URL)
    import urllib.request
    urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
    logger.info("手部模型下载完成")


class GestureDetector:
    """MediaPipe Hand Landmarker 封装（tasks API）"""

    def __init__(self):
        _ensure_model()
        base_options = mp_python.BaseOptions(model_asset_path=_MODEL_PATH)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=int(os.getenv("NUM_HANDS", "1")),
            min_hand_detection_confidence=0.7,
            min_tracking_confidence=0.5,
            min_hand_presence_confidence=0.5,
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)
        self._last_ts_ms = 0

    def _next_timestamp_ms(self) -> int:
        """VIDEO 模式要求时间戳严格递增。"""
        now = int(time.monotonic() * 1000)
        ts = max(now, self._last_ts_ms + 1)
        self._last_ts_ms = ts
        return ts

    def detect(self, frame: np.ndarray) -> dict:
        """
        检测手部。返回 dict 中坐标均为输入帧（处理帧）像素坐标，
        调用方负责换算回原始帧坐标。
        """
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect_for_video(mp_image, self._next_timestamp_ms())

        if result.hand_landmarks:
            lm = result.hand_landmarks[0]
            px = [(p.x * w, p.y * h) for p in lm]
            return {
                "hand_detected": True,
                "pointing": is_pointing(px),
                "finger_tip": (int(px[8][0]), int(px[8][1])),
                "finger_mcp": (int(px[5][0]), int(px[5][1])),
                "landmarks": [[int(x), int(y)] for x, y in px],
            }

        return {
            "hand_detected": False,
            "pointing": False,
            "finger_tip": None,
            "finger_mcp": None,
            "landmarks": [],
        }

    def release(self):
        try:
            self.landmarker.close()
        except Exception:
            logger.debug("关闭 HandLandmarker 时异常", exc_info=True)
