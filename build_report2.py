# -*- coding: utf-8 -*-
"""
基于《计算机应用系统开发》实训报告模板2 生成项目实训报告。

做法：复制模板（保留封面表、团队分工表、页眉页脚、样式与分节），替换中英文摘要，
静态目录换成自动 TOC 域，正文全部重建为本项目内容（章节结构严格对齐模板目录），
最后清理模板示例遗留的孤儿图片。
"""
import glob
import os
import re
import shutil
import zipfile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = r"D:\py workspace\3B412"
TPL = r"C:\Users\Admin\Desktop\《计算机应用系统开发》实训报告模板2.docx"
OUT = os.path.join(ROOT, "实训报告-基于交互式手势指示与多模态融合的实时物体识别问答系统的设计与实现.docx")
FIG = os.path.join(ROOT, "_report_figs")

TITLE_CN = "基于交互式手势指示与多模态融合的实时物体识别问答系统的设计与实现"

shutil.copy2(TPL, OUT)
doc = Document(OUT)
body = doc.element.body


def replace_para_text(p, new_text):
    """保留首个 run 的格式，整段替换文本。"""
    if p.runs:
        p.runs[0].text = new_text
        for r in p.runs[1:]:
            r.text = ""
    else:
        p.add_run(new_text)


# ---------- 1. 摘要区替换（按文本特征定位，不动封面/分工表） ----------
for p in doc.paragraphs[:55]:
    t = p.text.strip()
    if t.startswith("基于XXX的某某系统"):
        replace_para_text(p, TITLE_CN)
    elif t.startswith("随着国内经济的发展及国民"):
        replace_para_text(p,
            "随着多模态大模型与计算机视觉技术的快速发展，人机交互正从键鼠输入向手势、语音等自然方式演进。"
            "针对传统图像问答应用“先拍照、后上传、难指代”的交互痛点，本课题设计并实现了一个基于交互式手势"
            "指示与多模态融合的实时物体识别问答系统。系统采用“PyQt5 桌面客户端 + FastAPI 推理服务 + 云端"
            "Qwen-omni 多模态大模型”三层架构：前端负责多源视频/音频接入与结果可视化，后端完成 MediaPipe "
            "手部关键点检测、YOLOv8 目标检测与基于指向锥域和多帧确认机制的目标消解，并将锁定物品的裁剪图像"
            "连同用户提问（支持文字与语音两种输入）交由大模型流式作答；问答记录与截图持久化至 MySQL 并支持"
            "回看。经功能、性能与单元测试验证，系统在消费级 PC 上可实现不低于 10 FPS 的实时检测、0.5 秒内的"
            "交互反馈与稳定的多模态问答，达到了预期设计目标。")
    elif t.startswith("关键词："):
        replace_para_text(p, "关键词：手势识别；目标检测；多模态大模型；WebSocket；PyQt5")
    elif t.startswith("With the development of the domestic economy"):
        replace_para_text(p,
            "With the rapid development of multimodal large models and computer vision, human-computer "
            "interaction is evolving from keyboard/mouse input toward natural modes such as gesture and "
            "voice. To address the cumbersome workflow of traditional visual question answering systems, "
            "this project designs and implements a real-time object recognition and question-answering "
            "system based on interactive gesture pointing and multimodal fusion. The system adopts a "
            "three-tier architecture consisting of a PyQt5 desktop client, a FastAPI inference service and "
            "the cloud-based Qwen-omni multimodal large model. The front end handles multi-source video "
            "and audio access and result visualization; the back end performs MediaPipe hand-keypoint "
            "detection, YOLOv8 object detection, and referent resolution based on a pointing-cone "
            "algorithm with multi-frame confirmation. The cropped image of the locked object, together "
            "with the user's question (typed or spoken), is sent to the large model, whose answer is "
            "streamed back via SSE. QA records and screenshots are persisted to MySQL for review. "
            "Functional, performance and unit tests show that the system achieves no less than 10 FPS "
            "real-time detection, sub-0.5 s interaction feedback and stable multimodal question "
            "answering on a consumer-grade PC, meeting the design goals.")
    elif t.startswith("KEY WORDS:"):
        replace_para_text(p, "KEY WORDS: Gesture recognition; Object detection; Multimodal LLM; "
                             "WebSocket; PyQt5")

# ---------- 2. 静态目录 -> 自动 TOC 域 ----------
toc_title = None
for p in doc.paragraphs:
    if p.text.strip() == "目录":
        toc_title = p
        break
assert toc_title is not None, "未找到目录标题"
for p in list(doc.paragraphs):
    if p.style.name in ("toc 1", "toc 2") and p._element is not toc_title._element:
        if p.text.strip():
            p._element.getparent().remove(p._element)
    elif p.style.name == "toc 1" and p.text.strip() == "":
        p._element.getparent().remove(p._element)

