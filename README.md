# 基于交互式手势指示与多模态融合的实时物体识别问答系统

## 项目简介

本系统通过摄像头实时采集视频流，利用 MediaPipe 进行手部关键点检测识别指向手势，结合 YOLOv8 进行物体检测与分类，并通过阿里云多模态大模型（Qwen3.5-omni-plus）实现智能问答。用户可以用手指指向画面中的物体，系统自动识别该物体并回答相关问题。

### 功能特性

- **视频采集/上传/预览**：支持调用电脑摄像头或上传视频文件（MP4/AVI/MOV/MKV/WMV）
- **手势识别**：基于 MediaPipe Hands 实时检测手部 21 个关键点，识别指向手势并可视化标注（VIDEO 跟踪模式 + 完整骨架连线）
- **物体检测**：基于 YOLOv8（COCO 80 类）实时检测物体，绘制边界框与标签，置信度阈值可调
- **指向匹配**：指向锥域过滤 + 综合评分匹配被指向的物品；指向空白处不会误报最近物体
- **智能问答**：接入阿里云 Qwen3.5-omni-plus 多模态大模型，支持对识别物品的对话问答（SSE 流式输出）
- **语音输入提问**：手动开关麦克风后，点击录音说话，自动转写为文字填入输入框，可编辑后回车发送（复用 omni 模型的音频理解能力，无需额外 ASR 服务）；音源可选**电脑麦克风**或**手机麦克风**（IP Webcam 音频流，与画面同一服务）
- **历史记录**：问答与物品截图自动存入 MySQL，前端内置历史面板可回看截图与问答内容
- **实时性能**：latest-frame 背压（处理不过来的旧帧自动丢弃）+ 推理降采样，结果反馈不堆积
- **异常处理**：未检测到手部、指向但无物体匹配、API 超时/失败、数据库断开等均有降级提示

### 技术架构

```
──────────────────┐         WebSocket / HTTP         ┌──────────────────┐
│                  │  ◄─────────────────────────────► │                  │
│   前端 (PyQt5)    │   帧数据 / 检测结果 / 问答请求     │   后端 (FastAPI)  │
│                  │                                  │                  │
│  - 摄像头采集     │                                  │  - 手势识别       │
│  - 视频预览      │                                  │    (MediaPipe)    │
│  - 检测可视化    │                                  │  - 物体检测       │
│  - 问答交互      │                                  │    (YOLOv8)       │
│                  │                                  │  - 多模态LLM      │
│                  │                                  │  - 数据库存储     │
└──────────────────┘                                  └──────────────────┘
```

### 状态流转

```
空闲中 → 感知中 → 指向就绪 → 问答触发中 → 关联匹配中 → 问答生成中 → 结果展示中
  ↑                                                          │
  └──────────────────────────────────────────────────────────┘
```

---

## 环境要求

- Python 3.10 ~ 3.13（本仓库 `.venv` 为 3.13.12，已实测通过；勿与旧文档中的 3.9 混用）
- CUDA 11.8+（可选，GPU 加速 YOLOv8 推理；无 GPU 时 CPU 推理即可运行）
- MySQL 5.7+ 或 8.0+
- Windows 10/11

---

## 部署步骤

### 1. 获取项目

```bash
git clone https://github.com/3464586416/multimodal-gesture-qa.git
cd multimodal-gesture-qa
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv .venv
.venv\Scripts\activate
```

> 也可以直接双击运行 `install_packages.bat`，它会自动完成本节到第 4 步的全部工作。
> 注意：仓库中遗留的 `venv/` 目录基于另一台机器的 Python 创建，已失效，可删除重建。

### 3. 安装后端依赖

```bash
pip install -r backend\requirements.txt
```

> `websockets` 必须随依赖一起安装：它是 uvicorn 提供 WebSocket 协议支持的关键包，
> 缺失时 `/ws/process` 握手会返回 404。
> 如果遇到 `torch` 安装问题，可先单独安装 GPU 版：
> ```bash
> pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
> ```

### 4. 安装前端依赖

```bash
pip install -r frontend\requirements.txt
```

### 5. 初始化数据库

在 **Navicat Premium 17** 中连接到本地 MySQL（用户名 `root`，密码为你自己的本地密码），然后：

1. 打开项目根目录下的 `schema.sql` 文件
2. 在 Navicat 中点击「运行」执行全部 SQL

或者在 MySQL 命令行中执行：

```bash
mysql -u root -p < schema.sql
```

### 6. 配置环境变量

复制根目录的 `.env.example` 为 `.env`，填入你自己的密钥与密码：

