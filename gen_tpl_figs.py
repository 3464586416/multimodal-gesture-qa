# -*- coding: utf-8 -*-
"""生成模板2所需工程图（全部程序绘制：matplotlib/cv2，非AI生成图）。
用例图 / 功能模块图 / E-R图 / 类图 / 流程图x3 / 状态图 / 确认中叠加示意。"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mp
from matplotlib.patches import Ellipse, FancyBboxPatch, FancyArrowPatch, Rectangle

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
FIG = r"D:\py workspace\3B412\_report_figs"
import os
os.makedirs(FIG, exist_ok=True)


def canvas(w=10.5, h=6.2):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, fc="#eaf2ff", ec="#2f6fe0", fs=10):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012",
                                fc=fc, ec=ec, lw=1.3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def diamond(ax, cx, cy, w, h, text, fs=9, fc="#fff4e0", ec="#d97706"):
    ax.add_patch(mp.Polygon([(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2),
                             (cx - w / 2, cy)], closed=True, fc=fc, ec=ec, lw=1.3))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs)


def oval(ax, cx, cy, w, h, text, fs=9.5, fc="#fff", ec="#555"):
    ax.add_patch(Ellipse((cx, cy), w, h, fc=fc, ec=ec, lw=1.2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs)


def edge(ax, p1, p2, label="", fs=8.5, arrow=True, style="->", color="#555"):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style if arrow else "-",
                                 mutation_scale=12, color=color, lw=1.1))
    if label:
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        ax.text(mx + 0.012, my + 0.012, label, fontsize=fs, color="#333")


def actor(ax, x, y, name, fs=10):
    ax.add_patch(Ellipse((x, y + 0.062), 0.028, 0.045, fc="#fff", ec="#333", lw=1.3))
    ax.plot([x, x], [y + 0.04, y - 0.01], color="#333", lw=1.3)
    ax.plot([x - 0.022, x + 0.022], [y + 0.025, y + 0.025], color="#333", lw=1.3)
    ax.plot([x, x - 0.018], [y - 0.01, y - 0.05], color="#333", lw=1.3)
    ax.plot([x, x + 0.018], [y - 0.01, y - 0.05], color="#333", lw=1.3)
    ax.text(x, y - 0.085, name, ha="center", fontsize=fs)


# ================= 图2.1 用例图 =================
fig, ax = canvas(10.5, 5.6)
ax.add_patch(Rectangle((0.26, 0.06), 0.5, 0.88, fc="#fafafa", ec="#888", lw=1.2))
ax.text(0.51, 0.955, "手势指示多模态问答系统", ha="center", fontsize=11, weight="bold")
ucs = [
    ("选择视频源(摄像头/文件/手机)", 0.51, 0.82),
    ("指向画面物品", 0.51, 0.68),
    ("查看检测与确认状态", 0.51, 0.54),
    ("文字输入问题", 0.51, 0.40),
    ("语音输入问题", 0.51, 0.26),
    ("查看/回看历史记录", 0.51, 0.13),
]
for t, cx, cy in ucs:
    oval(ax, cx, cy, 0.44, 0.09, t, fs=9)
actor(ax, 0.11, 0.5, "使用者")
for t, cx, cy in ucs[:2] + ucs[3:]:
    edge(ax, (0.125, 0.5), (cx - 0.22, cy), arrow=False)
edge(ax, (0.125, 0.44), (ucs[2][1] - 0.22, ucs[2][2]), arrow=False)
edge(ax, (0.125, 0.3), (ucs[5][1] - 0.22, ucs[5][2] + 0.02), arrow=False)
# include 关系：语音输入 -> 文字输入（转写填入），指向物品 include 查看确认
arrow = FancyArrowPatch((0.51, 0.26 + 0.05), (0.51, 0.40 - 0.05),
                        arrowstyle="-|>", mutation_scale=10, color="#666",
                        linestyle="--", lw=1)
ax.add_patch(arrow)
ax.text(0.525, 0.33, "«include»\n转写为文本", fontsize=7.5, color="#666")
ax.add_patch(FancyArrowPatch((0.51, 0.68 - 0.048), (0.51, 0.54 + 0.048),
                             arrowstyle="-|>", mutation_scale=10, color="#666",
                             linestyle="--", lw=1))
ax.text(0.525, 0.60, "«include» 锥域匹配+多帧确认", fontsize=7.5, color="#666")
actor(ax, 0.9, 0.4, "云端大模型")
edge(ax, (0.73, 0.40), (0.885, 0.36), "问答请求", arrow=False)
fig.savefig(os.path.join(FIG, "fig_usecase.png"), dpi=150); plt.close(fig)
print("usecase ok")

# ================= 图3.2 功能模块图 =================
fig, ax = canvas(10.5, 5.4)
box(ax, 0.33, 0.84, 0.34, 0.1, "实时物体识别问答系统", fc="#dbe7ff", fs=11)
mods = [
    (0.02, "视频/音频接入", "摄像头\n视频文件\n手机MJPEG流\n手机/PC麦克风"),
    (0.21, "识别与匹配", "手势判定\n物体检测\n锥域指向匹配\n多帧确认"),
    (0.40, "问答交互", "图像问答(SSE)\n语音转写\n打字机展示\n物品元数据"),
    (0.59, "数据管理", "历史记录落库\n截图存储/回看\n物品统计\n重连与容错"),
    (0.78, "界面呈现", "深色主题UI\n状态徽章\n检测叠加层\n历史面板"),
]
for x, title, detail in mods:
    box(ax, x, 0.56, 0.18, 0.08, title, fc="#e6f7ee", ec="#16a34a", fs=10)
    box(ax, x, 0.20, 0.18, 0.31, detail, fc="#fff", ec="#999", fs=8.5)
    edge(ax, (x + 0.09, 0.64), (x + 0.09, 0.56), arrow=False)
    edge(ax, (0.5, 0.84), (x + 0.09, 0.64), arrow=False)
fig.savefig(os.path.join(FIG, "fig_modules.png"), dpi=150); plt.close(fig)
print("modules ok")

# ================= 图3.3 E-R图 =================
fig, ax = canvas(10.5, 6.0)
# 实体:用户 / 问答记录 / 物品统计
box(ax, 0.06, 0.45, 0.13, 0.09, "用户", fc="#dbe7ff", ec="#333")
box(ax, 0.44, 0.45, 0.16, 0.09, "问答记录", fc="#dbe7ff", ec="#333")
box(ax, 0.82, 0.45, 0.14, 0.09, "物品统计", fc="#dbe7ff", ec="#333")
diamond(ax, 0.29, 0.495, 0.11, 0.09, "发起", fc="#fff4e0")
diamond(ax, 0.71, 0.495, 0.11, 0.09, "归类", fc="#fff4e0")
edge(ax, (0.19, 0.495), (0.235, 0.495), arrow=False)
ax.text(0.2, 0.515, "1", fontsize=9)
edge(ax, (0.345, 0.495), (0.44, 0.495), arrow=False)
ax.text(0.36, 0.515, "n", fontsize=9)
edge(ax, (0.60, 0.495), (0.655, 0.495), arrow=False)
ax.text(0.61, 0.515, "n", fontsize=9)
edge(ax, (0.765, 0.495), (0.82, 0.495), arrow=False)
ax.text(0.78, 0.515, "1", fontsize=9)
# 属性椭圆
attrs_rec = ["记录ID", "时间", "置信度", "边界框", "问题", "回答", "截图路径", "物品名称", "COCO类别"]
pos = [(0.36, 0.30), (0.44, 0.26), (0.52, 0.30), (0.60, 0.26),
       (0.34, 0.13), (0.44, 0.09), (0.54, 0.13), (0.63, 0.10), (0.70, 0.20)]
for (name, (cx, cy)) in zip(attrs_rec, pos):
    oval(ax, cx, cy, 0.09, 0.07, name, fs=8)
    edge(ax, (cx, cy + 0.035), (0.52, 0.45), arrow=False)
oval(ax, 0.10, 0.20, 0.1, 0.07, "用户角色", fs=8)
edge(ax, (0.10, 0.235), (0.125, 0.45), arrow=False)
attrs_obj = ["名称(唯一)", "首见时间", "最近时间", "累计次数"]
opos = [(0.83, 0.30), (0.92, 0.30), (0.83, 0.20), (0.92, 0.20)]
for (name, (cx, cy)) in zip(attrs_obj, opos):
    oval(ax, cx, cy, 0.1, 0.07, name, fs=8)
    edge(ax, (cx, cy + 0.035), (0.89, 0.45), arrow=False)
fig.savefig(os.path.join(FIG, "fig_er.png"), dpi=150); plt.close(fig)
print("er ok")

# ================= 图4.2 核心类图 =================
fig, ax = canvas(10.5, 6.4)


def class_box(ax, x, y, w, h, name, attrs, methods, fc="#eaf2ff"):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec="#333", lw=1.3))
    ax.text(x + w / 2, y + h - 0.05, name, ha="center", fontsize=10, weight="bold")
    ax.plot([x, x + w], [y + h - 0.08] * 2, color="#333", lw=0.9)
    ax.text(x + 0.008, y + h - 0.095, "\n".join(attrs), fontsize=7.8, va="top")
    sep_y = y + h - 0.1 - 0.022 * len(attrs) - 0.02
    ax.plot([x, x + w], [sep_y] * 2, color="#333", lw=0.9)
    ax.text(x + 0.008, sep_y - 0.018, "\n".join(methods), fontsize=7.8, va="top")


class_box(ax, 0.02, 0.72, 0.25, 0.26, "MainWindow(QMainWindow)",
          ["camera_thread: CameraThread", "video_source/video_path", "last_object_image"],
          ["handle_detection(r)", "send_question()", "_toggle_record()"], fc="#fff4e0")
class_box(ax, 0.02, 0.38, 0.25, 0.26, "CameraThread(QThread)",
          ["_latest_frame + Lock", "ws: WebSocket", "_receiver_thread"],
          ["run()", "get_current_frame()", "send_reset()"], fc="#fff4e0")
class_box(ax, 0.38, 0.72, 0.26, 0.26, "ObjectDetector",
          ["model: YOLO", "confidence", "max_angle_deg"],
          ["detect(frame) -> dict", "find_pointed_object(\n  objects, tip, mcp)"], fc="#e6f7ee")
class_box(ax, 0.38, 0.38, 0.26, 0.26, "GestureDetector",
          ["landmarker: HandLandmarker", "_last_ts_ms"],
          ["detect(frame) -> dict", "release()"], fc="#e6f7ee")
class_box(ax, 0.71, 0.72, 0.27, 0.26, "LLMClient",
          ["api_key, model", "base_url"],
          ["ask_stream(q, img)", "transcribe_audio(wav, fmt)"], fc="#ffe4e6")
class_box(ax, 0.71, 0.38, 0.27, 0.26, "Database",
          ["connection, _lock", "config: dict"],
          ["save_detection()", "get_history()", "_execute(sql)"], fc="#ffe4e6")
class_box(ax, 0.38, 0.06, 0.26, 0.22, "geometry(纯函数模块)",
          ["无状态"],
          ["is_pointing(lm)", "find_pointed_object(...)", "scale_*()"], fc="#f3e8ff")
edge(ax, (0.145, 0.72), (0.145, 0.64), "")
ax.text(0.155, 0.675, "创建/持有", fontsize=8)
edge(ax, (0.27, 0.51), (0.38, 0.51), "")
ax.text(0.275, 0.525, "帧→后端", fontsize=8)
edge(ax, (0.51, 0.38), (0.51, 0.28), "")
ax.text(0.52, 0.32, "依赖", fontsize=8)
edge(ax, (0.64, 0.17), (0.71, 0.45), "")
ax.text(0.66, 0.24, "依赖", fontsize=8)
ax.text(0.5, 0.015, "注：右侧服务类由 backend/app.py（FastAPI）在 lifespan 中装配，经 WebSocket/HTTP 路由被调用",
        ha="center", fontsize=8.5, color="#777")
fig.savefig(os.path.join(FIG, "fig_class.png"), dpi=150); plt.close(fig)
print("class ok")


def flowchart(fname, nodes, edges_spec, size=(6.2, 8.6), xlim=1.0):
    fig, ax = canvas(*size)
    for n in nodes:
        kind, cx, cy, text = n["k"], n["x"], n["y"], n["t"]
        if kind == "se":
            oval(ax, cx, cy, 0.16, 0.05, text, fc="#dbe7ff")
        elif kind == "p":
            box(ax, cx - 0.09, cy - 0.026, 0.18, 0.052, text)
        elif kind == "d":
            diamond(ax, cx, cy, 0.2, 0.075, text)
        elif kind == "io":
            ax.add_patch(mp.Polygon([(cx - 0.075, cy - 0.026), (cx + 0.085, cy - 0.026),
                                     (cx + 0.075, cy + 0.026), (cx - 0.085, cy + 0.026)],
                                    closed=True, fc="#f0f0f0", ec="#555", lw=1.2))
            ax.text(cx, cy, text, ha="center", va="center", fontsize=9)
    for e in edges_spec:
        a, b, label = e[0], e[1], e[2] if len(e) > 2 else ""
        style = "-|>"
        ls = "--" if label and "否" in label else "-"
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=11,
                                     color="#555", lw=1.1, linestyle=ls))
        if label:
            ax.text((a[0] + b[0]) / 2 + 0.015, (a[1] + b[1]) / 2, label,
                    fontsize=8, color="#333")
    fig.savefig(os.path.join(FIG, fname), dpi=150)
    plt.close(fig)
    print(fname, "ok")


# ============ 图4.1(a) 指向确认流程图 ============
nodes = [
    dict(k="se", x=0.5, y=0.95, t="收到视频帧"),
    dict(k="p", x=0.5, y=0.87, t="解码/降采样(≤1280)"),
    dict(k="p", x=0.5, y=0.79, t="MediaPipe 关键点检测(VIDEO)"),
    dict(k="d", x=0.5, y=0.69, t="检测到手?"),
    dict(k="d", x=0.5, y=0.585, t="指向手势成立?"),
    dict(k="p", x=0.5, y=0.49, t="YOLOv8 物品检测"),
    dict(k="d", x=0.5, y=0.39, t="锥域内命中物品?"),
    dict(k="p", x=0.5, y=0.295, t="同一物品? 计数+1 : 重置1"),
    dict(k="d", x=0.5, y=0.19, t="计数 ≥ 3?"),
    dict(k="se", x=0.5, y=0.08, t="发布已确认+截图裁剪"),
    dict(k="p", x=0.87, y=0.69, t="提示:未检测到手"),
    dict(k="p", x=0.87, y=0.39, t="提示:指向无匹配"),
    dict(k="p", x=0.13, y=0.295, t="计数-1(衰减)"),
    dict(k="p", x=0.87, y=0.19, t="发布 CONFIRMING n/3"),
]
edges_spec = [
    ((0.5, 0.925), (0.5, 0.895)), ((0.5, 0.845), (0.5, 0.815)),
    ((0.5, 0.764), (0.5, 0.727)),
    ((0.5, 0.652), (0.5, 0.622), "是"),
    ((0.5, 0.547), (0.5, 0.515), "是"),
    ((0.5, 0.464), (0.5, 0.427)),
    ((0.5, 0.352), (0.5, 0.321), "是"),
    ((0.5, 0.269), (0.5, 0.227)),
    ((0.5, 0.152), (0.5, 0.105), "是"),
    ((0.6, 0.69), (0.78, 0.69), "否"),
    ((0.6, 0.39), (0.78, 0.39), "否"),
    ((0.4, 0.295), (0.23, 0.295), "未命中"),
    ((0.4, 0.19), (0.77, 0.19), "否"),
]
flowchart("fig_flow_point.png", nodes, edges_spec)

# ============ 图4.1(b) 语音提问流程图 ============
nodes = [
    dict(k="se", x=0.5, y=0.95, t="打开语音输入开关"),
    dict(k="io", x=0.5, y=0.87, t="选择音源: PC/手机"),
    dict(k="p", x=0.5, y=0.79, t="点击开始录音(打开设备/拉流)"),
    dict(k="d", x=0.5, y=0.695, t="手动停止或达15s?"),
    dict(k="p", x=0.5, y=0.60, t="停止采集, 重建标准WAV/取MP3"),
    dict(k="d", x=0.5, y=0.505, t="时长≥0.5s?"),
    dict(k="p", x=0.5, y=0.41, t="POST /asr → Qwen-omni 转写"),
    dict(k="d", x=0.5, y=0.31, t="返回文本?"),
    dict(k="p", x=0.5, y=0.21, t="填入问题输入框(可编辑)"),
    dict(k="se", x=0.5, y=0.115, t="回车发送 → /qa 流式回答"),
    dict(k="p", x=0.86, y=0.505, t="提示:录音太短,丢弃"),
    dict(k="p", x=0.86, y=0.31, t="提示失败原因(保留重录)"),
    dict(k="p", x=0.14, y=0.695, t="继续录音/累积数据"),
]
edges_spec = [
    ((0.5, 0.922), (0.5, 0.896)), ((0.5, 0.844), (0.5, 0.816)),
    ((0.5, 0.764), (0.5, 0.732)),
    ((0.5, 0.657), (0.5, 0.626), "是"),
    ((0.5, 0.574), (0.5, 0.542)),
    ((0.5, 0.467), (0.5, 0.436), "是"),
    ((0.5, 0.384), (0.5, 0.347)),
    ((0.5, 0.272), (0.5, 0.236), "是"),
    ((0.5, 0.184), (0.5, 0.14)),
    ((0.6, 0.695), (0.775, 0.695)),  # loop placeholder drawn below
    ((0.5, 0.467), (0.86, 0.467), "否"),
    ((0.5, 0.272), (0.86, 0.29), "否"),
    ((0.14, 0.66), (0.49, 0.672), "否"),
]
flowchart("fig_flow_voice.png", nodes, edges_spec)

# ============ 图4.1(c) 手机视频源接入流程图 ============
nodes = [
    dict(k="se", x=0.5, y=0.95, t="点击「手机摄像头」"),
    dict(k="p", x=0.5, y=0.865, t="ADB转发探测(8080/8081/18080)"),
    dict(k="d", x=0.5, y=0.76, t="本机端口探活成功?"),
    dict(k="io", x=0.5, y=0.66, t="弹出地址框(预填直连/转发地址)"),
    dict(k="p", x=0.5, y=0.565, t="normalize 地址纠错(剥离15555等)"),
    dict(k="d", x=0.5, y=0.465, t="URL 合法?"),
    dict(k="p", x=0.5, y=0.365, t="MjpegSource 连接 /video"),
    dict(k="d", x=0.5, y=0.265, t="HTTP 200 且含JPEG?"),
    dict(k="se", x=0.5, y=0.16, t="持续拉帧→编码→WS发往后端"),
    dict(k="p", x=0.86, y=0.465, t="弹框提示正确格式"),
    dict(k="p", x=0.86, y=0.265, t="指数退避重连(≤10次)"),
    dict(k="p", x=0.14, y=0.76, t="回退:用记忆地址/WiFi直连"),
]
edges_spec = [
    ((0.5, 0.922), (0.5, 0.893)),
    ((0.5, 0.838), (0.5, 0.797)),
    ((0.5, 0.722), (0.5, 0.688), "是"),
    ((0.5, 0.634), (0.5, 0.593)),
    ((0.5, 0.538), (0.5, 0.503)),
    ((0.5, 0.427), (0.5, 0.393), "是"),
    ((0.5, 0.338), (0.5, 0.303)),
    ((0.5, 0.227), (0.5, 0.186), "是"),
    ((0.5, 0.722), (0.23, 0.762), "否"),
    ((0.6, 0.465), (0.775, 0.465), "否"),
    ((0.6, 0.265), (0.775, 0.265), "否"),
]
flowchart("fig_flow_source.png", nodes, edges_spec)

# ================= 图5.3 指向确认状态图 =================
fig, ax = canvas(10.5, 4.6)
st = [
    (0.08, "空闲", "#eee"), (0.24, "感知中", "#dbe7ff"), (0.40, "检测到手", "#fff4e0"),
    (0.56, "指向成立", "#fff4e0"), (0.72, "确认中 n/3", "#ffe4e6"), (0.88, "已确认", "#e6f7ee"),
]
for x, t, fc in st:
    ax.add_patch(Ellipse((x, 0.62), 0.135, 0.16, fc=fc, ec="#444", lw=1.3))
    ax.text(x, 0.62, t, ha="center", va="center", fontsize=9.5)
for i in range(len(st) - 1):
    edge(ax, (st[i][0] + 0.072, 0.62), (st[i + 1][0] - 0.072, 0.62), "")
edge(ax, (0.24, 0.54), (0.08, 0.54), "无手", style="-|>")
edge(ax, (0.4, 0.535), (0.24, 0.535), "手势不成立", style="-|>")
edge(ax, (0.72, 0.70), (0.56, 0.70), "未命中/衰减", style="-|>")
edge(ax, (0.88, 0.70), (0.72, 0.70), "换物品重置", style="-|>")
edge(ax, (0.88, 0.535), (0.24, 0.47), "「识别新物品」reset 指令", style="-|>")
ax.text(0.5, 0.16, "确认计数：同物品连续命中 +1，未命中 -1，达到阈值(默认3)进入「已确认」并允许提问",
        ha="center", fontsize=9, color="#555")
fig.savefig(os.path.join(FIG, "fig_state.png"), dpi=150); plt.close(fig)
print("state ok")

# ============ 图5.2 确认过程中帧 (叠加示意) ============
sys.path.insert(0, r"D:\py workspace\3B412\frontend")
import numpy as np
import cv2
import overlay
img = np.full((480, 854, 3), 40, np.uint8)
cv2.rectangle(img, (0, 380), (854, 480), (60, 50, 120), -1)
cv2.rectangle(img, (560, 240), (660, 360), (210, 160, 70), -1)
cv2.rectangle(img, (720, 200), (780, 360), (100, 190, 100), -1)
lm = [[120 + (i % 5) * 18, 330 - (i // 5) * 12] for i in range(21)]
res = {"status": "ok", "hand_detected": True, "pointing": True,
       "finger_tip": [300, 240], "finger_mcp": [210, 300], "landmarks": lm,
       "objects": [
           {"class_id": 41, "class_name": "cup", "confidence": 0.91, "bbox": [552, 232, 668, 368]},
           {"class_id": 39, "class_name": "bottle", "confidence": 0.85, "bbox": [716, 196, 786, 364]}],
       "pointed_object": None, "confirm_count": 2, "confirm_threshold": 3}
out = overlay.draw_overlay(img, res)
cv2.imwrite(os.path.join(FIG, "fig_overlay_confirm.png"), out)
print("overlay_confirm ok")

# ================= 图2.2 系统数据流图(1层) =================
fig, ax = canvas(10.5, 6.2)
# 外部实体：方框；加工：圆角；存储：开口条
def entity(x, y, w, h, t, fc="#dbe7ff"):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec="#333", lw=1.4))
    ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=9)

def store(x, y, w, h, t):
    ax.add_patch(Rectangle((x, y), w, h, fc="#fff", ec="#333", lw=1.4))
    ax.plot([x + 0.028, x + 0.028], [y, y + h], color="#333", lw=1.2)
    ax.text(x + 0.036 + w / 2, y + h / 2, t, ha="center", va="center", fontsize=8.5)

entity(0.02, 0.74, 0.14, 0.1, "使用者\n(摄像头/麦克风)")
entity(0.02, 0.34, 0.14, 0.1, "手机端\nIP Webcam")
entity(0.84, 0.55, 0.14, 0.1, "云端\nQwen-omni")
procs = [
    (0.30, 0.78, "P1\n音视频接入\n与帧解码"),
    (0.30, 0.55, "P2\n手势/物体\n识别"),
    (0.30, 0.32, "P3\n指向匹配\n与多帧确认"),
    (0.55, 0.55, "P4\n多模态问答\n/语音转写"),
    (0.55, 0.10, "P5\n数据存储与\n历史查询"),
]
for x, y, t in procs:
    ax.add_patch(FancyBboxPatch((x, y), 0.16, 0.11, boxstyle="round,pad=0.02",
                                fc="#fff4e0", ec="#d97706", lw=1.4))
    ax.text(x + 0.08, y + 0.055, t, ha="center", va="center", fontsize=8.5)
store(0.80, 0.26, 0.16, 0.06, "D1 历史记录表")
store(0.80, 0.17, 0.16, 0.06, "D2 物品统计表")
store(0.80, 0.08, 0.16, 0.06, "D3 截图文件")
edge(ax, (0.16, 0.80), (0.30, 0.83), "视频帧/音频流", fs=8)
edge(ax, (0.16, 0.38), (0.30, 0.80), "MJPEG/WAV流", fs=8)
edge(ax, (0.38, 0.78), (0.38, 0.66), "待检帧", fs=8)
edge(ax, (0.38, 0.55), (0.38, 0.43), "关键点+物品框", fs=8)
edge(ax, (0.46, 0.37), (0.55, 0.58), "锁定物品裁剪图", fs=8)
edge(ax, (0.63, 0.66), (0.84, 0.62), "图像+问题/音频", fs=8)
edge(ax, (0.86, 0.55), (0.71, 0.55), "回答/转写文本", fs=8)
edge(ax, (0.63, 0.55), (0.63, 0.21), "问答记录", fs=8)
edge(ax, (0.71, 0.15), (0.80, 0.20), "", fs=8)
edge(ax, (0.80, 0.13), (0.71, 0.11), "", fs=8)
fig.savefig(os.path.join(FIG, "fig_dfd.png"), dpi=150); plt.close(fig)
print("dfd ok")
print("ALL TPL FIGURES DONE")
