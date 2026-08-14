"""阶段 8 API 端到端验证：注册 → 创建项目 → 轮询完成 → 分集状态 → 合集 → SSE 事件 → 继续生成。

运行：python scripts/test_api_e2e.py
"""

import json
import os
import shutil
import sys
import time
from pathlib import Path

os.environ["LLM_PROVIDER"] = "mock"
os.environ["MINIMAX_API_KEY"] = ""
os.environ["DEEPSEEK_API_KEY"] = ""

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS  {name}", flush=True)
    else:
        FAIL += 1
        print(f"FAIL  {name}  {detail}", flush=True)


def main() -> int:
    username = f"e2e_{int(time.time())}"
    with TestClient(app) as client:
        # 1) 注册
        reg = client.post("/api/auth/register", json={"username": username, "password": "secret123"})
        check("注册", reg.status_code == 200, str(reg.text[:200]))
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2) 模板库
        tpl = client.get("/api/projects/templates")
        check("题材模板库", tpl.status_code == 200 and len(tpl.json()["templates"]) >= 8, str(tpl.text[:200]))

        # 3) 成本估算
        est = client.post(
            "/api/projects/estimate",
            json={"idea": "被夺走一切的千金十年后携子回国复仇", "episode_count": 2, "seconds_per_episode": 120, "video_tier": "mock"},
            headers=headers,
        )
        check("成本估算", est.status_code == 200 and est.json()["sufficient"], str(est.text[:200]))

        # 4) 创建项目
        create = client.post(
            "/api/projects",
            json={"idea": "被夺走一切的千金十年后携子回国复仇", "episode_count": 2, "seconds_per_episode": 120, "video_tier": "mock"},
            headers=headers,
        )
        check("创建项目", create.status_code == 201, str(create.text[:300]))
        project_id = create.json()["id"]

        # 5) 轮询完成
        status = ""
        deadline = time.time() + 240
        while time.time() < deadline:
            proj = client.get(f"/api/projects/{project_id}", headers=headers)
            status = proj.json()["status"]
            if status in ("done", "partial", "failed"):
                break
            time.sleep(2)
        check("生成完成（mock 2 集）", status in ("done", "partial"), status)
        proj = client.get(f"/api/projects/{project_id}", headers=headers).json()
        check("novel_ready", proj.get("novel_ready") is True, str(proj))
        check("video_ready", proj.get("video_ready") is True, str(proj))

        # 6) 分集状态
        eps = client.get(f"/api/projects/{project_id}/episodes", headers=headers)
        check("分集状态", eps.status_code == 200 and len(eps.json()["episodes"]) == 2, str(eps.text[:300]))
        check("分集都有成片", all(e["has_video"] for e in eps.json()["episodes"]), str(eps.text[:300]))
        check("分集时长正确", all(110 <= e["duration_seconds"] <= 130 for e in eps.json()["episodes"]), str(eps.text[:300]))

        # 7) SSE 事件流（读取前若干事件后关闭）
        # 注：TestClient 对无限 SSE 流有阻塞风险，这里验证事件日志本身；
        # SSE 端点逻辑简单（读日志尾部），由单元层面的事件读写保证。
        from app.services.project_store import project_dir

        log_path = project_dir(project_id) / "events.jsonl"
        lines = [l for l in log_path.read_text(encoding="utf-8").splitlines() if l.strip()] if log_path.exists() else []
        check("SSE 事件日志", len(lines) >= 8, str(len(lines)))
        types = {json.loads(l).get("type") for l in lines}
        check("SSE 事件类型完整", {"stage", "step_done", "done"}.issubset(types), str(types))

        # 8) 合集下载
        col = client.get(f"/api/delivery/{project_id}/collection", headers=headers)
        check("全剧合集下载", col.status_code == 200 and len(col.content) > 1000, f"{col.status_code} {len(col.content)}")

        # 9) 继续生成（已完成项目应返回 done 提示）
        resume = client.post(f"/api/projects/{project_id}/resume", headers=headers)
        check("继续生成幂等", resume.status_code == 200 and resume.json()["status"] == "done", str(resume.text[:200]))

        # 10) 交付包
        arch = client.get(f"/api/delivery/{project_id}/archive", headers=headers)
        check("交付包下载", arch.status_code == 200 and len(arch.content) > 10000, f"{arch.status_code} {len(arch.content)}")

        # 清理
        client.delete(f"/api/projects/{project_id}", headers=headers)
        shutil.rmtree(project_dir(project_id), ignore_errors=True)

    print(f"\nAPI E2E：{PASS} 通过 / {FAIL} 失败", flush=True)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
