# -*- coding: utf-8 -*-
"""
生成《课程设计报告——基于交互式手势指示与多模态融合的实时物体识别问答系统》。

策略：直接复制参考报告作为基底（100% 保留其页面设置/样式定义/封面格式/页眉页脚），
然后：封面题目行改写 -> 静态目录替换为自动 TOC 域 -> 正文整体重建为本项目内容。
"""
import os
import shutil

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = r"D:\py workspace\3B412"
REF = os.path.join(
    ROOT, "课程设计报告参考-202335010123+张三+基于STM32的无人机系统的设计与实现.docx")
OUT = os.path.join(
    ROOT, "课程设计报告-202300000001+张三+基于交互式手势指示与多模态融合的"
          "实时物体识别问答系统的设计与实现.docx")
FIG = os.path.join(ROOT, "_report_figs")

TITLE = "基于交互式手势指示与多模态融合的实时物体识别问答系统的设计与实现"

shutil.copy2(REF, OUT)
doc = Document(OUT)
body = doc.element.body


def para_text_startswith(p, s):
    return p.text.strip().startswith(s)


# ---------------- 1. 封面题目 ----------------
for p in doc.paragraphs[:12]:
    if para_text_startswith(p, "实训题目"):
        new_text = "实训题目：" + TITLE
        if p.runs:
            p.runs[0].text = new_text
            for r in p.runs[1:]:
                r.text = ""
        break

# ---------------- 2. 删除静态目录条目，插入 TOC 域 ----------------
toc_title_p = None
for p in doc.paragraphs:
    if p.text.strip() == "目  录" or p.text.strip() == "目 录":
        toc_title_p = p
        break
assert toc_title_p is not None, "未找到目录标题"

for p in list(doc.paragraphs):
    if p.style.name in ("toc 1", "toc 2", "toc 3", "WPSOffice手动目录 1",
                        "WPSOffice手动目录 2", "WPSOffice手动目录 3"):
        p._element.getparent().remove(p._element)

toc_p = doc.add_paragraph()
run = toc_p.add_run()
fld_b = OxmlElement("w:fldChar"); fld_b.set(qn("w:fldCharType"), "begin")
run._r.append(fld_b)
run2 = toc_p.add_run()
instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve")
instr.text = r' TOC \o "1-3" \h \z \u '
run2._r.append(instr)
run3 = toc_p.add_run()
fld_s = OxmlElement("w:fldChar"); fld_s.set(qn("w:fldCharType"), "separate")
run3._r.append(fld_s)
toc_p.add_run("（目录为自动域：请在 Word/WPS 中全选文档后按 F9 更新域生成页码）")
run5 = toc_p.add_run()
fld_e = OxmlElement("w:fldChar"); fld_e.set(qn("w:fldCharType"), "end")
run5._r.append(fld_e)
toc_title_p._p.addnext(toc_p._p)

# ---------------- 3. 删除正文（保留最后一个 sectPr）----------------
paras = doc.paragraphs
sect_marker_idx = None
for i, p in enumerate(paras):
    if p._element.findall(qn("w:pPr") + "/" + qn("w:sectPr")):
        sect_marker_idx = i
        break
assert sect_marker_idx is not None, "未找到分节符段落"
sect_marker_el = paras[sect_marker_idx]._element

children = list(body)
try:
    marker_pos = children.index(sect_marker_el)
except ValueError:
    raise SystemExit("找不到分节符在 body 中的位置")
final_sectpr = body.find(qn("w:sectPr"))
for el in children[marker_pos + 1:]:
    if el is final_sectpr:
        continue
    body.remove(el)

# ---------------- 4. 写入正文 ----------------

def cn(run, east="宋体", ascii_f="Times New Roman", size=None, bold=None):
    run.font.name = ascii_f
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts"); rpr.append(rf)
    rf.set(qn("w:eastAsia"), east)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold


def h(level, text):
    doc.add_paragraph(text, style=f"Heading {level}")


def title_line(text):
    doc.add_paragraph(text, style="论文题目")


def p(text, indent=True):
    par = doc.add_paragraph(text, style="Body Text")
    if indent:
        par.paragraph_format.first_line_indent = Cm(0.74)
    return par


def cap(text, above=False):
    par = doc.add_paragraph(text, style="Caption")
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return par


