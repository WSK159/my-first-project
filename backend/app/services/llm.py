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
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        chat_path: str = "chat/completions",
        max_tokens: int | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.chat_path = chat_path.lstrip("/")
        self.max_tokens = max_tokens

    def complete(self, messages: Iterable[dict], temperature: float = 0.8) -> str:
        if not self.api_key:
            raise LLMError(f"未配置 {self.model} 的 API key")
        resp = httpx.post(
            f"{self.base_url}/{self.chat_path}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": list(messages),
                "temperature": temperature,
                **({"max_tokens": self.max_tokens} if self.max_tokens else {}),
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        base = data.get("base_resp") or {}
        if base.get("status_code", 0) not in (0, None, 200):
            raise LLMError(f"LLM 调用失败：{base.get('status_msg', base.get('status_code'))}")
        if "choices" in data:
            if not data["choices"]:
                raise LLMError(f"LLM 返回空 choices：{str(data)[:200]}")
            return data["choices"][0]["message"]["content"]
        if "output" in data and "choices" in data["output"]:
            return data["output"]["choices"][0]["message"]["content"]
        raise LLMError(f"响应缺少 choices：{str(data)[:200]}")


def get_llm(user_id: int | None = None):
    if user_id is not None:
        try:
            from . import keys

            user_key = keys.get_user_overrides(user_id).get("llm", "")
            if user_key:
                if settings.llm_provider == "minimax":
                    return OpenAICompatLLM(
                        user_key,
                        settings.minimax_base_url,
                        settings.minimax_chat_model,
                        chat_path="v1/text/chatcompletion_v2",
                        max_tokens=8192,
                    )
                return OpenAICompatLLM(user_key, settings.deepseek_base_url, settings.deepseek_model)
        except Exception:  # noqa: BLE001 密钥读取失败时回退平台配置
            logger.exception("读取用户 LLM Key 失败")
    if settings.llm_provider == "deepseek":
        return OpenAICompatLLM(settings.deepseek_api_key, settings.deepseek_base_url, settings.deepseek_model)
    if settings.llm_provider == "openai":
        return OpenAICompatLLM(settings.openai_api_key, settings.openai_base_url, settings.openai_model)
    if settings.llm_provider == "minimax":
        return OpenAICompatLLM(
            settings.minimax_api_key,
            settings.minimax_base_url,
            settings.minimax_chat_model,
            chat_path="v1/text/chatcompletion_v2",
            max_tokens=8192,
        )
    return MockLLM()


def complete(prompt: str, system: str = "你是一名专业短剧编剧与导演。", temperature: float = 0.8, user_id: int | None = None) -> str:
    return get_llm(user_id).complete(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )
