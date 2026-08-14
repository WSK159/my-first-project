"""字幕：根据剧本对白+时间轴生成 SRT，并烧录进成片。"""

import logging
import subprocess
from pathlib import Path

from .audio import build_audio_plan
from ..config import settings
from .project_store import project_dir, read_json
from .videos import _find_ffmpeg

logger = logging.getLogger(__name__)


def _fmt_ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(project_id: int, episode: int) -> Path:
    """按场景时间轴为对白生成 SRT。"""
    script = read_json(project_id, f"episodes/ep{episode:03d}/script.json")
    plan = build_audio_plan(script)
    blocks = []
    idx = 1
    for item in plan:
        scene = next((s for s in script.get("scenes", []) if s.get("scene") == item["scene"]), {})
        lines = scene.get("dialogue", [])
        if not lines:
            continue
        seg = item["duration"] / max(len(lines), 1)
        for j, d in enumerate(lines):
            start = item["start"] + j * seg
            end = min(start + seg, item["end"])
            blocks.append(f"{idx}\n{_fmt_ts(start)} --> {_fmt_ts(end)}\n{d['speaker']}：{d['line']}\n")
            idx += 1
    srt = "\n".join(blocks)
    if settings.ai_subtitle_label and blocks:
        srt = f"0\n00:00:00,000 --> 00:00:02,000\nAI 生成内容\n\n" + srt
    path = project_dir(project_id) / "episodes" / f"ep{episode:03d}" / "episode.srt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(srt, encoding="utf-8")
    return path


def burn_subtitles(project_id: int, episode: int, source: Path) -> Path:
    """烧录字幕到成片（libass）。失败时回退无字幕成片。"""
    ffmpeg = _find_ffmpeg()
    ep_dir = project_dir(project_id) / "episodes" / f"ep{episode:03d}"
    srt = build_srt(project_id, episode)
    output = ep_dir / "final-subtitled.mp4"
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-i", str(source),
        "-vf", f"subtitles={srt.name}:force_style='FontSize=20,FontName=Microsoft YaHei,MarginV=64'",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-c:a", "copy", str(output),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, cwd=str(ep_dir), timeout=600)
        return output
    except (subprocess.CalledProcessError, RuntimeError) as exc:
        logger.warning("字幕烧录失败，回退无字幕版本：%s", getattr(exc, "stderr", exc))
        return source
