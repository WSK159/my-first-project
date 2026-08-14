"""流水线编排器（骨架）。

后续阶段按顺序接入：
1. LLM 生成 series.md / characters.md（阶段1）
2. 分集剧本 + 分镜提示词（阶段1）
3. Seedream 角色/场景图（阶段2）
4. Seedance 视频分段生成（阶段3）
5. Seed Audio 配音/音乐（阶段4）
6. FFmpeg 合成 + 字幕 + 交付包（阶段5）
"""

import logging

from ..config import settings

logger = logging.getLogger(__name__)


STAGES = [
    ("series", 0.05, "生成系列设定"),
    ("characters", 0.12, "生成角色设定"),
    ("episodes", 0.25, "生成分集剧本"),
    ("shots", 0.32, "生成分镜提示词"),
    ("images", 0.45, "生成角色/场景图"),
    ("videos", 0.75, "生成视频片段"),
    ("audio", 0.88, "生成配音与音乐"),
    ("assembly", 0.98, "后期合成与字幕"),
    ("delivery", 1.0, "打包交付"),
]


def run_project_pipeline(project_id: int) -> None:
    """执行项目流水线。骨架：先打印阶段计划，后续逐步替换为真实调用。"""
    logger.info("流水线启动 project_id=%s provider=%s", project_id, settings.llm_provider)
    for stage, _, label in STAGES:
        logger.info("阶段 %s：%s", stage, label)
    # TODO(阶段1+): 实现各阶段，并持久化进度/产物

