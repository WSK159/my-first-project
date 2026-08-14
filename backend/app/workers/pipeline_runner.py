"""流水线编排器：大纲先行 → 角色 → 一致性台账 → 分集(并行) → 分镜 → 图片 → 视频 → 音频 → 合成 → 交付。

能力：
- 任务表持久化（Task 行记录每集每步骤状态/尝试次数/错误）
- 断点续跑（已完成产物直接跳过；服务重启后自动恢复）
- 失败自动重试（指数退避，最多 task_retry_attempts 次）
- 按集预算（超支自动跳过该集昂贵步骤，不拖垮整剧）
- SSE 事件日志（events.jsonl，前端实时进度）
- 实际消耗计费与冻结退款
- BYOK（用户自带 Key 覆盖平台配置）
"""

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from ..config import settings
from ..db import SessionLocal
from ..models import Project, Task, Transaction
from ..services import (
    audio as audio_svc,
    assembly as assembly_svc,
    characters as characters_svc,
    continuity as continuity_svc,
    delivery as delivery_svc,
    episodes as episodes_svc,
    events,
    images as images_svc,
    keys,
    novel as novel_svc,
    outline as outline_svc,
    series as series_svc,
    shots as shots_svc,
    subtitles as subtitles_svc,
    videos as videos_svc,
)
from ..services.project_store import ensure_project_dirs, project_dir, read_json

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_running: set[int] = set()


# ---------- 工具 ----------


def _update(project_id: int, stage: str, progress: float, status: str | None = None, error: str = "") -> None:
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        if project is None:
            return
        project.stage = stage
        project.progress = progress
        if status:
            project.status = status
        if error is not None:
            project.error = error
        db.commit()
    events.append_event(project_id, {"type": "stage", "stage": stage, "progress": progress, "message": stage})


def _emit(project_id: int, etype: str, message: str, episode: int = 0, progress: float | None = None) -> None:
    row: dict = {"type": etype, "message": message}
    if episode:
        row["episode"] = episode
    if progress is not None:
        row["progress"] = progress
    events.append_event(project_id, row)


def _upsert_task(
    project_id: int,
    episode: int,
    step: str,
    *,
    status: str | None = None,
    error: str = "",
    payload: dict | None = None,
    result: dict | None = None,
) -> Task:
    with SessionLocal() as db:
        task = (
            db.query(Task)
            .filter(Task.project_id == project_id, Task.episode_no == episode, Task.step == step)
            .first()
        )
        if task is None:
            task = Task(project_id=project_id, episode_no=episode, step=step)
            db.add(task)
        if status is not None:
            task.status = status
        if error:
            task.error = error
        if payload is not None:
            task.payload_json = json.dumps(payload, ensure_ascii=False)
        if result is not None:
            task.result_json = json.dumps(result, ensure_ascii=False)
        db.commit()
        return task


def _mark_done(project_id: int, episode: int, step: str, result: dict | None = None) -> None:
    _upsert_task(project_id, episode, step, status="done", result=result or {})


def _retry(name: str, fn, attempts: int | None = None):
    """指数退避重试：2^attempt 秒，封顶 8 秒。"""
    max_attempts = attempts or settings.task_retry_attempts
    last_exc: Exception | None = None
    for i in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if i >= max_attempts:
                break
            delay = min(2**i, 8)
            logger.warning("%s 第 %d/%d 次失败，%.1fs 后重试：%s", name, i, max_attempts, delay, exc)
            time.sleep(delay)
    raise RuntimeError(f"{name} 重试 {max_attempts} 次仍失败：{last_exc}")


