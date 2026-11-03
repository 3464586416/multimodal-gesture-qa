"""视频叠加绘制（纯函数，便于单测）。

改进点：
- 类别颜色用确定性哈希生成（旧后端 detector 用 np.random.seed 会污染全局随机状态）；
- 边界框带半透明填充与标签底色块，指向物体用四角括号高亮；
- 手部骨架连线直接用后端返回的 21 关键点绘制；
- 指向射线用虚线延伸；所有文字均为英文（cv2 不支持中文渲染，中文在 UI 面板显示）。
"""
import math

import cv2
import numpy as np

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]

_GREEN = (80, 220, 100)
_CYAN = (255, 220, 80)
_MAGENTA = (200, 80, 255)
_YELLOW = (60, 220, 240)


def color_for_class(class_id: int):
    """按类别 id 生成稳定、区分度高的 BGR 颜色（不触碰任何全局随机状态）。"""
    hue = (class_id * 47 + 23) % 180
    hsv = np.uint8([[[hue, 210, 235]]])
    b, g, r = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0][0]
    return int(b), int(g), int(r)


def _text_chip(img, text, x, y, color, font_scale=0.55, thickness=1):
    """带底色块的标签文字。"""
    font = cv2.FONT_HERSHEY_SIMPLEX
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
    x = max(0, min(x, img.shape[1] - tw - 8))
    y = max(th + 6, y)
    cv2.rectangle(img, (x - 3, y - th - 5), (x + tw + 3, y + 4), (10, 12, 18), -1)
    cv2.putText(img, text, (x, y - 2), font, font_scale, color, thickness, cv2.LINE_AA)


def _dashed_line(img, p1, p2, color, thickness=1, dash=10, gap=7):
    x1, y1 = p1
    x2, y2 = p2
    dist = math.hypot(x2 - x1, y2 - y1)
    if dist < 1:
        return
    ux, uy = (x2 - x1) / dist, (y2 - y1) / dist
    pos = 0.0
    while pos < dist:
        end = min(pos + dash, dist)
        cv2.line(img,
                 (int(x1 + ux * pos), int(y1 + uy * pos)),
                 (int(x1 + ux * end), int(y1 + uy * end)),
                 color, thickness, cv2.LINE_AA)
        pos = end + gap


def _corner_brackets(img, x1, y1, x2, y2, color, thickness=3, ratio=0.22):
    """四角括号式高亮框。"""
    w, h = x2 - x1, y2 - y1
    ln = max(6, int(min(w, h) * ratio))
    pts = [
        ((x1, y1), (x1 + ln, y1), (x1, y1 + ln)),
        ((x2, y1), (x2 - ln, y1), (x2, y1 + ln)),
        ((x1, y2), (x1 + ln, y2), (x1, y2 - ln)),
        ((x2, y2), (x2 - ln, y2), (x2, y2 - ln)),
    ]
    for anchor, a, b in pts:
        cv2.line(img, a, anchor, color, thickness, cv2.LINE_AA)
        cv2.line(img, b, anchor, color, thickness, cv2.LINE_AA)


def draw_overlay(frame: np.ndarray, result: dict) -> np.ndarray:
    """
    在帧上绘制检测标注。result 为后端 /ws/process 返回的 JSON，
    其中所有坐标均为原始帧坐标系（后端已换算，前后端不再错位）。
    所有坐标做 int 强制转换，兼容 JSON 反序列化出的 float/list。
    """
    img = frame.copy()
    h, w = img.shape[:2]
    objects = result.get("objects", [])

    # 物体框：半透明填充 + 边框 + 标签
    for obj in objects:
        x1, y1, x2, y2 = (int(v) for v in obj["bbox"])
        color = color_for_class(obj.get("class_id", 0))
        fill = img.copy()
        cv2.rectangle(fill, (x1, y1), (x2, y2), color, -1)
        cv2.addWeighted(fill, 0.08, img, 0.92, 0, dst=img)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
        _text_chip(img, f"{obj['class_name']} {obj['confidence']:.2f}",
                   x1, y1, color)

    # 手部骨架
    landmarks = result.get("landmarks", [])
    if landmarks and len(landmarks) >= 21:
        pts = [(int(p[0]), int(p[1])) for p in landmarks]
        for a, b in HAND_CONNECTIONS:
            cv2.line(img, pts[a], pts[b], _GREEN, 2, cv2.LINE_AA)
        for lx, ly in pts:
            cv2.circle(img, (lx, ly), 3, _CYAN, -1, cv2.LINE_AA)

    tip = result.get("finger_tip")
    mcp = result.get("finger_mcp")
    if tip:
        tip = (int(tip[0]), int(tip[1]))
    if mcp:
        mcp = (int(mcp[0]), int(mcp[1]))

    if result.get("pointing") and tip and mcp:
        # 指向射线：虚线延伸到画面边缘附近
        dx, dy = tip[0] - mcp[0], tip[1] - mcp[1]
        norm = math.hypot(dx, dy) or 1.0
        ext = min(w, h) * 0.9
        ex, ey = int(tip[0] + dx / norm * ext), int(tip[1] + dy / norm * ext)
        _dashed_line(img, tip, (ex, ey), _MAGENTA, 1)
        cv2.arrowedLine(img, mcp,
                        (int(tip[0] + dx / norm * 60), int(tip[1] + dy / norm * 60)),
                        _MAGENTA, 2, cv2.LINE_AA, tipLength=0.35)

    if tip:
        cv2.circle(img, tip, 7, (60, 60, 255), -1, cv2.LINE_AA)
        cv2.circle(img, tip, 11, _YELLOW, 2, cv2.LINE_AA)
    if mcp:
        cv2.circle(img, mcp, 5, (255, 120, 60), -1, cv2.LINE_AA)

    # 指向物体高亮
    pointed = result.get("pointed_object")
    if pointed:
        x1, y1, x2, y2 = (int(v) for v in pointed["bbox"])
        _corner_brackets(img, x1 - 3, y1 - 3, x2 + 3, y2 + 3, _YELLOW, 3)
        _text_chip(img, f">> {pointed['class_name']}", x1, y2 + 24, _YELLOW, 0.6, 2)

    # 状态徽章（左上角）
    threshold = result.get("confirm_threshold", 3)
    count = result.get("confirm_count", 0)
    if pointed and count >= threshold:
        status, scol = f"LOCKED: {pointed['class_name']}", _YELLOW
    elif count > 0:
        status, scol = f"CONFIRMING {count}/{threshold}", _CYAN
    elif result.get("pointing"):
        status, scol = "POINTING", _MAGENTA
    elif result.get("hand_detected"):
        status, scol = "HAND DETECTED", _GREEN
    elif result.get("status") == "gesture_unavailable":
        status, scol = "GESTURE MODEL UNAVAILABLE", (60, 60, 255)
    else:
        status, scol = "NO HAND", (120, 140, 190)
    _text_chip(img, status, 12, 30, scol, 0.65, 2)

    return img
