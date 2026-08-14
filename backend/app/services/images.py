"""视觉资产生成：Seedream 角色图/场景图/封面（真实 API + mock 占位双路径）。"""

import logging
import struct
import zlib
from pathlib import Path

import httpx

from ..config import settings
from .json_utils import dump_json
from .project_store import write_json, write_text

logger = logging.getLogger(__name__)


def _mock_png(path: Path, size: tuple[int, int], rgb: tuple[int, int, int], variant: int = 0) -> Path:
    """纯标准库生成渐变 PNG（避免 mock 依赖 PIL）。"""
    width, height = size
    rows = bytearray()
    r0, g0, b0 = rgb
    for y in range(height):
        t = y / max(height - 1, 1)
        shift = (variant * 37) % 90
        r = max(0, min(255, int(r0 * (1 - t) + ((r0 + shift) % 256) * t)))
        g = max(0, min(255, int(g0 * (1 - t) + ((g0 + shift * 2) % 256) * t)))
        b = max(0, min(255, int(b0 * (1 - t) + ((b0 + shift * 3) % 256) * t)))
        rows.append(0)  # filter type 0
        rows.extend(bytes((r, g, b)) * width)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(rows), 6))
        + chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return path


def _ratio_size(ratio: str) -> tuple[int, int]:
    return {
        "9:16": (720, 1280),
        "3:4": (900, 1200),
        "1:1": (1024, 1024),
        "16:9": (1280, 720),
    }.get(ratio, (720, 1280))


def _color_for(text: str) -> tuple[int, int, int]:
    digest = zlib.crc32(text.encode("utf-8"))
    return (digest % 220 + 20, (digest >> 8) % 220 + 20, (digest >> 16) % 220 + 20)


class SeedreamClient:
    """火山方舟 Seedream 直接 API 客户端（不走机器特定脚本路径）。"""

    def __init__(self) -> None:
        self.api_key = settings.seedream_api_key
        self.base_url = settings.seedream_base_url.rstrip("/")
        self.model = settings.seedream_model

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, size: str = "2K", ratio: str = "9:16") -> bytes:
        resp = httpx.post(
            f"{self.base_url}/images/generations",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "prompt": prompt,
                "size": size,
                "response_format": "url",
                "watermark": False,
            },
            timeout=180,
        )
        resp.raise_for_status()
        data = resp.json().get("data") or []
        if not data or not data[0].get("url"):
            raise RuntimeError("Seedream 响应缺少图片 URL")
        image = httpx.get(data[0]["url"], timeout=180)
        image.raise_for_status()
        return image.content


def generate_image(project_id: int, rel_path: str, prompt: str, ratio: str = "9:16", seed: str = "") -> Path:
    """生成单张图片：有 key 走 Seedream，否则写 mock 占位图。"""
    target = Path(rel_path) if not rel_path.startswith("project") else None
    path = _project_path(project_id, rel_path)
    client = SeedreamClient()
    if client.available:
        try:
            content = client.generate(prompt, size="2K", ratio=ratio)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            logger.info("Seedream 生成 %s (%d bytes)", rel_path, len(content))
            return path
        except Exception as exc:  # noqa: BLE001
            logger.warning("Seedream 生成失败，回退 mock 占位：%s", exc)
    return _mock_png(path, _ratio_size(ratio), _color_for(seed or prompt), variant=len(seed))


def _project_path(project_id: int, rel_path: str) -> Path:
    from .project_store import project_dir

    return project_dir(project_id) / rel_path


def _character_prompt(char: dict, tone: str) -> str:
    va = char.get("visual_anchor", {})
    parts = [
        f"正面半身角色设定照：{char.get('name', '角色')}，{char.get('age', '')}岁，{char.get('gender', '')}",
        f"面容：{va.get('face', '清晰五官')}",
        f"体态：{va.get('body', '自然站姿')}",
        f"服装：{va.get('wardrobe', '简洁服装')}",
        f"标志道具：{va.get('props', '无')}",
        f"主色板：{va.get('palette', '中性色')}",
        f"系列视觉基调：{tone}",
        "不变项：" + "、".join(va.get("invariants", [])),
        "电影级质感，稳定光照，清晰五官，无文字无字幕无水印，画面只含一人。",
    ]
    return "，".join(parts)


def generate_project_images(project_id: int, series: dict, characters: dict) -> dict:
    """生成全部视觉资产并回写 characters.json（含图片路径）。"""
    tone = series.get("tone", "电影质感")
    for char in characters.get("characters", []):
        cid = char.get("id", "char")
        rel = f"characters/{cid}.png"
        generate_image(project_id, rel, _character_prompt(char, tone), ratio="3:4", seed=f"{series.get('title','')}{char.get('name','')}")
        char["image"] = rel

    cover_prompt = (
        f"竖屏短剧宣传封面，标题「{series.get('title', '')}」，{series.get('genre', '')}题材，"
        f"主角{characters['characters'][0]['name']}处于画面中心，情绪张力拉满，{tone}，电影海报质感，构图饱满。"
    )
    generate_image(project_id, "cover.png", cover_prompt, ratio="9:16", seed=series.get("title", "cover"))

    for idx, loc in enumerate(series.get("locations", []), start=1):
        scene_prompt = f"场景概念图：{loc.get('name', '场景')}，{loc.get('visual', '')}，{tone}，无人，电影场景设计图。"
        generate_image(project_id, f"scenes/scene{idx:02d}.png", scene_prompt, ratio="16:9", seed=loc.get("name", f"scene{idx}"))

    write_json(project_id, "characters.json", characters)
    write_text(project_id, "characters.md", _characters_md(characters))
    return {"characters": len(characters.get("characters", [])), "cover": True}


def _characters_md(characters: dict) -> str:
    lines = ["# 角色设定", ""]
    for char in characters.get("characters", []):
        lines.append(f"## {char.get('name')}（{char.get('role', '')}）")
        lines.append(f"- 形象图：![{char.get('name')}]({char.get('image', '')})")
        lines.append(f"- 身份：{char.get('age', '')}岁，{char.get('gender', '')}")
        lines.append(f"- 欲望：{char.get('desire', '')}")
        lines.append(f"- 矛盾：{char.get('wound', '')}")
        lines.append(f"- 对白风格：{char.get('dialogue_style', '')}")
        lines.append("")
    lines.append(f"## 出演规则\n{characters.get('cast_rules', '')}")
    lines.append(f"\n## 音色备注\n{dump_json(characters.get('voice_notes', {}))}")
    return "\n".join(lines)