```env
# 阿里云 DashScope API
DASHSCOPE_API_KEY=sk-你的密钥
DASHSCOPE_MODEL=qwen3.5-omni-plus

# MySQL 数据库
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=你的MySQL密码
DB_NAME=gesture_qa

# 检测参数
YOLO_CONFIDENCE=0.45
```

### 7. 启动后端服务

```bash
.venv\Scripts\python backend\app.py
```

或直接双击 `start_backend.bat`。后端将在 `http://127.0.0.1:8000` 启动。
`yolov8n.pt` 已随仓库附带于项目根目录，无需联网下载；若缺失会由 ultralytics 自动拉取。

### 8. 启动前端应用

打开新的终端窗口：

```bash
.venv\Scripts\python frontend\main.py
```

或直接双击 `start_frontend.bat`。

### 9. 使用流程

1. 点击「摄像头」「上传视频」或「手机摄像头」选择视频源
2. 点击绿色的「开始检测」按钮启动检测
3. 在摄像头前做出指向手势（食指伸直，其余手指弯曲）
4. 系统自动识别指向的物品，右侧「指向物品」卡片显示图片和名称
5. 在「智能问答」区输入问题，点击「发送」或回车获取 AI 回答
   - 也可先用语音输入：打开「🎤 语音输入」开关 → 点「按住录音提问」说话 → 再点一次自动转写为文字填入输入框 → 确认/编辑后回车发送
6. 点击红色的「停止检测」按钮停止

---

## 项目结构

```
3B412/
├── backend/
│   ├── app.py              # FastAPI 主入口（WebSocket 背压处理 + REST API）
│   ├── gesture.py          # MediaPipe 手势识别（VIDEO 跟踪模式）
│   ├── detector.py         # YOLOv8 物体检测（纯结构化输出，不做绘制）
│   ├── geometry.py         # 指向匹配/手势判定/坐标换算（纯函数，可单测）
│   ├── llm_client.py       # 阿里云 DashScope 客户端（失败抛 LLMError）
│   ├── db.py               # MySQL 操作（线程安全 + 自动重连 + JSON bbox）
│   ├── models/             # 本地手部模型（离线可用）
│   ├── uploads/            # 问答截图目录（自动创建，静态挂载 /uploads）
│   └── requirements.txt
├── frontend/
│   ├── main.py             # 入口（QApplication + 主题）
│   ├── main_window.py      # 主窗口（深色 UI：状态徽章/三卡片/历史面板/语音输入）
│   ├── camera_thread.py    # 采集 + WebSocket 线程（帧锁 + QImage 安全）
│   ├── mjpeg_source.py     # 手机 MJPEG 拉流（自研解析，绕开 FFmpeg 兼容坑）
│   ├── mic_capture.py      # 麦克风录音（sounddevice，语音输入提问）
│   ├── overlay.py          # 视频叠加绘制（纯函数）
│   ├── theme.py            # 深色 QSS 主题与调色板
│   ├── i18n.py             # COCO 类别中英映射
│   ├── config.py           # 配置集中读取 .env
│   └── requirements.txt
├── tests/                  # 单元测试（pytest：几何逻辑 + 叠加绘制）
├── schema.sql              # 建表脚本（幂等，可重复执行）
├── start_backend.bat / start_frontend.bat   # 一键启动（使用 .venv）
├── setup_python.bat / install_packages.bat  # 新机快速部署
├── .env                    # 环境变量配置（勿提交到版本库）
├── .gitignore
└── README.md
```

---

## API 接口说明

| 接口 | 方法 | 说明 |
|------|------|------|
| `/ws/process` | WebSocket | 实时视频帧处理，返回手势+物体检测结果（latest-frame 背压；坐标为原始帧坐标系） |
| `/qa` | POST | 多模态问答（SSE 流式），接收问题与可选截图，成功回答后写历史记录 |
| `/asr` | POST | 语音转文字：上传麦克风录制的 WAV，返回 `{"text": "..."}` |
| `/history` | GET | 获取历史记录（含 total 全库计数、bbox 已解析、image_path） |
| `/latest` | GET | 获取最新检测记录 |
| `/uploads/{file}` | GET | 静态访问问答截图 |
| `/health` | GET | 健康检查（返回 db / gesture_ready / detector_ready） |

WebSocket 文本控制指令：`{"type": "reset"}` 清除后端指向确认状态。

### 可选环境变量（均有默认值，写在 `.env`）

| 变量 | 默认 | 作用 |
|------|------|------|
| `YOLO_CONFIDENCE` | 0.45 | 检测置信度阈值 |
| `YOLO_MODEL` | yolov8n.pt | 模型文件（相对项目根/backend 解析，可切 yolov8s.pt） |
| `POINT_CONFIRM_FRAMES` | 3 | 指向确认所需连续帧数 |
| `POINT_MAX_ANGLE` | 45 | 指向匹配锥域半角（度），越小越严格 |
| `MAX_INFER_WIDTH` | 1280 | 推理宽度上限，超出则等比降采样 |
| `MAX_AUDIO_BYTES` | 10485760 | /asr 上传音频大小上限（字节） |
| `FRONTEND_FPS` | 10 | 前端采集/发送帧率 |
| `NUM_HANDS` | 1 | MediaPipe 最大手数 |