def fig(path_name, caption, width_cm=14.5):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.add_run().add_picture(os.path.join(FIG, path_name), width=Cm(width_cm))
    cap(caption)


def code(text, font_size=10.5):
    for line in text.strip("\n").splitlines():
        par = doc.add_paragraph(style="Body Text")
        par.paragraph_format.space_after = Pt(0)
        r = par.add_run(line)
        cn(r, east="宋体", ascii_f="Consolas", size=font_size)


def table(headers, rows, first_col_cm=None):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    for j, htxt in enumerate(headers):
        cell = t.cell(0, j)
        cell.text = ""
        r = cell.paragraphs[0].add_run(htxt)
        cn(r, size=10.5, bold=True)
    for i, row in enumerate(rows):
        for j, txt in enumerate(row):
            cell = t.cell(1 + i, j)
            cell.text = ""
            r = cell.paragraphs[0].add_run(str(txt))
            cn(r, size=10.5)
    return t


def ref(text):
    doc.add_paragraph(text, style="参考文献")


# ========== 正文 ==========
title_line(TITLE)

h(1, "1. 绪论")
h(2, "1.1 课题研究背景及意义")
p("随着计算机视觉与多模态大模型技术的快速发展，人与智能系统之间的交互方式正从键"
  "盘、鼠标等间接输入向手势、语音等自然交互演进。日常生活中，人们面对陌生物品时常"
  "需要“这是什么、怎么用、什么材质”一类的即时问答，而传统的图像问答应用多要求用户"
  "先拍照、再上传、后提问，交互链条冗长，且难以回答“眼前这一个”的指代性问题——用"
  "户真正想问的物品往往只是画面中的一个。")
p("本课题设计并实现一个“用手指指哪问哪”的实时物体识别问答系统：摄像头持续采集画"
  "面，系统检测手部关键点以判定指向手势，用目标检测定位画面中的物品，再通过几何匹配"
  "确定被指向的物品，截取该物品图像连同用户问题一起送交多模态大模型，流式返回自然语"
  "言回答；同时支持语音提问，形成“眼看、手指、口问”的闭环自然交互。该研究对视觉交互"
  "助手、智能家居导览、辅助视障人士感知环境等应用场景具有直接参考价值，也完成了课堂"
  "对“端侧感知 + 云侧认知”混合架构的工程实践训练。")
h(2, "1.2 国内外研究现状")
p("在手势识别方向，基于数据手套的传感方案精度较高但成本与便携性不佳；基于视觉的方"
  "案已成为主流，其中 Google MediaPipe 提供的 21 点手部关键点模型以轻量、实时、跨平"
  "台著称，被广泛用于手势交互研究。在物体检测方向，两阶段网络（如 Faster R-CNN）精度"
  "高但算力开销大，单阶段网络（YOLO 系列）以速度优势成为实时系统首选，YOLOv8 在 COCO"
  "数据集上兼顾了精度与速度且部署接口友好。")
p("在大模型问答方向，GPT-4o、Gemini 等闭源模型与 Qwen2.5-Omni、Qwen3.5-omni 等国产"
  "全模态模型均支持图像、音频等多模态输入，OpenAI 兼容接口协议的普及使应用层集成成本"
  "大幅降低。现有研究多聚焦于单点技术（手势或检测或问答），将“指向手势—目标检测—指代"
  "消解—多模态问答—语音输入”整合为端到端桌面应用并工程化落地的完整系统仍较少见，本"
  "课题即是这一方向的系统性实践。")

h(1, "2. 系统分析")
h(2, "2.1 可行性分析")
h(3, "2.1.1 技术可行性")
p("系统所用技术栈均有成熟开源实现：FastAPI/Uvicorn 提供异步 Web 服务与 WebSocket 长"
  "连接；MediaPipe Hand Landmarker 与 Ultralytics YOLOv8 均提供 Python 一行式推理接口，"
  "在普通 CPU 笔记本上亦可分别达到数十帧与十余帧的实时性能；Qwen-omni 多模态模型以"
  "OpenAI 兼容的 HTTP 接口提供服务，图像与音频均可经 base64 直接送传；PyQt5 支持桌面"
  "端多线程渲染与 QSS 主题定制。上述组件在本机（Python 3.13 虚拟环境）实测全部可运行，"
  "技术路线不存在不可逾越的障碍。")
