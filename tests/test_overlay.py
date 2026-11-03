"""overlay 纯绘制函数单元测试。"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))

import overlay  # noqa: E402


def base_result():
    return {
        "status": "ok",
        "hand_detected": True,
        "pointing": True,
        "finger_tip": [200, 150],
        "finger_mcp": [180, 220],
        "landmarks": [[180 + i % 30, 220 - i * 3] for i in range(21)],
        "objects": [{"class_id": 39, "class_name": "cup",
                     "confidence": 0.91, "bbox": [220, 80, 320, 260]}],
        "pointed_object": None,
        "confirm_count": 1,
        "confirm_threshold": 3,
    }


class TestOverlay:
    def setup_method(self):
        self.frame = np.zeros((480, 640, 3), np.uint8)

    def test_returns_copy_does_not_mutate(self):
        out = overlay.draw_overlay(self.frame, base_result())
        assert out is not self.frame
        assert not self.frame.any(), "输入帧被原地修改了（旧实现的 bug）"

    def test_draws_something(self):
        out = overlay.draw_overlay(self.frame, base_result())
        assert out.any()

    def test_empty_result_no_crash(self):
        out = overlay.draw_overlay(self.frame, {"status": "ok"})
        assert out.shape == self.frame.shape

    def test_pointed_object_highlight(self):
        r = base_result()
        r["pointed_object"] = dict(r["objects"][0], confirmed=True)
        r["confirm_count"] = 3
        out = overlay.draw_overlay(self.frame, r)
        assert out.any()

    def test_color_for_class_stable_and_in_range(self):
        c1 = overlay.color_for_class(39)
        assert c1 == overlay.color_for_class(39)
        assert all(0 <= v <= 255 for v in c1)
        assert c1 != overlay.color_for_class(40)

    def test_landmarks_from_json_lists(self):
        """后端经 JSON 返回的是 list，不是 tuple——不应崩溃。"""
        r = base_result()
        r["landmarks"] = [[float(x), float(y)] for x, y in r["landmarks"]]
        out = overlay.draw_overlay(self.frame, r)
        assert out.shape == self.frame.shape