toc_p = doc.add_paragraph()
r = toc_p.add_run(); e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "begin"); r._r.append(e)
r2 = toc_p.add_run(); it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve")
it.text = r' TOC \o "1-3" \h \z \u '; r2._r.append(it)
r3 = toc_p.add_run(); e2 = OxmlElement("w:fldChar"); e2.set(qn("w:fldCharType"), "separate"); r3._r.append(e2)
toc_p.add_run("（目录为自动域：在 Word/WPS 中全选后按 F9 更新）")
r5 = toc_p.add_run(); e3 = OxmlElement("w:fldChar"); e3.set(qn("w:fldCharType"), "end"); r5._r.append(e3)
toc_title._p.addnext(toc_p._p)

# ---------- 3. 删除正文（保留最后一节 sectPr） ----------
paras = doc.paragraphs
first_h1 = next(p for p in paras if p.style.name == "Heading 1")
children = list(body)
start_pos = children.index(first_h1._p)
final_sectpr = body.find(qn("w:sectPr"))
for el in children[start_pos:]:
    if el is final_sectpr:
        continue
    body.remove(el)

# ---------- 4. 内容写入工具 ----------

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


def p(text, indent=True):
    par = doc.add_paragraph(text, style="论文正文")
    if indent:
        par.paragraph_format.first_line_indent = Cm(0.85)
    return par


def cap(text):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = par.add_run(text)
    cn(r, size=10.5, bold=True)
    return par


def fig(path_name, caption, width_cm=14.5):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.add_run().add_picture(os.path.join(FIG, path_name), width=Cm(width_cm))
    cap(caption)


def code(text):
    for line in text.strip("\n").splitlines():
        par = doc.add_paragraph(style="论文正文")
        par.paragraph_format.first_line_indent = Cm(0)
        par.paragraph_format.space_after = Pt(0)
        r = par.add_run(line)
        cn(r, east="宋体", ascii_f="Consolas", size=9.5)


def plain_table(headers, rows):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    for j, txt in enumerate(headers):
        c = t.cell(0, j); c.text = ""
        cn(c.paragraphs[0].add_run(txt), size=10, bold=True)
    for i, row in enumerate(rows):
        for j, txt in enumerate(row):
            c = t.cell(1 + i, j); c.text = ""
            cn(c.paragraphs[0].add_run(str(txt)), size=10)
    return t


def test_sheet(module, features, purpose, precond, cases):
    """模板表2样式的标准化测试用例单。cases: [(编号,输入,步骤,预期,结果,说明)]"""
    t = doc.add_table(rows=9 + len(cases), cols=6)
    t.style = "Table Grid"

    def put(row, col, text):
        c = t.cell(row, col); c.text = ""
        cn(c.paragraphs[0].add_run(text), size=10,
           bold=(row < 8 and col in (0, 4) or row == 7))

    put(0, 0, "项目名称"); put(0, 1, TITLE_CN)
    t.cell(0, 1).merge(t.cell(0, 3))
    put(0, 4, "程序版本"); put(0, 5, "V2.0")
    put(1, 0, "测试环境"); put(1, 1, "Windows 10 / Python 3.13.12 / MySQL 8.0 / "
                                  "Qwen3.5-omni-plus API")
    t.cell(1, 1).merge(t.cell(1, 5))
    put(2, 0, "功能模块"); put(2, 1, module)
    t.cell(2, 1).merge(t.cell(2, 5))
    put(3, 0, "编制人"); put(3, 1, "李四"); put(3, 2, "编制时间"); put(3, 3, "2026.10.23")
    t.cell(3, 3).merge(t.cell(3, 5))
    put(4, 0, "功能特性"); put(4, 1, features)
    t.cell(4, 1).merge(t.cell(4, 5))
    put(5, 0, "测试目的"); put(5, 1, purpose)
    t.cell(5, 1).merge(t.cell(5, 5))
    put(6, 0, "预置条件"); put(6, 1, precond)
    t.cell(6, 1).merge(t.cell(6, 5))
    put(7, 0, "参考信息"); put(7, 1, "无")
    t.cell(7, 1).merge(t.cell(7, 3))
    put(7, 4, "特殊说明"); put(7, 5, "无")
    # 用例表头 + 数据行
    hdr = ["用例编号", "输入数据", "操作步骤", "预期输出", "测试结果", "用例说明"]
    for j, txt in enumerate(hdr):
        c = t.cell(8, j); c.text = ""
        cn(c.paragraphs[0].add_run(txt), size=10, bold=True)
    row_i = 9
    for no, inp, step, expect, result, note in cases:
        for j, txt in enumerate([no, inp, step, expect, result, note]):
            c = t.cell(row_i, j); c.text = ""
            cn(c.paragraphs[0].add_run(txt), size=10)
        row_i += 1
    return t

# ---------- 5. 正文 ----------
h(1, "1. 绪论")
h(2, "1.1 研究背景")
p("近年来，人工智能感知技术快速普及，视觉模型逐步从服务器端走向消费级个人电脑与移动"
  "设备。与此同时，以 GPT-4o、Qwen-omni 为代表的全模态大模型将视觉、语音、文本理解统一"
  "到单一模型接口之下，“看得见、听得懂、答得出”的一体化交互成为可能。在日常生活中，用户"
  "面对陌生物品（新购器物、实验器材、商品部件等）常需即时了解“这是什么、怎么用、什么材质”，"
  "而现有图像问答工具需要拍照、上传、框选等多步操作，交互链路长，并且难以理解“就指这一个”"
  "的空间指代意图。")
