"""LLM 适配层：mock | deepseek | openai 一键切换。"""

import json
import logging
from typing import Iterable

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


class MockLLM:
    """离线 mock：按模板返回占位内容，保证无 key 也能跑通流程。"""

    def complete(self, messages: Iterable[dict], temperature: float = 0.8) -> str:
        text = json.dumps(list(messages), ensure_ascii=False)
        return (
            "【mock 内容】收到请求：\n"
            + text[:500]
            + "\n\n请配置 DEEPSEEK_API_KEY / OPENAI_API_KEY 后切换 LLM_PROVIDER 获取真实内容。"
        )


class OpenAICompatLLM:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def complete(self, messages: Iterable[dict], temperature: float = 0.8) -> str:
        if not self.api_key:
            raise LLMError(f"未配置 {self.model} 的 API key")
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "messages": list(messages), "temperature": temperature},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


def get_llm():
    if settings.llm_provider == "deepseek":
        return OpenAICompatLLM(settings.deepseek_api_key, settings.deepseek_base_url, settings.deepseek_model)
    if settings.llm_provider == "openai":
        return OpenAICompatLLM(settings.openai_api_key, settings.openai_base_url, settings.openai_model)
    return MockLLM()


def complete(prompt: str, system: str = "你是一名专业短剧编剧与导演。", temperature: float = 0.8) -> str:
    return get_llm().complete(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )

