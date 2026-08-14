"""项目产物目录管理：所有生成内容落在 backend/data/projects/<id>/ 下。"""

import json
from pathlib import Path

from ..config import PROJECTS_DIR


def project_dir(project_id: int) -> Path:
    return PROJECTS_DIR / f"project-{project_id}"


def episodes_dir(project_id: int) -> Path:
    return project_dir(project_id) / "episodes"


def episode_dir(project_id: int, episode: int) -> Path:
    return episodes_dir(project_id) / f"ep{episode:03d}"


def ensure_project_dirs(project_id: int) -> None:
    for d in (project_dir(project_id), episodes_dir(project_id)):
        d.mkdir(parents=True, exist_ok=True)


def write_text(project_id: int, rel_path: str, content: str) -> Path:
    path = project_dir(project_id) / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def write_json(project_id: int, rel_path: str, data: dict) -> Path:
    return write_text(project_id, rel_path, json.dumps(data, ensure_ascii=False, indent=2))


def read_json(project_id: int, rel_path: str) -> dict:
    path = project_dir(project_id) / rel_path
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(project_id: int, rel_path: str) -> str:
    path = project_dir(project_id) / rel_path
    return path.read_text(encoding="utf-8") if path.exists() else ""


def to_markdown(title: str, data: dict) -> str:
    """把结构化 JSON 转成可读的 Markdown 文件。"""

    def fmt(value, indent=0):
        if isinstance(value, dict):
            lines = []
            for k, v in value.items():
                lines.append(f"{'  ' * indent}- **{k}**：{fmt(v, indent + 1)}")
            return "\n".join(lines)
        if isinstance(value, list):
            return "\n" + "\n".join(f"{'  ' * indent}- {fmt(item, indent + 1)}" for item in value)
        return str(value)

    return f"# {title}\n\n" + fmt(data) + "\n"
