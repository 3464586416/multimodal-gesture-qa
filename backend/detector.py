"""YOLOv8 物体检测模块。

只负责返回结构化检测结果，不在输入帧上做任何绘制（绘制由前端完成，
见 frontend/overlay.py），避免对调用方帧的原地修改与重复绘制。
"""
import logging
import os
from typing import Dict, List, Optional, Tuple

from ultralytics import YOLO

from geometry import find_pointed_object

logger = logging.getLogger("detector")

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_BACKEND_DIR)


class ObjectDetector:
    """YOLOv8 物体检测器"""

    def __init__(self, model_path: str = None, confidence: float = None):
        resolved = self._resolve_model(model_path)
        logger.info("加载 YOLO 模型: %s", resolved)
        self.model = YOLO(resolved)
        self.confidence = (
            confidence if confidence is not None
            else float(os.getenv("YOLO_CONFIDENCE", "0.45"))
        )
        self.forward_weight = float(os.getenv("POINT_FORWARD_WEIGHT", "0.3"))
        self.max_angle_deg = float(os.getenv("POINT_MAX_ANGLE", "45"))
        self.names = self.model.names

    @staticmethod
    def _resolve_model(model_path: Optional[str]) -> str:
        """
        模型路径解析顺序：
        显式参数 > 环境变量 YOLO_MODEL > 项目根/backend 下同名文件 > ultralytics 自动下载。
        （旧实现写死 "yolov8n.pt"，只有恰好在工作目录才能加载到本地模型。）
        """
        candidates: List[str] = []
        for p in (model_path, os.getenv("YOLO_MODEL"), "yolov8n.pt"):
            if not p:
                continue
            if os.path.isabs(p):
                candidates.append(p)
            else:
                candidates.extend([
                    os.path.join(_ROOT_DIR, p),
                    os.path.join(_BACKEND_DIR, p),
                    p,
                ])
        for c in candidates:
            if os.path.exists(c):
                return c
        # 未找到本地文件：交给 ultralytics 按名称自动下载
        return model_path or os.getenv("YOLO_MODEL") or "yolov8n.pt"

    def detect(self, frame, exclude_classes: List[str] = None) -> Dict:
        """
        检测画面中的物体，返回 {"objects": [...]}。
        坐标为输入帧（处理帧）像素坐标。
        :param exclude_classes: 要排除的类别，默认排除 ["person"]
        """
        if exclude_classes is None:
            exclude_classes = ["person"]
        results = self.model(frame, conf=self.confidence, verbose=False)
        objects = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                cls_name = self.names[cls_id]
                if cls_name in exclude_classes:
                    continue
                objects.append({
                    "class_id": cls_id,
                    "class_name": cls_name,
                    "confidence": round(conf, 3),
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                })
        return {"objects": objects}

    def find_pointed_object(self, objects: List[Dict],
                            finger_tip: Tuple[int, int],
                            finger_mcp: Tuple[int, int]) -> Optional[Dict]:
        """指向锥域内匹配被指向物体（纯几何实现见 geometry.find_pointed_object）。"""
        return find_pointed_object(
            objects, finger_tip, finger_mcp,
            forward_weight=self.forward_weight,
            max_angle_deg=self.max_angle_deg,
        )
