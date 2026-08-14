"""视频生成：Seedance 分段生成（提交/轮询/尾帧衔接）+ mock ffmpeg 占位片段。"""

import logging
import base64
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from ..config import settings
from .project_store import read_json, write_json

logger = logging.getLogger(__name__)
_manifest_lock = threading.Lock()

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
        f"color=c={color}:s=720x1280:r=24:d={max(2, min(seconds, 15))}",
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

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.seedance_api_key
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


class MiniMaxVideoClient:
    """MiniMax H3 生视频客户端：提交异步任务 → 轮询 → 返回直链下载。"""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.minimax_api_key
        self.base_url = settings.minimax_base_url.rstrip("/")
        self.model = settings.minimax_video_model

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def create_task(
        self,
        prompt: str,
        duration: int,
        first_frame_path: Path | None = None,
        reference_images: list[Path] | None = None,
    ) -> str:
        content: list[dict] = [{"type": "text", "text": prompt}]
        payload: dict = {
            "model": self.model,
            "content": content,
            "duration": max(4, min(int(duration), 15)),
            "resolution": settings.minimax_video_resolution,
        }
        if first_frame_path is not None:
            content.append(
                {"type": "image_url", "image_url": {"url": first_frame_path.as_uri()}, "role": "first_frame"}
            )
        else:
            payload["ratio"] = settings.seedance_ratio
        for ref in reference_images or []:
            if ref.exists():
                content.append(
                    {"type": "image_url", "image_url": {"url": _data_uri(ref)}, "role": "reference_image"}
                )
        resp = httpx.post(
            f"{self.base_url}/v2/video_generation",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        payload = resp.json()
        base = payload.get("base_resp") or {}
        if base.get("status_code", 0) not in (0, None, 200):
            raise RuntimeError(f"MiniMax 视频失败：{base.get('status_msg', base.get('status_code'))}")
        task_id = payload.get("task_id")
        if not task_id:
            raise RuntimeError(f"MiniMax 创建视频任务失败：{str(payload)[:200]}")
        return task_id

    def poll_task(self, task_id: str, timeout_seconds: int | None = None) -> str:
        """轮询直到成功，返回视频下载直链。"""
        deadline = time.time() + (timeout_seconds or settings.seedance_max_wait_minutes * 60)
        while True:
            resp = httpx.get(
                f"{self.base_url}/v2/query/video_generation/{task_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=60,
            )
            resp.raise_for_status()
            payload = resp.json()
            base = payload.get("base_resp") or {}
            if base.get("status_code", 0) not in (0, None, 200):
                raise RuntimeError(f"MiniMax 视频查询失败：{base.get('status_msg', base.get('status_code'))}")
            task = payload.get("task") or {}
            status = task.get("status")
            if status == "succeeded":
                url = (task.get("content") or {}).get("url")
                if not url:
                    raise RuntimeError("MiniMax 成功响应缺少视频 URL")
                return url
            if status in ("failed", "cancelled"):
                raise RuntimeError(f"MiniMax 视频任务失败：{task.get('error', status)}")
            if time.time() > deadline:
                raise TimeoutError(f"MiniMax 视频任务超时：{task_id}")
            time.sleep(settings.seedance_poll_interval)

    @staticmethod
    def download(url: str, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.stream("GET", url, timeout=300) as resp:
            resp.raise_for_status()
            with path.open("wb") as f:
                for chunk in resp.iter_bytes(chunk_size=1 << 20):
                    f.write(chunk)
        return path


def _data_uri(path: Path) -> str:
    """把本地图片转为 data URI（MiniMax 参考图无需公网 URL）。"""
    import mimetypes

    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _generate_one_clip(
    project_id: int,
    episode: int,
    clip_no: int,
    prompt: str,
    duration: int,
    first_frame: Path | None,
    api_key: str | None = None,
    reference_images: list[Path] | None = None,
    force_mock: bool = False,
) -> dict:
    rel_dir = f"episodes/ep{episode:03d}/videos/clip-{clip_no:02d}"
    video_path = _project_file(project_id, f"{rel_dir}/video.mp4")
    client = SeedanceClient(api_key)
    if client.available and not force_mock:
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
    minimax = MiniMaxVideoClient()
    if minimax.available and not force_mock:
        task_id = minimax.create_task(prompt, duration, first_frame, reference_images)
        video_url = minimax.poll_task(task_id)
        minimax.download(video_url, video_path)
        last_frame = _project_file(project_id, f"{rel_dir}/last-frame.png")
        try:
            _mock_last_frame(video_path, last_frame)
        except Exception:  # noqa: BLE001 尾帧提取失败不阻断（仅影响衔接）
            logger.warning("MiniMax 视频尾帧提取失败：clip %s ep %s", clip_no, episode)
        return {
            "episode": episode,
            "clip": clip_no,
            "video": f"{rel_dir}/video.mp4",
            "last_frame": f"{rel_dir}/last-frame.png" if last_frame.exists() else "",
            "task_id": task_id,
            "tokens": 0,
            "provider": "minimax",
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


def _clip_prompt(clip: dict, continuity: dict | None = None, script: dict | None = None) -> str:
    beats = "；".join(clip.get("timeline_beats", []))
    rules = "；".join(clip.get("continuity_rules", []))
    negative = "；".join(clip.get("negative", []))
    prompt = (
        f"{beats}。运镜：{clip.get('camera', '固定机位')}。"
        f"连续性：{rules}。避免：{negative}。角色身份与服装严格参考提供的角色图。"
    )
    if continuity:
        registry = continuity.get("registry", {})
        style = continuity.get("style", {})
        scene_id = clip.get("references", {}).get("scene", "")
        scene = next((s for s in registry.get("scenes", []) if s.get("id") == scene_id), None)
        if scene:
            prompt += f" 场景必须严格匹配：{scene.get('name')}，{scene.get('visual', '')}，光线{scene.get('lighting', '')}，运镜习惯{scene.get('camera_habit', '')}。"
        chars = registry.get("characters", [])
        if chars:
            fixed = "；".join(
                f"{c.get('name')}:面容{c.get('face')}，发型{c.get('hair')}，服装{c.get('outfit')}，配饰{c.get('props')}"
                for c in chars[:2]
            )
            prompt += f" 角色外观固定：{fixed}。"
        if style:
            prompt += f" 全局风格：{style.get('tone', '')}，主色板{'/'.join(style.get('color_palette', []))}，镜头语言{style.get('lens_language', '')}。"
    return prompt


def generate_project_videos(
    project_id: int,
    episodes: list[dict],
    shots_map: dict[int, dict],
    continuity: dict | None = None,
    api_key: str | None = None,
    reference_images: dict[int, list[Path]] | None = None,
    force_mock: bool = False,
) -> dict:
    """按集生成视频片段。真实模式按尾帧链顺序生成；mock 模式并发生成。"""
    client = SeedanceClient(api_key)
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
            refs = (reference_images or {}).get(ep, [])
            tasks.append((ep, clip_no, _clip_prompt(clip, continuity, script), duration, refs))

    results: list[dict] = []
    reference_images = reference_images or {}
    if client.available:
        # 真实模式：逐段生成，上一段尾帧作为下一段首帧（跨集重置）
        last_frame: Path | None = None
        current_ep = None
        for ep, clip_no, prompt, duration, refs in tasks:
            if ep != current_ep:
                last_frame = None
                current_ep = ep
            result = _generate_one_clip(project_id, ep, clip_no, prompt, duration, last_frame, api_key, refs, force_mock)
            if result["last_frame"]:
                last_frame = _project_file(project_id, result["last_frame"])
            results.append(result)
    else:
        with ThreadPoolExecutor(max_workers=min(3, settings.llm_max_workers)) as pool:
            futures = [
                pool.submit(_generate_one_clip, project_id, ep, clip_no, prompt, duration, None, api_key, refs, force_mock)
                for ep, clip_no, prompt, duration, refs in tasks
            ]
            for f in futures:
                results.append(f.result())

    # 原子合并清单（支持多线程按集并行生成）
    with _manifest_lock:
        manifest = read_json(project_id, "videos-manifest.json")
        if not isinstance(manifest, dict) or "episodes" not in manifest:
            manifest = {"episodes": {}}
        for result in results:
            manifest["episodes"].setdefault(str(result["episode"]), []).append(result)
    write_json(project_id, "videos-manifest.json", manifest)
    return manifest
