from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Project, User
from ..services.project_store import project_dir
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
    path = project_dir(project_id) / "novel.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="小说文件缺失")
    return FileResponse(path, media_type="text/markdown; charset=utf-8", filename="novel.md")


@router.get("/{project_id}/video")
def download_video(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _get_owned_project(project_id, user, db)
    if not project.video_ready:
        raise HTTPException(status_code=404, detail="成片尚未生成")
    path = project_dir(project_id) / "episodes" / "ep001" / "final.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="成片文件缺失")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@router.get("/{project_id}/video/{episode}")
def download_episode_video(
    project_id: int, episode: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    project = _get_owned_project(project_id, user, db)
    if not project.video_ready:
        raise HTTPException(status_code=404, detail="成片尚未生成")
    path = project_dir(project_id) / "episodes" / f"ep{episode:03d}" / "final.mp4"
    if not path.exists():
        raise HTTPException(status_code=404, detail="该集成片缺失")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@router.get("/{project_id}/archive")
def download_archive(project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _get_owned_project(project_id, user, db)
    if not (project.novel_ready and project.video_ready):
        raise HTTPException(status_code=404, detail="交付包尚未就绪")
    path = project_dir(project_id) / "delivery" / f"project-{project_id}.zip"
    if not path.exists():
        raise HTTPException(status_code=404, detail="交付包文件缺失")
    return FileResponse(path, media_type="application/zip", filename=path.name)
