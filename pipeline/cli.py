"""一键短剧生成 CLI：直接驱动内容引擎（阶段1：LLM 全链路）。"""

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings  # noqa: E402
from app.services import audio as audio_svc  # noqa: E402
from app.services import assembly as assembly_svc  # noqa: E402
from app.services import characters as characters_svc  # noqa: E402
from app.services import delivery as delivery_svc  # noqa: E402
from app.services import episodes as episodes_svc  # noqa: E402
from app.services import images as images_svc  # noqa: E402
from app.services import novel as novel_svc  # noqa: E402
from app.services import series as series_svc  # noqa: E402
from app.services import shots as shots_svc  # noqa: E402
from app.services import subtitles as subtitles_svc  # noqa: E402
from app.services import videos as videos_svc  # noqa: E402
from app.services.project_store import ensure_project_dirs, project_dir  # noqa: E402


def run(project_id: int, idea: str, random_mode: bool, genre: str, episodes: int, seconds: int) -> Path:
    ensure_project_dirs(project_id)
    print(f"[1/10] 系列设定 … provider={settings.llm_provider}")
    series = series_svc.generate_series(project_id, idea, random_mode, genre, episodes)
    print(f"      标题：{series.get('title')} 题材：{series.get('genre')}")

    print("[2/10] 角色设定 …")
    characters = characters_svc.generate_characters(project_id, series)
    print(f"      角色：{', '.join(c['name'] for c in characters['characters'])}")

    print(f"[3/10] 分集剧本（{episodes} 集，并发 {settings.llm_max_workers}）…")
    episode_scripts = episodes_svc.generate_episodes(project_id, series, characters, episodes, seconds)

    print("[4/10] 分镜/视频提示词 …")
    shots_map = {}
    for script in episode_scripts:
        ep = script["episode"]
        shots_map[ep] = shots_svc.generate_shots(project_id, script, characters, ep)

    if settings.media_enabled or settings.mock_media:
        print("[5/10] 视觉资产（角色/场景/封面）…")
        images_svc.generate_project_images(project_id, series, characters)
        print("[6/10] 视频片段（Seedance/mock）…")
        videos_svc.generate_project_videos(project_id, episode_scripts, shots_map)
        print("[7/10] 配音与音乐（Seed Audio/mock）…")
        audio_svc.generate_project_audio(project_id, series, characters, episode_scripts)
        print("[8/10] FFmpeg 合成与字幕 …")
        for script in episode_scripts:
            ep = script["episode"]
            assembled = assembly_svc.assemble_episode(project_id, ep)
            subtitled = subtitles_svc.burn_subtitles(project_id, ep, assembled)
            assembly_svc.finalize_episode(project_id, ep, subtitled)
        print("[9/10] 打包交付 …")
        delivery_svc.build_delivery_package(project_id)

    print("[10/10] 完整小说 …")
    novel_svc.generate_novel(project_id, series, episode_scripts)

    root = project_dir(project_id)
    print(f"完成！产物目录：{root}")
    return root


def main() -> None:
    parser = argparse.ArgumentParser(description="一键生成短剧（阶段1：小说+剧本+分镜）")
    parser.add_argument("--idea", default="", help="一句话灵感")
    parser.add_argument("--random", action="store_true", help="完全随机模式")
    parser.add_argument("--genre", default="", help="题材（可选）")
    parser.add_argument("--episodes", type=int, default=1, help="集数")
    parser.add_argument("--seconds", type=int, default=60, help="单集秒数")
    parser.add_argument("--project-id", type=int, default=0, help="指定项目目录编号（默认随机）")
    args = parser.parse_args()

    if not args.idea and not args.random:
        parser.error("请提供 --idea 或使用 --random")
    project_id = args.project_id or random.randint(900000, 999999)
    run(project_id, args.idea, args.random, args.genre, args.episodes, args.seconds)


if __name__ == "__main__":
    main()
