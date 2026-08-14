"""一键短剧生成 CLI（骨架，阶段1起逐步实现）。"""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="一键生成短剧")
    parser.add_argument("--idea", default="", help="一句话灵感")
    parser.add_argument("--random", action="store_true", help="完全随机模式")
    parser.add_argument("--episodes", type=int, default=1, help="集数")
    parser.add_argument("--seconds", type=int, default=60, help="单集秒数")
    parser.add_argument("--tier", default="mock", choices=["mock", "fast", "quality"], help="档位")
    args = parser.parse_args()

    if not args.idea and not args.random:
        parser.error("请提供 --idea 或使用 --random")

    print(
        f"CLI 骨架：idea={args.idea or '(随机)'} episodes={args.episodes} "
        f"seconds={args.seconds} tier={args.tier}"
    )
    print("阶段1起将依次执行：系列设定 → 角色 → 分集剧本 → 分镜 → 生图 → 生视频 → 音频 → 合成。")


if __name__ == "__main__":
    main()

