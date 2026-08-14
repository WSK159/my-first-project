"""全剧一致性台账：角色形象注册表 + 场景注册表 + 全局风格锚点。

任何图片/视频提示词都从这份权威档案取字段，禁止模型自由发挥，保证 60 集不崩脸、
不换装、不换场景。"""

import logging
from pathlib import Path

from ..config import ROOT_DIR
from . import mock_content
from .json_utils import dump_json, extract_json
from .llm import complete
from .project_store import to_markdown, write_json, write_text

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = Path(ROOT_DIR / "pipeline" / "prompts" / "continuity.md").read_text(encoding="utf-8")


def _build_prompt(series: dict, characters: dict) -> str:
    return (
        PROMPT_TEMPLATE
        + "\n\n## 本次任务\n系列设定：\n"
        + dump_json(series)
        + "\n角色设定：\n"
        + dump_json(characters)
        + "\n请只输出一个合法 JSON 对象（不要输出 Markdown 或解释文字）。"
    )


def _normalize(ledger: dict, series: dict, characters: dict) -> dict:
    """规范化台账结构，保证下游字段齐全。"""
    registry = ledger.get("registry", {})
    style = ledger.get("style", {})
    registry.setdefault(
        "characters",
        [
            {
                "id": c.get("id"),
                "name": c.get("name", ""),
                "face": c.get("visual_anchor", {}).get("face", "清晰五官"),
                "hair": c.get("visual_anchor", {}).get("hair", ""),
                "outfit": c.get("visual_anchor", {}).get("wardrobe", "简洁服装"),
                "props": c.get("visual_anchor", {}).get("props", ""),
                "invariants": c.get("visual_anchor", {}).get("invariants", []),
            }
            for c in characters.get("characters", [])
        ],
    )
    if not registry.get("scenes"):
        registry["scenes"] = [
            {
                "id": f"scene{idx:02d}",
                "name": loc.get("name", f"场景{idx}"),
                "visual": loc.get("visual", ""),
                "lighting": "稳定主光，无闪烁",
                "props": [],
            }
            for idx, loc in enumerate(series.get("locations", []), start=1)
        ]
    style.setdefault("tone", series.get("tone", "电影质感"))
    style.setdefault("color_palette", [])
    style.setdefault("lens_language", "竖屏 9:16，中近景为主，慢推镜头")
    style.setdefault("subtitle_style", "白字黑边，底部安全区")
    style.setdefault("cover_layout", "主角居中，标题置顶，情绪张力拉满")
    return {"registry": registry, "style": style}


def build_consistency_ledger(project_id: int, series: dict, characters: dict, user_id: int | None = None) -> dict:
    """生成 continuity.json / scenes.md / style.md，返回规范化台账。"""
    from ..config import settings

    if settings.llm_provider == "mock":
        ledger = mock_content.make_continuity(series, characters)
    else:
        ledger = extract_json(complete(_build_prompt(series, characters), temperature=0.7, user_id=user_id))
        if not ledger:
            raise RuntimeError("一致性台账生成失败：LLM 输出无法解析")
    ledger = _normalize(ledger, series, characters)
    write_json(project_id, "continuity.json", ledger)
    registry = ledger["registry"]
    scenes_md = to_markdown("场景注册表", {"scenes": registry.get("scenes", [])})
    write_text(project_id, "scenes.md", scenes_md)
    style_md = to_markdown("全局风格锚点", ledger["style"])
    write_text(project_id, "style.md", style_md)
    return ledger
