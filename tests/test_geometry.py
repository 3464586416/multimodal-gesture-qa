"""geometry 模块纯逻辑单元测试（无需 GPU/网络/摄像头）。"""
import math

from geometry import (
    find_pointed_object,
    is_pointing,
    scale_bbox,
    scale_landmarks,
    scale_objects,
    scale_point,
)


def make_hand(index_ratio: float, other_ratio: float):
    """构造 21 点假手：腕在原点，四指指根半径 1.0，指尖半径按比例伸缩。"""
    lm = [(0.0, 0.0)] * 21
    for i, (base, tip, ang) in enumerate([(5, 8, 0.2), (9, 12, 0.0),
                                          (13, 16, -0.2), (17, 20, -0.4)]):
        r = index_ratio if i == 0 else other_ratio
        lm[base] = (math.cos(ang), math.sin(ang))
        lm[tip] = (r * math.cos(ang), r * math.sin(ang))
    return lm


class TestIsPointing:
    def test_index_extended_others_curled(self):
        assert is_pointing(make_hand(1.6, 1.0))

    def test_fist_not_pointing(self):
        assert not is_pointing(make_hand(1.0, 1.0))

    def test_open_palm_not_pointing(self):
        assert not is_pointing(make_hand(1.6, 1.6))

    def test_short_landmarks(self):
        assert not is_pointing([(0, 0)] * 10)
        assert not is_pointing([])
        assert not is_pointing(None)


def obj(cx, cy, half=20):
    return {"class_id": 39, "class_name": "cup", "confidence": 0.9,
            "bbox": [cx - half, cy - half, cx + half, cy + half]}


class TestFindPointedObject:
    TIP = (100, 100)
    MCP = (50, 100)  # 指向正右方

    def test_object_directly_ahead(self):
        target = obj(300, 100)
        assert find_pointed_object([target], self.TIP, self.MCP) is target

    def test_nearest_ahead_wins(self):
        near, far = obj(180, 100), obj(500, 105)
        assert find_pointed_object([far, near], self.TIP, self.MCP) is near

    def test_object_behind_ignored(self):
        assert find_pointed_object([obj(30, 100)], self.TIP, self.MCP) is None

    def test_no_false_positive_on_empty_pointing(self):
        """指向空白/侧向物体时不得误报（修复前"最近物体兜底"必报最近项）。"""
        side = obj(100, 500)  # 正下方，与指向方向夹角 90°，超出锥域
        assert find_pointed_object([side], self.TIP, self.MCP) is None

    def test_offaxis_within_cone_matches(self):
        diagonal = obj(160, 120)  # 前方略偏，约 18°，在 45° 锥域内
        assert find_pointed_object([diagonal], self.TIP, self.MCP) is diagonal

    def test_cone_rejects_wide_angle(self):
        wide = obj(150, 320)  # 前方但夹角约 76°
        assert find_pointed_object([wide], self.TIP, self.MCP) is None

    def test_cone_shrinks_with_tighter_angle(self):
        diagonal = obj(160, 120)  # 夹角约 18.4°：45° 锥内命中，15° 锥外拒绝
        assert find_pointed_object([diagonal], self.TIP, self.MCP,
                                   max_angle_deg=15.0) is None

    def test_empty_inputs(self):
        assert find_pointed_object([], self.TIP, self.MCP) is None
        assert find_pointed_object([obj(1, 1)], None, self.MCP) is None
        assert find_pointed_object([obj(1, 1)], self.TIP, self.TIP) is None


class TestScaling:
    def test_scale_point(self):
        assert scale_point((10, 20), 2) == [20, 40]
        assert scale_point(None, 2) is None
        assert scale_point((7, 7), 1) == [7, 7]

    def test_scale_bbox(self):
        assert scale_bbox([10, 20, 30, 40], 2) == [20, 40, 60, 80]

    def test_scale_objects_no_mutation(self):
        original = obj(300, 100)
        scaled = scale_objects([original], 2)
        assert scaled[0]["bbox"] == [560, 160, 640, 240]
        assert original["bbox"] == [280, 80, 320, 120]  # 未被修改
        assert scaled[0]["class_name"] == "cup"

    def test_scale_landmarks(self):
        assert scale_landmarks([[1, 2], [3, 4]], 2) == [[2, 4], [6, 8]]
        assert scale_landmarks([], 2) == []
        assert scale_landmarks(None, 2) == []
