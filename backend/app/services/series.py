"""系列设定生成：一句话/随机 → series.md + series.json。"""

import logging
from pathlib import Path

from ..config import ROOT_DIR
from . import mock_content
from .json_utils import dump_json, extract_json
from .llm import complete
from .project_store import to_markdown, write_json, write_text

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = Path(ROOT_DIR / "pipeline" / "prompts" / "series.md").read_text(encoding="utf-8")


def _build_prompt(idea: str, random_mode: bool, genre: str, episode_count: int) -> str:
    mode = "完全随机模式：请自行选择题材并生成一个完整的原创短剧系列设定。" if random_mode else "根据用户的一句话灵感扩展。"
    return (
        PROMPT_TEMPLATE
        + f"\n\n## 本次任务\n模式：{mode}\n一句话灵感：{idea or '（无，随机生成）'}\n"
        + f"题材（可选，留空则由你决定）：{genre}\n集数：{episode_count}\n"
        + "请只输出一个合法 JSON 对象（不要输出 Markdown 或解释文字）。"
    )


def generate_series(
    project_id: int,
    idea: str = "",
    random_mode: bool = False,
    genre: str = "",
    episode_count: int = 1,
    user_id: int | None = None,
) -> dict:
    """返回 series 字典，并写入 series.json / series.md。"""
    from ..config import settings

    if settings.llm_provider == "mock" or random_mode:
        series = mock_content.make_series(idea, genre, episode_count)
    else:
        series = extract_json(complete(_build_prompt(idea, random_mode, genre, episode_count), temperature=0.85, user_id=user_id))
        if not series:
            raise RuntimeError("系列设定生成失败：LLM 输出无法解析")
    write_json(project_id, "series.json", series)
    write_text(project_id, "series.md", to_markdown(series.get("title", "系列设定"), series))
    return series
