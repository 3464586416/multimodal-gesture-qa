"""mjpeg_source 单元测试：JPEG 帧扫描 + 地址纠错/校验（无需网络）。"""
import os
import sys

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))

from mjpeg_source import (  # noqa: E402
    MjpegError,
    MjpegSource,
    iter_jpeg_frames,
    normalize_stream_url,
    validate_stream_url,
)


def _jpeg(color):
    img = np.zeros((40, 60, 3), np.uint8)
    img[:, :] = color
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


def _chunk(data, size=7):
    return (data[i:i + size] for i in range(0, len(data), size))


class TestIterJpegFrames:
    def test_two_frames_multipart(self):
        j1, j2 = _jpeg((0, 0, 255)), _jpeg((255, 0, 0))
        stream = (b"--bnd\r\nContent-Type: image/jpeg\r\n\r\n" + j1
                  + b"\r\n--bnd\r\nContent-Type: image/jpeg\r\n\r\n" + j2
                  + b"\r\n--bnd--")
        frames = list(iter_jpeg_frames(_chunk(stream)))
        assert len(frames) == 2
        assert frames[0][20, 30][2] > 200          # 第一帧偏红(BGR 的 R 通道)
        assert frames[1][20, 30][2] < 50           # 第二帧不偏红

    def test_ignores_garbage_prefix_and_tails(self):
        j1 = _jpeg((0, 255, 0))
        stream = b"HTTP/1.1 200 OK\r\nbroken-boundary-stuff\xff\xfedeadbeef" + j1 + b"\r\n--x--"
        frames = list(iter_jpeg_frames(_chunk(stream)))
        assert len(frames) == 1

    def test_frame_split_across_many_chunks(self):
        j1 = _jpeg((0, 0, 255))
        frames = list(iter_jpeg_frames(_chunk(j1, size=3)))  # 3 字节一切
        assert len(frames) == 1
        assert frames[0].shape == (40, 60, 3)

    def test_truncated_frame_not_yielded(self):
        j1 = _jpeg((0, 0, 255))
        frames = list(iter_jpeg_frames(_chunk(j1[:len(j1) // 2])))
        assert frames == []


class TestNormalizeStreamUrl:
    def test_adds_missing_scheme(self):
        assert normalize_stream_url("10.0.0.5:8081/video") == "http://10.0.0.5:8081/video"

    def test_strips_adb_debug_port(self):
        # 用户把 adb devices 的 15555 调试端口也粘进来了
        bad = "http://10.33.31.139:15555:8081/video"
        assert normalize_stream_url(bad) == "http://10.33.31.139:8081/video"

    def test_localhost_double_port(self):
        assert normalize_stream_url("http://localhost:15555:8080/video") == "http://localhost:8080/video"

    def test_already_valid_unchanged(self):
        u = "http://localhost:8081/video"
        assert normalize_stream_url(u) == u

    def test_strips_whitespace(self):
        assert normalize_stream_url("  http://x:80/video  ") == "http://x:80/video"


class TestValidateStreamUrl:
    def test_valid_http(self):
        assert validate_stream_url("http://10.33.31.139:8081/video") is None

    def test_valid_localhost(self):
        assert validate_stream_url("http://localhost:8080/video") is None

    def test_rejects_non_http_scheme(self):
        assert validate_stream_url("ftp://a:8081/video") is not None

    def test_rejects_missing_host(self):
        assert validate_stream_url("http://") is not None

    def test_rejects_adb_port_as_stream_port(self):
        # 直接拿调试端口 15555 当视频端口 -> 给出纠正提示
        assert "15555" in (validate_stream_url("http://10.33.31.139:15555/video") or "")


class TestMjpegSourceFastFail:
    def test_invalid_url_raises_immediately(self):
        # 非法主机（空 host）应在首次 next() 抛 MjpegError，而不是无限重连
        src = MjpegSource("http://", max_attempts=1)
        gen = src.frames()
        with pytest.raises(MjpegError):
            next(gen)

    def test_double_port_url_normalized_before_request(self):
        # 纠正逻辑发生在发请求之前：非法到无法纠正才抛，能纠正的走网络(此处不断言网络结果)
        src = MjpegSource("http://127.0.0.1:9:9:9/bad", max_attempts=1)
        with pytest.raises(MjpegError):
            next(src.frames())
