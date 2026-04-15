from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from .auth.router import router as auth_router
from .admin.router import router as admin_router
from .feedback.router import router as feedback_router
from .config import settings
from .utils.jwt import decode_token
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ClearPath API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static/pdfs", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(feedback_router)


# ─────────────────────────────────────────────
# TEST ATTEMPT — schema
# ─────────────────────────────────────────────
class AttemptSubmitRequest(BaseModel):
    test_id: int
    test_name: str
    test_section: Optional[str] = "reading"
    score: int
    total: int
    percent: float
    time_spent_seconds: Optional[int] = None
    user_answers: Optional[Dict[str, Any]] = None


# ─────────────────────────────────────────────
# POST /attempts  — natijani saqlash
# ─────────────────────────────────────────────
@app.post("/attempts")
def submit_attempt(
    body: AttemptSubmitRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    from .models import TestAttempt

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token yo'q")

    payload = decode_token(authorization.split(" ")[1])
    if not payload:
        raise HTTPException(status_code=401, detail="Token noto'g'ri")

    user_id = int(payload.get("sub"))

    attempt = TestAttempt(
        user_id=user_id,
        test_id=body.test_id,
        test_name=body.test_name,
        test_section=body.test_section,
        score=body.score,
        total=body.total,
        percent=body.percent,
        time_spent_seconds=body.time_spent_seconds,
        user_answers=body.user_answers,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return {"id": attempt.id, "message": "Attempt saqlandi"}


# ─────────────────────────────────────────────
# GET /attempts/me  — foydalanuvchining attemptlari
# ─────────────────────────────────────────────
@app.get("/attempts/me")
def get_my_attempts(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    from .models import TestAttempt

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token yo'q")

    payload = decode_token(authorization.split(" ")[1])
    if not payload:
        raise HTTPException(status_code=401, detail="Token noto'g'ri")

    user_id = int(payload.get("sub"))

    attempts = (
        db.query(TestAttempt)
        .filter(TestAttempt.user_id == user_id)
        .order_by(TestAttempt.completed_at.desc())
        .all()
    )

    return [
        {
            "id": a.id,
            "test_id": a.test_id,
            "test_name": a.test_name,
            "test_section": a.test_section,
            "score": a.score,
            "total": a.total,
            "percent": a.percent,
            "time_spent_seconds": a.time_spent_seconds,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        }
        for a in attempts
    ]


# ─────────────────────────────────────────────
# GET /attempts/{attempt_id}  — bitta attempt (review uchun)
# ─────────────────────────────────────────────
@app.get("/attempts/{attempt_id}")
def get_attempt(
    attempt_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    from .models import TestAttempt

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token yo'q")

    payload = decode_token(authorization.split(" ")[1])
    if not payload:
        raise HTTPException(status_code=401, detail="Token noto'g'ri")

    user_id = int(payload.get("sub"))

    attempt = db.query(TestAttempt).filter(
        TestAttempt.id == attempt_id,
        TestAttempt.user_id == user_id,
    ).first()

    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt topilmadi")

    return {
        "id": attempt.id,
        "test_id": attempt.test_id,
        "test_name": attempt.test_name,
        "test_section": attempt.test_section,
        "score": attempt.score,
        "total": attempt.total,
        "percent": attempt.percent,
        "time_spent_seconds": attempt.time_spent_seconds,
        "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
        "user_answers": attempt.user_answers or {},
    }


# ─────────────────────────────────────────────
# Mavjud endpointlar (o'zgarmagan)
# ─────────────────────────────────────────────
@app.get("/tests")
def get_public_tests(section: str = None, db: Session = Depends(get_db)):
    from .models import Test, Category
    query = db.query(Test).filter(Test.is_active == True)
    if section:
        query = query.filter(Test.section == section)
    tests = query.all()
    result = []
    for t in tests:
        cat = db.query(Category).filter(Category.id == t.category_id).first()
        pdf_url = f"http://127.0.0.1:8000/static/pdfs/{t.pdf_filename}" if t.pdf_filename else None
        result.append({
            "id": t.id, "name": t.name,
            "category_name": cat.name if cat else "Other",
            "section": t.section,
            "level": t.level, "type": t.test_type,
            "format": t.format or "full",
            "parts": t.parts,
            "duration": t.duration,
            "questions_count": t.questions_count,
            "telegram_channel": t.telegram_channel,
            "telegram_link": t.telegram_link,
            "pdf_url": pdf_url,
        })
    return result


@app.get("/")
def root():
    return {"message": "ClearPath API ishlayapti!"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/tests/{test_id}/questions")
def get_public_questions(test_id: int, db: Session = Depends(get_db)):
    from .models import Question
    questions = db.query(Question).filter(
        Question.test_id == test_id
    ).order_by(Question.part_number, Question.question_number).all()

    result = []
    for q in questions:
        result.append({
            "id": q.id,
            "part_number": q.part_number,
            "question_number": q.question_number,
            "question_type": q.question_type,
            "question_text": q.question_text,
            "passage_text": q.passage_text,
            "option_a": q.option_a,
            "option_b": q.option_b,
            "option_c": q.option_c,
            "option_d": q.option_d,
        })
    return result