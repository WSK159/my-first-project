from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 仓库根目录：本地 backend/app/config.py -> parents[2]=repo root；Docker /app/app/config.py -> parents[1]=/app
_config_file = Path(__file__).resolve()
ROOT_DIR = (
    _config_file.parents[2]
    if (_config_file.parents[2] / "pipeline").exists()
    else _config_file.parents[1]
)
# 本地 backend/data 或 Docker 挂载 /app/data
_data_candidate = ROOT_DIR / "backend" / "data"
DATA_DIR = _data_candidate if _data_candidate.exists() else ROOT_DIR / "data"
PROJECTS_DIR = DATA_DIR / "projects"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI短剧工坊"
    database_url: str = f"sqlite:///{(DATA_DIR / 'platform.db').as_posix()}"
    secret_key: str = "dev-only-change-me-0123456789abcdef"
    jwt_expire_minutes: int = 1440
    cors_origins: str = "*"  # 逗号分隔；上线建议收紧为前端域名
    ai_subtitle_label: bool = True  # 成片字幕首行标注"AI 生成内容"

    # LLM
    llm_provider: str = "mock"  # mock | deepseek | openai
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    # MiniMax（文本/生图/生视频/TTS 全能力，CN 端点）
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimaxi.com"
    minimax_chat_model: str = "MiniMax-Text-01"
    minimax_image_model: str = "image-01"
    minimax_video_model: str = "MiniMax-H3"
    minimax_video_resolution: str = "768P"  # 768P | 2K
    minimax_tts_model: str = "speech-02-hd"
    minimax_tts_voice_female: str = "female-shaonv"
    minimax_tts_voice_male: str = "male-qn-jingying"

    # Seedream
    seedream_api_key: str = ""
    seedream_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    seedream_model: str = "doubao-seedream-5-0-260128"

    # Seedance
    seedance_api_key: str = ""
    seedance_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    seedance_model: str = "doubao-seedance-2-0-fast-260128"
    seedance_duration: int = 10
    seedance_resolution: str = "720p"
    seedance_ratio: str = "9:16"
    seedance_watermark: bool = False
    seedance_generate_audio: bool = False  # 视觉优先：音频由 Seed Audio 阶段统一生成
    seedance_poll_interval: int = 5
    seedance_max_wait_minutes: int = 30

    # Seed Audio
    seed_audio_api_key: str = ""
    seed_audio_base_url: str = "https://openspeech.bytedance.com"
    seed_audio_model: str = "seed-audio-1.0"
    seed_audio_format: str = "mp3"
    seed_audio_sample_rate: int = 24000

    # 计费（分）
    price_llm_input_cents_per_m: int = 100
    price_llm_output_cents_per_m: int = 200
    price_video_cents_per_second: int = 50
    platform_markup: float = 1.5
    signup_bonus_cents: int = 1000

    # 流水线
    llm_max_workers: int = 3          # 分集生成并发上限
    media_enabled: bool = False       # 阶段2+ 开启媒体生成后置 True
    mock_media: bool = True           # mock 档位用 ffmpeg 生成占位媒体
    task_retry_attempts: int = 3      # 每步骤最大尝试次数
    resume_on_startup: bool = True    # 服务启动时自动恢复未完成项目
    max_concurrent_projects: int = 2  # 同时运行的项目数
    episode_budget_ratio: float = 0.9 # 每集预算占均摊金额的比例（预留缓冲）
    event_log_max_lines: int = 2000   # 事件日志保留行数
    collection_enabled: bool = True   # 是否允许生成全剧合集

    # 火山资源包预检（可选：用 IAM AK/SK 查询套餐余额）
    volc_access_key: str = ""
    volc_secret_key: str = ""
    volc_region: str = "cn-beijing"
    seedance_tokens_per_second: float = 800.0  # Seedance fast 720p 粗略 token/秒（可按实际校准）


settings = Settings()
