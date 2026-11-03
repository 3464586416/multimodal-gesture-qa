"""phone_mic 纯函数测试（合成字节，无需手机/网络）。"""
import io
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))

from phone_mic import (  # noqa: E402
    audio_url_for,
    finalize_wav_stream,
    pcm_bytes_to_wav,
)


def _stream_header(riff_size, data_size, rate=44100, ch=1, bits=16):
    return (b"RIFF" + struct.pack("<I", riff_size) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, ch, rate,
                          rate * ch * bits // 8, ch * bits // 8, bits)
            + b"data" + struct.pack("<I", data_size))


class TestAudioUrlFor:
    def test_from_video_url(self):
        assert (audio_url_for("http://10.33.31.139:8081/video", "/mic.mp3")
                == "http://10.33.31.139:8081/mic.mp3")

    def test_localhost_forward(self):
        assert (audio_url_for("http://localhost:8081/video", "/audiofeed")
                == "http://localhost:8081/audiofeed")

    def test_keeps_port(self):
        assert audio_url_for("http://a.b.c.d:9999/x", "/mic.mp3").endswith(
            "a.b.c.d:9999/mic.mp3")


class TestPcmToWav:
    def test_wraps_header(self):
        pcm = b"\x00\x01" * 1600
        out = pcm_bytes_to_wav(pcm, 44100)
        with wave.open(io.BytesIO(out)) as wf:
            assert wf.getframerate() == 44100
            assert wf.getnframes() == 1600
            assert wf.getsampwidth() == 2


class TestFinalizeWavStream:
    def test_streaming_header_rebuilt_with_real_sizes(self):
        """App 的 0xFFFFFFFF 无限流头 -> 重建为长度真实的标准 WAV。"""
        pcm = b"\x01\x02" * 800
        raw = _stream_header(0xFFFFFFFF, 0xFFFFFFFF) + pcm
        out = finalize_wav_stream(raw)
        with wave.open(io.BytesIO(out)) as wf:
            assert wf.getnframes() == 800
            assert wf.getframerate() == 44100
            assert wf.getnchannels() == 1
        assert out[out.find(b"data") + 8:] == pcm

    def test_stereo_48k_preserved(self):
        pcm = b"\x00\x01\x02\x03" * 250   # 250 个双声道采样帧 = 1000 字节
        raw = _stream_header(0xFFFFFFFF, 0xFFFFFFFF, rate=48000, ch=2) + pcm
        out = finalize_wav_stream(raw)
        with wave.open(io.BytesIO(out)) as wf:
            assert wf.getframerate() == 48000
            assert wf.getnchannels() == 2
            assert wf.getnframes() == 250

    def test_headerless_pcm_wrapped(self):
        out = finalize_wav_stream(b"\x00\x01" * 100)
        with wave.open(io.BytesIO(out)) as wf:
            assert wf.getnframes() == 100

    def test_complete_wav_passthrough(self):
        pcm = b"\x03\x04" * 200
        raw = _stream_header(36 + len(pcm), len(pcm)) + pcm
        assert finalize_wav_stream(raw) == raw
