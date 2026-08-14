"""初始化数据库（建表 + 可选演示数据）。"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.db import init_db  # noqa: E402


def main() -> None:
    init_db()
    print("数据库初始化完成")


if __name__ == "__main__":
    main()

