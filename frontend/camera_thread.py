"""摄像头/视频帧采集与 WebSocket 通信线程。

改进点（相对旧 frontend/main.py 内嵌版本）：
- latest_frame 读写加锁（旧实现主线程裁剪与采集线程写入无同步竞争）；
- QImage 构造后立即 .copy()，避免 numpy 缓冲区被 GC 导致花屏/崩溃；
- 帧率、JPEG 质量从 config 读取；
- 叠加绘制委托 overlay.draw_overlay（纯函数，可单测）；
- 确认阈值用后端返回值，不再硬编码 /3。
"""
import json
import threading
import time

import cv2
import websocket
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

import config
import overlay
from mjpeg_source import MjpegError, MjpegSource, normalize_stream_url


def _is_http_url(path) -> bool:
    return isinstance(path, str) and path.lower().startswith(("http://", "https://"))


class CameraThread(QThread):
    """采集视频源 -> 发送帧到后端 -> 接收检测结果 -> 绘制叠加层输出画面"""

    frame_ready = pyqtSignal(QImage)
    detection_result = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    status_changed = pyqtSignal(str)
    reset_confirmed = pyqtSignal()

    def __init__(self, source_type="camera", video_path=None, parent=None):
        super().__init__(parent)
        self.source_type = source_type
        if source_type == "video" and _is_http_url(video_path):
            video_path = normalize_stream_url(video_path)   # 纠正 15555:8081 之类的双端口
        self.video_path = video_path
        self.running = False
        self.cap = None
        self.ws = None
        self._frame_lock = threading.Lock()
        self._latest_frame = None
        self._result_lock = threading.Lock()
        self._latest_result = {}
        self._receiver_thread = None
        self._stream = None       # HTTP MJPEG 源（手机摄像头）

    # ---------- 对主线程暴露的安全访问 ----------

    def get_current_frame(self):
        """返回当前帧副本（线程安全），无帧时返回 None。"""
        with self._frame_lock:
            return None if self._latest_frame is None else self._latest_frame.copy()

    # ---------- 内部 ----------

    def _receiver_method(self):
        """独立线程持续接收后端结果。"""
        while self.running and self.ws:
            try:
                result = self.ws.recv()
                result_data = json.loads(result)
                with self._result_lock:
                    self._latest_result = result_data
                if result_data.get("type") == "reset_confirmed":
                    self.reset_confirmed.emit()
                else:
                    self.detection_result.emit(result_data)
            except websocket.WebSocketTimeoutException:
                continue
            except Exception:
                break

    def run(self):
        self.running = True

        is_http = _is_http_url(self.video_path)
        frame_iter = None
        if is_http:
            # HTTP MJPEG（手机 IP Webcam）：自研解析器，绕开 FFmpeg 兼容坑
            self._stream = MjpegSource(
                self.video_path,
                on_reconnect=lambda: self.status_changed.emit("手机摄像头流已重连"))
            frame_iter = self._stream.frames()
        else:
            if self.source_type == "camera":
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            else:
                self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                self.error_occurred.emit("无法打开视频源")
                return
        self.status_changed.emit("已连接视频源")

        try:
            self.ws = websocket.create_connection(
                config.BACKEND_WS, timeout=config.WS_TIMEOUT,
                enable_multithread=True)
            self.status_changed.emit("已连接后端服务")
        except Exception as e:
            self.error_occurred.emit(f"无法连接后端: {e}")
            self.cap.release()
            return

        self._receiver_thread = threading.Thread(
            target=self._receiver_method, daemon=True)
        self._receiver_thread.start()

        frame_interval = 1.0 / max(1, config.TARGET_FPS)
        skip_frames = 3 if is_http else 2

        while self.running:
            start = time.time()

            if is_http:
                # 丢弃积压旧帧压低延迟；网络性断流由生成器内部自动重连
                try:
                    for _ in range(skip_frames):
                        if next(frame_iter, None) is None:
                            break
                    frame = next(frame_iter, None)
                except MjpegError as e:
                    # 永久性错误（地址非法/连续重连失败）：明确报错并退出，不刷日志
                    self.error_occurred.emit(str(e))
                    break
                if frame is None:
                    if not self.running:
                        break
                    time.sleep(0.3)
                    continue
            else:
                for _ in range(skip_frames):
                    self.cap.grab()
                ret, frame = self.cap.read()
                if not ret:
                    if self.source_type == "video":
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # 本地视频循环
                    continue

            if frame.ndim != 3 or frame.shape[2] != 3:
                continue

            with self._frame_lock:
                self._latest_frame = frame

            _, buffer = cv2.imencode(
                '.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, config.FRAME_JPEG_QUALITY])
            ws = self.ws
            if ws and self._receiver_thread and self._receiver_thread.is_alive():
                try:
                    ws.send_binary(buffer.tobytes())
                except Exception:
                    self._reconnect()
            else:
                self._reconnect()

            with self._result_lock:
                current_result = dict(self._latest_result)
            display = overlay.draw_overlay(frame, current_result)

            rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            # .copy(): 让 QImage 拥有独立内存，rgb 离开作用域后不会花屏
            q_img = QImage(rgb.data, w, h, ch * w,
                           QImage.Format_RGB888).copy()
            self.frame_ready.emit(q_img)

            elapsed = time.time() - start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        self._cleanup()

    def _reconnect(self):
        """重连 WebSocket（带防抖延迟）。"""
        old_ws = self.ws
        self.ws = None
        if self._receiver_thread and self._receiver_thread.is_alive():
            self._receiver_thread.join(timeout=2)
        try:
            if old_ws:
                old_ws.close()
        except Exception:
            pass

        time.sleep(0.5)
        try:
            self.ws = websocket.create_connection(
                config.BACKEND_WS, timeout=config.WS_TIMEOUT,
                enable_multithread=True)
            self._receiver_thread = threading.Thread(
                target=self._receiver_method, daemon=True)
            self._receiver_thread.start()
            self.status_changed.emit("已重连后端服务")
        except Exception:
            pass

    def send_reset(self):
        """发送重置指令（不断开连接）。"""
        try:
            if self.ws:
                self.ws.send_text(json.dumps({"type": "reset"}))
        except Exception:
            pass

    def _cleanup(self):
        self.running = False
        if self._stream:
            self._stream.stop()
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None
        if self._receiver_thread and self._receiver_thread.is_alive():
            self._receiver_thread.join(timeout=2)
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass

    def stop(self):
        self.running = False
        if self._stream:
            self._stream.stop()
