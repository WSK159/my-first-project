import asyncio
import json
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Project, Task, User
from ..schemas import EstimateIn, EstimateOut, ProjectOut
from ..services import events
from ..services.assembly import probe_duration
from ..services.project_store import project_dir
from ..services.resource_query import check_seedance_quota, estimate_video_tokens
from ..workers.pipeline_runner import start_pipeline
from .auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

THEME_TEMPLATES = [
    {
        "name": "女频复仇 · 千金归来",
        "genre": "都市复仇",
        "idea": "被夺走一切的豪门千金，十年后携子回国复仇，却发现当年真相另有隐情",
        "episode_count": 60,
        "seconds_per_episode": 120,
        "tier": "fast",
    },
    {
        "name": "男频逆袭 · 宗门觉醒",
        "genre": "男频逆袭",
        "idea": "被逐出宗门的废柴少年，觉醒上古血脉，一路打脸归来，揭开宗门百年阴谋",
        "episode_count": 60,
        "seconds_per_episode": 120,
        "tier": "fast",
    },
    {
        "name": "女频甜宠 · 双向奔赴",
        "genre": "女频甜宠",
        "idea": "被家族安排的联姻，从互看不顺眼到双向奔赴，中间隔着一场误会与一场守护",
        "episode_count": 40,
        "seconds_per_episode": 120,
        "tier": "fast",
    },
    {
        "name": "悬疑规则 · 天黑别照镜子",
        "genre": "悬疑规则",
        "idea": "一座每到午夜就会改变规则的小镇，女主发现规则纸条背后还有一行字",
        "episode_count": 40,
        "seconds_per_episode": 120,
        "tier": "fast",
    },
    {
        "name": "都市战神 · 龙王归来",
        "genre": "男频逆袭",
        "idea": "失踪五年的战神归来，发现女儿被欺负、家业被吞，他决定让所有人为之付出代价",
        "episode_count": 60,
        "seconds_per_episode": 120,
        "tier": "fast",
    },
    {
        "name": "女频虐恋 · 破镜重圆",
        "genre": "都市复仇",
        "idea": "三年婚姻换来一纸离婚协议，女主转身惊艳全场，前夫才发现自己失去了什么",
        "episode_count": 30,
        "seconds_per_episode": 120,
        "tier": "fast",
    },
    {
        "name": "穿越女帝 · 凤临天下",
        "genre": "女频甜宠",
        "idea": "现代女律师穿越成被废的女帝，凭现代思维翻盘朝堂，收服忠犬将军",
        "episode_count": 50,
        "seconds_per_episode": 120,
        "tier": "fast",
    },
    {
        "name": "悬疑追凶 · 双面真相",
        "genre": "悬疑规则",
        "idea": "刑警与心理侧写师搭档追查连环案，每个嫌疑人都有完美不在场证明",
        "episode_count": 30,
        "seconds_per_episode": 120,
        "tier": "fast",
    },
    {
        "name": "萌宝助攻 · 爹地别跑",
        "genre": "女频甜宠",
        "idea": "天才萌宝给单身妈咪找爹地，目标锁定高冷总裁，撮合路上笑料百出",
        "episode_count": 40,
        "seconds_per_episode": 120,
        "tier": "fast",
    },
    {
        "name": "重生商战 · 逆风翻盘",
        "genre": "都市复仇",
        "idea": "重活一世的破产千金，凭借记忆里三年后的商业情报，一步步夺回家族企业",
        "episode_count": 60,
        "seconds_per_episode": 120,
        "tier": "fast",
    },
]