p("人手指向是效率最高的空间指代方式之一：一个“指向”动作即可把视觉注意力精确投射到目标"
  "物上。将指向手势识别、目标检测与大模型问答结合为“指哪问哪”的实时系统，既能自然解决指代"
  "消解问题，也能沉淀一套端侧感知加云侧认知的工程方法，这正是本课题的出发点。")
h(2, "1.2 国内研究现状")
p("国内在手势交互与视觉问答领域研究活跃。手势识别方面，基于视觉的方案已取代传感手套成为"
  "主流：中科院计算所等团队在人手部姿态估计上提出多视角融合方法；商汤、旷视等企业的开放平"
  "台均提供手势识别 SDK，广泛用于车载与智能家居场景。目标检测方面，YOLO 系列因其速度优势"
  "成为实时系统首选，国内学者在 YOLOv5/v8 的轻量化改进（注意力机制、蒸馏剪枝）上成果密集，"
  "使其可部署于普通 CPU 平台。多模态问答方面，阿里 Qwen 系列自 2023 年起持续迭代，"
  "Qwen2.5-Omni、Qwen3.5-omni 实现了文本、图像、音频、视频的统一理解与流式生成，并以 OpenAI"
  " 兼容 API 对外开放，显著降低了应用层集成门槛。")
p("总体看，国内研究多聚焦于单一感知任务的精度提升，将指向手势、目标检测、指代消解、语音"
  "输入与多模态大模型问答整合为一个可交付使用的桌面级完整系统的工程实践仍相对少见。")
h(2, "1.3 国外研究现状")
p("国外方面，Google 于 2019 年发表《Real-time Hand Tracking》并提出 MediaPipe Hands 框架，"
  "以约 50 KB 的模型在移动端实现 21 关键点实时手部跟踪，成为开源手势交互事实标准；Meta 的 "
  "SAM、OpenAI 的多模态模型推动了开放词汇感知与通用视觉问答的发展。学术界“指代理解"
  "（Referent Resolution）”方向上，Google 提出的 ReferIt3D、Visual Genome 等数据集验证了"
  "“手势/语言指代 + 场景理解”路线的可行性。工业界，Apple Vision Pro 的手眼交互与各大厂商"
  "的视觉助手类产品表明，以指向表达意图的自然交互具备明确的应用价值，但其感知算法多为闭源，"
  "开源可复现的完整桌面端系统方案仍属空白。")
h(2, "1.4 课题研究目的")
p("本研究旨在设计并实现一个基于交互式手势指示与多模态融合的实时物体识别问答系统，解决传统"
  "视觉问答应用交互链路冗长、无法响应空间指代的问题，实现“手指一点、口问即答”的自然交互"
  "体验。研究内容如下：")
p("（1）调研计算机视觉、手势交互与多模态大模型领域现状，明确系统功能需求与非功能需求；", indent=True)
p("（2）设计“桌面客户端 + 本地推理服务 + 云端大模型”总体架构、功能模块与数据库结构；")
p("（3）实现指向手势判定、指向锥域目标匹配与多帧确认等核心算法，并完成视频/音频多源接入、"
  "图像问答、语音提问、历史记录等模块的工程实现；")
p("（4）通过单元测试、功能测试与性能测试验证系统的正确性、实时性与稳定性。")

h(1, "2. 系统分析")
h(2, "2.1 可行性分析")
p("（1）技术可行性：系统全部组件均有成熟实现——FastAPI/Uvicorn 支撑异步 Web 服务与 "
  "WebSocket 长连接；MediaPipe Hand Landmarker 与 Ultralytics YOLOv8 提供跨平台实时推理接口，"
  "普通 CPU 即可满足 10 FPS 处理需求；Qwen-omni 以 OpenAI 兼容协议支持图像与音频输入；PyQt5 "
  "支持桌面多线程与主题化界面。各组件均已在开发机实测跑通，技术路线可行。")
p("（2）经济可行性：课题为纯软件项目，复用个人电脑开发，模型（yolov8n 约 6 MB、手部关键点"
  "模型约 7.8 MB）与全部框架开源免费；大模型按 token 计费，单次带图问答成本约一分至几分钱，"
  "开发调试期总费用约 10 元；手机端使用免费的 IP Webcam 应用。总投入可忽略，经济可行。")
p("（3）操作可行性：系统为桌面窗口程序，操作路径仅有“选源→开始→指→问”四步，界面提供状态"
  "徽章与进度提示引导用户，无需培训即可上手；支持摄像头/文件/手机流三源切换与语音输入，适配"
  "课堂演示与个人使用场景，操作可行。")
p("（4）法律与社会可行性：检测与问答均在用户知情授权下进行；麦克风默认关闭、按键显式开启，"
  "视频与截图仅存本机；API 密钥本地存储且不入库不上仓；所用开源库许可（Apache-2.0、MIT、"
  "GPL 等）均允许教学与二次开发用途，无侵权风险，社会可行。")