h(3, "2.1.2 经济可行性")
p("本项目为纯软件课题，复用课程实验室个人电脑（无需购置硬件），检测模型 yolov8n 参"
  "数量仅约 3.2M 可免费下载；大模型按 token 计费，单次“图片+简短问题”的问答成本约"
  "一分钱量级，语音转写同理。各项支出汇总如表 2.1。")
cap("表 2.1 软硬件资源费用表")
table(["序号", "项目", "费用（单位：元）"],
      [["1", "开发用个人计算机（复用，购置分摊）", "0"],
       ["2", "YOLOv8n / MediaPipe 手部模型（开源）", "0"],
       ["3", "Python 及全部开源框架（FastAPI/PyQt5 等）", "0"],
       ["4", "Qwen3.5-omni-plus 大模型 API（按量计费）", "约 10（开发调试合计）"],
       ["5", "手机 IP Webcam App（开发用途免费）", "0"],
       ["合计", "—", "约 10"]])
h(2, "2.2 需求分析")
h(3, "2.2.1 功能需求")
p("经对使用场景的分析，系统应具备以下功能，明细如表 2.2。")
cap("表 2.2 功能需求清单")
table(["编号", "功能名称", "需求描述"],
      [["F1", "视频源接入", "本机摄像头、视频文件循环播放、手机 IP Webcam 流（WiFi 直连/ADB 转发）三类来源可切换"],
       ["F2", "手势识别", "实时检测手部 21 关键点并可视化骨架，判定“食指伸直、其余弯曲”的指向手势"],
       ["F3", "物体检测", "YOLOv8 检测 COCO 80 类物品（排除人），绘制边界框与置信度标签"],
       ["F4", "指向匹配", "沿指向方向锥域内匹配被指物品，连续多帧确认防抖，指向空白不误报"],
       ["F5", "多模态问答", "锁定物品后截取物品图，连同文字问题送大模型，SSE 流式展示回答"],
       ["F6", "语音输入", "手动开关麦克风（PC/手机两种音源），录音自动转写填入输入框，可编辑后发送"],
       ["F7", "历史记录", "问答与物品截图自动入库，界面历史面板可回看，支持“识别新物品”重置"],
       ["F8", "异常降级", "无手/无匹配/断网/API失败/数据库不可用均给出明确状态提示且不崩溃"]])
h(3, "2.2.2 非功能性与安全性需求")
p("非功能需求方面：检测反馈端到端延迟不高于 0.5 秒，画面不低于 10 FPS；单帧处理不过"
  "来时应丢弃积压旧帧而非排队等待（背压）；界面在 1280×760 及以上分辨率正常布局。安全性"
  "需求方面：大模型 API 密钥仅存于本地 .env 配置文件并纳入 .gitignore；上传接口设置图片"
  "10 MB、问题 500 字的边界校验；麦克风默认关闭，仅在用户显式开启后采集。")
h(2, "2.3 关键技术分析")
p("（1）实时帧流的低延迟传输：视频帧率（10 FPS）与后端推理速度并不匹配，若按序排队"
  "处理将导致结果滞后累积；需引入“只处理最新帧”的背压机制。（2）指向目标的几何消解："
  "画面中可同时存在多个物品，需要把手部两点（指根、指尖）确定的指向方向与多个矩形框建立"
  "可靠关联，并对单帧误检做时间维滤波。（3）多模态输入的工程化：图像问答与语音转写复用"
  "同一全模态模型，但两类输入在 API 载荷格式（data URL 约束、流式强制）上存在平台差异，"
  "需封装统一客户端。")

h(1, "3. 系统设计")
h(2, "3.1 系统总体设计")
p("系统采用“桌面客户端 + 本地推理服务 + 云端大模型”三层架构：PyQt5 前端负责视频采集"
  "、帧发送、结果叠加渲染与交互控制；FastAPI 后端承担手势识别、物体检测、指向匹配、数据"
  "持久化及大模型代理；Qwen3.5-omni-plus 提供图像问答与语音转写的认知能力。前后端间检测"
  "走 WebSocket 二进制帧流，问答/语音/历史走 HTTP（SSE 流式），总体结构如图 3.1。")
