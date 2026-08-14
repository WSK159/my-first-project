"""用户自带 Key（BYOK）加密存储：提供加密/解密与按用户读取覆盖配置。"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from ..config import settings


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_value(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_value(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""


def get_user_overrides(user_id: int) -> dict:
    """返回该用户的密钥覆盖：{"llm": "...", "seedream": "...", "seedance": "...", "seed_audio": "..."}。
    未配置的 provider 不出现在结果中。"""
    from ..db import SessionLocal
    from ..models import UserKey

    overrides: dict[str, str] = {}
    with SessionLocal() as db:
        rows = db.query(UserKey).filter(UserKey.user_id == user_id).all()
        for row in rows:
            value = decrypt_value(row.ciphertext)
            if value:
                overrides[row.provider] = value
    return overrides