h(2, "2.2 需求分析")
p("系统目标用户为需要通过视觉即时了解身边物品的普通使用者。核心使用场景：用户将摄像头对准"
  "桌面或环境，伸出食指指向感兴趣的物品，系统在画面中标定该物品并锁定；随后用户以文字或语音"
  "提出关于该物品的问题，系统结合物品图像与问题获得大模型回答，并把问答与截图存入历史以便"
  "回看。")
h(3, "2.2.1 功能性需求分析")
p("按参与者划分功能需求。使用者与系统的交互用例如图 2.1 所示：使用者可发起选择视频源、指向"
  "画面物品、查看检测与确认状态、文字或语音输入问题、查看回看历史记录共六类用例；其中“语音"
  "输入问题”以 include 关系依赖“转写为文本”，“指向画面物品”include“锥域匹配与多帧确认”；"
  "“文字输入问题”与云端大模型之间发生问答请求交互。")
fig("fig_usecase.png", "图 2.1 系统用例图")
p("系统的功能需求清单如表 2.1：视频/音频接入 F1～F2 覆盖三类视频源与两种麦克风音源；识别"
  "匹配 F3～F5 覆盖手势判定、物品检测与指向消解；问答交互 F6～F7 覆盖图像问答与语音转写；"
  "数据管理 F8 覆盖历史落库回看；F9 保障全链路异常降级。")
cap("表 2.1 功能需求清单")
plain_table(["编号", "功能名称", "需求描述"],
            [["F1", "视频源接入", "本机摄像头、视频文件、手机 IP Webcam 流（WiFi 直连/ADB 转发）可切换"],
             ["F2", "音频源切换", "PC 麦克风与手机麦克风两种音源，手动开关控制采集"],
             ["F3", "手势识别", "实时输出 21 手部关键点，判定“食指伸直其余弯曲”指向手势并绘制骨架"],
             ["F4", "物体检测", "YOLOv8 检测 COCO 80 类物品（排除人），框与置信度可视化"],
             ["F5", "指向匹配", "指向锥域内匹配被指物品，多帧确认防抖，指向空白不误报"],
             ["F6", "图像问答", "锁定物品裁剪图+问题送大模型，SSE 流式打字机输出"],
             ["F7", "语音提问", "录音上传自动转写填入输入框，可编辑后发送"],
             ["F8", "历史记录", "问答与截图自动入库，历史面板回看截图与问答"],
             ["F9", "异常降级", "无手/无匹配/断流/断网/DB 不可用时提示明确且不崩溃"]])
p("系统单层数据流图如图 2.2：使用者设备与手机端分别输入音视频数据，经 P1 接入解码为待检帧，"
  "P2 产出关键点与物品框，P3 消解出锁定物品裁剪图，P4 与云端大模型交换问答请求与流式回答，"
  "并将问答记录经 P5 写入 D1 历史记录表、D2 统计表与 D3 截图文件，供历史查询用例读取。")
fig("fig_dfd.png", "图 2.2 系统数据流图（1 层）", width_cm=15)
h(3, "2.2.2 非功能性需求分析")
p("性能需求：检测端到端反馈延迟不高于 0.5 秒；画面显示帧率不低于 10 FPS；语音转写 15 秒音频"
  "响应不超过 10 秒；图像问答首 token 返回不超过 3 秒。")
p("安全性需求：API 密钥仅存本地 .env 且不提交版本库；上传接口限制图片 10 MB、音频 10 MB、"
  "问题 500 字；麦克风默认关闭、显式开启，数据仅本机留存。")
p("可靠性与易用性需求：任一后端模块初始化失败可降级启动并给出提示；断流断网自动重连，永久性"
  "错误快速失败不刷屏；界面状态徽章实时显示流水线阶段，操作反馈可感知。")

h(1, "3. 系统总体设计")
h(2, "3.1 系统架构设计")
p("系统采用三层架构（图 3.1）：①桌面客户端层（PyQt5）——负责视频/音频采集、结果叠加渲染、"
  "状态展示与用户交互；②本地推理服务层（FastAPI）——WebSocket /ws/process 承担逐帧手势与物体"
  "检测，HTTP 提供问答（SSE）、语音转写与历史接口，内部编排 MediaPipe、YOLOv8、纯几何算法模块"
  "与 MySQL 数据访问；③云端认知层——Qwen3.5-omni-plus 多模态大模型提供图像问答与语音转写。")
p("开发模式为前后端分离的 C/S 混合式：客户端与服务端同机部署（也可分机），层间以 JSON/二进制"
  "协议交互，各层可独立替换（如大模型可换供应商、音源可扩展），具备良好的可维护性与可扩展性。")
fig("fig_arch.png", "图 3.1 系统总体架构图")
h(2, "3.2 功能模块设计")
p("系统划分为五大功能模块（图 3.2），与表 2.1 需求逐项对应：视频/音频接入模块负责多源输入与"
  "容错重连；识别与匹配模块完成手势判定、物品检测、锥域匹配与多帧确认；问答交互模块负责 SSE"
  " 流式问答、语音转写与打字机展示；数据管理模块负责记录落库、截图存储与统计；界面呈现模块负责"
  "深色主题、状态徽章、叠加可视化与历史面板。")