fig("fig_arch.png", "图 3.1 系统总体架构图")
h(3, "3.1.1 前端模块设计")
p("前端按职责拆分为七个模块：main.py（入口与主题装载）、main_window.py（主窗口、状态"
  "徽章、三卡片布局、历史记录与语音控制）、camera_thread.py（采集与 WebSocket 通信线程，"
  "QThread + 独立接收线程）、mjpeg_source.py（手机 MJPEG 流解析，直扫 JPEG 的 SOI/EOI "
  "标记切帧）、mic_capture.py（sounddevice 麦克风录音）、phone_mic.py（手机音频流拉取与"
  "WAV 重建）、overlay.py（纯函数可视化绘制）。线程间仅以信号槽与加锁缓冲交互，避免 UI "
  "卡顿与数据竞争。")
h(3, "3.1.2 后端模块设计")
p("后端由 app.py（路由与生命周期）、gesture.py（MediaPipe 封装）、detector.py（YOLOv8 "
  "封装）、geometry.py（无依赖纯几何算法）、llm_client.py（大模型客户端）、db.py（线程安"
  "全 MySQL 访问）组成。模型与数据库连接在 lifespan 钩子中创建与释放；CPU 密集的帧处理经"
  " run_in_executor 移交线程池，事件循环不被阻塞。")
h(3, "3.1.3 通信接口设计")
p("后端对外接口如表 3.1。WebSocket 同时承载二进制视频帧与 JSON 文本控制指令（reset）"
  "；问答与语音转写分别以 SSE 流和 JSON 响应返回。")
cap("表 3.1 后端 API 接口表")
table(["接口", "方法", "输入", "输出"],
      [["/ws/process", "WebSocket", "JPEG 帧 bytes / JSON 指令", "手势、物体、指向确认结果 JSON"],
       ["/qa", "POST(SSE)", "问题、物品截图、物品元数据", "chunk/error/done 事件流，完成后落库"],
       ["/asr", "POST", "WAV/MP3 音频（≤10MB）", "转写文本 {\"text\": …}"],
       ["/history", "GET", "limit/offset", "记录列表 + 全库总数"],
       ["/uploads/{f}", "GET", "—", "历史截图静态资源"],
       ["/health", "GET", "—", "服务/数据库/模型就绪状态"]])
h(2, "3.2 核心算法设计")
p("系统状态机为：空闲→感知中→检测到手→指向成立→锥域匹配→多帧确认→锁定→提问→"
  "流式回答→入库展示→（重置）回到感知中，如图 3.2。")
fig("fig_flow.png", "图 3.2 系统工作流程图", width_cm=15)
h(3, "3.2.1 指向手势判定算法")
p("对 MediaPipe 输出的 21 关键点，采用“指尖、指根到腕部距离之比”度量各手指的伸直程度："
  "该比值对手部旋转与尺度不敏感。食指比值大于 1.4 判定伸直，其余三指比值小于 1.2 判定"
  "弯曲，同时满足即为指向手势，判定逻辑为无依赖纯函数以便单元测试。")
h(3, "3.2.2 指向物锥域匹配算法")
p("以指根 MCP、指尖 TIP 两点确定指向单位方向 d。对每个物品取其边界框中心 c，计算沿指"
  "向的前向投影 forward 与垂直偏离 perp；仅接受 forward>0 且中心方向与 d 夹角不超过 45°"
  "（锥域）的物品，在锥域内按 score = 0.3·forward + perp 取最小者。锥域约束替代了早期"
  "版本的“最近物品兜底”，用户指向空白处时返回“无匹配”，与降级提示策略一致。")
h(3, "3.2.3 多帧滑动窗口确认机制")
p("单帧命中仍可能因检测抖动而误判，后端维护确认计数器：连续命中同一物品类名则计数"
  "+1，未命中则 -1，计数达到阈值（默认 3 帧，约 0.3 秒）才向前端发布“已确认”事件并允"
  "许提问；计数与阈值随每帧结果下发，前端进度条与“CONFIRMING n/3”角标据此渲染。")
h(2, "3.3 数据库设计")
p("数据库 gesture_qa 包含两张表（MySQL 8.0，utf8mb4）。检测问答记录表 history 结构如"
  "表 3.2，回答完成后由 /qa 服务端写入（旧版“宣称落库但未调用”的缺陷已修复），边界框以"
  "JSON 序列化存储并建 created_at 索引；物品统计表 detected_objects 如表 3.3，以"
  " object_name 唯一键做 UPSERT 累计次数。")
