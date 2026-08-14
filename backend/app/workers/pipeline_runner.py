"""流水线编排器：后台线程按阶段执行内容生成，实时更新进度。"""

import logging
import threading

from ..config import settings
from ..db import SessionLocal
from ..models import Project
from ..services import characters as characters_svc
from ..services import episodes as episodes_svc
from ..services import images as images_svc
from ..services import novel as novel_svc
from ..services import series as series_svc
from ..services import shots as shots_svc
from ..services.project_store import ensure_project_dirs

logger = logging.getLogger(__name__)


def _update(project_id: int, stage: str, progress: float, status: str | None = None, error: str = "") -> None:
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        if project is None:
            return
        project.stage = stage
        project.progress = progress
        if status:
            project.status = status
        if error:
            project.error = error
        db.commit()


def run_project_pipeline(project_id: int) -> None:
    """执行内容生成流水线（阶段1：LLM 全链路）。"""
    try:
        with SessionLocal() as db:
            project = db.get(Project, project_id)
            if project is None:
                return
            idea, random_mode = project.idea, project.random_mode
            genre, episode_count = project.genre, project.episode_count
            seconds = project.seconds_per_episode

        ensure_project_dirs(project_id)
        _update(project_id, "series", 0.03, status="running")
        series = series_svc.generate_series(project_id, idea, random_mode, genre, episode_count)

        _update(project_id, "characters", 0.15)
        characters = characters_svc.generate_characters(project_id, series)

        _update(project_id, "episodes", 0.25)
        episodes = episodes_svc.generate_episodes(project_id, series, characters, episode_count, seconds)

        _update(project_id, "shots", 0.65)
        for script in episodes:
            shots_svc.generate_shots(project_id, script, characters, script["episode"])

        if settings.media_enabled or settings.mock_media:
            _update(project_id, "images", 0.72)
            images_svc.generate_project_images(project_id, series, characters)

        _update(project_id, "novel", 0.9)
        novel_svc.generate_novel(project_id, series, episodes)

        with SessionLocal() as db:
            project = db.get(Project, project_id)
            project.title = series.get("title", project.title) or project.title
            project.novel_ready = True
            project.stage = "delivery"
            project.progress = 1.0
            project.status = "done"
            project.error = ""
            db.commit()
        logger.info("流水线完成 project_id=%s provider=%s", project_id, settings.llm_provider)
    except Exception as exc:  # noqa: BLE001
        logger.exception("流水线失败 project_id=%s", project_id)
        _update(project_id, "failed", 0.0, status="failed", error=str(exc))


def start_pipeline(project_id: int) -> None:
    """在后台线程启动流水线，不阻塞请求。"""
    thread = threading.Thread(target=run_project_pipeline, args=(project_id,), name=f"pipeline-{project_id}", daemon=True)
    thread.start()
