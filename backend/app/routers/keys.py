"""BYOK：用户自带 API Key 管理（加密存储，仅本人可用）。"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User, UserKey
from ..services.keys import decrypt_value, encrypt_value
from .auth import get_current_user

router = APIRouter()

PROVIDERS = ("llm", "seedream", "seedance", "seed_audio")
PROVIDER_LABELS = {
    "llm": "文本大模型（DeepSeek 兼容）",
    "seedream": "生图（火山方舟 Seedream）",
    "seedance": "生视频（火山方舟 Seedance）",
    "seed_audio": "配音（火山语音 Seed Audio）",
}


class KeyIn(BaseModel):
    provider: str = Field(pattern="^(llm|seedream|seedance|seed_audio)$")
    api_key: str = Field(min_length=4, max_length=512)


class KeyOut(BaseModel):
    provider: str
    label: str
    configured: bool
    api_key_masked: str = ""


@router.get("", response_model=list[KeyOut])
def list_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = {r.provider: r for r in db.query(UserKey).filter(UserKey.user_id == user.id).all()}
    result = []
    for provider in PROVIDERS:
        row = rows.get(provider)
        result.append(
            KeyOut(
                provider=provider,
                label=PROVIDER_LABELS[provider],
                configured=bool(row),
                api_key_masked=decrypt_value(row.ciphertext)[:6] + "…" if row else "",
            )
        )
    return result


@router.post("")
def save_key(data: KeyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(UserKey).filter(UserKey.user_id == user.id, UserKey.provider == data.provider).first()
    if row is None:
        row = UserKey(user_id=user.id, provider=data.provider)
        db.add(row)
    row.ciphertext = encrypt_value(data.api_key)
    row.label = PROVIDER_LABELS[data.provider]
    db.commit()
    return {"provider": data.provider, "configured": True}


@router.delete("/{provider}")
def delete_key(provider: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail="未知 provider")
    row = db.query(UserKey).filter(UserKey.user_id == user.id, UserKey.provider == provider).first()
    if row is not None:
        db.delete(row)
        db.commit()
    return {"provider": provider, "configured": False}
