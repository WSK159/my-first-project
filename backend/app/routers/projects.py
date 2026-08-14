from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Project, User
from ..schemas import EstimateIn, EstimateOut, ProjectOut
from ..workers.pipeline_runner import start_pipeline
from .auth import get_current_user

router = APIRouter()


def estimate_cost(data: EstimateIn, balance_cents: int) -> tuple[int, dict]:
    """按档位估算成本（分）。mock 档只算 LLM 粗略成本。"""
    from ..config import settings

    llm_cost = (
        data.episode_count
        * settings.price_llm_input_cents_per_m
        // 20  # 粗略占位：后续按实际 token 计算
    )
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
    return EstimateOut(
        frozen_cents=frozen,
        balance_cents=user.balance_cents,
        sufficient=user.balance_cents >= frozen,
        detail=detail,
    )


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(data: EstimateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    frozen, _ = estimate_cost(data, user.balance_cents)
    if user.balance_cents < frozen:
        raise HTTPException(status_code=402, detail="余额不足，请先充值")
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
    project = db.get(Project, project_id)
    if project is None or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project
