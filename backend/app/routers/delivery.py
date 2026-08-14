from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Project, User
from .auth import get_current_user

router = APIRouter()


def _get_owned_project(project_id: int, user: User, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.get("/{project_id}/novel")
def download_novel(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _get_owned_project(project_id, user, db)
    if not project.novel_ready:
        raise HTTPException(status_code=404, detail="小说尚未生成")
    # TODO(阶段1): 从项目数据目录读取 novel.md 返回
    return {"detail": "阶段1实现"}


@router.get("/{project_id}/video")
def download_video(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _get_owned_project(project_id, user, db)
    if not project.video_ready:
        raise HTTPException(status_code=404, detail="成片尚未生成")
    # TODO(阶段5): 从项目数据目录读取 final.mp4 返回
    return {"detail": "阶段5实现"}


@router.get("/{project_id}/archive")
def download_archive(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _get_owned_project(project_id, user, db)
    if not (project.novel_ready and project.video_ready):
        raise HTTPException(status_code=404, detail="交付包尚未就绪")
    # TODO(阶段5): 打包 zip 返回
    return {"detail": "阶段5实现"}

