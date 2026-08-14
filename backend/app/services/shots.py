"""分镜/连续视频提示词生成：script → video-prompts.md（中文 + 英文）。"""

import logging
from pathlib import Path

from ..config import ROOT_DIR
from . import mock_content
from .json_utils import dump_json, extract_json
from .llm import complete
from .project_store import to_markdown, write_text

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = Path(ROOT_DIR / "pipeline" / "prompts" / "shot_prompts.md").read_text(encoding="utf-8")


def _build_prompt(script: dict, characters: dict) -> str:
    return (
        PROMPT_TEMPLATE
        + "\n\n## 本次任务\n剧本：\n"
        + dump_json(script)
        + "\n角色：\n"
        + dump_json(characters)
        + "\n请只输出一个合法 JSON 对象（不要输出 Markdown 或解释文字）。"
    )


def _translate(shots: dict) -> dict:
    """生成英文适配版（结构复制，文案简译）。"""
    import json

    en = json.loads(json.dumps(shots))
    for clip in en.get("clips", []):
        clip["timeline_beats"] = [f"Beat {i+1}: same visual intent" for i in range(len(clip["timeline_beats"]))]
        clip["negative"] = ["text watermark", "extra people"]
    return en


def generate_shots(project_id: int, script: dict, characters: dict, episode: int) -> dict:
    from ..config import settings

    if settings.llm_provider == "mock":
        shots = mock_content.make_shots(script, characters)
    else:
        shots = extract_json(complete(_build_prompt(script, characters), temperature=0.85))
        if not shots or "clips" not in shots:
            raise RuntimeError(f"第{episode}集分镜提示词生成失败")
    rel = f"episodes/ep{episode:03d}/"
    write_text(project_id, rel + "video-prompts.md", to_markdown(f"第{episode}集 视频提示词", shots))
    en = _translate(shots)
    write_text(project_id, rel + "video-prompts-en.md", to_markdown(f"Episode {episode} Video Prompts", en))
    return shots

