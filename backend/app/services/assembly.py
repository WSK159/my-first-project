"""后期合成：FFmpeg 拼接片段、混入音频、生成成片。"""

import logging
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from .project_store import project_dir, read_json
from .videos import _find_ffmpeg

logger = logging.getLogger(__name__)


@lru_cache(maxsize=4096)
def probe_duration(path: Path) -> float:
    """探测媒体时长（带缓存，按路径+修改时间失效）。"""
    mtime = path.stat().st_mtime if path.exists() else 0
    return _probe_duration_uncached(path, mtime)


def _probe_duration_uncached(path: Path, _mtime: float) -> float:
    ffmpeg = _find_ffmpeg()
    ffprobe_candidate = Path(ffmpeg).parent / "ffprobe.exe"
    ffprobe = str(ffprobe_candidate) if ffprobe_candidate.exists() else "ffprobe"
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True,
        capture_output=True,
        timeout=60,
    )
    try:
        return float(result.stdout.decode().strip().splitlines()[0])
    except (ValueError, IndexError):
        return 0.0


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    try:
        subprocess.run(cmd, check=True, capture_output=True, cwd=str(cwd) if cwd else None, timeout=600)
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or b"").decode("utf-8", "ignore")[-1200:]
        raise RuntimeError(f"FFmpeg 执行失败：{err}") from exc


def assemble_episode(project_id: int, episode: int) -> Path:
    """拼接单集片段 → 混入场景音频 → 生成 episodes/epXXX/final.mp4。"""
    ffmpeg = _find_ffmpeg()
    root = project_dir(project_id)
    ep_dir = root / "episodes" / f"ep{episode:03d}"
    videos_dir = ep_dir / "videos"
    audio_dir = ep_dir / "audio"

    manifest = read_json(project_id, "videos-manifest.json")
    clips = sorted(
        manifest.get("episodes", {}).get(str(episode), []),
        key=lambda c: int(c.get("clip", 0)),
    )
    if not clips:
        raise RuntimeError(f"第{episode}集缺少视频片段")

    # 1) 拼接视频（用相对文件名避免中文路径问题）
    concat_file = videos_dir / "concat.txt"
    concat_file.write_text(
        "\n".join(f"file 'clip-{int(c.get('clip', 0)):02d}/video.mp4'" for c in clips),
        encoding="utf-8",
    )
    visual = ep_dir / "final-visual.mp4"
    _run(
        [
            ffmpeg, "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", "concat.txt",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
            str(visual),
        ],
        cwd=videos_dir,
    )

    # 2) 拼接音频（场景顺序，scene-01..N）
    audio_files = sorted(audio_dir.glob("scene-*.wav"))
    if audio_files:
        audio_concat = audio_dir / "concat.txt"
        audio_concat.write_text("\n".join(f"file '{p.name}'" for p in audio_files), encoding="utf-8")
        full_audio = ep_dir / "full-audio.wav"
        _run(
            [
                ffmpeg, "-y", "-loglevel", "error",
                "-f", "concat", "-safe", "0", "-i", "concat.txt",
                "-c", "copy", str(full_audio),
            ],
            cwd=audio_dir,
        )
        # 3) 混入音频（视频时长为准）
        final = ep_dir / "final-muxed.mp4"
        _run(
            [
                ffmpeg, "-y", "-loglevel", "error",
                "-i", str(visual), "-i", str(full_audio),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest",
                str(final),
            ]
        )
    else:
        final = visual

    return final


def finalize_episode(project_id: int, episode: int, subtitled: Path | None = None) -> Path:
    """把成片放到规范位置 episodes/epXXX/final.mp4。"""
    ep_dir = project_dir(project_id) / "episodes" / f"ep{episode:03d}"
    candidates = [subtitled, ep_dir / "final-muxed.mp4", ep_dir / "final-visual.mp4"]
    source = next((c for c in candidates if c is not None and c.exists()), None)
    if source is None:
        raise RuntimeError(f"第{episode}集成片不存在，无法交付")
    target = ep_dir / "final.mp4"
    if source != target:
        shutil.copyfile(source, target)
    return target


def build_collection(project_id: int) -> Path | None:
    """把各集 final.mp4 拼接为全剧合集 collection.mp4（-c copy 快速拼接）。
    少于 2 集或拼接失败时返回 None。"""
    root = project_dir(project_id)
    eps_dir = root / "episodes"
    finals = sorted(eps_dir.glob("ep*/final.mp4"))
    if len(finals) < 2:
        return None
    ffmpeg = _find_ffmpeg()
    concat = root / "collection-concat.txt"
    concat.write_text("\n".join(f"file '{p.relative_to(root).as_posix()}'" for p in finals), encoding="utf-8")
    target = root / "collection.mp4"
    try:
        _run(
            [
                ffmpeg, "-y", "-loglevel", "error",
                "-f", "concat", "-safe", "0", "-i", str(concat),
                "-c", "copy", str(target),
            ],
            cwd=root,
        )
    except RuntimeError as exc:
        logger.warning("合集快速拼接失败（回退重编码）：%s", exc)
        try:
            _run(
                [
                    ffmpeg, "-y", "-loglevel", "error",
                    "-f", "concat", "-safe", "0", "-i", str(concat),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", str(target),
                ],
                cwd=root,
            )
        except RuntimeError as exc2:
            logger.warning("合集生成失败：%s", exc2)
            return None
    return target
