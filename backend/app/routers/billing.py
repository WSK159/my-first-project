from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Transaction, User
from .auth import get_current_user

router = APIRouter()


@router.get("/balance")
def balance(user: User = Depends(get_current_user)):
    return {"balance_cents": user.balance_cents}


@router.get("/transactions")
def transactions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id)
        .order_by(Transaction.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {"kind": t.kind, "amount_cents": t.amount_cents, "note": t.note, "created_at": t.created_at}
        for t in rows
    ]