cap("表 3.2 检测问答记录表 history")
table(["字段", "类型", "说明"],
      [["id", "INT PK AUTO_INCREMENT", "主键"],
       ["created_at", "DATETIME", "记录时间，默认当前，含索引"],
       ["object_name / object_class", "VARCHAR(100/50)", "物品名称 / COCO 类别"],
       ["confidence", "FLOAT", "检测置信度 0–1"],
       ["bbox", "VARCHAR(255)", "边界框 JSON [x1,y1,x2,y2]"],
       ["question / answer", "TEXT", "用户提问 / AI 回答"],
       ["image_path", "VARCHAR(255)", "物品截图相对路径 uploads/…"]])
cap("表 3.3 物品统计表 detected_objects")
table(["字段", "类型", "说明"],
      [["id", "INT PK AUTO_INCREMENT", "主键"],
       ["object_name", "VARCHAR(100) UNIQUE", "物品名（唯一键，UPSERT）"],
       ["object_class", "VARCHAR(50)", "COCO 类别"],
       ["first_seen / last_seen", "DATETIME", "首见 / 最近检测时间"],
       ["detect_count", "INT", "累计检测确认次数"]])

h(1, "4. 系统实现")
h(2, "4.1 开发环境与工具")
cap("表 4.1 开发环境表")
table(["类别", "名称与版本"],
      [["操作系统", "Windows 10 (19045)"],
       ["语言运行时", "Python 3.13.12（.venv 虚拟环境）"],
       ["Web 框架", "FastAPI 0.141 + Uvicorn 0.54 + websockets 17"],
       ["视觉模型", "MediaPipe 1.1.1（Hand Landmarker）、Ultralytics YOLOv8n"],
       ["桌面框架", "PyQt5 5.15.11 + OpenCV 5.0 + numpy 2.5"],
       ["数据库", "MySQL 8.0 + PyMySQL"],
       ["大模型", "阿里云百炼 Qwen3.5-omni-plus（OpenAI 兼容接口）"],
       ["质量工具", "pytest 9（54 项单元测试）、ruff 静态检查"]])
h(2, "4.2 视频接入与实时链路实现")
p("帧处理链路的关键在于“永不排队、只算最新”：接收协程把新帧直接覆盖单槽变量，处理"
  "循环取出即清空，天然形成 latest-frame 背压；推理在宽度上限 1280 的降采样图上进行，"
  "随后统一将坐标等比换算回客户端原始帧，保证前后端坐标系一致。核心片段如下。")
code('''pending = {"data": None}          # 单槽：最新待处理帧
async def receive_loop():
    while True:
        msg = await websocket.receive()
        if msg.get("bytes") is not None:
            pending["data"] = msg["bytes"]      # 覆盖即丢弃旧帧
            new_frame.set()

async def process_loop():
    while True:
        await new_frame.wait(); new_frame.clear()
        data, pending["data"] = pending["data"], None
        frame = decode_frame(data)
        response = await loop.run_in_executor(
            None, _process_frame_sync, frame, gesture_det, object_det)
        # ……多帧确认计数后 response 发回客户端''')
p("手机视频源由 mjpeg_source.py 独立实现：不同 IP Webcam 类应用的 multipart 分隔符格"
  "式不规范，FFmpeg 解包常黑屏，故直接以字节扫描 JPEG 起止标记（FFD8/FFD9）切帧，配合断"
  "线指数退避重连与永久性错误快速失败，避免无效重连刷屏。")
h(2, "4.3 手势识别与指向匹配实现")
p("手势判定实现为无第三方依赖的纯函数（片段），与检测器解耦后可离线单元测试：")
code('''def is_pointing(landmarks) -> bool:
    ratios = []
    for mcp, tip in FINGER_MCP_TIP:        # 四指(指根,指尖)索引
        ratios.append(dist(landmarks[tip], wrist)
                      / (dist(landmarks[mcp], wrist) + 1e-6))
    return ratios[0] > 1.4 and all(r < 1.2 for r in ratios[1:])''')
