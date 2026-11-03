"""手机麦克风录音：拉取 IP Webcam 的音频流，复用语音提问链路。

手机画面与声音共用同一 IP Webcam 服务（视频 :8081/video，音频 /mic.mp3）。
录音线程后台攒块，stop() 返回 (bytes, format) 交给 /asr——MP3 直接上传
（Qwen-omni 原生支持 mp3），/audiofeed(PCM) 作为备选自动封装 WAV。
"""
import io
import logging
import struct
import threading
import wave
from urllib.parse import urlparse

import requests

logger = logging.getLogger("phone_mic")

# 端点优先级：/mic.mp3（经典 IP Webcam）-> /audio.wav（hit-mob 版，单头无限流）
# -> /audiofeed（老版 multipart PCM）
AUDIO_ENDPOINTS = [("/mic.mp3", "mp3"), ("/audio.wav", "wav"), ("/audiofeed", "wav")]


def audio_url_for(video_url: str, path: str) -> str:
    """从视频流地址推导音频端点：http://ip:8081/video -> http://ip:8081/mic.mp3"""
    p = urlparse(video_url)
    return f"{p.scheme}://{p.netloc}{path}"


def pcm_bytes_to_wav(pcm: bytes, samplerate: int = 44100,
                     channels: int = 1, bits: int = 16) -> bytes:
    """裸 PCM 补标准 WAV 头（纯函数，可单测）。"""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(bits // 8)
        wf.setframerate(samplerate)
        wf.writeframes(pcm)
    return buf.getvalue()


def finalize_wav_stream(raw: bytes) -> bytes:
    """
    把 App 的"单 RIFF 头 + 无限 PCM"流式 WAV（size 字段恒为 0xFFFFFFFF/0）
    重建为长度真实的标准 WAV。无头 PCM 直接封装；已是完整 WAV 原样返回。
    """
    if raw[:4] != b"RIFF":
        return pcm_bytes_to_wav(raw)
    try:
        riff_size = struct.unpack("<I", raw[4:8])[0]
    except struct.error:
        return raw
    if riff_size not in (0, 0xFFFFFFFF) and len(raw) >= riff_size + 8:
        return raw                       # 头部声明的字节真在流里 -> 已是完整 WAV
    i = raw.find(b"data", 12, 256)       # 定位 data 子块
    if i < 0:
        return raw
    pcm = raw[i + 8:]
    if len(pcm) < 2:
        return pcm_bytes_to_wav(b"")
    channels = struct.unpack("<H", raw[22:24])[0] or 1
    rate = struct.unpack("<I", raw[24:28])[0] or 44100
    bits = struct.unpack("<H", raw[34:36])[0] or 16
    return pcm_bytes_to_wav(pcm, rate, channels, bits)


class PhoneMicRecorder:
    """start() -> stop() 返回 (音频字节, 格式)。设备侧未开音频时给出明确指引。"""

    def __init__(self, video_url: str):
        self.video_url = video_url
        self._session = requests.Session()
        self._resp = None
        self._thread = None
        self._fmt = "mp3"
        self._chunks = []
        self._lock = threading.Lock()
        self._stop_evt = threading.Event()

    @property
    def recording(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        """探测可用音频端点并开始攒流；都不可用抛 RuntimeError（含手机侧指引）。"""
        self._stop_evt.clear()
        with self._lock:
            self._chunks = []
        last_status = []
        for path, fmt in AUDIO_ENDPOINTS:
            url = audio_url_for(self.video_url, path)
            try:
                resp = self._session.get(url, stream=True, timeout=(5, 60))
            except requests.RequestException as e:
                last_status.append(f"{path}: {type(e).__name__}")
                continue
            ctype = resp.headers.get("content-type", "").lower()
            if resp.status_code == 200 and ("audio" in ctype or "mpeg" in ctype
                                            or "octet-stream" in ctype):
                resp.close()
                # 探测成功，重新开正式流
                self._resp = self._session.get(url, stream=True, timeout=(5, 120))
                self._fmt = fmt
                self._thread = threading.Thread(target=self._pump, daemon=True)
                self._thread.start()
                logger.info("手机麦克风已连接: %s (%s)", url, fmt)
                return
            resp.close()
            last_status.append(f"{path}: HTTP {resp.status_code} {ctype[:40]}")
        raise RuntimeError(
            "手机未提供音频流（已尝试 /mic.mp3、/audio.wav、/audiofeed）。请在手机上：\n"
            "1. IP Webcam 设置 → 勾选 Enable audio capture（部分版本在 "
            "Video and cameras 或 Audio settings 分组）\n"
            "2. 设置后必须 Stop server 再 Start server 才生效\n"
            f"（探测记录: {'; '.join(last_status)}）")

    def _pump(self):
        try:
            for chunk in self._resp.iter_content(chunk_size=16384):
                if self._stop_evt.is_set():
                    break
                if chunk:
                    with self._lock:
                        self._chunks.append(chunk)
        except Exception:
            pass   # 断流时保留已攒数据，stop() 照常返回

    def _teardown(self):
        self._stop_evt.set()
        if self._resp is not None:
            try:
                self._resp.close()
            except Exception:
                pass
            self._resp = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def stop(self):
        """返回 (bytes, format)。"""
        self._teardown()
        with self._lock:
            raw = b"".join(self._chunks)
            self._chunks = []
        fmt = self._fmt
        if fmt == "wav":
            raw = finalize_wav_stream(raw)
        return raw, fmt

    def cancel(self):
        self._teardown()
        with self._lock:
            self._chunks = []
