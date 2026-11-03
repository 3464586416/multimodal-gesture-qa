"""麦克风录音（sounddevice / PortAudio）。

用途：语音输入提问 —— 手动开关 + 点击开始/停止，产出标准 WAV 字节，
POST 到后端 /asr 转写为文本填入输入框（可编辑后再发送）。

设计：
- 默认尝试 16kHz 单声道（ASR 友好、体积小），设备不支持则退回默认采样率；
- 录音在 sounddevice 回调线程里只做"塞缓冲"，主线程停止时统一编码；
- int16_chunks_to_wav 为纯函数，可离线单元测试。
"""
import io
import logging
import threading
import wave

import numpy as np

logger = logging.getLogger("mic")


def int16_chunks_to_wav(chunks, samplerate: int, channels: int = 1) -> bytes:
    """把若干 int16 numpy 数组/bytes 拼接编码为 PCM WAV 字节。"""
    if len(chunks) == 0:
        data = np.zeros(0, dtype=np.int16)
    else:
        parts = [c if isinstance(c, np.ndarray) else np.frombuffer(c, np.int16)
                 for c in chunks]
        data = np.concatenate(parts).astype(np.int16, copy=False)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(int(samplerate))
        wf.writeframes(data.tobytes())
    return buf.getvalue()


class MicRecorder:
    """按需开关的麦克风录音器：start() -> stop() 返回 WAV 字节。"""

    PREFERRED_RATE = 16000

    def __init__(self):
        self._stream = None
        self._chunks = []
        self._lock = threading.Lock()
        self.samplerate = self.PREFERRED_RATE
        self.channels = 1

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def start(self):
        """打开输入流开始录音；失败抛 RuntimeError（无麦克风/被占用）。"""
        if self._stream is not None:
            return
        import sounddevice as sd
        with self._lock:
            self._chunks = []
        last_err = None
        for rate in (self.PREFERRED_RATE, 44100, 48000):
            try:
                self._stream = sd.InputStream(
                    samplerate=rate, channels=1, dtype="int16",
                    callback=self._callback)
                self._stream.start()
                self.samplerate = rate
                logger.info("麦克风已开启: %s Hz 单声道", rate)
                return
            except Exception as e:      # 采样率不支持/设备占用 -> 试下一个
                last_err = e
                self._stream = None
        raise RuntimeError(f"无法打开麦克风：{last_err}")

    def _callback(self, indata, frames, time_info, status):
        # 回调线程：仅做数据搬运
        with self._lock:
            self._chunks.append(indata.copy())

    def stop(self) -> bytes:
        """停止录音并返回 WAV 字节。"""
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                logger.debug("关闭录音流异常", exc_info=True)
        with self._lock:
            chunks, self._chunks = self._chunks, []
        return int16_chunks_to_wav(chunks, self.samplerate, self.channels)

    def cancel(self):
        """停止并丢弃本次录音（不编码）。"""
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        with self._lock:
            self._chunks = []

    @staticmethod
    def list_input_devices():
        import sounddevice as sd
        return [(i, d.get("name", "?")) for i, d in enumerate(sd.query_devices())
                if d.get("max_input_channels", 0) > 0]