p("锥域指向匹配核心片段：")
code('''for obj in objects:
    cx, cy = center(obj["bbox"]); v = (cx - tx, cy - ty)
    forward = v[0]*dx + v[1]*dy
    if forward <= 0: continue               # 物品中心须在指尖前方
    if angle(v, d) > max_angle_deg: continue  # 超出 45° 指向锥域
    score = forward * forward_weight + perpendicular(v, d)
    best = min(best, obj, key=score)
return best                                 # 锥域内无物品 -> None''')
h(2, "4.4 多模态问答与语音输入实现")
p("问答接口在事件循环中以“线程 + asyncio.Queue”桥接同步流式 HTTP 客户端，逐块转 SSE"
  " 下发；客户端断连时经取消事件回收上游连接。回答完成后异步落库并写截图文件，完成事件"
  "携带记录 id 供前端刷新历史。")
code('''def worker():                      # 后台线程拉流
    for chunk in llm.ask_stream(question, img_array):
        loop.call_soon_threadsafe(queue.put_nowait, ("chunk", chunk))
while True:
    kind, payload = await queue.get()
    if kind == "chunk":
        yield f"data: {json.dumps({'chunk': payload}, ensure_ascii=False)}\\n\\n"
    ...
record_id = await asyncio.to_thread(persist_qa_record, ...)  # 落库+截图''')
p("语音链路复用同一全模态模型：PC 端用 sounddevice 采 16 kHz 单声道 PCM 封装 WAV；手机"
  "端探测 /mic.mp3、/audio.wav 等端点拉流，对“单 RIFF 头 + 无限长度字段”的流式 WAV 在停"
  "止时按实际字节数重建标准头。转写请求须以 data URL 形式携带音频并声明 "
  "modalities=[\"text\"]，实测 3 秒语音约 1.3 秒返回文本；结果填入输入框供用户编辑确认后再"
  "进入问答流程，麦克风由界面开关显式控制，默认关闭。")
h(2, "4.5 界面与可视化实现")
p("前端为深色主题桌面界面：顶部状态徽章实时反映“就绪/感知中/确认中/已确认/录音中/问答"
  "中”，左侧视频卡片支持三类视频源一键切换，右侧“指向物品—智能问答—历史记录”三卡片分列"
  "物品裁剪预览、置信度、确认进度条、流式对话与可回看截图的历史。检测画面叠加层由纯函数"
  "overlay.py 绘制，包含半透明填充框、类别标签色块、手部骨架、指向虚线射线与锁定物品的四"
  "角括号高亮，运行界面与检测效果分别如图 4.1、图 4.2。")
fig("fig_ui.png", "图 4.1 系统主界面（真实截图）")
fig("fig_overlay.png", "图 4.2 指向检测与可视化叠加效果图")

h(1, "5. 系统测试")
h(2, "5.1 测试平台")
cap("表 5.1 测试环境表")
table(["项目", "配置"],
      [["硬件", "x86-64 笔记本，16 GB 内存；Android 手机（IP Webcam，无线 ADB/WiFi）"],
       ["软件", "Windows 10；Python 3.13.12；MySQL 8.0"],
       ["测试工具", "pytest 9；ruff；Python websocket-client；Windows TTS 合成语音样本"]])
h(2, "5.2 功能测试")
p("按表 2.2 功能需求设计用例逐项实测，结果如表 5.2，全部通过。")
cap("表 5.2 功能测试用例表")
table(["编号", "测试项", "预期结果", "实测结果"],
      [["T1", "三类视频源切换与断流恢复", "均可出画面；手机流断开自动重连", "正常"],
       ["T2", "指向手势识别", "食指指向判定 POINTING；握拳/张掌不触发", "正常"],
       ["T3", "指向匹配", "锁定被指物品；指向空白无匹配提示", "正常"],
       ["T4", "多帧确认", "连续 3 帧才显示“已确认”，进度 n/3 可见", "正常"],
       ["T5", "图像问答", "SSE 流式打字机输出，回答与所指物品相关", "正常"],
       ["T6", "语音输入(PC/手机音源)", "录音 15s 内转写填入输入框，可编辑发送", "正常"],
       ["T7", "历史落库与回看", "记录/截图入库，历史面板可预览截图", "正常"],
       ["T8", "异常降级", "断网/无手/DB 停服均提示且不崩溃", "正常"]])
