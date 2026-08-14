"""项目事件日志：持久化追加式日志，供 SSE 实时进度与断点续跑使用。"""

import json
import threading
import time
from pathlib import Path

from ..config import settings
from .project_store import project_dir

_write_lock = threading.Lock()


def _log_path(project_id: int) -> Path:
    return project_dir(project_id) / "events.jsonl"


def append_event(project_id: int, event: dict) -> None:
    """追加一条事件：{ts, type, stage, episode, message, progress}。"""
    row = {"ts": time.time(), **event}
    path = _log_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _write_lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    # 防无限增长：超过上限时截断
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) > settings.event_log_max_lines:
        path.write_text("\n".join(lines[-settings.event_log_max_lines :]) + "\n", encoding="utf-8")


def read_events(project_id: int, after_ts: float = 0.0) -> list[dict]:
    path = _log_path(project_id)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("ts", 0) > after_ts:
            rows.append(row)
    return rows
