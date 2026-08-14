"""60 集大纲先行：系列设定 → 全剧大纲表（每集钩子/冲突/反转/结尾钩子），保证长剧连贯。"""

import logging
from pathlib import Path

from ..config import ROOT_DIR
from . import mock_content
from .json_utils import dump_json, extract_json
from .llm import complete
from .project_store import to_markdown, write_json, write_text

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = Path(ROOT_DIR / "pipeline" / "prompts" / "outline.md").read_text(encoding="utf-8")


def _build_prompt(series: dict, characters: dict, episode_count: int) -> str:
    return (
        PROMPT_TEMPLATE
        + "\n\n## 本次任务\n集数：" 
        + str(episode_count)
        + "。\n系列设定：\n"
        + dump_json(series)
        + "\n角色设定：\n"
        + dump_json(characters)
        + "\n请只输出一个合法 JSON 对象（不要输出 Markdown 或解释文字）。"
    )


def generate_outline(
    project_id: int, series: dict, characters: dict, episode_count: int, user_id: int | None = None
) -> dict:
    """生成 outline.json / outline.md。返回 {episodes: [ {episode, hook, conflict, escalation, reversal, ending_hook, locations} ]}。"""
    from ..config import settings

    if settings.llm_provider == "mock":
        outline = mock_content.make_outline(series, characters, episode_count)
    else:
        outline = extract_json(complete(_build_prompt(series, characters, episode_count), temperature=0.9, user_id=user_id))
        if not outline or "episodes" not in outline:
            raise RuntimeError("大纲生成失败：LLM 输出无法解析")
        if len(outline["episodes"]) != episode_count:
            # 容错：补齐/截断到目标集数
            rows = outline["episodes"]
            if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                first = rows[0]
                if len(rows) < episode_count:
                    for i in range(len(rows) + 1, episode_count + 1):
                        rows.append({**first, "episode": i, "hook": f"第{i}集：剧情持续推进", "ending_hook": "悬念升级"})
                outline["episodes"] = rows[:episode_count]
            else:
                raise RuntimeError("大纲格式错误：episodes 应为对象数组")
    write_json(project_id, "outline.json", outline)
    write_text(project_id, "outline.md", to_markdown(f"{series.get('title', '')} 全剧大纲", outline))
    return outline
