"""角色设定生成：series → characters.md + characters.json。"""

import logging
from pathlib import Path

from ..config import ROOT_DIR
from . import mock_content
from .json_utils import dump_json, extract_json
from .llm import complete
from .project_store import to_markdown, write_json, write_text

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = Path(ROOT_DIR / "pipeline" / "prompts" / "characters.md").read_text(encoding="utf-8")


def _build_prompt(series: dict) -> str:
    return (
        PROMPT_TEMPLATE
        + "\n\n## 本次任务\n系列设定如下：\n"
        + dump_json(series)
        + "\n请只输出一个合法 JSON 对象（不要输出 Markdown 或解释文字）。"
    )


def generate_characters(project_id: int, series: dict, user_id: int | None = None) -> dict:
    from ..config import settings

    if settings.llm_provider == "mock":
        characters = mock_content.make_characters(series)
    else:
        characters = extract_json(complete(_build_prompt(series), temperature=0.85, user_id=user_id))
        if not characters or "characters" not in characters:
            raise RuntimeError("角色设定生成失败：LLM 输出无法解析")
    write_json(project_id, "characters.json", characters)
    write_text(project_id, "characters.md", to_markdown("角色设定", characters))
    return characters