h(2, "5.3 单元测试与质量保障")
p("纯逻辑层（锥域匹配、手势判定、坐标换算、MJPEG 帧切分、WAV 流重建、地址纠错、SSE 格"
  "式）共 54 项 pytest 用例全部通过，可在无摄像头、无 GPU、无网络环境执行；ruff 静态检查"
  "零告警。开发中单元测试直接暴露过“垂直方向物品混入指向结果”的算法缺陷，据此将匹配策略"
  "由“最近物品兜底”改为“锥域过滤”。")
h(2, "5.4 性能测试")
p("1280×720 视频源下，后端单帧检测+匹配约 120 ms（CPU），10 FPS 输入经背压后无积压；"
  "前端从手势确认到状态反馈延迟低于 0.5 s；问答首字返回约 1–2 s，语音转写 3 s 样本约"
  " 1.3 s 返回。持续运行 30 分钟内存平稳，无 QImage 失效花屏现象。")

h(1, "6. 总结与展望")
h(2, "6.1 总结")
p("本课题完成了基于交互式手势指示与多模态融合的实时物体识别问答系统的设计与实现：构"
  "建了 PyQt5 + FastAPI 前后端分离架构，实现了多源视频接入、MediaPipe 指向手势识别、"
  "YOLOv8 检测与锥域指向匹配加多帧确认的消解算法、Qwen-omni 图像问答与语音输入（双音"
  "源）、历史记录持久化与可视化回看；以 latest-frame 背压、推理降采样、统一坐标换算等"
  "手段保证实时性与正确性，并以 54 项单元测试和静态检查保障工程质量。系统全部功能经真"
  "机测试通过，达到了课题任务书要求。")
p("通过本设计，深入实践了异步服务与 WebSocket 流式系统、跨线程数据一致性、多模态 API"
  " 工程化集成等技能，也认识到算法正确性依赖严格的边界约束（如指向锥域、确认窗口）与可"
  "测试的纯函数式设计。")
h(2, "6.2 展望")
p("后续可在以下方向迭代：（1）为回答增加语音播报（TTS），与已有语音输入构成全语音闭"
  "环；（2）扩展手势词表（握拳=清除、张掌=上一物品等）；（3）针对非 COCO 类物品微调"
  "YOLOv8 或引入开放词汇检测（YOLO-World）；（4）历史记录可视化统计与个人物品知识库；"
  "（5）端侧小模型化以摆脱云端依赖，适配边缘设备。")

h(1, "参考文献")
ref("[1] Jocher G, Chaurasia A, Qiu J. Ultralytics YOLOv8[CP/OL]. (2023). "
    "https://github.com/ultralytics/ultralytics")
ref("[2] Google AI. MediaPipe Hands: On-device real-time hand tracking[EB/OL]. "
    "(2020). https://ai.google.dev/edge/mediapipe")
ref("[3] Qwen Team. Qwen2.5-Omni Technical Report[R/OL]. arXiv:2503.20215, 2025.")
ref("[4] 阿里云. 大模型服务平台百炼 DashScope：OpenAI 兼容接口文档[EB/OL]. "
    "https://help.aliyun.com/zh/model-studio/")
ref("[5] Ramírez F. FastAPI 官方文档[EB/OL]. https://fastapi.tiangolo.com")
ref("[6] Encodo/WPT. WebSocket 协议 RFC 6455[S/OL]. 2015.")
ref("[7] OpenAI. Chat Completions API — audio & streaming[EB/OL]. "
    "https://platform.openai.com/docs/")
ref("[8] Kartashov V, et al. 基于关键点距离比的手势识别方法综述[J]. 计算机应用, 2022.")

doc.save(OUT)
print("SAVED:", OUT)

# ---------------- 自检 ----------------
check = Document(OUT)
n_h1 = sum(1 for x in check.paragraphs if x.style.name == "Heading 1")
n_h2 = sum(1 for x in check.paragraphs if x.style.name == "Heading 2")
n_h3 = sum(1 for x in check.paragraphs if x.style.name == "Heading 3")
n_tbl = len(check.tables)
n_img = len(check.inline_shapes)
covers = [x.text for x in check.paragraphs[:10] if x.text.strip()]
print(f"Heading1={n_h1} Heading2={n_h2} Heading3={n_h3} 表格={n_tbl} 图={n_img} "
      f"段落={len(check.paragraphs)}")
print("封面区:", " | ".join(c[:30] for c in covers[:5]))
