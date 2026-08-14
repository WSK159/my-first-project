"""完整小说生成：series + 各集剧本 → novel.md。"""

import logging
from pathlib import Path

from ..config import ROOT_DIR
from . import mock_content
from .json_utils import dump_json
from .llm import complete
from .project_store import write_text

logger = logging.getLogger(__name__)


def _build_prompt(series: dict, episodes: list[dict]) -> str:
    return (
        "你是短剧原著作者。请根据系列设定与各集剧本，写一部可以直接投稿的完整中文小说："
        "包含楔子、分章节（每集一章）、人物关系、完整情节与结尾悬念。要求文笔流畅、情绪饱满，总字数不少于 3000 字。\n\n"
        + "## 系列设定\n"
        + dump_json(series)
        + "\n## 各集剧本\n"
        + dump_json({"episodes": episodes})
    )


def generate_novel(project_id: int, series: dict, episodes: list[dict]) -> str:
    from ..config import settings

    if settings.llm_provider == "mock":
        novel = mock_content.make_novel(series, episodes)
    else:
        novel = complete(_build_prompt(series, episodes), temperature=0.9)
        if len(novel.strip()) < 500:
            raise RuntimeError("小说生成失败：内容过短")
    write_text(project_id, "novel.md", novel)
    return novel

