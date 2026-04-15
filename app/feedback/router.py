"""
Bu faylni app/feedback/router.py sifatida saqlang
va main.py ga qo'shing:
"""

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Feedback, User
from ..utils.jwt import decode_token
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/feedback", tags=["Feedback"])


class FeedbackCreate(BaseModel):
    message: str
    rating: Optional[int] = None


@router.post("/submit")
def submit_feedback(
    data: FeedbackCreate,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Foydalanuvchi feedback qoldiradi.
    Login qilgan bo'lsa — ismi avtomatik olinadi.
    Guest bo'lsa — anonymous saqlanadi.
    """
    user_id = None
    user_name = "Anonymous"
    user_email = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        payload = decode_token(token)
        if payload:
            user = db.query(User).filter(User.id == int(payload.get("sub"))).first()
            if user:
                user_id = user.id
                user_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
                user_email = user.email

    fb = Feedback(
        user_id=user_id,
        user_name=user_name,
        user_email=user_email,
        message=data.message.strip(),
        rating=data.rating,
        is_approved=False
    )
    db.add(fb)
    db.commit()
    return {"message": "Feedback qabul qilindi! Tekshirilgach chiqariladi."}


@router.get("/approved")
def get_approved_feedbacks(db: Session = Depends(get_db)):
    """
    Index.html testimonial section uchun — tasdiqlangan feedbacklar.
    """
    feedbacks = db.query(Feedback).filter(
        Feedback.is_approved == True
    ).order_by(Feedback.created_at.desc()).all()

    return [
        {
            "id": fb.id,
            "user_name": fb.user_name or "Anonymous",
            "message": fb.message,
            "rating": fb.rating,
            "created_at": fb.created_at.isoformat() if fb.created_at else None,
        }
        for fb in feedbacks
    ]