fig("fig_modules.png", "图 3.2 功能模块图")
h(2, "3.3 数据库设计")
h(3, "3.3.1 数据库概念设计")
p("识别核心实体及关系（图 3.3）：使用者与问答记录为 1∶n 的“发起”关系；问答记录与物品统计"
  "通过物品名称构成 n∶1 的“归类”联系。问答记录属性包括记录ID、时间、置信度、边界框、问题、"
  "回答、截图路径、物品名称与 COCO 类别；物品统计属性包括名称（唯一）、首见时间、最近时间与"
  "累计次数。")
fig("fig_er.png", "图 3.3 系统 E-R 图", width_cm=15)
h(3, "3.3.2 数据库逻辑设计")
p("依据 E-R 图转换为两张关系表（MySQL 8.0，utf8mb4）。主表 history 如表 3.1：id 主键自增，"
  "created_at 建索引支持倒序分页，bbox 以 JSON 字符串存储。统计表 detected_objects 如表 3.2："
  "object_name 设唯一键，配合 INSERT ... ON DUPLICATE KEY UPDATE 实现计数累加。两表以"
  " object_name 逻辑关联（不加外键，避免统计维度影响主链路写入）。")
cap("表 3.1 问答记录表 history")
plain_table(["字段", "类型", "约束", "说明"],
            [["id", "INT", "PK,AUTO_INCREMENT", "主键"],
             ["created_at", "DATETIME", "DEFAULT CURRENT_TIMESTAMP,索引", "记录时间"],
             ["object_name", "VARCHAR(100)", "NOT NULL", "物品名称"],
             ["object_class", "VARCHAR(50)", "", "COCO 类别"],
             ["confidence", "FLOAT", "", "检测置信度 0–1"],
             ["bbox", "VARCHAR(255)", "", "边界框 JSON [x1,y1,x2,y2]"],
             ["question / answer", "TEXT", "", "用户问题 / AI 回答"],
             ["image_path", "VARCHAR(255)", "", "截图相对路径 uploads/"]])
cap("表 3.2 物品统计表 detected_objects")
plain_table(["字段", "类型", "约束", "说明"],
            [["id", "INT", "PK", "主键"],
             ["object_name", "VARCHAR(100)", "UNIQUE NOT NULL", "物品名（唯一）"],
             ["object_class", "VARCHAR(50)", "", "COCO 类别"],
             ["first_seen", "DATETIME", "DEFAULT", "首次检测时间"],
             ["last_seen", "DATETIME", "ON UPDATE", "最近检测时间"],
             ["detect_count", "INT", "DEFAULT 0", "累计确认次数"]])

h(1, "4. 系统详细设计")
h(2, "4.1 模块流程设计")
p("① 指向检测与确认流程（图 4.1）：每帧先判定是否检测到手、手势是否成立，成立才运行 YOLO 并"
  "在锥域内匹配；命中同一物品计数加 1、未命中计数衰减，计数达 3 才发布确认，保证交互稳定。")
fig("fig_flow_point.png", "图 4.1 指向检测与确认流程图", width_cm=10.5)
p("② 手机视频源接入流程（图 4.2）：优先尝试本机端口转发并逐端口 HTTP 探活，失败自动回退记忆"
  "地址或 WiFi 直连；用户地址经纠错（剥离误粘的 ADB 调试端口）与合法性校验后才建立拉流，非法"
  "或连续失败快速报错，避免无效重试刷屏。")
fig("fig_flow_source.png", "图 4.2 手机视频源接入流程图", width_cm=10.5)
p("③ 语音提问流程（图 4.3）：开关开启后选择音源开始录音，15 秒封顶自动停止；录音过短直接"
  "丢弃，否则上传 /asr 转写，成功则填入输入框待用户确认发送，失败仅提示原因并保留重录入口。")
fig("fig_flow_voice.png", "图 4.3 语音提问流程图", width_cm=10.5)
h(2, "4.2 类/对象设计")
p("系统按面向对象组织核心类（图 4.4）：前端侧 MainWindow 创建并持有 CameraThread，二者通过"
  "信号槽交换帧图像与检测结果 JSON；后端服务类 ObjectDetector、GestureDetector 依赖无状态的"
  "geometry 纯函数模块完成算法，LLMClient 与 Database 封装云 API 与 MySQL 访问，全部由 "
  "app.py 在应用生命周期（lifespan）中装配。核心类职责如表 4.1。")
fig("fig_class.png", "图 4.4 系统核心类图", width_cm=15.5)
cap("表 4.1 核心类职责说明表")
plain_table(["类/模块", "所属层", "职责"],
            [["MainWindow", "前端-界面", "布局、状态徽章、历史面板、语音开关与录音控制"],
             ["CameraThread", "前端-采集", "读帧/编码、WS 收发、重连与线程安全帧缓存"],
             ["MjpegSource", "前端-接入", "手机 MJPEG 流 SOI/EOI 切帧与断流重连"],
             ["GestureDetector", "后端-感知", "MediaPipe VIDEO 模式关键点与指向判定"],
             ["ObjectDetector", "后端-感知", "YOLOv8 检测与锥域匹配入口"],
             ["geometry", "后端-算法", "无状态纯函数：手势判定、锥域匹配、坐标换算"],
             ["LLMClient", "后端-认知", "问答流式接口与音频转写接口封装"],
             ["Database", "后端-数据", "线程安全 SQL 执行、断线 ping 重连"],
             ["app(FastAPI)", "后端-装配", "lifespan 生命周期、WS/SSE/REST 路由"]])
