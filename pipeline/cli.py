"""一键短剧生成 CLI：直接驱动内容引擎（阶段1：LLM 全链路）。"""

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings  # noqa: E402
from app.services import characters as characters_svc  # noqa: E402
from app.services import episodes as episodes_svc  # noqa: E402
from app.services import novel as novel_svc  # noqa: E402
from app.services import series as series_svc  # noqa: E402
from app.services import shots as shots_svc  # noqa: E402
from app.services.project_store import ensure_project_dirs, project_dir  # noqa: E402


def run(project_id: int, idea: str, random_mode: bool, genre: str, episodes: int, seconds: int) -> Path:
    ensure_project_dirs(project_id)
    print(f"[1/5] 系列设定 … provider={settings.llm_provider}")
    series = series_svc.generate_series(project_id, idea, random_mode, genre, episodes)
    print(f"      标题：{series.get('title')} 题材：{series.get('genre')}")

    print("[2/5] 角色设定 …")
    characters = characters_svc.generate_characters(project_id, series)
    print(f"      角色：{', '.join(c['name'] for c in characters['characters'])}")

    print(f"[3/5] 分集剧本（{episodes} 集，并发 {settings.llm_max_workers}）…")
    episode_scripts = episodes_svc.generate_episodes(project_id, series, characters, episodes, seconds)

    print("[4/5] 分镜/视频提示词 …")
    for script in episode_scripts:
        shots_svc.generate_shots(project_id, script, characters, script["episode"])

    print("[5/5] 完整小说 …")
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

