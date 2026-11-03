# -*- coding: utf-8 -*-
"""重绘 6 张图（图2.1/2.2/4.1/4.2/4.3/4.4），所有图形尺寸由实测文字决定，保证文字在框内。"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Ellipse, FancyBboxPatch, FancyArrowPatch, Rectangle

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
FIG = r"D:\py workspace\3B412\_report_figs"


def new_canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    fig.canvas.draw()
    return fig, ax


def measure(fig, ax, text, fs, bold=False):
    """测量文字在该 axes 数据坐标下的宽高。"""
    tmp = ax.text(0, 0, text, fontsize=fs,
                  fontweight="bold" if bold else "normal")
    r = fig.canvas.get_renderer()
    fig.canvas.draw()
    bb = tmp.get_window_extent(renderer=r)
    inv = ax.transData.inverted()
    x0, y0 = inv.transform((bb.x0, bb.y0))
    x1, y1 = inv.transform((bb.x1, bb.y1))
    tmp.remove()
    return abs(x1 - x0), abs(y1 - y0)


def oval_fit(ax, fig, cx, cy, text, fs=9, pad=1.3, fc="white", ec="#555"):
    """椭圆：宽度按最长行实测，高度按整段文字×2.4，保证文字在椭圆内。"""
    lines = text.split("\n")
    tw = max(measure(fig, ax, ln, fs)[0] for ln in lines)
    th = sum(measure(fig, ax, ln, fs)[1] for ln in lines) * (1 + 0.25 * (len(lines) - 1))
    w = max(tw * pad + 0.02, 0.10)
    h = max(th * 2.4 + 0.02, 0.06)
    ax.add_patch(Ellipse((cx, cy), w, h, fc=fc, ec=ec, lw=1.3))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs)
    return w, h


def rbox_fit(ax, fig, cx, cy, text, fs=9, fc="#eaf2ff", ec="#2f6fe0",
             padx=0.035, pady=1.9, bold=False):
    tw, th = measure(fig, ax, text, fs, bold)
    w = tw + padx
    h = max(th * pady, 0.05)
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                boxstyle="round,pad=0.008", fc=fc, ec=ec, lw=1.3))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal")
    return w, h


def diamond_fit(ax, fig, cx, cy, text, fs=9, fc="#fff4e0", ec="#d97706"):
    tw, th = measure(fig, ax, text, fs)
    w = max(tw * 2.35 + 0.02, 0.10)
    h = max(th * 3.0 + 0.02, 0.07)
    ax.add_patch(mpatches.Polygon([(cx, cy + h / 2), (cx + w / 2, cy),
                                   (cx, cy - h / 2), (cx - w / 2, cy)],
                                  closed=True, fc=fc, ec=ec, lw=1.3))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs)
    return w, h


def square_fit(ax, fig, cx, cy, text, fs=9, fc="#dbe7ff", ec="#333"):
    tw, th = measure(fig, ax, text, fs)
    w = tw + 0.03
    h = max(th * 2.0, 0.06)
    ax.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h, fc=fc, ec=ec, lw=1.4))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs)
    return w, h


def arrow(ax, p1, p2, label="", fs=8.5, dashed=False, ls_label=(0.01, 0.012)):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=12,
                                 color="#555", lw=1.1,
                                 linestyle="--" if dashed else "-"))
    if label:
        lx, ly = ls_label if isinstance(ls_label, tuple) else (0.01, 0.012)
        ax.text((p1[0] + p2[0]) / 2 + lx, (p1[1] + p2[1]) / 2 + ly,
                label, fontsize=fs, color="#333", ha="left")


def line(ax, p1, p2):
    ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#555", lw=1.1)


# ================= 图2.1 用例图 =================
fig, ax = new_canvas(10.5, 6.0)
ucs = [
    "选择视频源（摄像头/文件/手机）", "指向画面中的物品",
    "查看检测与确认状态", "文字输入问题并获取回答",
    "语音输入问题（录音→转写）", "查看/回看历史记录", "重置当前识别物品",
]
ys = [0.88, 0.75, 0.62, 0.49, 0.35, 0.22, 0.09]
sizes = []
for t, y in zip(ucs, ys):
    sizes.append(oval_fit(ax, fig, 0.56, y, t, fs=9.5, pad=1.45))
maxw = max(w for w, h in sizes)
bx0, bx1 = 0.56 - maxw / 2 - 0.035, 0.56 + maxw / 2 + 0.035
ax.add_patch(Rectangle((bx0, 0.03), bx1 - bx0, 0.93, fill=False, ec="#888", lw=1.2))
ax.text((bx0 + bx1) / 2, 0.985, "手势指示多模态问答系统", ha="center", fontsize=10.5, weight="bold")

def actor(x, y, name):
    ax.add_patch(Ellipse((x, y + 0.055), 0.03, 0.04, fill=False, ec="#333", lw=1.3))
    line(ax, (x, y + 0.035), (x, y - 0.01))
    line(ax, (x - 0.022, y + 0.02), (x + 0.022, y + 0.02))
    line(ax, (x, y - 0.01), (x - 0.018, y - 0.05))
    line(ax, (x, y - 0.01), (x + 0.018, y - 0.05))
    ax.text(x, y - 0.075, name, ha="center", fontsize=9.5)

actor(0.12, 0.52, "使用者")
for (w, _), y in zip(sizes, ys):
    line(ax, (0.135, 0.52), (0.56 - w / 2 - 0.005, y))
arrow(ax, (0.56, 0.35 + sizes[4][1] / 2), (0.56, 0.49 - sizes[3][1] / 2),
      "«include» 转写为文本", dashed=True)
arrow(ax, (0.56, 0.75 - sizes[1][1] / 2), (0.56, 0.62 + sizes[2][1] / 2),
      "«include» 锥域匹配与多帧确认", dashed=True)
actor(0.93, 0.49, "云端大模型")
line(ax, (0.56 + sizes[3][0] / 2, 0.49), (0.915, 0.49))
ax.text(0.75, 0.505, "问答请求(SSE)", fontsize=8)
fig.savefig(os.path.join(FIG, "fig_usecase.png"), dpi=150, bbox_inches="tight")
plt.close(fig)
print("2.1 usecase ok")

# ================= 图2.2 数据流图 =================
fig, ax = new_canvas(10.5, 6.6)
ew, eh = square_fit(ax, fig, 0.12, 0.88, "使用者\n(摄像头/麦克风)", fs=8.5)
pw, ph = square_fit(ax, fig, 0.12, 0.55, "手机端\nIP Webcam", fs=8.5)
cw, chh = square_fit(ax, fig, 0.88, 0.88, "云端 Qwen-omni", fs=8.5)
pdefs = [
    (0.36, 0.88, "P1  音视频接入与解码"),
    (0.36, 0.62, "P2  手势/物体识别"),
    (0.36, 0.36, "P3  指向匹配与确认"),
    (0.68, 0.62, "P4  多模态问答/转写"),
    (0.68, 0.24, "P5  存储与历史查询"),
]
ps = [oval_fit(ax, fig, x, y, t, fs=9, pad=1.12, fc="#fff4e0", ec="#d97706")
      for x, y, t in pdefs]
def store(cx, cy, t):
    tw, th = measure(fig, ax, t, 8.5)
    w = max(tw + 0.075, 0.16); h = 0.05
    ax.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h, fc="white", ec="#333", lw=1.2))
    ax.plot([cx - w / 2 + 0.03, cx - w / 2 + 0.03], [cy - h / 2, cy + h / 2], color="#333", lw=1)
    ax.text(cx + 0.015, cy, t, ha="center", va="center", fontsize=8.5)
    return w
sw1 = store(0.92, 0.16, "D1 历史记录表")
store(0.92, 0.10, "D2 物品统计表")
store(0.92, 0.04, "D3 截图文件")
arrow(ax, (0.12 + ew / 2, 0.895), (0.36 - ps[0][0] / 2, 0.895), "视频帧/音频", ls_label=(-0.02, 0.014))
arrow(ax, (0.12 + pw / 2, 0.565), (0.36 - ps[0][0] / 2, 0.85), "MJPEG/WAV流", ls_label=(0.005, 0.02))
arrow(ax, (0.36, 0.88 - ps[0][1] / 2), (0.36, 0.62 + ps[1][1] / 2), "待检帧")
arrow(ax, (0.36, 0.62 - ps[1][1] / 2), (0.36, 0.36 + ps[2][1] / 2), "关键点+物品框")
arrow(ax, (0.36 + ps[2][0] / 2, 0.39), (0.68 - ps[3][0] / 2, 0.60), "锁定物品裁剪图", ls_label=(-0.03, 0.01))
arrow(ax, (0.68 + ps[3][0] / 2, 0.65), (0.88 - cw / 2, 0.86), "图像+问题/音频", ls_label=(-0.06, 0.01))
arrow(ax, (0.88 - cw / 2, 0.875), (0.68 + ps[3][0] / 2 - 0.01, 0.635), "回答/转写", ls_label=(-0.045, -0.03))
arrow(ax, (0.68, 0.62 - ps[3][1] / 2), (0.68, 0.24 + ps[4][1] / 2), "问答记录")
arrow(ax, (0.68 + ps[4][0] / 2 - 0.02, 0.22), (0.92 - sw1 / 2 + 0.02, 0.175), "写入")
arrow(ax, (0.92 - sw1 / 2, 0.115), (0.68 + ps[4][0] / 2 - 0.02, 0.255), "查询回看", ls_label=(-0.055, -0.02))
fig.savefig(os.path.join(FIG, "fig_dfd.png"), dpi=150, bbox_inches="tight")
plt.close(fig)
print("2.2 dfd ok")


# ================= 流程图通用渲染器（垂直主链 + 侧分支） =================
def render_flow(fname, main_nodes, branches, size=(6.4, 8.8), gx=0.46):
    """main_nodes: [(kind,text)]; branches: [(from_idx, side('r'/'l'), kind, text, label)]"""
    fig, ax = new_canvas(*size)
    n = len(main_nodes)
    pitch = 0.86 / max(n - 1, 1)
    top, x = 0.95, gx
    geo = []
    for i, (kind, t) in enumerate(main_nodes):
        y = top - i * pitch
        if kind == "se":
            w, h = oval_fit(ax, fig, x, y, t, fs=9, fc="#dbe7ff", ec="#333")
        elif kind == "d":
            w, h = diamond_fit(ax, fig, x, y, t, fs=9)
        else:
            w, h = rbox_fit(ax, fig, x, y, t, fs=9)
        geo.append((x, y, w, h))
    for i in range(n - 1):
        x1, y1, w1, h1 = geo[i]
        x2, y2, w2, h2 = geo[i + 1]
        arrow(ax, (x1, y1 - h1 / 2), (x2, y2 + h2 / 2))
        # 主链是/否标签由分支函数决定，这里不加
    for (fi, side, kind, t, label) in branches:
        x0, y0, w0, h0 = geo[fi]
        bx = x0 + 0.30 if side == "r" else x0 - 0.30
        if kind == "se":
            w, h = oval_fit(ax, fig, bx, y0, t, fs=8.5, fc="#dbe7ff", ec="#333")
        elif kind == "d":
            w, h = diamond_fit(ax, fig, bx, y0, t, fs=8.5)
        else:
            w, h = rbox_fit(ax, fig, bx, y0, t, fs=8.5, fc="#f2f2f2", ec="#777")
        p1 = (x0 + w0 / 2 if side == "r" else x0 - w0 / 2, y0)
        p2 = (bx - w / 2 if side == "r" else bx + w / 2, y0)
        off = (0.008, 0.012) if side == "r" else (-0.028, 0.012)
        arrow(ax, p1, p2, label, ls_label=off)
    fig.savefig(os.path.join(FIG, fname), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(fname, "ok")


render_flow("fig_flow_point.png",
    [("se", "收到视频帧"),
     ("p", "解码并降采样(宽≤1280)"),
     ("p", "MediaPipe 手部关键点检测"),
     ("d", "检测到手?"),
     ("d", "指向手势成立?"),
     ("p", "YOLOv8 物品检测"),
     ("d", "锥域内命中物品?"),
     ("p", "同一物品: 计数+1\n否则重置为1; 脱靶: 计数-1"),
     ("d", "计数 ≥ 3 ?"),
     ("se", "发布已确认, 裁剪物品图")],
    [(3, "r", "p", "提示: 未检测到手", "否"),
     (4, "r", "p", "提示: 无指向手势", "否"),
     (6, "r", "p", "提示: 指向无匹配", "否"),
     (8, "r", "p", "发布 CONFIRMING n/3", "否")])

render_flow("fig_flow_source.png",
    [("se", "点击「手机摄像头」"),
     ("p", "尝试 ADB 端口转发\n(8080/8081/18080)"),
     ("d", "本机端口探活成功?"),
     ("io", "弹出地址框\n(预填可用地址)"),
     ("p", "地址纠错: 补协议头/\n剥离调试端口 15555"),
     ("d", "URL 合法?"),
     ("p", "MjpegSource 连接 /video"),
     ("d", "HTTP 200 且含 JPEG?"),
     ("se", "持续拉帧→编码→\nWebSocket 发往后端")],
    [(2, "r", "p", "回退: 使用记忆地址\n或 WiFi 直连", "否"),
     (5, "r", "p", "弹框提示正确格式", "否"),
     (7, "r", "p", "指数退避重连\n(≤10 次后报错)", "否")])

render_flow("fig_flow_voice.png",
    [("se", "打开语音输入开关"),
     ("io", "选择音源: PC / 手机"),
     ("p", "开始录音\n(打开设备 / 拉 WAV 流)"),
     ("d", "停止或达 15s?"),
     ("p", "停止采集, 封装标准音频"),
     ("d", "时长 ≥ 0.5s?"),
     ("p", "POST /asr\nQwen-omni 转写"),
     ("d", "返回文本?"),
     ("p", "转写填入输入框(可编辑)"),
     ("se", "回车发送 → /qa 流式回答")],
    [(3, "l", "p", "继续录音累积", "否"),
     (5, "r", "p", "提示录音太短, 丢弃", "否"),
     (7, "r", "p", "提示失败原因, 可重录", "否")])


# ================= 图4.4 类图 =================
fig, ax = new_canvas(10.5, 6.8)

def class_box(cx, cy, name, attrs, methods, fs=8.5, fc="#eaf2ff"):
    tw_n, _ = measure(fig, ax, name, fs + 0.5, bold=True)
    w = tw_n + 0.03
    for s in attrs + methods:
        for ln in s.split("\n"):
            w = max(w, measure(fig, ax, ln, fs)[0] + 0.025)
    h_title, h_attr, h_meth = 0.048, 0.030 * len(attrs) + 0.012, 0.030 * len(methods) + 0.012
    h = h_title + h_attr + h_meth
    x, y = cx - w / 2, cy - h / 2
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec="#333", lw=1.3))
    ax.text(cx, y + h - h_title / 2, name, ha="center", va="center",
            fontsize=fs + 0.5, weight="bold")
    ax.plot([x, x + w], [y + h - h_title] * 2, color="#333", lw=0.9)
    accy = y + h - h_title - 0.022
    for s in attrs:
        ax.text(x + 0.008, accy, s, fontsize=fs, va="center")
        accy -= 0.027
    ax.plot([x, x + w], [accy + 0.014] * 2, color="#333", lw=0.9)
    accy -= 0.012
    for s in methods:
        ax.text(x + 0.008, accy, s, fontsize=fs, va="center")
        accy -= 0.027
    return x, y, w, h

boxes = {}
boxes["MW"] = class_box(0.17, 0.80, "MainWindow(QMainWindow)",
                        ["camera_thread: CameraThread", "video_source / video_path",
                         "last_object_image"],
                        ["handle_detection(r)", "send_question()",
                         "_toggle_record()"], fc="#fff4e0")
boxes["CT"] = class_box(0.17, 0.42, "CameraThread(QThread)",
                        ["_latest_frame + Lock", "ws: WebSocket", "_receiver_thread"],
                        ["run()", "get_current_frame()", "send_reset()"], fc="#fff4e0")
boxes["OD"] = class_box(0.50, 0.80, "ObjectDetector",
                        ["model: YOLO", "confidence", "max_angle_deg"],
                        ["detect(frame)", "find_pointed_object()"], fc="#e6f7ee")
boxes["GD"] = class_box(0.50, 0.45, "GestureDetector",
                        ["landmarker: HandLandmarker", "_last_ts_ms"],
                        ["detect(frame)", "release()"], fc="#e6f7ee")
boxes["LC"] = class_box(0.83, 0.80, "LLMClient",
                        ["api_key, model", "base_url"],
                        ["ask_stream(q, img)", "transcribe_audio()"], fc="#ffe4e6")
boxes["DB"] = class_box(0.83, 0.52, "Database",
                        ["connection, _lock", "config: dict"],
                        ["save_detection()", "get_history()", "_execute(sql)"], fc="#ffe4e6")
boxes["GE"] = class_box(0.50, 0.155, "geometry 纯函数模块",
                        ["(无状态)"],
                        ["is_pointing(lm)", "find_pointed_object(...)", "scale_*()"], fc="#f3e8ff")

def edge(a, b, la, x1=None, y1=None, x2=None, y2=None):
    ax1, ay1, aw1, ah1 = a
    ax2, ay2, aw2, ah2 = b
    p1 = (x1 if x1 is not None else ax1 + aw1 / 2, y1 if y1 is not None else ay1 + ah1 / 2)
    p2 = (x2 if x2 is not None else ax2 + aw2 / 2, y2 if y2 is not None else ay2 + ah2 / 2)
    arrow(ax, p1, p2, la)

edge(boxes["MW"], boxes["CT"], "创建/持有",
     x1=0.17, y1=0.80 - 0.10, x2=0.17, y2=0.42 + 0.12)
arrow(ax, (0.17 + 0.135, 0.40), (0.50 - 0.14, 0.385), "")
ax.text(0.235, 0.425, "帧→后端", fontsize=8.5, color="#333")
edge(boxes["GD"], boxes["GE"], "依赖", x1=0.50, y1=0.45 - 0.10, x2=0.50, y2=0.155 + 0.12)
edge(boxes["OD"], boxes["GE"], "依赖", x1=0.50, y1=0.80 - 0.10, x2=0.50, y2=0.45 + 0.11)
edge(boxes["GE"], boxes["DB"], "经 app.py 装配", x1=0.50 + 0.16, y1=0.18, x2=0.83, y2=0.52 - 0.10)
ax.text(0.5, 0.015, "注：前端经 WebSocket/HTTP 与后端 app.py 交互；OD/GD/LC/DB 均由 app.py 在 lifespan 中装配",
        ha="center", fontsize=8.5, color="#777")
fig.savefig(os.path.join(FIG, "fig_class.png"), dpi=150, bbox_inches="tight")
plt.close(fig)
print("4.4 class ok")
print("ALL FIT FIGURES DONE")
