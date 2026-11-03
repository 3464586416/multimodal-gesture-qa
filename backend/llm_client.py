"""阿里云 DashScope 多模态大模型客户端（OpenAI 兼容模式）。

改进点：失败时抛出 LLMError 而不是把错误文案伪装成正常回答返回，
调用方（/qa）可以把错误作为结构化事件通知前端。
"""
import base64
import json
import logging
from typing import Generator

import cv2
import numpy as np
import os
import requests

logger = logging.getLogger("llm")

CONNECT_TIMEOUT = float(os.getenv("LLM_CONNECT_TIMEOUT", "10"))
READ_TIMEOUT = float(os.getenv("LLM_READ_TIMEOUT", "120"))


class LLMError(RuntimeError):
    """大模型调用失败"""


class LLMClient:
    """阿里云 DashScope 多模态大模型客户端"""

    def __init__(self, api_key: str, model: str = "qwen3.5-omni-plus",
                 base_url: str = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url or os.getenv(
            "DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def ask(self, question: str, image: np.ndarray = None) -> str:
        """向多模态模型提问（非流式，收集全部片段）"""
        return "".join(self.ask_stream(question, image))

    def transcribe_audio(self, audio_bytes: bytes,
                         audio_format: str = "wav") -> str:
        """
        语音转文字（ASR）：复用 Qwen-omni 的多模态输入能力，
        无需引入第二个 API/SDK。omni 要求 stream=True + modalities=['text']。
        失败抛 LLMError。
        """
        url = f"{self.base_url}/chat/completions"
        # DashScope 兼容模式的 omni 音频输入要求 data URL 形式（实测纯 base64 会被当 URL 校验而报错）
        mime = {"wav": "wav", "mp3": "mpeg", "m4a": "mp4", "aac": "aac",
                "ogg": "ogg", "opus": "ogg", "flac": "flac"}.get(audio_format, "wav")
        audio_uri = f"data:audio/{mime};base64,{base64.b64encode(audio_bytes).decode('utf-8')}"
        payload = {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "input_audio",
                     "input_audio": {"data": audio_uri, "format": audio_format}},
                    {"type": "text", "text":
                     "请把这段语音转写为文本。只输出转写内容本身，"
                     "不要任何解释、引号或前后缀。"},
                ],
            }],
            "modalities": ["text"],
            "max_tokens": 500,
            "temperature": 0.0,
            "stream": True,
        }
        try:
            resp = requests.post(url, json=payload, headers=self.headers,
                                 timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                                 stream=True)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise LLMError(f"语音识别 API 调用失败: {e}") from e

        parts = []
        for line in resp.iter_lines():
            if not line:
                continue
            line = line.decode('utf-8', errors='replace')
            if not line.startswith('data: '):
                continue
            data = line[6:]
            if data == '[DONE]':
                break
            try:
                chunk = json.loads(data)
                delta = chunk['choices'][0].get('delta', {})
                text = delta.get('content')
            except (json.JSONDecodeError, KeyError, IndexError):
                continue
            if text:
                parts.append(text)
        result = "".join(parts).strip()
        if not result:
            raise LLMError("未识别到语音内容（可能太短或太安静）")
        return result

    def ask_stream(self, question: str,
                   image: np.ndarray = None) -> Generator[str, None, None]:
        """
        流式提问，逐段 yield 文本。
        出错时抛出 LLMError（旧实现会把错误文案当正常回答 yield 给前端）。
        """
        url = f"{self.base_url}/chat/completions"

        content = [{"type": "text", "text": question}]
        if image is not None:
            ok, buffer = cv2.imencode('.jpg', image,
                                       [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ok:
                raise LLMError("物品截图编码失败")
            img_b64 = base64.b64encode(buffer).decode('utf-8')
            content.insert(0, {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
            })

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 2000,
            "temperature": 0.7,
            "stream": True,
        }

        try:
            resp = requests.post(url, json=payload, headers=self.headers,
                                 timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                                 stream=True)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise LLMError(f"API 调用失败: {e}") from e

        for line in resp.iter_lines():
            if not line:
                continue
            line = line.decode('utf-8', errors='replace')
            if not line.startswith('data: '):
                continue
            data = line[6:]
            if data == '[DONE]':
                break
            try:
                chunk = json.loads(data)
                delta = chunk['choices'][0].get('delta', {})
                text = delta.get('content')
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logger.warning("SSE 片段解析失败: %s", e)
                continue
            if text:
                yield text
