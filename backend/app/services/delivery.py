"""交付：打包最终成片+小说+剧本+角色图+封面+元数据为 zip。"""

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .assembly import probe_duration
from .project_store import project_dir, read_json, read_text


def _metadata(project_id: int) -> dict:
    series = read_json(project_id, "series.json")
    videos = read_json(project_id, "videos-manifest.json")
    total_seconds = 0.0
    total_tokens = 0
    episodes_meta = []
    for ep_clips in videos.get("episodes", {}).values():
        for clip in ep_clips:
            total_tokens += int(clip.get("tokens", 0))
            video = project_dir(project_id) / clip["video"]
            if video.exists():
                total_seconds += probe_duration(video)
    for ep_dir in sorted((project_dir(project_id) / "episodes").glob("ep*")):
        final = ep_dir / "final.mp4"
        episodes_meta.append(
            {
                "episode": int(ep_dir.name.replace("ep", "")),
                "final_video": f"{ep_dir.name}/final.mp4" if final.exists() else "",
                "duration_seconds": round(probe_duration(final), 1) if final.exists() else 0,
                "subtitle": f"{ep_dir.name}/episode.srt" if (ep_dir / "episode.srt").exists() else "",
            }
        )
    total_minutes = round(total_seconds / 60, 1)
    return {
        "title": series.get("title", ""),
        "genre": series.get("genre", ""),
        "logline": series.get("logline", ""),
        "episode_count": len(videos.get("episodes", {})),
        "total_seconds": round(total_seconds, 1),
        "total_minutes": total_minutes,
        "episodes": episodes_meta,
        "collection": "collection.mp4" if (project_dir(project_id) / "collection.mp4").exists() else "",
        "video_tokens": total_tokens,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platform": "AI短剧工坊",
        "ai_generated": True,
        "compliance": {
            "label": "AI 生成内容（投稿前请按平台要求标识）",
            "recommendations": [
                "投稿前确认无侵权素材与敏感内容",
                "按目标平台规格导出封面与字幕",
                "保留原始工程以便修改",
            ],
        },
    }


def _platform_specs() -> dict:
    """主流短剧投稿平台规格（封面/分辨率/时长建议）。"""
    return {
        "douyin": {
            "name": "抖音",
            "video_ratio": "9:16",
            "resolution": "1080x1920 起",
            "episode_duration": "60-180 秒",
            "cover_size": "1080x1440 或 1080x1920",
            "subtitle": "底部安全区，字号 ≥ 5% 屏高",
            "notes": "AI 内容需在发布页勾选标识",
        },
        "kuaishou": {
            "name": "快手",
            "video_ratio": "9:16",
            "resolution": "720x1280 起",
            "episode_duration": "60-180 秒",
            "cover_size": "1080x1920",
            "subtitle": "避免顶部/底部 10% 区域被遮挡",
            "notes": "标题 ≤ 20 字",
        },
        "hongguo": {
            "name": "红果短剧",
            "video_ratio": "9:16",
            "resolution": "1080x1920",
            "episode_duration": "90-180 秒（横屏剧 3-8 分钟）",
            "cover_size": "1080x1440",
            "subtitle": "白字黑边，安全区内",
            "notes": "需要完整剧集+分集简介+角色海报",
        },
    }


def build_delivery_package(project_id: int) -> Path:
    """生成 project-<id>/delivery/project-<id>.zip。"""
    root = project_dir(project_id)
    meta = _metadata(project_id)
    (root / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    platforms = _platform_specs()
    (root / "platforms.json").write_text(json.dumps(platforms, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "投稿与合规说明.md").write_text(_compliance_doc(meta, platforms), encoding="utf-8")

    out_dir = root / "delivery"
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"project-{project_id}.zip"

    include = [
        "novel.md", "series.md", "characters.md", "outline.md", "scenes.md", "style.md",
        "continuity.json", "metadata.json", "platforms.json", "投稿与合规说明.md", "cover.png",
        "characters", "scenes",
        "episodes",  # 各集剧本/提示词/字幕/final.mp4
    ]
    if (root / "collection.mp4").exists():
        include.append("collection.mp4")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in include:
            src = root / item
            if src.is_dir():
                for f in src.rglob("*"):
                    if f.is_file() and not f.suffix.lower() in (".wav",):
                        zf.write(f, f.relative_to(root))
            elif src.exists():
                zf.write(src, src.relative_to(root))
    return zip_path


def _compliance_doc(meta: dict, platforms: dict) -> str:
    lines = [
        "# 投稿与合规说明",
        "",
        f"《{meta.get('title', '')}》为 AI 生成内容（{meta.get('episode_count', 0)} 集，总时长约 {meta.get('total_minutes', 0)} 分钟）。",
        "",
        "## 投稿前检查清单",
        "",
        "1. 在平台发布页勾选「AI 生成内容」标识（各平台要求见下表）。",
        "2. 检查剧情是否含平台禁止的敏感话题、暴力、擦边内容。",
        "3. 确认封面无文字溢出、标题 ≤ 20 字。",
        "4. 下载交付包后按目标平台规格重新导出（分辨率/字幕样式）。",
        "",
        "## 平台规格",
        "",
    ]
    for key, spec in platforms.items():
        lines.append(f"### {spec['name']}（{key}）")
        for k, v in spec.items():
            if k != "name":
                lines.append(f"- {k}：{v}")
        lines.append("")
    lines.append("> 提示：投稿前请以平台最新审核规则为准。")
    return "\n".join(lines)
