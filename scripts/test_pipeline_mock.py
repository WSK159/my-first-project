"""阶段1验证：mock 档完整跑通 LLM 内容流水线并检查产物。"""

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings  # noqa: E402
from pipeline.cli import run  # noqa: E402


def main() -> int:
    assert settings.llm_provider == "mock", "测试需在 mock 档运行"
    project_id = random.randint(800000, 899999)
    root = run(project_id, idea="被夺走一切的千金十年后携子回国复仇", random_mode=False, genre="", episodes=2, seconds=60)

    checks = [
        ("series.json", root / "series.json"),
        ("series.md", root / "series.md"),
        ("characters.json", root / "characters.json"),
        ("outline.md", root / "outline.md"),
        ("outline.json", root / "outline.json"),
        ("continuity.json", root / "continuity.json"),
        ("scenes.md", root / "scenes.md"),
        ("style.md", root / "style.md"),
        ("novel.md", root / "novel.md"),
        ("ep001/script.json", root / "episodes" / "ep001" / "script.json"),
        ("ep001/video-prompts.md", root / "episodes" / "ep001" / "video-prompts.md"),
        ("ep002/script.json", root / "episodes" / "ep002" / "script.json"),
        ("characters/lead.png", root / "characters" / "lead.png"),
        ("cover.png", root / "cover.png"),
        ("scenes/scene01.png", root / "scenes" / "scene01.png"),
        ("ep001/videos/clip-01/video.mp4", root / "episodes" / "ep001" / "videos" / "clip-01" / "video.mp4"),
        ("ep001/videos/clip-01/last-frame.png", root / "episodes" / "ep001" / "videos" / "clip-01" / "last-frame.png"),
        ("ep001/audio/scene-01.wav", root / "episodes" / "ep001" / "audio" / "scene-01.wav"),
        ("audio-manifest.json", root / "audio-manifest.json"),
        ("ep001/final.mp4", root / "episodes" / "ep001" / "final.mp4"),
        ("ep001/episode.srt", root / "episodes" / "ep001" / "episode.srt"),
        ("delivery zip", root / "delivery" / f"project-{project_id}.zip"),
    ]
    failed = False
    for label, path in checks:
        ok = path.exists() and path.stat().st_size > 0
        print(f"{'PASS' if ok else 'FAIL'}  {label} ({path.stat().st_size if path.exists() else 0} B)")
        failed = failed or not ok

    png = root / "characters" / "lead.png"
    if png.exists():
        magic_ok = png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        print(f"{'PASS' if magic_ok else 'FAIL'}  PNG 魔数校验")
        failed = failed or not magic_ok

    mp4 = root / "episodes" / "ep001" / "videos" / "clip-01" / "video.mp4"
    if mp4.exists():
        mp4_ok = mp4.read_bytes()[:12] == b"\x00\x00\x00\x18ftypmp42" or mp4.stat().st_size > 1000
        print(f"{'PASS' if mp4_ok else 'FAIL'}  MP4 文件校验（{mp4.stat().st_size} B）")
        failed = failed or not mp4_ok

    wav = root / "episodes" / "ep001" / "audio" / "scene-01.wav"
    if wav.exists():
        wav_ok = wav.read_bytes()[:4] == b"RIFF" and wav.stat().st_size > 1000
        print(f"{'PASS' if wav_ok else 'FAIL'}  WAV 文件校验（{wav.stat().st_size} B）")
        failed = failed or not wav_ok

    final = root / "episodes" / "ep001" / "final.mp4"
    if final.exists():
        final_ok = final.stat().st_size > 100_000
        print(f"{'PASS' if final_ok else 'FAIL'}  成片 final.mp4（{final.stat().st_size} B）")
        failed = failed or not final_ok

    novel_path = root / "novel.md"
    novel_len = len(novel_path.read_text(encoding="utf-8")) if novel_path.exists() else 0
    print(f"novel.md 字数：{novel_len}")
    if novel_len < 200:
        failed = True
    print("阶段1 mock 流水线：" + ("通过" if not failed else "存在失败项"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
