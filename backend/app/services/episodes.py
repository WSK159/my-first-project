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


def _build_card_prompt(
    series: dict, characters: dict, episode: int, seconds: int, outline_row: dict | None, continuity: dict | None
) -> str:
    prompt = (
        CARD_TEMPLATE
        + "\n\n## 本次任务\n"
        + f"集数：第{episode}集，目标时长 {seconds} 秒。\n系列设定：\n"
        + dump_json(series)
        + "\n角色设定：\n"
        + dump_json(characters)
    )
    if outline_row:
        prompt += "\n本集大纲行（必须忠实执行）：\n" + dump_json(outline_row)
    if continuity:
        prompt += "\n全剧一致性台账（场景/风格必须遵守）：\n" + dump_json(continuity)
    prompt += "\n请只输出一个合法 JSON 对象（不要输出 Markdown 或解释文字）。"
    return prompt


def generate_episode(
    project_id: int,
    series: dict,
    characters: dict,
    episode: int,
    seconds: int,
    outline_row: dict | None = None,
    continuity: dict | None = None,
    user_id: int | None = None,
) -> dict:
    if settings.llm_provider == "mock":
        card = mock_content.make_episode(series, characters, episode, seconds, outline_row)
        script = card  # mock 的 card 已含 scenes，直接复用
    else:
        card = extract_json(
            complete(
                _build_card_prompt(series, characters, episode, seconds, outline_row, continuity),
                temperature=0.9,
                user_id=user_id,
            )
        )
        if not card:
            raise RuntimeError(f"第{episode}集剧情卡生成失败")
        script = extract_json(
            complete(_build_script_prompt(card, series, characters, continuity), temperature=0.9, user_id=user_id)
        )
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


def _build_script_prompt(card: dict, series: dict, characters: dict, continuity: dict | None) -> str:
    prompt = (
        SCRIPT_TEMPLATE
        + "\n\n## 本次任务\n分集剧情卡：\n"
        + dump_json(card)
        + "\n系列设定：\n"
        + dump_json(series)
        + "\n角色设定：\n"
        + dump_json(characters)
    )
    if continuity:
        prompt += "\n全剧一致性台账（场景/风格必须遵守）：\n" + dump_json(continuity)
    prompt += "\n请只输出一个合法 JSON 对象（不要输出 Markdown 或解释文字）。"
    return prompt


def generate_episodes(
    project_id: int,
    series: dict,
    characters: dict,
    episode_count: int,
    seconds_per_episode: int,
    outline: dict | None = None,
    continuity: dict | None = None,
    user_id: int | None = None,
) -> list[dict]:
    """并行生成各集（受 llm_max_workers 限制）。单集失败只记录日志，
    返回成功的剧本列表；失败集由流水线重试逻辑单独补跑。"""
    rows = {r.get("episode"): r for r in (outline or {}).get("episodes", [])}
    episodes = []
    with ThreadPoolExecutor(max_workers=settings.llm_max_workers) as pool:
        futures = [
            pool.submit(
                generate_episode,
                project_id, series, characters, ep, seconds_per_episode, rows.get(ep), continuity, user_id,
            )
            for ep in range(1, episode_count + 1)
        ]
        for f in futures:
            try:
                episodes.append(f.result())
            except Exception as exc:  # noqa: BLE001
                logger.warning("分集生成失败（将由重试逻辑补跑）：%s", exc)
    return episodes
