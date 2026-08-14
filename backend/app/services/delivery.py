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
    for ep_clips in videos.get("episodes", {}).values():
        for clip in ep_clips:
            total_tokens += int(clip.get("tokens", 0))
            video = project_dir(project_id) / clip["video"]
            if video.exists():
                total_seconds += probe_duration(video)
    return {
        "title": series.get("title", ""),
        "genre": series.get("genre", ""),
        "logline": series.get("logline", ""),
        "episode_count": len(videos.get("episodes", {})),
        "total_seconds": round(total_seconds, 1),
        "video_tokens": total_tokens,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platform": "AI短剧工坊",
    }


def build_delivery_package(project_id: int) -> Path:
    """生成 project-<id>/delivery/project-<id>.zip。"""
    root = project_dir(project_id)
    meta = _metadata(project_id)
    (root / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    out_dir = root / "delivery"
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"project-{project_id}.zip"

    include = [
        "novel.md", "series.md", "characters.md", "metadata.json", "cover.png",
        "characters", "scenes",
        "episodes",  # 各集剧本/提示词/字幕/final.mp4
    ]
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

