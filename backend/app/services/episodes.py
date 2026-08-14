"""分集内容生成：episode-card + 完整剧本 script。支持并行生成（性能优化）。"""

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ..config import ROOT_DIR, settings
from . import mock_content
from .json_utils import dump_json, extract_json
from .llm import complete
from .project_store import episode_dir, to_markdown, write_json, write_text

logger = logging.getLogger(__name__)

CARD_TEMPLATE = Path(ROOT_DIR / "pipeline" / "prompts" / "episode_card.md").read_text(encoding="utf-8")
SCRIPT_TEMPLATE = Path(ROOT_DIR / "pipeline" / "prompts" / "script.md").read_text(encoding="utf-8")


def _build_card_prompt(series: dict, characters: dict, episode: int, seconds: int) -> str:
    return (
        CARD_TEMPLATE
        + "\n\n## 本次任务\n"
        + f"集数：第{episode}集，目标时长 {seconds} 秒。\n系列设定：\n"
        + dump_json(series)
        + "\n角色设定：\n"
        + dump_json(characters)
        + "\n请只输出一个合法 JSON 对象（不要输出 Markdown 或解释文字）。"
    )


def _build_script_prompt(card: dict, series: dict, characters: dict) -> str:
    return (
        SCRIPT_TEMPLATE
        + "\n\n## 本次任务\n分集剧情卡：\n"
        + dump_json(card)
        + "\n系列设定：\n"
        + dump_json(series)
        + "\n角色设定：\n"
        + dump_json(characters)
        + "\n请只输出一个合法 JSON 对象（不要输出 Markdown 或解释文字）。"
    )


def _generate_one_episode(project_id: int, series: dict, characters: dict, episode: int, seconds: int) -> dict:
    if settings.llm_provider == "mock":
        card = mock_content.make_episode(series, characters, episode, seconds)
        script = card  # mock 的 card 已含 scenes，直接复用
    else:
        card = extract_json(complete(_build_card_prompt(series, characters, episode, seconds), temperature=0.9))
        if not card:
            raise RuntimeError(f"第{episode}集剧情卡生成失败")
        script = extract_json(complete(_build_script_prompt(card, series, characters), temperature=0.9))
        if not script or "scenes" not in script:
            raise RuntimeError(f"第{episode}集剧本生成失败")
        script["episode"] = episode
    ep_dir = episode_dir(project_id, episode)
    ep_dir.mkdir(parents=True, exist_ok=True)
    write_json(project_id, f"episodes/ep{episode:03d}/episode-card.json", card)
    write_text(project_id, f"episodes/ep{episode:03d}/episode-card.md", to_markdown(f"第{episode}集 剧情卡", card))
    write_json(project_id, f"episodes/ep{episode:03d}/script.json", script)
    write_text(project_id, f"episodes/ep{episode:03d}/script.md", to_markdown(f"第{episode}集 剧本", script))
    return script


def generate_episodes(project_id: int, series: dict, characters: dict, episode_count: int, seconds_per_episode: int) -> list[dict]:
    """并行生成各集（受 llm_max_workers 限制），返回剧本列表。"""
    episodes = []
    with ThreadPoolExecutor(max_workers=settings.llm_max_workers) as pool:
        futures = [
            pool.submit(_generate_one_episode, project_id, series, characters, ep, seconds_per_episode)
            for ep in range(1, episode_count + 1)
        ]
        for f in futures:
            episodes.append(f.result())  # 保持顺序；异常向上抛
    return episodes