def _get_owned_project(project_id: int, user: User, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.get("/templates")
def theme_templates():
    return {"templates": THEME_TEMPLATES}


def estimate_cost(data: EstimateIn, balance_cents: int) -> tuple[int, dict]:
    """按档位估算成本（分）。mock 档只算 LLM 粗略成本。"""
    from ..config import settings

    # 真实档 LLM 调用次数：series+characters+outline+continuity+novel = 5 次全局，
    # 每集 = card+script+shots = 3 次；与流水线逐步骤记账保持一致
    llm_calls = 3 * data.episode_count + 5
    llm_cost = llm_calls * (settings.price_llm_input_cents_per_m // 20)
    if data.video_tier == "mock":
        video_cost = 0
    elif data.video_tier == "fast":
        seconds = data.episode_count * data.seconds_per_episode
        video_cost = int(seconds * settings.price_video_cents_per_second * settings.platform_markup)
    else:  # quality
        seconds = data.episode_count * data.seconds_per_episode
        video_cost = int(seconds * settings.price_video_cents_per_second * 2 * settings.platform_markup)
    total = llm_cost + video_cost
    return total, {"llm_cents": llm_cost, "video_cents": video_cost}


@router.post("/estimate", response_model=EstimateOut)
def estimate(data: EstimateIn, user: User = Depends(get_current_user)):
    frozen, detail = estimate_cost(data, user.balance_cents)
    quota = None
    if data.video_tier != "mock" and frozen > 0:
        try:
            seconds = data.episode_count * data.seconds_per_episode
            quota = check_seedance_quota(estimate_video_tokens(seconds))
        except Exception as exc:  # noqa: BLE001 预检失败不阻塞估算
            quota = {"available": None, "ok": None, "error": str(exc)}
    return EstimateOut(
        frozen_cents=frozen,
        balance_cents=user.balance_cents,
        sufficient=user.balance_cents >= frozen,
        detail=detail,
        quota=quota,
    )


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(data: EstimateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    frozen, _ = estimate_cost(data, user.balance_cents)
    if user.balance_cents < frozen:
        raise HTTPException(status_code=402, detail="余额不足，请先充值")
    if data.video_tier != "mock" and frozen > 0:
        try:
            seconds = data.episode_count * data.seconds_per_episode
            quota = check_seedance_quota(estimate_video_tokens(seconds))
            if quota.get("available") is True and quota.get("ok") is False:
                raise HTTPException(
                    status_code=402,
                    detail=(
                        f"火山 Seedance 套餐余量不足：还需 {quota.get('deficit_tokens', 0):.0f} tokens。"
                        "请先购买资源包或改用 mock 档。"
                    ),
                )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 预检失败仅告警，不阻塞（开发/未配置场景）
            logger.warning("资源包预检失败：%s", exc)
    user.balance_cents -= frozen
    project = Project(
        owner_id=user.id,
        idea=data.idea,
        random_mode=data.random_mode,
        genre=data.genre,
        episode_count=data.episode_count,
        seconds_per_episode=data.seconds_per_episode,
        video_tier=data.video_tier,
        status="pending",
        stage="queued",
        frozen_cents=frozen,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    start_pipeline(project.id)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Project)
        .filter(Project.owner_id == user.id)
        .order_by(Project.created_at.desc())
        .limit(100)
        .all()
    )
    return rows


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _get_owned_project(project_id, user, db)
    return project


@router.post("/{project_id}/resume")
def resume_project(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _get_owned_project(project_id, user, db)
    if project.status == "done":
        return {"status": "done", "message": "项目已完成，无需继续"}
    start_pipeline(project.id)
    return {"status": "running", "message": "已重新启动生成（已完成部分自动跳过）"}


@router.get("/{project_id}/episodes")
def episodes_status(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _get_owned_project(project_id, user, db)
    rows = []
    for ep in range(1, project.episode_count + 1):
        steps: dict[str, str] = {}
        failed: list[str] = []
        tasks = (
            db.query(Task)
            .filter(Task.project_id == project_id, Task.episode_no == ep)
            .order_by(Task.step)
            .all()
        )
        for task in tasks:
            steps[task.step] = task.status
            if task.status == "failed":
                failed.append(task.step)
        final = project_dir(project_id) / "episodes" / f"ep{ep:03d}" / "final.mp4"
        duration = 0
        if final.exists():
            try:
                duration = round(probe_duration(final), 1)
            except Exception:  # noqa: BLE001 无 ffmpeg 时容错
                duration = 0
        rows.append(
            {
                "episode": ep,
                "steps": steps,
                "failed": failed,
                "has_video": final.exists(),
                "duration_seconds": duration,
            }
        )
    return {"episodes": rows, "episode_count": project.episode_count}


@router.get("/{project_id}/events")
async def stream_events(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _get_owned_project(project_id, user, db)

    async def gen():
        snapshot = {
            "type": "snapshot",
            "status": project.status,
            "stage": project.stage,
            "progress": project.progress,
            "message": f"当前状态：{project.stage} ({round(project.progress * 100)}%)",
        }
        yield f"data: {json.dumps(snapshot, ensure_ascii=False)}\n\n"
        last_ts = 0.0
        try:
            while True:
                rows = events.read_events(project_id, after_ts=last_ts)
                for row in rows:
                    yield f"data: {json.dumps(row, ensure_ascii=False)}\n\n"
                    last_ts = row.get("ts", 0)
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.delete("/{project_id}")
def delete_project(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="项目不存在")
    data_dir = project_dir(project_id)
    db.delete(project)
    db.commit()
    if data_dir.exists():
        shutil.rmtree(data_dir)
    return {"deleted": project_id}