---

## 常见问题

**Q: YOLOv8 首次运行很慢？**
A: `yolov8n.pt` 已随仓库附带于项目根目录，正常情况下无需下载；若被删除，
ultralytics 会在首次运行时自动重新下载（约 6MB）。

**Q: 摄像头无法打开？**
A: 检查是否有其他程序占用摄像头，或尝试重启应用。

**Q: 指向手势识别不准确？**
A: 确保食指完全伸直，其余三指弯曲，手部距离摄像头 30-60cm 效果最佳。

**Q: API 调用超时？**
A: 检查网络连接，确认 DashScope API Key 有效，可适当增加超时时间。

**Q: 数据库连接失败？**
A: 确认 MySQL 服务已启动，`.env` 中的数据库配置正确，且已通过 Navicat 执行了 `schema.sql`。
数据库连不上时主检测链路仍可用，仅"历史记录"功能不可用（后端日志有 warning）。

**Q: 前端连不上后端 WebSocket（握手返回 404）？**
A: 后端 Python 环境缺少 `websockets` 包——它是 uvicorn 处理 WS 协议所必需的。
运行 `pip install -r backend\requirements.txt` 补全依赖后重启后端。

**Q: 画面里的检测框位置偏移？**
A: 旧版本前后端坐标系不一致会导致偏移，现已修复（后端统一换算回原始帧坐标）。
若仍有问题，确认后端为当前版本、`MAX_INFER_WIDTH` 未被改为异常值。

**Q: 手机麦克风音源不可用（提示未提供音频流）？**
A: IP Webcam 类 App 默认关闭音频采集（未开启时 `/mic.mp3`、`/audio.wav`、`/audiofeed` 均 404）。
在手机上：IP Webcam → 设置 → 勾选 **Enable audio capture**（不同版本位于
Video and cameras 或 Audio settings 分组）→ **Stop server 再 Start server**（必须重启服务器）。
前端已内置三种端点自动探测；对"单 RIFF 头 + 无限 PCM"的流式 WAV 会自动重建标准头部
（声明长度 0xFFFFFFFF 的无限头直接上传会被识别 API 拒绝）。

**Q: 手机摄像头（ADB 模式）连不上 / adb forward 报 10013？**
A: 10013 = 本机端口被其他程序独占绑定，**8080 常被腾讯系进程（ApplicationWebServer.exe）占用**。
手动方式：在 `res\platform-tools` 目录执行 `adb forward tcp:8080 tcp:8080`，
若报 10013 就换端口：`adb forward tcp:8081 tcp:8081`，视频地址相应填
`http://localhost:8081/video`。前提是手机 IP Webcam 监听同一端口（App 设置里可看）。
新版本前端已内置自动化：点「手机摄像头」时自动逐个尝试
(8080→8080, 8081→8081, 18080→8080, 18080→8081) 并**实测探测**转发是否真的通向手机
HTTP 服务，成功后对话框自动填好可用地址。

**Q: 后端控制台日志出现 `[32mINFO[0m` 这样的乱码？**
A: 旧版 uvicorn 向不解析 ANSI 的 cmd 终端输出颜色代码。现已自动处理：
启动时激活终端虚拟转义模式（正常显示颜色），无法激活时自动关闭彩色日志。

**Q: 指向识别正常但手机画面很卡 / 发热？**
A: IP Webcam 默认 1080p@20fps 经 ADB 隧道带宽压力大，在 App 设置里把
视频分辨率调到 640×480 或 960×540 即可（检测精度几乎不受影响）。

---

## 开发与测试

纯逻辑单元测试无需摄像头 / GPU / 网络：

```bash
pip install -r requirements-dev.txt
python -m pytest tests -q
```

覆盖 `backend/geometry.py`（指向锥域匹配、手势判定、坐标换算）与
`frontend/overlay.py`（叠加绘制不修改输入帧、类型兼容）。

---

## 后续计划（二期）

- ~~语音输入提问（ASR）~~ ✅ 已实现（`/asr` + 麦克风录音转写）
- 语音播报答案（TTS，与已实现的 ASR 配成"语音对话"闭环）
- 历史记录可视化统计（物品频次图表）
- 更多手势类型支持（握拳、张掌等）
- 模型精度优化（配置 `YOLO_MODEL=yolov8s.pt` 即可切换）