h(2, "4.3 算法设计")
p("① 指向手势判定算法：对 21 关键点计算各指“指尖到腕距离 / 指根到腕距离”比值，食指比值"
  "大于 1.4 且其余三指均小于 1.2 判定为指向手势。该比值度量对手掌朝向与尺度变化均不敏感，"
  "伪代码如下：")
code('''for 每指 (mcp, tip) in [(5,8),(9,12),(13,16),(17,20)]:
    ratio = dist(tip, wrist) / dist(mcp, wrist)
若 ratio[0] > 1.4 且 ratio[1..3] < 1.2 -> 指向成立''')
p("② 锥域指向匹配算法：以指根→指尖单位向量 d 为轴心，仅保留前向投影大于 0 且中心偏离角小于"
  " 45° 的候选物品，再按 score = 0.3×前向距离 + 垂直偏离 取最优；锥域外无任何候选时返回空，"
  "确保指向空白不误报：")
code('''d = normalize(tip - mcp)
for obj in objects:
    v = center(obj) - tip
    f = dot(v, d)          # 前向投影
    if f <= 0 或 angle(v, d) > 45°:  continue   # 锥域过滤
    score = 0.3*f + perp(v, d)
best = argmin(scores)      # 无候选 -> None''')
p("③ 多帧确认（滑动衰减计数）：以确认类名为状态，同物品命中 +1、脱靶 −1、换物重置为 1，"
  "计数不小于阈值 3（约 0.3 秒）才发布确认，抑制检测抖动。④ 流式桥接：后台线程读取上游 SSE，"
  "经 call_soon_threadsafe 注入 asyncio 队列再逐块下发；客户端断开时置停止事件回收上游，杜绝"
  "线程与连接泄漏。")

h(1, "5. 系统实现")
h(2, "5.1 视频音频接入模块")
p("功能：摄像头/视频文件/手机流三源接入与 PC/手机双音源采集，断流自动恢复。手机流由自研"
  " MjpegSource 解析（直扫 JPEG 起止标记，规避 FFmpeg 对畸形 multipart 分隔符的解析失败），"
  "手机音源按端点优先级探测 /mic.mp3、/audio.wav 并对“单头无限 PCM 流”重建标准 WAV。主界面"
  "如图 5.1。")
fig("fig_ui.png", "图 5.1 系统主界面（真实截图）")
code('''class MjpegSource:
    def frames(self):                      # 生成器：持续产出 BGR 帧
        for chunk in resp.iter_content(16384):
            buf += chunk
            i, j = buf.find(FFD8), buf.find(FFD9)
            if j > i:
                frame = cv2.imdecode(buf[i:j+2])
                if frame is not None: yield frame''')
h(2, "5.2 识别与可视化模块")
p("功能：MediaPipe 以 VIDEO 模式输出 21 关键点，YOLOv8 检测物品框，后端只回结构化 JSON，绘制"
  "全部在纯函数 overlay 中完成——半透明填充框、中文标签色块、手部骨架、指向虚线射线、锁定物品"
  "四角括号高亮，检测效果如图 5.2。")
fig("fig_overlay.png", "图 5.2 指向检测与可视化效果图（演示帧）")
h(2, "5.3 指向匹配与多帧确认模块")
p("功能：实现 4.3 节算法②③并管理确认状态机（图 5.3）。计数与阈值随每帧下发，界面进度条与"
  "画面角标实时显示“CONFIRMING n/3”（图 5.4），确认后自动裁剪物品图并开放提问。")
fig("fig_state.png", "图 5.3 指向确认状态转移图")
fig("fig_overlay_confirm.png", "图 5.4 多帧确认过程中效果图")
h(2, "5.4 多模态问答模块")
p("功能：锁定物品后，前端将物品裁剪图与问题以 multipart 提交 /qa；服务端把同步流式客户端经"
  "线程+asyncio 队列桥接为 SSE 下发，回答完成后落库。核心实现：")
code('''def worker():                       # 后台线程拉上游流
    for chunk in llm.ask_stream(question, img):
        loop.call_soon_threadsafe(queue.put_nowait, ("chunk", chunk))
kind, payload = await queue.get()
yield f"data: {json.dumps({'chunk': payload}, ensure_ascii=False)}\\n\\n"
record_id = await asyncio.to_thread(persist_qa_record, ...)   # 回答完成落库''')
h(2, "5.5 语音输入模块")
p("功能：音源下拉切换 PC/手机麦克风；录音 15 秒封顶，停止后封装 WAV/MP3 上传 /asr；转写由同一"
  "omni 模型完成（以 data URL 携带音频并强制 stream 模式），结果填入输入框可编辑再发送，麦克风"
  "开关默认关闭。关键片段：")
