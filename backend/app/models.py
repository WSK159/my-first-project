from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    balance_cents: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    projects: Mapped[list["Project"]] = relationship(back_populates="owner")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    idea: Mapped[str] = mapped_column(Text, default="")
    random_mode: Mapped[bool] = mapped_column(default=False)
    genre: Mapped[str] = mapped_column(String(64), default="")
    episode_count: Mapped[int] = mapped_column(Integer, default=1)
    seconds_per_episode: Mapped[int] = mapped_column(Integer, default=60)
    video_tier: Mapped[str] = mapped_column(String(32), default="mock")  # mock | fast | quality
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|running|done|failed
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    stage: Mapped[str] = mapped_column(String(64), default="created")
    error: Mapped[str] = mapped_column(Text, default="")
    frozen_cents: Mapped[int] = mapped_column(Integer, default=0)
    novel_ready: Mapped[bool] = mapped_column(default=False)
    video_ready: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner: Mapped[User] = relationship(back_populates="projects")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    amount_cents: Mapped[int] = mapped_column(Integer)  # 正=充值/赠送，负=扣费
    kind: Mapped[str] = mapped_column(String(32), default="adjust")  # signup|charge|spend|refund
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

