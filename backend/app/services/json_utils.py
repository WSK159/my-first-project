"""LLM 结构化输出解析：从任意文本中稳健提取 JSON。"""

import json
import logging
import re

logger = logging.getLogger(__name__)


def _strip_fence(text: str) -> str:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    return fence.group(1).strip() if fence else text


def _clean_jsonc(text: str) -> str:
    # 去掉行尾逗号、注释，处理单引号（轻量修复常见模型输出）
    text = re.sub(r",\s*([}\]])", r"\1", text)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def extract_json(text: str) -> dict:
    """返回 dict；解析失败返回空 dict 并记录原因。"""
    candidate = _strip_fence(text)
    for variant in (candidate, _clean_jsonc(candidate)):
        for start_ch, end_ch in (("{", "}"), ("[", "]")):
            start = variant.find(start_ch)
            end = variant.rfind(end_ch)
            if start >= 0 and end > start:
                try:
                    data = json.loads(variant[start : end + 1])
                    if isinstance(data, dict):
                        return data
                except json.JSONDecodeError as exc:
                    logger.debug("JSON 解析失败: %s", exc)
    logger.warning("无法从 LLM 输出中提取 JSON：%.200s", candidate)
    return {}


def dump_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)

