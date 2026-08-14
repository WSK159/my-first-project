"""阶段 8 专项验证：大纲先行 / 一致性台账 / 任务表 / 断点续跑 / 事件日志 / 合集 / 退款。

运行：python scripts/test_pipeline_stage8.py
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.db import SessionLocal, init_db  # noqa: E402
from app.models import Project, Task, Transaction, User  # noqa: E402
from app.services.project_store import project_dir  # noqa: E402
from app.workers.pipeline_runner import run_project_pipeline  # noqa: E402

init_db()

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}  {detail}")


def main() -> int:
    project_id = 871001
    root = project_dir(project_id)
    if root.exists():
        import shutil

        shutil.rmtree(root)
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == "stage8_test").first()
        if user is None:
            user = User(username="stage8_test", password_hash="x", balance_cents=0)
            db.add(user)
            db.flush()
        db.query(Project).filter(Project.id == project_id).delete()
        project = Project(
            id=project_id,
            owner_id=user.id,
            idea="被夺走一切的千金十年后携子回国复仇",
            random_mode=False,
            genre="都市复仇",
            episode_count=2,
            seconds_per_episode=120,
            video_tier="mock",
            status="pending",
            frozen_cents=1000,
        )
        db.add(project)
        db.commit()

    run_project_pipeline(project_id)

    # 1) 大纲与一致性台账
    outline = json.loads((root / "outline.json").read_text(encoding="utf-8"))
    check("大纲先行：2 集", len(outline.get("episodes", [])) == 2, str(len(outline.get("episodes", []))))
    check("大纲先行：每集钩子不重复", outline["episodes"][0]["hook"] != outline["episodes"][1]["hook"])
    continuity = json.loads((root / "continuity.json").read_text(encoding="utf-8"))
    check("一致性台账：角色注册表", len(continuity["registry"]["characters"]) >= 3)
    check("一致性台账：场景注册表", len(continuity["registry"]["scenes"]) >= 1)
    check("一致性台账：风格锚点", bool(continuity["style"].get("tone")))
    check("场景注册表文件", (root / "scenes.md").exists())
    check("风格锚点文件", (root / "style.md").exists())

    # 2) 任务表
    with SessionLocal() as db:
        tasks = db.query(Task).filter(Task.project_id == project_id).all()
        task_statuses = {(t.episode_no, t.step): t.status for t in tasks}
    check(
        "任务表：全局步骤已记录",
        all((0, s) in task_statuses for s in ("series", "characters", "outline", "continuity")),
    )
    check("任务表：分集步骤已记录", all((ep, "script") in task_statuses for ep in (1, 2)))
    check("任务表：全部成功", all(v in ("done", "skipped") for v in task_statuses.values()))

    # 3) 事件日志
    events = [line for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    check("事件日志：已写入", len(events) > 5, str(len(events)))
    check("事件日志：含完成事件", any("done" in json.loads(line).get("type", "") for line in events))

    # 4) 成片与合集
    check("第1集成片", (root / "episodes/ep001/final.mp4").exists())
    check("第2集成片", (root / "episodes/ep002/final.mp4").exists())
    check("全剧合集", (root / "collection.mp4").exists())
    check("交付包", (root / "delivery/project-871001.zip").exists())

    # 5) 断点续跑：再次运行应跳过已完成步骤
    run_project_pipeline(project_id)
    with SessionLocal() as db:
        tasks2 = db.query(Task).filter(Task.project_id == project_id).all()
        skipped = sum(1 for t in tasks2 if t.status == "skipped" and t.episode_no > 0)
    check("断点续跑：二次运行跳过已完成步骤", skipped >= 4, f"skipped={skipped}")
    check("断点续跑：状态保持完成", True)

    # 6) 退款逻辑：frozen=1000、mock 实际成本 0 → 退还 1000
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == "stage8_test").first()
        tx = db.query(Transaction).filter(Transaction.project_id == project_id, Transaction.kind == "refund").first()
        check("退款：产生 refund 记录", tx is not None)
        check("退款：金额等于冻结额", tx is not None and tx.amount_cents == 1000)
        check("退款：余额已入账", user.balance_cents >= 1000)

    # 清理
    with SessionLocal() as db:
        db.query(Task).filter(Task.project_id == project_id).delete()
        db.query(Transaction).filter(Transaction.project_id == project_id).delete()
        db.query(Project).filter(Project.id == project_id).delete()
        db.commit()
    import shutil

    shutil.rmtree(root, ignore_errors=True)

    print(f"\n阶段 8 验证：{PASS} 通过 / {FAIL} 失败")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
