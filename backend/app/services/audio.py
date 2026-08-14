"""音频生成：Seed Audio 对白/旁白/环境/音乐（Audio Director cue sheet）+ mock WAV。"""

import base64
import logging
import math
import struct
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from ..config import settings
from .project_store import write_json

logger = logging.getLogger(__name__)


def _mock_wav(path: Path, seconds: float, freq: float = 440.0, amp: float = 0.22) -> Path:
    """纯标准库生成正弦波 WAV（mock 音频，避免额外依赖）。"""
    rate = 24000
    n = max(1, int(rate * seconds))
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = bytearray()
    for i in range(n):
        t = i / rate
        env = min(1.0, t * 5, max(0.0, (seconds - t) * 5))
        value = int(amp * 32767 * math.sin(2 * math.pi * freq * t) * env)
        frames += struct.pack("<h", max(-32768, min(32767, value)))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return path


class SeedAudioClient:
    """火山语音 Seed Audio 直接 API 客户端。"""

    def __init__(self) -> None:
        self.api_key = settings.seed_audio_api_key
        self.base_url = settings.seed_audio_base_url.rstrip("/")
        self.model = settings.seed_audio_model

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, path: Path, enable_subtitle: bool = True) -> dict:
        payload = {
            "model": self.model,
            "text_prompt": prompt[:2048],
            "audio_config": {
                "format": settings.seed_audio_format,
                "sample_rate": settings.seed_audio_sample_rate,
                "speech_rate": 0,
                "loudness_rate": 0,
                "pitch_rate": 0,
                "enable_subtitle": enable_subtitle,
            },
        }
        resp = httpx.post(
            f"{self.base_url}/api/v3/tts/create",
            headers={"X-Api-Key": self.api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=180,
        )
        resp.raise_for_status()
        data = resp.json()
        code = data.get("code")
        if code not in (None, 0, 200, "0", "200"):
            raise RuntimeError(f"Seed Audio 失败：{data.get('message', code)}")
        path.parent.mkdir(parents=True, exist_ok=True)
        audio_b64 = data.get("audio")
        if audio_b64:
            path.write_bytes(base64.b64decode(audio_b64))
        elif data.get("url"):
            audio = httpx.get(data["url"], timeout=180)
            audio.raise_for_status()
            path.write_bytes(audio.content)
        else:
            raise RuntimeError("Seed Audio 响应缺少音频数据")
        return {
            "path": str(path),
            "duration": data.get("duration") or data.get("original_duration") or 0,
            "subtitle": data.get("subtitle") or [],
        }


def _scene_director_prompt(scene: dict, series: dict, characters: dict, voice_notes: dict) -> str:
    """按 Audio Director cue sheet 组装单场景提示词。"""
    loc = scene.get("location", "场景")
    time_of_day = scene.get("time", "日")
    genre = series.get("genre", "")
    ambience_map = {
        "都市复仇": f"{loc}的都市底噪，远处车流与低鸣，{time_of_day}环境",
        "男频逆袭": f"{loc}的风声与灵气流动感，环境空旷",
        "女频甜宠": f"{loc}的柔和风声与轻快环境音",
        "悬疑规则": f"{loc}的压迫感底噪，电灯滋滋声，回声",
    }
    mood_map = {"紧张": "低弦乐铺底，克制压抑", "温暖": "钢琴与弦乐，舒缓", "热血": "鼓点推进，能量感", "悬疑": "低频合成器，不安感"}
    ambience = ambience_map.get(genre, f"{loc}的环境底噪")
    lines = scene.get("dialogue", [])
    if not lines:
        return f"背景持续有{ambience}，音乐以{mood_map.get('悬疑' if genre == '悬疑规则' else '温暖', '轻音乐')}铺底。时长{scene.get('duration_seconds', 8)}秒，只有环境音，没有人声。人声不要出现。"
    dialogue_part = "。".join(
        f'{d["speaker"]}（{voice_notes.get(d["speaker"], "青年，普通话")}）用{d.get("emotion", "平静")}的语气说道："{d["line"]}"'
        for d in lines
    )
    prompt = (
        f"背景持续有{ambience}，音乐以{mood_map.get(lines[0].get('emotion', '悬疑'), '轻音乐')}铺底。"
        f"先是{dialogue_part}。人声清楚靠前，不要让噪声盖住台词，不要添加额外旁白。"
    )
    return prompt


def build_audio_plan(episode_script: dict) -> list[dict]:
    """把剧本场景转为音频时间轴计划。"""
    plan = []
    cursor = 0.0
    for scene in episode_script.get("scenes", []):
        duration = float(scene.get("duration_seconds", 8))
        plan.append(
            {
                "scene": scene.get("scene", len(plan) + 1),
                "start": cursor,
                "end": cursor + duration,
                "duration": duration,
                "location": scene.get("location", ""),
                "beat": scene.get("beat", ""),
                "dialogue": scene.get("dialogue", []),
            }
        )
        cursor += duration
    return plan


def _generate_scene_audio(project_id: int, episode: int, scene: dict, prompt: str, duration: float) -> dict:
    rel = f"episodes/ep{episode:03d}/audio/scene-{scene['scene']:02d}.wav"
    path = _project_file(project_id, rel)
    client = SeedAudioClient()
    if client.available:
        result = client.generate(prompt, path)
        return {"scene": scene["scene"], "audio": rel, "provider": "seed-audio", **result}
    _mock_wav(path, max(1.0, duration), freq=320 + scene["scene"] * 40, amp=0.18)
    return {"scene": scene["scene"], "audio": rel, "provider": "mock", "duration": duration, "subtitle": []}


def _project_file(project_id: int, rel_path: str) -> Path:
    from .project_store import project_dir

    return project_dir(project_id) / rel_path


def generate_project_audio(project_id: int, series: dict, characters: dict, episodes: list[dict]) -> dict:
    """逐集生成配音/环境音（场景级 cue sheet），写入 audio-manifest.json。"""
    voice_notes = characters.get("voice_notes", {})
    tasks: list[tuple[int, dict, str, float]] = []
    for script in episodes:
        ep = script.get("episode", 1)
        for item in build_audio_plan(script):
            scene = next((s for s in script.get("scenes", []) if s.get("scene") == item["scene"]), item)
            prompt = _scene_director_prompt(scene, series, characters, voice_notes)
            tasks.append((ep, scene, prompt, item["duration"]))

    with ThreadPoolExecutor(max_workers=min(3, settings.llm_max_workers)) as pool:
        futures = [pool.submit(_generate_scene_audio, project_id, ep, scene, prompt, duration) for ep, scene, prompt, duration in tasks]
        results = [f.result() for f in futures]
    manifest: dict[str, list] = {}
    for (ep, _scene, _prompt, _dur), result in zip(tasks, results):
        manifest.setdefault(str(ep), []).append(result)
    write_json(project_id, "audio-manifest.json", manifest)
    return manifest
