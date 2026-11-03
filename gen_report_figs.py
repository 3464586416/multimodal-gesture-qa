# -*- coding: utf-8 -*-
"""生成课程设计报告所需插图：架构图/流程图( matplotlib )、叠加效果图(cv2)、UI真实截图(PrintWindow)。"""
import os
import subprocess
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

FIG = r"D:\py workspace\3B412\_report_figs"
os.makedirs(FIG, exist_ok=True)


def box(ax, x, y, w, h, text, fc="#eaf2ff", ec="#2f6fe0", fs=11, bold=False):
    ax.add_patch(mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02",
        fc=fc, ec=ec, lw=1.5))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fs, fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, p1, p2, label="", color="#444", ls="-"):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="<|-|>", mutation_scale=14,
                                 color=color, linestyle=ls, lw=1.4))
    if label:
        ax.text((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 + 0.02, label,
                fontsize=9.5, ha="center", color="#333")


# ============ 图3.1 系统总体架构图 ============
fig, ax = plt.subplots(figsize=(10.5, 6.2))
ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

box(ax, 0.03, 0.72, 0.27, 0.2,
    "前端（PyQt5 桌面应用）\n视频显示 / 深色UI / 交互控制\n采集线程 CameraThread",
    fc="#fff4e0", ec="#d97706", bold=False)
box(ax, 0.03, 0.40, 0.27, 0.16, "视频源\n本机摄像头 / 视频文件\n手机IP Webcam流(MJPEG)", fc="#f0f0f0", ec="#666")
box(ax, 0.03, 0.14, 0.27, 0.16, "音频源\nPC麦克风(sounddevice)\n手机麦克风(WAV流)", fc="#f0f0f0", ec="#666")

box(ax, 0.42, 0.62, 0.26, 0.3,
    "后端（FastAPI + Uvicorn）\nWebSocket /ws/process\nHTTP+SSE /qa  /asr\n/static /uploads",
    fc="#e6f7ee", ec="#16a34a")
box(ax, 0.42, 0.40, 0.26, 0.16,
    "检测引擎\nMediaPipe Hands(21关键点)\nYOLOv8(COCO 80类)\ngeometry 指向匹配", fc="#eaf2ff", ec="#2f6fe0")
box(ax, 0.42, 0.14, 0.26, 0.18,
    "数据层\nDatabase(线程安全)\nMySQL: history /\ndetected_objects", fc="#f3e8ff", ec="#8b5cf6")

box(ax, 0.78, 0.44, 0.2, 0.24, "云端多模态大模型\nQwen3.5-omni-plus\n图像问答 / 语音转写\n(OpenAI兼容API)", fc="#ffe4e6", ec="#e11d48")

arrow(ax, (0.165, 0.48), (0.165, 0.72))
arrow(ax, (0.165, 0.22), (0.30, 0.30))
arrow(ax, (0.30, 0.82), (0.42, 0.77), "JPEG帧 / WebSocket")
arrow(ax, (0.30, 0.26), (0.42, 0.22), "WAV /asr")
arrow(ax, (0.55, 0.62), (0.55, 0.56), "帧→结果")
arrow(ax, (0.62, 0.52), (0.78, 0.56), "图像+问题")
arrow(ax, (0.68, 0.24), (0.88, 0.44), "", ls="--")
arrow(ax, (0.55, 0.40), (0.55, 0.32))
ax.text(0.86, 0.64, "SSE流式回答", fontsize=9.5, ha="center", color="#e11d48")
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_arch.png"), dpi=150)
plt.close(fig)
print("fig_arch done")

# ============ 图3.2 系统工作流程图 ============
fig, ax = plt.subplots(figsize=(10.5, 3.6))
ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
steps = ["空闲", "感知中\n(无手)", "检测到手", "指向手势\n成立", "锥域匹配\n物品", "多帧确认\nn/3", "锁定物品\n裁剪截图", "提问\n文字/语音", "ASR转写\n(语音)", "SSE流式\n回答", "截图+问答\n入库", "结果展示"]
xs = [0.02 + i * 0.084 for i in range(12)]
for x, s in zip(xs, steps):
    fc = "#eaf2ff"
    if "确认" in s or "锁定" in s:
        fc = "#fff4e0"
    if "回答" in s or "入库" in s or "展示" in s:
        fc = "#e6f7ee"
    box(ax, x, 0.45, 0.072, 0.26, s, fc=fc, fs=8.5)
for i in range(11):
    ax.annotate("", xy=(xs[i + 1], 0.58), xytext=(xs[i] + 0.072, 0.58),
                arrowprops=dict(arrowstyle="->", color="#555", lw=1.2))
ax.annotate("", xy=(xs[0] + 0.036, 0.75), xytext=(xs[10] + 0.036, 0.75),
            arrowprops=dict(arrowstyle="->", color="#999", lw=1.0,
                            linestyle="--", connectionstyle="arc3,rad=-0.15"))
ax.text(0.5, 0.84, "回答完成/重置 → 回到感知中（持续循环）", fontsize=8.5,
        ha="center", color="#999")
ax.text(0.5, 0.9, "异常降级：无手/指向无匹配/API失败/DB断连 → 状态提示，不中断主链路",
        fontsize=9, ha="center", color="#888")
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig_flow.png"), dpi=150)
plt.close(fig)
print("fig_flow done")

# ============ 图4.x 检测与可视化叠加效果（合成演示帧） ============
sys.path.insert(0, r"D:\py workspace\3B412\frontend")
import numpy as np
import cv2
import overlay

img = np.full((720, 1280, 3), 32, np.uint8)
cv2.rectangle(img, (0, 560), (1280, 720), (48, 54, 66), -1)          # 桌面
cv2.rectangle(img, (620, 400), (980, 560), (70, 60, 130), -1)        # 桌面物体阴影
# 杯子
cv2.rectangle(img, (700, 380), (800, 500), (200, 150, 60), -1)
cv2.ellipse(img, (750, 380), (50, 14), 0, 0, 360, (200, 150, 60), -1)
# 瓶子
cv2.rectangle(img, (900, 300), (960, 500), (90, 180, 90), -1)
cv2.rectangle(img, (915, 250), (945, 300), (90, 180, 90), -1)

# 假手(左下伸入): 21点
import math
pts = []
wrist = (180, 620)
pts.append(wrist)
for i, (dx, dy) in enumerate([(40, -10), (80, -20), (115, -30)]):   # 0-3 拇指近似
    pts.append((wrist[0] + dx, wrist[1] + dy))
base_y = 590
for k in range(1, 5):                                                # 4: 拇指尖占位
    pass
knuckles = [(230, 560), (280, 540), (325, 545), (365, 565)]
for (kx, ky) in knuckles:
    pts.append((kx, ky))
    # 中段略弯除食指
tip_extra = [(430, 300), (360, 470), (400, 480), (420, 500)]        # 食指长, 其余弯
mids = [(300, 420), (315, 500), (355, 505), (390, 520)]
for (mx, my), (tx, ty) in zip(mids, tip_extra):
    pts.append((mx, my))
    pts.append((tx, ty))
pts.append((430, 285))  # 食指指尖 index8
# 顺序修正: mediapipe为 0腕,1-4拇,5-8食,9-12中,13-16无名,17-20小
order_fix = [wrist, (200, 610), (230, 595), (260, 580), (300, 560),
             (240, 545), (280, 480), (350, 380), (430, 285),
             (290, 540), (330, 490), (355, 465), (360, 470),
             (330, 545), (365, 510), (390, 490), (400, 480),
             (370, 565), (400, 535), (415, 515), (420, 505)]
res = {
    "status": "ok", "frame_size": [1280, 720],
    "hand_detected": True, "pointing": True,
    "finger_tip": [430, 285], "finger_mcp": [240, 545],
    "landmarks": [list(p) for p in order_fix],
    "objects": [
        {"class_id": 41, "class_name": "cup", "confidence": 0.93, "bbox": [692, 372, 808, 508]},
        {"class_id": 39, "class_name": "bottle", "confidence": 0.87, "bbox": [905, 248, 962, 505]},
    ],
    "pointed_object": {"class_id": 41, "class_name": "cup", "confidence": 0.93,
                       "bbox": [692, 372, 808, 508], "confirmed": True},
    "confirm_count": 3, "confirm_threshold": 3,
}
out = overlay.draw_overlay(img, res)
cv2.imwrite(os.path.join(FIG, "fig_overlay.png"), out)
print("fig_overlay done")

# ============ 图5.x 软件主界面真实截图 (PrintWindow) ============
def capture_app_window(png_path):
    import ctypes
    import ctypes.wintypes as wt
    from PIL import Image
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    hwnd = user32.FindWindowW(None, "手势指示多模态问答系统")
    if not hwnd:
        found = []
        EnumWindows = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

        @EnumWindows
        def cb(h, lp):
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(h, buf, 256)
            if "手势指示" in buf.value:
                found.append(h)
            return True
        user32.EnumWindows(cb, 0)
        if not found:
            return False
        hwnd = found[0]

    rc = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rc))
    w, h = rc.right - rc.left, rc.bottom - rc.top
    if w < 100 or h < 100:
        return False
    hwnd_dc = user32.GetWindowDC(hwnd)
    mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
    bmp = gdi32.CreateCompatibleBitmap(hwnd_dc, w, h)
    gdi32.SelectObject(mem_dc, bmp)
    user32.PrintWindow(hwnd, mem_dc, 2)   # PW_RENDERFULLCONTENT
    bmi = ctypes.create_string_buffer(40)
    # BITMAPINFOHEADER
    import struct
    ctypes.memmove(bmi, struct.pack("<IiiHHIIiiII", 40, w, -h, 1, 32, 0, 0, 0, 0, 0, 0), 40)
    buf = (ctypes.c_char * (w * h * 4))()
    gdi32.GetDIBits(mem_dc, bmp, 0, h, buf, bmi, 0)
    img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB")
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(hwnd, hwnd_dc)
    img.save(png_path)
    return True

started_proc = None
if not capture_app_window(os.path.join(FIG, "fig_ui.png")):
    # 无现成窗口 -> 启动临时实例截图后关闭
    started_proc = subprocess.Popen(
        [r"D:\py workspace\3B412\.venv\Scripts\python.exe", r"D:\py workspace\3B412\frontend\main.py"],
        cwd=r"D:\py workspace\3B412")
    ok = False
    for _ in range(30):
        time.sleep(1)
        if capture_app_window(os.path.join(FIG, "fig_ui.png")):
            ok = True
            break
    time.sleep(1)
    if started_proc:
        started_proc.terminate()
    print("ui capture (after launch):", ok)
else:
    print("ui capture (existing window)")
print("ALL FIGURES DONE:", sorted(os.listdir(FIG)))
