from datetime import datetime

from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    balance_cents: int = 0


class EstimateIn(BaseModel):
    idea: str = ""
    random_mode: bool = False
    genre: str = ""
    episode_count: int = Field(default=1, ge=1, le=20)
    seconds_per_episode: int = Field(default=60, ge=15, le=180)
    video_tier: str = Field(default="mock", pattern="^(mock|fast|quality)$")


class ProjectOut(BaseModel):
    id: int
    title: str
    idea: str
    random_mode: bool
    genre: str
    episode_count: int
    seconds_per_episode: int
    video_tier: str
    status: str
    progress: float
    stage: str
    error: str
    frozen_cents: int
    novel_ready: bool
    video_ready: bool
    created_at: datetime
    updated_at: datetime


class EstimateOut(BaseModel):
    frozen_cents: int
    balance_cents: int
    sufficient: bool
    detail: dict

