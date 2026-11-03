"""麦克风录音与 /asr 端点的离线测试。"""
import io
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from mic_capture import int16_chunks_to_wav  # noqa: E402


class TestWavAssembly:
    def test_params_and_frames(self):
        c1 = (np.arange(1600, dtype=np.int16))
        c2 = (np.arange(800, dtype=np.int16)) + 100
        wav_bytes = int16_chunks_to_wav([c1, c2], 16000, 1)
        with wave.open(io.BytesIO(wav_bytes)) as wf:
            assert wf.getframerate() == 16000
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getnframes() == 2400
            data = np.frombuffer(wf.readframes(2400), np.int16)
        np.testing.assert_array_equal(data[:1600], c1)
        np.testing.assert_array_equal(data[1600:], c2)

    def test_raw_bytes_chunks_accepted(self):
        raw = (np.arange(100, dtype=np.int16)).tobytes()
        wav_bytes = int16_chunks_to_wav([raw], 16000)
        with wave.open(io.BytesIO(wav_bytes)) as wf:
            assert wf.getnframes() == 100

    def test_empty_still_valid_wav(self):
        wav_bytes = int16_chunks_to_wav([], 16000)
        with wave.open(io.BytesIO(wav_bytes)) as wf:
            assert wf.getnframes() == 0


class TestAsrEndpoint:
    """用假 LLM 验证 /asr 的校验与转发逻辑（不真实调用 API）。"""

    class FakeLLM:
        def __init__(self, fail=False):
            self.fail = fail
        def transcribe_audio(self, data, fmt="wav"):
            if self.fail:
                raise RuntimeError("模拟识别故障")
            return f"识别({len(data)}B,{fmt})"

    def _client(self, fake):
        from fastapi.testclient import TestClient
        import app as app_module
        client = TestClient(app_module.app)   # 不进 with -> 不跑 lifespan，轻量
        app_module.app.state.llm = fake
        return client

    def test_success(self):
        client = self._client(self.FakeLLM())
        r = client.post("/asr", files={"file": ("q.wav", b"x" * 1000, "audio/wav")})
        assert r.status_code == 200
        assert "1000B,wav" in r.json()["text"]

    def test_mp3_format_detected_by_filename(self):
        client = self._client(self.FakeLLM())
        r = client.post("/asr", files={"file": ("q.mp3", b"x" * 10, "audio/mpeg")})
        assert "mp3" in r.json()["text"]

    def test_empty_audio_rejected(self):
        client = self._client(self.FakeLLM())
        r = client.post("/asr", files={"file": ("q.wav", b"", "audio/wav")})
        assert r.status_code == 400

    def test_oversize_rejected(self):
        client = self._client(self.FakeLLM())
        big = b"z" * (11 * 1024 * 1024)
        r = client.post("/asr", files={"file": ("q.wav", big, "audio/wav")})
        assert r.status_code == 413

    def test_llm_failure_maps_to_502(self):
        client = self._client(self.FakeLLM(fail=True))
        r = client.post("/asr", files={"file": ("q.wav", b"x" * 10, "audio/wav")})
        assert r.status_code == 502