def _artifact(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def _ep_artifact(project_id: int, episode: int, rel: str) -> Path:
    return project_dir(project_id) / "episodes" / f"ep{episode:03d}" / rel


def _episode_done(project_id: int, episode: int, step: str) -> bool:
    markers = {
        "script": "script.json",
        "shots": "video-prompts.json",
        "videos": "videos-manifest.json",
        "audio": "audio-manifest.json",
        "assembly": "final.mp4",
    }
    if step == "videos":
        manifest = read_json(project_id, "videos-manifest.json")
        clips = manifest.get("episodes", {}).get(str(episode), [])
        return bool(clips) and all(_artifact(project_dir(project_id) / c["video"]) for c in clips)
    if step == "audio":
        manifest = read_json(project_id, "audio-manifest.json")
        rows = manifest.get(str(episode), [])
        return bool(rows) and all(_artifact(project_dir(project_id) / r["audio"]) for r in rows)
    return _artifact(_ep_artifact(project_id, episode, markers[step]))


def _step_cost_cents(step: str, result: dict) -> int:
    """按实际产出估算消耗（分）。mock 档为 0；真实档按秒与调用次数估算。"""
    if result.get("provider") == "mock" or settings.llm_provider == "mock":
        return 0
    if step == "videos":
        seconds = int(result.get("seconds", 0))
        factor = 2 if result.get("tier") == "quality" else 1
        return int(seconds * settings.price_video_cents_per_second * settings.platform_markup * factor)
    if step in ("script", "shots", "series", "characters", "outline", "continuity", "novel"):
        return settings.price_llm_input_cents_per_m // 20
    return 0


def _episode_spent(project_id: int, episode: int) -> int:
    """累计某集已完成步骤的估算消耗（分）。"""
    total = 0
    with SessionLocal() as db:
        tasks = (
            db.query(Task)
            .filter(Task.project_id == project_id, Task.episode_no == episode, Task.status == "done")
            .all()
        )
        for task in tasks:
            try:
                result = json.loads(task.result_json) if task.result_json else {}
            except json.JSONDecodeError:
                result = {}
            total += int(result.get("cost_cents", 0))
    return total


# ---------- 各阶段 ----------


def _stage_global(project_id: int, step: str, rel_artifact: str, fn, progress: float, stage: str) -> dict:
    """全局步骤：产物存在则跳过，否则重试执行并记录任务。"""
    path = project_dir(project_id) / rel_artifact
    _upsert_task(project_id, 0, step, status="running", payload={"artifact": rel_artifact})
    if _artifact(path):
        _upsert_task(project_id, 0, step, status="skipped", result={"skipped": True})
        _update(project_id, stage, progress)
        return read_json(project_id, rel_artifact) if rel_artifact.endswith(".json") else {}
    result = _retry(f"全局步骤 {step}", fn)
    _mark_done(project_id, 0, step, {"cost_cents": _step_cost_cents(step, result or {})})
    _update(project_id, stage, progress)
    return result or {}


def _stage_episode(project_id: int, episode: int, step: str, marker_fn, fn, progress_base: float) -> bool:
    """单集步骤：已完成则跳过，失败重试。返回是否成功。"""
    _upsert_task(project_id, episode, step, status="running")
    if marker_fn():
        _upsert_task(project_id, episode, step, status="skipped", result={"skipped": True})
        return True
    try:
        result = _retry(f"第{episode}集 {step}", fn)
        cost = _step_cost_cents(step, result or {})
        extra = result if isinstance(result, dict) else {}
        _mark_done(project_id, episode, step, {"cost_cents": cost, **extra})
        _emit(project_id, "step_done", f"第{episode}集 {step} 完成", episode=episode, progress=progress_base)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("第%s集 %s 失败", episode, step)
        _upsert_task(project_id, episode, step, status="failed", error=str(exc))
        _emit(project_id, "step_failed", f"第{episode}集 {step} 失败：{exc}", episode=episode)
        return False


def _run_parallel(project_id: int, steps: list[tuple[int, callable]]) -> int:
    """并行执行各集独立步骤（受 llm_max_workers 限制），返回成功数。
    单集失败已在 _stage_episode 内部记录，不抛给其他集。"""
    if not steps:
        return 0
    ok = 0
    with ThreadPoolExecutor(max_workers=settings.llm_max_workers) as pool:
        futures = {pool.submit(fn, ep): ep for ep, fn in steps}
        for fut in as_completed(futures):
            try:
                if fut.result():
                    ok += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("并行步骤异常（ep=%s）：%s", futures[fut], exc)
    return ok


# ---------- 主流程 ----------


def run_project_pipeline(project_id: int) -> None:
    with _lock:
        if project_id in _running:
            logger.info("project_id=%s 已在运行，跳过", project_id)
            return
        _running.add(project_id)
    try:
        _run_inner(project_id)
    finally:
        with _lock:
            _running.discard(project_id)


def _run_inner(project_id: int) -> None:
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        if project is None:
            return
        idea, random_mode = project.idea, project.random_mode
        genre, episode_count = project.genre, project.episode_count
        seconds = project.seconds_per_episode
        tier = project.video_tier
        owner_id = project.owner_id
        frozen = project.frozen_cents
    ensure_project_dirs(project_id)
    _update(project_id, "running", 0.01, status="running", error="")
    overrides = keys.get_user_overrides(owner_id)
    api_key = overrides.get("seedance")
    audio_key = overrides.get("seed_audio")
    image_key = overrides.get("seedream")
    user_id = owner_id if overrides.get("llm") else None
    _emit(project_id, "info", f"开始生成：{episode_count} 集 × {seconds} 秒，档位 {tier}")

    # 1) 系列设定
    series = _stage_global(
        project_id, "series", "series.json",
        lambda: series_svc.generate_series(project_id, idea, random_mode, genre, episode_count, user_id=user_id),
        0.04, "series",
    )
    # 2) 角色设定
    characters = _stage_global(
        project_id, "characters", "characters.json",
        lambda: characters_svc.generate_characters(project_id, series, user_id=user_id),
        0.08, "characters",
    )
    # 3) 大纲先行
    outline = _stage_global(
        project_id, "outline", "outline.json",
        lambda: outline_svc.generate_outline(project_id, series, characters, episode_count, user_id=user_id),
        0.12, "outline",
    )
    _emit(project_id, "outline_ready", f"全剧大纲完成：{len((outline or {}).get('episodes', []))} 集")
    # 4) 一致性台账
    continuity = _stage_global(
        project_id, "continuity", "continuity.json",
        lambda: continuity_svc.build_consistency_ledger(project_id, series, characters, user_id=user_id),
        0.16, "continuity",
    )
    _emit(project_id, "continuity_ready", "全剧一致性台账完成（角色/场景/风格已锁定）")

    # 5) 分集剧本（并行 + 逐集重试）
    outline_rows = {r.get("episode"): r for r in (outline or {}).get("episodes", [])}
    _update(project_id, "episodes", 0.22)
    _upsert_task(project_id, 0, "episodes-batch", status="running")
    scripts = episodes_svc.generate_episodes(
        project_id, series, characters, episode_count, seconds, outline, continuity, user_id=user_id
    )
    script_map: dict[int, dict] = {}
    for script in scripts:
        script_map[script["episode"]] = script
    for ep in range(1, episode_count + 1):
        if _episode_done(project_id, ep, "script"):
            script_map.setdefault(ep, read_json(project_id, f"episodes/ep{ep:03d}/script.json"))
            _upsert_task(project_id, ep, "script", status="skipped", result={"skipped": True})
            continue
        ok = _stage_episode(
            project_id, ep, "script",
            lambda e=ep: _episode_done(project_id, e, "script"),
            lambda e=ep: episodes_svc.generate_episode(
                project_id, series, characters, e, seconds, outline_rows.get(e), continuity, user_id=user_id
            ),
            0.24,
        )
        if ok:
            script_map.setdefault(ep, read_json(project_id, f"episodes/ep{ep:03d}/script.json"))
    _mark_done(project_id, 0, "episodes-batch", {"done": len(script_map), "total": episode_count})

    # 6) 分镜提示词（按集）
    shots_map: dict[int, dict] = {}
    _update(project_id, "shots", 0.4)
    for ep in range(1, episode_count + 1):
        script = script_map.get(ep)
        if script is None:
            continue
        ok = _stage_episode(
            project_id, ep, "shots",
            lambda e=ep: _episode_done(project_id, e, "shots"),
            lambda s=script, e=ep: shots_svc.generate_shots(project_id, s, characters, e, continuity, user_id=user_id),
            0.42,
        )
        if ok:
            shots_map[ep] = read_json(project_id, f"episodes/ep{ep:03d}/video-prompts.json")

    media_enabled = settings.media_enabled or settings.mock_media
    if media_enabled:
        # 7) 图片（全局一次，产物存在跳过）
        if not _artifact(project_dir(project_id) / "cover.png"):
            _upsert_task(project_id, 0, "images", status="running")
            _retry(
                "图片生成",
                lambda: images_svc.generate_project_images(project_id, series, characters, continuity, api_key=image_key),
            )
            _mark_done(project_id, 0, "images", {"cost_cents": 0})
        else:
            _upsert_task(project_id, 0, "images", status="skipped", result={"skipped": True})
        _update(project_id, "images", 0.52)

        # 每集预算：按冻结金额均摊
        ep_budget = int(frozen / max(episode_count, 1) * settings.episode_budget_ratio) if frozen > 0 else 0

        # 8) 视频（按集）
        _update(project_id, "videos", 0.58)
        video_steps = []
        for ep in range(1, episode_count + 1):
            script = script_map.get(ep)
            shots = shots_map.get(ep)
            if script is None or shots is None:
                continue
            if ep_budget and _episode_spent(project_id, ep) >= ep_budget:
                _upsert_task(project_id, ep, "videos", status="skipped", error="超出该集预算，已跳过视频生成")
                _emit(project_id, "budget_skip", f"第{ep}集超出预算，跳过视频/音频/合成", episode=ep)
                continue

            def video_fn(e=ep, s=script, sh=shots):
                manifest = videos_svc.generate_project_videos(
                    project_id, [s], {e: sh}, continuity, api_key=api_key
                )
                clips = manifest.get("episodes", {}).get(str(e), [])
                seconds_sum = 0
                for c in clips:
                    video = project_dir(project_id) / c["video"]
                    if video.exists():
                        try:
                            from ..services.assembly import probe_duration

                            seconds_sum += int(probe_duration(video))
                        except Exception:  # noqa: BLE001
                            seconds_sum += 10
                return {"seconds": seconds_sum, "clips": len(clips), "provider": "seedance" if api_key else "mock", "tier": tier}

            video_steps.append(
                (
                    ep,
                    lambda e=ep, vf=video_fn: _stage_episode(
                        project_id, e, "videos",
                        lambda ee=e: _episode_done(project_id, ee, "videos"),
                        lambda ee=e: vf(ee),
                        0.62,
                    ),
                )
            )
        _run_parallel(project_id, video_steps)

        # 9) 音频（按集）
        _update(project_id, "audio", 0.72)
        audio_steps = []
        for ep in range(1, episode_count + 1):
            script = script_map.get(ep)
            if script is None:
                continue
            if ep_budget and _episode_spent(project_id, ep) >= ep_budget:
                continue

            def audio_fn(e=ep, s=script):
                manifest = audio_svc.generate_project_audio(project_id, series, characters, [s], api_key=audio_key)
                rows = manifest.get(str(e), [])
                seconds_sum = sum(float(r.get("duration", 0)) for r in rows)
                return {"seconds": seconds_sum, "provider": "seed-audio" if audio_key else "mock"}

            audio_steps.append(
                (
                    ep,
                    lambda e=ep, af=audio_fn: _stage_episode(
                        project_id, e, "audio",
                        lambda ee=e: _episode_done(project_id, ee, "audio"),
                        lambda ee=e: af(ee),
                        0.76,
                    ),
                )
            )
        _run_parallel(project_id, audio_steps)

        # 10) 合成与字幕（按集）
        _update(project_id, "assembly", 0.84)
        assembly_steps = []
        for ep in range(1, episode_count + 1):
            if not _episode_done(project_id, ep, "videos"):
                continue
            if ep_budget and _episode_spent(project_id, ep) >= ep_budget:
                continue

            def assembly_fn(e=ep):
                assembled = assembly_svc.assemble_episode(project_id, e)
                subtitled = subtitles_svc.burn_subtitles(project_id, e, assembled)
                final = assembly_svc.finalize_episode(project_id, e, subtitled)
                return {"final": str(final)}

            assembly_steps.append(
                (
                    ep,
                    lambda e=ep, afn=assembly_fn: _stage_episode(
                        project_id, e, "assembly",
                        lambda ee=e: _episode_done(project_id, ee, "assembly"),
                        lambda ee=e: afn(ee),
                        0.9,
                    ),
                )
            )
        _run_parallel(project_id, assembly_steps)

    # 11) 完整小说
    if not _artifact(project_dir(project_id) / "novel.md"):
        novel_scripts = sorted(script_map.values(), key=lambda s: s.get("episode", 0))
        _retry(
            "小说生成",
            lambda: novel_svc.generate_novel(project_id, series, novel_scripts, user_id=user_id),
        )
        _mark_done(project_id, 0, "novel", {"cost_cents": _step_cost_cents("novel", {})})
    else:
        _upsert_task(project_id, 0, "novel", status="skipped", result={"skipped": True})
    _update(project_id, "novel", 0.95)

    # 12) 交付
    if media_enabled:
        if settings.collection_enabled:
            assembly_svc.build_collection(project_id)
        delivery_svc.build_delivery_package(project_id)
        _update(project_id, "delivery", 0.98)

    # 汇总状态
    failed_eps = []
    with SessionLocal() as db:
        tasks = db.query(Task).filter(Task.project_id == project_id).all()
        for task in tasks:
            if task.episode_no > 0 and task.status == "failed":
                failed_eps.append(task.episode_no)
    failed_eps = sorted(set(failed_eps))
    completed_eps = sum(1 for ep in range(1, episode_count + 1) if _episode_done(project_id, ep, "assembly"))

    actual_cost = _actual_cost(project_id)
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        if project is None:
            return
        if failed_eps or completed_eps < episode_count:
            project.status = "partial"
            project.error = (
                f"已完成 {completed_eps}/{episode_count} 集；失败集：{failed_eps[:20]}。"
                "可点击“继续生成”重试失败集。"
            )
        else:
            project.status = "done"
            project.error = ""
        project.novel_ready = _artifact(project_dir(project_id) / "novel.md")
        project.video_ready = completed_eps > 0
        project.stage = "delivery"
        project.progress = 1.0
        db.commit()
        _refund(db, project, actual_cost)
    logger.info(
        "流水线结束 project_id=%s 完成=%s/%s 失败=%s 实际成本=%s分",
        project_id, completed_eps, episode_count, failed_eps, actual_cost,
    )
    _emit(
        project_id, "done",
        f"生成结束：{completed_eps}/{episode_count} 集完成" + (f"，失败 {failed_eps}" if failed_eps else ""),
    )


def _actual_cost(project_id: int) -> int:
    """汇总任务表中记录的成本（分）。"""
    total = 0
    with SessionLocal() as db:
        tasks = db.query(Task).filter(Task.project_id == project_id, Task.status == "done").all()
        for task in tasks:
            try:
                result = json.loads(task.result_json) if task.result_json else {}
            except json.JSONDecodeError:
                result = {}
            total += int(result.get("cost_cents", 0))
    return total


def _refund(db, project: Project, actual_cost: int) -> None:
    """退还冻结与实际消耗的差额。"""
    refund = project.frozen_cents - actual_cost
    if refund > 0:
        project.frozen_cents = actual_cost
        project.owner.balance_cents += refund
        db.add(
            Transaction(
                user_id=project.owner_id,
                project_id=project.id,
                amount_cents=refund,
                kind="refund",
                note=f"项目 {project.id} 实际消耗 {actual_cost} 分，退还冻结差额",
            )
        )
        db.commit()


def start_pipeline(project_id: int) -> None:
    """启动流水线（幂等：已在运行则跳过；失败/部分完成项目可直接重入续跑）。"""
    thread = threading.Thread(target=run_project_pipeline, args=(project_id,), name=f"pipeline-{project_id}", daemon=True)
    thread.start()


def resume_projects() -> None:
    """服务启动时恢复未完成项目（pending/running/partial）。"""
    if not settings.resume_on_startup:
        return
    with SessionLocal() as db:
        rows = (
            db.query(Project)
            .filter(Project.status.in_(["pending", "running", "partial"]))
            .order_by(Project.updated_at.desc())
            .limit(settings.max_concurrent_projects)
            .all()
        )
        ids = [p.id for p in rows]
    for pid in ids:
        logger.info("启动恢复 project_id=%s", pid)
        start_pipeline(pid)
