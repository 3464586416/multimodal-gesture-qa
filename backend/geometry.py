"""
纯几何/手势逻辑模块。

不依赖 torch / mediapipe / cv2，可独立单元测试。
坐标系约定：所有像素坐标 (x, y) 均指"处理帧"坐标系，
由调用方负责把结果换算回原始帧坐标（见 scale_* 函数）。
"""
import math
from typing import Dict, List, Optional, Sequence, Tuple

# MediaPipe 21 关键点索引
WRIST = 0
# 各手指 (MCP 指根, TIP 指尖)：食指、中指、无名指、小指
FINGER_MCP_TIP = [(5, 8), (9, 12), (13, 16), (17, 20)]


def is_pointing(landmarks: Sequence[Tuple[float, float]]) -> bool:
    """
    判断是否为指向手势（食指伸直，其余三指弯曲）。
    采用指尖/指根到腕部的距离比值，不受手部朝向影响。
    landmarks 可为归一化坐标或像素坐标的 (x, y) 序列，需至少 21 项。
    """
    if landmarks is None or len(landmarks) < 21:
        return False
    wrist = landmarks[WRIST]

    def dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    ratios = []
    for mcp, tip in FINGER_MCP_TIP:
        ratios.append(dist(landmarks[tip], wrist) / (dist(landmarks[mcp], wrist) + 1e-6))

    index_extended = ratios[0] > 1.4
    others_curled = all(r < 1.2 for r in ratios[1:])
    return index_extended and others_curled


def find_pointed_object(
    objects: List[Dict],
    finger_tip: Optional[Tuple[float, float]],
    finger_mcp: Optional[Tuple[float, float]],
    forward_weight: float = 0.3,
    max_angle_deg: float = 45.0,
) -> Optional[Dict]:
    """
    根据手指指向匹配被指向的物体（锥域过滤 + 综合评分）。

    仅考虑位于指向锥域内的物体（在指尖前方、且中心方向与指向射线
    夹角 <= max_angle_deg），按
        score = forward_dist * forward_weight + perp_dist
    取最优。锥域外没有物体时返回 None——用户指向空白处不会误报
    画面中碰巧最近的物品（旧实现无条件兜底"最近物体"导致误报）。
    """
    if not objects or not finger_tip or not finger_mcp:
        return None

    tx, ty = float(finger_tip[0]), float(finger_tip[1])
    mx, my = float(finger_mcp[0]), float(finger_mcp[1])
    dx, dy = tx - mx, ty - my
    dnorm = math.hypot(dx, dy)
    if dnorm < 1:
        return None
    dx, dy = dx / dnorm, dy / dnorm

    best_obj = None
    best_score = float("inf")

    for obj in objects:
        x1, y1, x2, y2 = obj["bbox"]
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        vx, vy = cx - tx, cy - ty

        forward_dist = vx * dx + vy * dy
        if forward_dist <= 0:            # 物体中心不在指尖前方
            continue
        dist = math.hypot(vx, vy)
        cosang = max(-1.0, min(1.0, forward_dist / (dist + 1e-6)))
        if math.degrees(math.acos(cosang)) > max_angle_deg:
            continue                     # 偏离指向锥域

        perp_dist = math.hypot(vx - forward_dist * dx, vy - forward_dist * dy)
        score = forward_dist * forward_weight + perp_dist
        if score < best_score:
            best_score = score
            best_obj = obj

    return best_obj


def scale_point(pt: Optional[Sequence[float]], factor: float) -> Optional[List[int]]:
    """把处理帧坐标点换算回原始帧坐标。"""
    if pt is None:
        return None
    return [int(round(pt[0] * factor)), int(round(pt[1] * factor))]


def scale_bbox(bbox: Sequence[int], factor: float) -> List[int]:
    x1, y1, x2, y2 = bbox
    return [int(round(x1 * factor)), int(round(y1 * factor)),
            int(round(x2 * factor)), int(round(y2 * factor))]


def scale_objects(objects: List[Dict], factor: float) -> List[Dict]:
    """返回换算后的物体列表（不修改原对象）。"""
    if factor == 1.0:
        return objects
    out = []
    for obj in objects:
        o = dict(obj)
        o["bbox"] = scale_bbox(obj["bbox"], factor)
        out.append(o)
    return out


def scale_landmarks(landmarks: Optional[Sequence[Sequence[float]]],
                    factor: float) -> List[List[int]]:
    if not landmarks:
        return []
    if factor == 1.0:
        return [[int(p[0]), int(p[1])] for p in landmarks]
    return [scale_point(p, factor) for p in landmarks]