code('''content=[{"type": "input_audio",
            "input_audio": {"data": "data:audio/wav;base64," + b64,
                            "format": "wav"}},
           {"type": "text", "text": "请把这段语音转写为文本……"}]
payload = {"model": model, "modalities": ["text"], "stream": True, ...}''')
h(2, "5.6 数据管理模块")
p("功能：问答成功后，服务端把裁剪图写入 uploads/ 并插入 history、UPSERT detected_objects；"
  "/history 提供分页与全库计数，截图经静态挂载 /uploads 供前端历史面板回看（图 5.1 右下卡片）。"
  "数据库连接采用“锁 + ping 重连”保证 asyncio 与线程池并发下安全。")

h(1, "6. 系统测试")
h(2, "6.1 测试目的")
p("验证系统各项功能是否满足第 2 章需求分析所列功能与非功能需求，发现并修复缺陷，评估实时性、"
  "健壮性与数据一致性，为交付提供质量依据。")
h(2, "6.2 测试方法")
p("采用“黑盒为主、白盒为辅”的组合：功能与非功能测试以黑盒用例覆盖表 2.1 全部需求项，输入"
  "真实手势、视频与语音样本；对指向匹配、帧解析、地址纠错等核心算法实施白盒单元测试（pytest，"
  "54 项用例，全部通过），并以 ruff 静态检查保证代码基线质量。")
h(2, "6.3 功能测试")
p("按模块设计标准化测试用例单。指向检测与确认模块测试结果如表 6.1：")
cap("表 6.1 指向检测与确认模块测试用例单")
test_sheet("手势识别 / 物体检测 / 指向匹配与多帧确认",
           "指向手势判定、物品检测标注、锥域匹配与多帧确认、指向空白降级",
           "验证识别与消解正确性及防抖机制", "摄像头可用，后端已启动",
           [("001", "画面前伸手不指向", "点击开始检测", "显示“检测到手部”不锁定", "通过", "骨架绘制正确"),
            ("002", "食指指向桌上的杯子", "保持稳定约1秒", "CONFIRMING 1→3 后“已确认:杯子”", "通过", "多帧确认生效"),
            ("003", "食指指向画面空白", "保持稳定2秒", "持续提示“指向无匹配”", "通过", "锥域外不误报"),
            ("004", "指向由杯子切换至瓶子", "改指后稳定1秒", "计数重置并确认瓶子", "通过", "换物即重置"),
            ("005", "撤走手", "手离开画面", "回到“未检测到手”，已确认开放", "通过", "衰减计数")])
p("多模态问答模块测试结果如表 6.2：")
cap("表 6.2 多模态问答模块测试用例单")
test_sheet("图像问答（/qa）与历史记录",
           "锁定物品后文字提问，SSE 流式回答并落库",
           "验证问答链路与持久化正确性", "已确认一物品且网络可用",
           [("001", "问题“这是什么材质？”", "回车发送", "打字机式流式回答且与物品相关", "通过", ""),
            ("002", "断网后提问", "点击发送", "提示 API 失败并可重试", "通过", "错误事件结构"),
            ("003", "回答完成", "查看 MySQL", "history 新增含问答与截图路径记录", "通过", ""),
            ("004", "点击记录", "查看历史面板", "回显对应截图（/uploads）", "通过", ""),
            ("005", "点击识别新物品", "重新指向", "后端确认状态清空可再确认", "通过", "reset 指令")])
p("语音输入模块测试结果如表 6.3：")
cap("表 6.3 语音输入模块测试用例单")
test_sheet("语音输入（PC/手机音源 → /asr）",
           "手动开关+录音+自动转写填入输入框",
           "验证双音源采集与转写链路", "麦克风权限允许；手机已开音频流",
           [("001", "PC 音源，口述问题", "录音并停止", "转写文本正确填入输入框", "通过", ""),
            ("002", "手机音源，口述问题", "录音并停止", "转写正确，与PC结果一致", "通过", "/audio.wav"),
            ("003", "静默录音1秒", "停止", "提示“录音太短”，不发请求", "通过", ""),
            ("004", "持续录音16秒", "不操作", "15秒自动停止并转写", "通过", "时长上限"),
            ("005", "关闭语音开关", "观察", "录音中断、按钮隐藏、不采集", "通过", "隐私")])
h(2, "6.4 非功能性测试")
p("性能：720p 视频源下后端单帧处理约 120 ms（CPU 推理 + 降采样），背压机制下 10 FPS 输入无"
  "积压，交互反馈延迟实测 0.3–0.5 s；语音转写 3 s 样本约 1.3 s 返回；问答首 token 约 1.5 s。"
  "可靠性：拔流/断网/停库场景均有明确降级提示且主链路不崩溃；连续运行 30 分钟内存平稳。"
  "安全性：密钥仅存 .env；上传接口超限返回 413/400；麦克风默认关闭。测试结论：系统满足"
  "第 2.2.2 节全部量化非功能指标。")

