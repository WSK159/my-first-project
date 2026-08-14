"""视频生成：Seedance 分段生成（提交/轮询/尾帧衔接）+ mock ffmpeg 占位片段。"""

import logging
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from ..config import settings
from .project_store import write_json

logger = logging.getLogger(__name__)

FFMPEG_CANDIDATES = [
    r"C:\Users\wangshike\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffmpeg.exe",
    "ffmpeg",
]


def _find_ffmpeg() -> str:
    for cand in FFMPEG_CANDIDATES:
        if shutil.which(cand):
            return shutil.which(cand)
        if Path(cand).exists():
            return cand
    raise RuntimeError("未找到 ffmpeg，请先安装（winget install Gyan.FFmpeg）")


def _mock_clip(path: Path, seconds: int, label: str, seed: int = 0) -> Path:
    """用 ffmpeg lavfi 生成占位竖屏片段（ultrafast，性能优先）。"""
    ffmpeg = _find_ffmpeg()
    path.parent.mkdir(parents=True, exist_ok=True)
    color = f"0x{0x223344 + seed * 0x10101 & 0xFFFFFF:06X}"
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-f", "lavfi", "-i",
        f"color=c={color}:s=720x1280:r=24:d={max(2, min(seconds, 8))}",
        "-vf",
        "drawbox=x=0:y=0:w=iw:h=ih:color=white@0.18:t=6",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30", "-pix_fmt", "yuv420p",
        str(path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    except subprocess.CalledProcessError as exc:
        err = (exc.stderr or b"").decode("utf-8", "ignore")[-800:]
        raise RuntimeError(f"ffmpeg 生成 mock 片段失败：{err}") from exc
    return path


def _mock_last_frame(video: Path, frame: Path) -> Path:
    ffmpeg = _find_ffmpeg()
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-i", str(video), "-frames:v", "1", str(frame)],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return frame


class SeedanceClient:
    """火山方舟 Seedance 直接 API 客户端。"""

    def __init__(self) -> None:
        self.api_key = settings.seedance_api_key
        self.base_url = settings.seedance_base_url.rstrip("/")
        self.model = settings.seedance_model

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def create_task(self, prompt: str, duration: int, first_frame_path: Path | None = None) -> str:
        content: list[dict] = [{"type": "text", "text": prompt}]
        if first_frame_path is not None:
            content.append({"type": "image_url", "image_url": {"url": first_frame_path.as_uri()}})
        resp = httpx.post(
            f"{self.base_url}/contents/generations/tasks",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "content": content,
                "duration": duration,
                "resolution": settings.seedance_resolution,
                "ratio": settings.seedance_ratio,
                "generate_audio": settings.seedance_generate_audio,
                "watermark": settings.seedance_watermark,
                "return_last_frame": True,
                "camera_fixed": False,
            },
            timeout=60,
        )
        resp.raise_for_status()
        task_id = resp.json().get("id")
        if not task_id:
            raise RuntimeError("Seedance 创建任务失败：无 task id")
        return task_id

    def poll_task(self, task_id: str, timeout_seconds: int | None = None) -> dict:
        deadline = time.time() + (timeout_seconds or settings.seedance_max_wait_minutes * 60)
        while True:
            resp = httpx.get(
                f"{self.base_url}/contents/generations/tasks/{task_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=60,
            )
            resp.raise_for_status()
            task = resp.json()
            status = task.get("status")
            if status in ("succeeded", "failed", "cancelled"):
                if status != "succeeded":
                    raise RuntimeError(f"Seedance 任务失败：{task.get('error', status)}")
                return task
            if time.time() > deadline:
                raise TimeoutError(f"Seedance 任务超时：{task_id}")
            time.sleep(settings.seedance_poll_interval)

    @staticmethod
    def download(url: str, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.stream("GET", url, timeout=180) as resp:
            resp.raise_for_status()
            with path.open("wb") as f:
                for chunk in resp.iter_bytes(chunk_size=1 << 20):
                    f.write(chunk)
        return path


def _generate_one_clip(
    project_id: int,
    episode: int,
    clip_no: int,
    prompt: str,
    duration: int,
    first_frame: Path | None,
) -> dict:
    rel_dir = f"episodes/ep{episode:03d}/videos/clip-{clip_no:02d}"
    video_path = _project_file(project_id, f"{rel_dir}/video.mp4")
    client = SeedanceClient()
    if client.available:
        task_id = client.create_task(prompt, duration, first_frame)
        task = client.poll_task(task_id)
        url = ((task.get("content") or {}).get("video_url")) or ""
        if not url:
            raise RuntimeError("Seedance 响应缺少 video_url")
        client.download(url, video_path)
        last_frame_url = ((task.get("content") or {}).get("last_frame_url")) or ""
        last_frame = _project_file(project_id, f"{rel_dir}/last-frame.png")
        if last_frame_url:
            client.download(last_frame_url, last_frame)
        usage = task.get("usage") or {}
        return {
            "episode": episode,
            "clip": clip_no,
            "video": f"{rel_dir}/video.mp4",
            "last_frame": f"{rel_dir}/last-frame.png" if last_frame_url else "",
            "task_id": task_id,
            "tokens": usage.get("total_tokens", 0),
            "provider": "seedance",
        }
    # mock：ffmpeg 占位片段
    label = f"EP{episode:02d}-C{clip_no:02d}"
    _mock_clip(video_path, duration, label, seed=episode * 100 + clip_no)
    last_frame = _project_file(project_id, f"{rel_dir}/last-frame.png")
    _mock_last_frame(video_path, last_frame)
    return {
        "episode": episode,
        "clip": clip_no,
        "video": f"{rel_dir}/video.mp4",
        "last_frame": f"{rel_dir}/last-frame.png",
        "task_id": "mock",
        "tokens": 0,
        "provider": "mock",
    }


def _project_file(project_id: int, rel_path: str) -> Path:
    from .project_store import project_dir

    return project_dir(project_id) / rel_path


def _clip_prompt(clip: dict) -> str:
    beats = "；".join(clip.get("timeline_beats", []))
    rules = "；".join(clip.get("continuity_rules", []))
    negative = "；".join(clip.get("negative", []))
    return (
        f"{beats}。运镜：{clip.get('camera', '固定机位')}。"
        f"连续性：{rules}。避免：{negative}。角色身份与服装严格参考提供的角色图。"
    )


def generate_project_videos(project_id: int, episodes: list[dict], shots_map: dict[int, dict]) -> dict:
    """按集生成视频片段。真实模式按尾帧链顺序生成；mock 模式并发生成。"""
    client = SeedanceClient()
    tasks: list[tuple[int, int, str, int, Path | None]] = []
    for script in episodes:
        ep = script.get("episode", 1)
        shots = shots_map.get(ep, {})
        clips = shots.get("clips", [])
        if not clips:  # 回退：按剧本场景生成
            clips = [{"clip": f"clip-{s.get('scene', i+1):02d}", "timeline_beats": [s.get("beat", "")], "camera": s.get("camera", "固定机位")} for i, s in enumerate(script.get("scenes", []))]
        for clip in clips:
            clip_no = int(str(clip.get("clip", "clip-01")).replace("clip-", ""))
            duration = max(4, min(int(clip.get("duration_hint", 10)), 15))
            tasks.append((ep, clip_no, _clip_prompt(clip), duration, None))

    manifest = {"episodes": {}}
    if client.available:
        # 真实模式：逐段生成，上一段尾帧作为下一段首帧（跨集重置）
        last_frame: Path | None = None
        current_ep = None
        for ep, clip_no, prompt, duration, _ in tasks:
            if ep != current_ep:
                last_frame = None
                current_ep = ep
            result = _generate_one_clip(project_id, ep, clip_no, prompt, duration, last_frame)
            if result["last_frame"]:
                last_frame = _project_file(project_id, result["last_frame"])
            manifest["episodes"].setdefault(str(ep), []).append(result)
    else:
        with ThreadPoolExecutor(max_workers=min(3, settings.llm_max_workers)) as pool:
            futures = [pool.submit(_generate_one_clip, project_id, ep, clip_no, prompt, duration, None) for ep, clip_no, prompt, duration, _ in tasks]
            for f in futures:
                result = f.result()
                manifest["episodes"].setdefault(str(result["episode"]), []).append(result)

    write_json(project_id, "videos-manifest.json", manifest)
    return manifest
