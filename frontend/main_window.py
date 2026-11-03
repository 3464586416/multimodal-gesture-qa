"""主窗口：全新深色主题 UI。

布局：顶部标题/状态徽章栏 + 左侧视频卡片 + 右侧三张卡片（指向物品 / 智能问答 / 历史记录）。
改进点：QImage 悬空修复、帧读取加锁、属性在 __init__ 初始化、确认阈值跟随后端、
历史面板（截图可预览）、后端连接状态指示、问答错误结构化提示。
"""
import json
import os
import threading
import time

import cv2
import requests
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPixmap, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QSplitter, QTextEdit, QVBoxLayout, QWidget,
)

import config
import theme
from camera_thread import CameraThread
from i18n import cn_name
from mjpeg_source import normalize_stream_url, validate_stream_url
from mic_capture import MicRecorder
from phone_mic import PhoneMicRecorder

MAX_RECORD_SECONDS = 15


def _repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class Card(QFrame):
    """圆角卡片容器：标题 + 内容布局。"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 14)
        outer.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)
        bar = QFrame()
        bar.setObjectName("AccentBar")
        bar.setFixedWidth(4)
        bar.setFixedHeight(16)
        lbl = QLabel(title)
        lbl.setObjectName("CardTitle")
        header.addWidget(bar)
        header.addWidget(lbl)
        header.addStretch()
        outer.addLayout(header)

        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        outer.addLayout(self.body)


class MainWindow(QMainWindow):
    """主窗口"""

    # 线程安全 UI 更新信号
    _history_loaded = pyqtSignal(list)
    _history_image = pyqtSignal(int, object)          # row index, QPixmap(None=失败)
    _backend_checked = pyqtSignal(bool, str)
    _qa_stream_start = pyqtSignal()
    _qa_stream_chunk = pyqtSignal(str)
    _qa_stream_done = pyqtSignal(object)              # record_id 或 None
    _qa_stream_error = pyqtSignal(str)
    _qa_result_line = pyqtSignal(str, str)            # 兜底：一次性消息（role, text）
    _asr_done = pyqtSignal(str)                       # 语音转写成功（文本）
    _asr_failed = pyqtSignal(str)                     # 语音转写失败（原因）

    def __init__(self):
        super().__init__()
        self.setWindowTitle("手势指示多模态问答系统")
        self.resize(1280, 760)
        self.setMinimumSize(1080, 640)

        # 运行状态（不再依赖 hasattr 兜底）
        self.camera_thread = None
        self.is_running = False
        self.video_source = None
        self.video_path = None
        self.last_pointed_object = None
        self.last_object_image = None
        self._history_records = []
        self._confirm_threshold = 3
        self._forwarded = None          # (本地端口, 手机端口)：adb 转发探测结果

        # 语音输入（麦克风默认关闭 —— 隐私优先，手动开启）
        self._recorder = MicRecorder()
        self._phone_rec = None
        self._mic_mode = "pc"
        self._recording = False
        self._record_start = 0.0

        self._history_loaded.connect(self._on_history_loaded)
        self._history_image.connect(self._on_history_image)
        self._backend_checked.connect(self._on_backend_checked)
        self._qa_stream_start.connect(self._start_ai_line)
        self._qa_stream_chunk.connect(self._append_ai_chunk)
        self._qa_stream_done.connect(self._finish_ai)
        self._qa_stream_error.connect(self._append_ai_error)
        self._qa_result_line.connect(self._append_qa_line)
        self._asr_done.connect(self._on_asr_done)
        self._asr_failed.connect(self._on_asr_failed)

        self.init_ui()
        self._check_backend()
        self._load_history()

    # ================= UI =================

    def init_ui(self):
        central = QWidget()
        central.setObjectName("Central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        # ----- 顶部标题栏 -----
        header = QFrame()
        header.setObjectName("Card")
        hb = QHBoxLayout(header)
        hb.setContentsMargins(18, 10, 18, 10)
        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        t = QLabel("手势指示 · 多模态问答系统")
        t.setObjectName("AppTitle")
        sub = QLabel("指向画面中的物品，向 AI 提问   |   Point → Ask → Understand")
        sub.setObjectName("AppSubtitle")
        title_col.addWidget(t)
        title_col.addWidget(sub)
        hb.addLayout(title_col)
        hb.addStretch()

        self.backend_chip = QLabel("后端检测中...")
        self.backend_chip.setObjectName("StatusBadge")
        self.backend_chip.setStyleSheet(theme.badge_style("idle"))
        hb.addWidget(self.backend_chip)

        self.status_badge = QLabel("就绪")
        self.status_badge.setObjectName("StatusBadge")
        self.status_badge.setStyleSheet(theme.badge_style("idle"))
        hb.addWidget(self.status_badge)
        root.addWidget(header)

        # ----- 主分割 -----
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(12)

        # 左：视频卡片
        left_card = Card("视频画面")
        self.video_label = QLabel("选择视频源后点击「开始检测」")
        self.video_label.setObjectName("VideoCanvas")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 420)
        left_card.body.addWidget(self.video_label, 1)

        source_row = QHBoxLayout()
        source_row.setSpacing(8)
        self.btn_camera = QPushButton("摄像头")
        self.btn_video = QPushButton("上传视频")
        self.btn_phone = QPushButton("手机摄像头")
        for b in (self.btn_camera, self.btn_video, self.btn_phone):
            b.setCheckable(True)
            b.setProperty("role", "toggle_off")
            source_row.addWidget(b)
        left_card.body.addLayout(source_row)

        start_row = QHBoxLayout()
        start_row.addStretch()
        self.btn_start = QPushButton("▶  开始检测")
        self.btn_start.setProperty("role", "start")
        self.btn_start.setFixedWidth(200)
        self.btn_start.setEnabled(False)
        start_row.addWidget(self.btn_start)
        start_row.addStretch()
        left_card.body.addLayout(start_row)
        splitter.addWidget(left_card)

        # 右：三张卡片
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        obj_card = Card("指向物品")
        self.object_image_label = QLabel("等待检测...")
        self.object_image_label.setObjectName("ObjectPreview")
        self.object_image_label.setAlignment(Qt.AlignCenter)
        self.object_image_label.setMinimumHeight(190)
        obj_card.body.addWidget(self.object_image_label)
        self.object_name_label = QLabel("物品名称：--")
        f = QFont("Microsoft YaHei", 12, QFont.Bold)
        self.object_name_label.setFont(f)
        self.object_name_label.setStyleSheet("background:transparent;border:none;")
        obj_card.body.addWidget(self.object_name_label)
        self.object_meta_label = QLabel("置信度：--    类别：--")
        self.object_meta_label.setStyleSheet(
            f"color:{theme.PALETTE['text_dim']};background:transparent;border:none;")
        obj_card.body.addWidget(self.object_meta_label)
        self.confirm_bar = QProgressBar()
        self.confirm_bar.setRange(0, self._confirm_threshold)
        self.confirm_bar.setValue(0)
        self.confirm_bar.setFixedHeight(10)
        obj_card.body.addWidget(self.confirm_bar)
        self.btn_new_object = QPushButton("识别新物品")
        self.btn_new_object.setProperty("role", "primary")
        self.btn_new_object.setEnabled(False)
        obj_card.body.addWidget(self.btn_new_object)
        right_layout.addWidget(obj_card)

        qa_card = Card("智能问答")
        # 语音输入行：开关（默认关）+ 录音按钮（开启开关后可见）
        mic_row = QHBoxLayout()
        mic_row.setSpacing(8)
        self.btn_mic = QPushButton("🎤  语音输入：关")
        self.btn_mic.setCheckable(True)
        self.btn_mic.setProperty("role", "toggle_off")
        mic_row.addWidget(self.btn_mic)
        mic_row.addWidget(QLabel("音源:"))
        self.mic_src = QComboBox()
        self.mic_src.addItems(["💻 电脑麦克风", "📱 手机麦克风"])
        self.mic_src.setToolTip("手机麦克风需先选择「手机摄像头」视频源，并在\n"
                                "IP Webcam 中启用 Enable audio capture")
        mic_row.addWidget(self.mic_src)
        self.btn_record = QPushButton("●  按住录音提问")
        self.btn_record.setProperty("role", "primary")
        self.btn_record.setVisible(False)
        mic_row.addWidget(self.btn_record)
        mic_row.addStretch()
        qa_card.body.addLayout(mic_row)

        self.qa_display = QTextEdit()
        self.qa_display.setReadOnly(True)
        self.qa_display.setMinimumHeight(140)
        self.qa_display.setPlaceholderText("指向一个物品后，输入问题点击发送…")
        qa_card.body.addWidget(self.qa_display, 1)
        qa_input_row = QHBoxLayout()
        self.qa_input = QLineEdit()
        self.qa_input.setPlaceholderText("输入关于物品的问题，回车发送")
        self.btn_send = QPushButton("发送")
        self.btn_send.setProperty("role", "primary")
        self.btn_send.setEnabled(False)
        qa_input_row.addWidget(self.qa_input, 1)
        qa_input_row.addWidget(self.btn_send)
        qa_card.body.addLayout(qa_input_row)
        right_layout.addWidget(qa_card, 1)

        hist_card = Card("历史记录")
        hist_row = QHBoxLayout()
        self.hist_image_label = QLabel("点击记录查看截图")
        self.hist_image_label.setObjectName("ObjectPreview")
        self.hist_image_label.setAlignment(Qt.AlignCenter)
        self.hist_image_label.setFixedSize(150, 110)
        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(150)
        hist_row.addWidget(self.hist_image_label)
        hist_row.addWidget(self.history_list, 1)
        hist_card.body.addLayout(hist_row)
        right_layout.addWidget(hist_card)

        splitter.addWidget(right)
        splitter.setSizes([780, 500])
        root.addWidget(splitter, 1)

        # ----- 底部状态栏 -----
        self.status_label = QLabel("就绪 — 请选择视频源")
        self.status_label.setStyleSheet(
            f"color:{theme.PALETTE['text_dim']}; padding:2px 6px;")
        root.addWidget(self.status_label)

        # ----- 事件绑定 -----
        self.btn_camera.clicked.connect(lambda: self._select_camera_source("camera"))
        self.btn_video.clicked.connect(self._select_video_source)
        self.btn_phone.clicked.connect(self._select_phone_source)
        self.btn_start.clicked.connect(self.toggle_detection)
        self.btn_new_object.clicked.connect(self.reset_object)
        self.btn_send.clicked.connect(self.send_question)
        self.qa_input.returnPressed.connect(self.send_question)
        self.btn_mic.toggled.connect(self._on_mic_toggled)
        self.btn_record.clicked.connect(self._toggle_record)
        self._record_timer = QTimer(self)
        self._record_timer.setInterval(500)
        self._record_timer.timeout.connect(self._on_record_tick)
        self.history_list.itemClicked.connect(self._on_history_item_clicked)

    # ---------- 徽章 ----------

    def _set_badge(self, text: str, kind: str = "idle"):
        self.status_badge.setText(text)
        self.status_badge.setStyleSheet(theme.badge_style(kind))

    # ---------- 后端健康检查 ----------

    def _check_backend(self):
        def worker():
            try:
                r = requests.get(f"{config.BACKEND_HTTP}/health", timeout=3)
                data = r.json()
                self._backend_checked.emit(r.ok, json.dumps(data))
            except Exception:
                self._backend_checked.emit(False, "")
        threading.Thread(target=worker, daemon=True).start()

    def _on_backend_checked(self, ok: bool, _info: str):
        if ok:
            self.backend_chip.setText("后端 · 已连接")
            self.backend_chip.setStyleSheet(theme.badge_style("ready"))
            self._load_history()
        else:
            self.backend_chip.setText("后端 · 未启动")
            self.backend_chip.setStyleSheet(theme.badge_style("error"))
            self.status_label.setText("后端未启动 — 请先运行 start_backend.bat")

    # ---------- 视频源选择 ----------

    def _mark_source(self, chosen: QPushButton):
        for b in (self.btn_camera, self.btn_video, self.btn_phone):
            checked = (b is chosen)
            b.setChecked(checked)
            b.setProperty("role", "toggle_on" if checked else "toggle_off")
            _repolish(b)

    def _guard_running(self) -> bool:
        if self.is_running:
            QMessageBox.warning(self, "提示", "请先停止当前检测")
            return True
        return False

    def _select_camera_source(self, _=None):
        if self._guard_running():
            return
        self.video_source = "camera"
        self.video_path = None
        self._mark_source(self.btn_camera)
        self.btn_start.setEnabled(True)
        self.status_label.setText("已选择：本机摄像头")

    def _select_video_source(self):
        if self._guard_running():
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.wmv);;所有文件 (*)")
        if not file_path:
            return
        self.video_source = "video"
        self.video_path = file_path
        self._mark_source(self.btn_video)
        self.btn_start.setEnabled(True)
        self.status_label.setText(f"已选择视频：{file_path}")

    def _select_phone_source(self):
        if self._guard_running():
            return
        port = self._setup_adb_forward()
        phone_ip = self._phone_ip()
        phone_port = self._forwarded[1] if self._forwarded else 8081
        if phone_ip:
            default_url = f"http://{phone_ip}:{phone_port}/video"
        else:
            saved = self._read_phone_url()
            default_url = saved or f"http://localhost:{port}/video"
            if saved and not self._forwarded:
                self.status_label.setText(f"使用上次直连地址：{saved}")
        url, ok = QInputDialog.getText(
            self, "手机摄像头",
            "输入 IP Webcam 视频流地址：\n\n"
            f"① WiFi 直连（推荐，更流畅）：{default_url}\n"
            f"② ADB 转发（已自动建立 localhost:{port} -> 手机:{phone_port}）：http://localhost:{port}/video\n\n"
            "注意：adb devices 显示的 15555 是 ADB 调试端口，不是视频端口！\n"
            "错误示例 http://10.33.31.139:15555:8081/video（会被自动纠正）",
            text=default_url)
        if not ok or not url:
            return

        normalized = normalize_stream_url(url)
        err = validate_stream_url(normalized)
        if err:
            QMessageBox.warning(
                self, "地址不可用",
                f"{err}\n\n可用格式：\n"
                f"  WiFi 直连  http://手机IP:{phone_port}/video\n"
                f"  ADB 转发   http://localhost:{port}/video\n\n"
                "（IP Webcam 视频端口在手机 App 主界面/设置里可查看，常见为 8080 或 8081）")
            return
        if normalized != url.strip():
            self.status_label.setText(f"地址已自动纠正为：{normalized}")
        self.video_source = "video"
        self.video_path = normalized
        self._write_phone_url(normalized)
        self._mark_source(self.btn_phone)
        self.btn_start.setEnabled(True)
        self.status_label.setText(f"已选择手机摄像头：{normalized}")

    # ----- 手机地址记忆（.frontend_state.json，随 .gitignore 排除） -----

    _STATE_FILE = os.path.join(config.ROOT_DIR, ".frontend_state.json")

    def _read_phone_url(self) -> str:
        try:
            with open(self._STATE_FILE, encoding="utf-8") as f:
                return json.load(f).get("phone_url", "")
        except Exception:
            return ""

    def _write_phone_url(self, url: str):
        try:
            with open(self._STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({"phone_url": url}, f, ensure_ascii=False)
        except Exception:
            pass

    def _phone_ip(self):
        """从 adb 设备序列号（无线连接形如 10.33.31.139:15555）提取手机 IP。"""
        import os
        if not os.path.exists(config.ADB_PATH):
            return None
        r = self._adb("devices")
        if r is None or r.returncode != 0:
            return None
        for line in r.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device" and ":" in parts[0]:
                return parts[0].split(":")[0]
        return None

    def _adb(self, *args):
        import subprocess
        try:
            return subprocess.run([config.ADB_PATH, *args], capture_output=True,
                                  timeout=6, encoding="utf-8", errors="replace")
        except Exception:
            return None

    def _probe_http_port(self, port: int, timeout: float = 2.0) -> bool:
        """探测本机端口是否真的有 HTTP 服务（验证转发指向的手机端口活着）。"""
        try:
            return requests.get(f"http://127.0.0.1:{port}/", timeout=timeout).status_code < 500
        except Exception:
            return False

    def _setup_adb_forward(self) -> int:
        """
        建立并验证 adb 端口转发，返回可用本地端口（并记录到 self._forwarded）。
        adb forward 成功只说明本机绑定成功，手机侧没监听照样"成功"，
        因此每个候选组合都转发后立即 HTTP 探测，不通就 --remove 换下一个。
        本机 8080 常被腾讯系 ApplicationWebServer.exe 独占（绑定报 10013），
        自动降级 8081/18080 等组合。
        """
        import os
        self._forwarded = None
        if not os.path.exists(config.ADB_PATH) or self._adb("get-state") is None:
            return 8080
        candidates = [
            (8080, 8080),      # 标准：手机 IP Webcam 默认端口
            (8081, 8081),      # 本机 8080 被占用 + 手机改为 8081（当前环境）
            (18080, 8080),     # 本机 8080 被占用 + 手机仍是 8080
            (18080, 8081),
        ]
        for local, phone in candidates:
            r = self._adb("forward", f"tcp:{local}", f"tcp:{phone}")
            if r is None or r.returncode != 0:
                continue
            if self._probe_http_port(local):
                self._forwarded = (local, phone)
                self.status_label.setText(
                    f"ADB 转发已就绪：localhost:{local} -> 手机:{phone}")
                return local
            self._adb("forward", "--remove", f"tcp:{local}")
        self.status_label.setText("ADB 转发失败：请确认手机已连接且 IP Webcam 已启动")
        return 8081

    # ---------- 检测控制 ----------

    def toggle_detection(self):
        if not self.is_running:
            self.start_detection()
        else:
            self.stop_detection()

    def start_detection(self):
        if self.video_source is None:
            QMessageBox.warning(self, "提示", "请先选择视频源")
            return
        self.is_running = True
        self.btn_start.setText("■  停止检测")
        self.btn_start.setProperty("role", "danger")
        _repolish(self.btn_start)
        for b in (self.btn_camera, self.btn_video, self.btn_phone):
            b.setEnabled(False)
        self._set_badge("感知中", "perceive")

        self.camera_thread = CameraThread(self.video_source, self.video_path)
        self.camera_thread.frame_ready.connect(self.update_video_frame)
        self.camera_thread.detection_result.connect(self.handle_detection)
        self.camera_thread.error_occurred.connect(self.handle_error)
        self.camera_thread.status_changed.connect(self._on_thread_status)
        self.camera_thread.reset_confirmed.connect(
            lambda: self.status_label.setText("已重置，请指向新物品"))
        self.camera_thread.start()

    def stop_detection(self):
        self.is_running = False
        self.btn_start.setText("▶  开始检测")
        self.btn_start.setProperty("role", "start")
        _repolish(self.btn_start)
        for b in (self.btn_camera, self.btn_video, self.btn_phone):
            b.setEnabled(True)

        self._clear_pointed_state()
        if self.camera_thread:
            self.camera_thread.stop()
            if not self.camera_thread.wait(5000):
                self.status_label.setText("警告：采集线程未在 5 秒内退出")
            self.camera_thread = None

        self.video_label.setText("选择视频源后点击「开始检测」")
        self.video_label.setPixmap(QPixmap())
        self._set_badge("就绪", "idle")
        self.status_label.setText("已停止检测")

    def _clear_pointed_state(self):
        self.last_pointed_object = None
        self.last_object_image = None
        self.object_name_label.setText("物品名称：--")
        self.object_meta_label.setText("置信度：--    类别：--")
        self.object_image_label.setText("等待检测...")
        self.object_image_label.setPixmap(QPixmap())
        self.confirm_bar.setValue(0)
        self.btn_send.setEnabled(False)
        self.btn_new_object.setEnabled(False)

    # ---------- 画面与检测回调 ----------

    def update_video_frame(self, q_img):
        pixmap = QPixmap.fromImage(q_img)
        scaled = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio,
                               Qt.FastTransformation)
        self.video_label.setPixmap(scaled)

    def handle_detection(self, result: dict):
        self._confirm_threshold = int(result.get("confirm_threshold", 3))
        if self.confirm_bar.maximum() != self._confirm_threshold:
            self.confirm_bar.setMaximum(self._confirm_threshold)

        if result.get("status") == "gesture_unavailable":
            self._set_badge("手势模型异常", "error")
            self.status_label.setText("后端手势模型未就绪，请检查后端日志")
            return

        pointed = result.get("pointed_object")
        count = int(result.get("confirm_count", 0))
        self.confirm_bar.setValue(min(count, self._confirm_threshold))

        if pointed:
            self.last_pointed_object = pointed
            name_cn = cn_name(pointed["class_name"])
            self.object_name_label.setText(f"物品名称：{name_cn}")
            self.object_meta_label.setText(
                f"置信度：{pointed['confidence']:.2f}    "
                f"类别：{pointed['class_name']}")
            self.btn_send.setEnabled(True)
            self.btn_new_object.setEnabled(True)
            self._set_badge(f"已确认：{name_cn}", "ready")
            self.status_label.setText(
                f"已确认指向：{name_cn}（置信度 {pointed['confidence']:.2f}）")

            frame = self.camera_thread.get_current_frame() if self.camera_thread else None
            if frame is not None:
                x1, y1, x2, y2 = pointed["bbox"]
                crop = frame[max(0, y1):y2, max(0, x1):x2]
                if crop.size > 0:
                    self.last_object_image = crop.copy()
                    self._show_crop_on_object_preview(crop)
        else:
            if count > 0:
                self._set_badge(f"确认中 {count}/{self._confirm_threshold}", "pointing")
                self.status_label.setText(f"指向确认中… {count}/{self._confirm_threshold}")
            elif result.get("pointing"):
                self._set_badge("指向中", "pointing")
            elif result.get("hand_detected"):
                self._set_badge("检测到手部", "perceive")
            else:
                self._set_badge("未检测到手", "idle")

    def _show_crop_on_object_preview(self, crop_bgr):
        ok, buffer = cv2.imencode('.png', crop_bgr)
        if not ok:
            return
        pix = QPixmap()
        if pix.loadFromData(buffer.tobytes(), "PNG"):
            scaled = pix.scaled(self.object_image_label.size(), Qt.KeepAspectRatio,
                               Qt.SmoothTransformation)
            self.object_image_label.setPixmap(scaled)

    def handle_error(self, error_msg: str):
        self.status_label.setText(f"连接问题：{error_msg}")
        self._set_badge("连接异常", "error")

    def _on_thread_status(self, status: str):
        self.status_label.setText(status)
        if "已连接后端" in status:
            self._set_badge("感知中", "perceive")

    def reset_object(self):
        self._clear_pointed_state()
        self.qa_display.clear()
        self.status_label.setText("已重置，请指向新物品")
        self._set_badge("感知中", "perceive")
        if self.camera_thread:
            self.camera_thread.send_reset()

    # ---------- 问答 ----------

    def send_question(self):
        question = self.qa_input.text().strip()
        if not question:
            return
        if not self.last_pointed_object:
            self._append_qa_line("system", "请先指向一个物品")
            return

        self.btn_send.setEnabled(False)
        self.qa_input.clear()
        self._append_qa_line("user", question)
        self._set_badge("问答中", "asking")
        self.status_label.setText("正在获取 AI 回答…")

        obj = self.last_pointed_object
        files = None
        if self.last_object_image is not None:
            ok, buffer = cv2.imencode('.jpg', self.last_object_image)
            if ok:
                files = {'image': ('object.jpg', buffer.tobytes(), 'image/jpeg')}
        data = {
            "question": question,
            "object_name": obj["class_name"],
            "object_class": obj["class_name"],
            "confidence": obj["confidence"],
            "bbox": json.dumps(obj["bbox"]),
        }

        def worker():
            try:
                resp = requests.post(f"{config.BACKEND_HTTP}/qa",
                                     data=data, files=files,
                                     timeout=180, stream=True)
                resp.raise_for_status()
                self._qa_stream_start.emit()
                record_id = None
                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    try:
                        msg = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    if "chunk" in msg:
                        self._qa_stream_chunk.emit(msg["chunk"])
                    elif msg.get("error"):
                        self._qa_stream_error.emit(
                            msg.get("message", "未知错误"))
                        return
                    elif msg.get("done"):
                        record_id = msg.get("record_id")
                self._qa_stream_done.emit(record_id)
            except Exception as e:
                self._qa_stream_error.emit(str(e))

        threading.Thread(target=worker, daemon=True).start()

    # ----- 聊天渲染 -----

    def _scroll_chat(self):
        sb = self.qa_display.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _cursor_at_end(self):
        cur = self.qa_display.textCursor()
        cur.movePosition(QTextCursor.End)
        return cur

    def _append_qa_line(self, role: str, text: str):
        cur = self._cursor_at_end()
        fmt = QTextCharFormat()
        if role == "user":
            fmt.setForeground(QColor("#67e8f9"))
            fmt.setFontWeight(QFont.Bold)
            cur.insertText("你  ", fmt)
            fmt.setForeground(QColor("#dbe4f0"))
            fmt.setFontWeight(QFont.Normal)
            cur.insertText(text, fmt)
        elif role == "ai":
            fmt.setForeground(QColor("#c4b5fd"))
            fmt.setFontWeight(QFont.Bold)
            cur.insertText("AI  ", fmt)
        else:  # system / error
            fmt.setForeground(QColor(theme.PALETTE['warn']))
            cur.insertText(f"提示  {text}", fmt)
        cur.insertBlock()
        self.qa_display.setTextCursor(cur)
        self._scroll_chat()

    def _start_ai_line(self):
        cur = self._cursor_at_end()
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#c4b5fd"))
        fmt.setFontWeight(QFont.Bold)
        cur.insertText("AI  ", fmt)
        self.qa_display.setTextCursor(cur)
        self._scroll_chat()

    def _append_ai_chunk(self, chunk: str):
        cur = self._cursor_at_end()
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#e6edf3"))
        cur.insertText(chunk, fmt)
        self.qa_display.setTextCursor(cur)
        self._scroll_chat()

    def _finish_ai(self, record_id):
        cur = self._cursor_at_end()
        cur.insertBlock()
        self.qa_display.setTextCursor(cur)
        self._set_badge(
            f"已确认：{cn_name(self.last_pointed_object['class_name'])}"
            if self.last_pointed_object else "就绪", "ready")
        self.status_label.setText(
            "回答完成，已存入历史记录" if record_id else "回答完成")
        self.btn_send.setEnabled(True)
        self._load_history()

    def _append_ai_error(self, message: str):
        cur = self._cursor_at_end()
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(theme.PALETTE['bad']))
        cur.insertText(f"错误  {message}", fmt)
        cur.insertBlock()
        self.qa_display.setTextCursor(cur)
        self._scroll_chat()
        self._set_badge("问答失败", "error")
        self.status_label.setText("获取回答失败")
        self.btn_send.setEnabled(True)

    # ---------- 语音输入（麦克风开关 + 录音转写）----------

    def _on_mic_toggled(self, checked: bool):
        self.btn_mic.setProperty("role", "toggle_on" if checked else "toggle_off")
        self.btn_mic.setText("🎤  语音输入：开" if checked else "🎤  语音输入：关")
        _repolish(self.btn_mic)
        self.btn_record.setVisible(checked)
        if not checked and self._recording:
            self._stop_recording(discard=True)
        elif checked:
            self.status_label.setText("语音输入已开启：点「按住录音提问」开始，"
                                      "说完再点一次自动转写")

    def _toggle_record(self):
        if not self._recording:
            self._start_recording()
        else:
            self._stop_recording(discard=False)

    def _start_recording(self):
        mode = "phone" if self.mic_src.currentIndex() == 1 else "pc"
        if mode == "phone":
            if not (self.video_path and str(self.video_path).lower().startswith("http")):
                QMessageBox.information(
                    self, "需要手机视频源",
                    "手机麦克风与画面共用同一 IP Webcam 服务。\n"
                    "请先点击「手机摄像头」选择视频源，再切换音源。")
                return
            self._phone_rec = PhoneMicRecorder(str(self.video_path))
            target = self._phone_rec
        else:
            target = self._recorder
        try:
            target.start()
        except Exception as e:
            self._phone_rec = None
            QMessageBox.warning(
                self, "麦克风不可用",
                str(e) if mode == "phone" else
                f"{e}\n\n请检查：系统设置 → 隐私 → 麦克风（允许桌面应用访问），"
                "或关闭其他占用麦克风的应用后重试。")
            return
        self._mic_mode = mode
        self._recording = True
        self._record_start = time.time()
        self.btn_record.setText("■  停止并转写")
        self.btn_record.setProperty("role", "danger")
        _repolish(self.btn_record)
        self._record_timer.start()
        self._set_badge("录音中", "asking")
        self._update_record_status()

    def _update_record_status(self):
        elapsed = int(time.time() - self._record_start)
        self.status_label.setText(
            f"● 正在录音 {elapsed}/{MAX_RECORD_SECONDS}s —— "
            "说完请再次点击按钮停止并转写")

    def _on_record_tick(self):
        if not self._recording:
            self._record_timer.stop()
            return
        if time.time() - self._record_start >= MAX_RECORD_SECONDS:
            self.status_label.setText("达到最长录音 15 秒，自动停止并转写")
            self._stop_recording(discard=False)
        else:
            self._update_record_status()

    def _stop_recording(self, discard: bool):
        self._recording = False
        self._record_timer.stop()
        self.btn_record.setText("●  按住录音提问")
        self.btn_record.setProperty("role", "primary")
        _repolish(self.btn_record)
        if discard:
            self._recorder.cancel()
            if self._phone_rec:
                self._phone_rec.cancel()
                self._phone_rec = None
            self._set_badge("感知中" if self.is_running else "就绪",
                            "perceive" if self.is_running else "idle")
            return
        if self._mic_mode == "phone" and self._phone_rec:
            payload, fmt = self._phone_rec.stop()
            self._phone_rec = None
            min_bytes = 4000        # 128kbps MP3 ≈ 16KB/s，短于 0.25s 视为过短
        else:
            payload, fmt = self._recorder.stop(), "wav"
            min_bytes = 44 + 16000  # PCM 16k/16bit ≈ 32KB/s
        if len(payload) < min_bytes:
            self.status_label.setText("录音太短，未发送识别")
            return
        self.btn_record.setEnabled(False)
        self.status_label.setText("正在语音转写…")
        mime = "audio/mpeg" if fmt == "mp3" else f"audio/{fmt}"

        def worker():
            try:
                r = requests.post(f"{config.BACKEND_HTTP}/asr",
                                  files={"file": (f"question.{fmt}", payload,
                                                  mime)},
                                  timeout=60)
                if r.ok:
                    self._asr_done.emit(r.json().get("text", ""))
                    return
                detail = ""
                try:
                    detail = r.json().get("detail", "")
                except Exception:
                    pass
                self._asr_failed.emit(detail or f"HTTP {r.status_code}")
            except Exception as e:
                self._asr_failed.emit(str(e))
        threading.Thread(target=worker, daemon=True).start()

    def _on_asr_done(self, text: str):
        self.btn_record.setEnabled(True)
        text = (text or "").strip()
        if not text:
            self._on_asr_failed("识别结果为空")
            return
        current = self.qa_input.text().strip()
        self.qa_input.setText(f"{current} {text}".strip())
        self.qa_input.setFocus()
        self.status_label.setText("语音转写完成：确认或编辑后按回车发送")

    def _on_asr_failed(self, message: str):
        self.btn_record.setEnabled(True)
        self.status_label.setText(f"语音识别失败：{message}")

    # ---------- 历史记录 ----------

    def _load_history(self):
        def worker():
            try:
                r = requests.get(f"{config.BACKEND_HTTP}/history",
                                 params={"limit": 30}, timeout=5)
                self._history_loaded.emit(r.json().get("records", []))
            except Exception:
                self._history_loaded.emit([])
        threading.Thread(target=worker, daemon=True).start()

    def _on_history_loaded(self, records: list):
        self._history_records = records
        self.history_list.clear()
        if not records:
            item = QListWidgetItem("暂无历史记录")
            item.setFlags(Qt.NoItemFlags)
            self.history_list.addItem(item)
            return
        for rec in records:
            created = str(rec.get("created_at", ""))[:16]
            name = cn_name(rec.get("object_name") or "")
            q = (rec.get("question") or "").strip().replace("\n", " ")
            preview = q[:14] + ("…" if len(q) > 14 else "")
            item = QListWidgetItem(f"{created}  {name}  {preview}")
            item.setToolTip(f"问：{q}\n答：{(rec.get('answer') or '')[:200]}")
            self.history_list.addItem(item)

    def _on_history_item_clicked(self, item):
        idx = self.history_list.row(item)
        if not (0 <= idx < len(self._history_records)):
            return
        rec = self._history_records[idx]
        path = rec.get("image_path")
        if not path:
            self.hist_image_label.setText("该记录无截图")
            self.hist_image_label.setPixmap(QPixmap())
            return
        url = f"{config.BACKEND_HTTP}/{path.lstrip('/').replace(chr(92), '/')}"

        def worker(row=idx, u=url):
            try:
                r = requests.get(u, timeout=5)
                pix = None
                if r.ok:
                    p = QPixmap()
                    pix = p if p.loadFromData(r.content) else None
                self._history_image.emit(row, pix)
            except Exception:
                self._history_image.emit(row, None)
        threading.Thread(target=worker, daemon=True).start()

    def _on_history_image(self, row: int, pixmap):
        if self.history_list.currentRow() != row:
            return   # 用户已切换选中项
        if pixmap is None:
            self.hist_image_label.setText("截图加载失败")
            self.hist_image_label.setPixmap(QPixmap())
            return
        self.hist_image_label.setPixmap(
            pixmap.scaled(self.hist_image_label.size(), Qt.KeepAspectRatio,
                          Qt.SmoothTransformation))

    # ---------- 退出 ----------

    def closeEvent(self, event):
        if self._recording:
            self._recorder.cancel()
            if self._phone_rec:
                self._phone_rec.cancel()
            self._recording = False
        if self.is_running:
            self.stop_detection()
        event.accept()
