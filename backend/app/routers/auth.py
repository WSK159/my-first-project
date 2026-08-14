import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Transaction, User
from ..schemas import LoginIn, RegisterIn, TokenOut

router = APIRouter()


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        return hmac.compare_digest(hash_password(password, bytes.fromhex(salt_hex)), stored)
    except (ValueError, TypeError):
        return False


def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def get_current_user(token: str, db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="无效或过期的令牌")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


@router.post("/register", response_model=TokenOut)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.username == data.username)):
        raise HTTPException(status_code=409, detail="用户名已存在")
    user = User(username=data.username, password_hash=hash_password(data.password))
    user.balance_cents = settings.signup_bonus_cents
    db.add(user)
    db.flush()
    db.add(
        Transaction(
            user_id=user.id,
            amount_cents=settings.signup_bonus_cents,
            kind="signup",
            note="注册赠送",
        )
    )
    db.commit()
    return TokenOut(access_token=create_token(user.id), balance_cents=user.balance_cents)


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == data.username))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return TokenOut(access_token=create_token(user.id), balance_cents=user.balance_cents)