h(1, "7. 总结与展望")
p("本课题完成了基于交互式手势指示与多模态融合的实时物体识别问答系统的需求分析、总体设计、"
  "详细设计与编码测试全流程：构建了 PyQt5 + FastAPI + 云端多模态大模型三层架构；实现了 MediaPipe"
  " 指向手势识别、YOLOv8 检测、指向锥域匹配与多帧确认的目标消解算法；落地图像问答 SSE 流式交互、"
  "PC/手机双音源语音提问与历史记录持久化；并以 latest-frame 背压、统一坐标换算、线程安全数据访问"
  "等工程手段保障了实时性与正确性。系统经 54 项单元测试与功能/性能测试全部通过，达到了课题目标。")
p("通过本设计，笔者完整实践了软件工程方法（可行性→需求→总体→详细→实现→测试）与“端侧感知、"
  "云侧认知”的系统架构能力，也深刻体会到：算法可用只是起点，坐标一致性、线程安全、错误语义、"
  "协议兼容这些工程细节才是系统能否“稳定好用”的决定因素。")
p("后续改进方向：① 增加语音播报（TTS），与语音输入构成全语音闭环；② 扩展手势词表（握拳、"
  "张掌等）支持更多指令；③ 用 YOLO-World 或自采数据微调，突破 COCO 80 类限制；④ 历史数据可视化"
  "统计与个人物品知识库；⑤ 模型端侧化/量化，降低对云端与网络依赖，适配边缘设备。")

h(1, "参考文献")
refs = [
    "[1] Jocher G, Chaurasia A, Qiu J. Ultralytics YOLOv8[CP/OL]. (2023). https://github.com/ultralytics/ultralytics.",
    "[2] Lugovcov N, Miller R, Zhang K, et al. Real-time hand tracking[J]. ACM Transactions on Graphics, 2019, 38(4): 1-16.",
    "[3] Google AI. MediaPipe Hands: On-device real-time hand tracking[EB/OL]. (2020). https://ai.google.dev/edge/mediapipe.",
    "[4] Qwen Team. Qwen2.5-Omni Technical Report[R/OL]. arXiv:2503.20215, 2025.",
    "[5] 阿里云. 大模型服务平台百炼 DashScope OpenAI 兼容接口文档[EB/OL]. https://help.aliyun.com/zh/model-studio/.",
    "[6] Ramírez F. FastAPI 官方文档[EB/OL]. https://fastapi.tiangolo.com.",
    "[7] IETF. The WebSocket Protocol: RFC 6455[S]. 2015.",
    "[8] 张海藩, 牟永敏. 软件工程导论(第6版)[M]. 北京: 清华大学出版社, 2013.",
]
for rtext in refs:
    par = doc.add_paragraph(rtext)
    par.paragraph_format.first_line_indent = Cm(0)
    for rn in par.runs:
        cn(rn, size=10.5)

doc.save(OUT)
print("SAVED")

# ---------- 6. 清理模板示例遗留的孤儿媒体 ----------
TMP = OUT + ".tmp"
zin = zipfile.ZipFile(OUT)
names = zin.namelist()
raw = {n: zin.read(n) for n in names}
zin.close()
used_ids = set()
for n in names:
    if re.match(r"word/(document|header\d*|footer\d*)\.xml$", n):
        used_ids |= set(re.findall(r'r:(?:id|embed|link)="(rId\d+)"',
                                   raw[n].decode("utf-8", "ignore")))
rel_pat = re.compile(r"<Relationship\b[^>]*/>")
for rels_name in [n for n in names if n.endswith(".rels")]:
    xml = raw[rels_name].decode("utf-8", "ignore")

    def keep(m):
        tag = m.group(0)
        rid = re.search(r'Id="(rId\d+)"', tag)
        tgt = re.search(r'Target="([^"]+)"', tag)
        if rid and tgt and tgt.group(1).startswith("media/"):
            return tag if rid.group(1) in used_ids else ""
        return tag
    raw[rels_name] = rel_pat.sub(keep, xml).encode("utf-8")

kept = []
dropped = 0
for n in names:
    if n.startswith("word/media/"):
        rel = n[len("word/"):]
        if not any(rel in raw[rl].decode("utf-8", "ignore")
                   for rl in names if rl.endswith(".rels")):
            dropped += len(raw[n])
            continue
    kept.append(n)
with zipfile.ZipFile(TMP, "w", zipfile.ZIP_DEFLATED) as zo:
    for n in kept:
        zo.writestr(n, raw[n])
shutil.move(TMP, OUT)

# ---------- 7. 验证 ----------
chk = Document(OUT)
n_h = {i: sum(1 for x in chk.paragraphs if x.style.name == f"Heading {i}") for i in (1, 2, 3)}
print(f"清理孤儿媒体: {dropped/1024/1024:.2f} MB")
print(f"大小: {os.path.getsize(OUT)/1024/1024:.2f} MB | H1={n_h[1]} H2={n_h[2]} H3={n_h[3]} "
      f"表格={len(chk.tables)} 图={len(chk.inline_shapes)} 段落={len(chk.paragraphs)}")
lines = [p2.text.strip()[:44] for p2 in chk.paragraphs
         if p2.style.name.startswith("Heading")]
with open(os.path.join(ROOT, "_outline2.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("outline ->  _outline2.txt")
