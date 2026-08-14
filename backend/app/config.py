from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 仓库根目录：backend/app/config.py -> parents[0]=app, [1]=backend, [2]=repo root
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "backend" / "data"
PROJECTS_DIR = DATA_DIR / "projects"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI短剧工坊"
    database_url: str = f"sqlite:///{(DATA_DIR / 'platform.db').as_posix()}"
    secret_key: str = "dev-only-change-me-0123456789abcdef"
    jwt_expire_minutes: int = 1440

    # LLM
    llm_provider: str = "mock"  # mock | deepseek | openai
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

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


settings = Settings()
