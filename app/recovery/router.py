"""
app/recovery/router.py

Recovery Mode — Xatolar ustida ishlash tizimi.

Endpointlar:
  POST /recovery/create              — attempt dan session yaratish
  GET  /recovery/{session_id}        — session holati
  POST /recovery/{session_id}/answer — javob yuborish
  GET  /recovery/history             — foydalanuvchi barcha sessiyalari
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..utils.jwt import decode_token
from ..models import (
    TestAttempt, RecoverySession, RecoveryAttempt
)
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timezone

router = APIRouter(prefix="/recovery", tags=["Recovery"])

MAX_ATTEMPTS = 3  # Har bir savol uchun maksimal urinish soni


# ── Auth helper ──
def get_current_user_id(authorization: str) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token yo'q")
    payload = decode_token(authorization.split(" ")[1])
    if not payload:
        raise HTTPException(status_code=401, detail="Token noto'g'ri")
    return int(payload.get("sub"))


# ── Schemas ──
class CreateRecoveryRequest(BaseModel):
    attempt_id: int


class AnswerRequest(BaseModel):
    question_id: str
    user_answer: str
    correct_answer: str   # Frontend JSON dan biladigan to'g'ri javob


# ══════════════════════════════════════════════════════
# POST /recovery/create
# ══════════════════════════════════════════════════════
@router.post("/create")
def create_recovery_session(
    body: CreateRecoveryRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    """
    TestAttempt topshirilgandan keyin chaqiriladi.
    Xato savollarni topib, yangi RecoverySession yaratadi.
    """
    user_id = get_current_user_id(authorization)

    # Attempt mavjudligini tekshirish
    attempt = db.query(TestAttempt).filter(
        TestAttempt.id == body.attempt_id,
        TestAttempt.user_id == user_id,
    ).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt topilmadi")

    # Xato savollarni topish: user_answers ichida to'g'ri javob berilmaganlar
    # user_answers format: {"q1": "A", "q2": "mental", ...}
    # Lekin to'g'ri javoblar faqat test JSON da bor, shuning uchun frontend
    # /attempts endpoint orqali wrong_ids ni ham yuboradi yoki biz boshqacha saqlaymiz.
    # Hozircha: agar attempt.score < attempt.total bo'lsa session yaratiladi
    # va wrong_question_ids ni frontend beradi (create body da).

    if attempt.score >= attempt.total:
        return {
            "created": False,
            "message": "Barcha savollar to'g'ri! Recovery kerak emas.",
            "session_id": None,
        }

    # Mavjud active session bormi?
    existing = db.query(RecoverySession).filter(
        RecoverySession.attempt_id == body.attempt_id,
        RecoverySession.user_id == user_id,
        RecoverySession.status == "active",
    ).first()
    if existing:
        return {
            "created": False,
            "message": "Bu attempt uchun session allaqachon mavjud",
            "session_id": existing.id,
        }

    # Yangi session yaratish
    # wrong_question_ids ni attempt.user_answers dan olamiz —
    # lekin to'g'ri javoblar bizda yo'q (test JSON da).
    # Shuning uchun frontend create vaqtida wrong_ids ni yuboradi.
    # Hozir: bo'sh list bilan yaratamiz, frontend keyinroq patch qiladi.
    session = RecoverySession(
        user_id=user_id,
        attempt_id=body.attempt_id,
        test_id=attempt.test_id,
        test_name=attempt.test_name,
        test_section=attempt.test_section,
        wrong_question_ids=[],   # Frontend /patch endpoint orqali to'ldiradi
        total_questions=0,
        mastered_count=0,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "created": True,
        "session_id": session.id,
        "message": "Recovery session yaratildi",
    }


# ── POST /recovery/create-with-questions (asosiy endpoint) ──
class CreateRecoveryWithQuestionsRequest(BaseModel):
    attempt_id: int
    wrong_question_ids: list   # ["q1", "p2_q5", ...]
    test_id: Optional[int] = None
    test_name: Optional[str] = None
    test_section: Optional[str] = "reading"


@router.post("/create-full")
def create_recovery_session_full(
    body: CreateRecoveryWithQuestionsRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    """
    To'liq endpoint: attempt + xato savollar ID lari bilan session yaratadi.
    Frontend testni topshirgandan so'ng darhol chaqiradi.
    """
    user_id = get_current_user_id(authorization)

    # Attempt tekshirish
    attempt = db.query(TestAttempt).filter(
        TestAttempt.id == body.attempt_id,
        TestAttempt.user_id == user_id,
    ).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt topilmadi")

    if not body.wrong_question_ids:
        return {
            "created": False,
            "message": "Barcha savollar to'g'ri! Recovery kerak emas.",
            "session_id": None,
        }

    # Mavjud active session
    existing = db.query(RecoverySession).filter(
        RecoverySession.attempt_id == body.attempt_id,
        RecoverySession.user_id == user_id,
        RecoverySession.status == "active",
    ).first()
    if existing:
        return {
            "created": False,
            "message": "Bu attempt uchun session allaqachon mavjud",
            "session_id": existing.id,
        }

    session = RecoverySession(
        user_id=user_id,
        attempt_id=body.attempt_id,
        test_id=body.test_id or attempt.test_id,
        test_name=body.test_name or attempt.test_name,
        test_section=body.test_section or attempt.test_section,
        wrong_question_ids=body.wrong_question_ids,
        total_questions=len(body.wrong_question_ids),
        mastered_count=0,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "created": True,
        "session_id": session.id,
        "total_questions": len(body.wrong_question_ids),
        "message": f"{len(body.wrong_question_ids)} ta savol uchun Recovery sessiyasi yaratildi",
    }


# ══════════════════════════════════════════════════════
# GET /recovery/{session_id}
# ══════════════════════════════════════════════════════
@router.get("/{session_id}")
def get_recovery_session(
    session_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    """
    Session holati: qancha savol qoldi, kim mastered, kim emas.
    """
    user_id = get_current_user_id(authorization)

    session = db.query(RecoverySession).filter(
        RecoverySession.id == session_id,
        RecoverySession.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session topilmadi")

    # Har bir savol uchun urinishlar soni
    attempts_data = db.query(RecoveryAttempt).filter(
        RecoveryAttempt.session_id == session_id,
    ).all()

    # question_id → {attempts: int, mastered: bool, last_correct: bool}
    question_status = {}
    for a in attempts_data:
        qid = a.question_id
        if qid not in question_status:
            question_status[qid] = {
                "attempts": 0,
                "mastered": False,
                "last_answer": None,
                "last_correct": False,
            }
        question_status[qid]["attempts"] = max(
            question_status[qid]["attempts"], a.attempt_number
        )
        if a.mastered:
            question_status[qid]["mastered"] = True
        question_status[qid]["last_answer"] = a.user_answer
        question_status[qid]["last_correct"] = a.is_correct

    remaining = [
        qid for qid in session.wrong_question_ids
        if not question_status.get(qid, {}).get("mastered", False)
           and question_status.get(qid, {}).get("attempts", 0) < MAX_ATTEMPTS
    ]
    exhausted = [
        qid for qid in session.wrong_question_ids
        if not question_status.get(qid, {}).get("mastered", False)
           and question_status.get(qid, {}).get("attempts", 0) >= MAX_ATTEMPTS
    ]

    return {
        "id": session.id,
        "attempt_id": session.attempt_id,
        "test_id": session.test_id,
        "test_name": session.test_name,
        "test_section": session.test_section,
        "status": session.status,
        "total_questions": session.total_questions,
        "mastered_count": session.mastered_count,
        "wrong_question_ids": session.wrong_question_ids,
        "question_status": question_status,
        "remaining_count": len(remaining),
        "exhausted_count": len(exhausted),
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }


# ══════════════════════════════════════════════════════
# POST /recovery/{session_id}/answer
# ══════════════════════════════════════════════════════
@router.post("/{session_id}/answer")
def submit_recovery_answer(
    session_id: int,
    body: AnswerRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    """
    Foydalanuvchi recovery savoliga javob beradi.
    
    Qaytaradi:
    - is_correct: bool
    - attempt_number: int (1, 2, 3)
    - mastered: bool
    - show_answer: bool  — 3-urinishdan keyin to'g'ri javob ko'rsatilsinmi
    - message: str       — foydalanuvchiga ko'rsatiladigan xabar
    """
    user_id = get_current_user_id(authorization)

    session = db.query(RecoverySession).filter(
        RecoverySession.id == session_id,
        RecoverySession.user_id == user_id,
        RecoverySession.status == "active",
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Aktiv session topilmadi")

    if body.question_id not in session.wrong_question_ids:
        raise HTTPException(status_code=400, detail="Bu savol ushbu sessionga tegishli emas")

    # Oldingi urinishlar
    prev_attempts = db.query(RecoveryAttempt).filter(
        RecoveryAttempt.session_id == session_id,
        RecoveryAttempt.question_id == body.question_id,
    ).all()

    # Allaqachon mastered?
    if any(a.mastered for a in prev_attempts):
        return {
            "is_correct": True,
            "mastered": True,
            "attempt_number": len(prev_attempts),
            "show_answer": False,
            "message": "Bu savol allaqachon o'zlashtirilgan!",
        }

    attempt_number = len(prev_attempts) + 1

    # 3 dan oshib ketishni oldini olish
    if attempt_number > MAX_ATTEMPTS:
        return {
            "is_correct": False,
            "mastered": False,
            "attempt_number": MAX_ATTEMPTS,
            "show_answer": True,
            "correct_answer": body.correct_answer,
            "message": "Urinishlar tugadi. To'g'ri javobni ko'ring.",
        }

    # Javobni tekshirish (case-insensitive, trim)
    is_correct = (
        body.user_answer.strip().lower() == body.correct_answer.strip().lower()
    )
    mastered = is_correct  # To'g'ri topilsa — mastered

    # RecoveryAttempt yozish
    rec_attempt = RecoveryAttempt(
        session_id=session_id,
        question_id=body.question_id,
        attempt_number=attempt_number,
        user_answer=body.user_answer,
        is_correct=is_correct,
        mastered=mastered,
    )
    db.add(rec_attempt)

    # Session mastered_count ni yangilash
    if mastered:
        session.mastered_count = (session.mastered_count or 0) + 1

    # Barcha savollar mastered yoki exhausted bo'lsa — session complete
    all_done = _check_all_done(session, db, extra_mastered=1 if mastered else 0)
    if all_done:
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)

    db.commit()

    # Javob tayyorlash
    show_answer = (not is_correct) and (attempt_number >= MAX_ATTEMPTS)

    if is_correct:
        message = "To'g'ri! Ajoyib ✓"
    elif attempt_number < MAX_ATTEMPTS:
        remaining_tries = MAX_ATTEMPTS - attempt_number
        message = f"Noto'g'ri. Yana {remaining_tries} ta urinish qoldi. Savolni diqqat bilan tahlil qiling."
    else:
        message = "Urinishlar tugadi. To'g'ri javobni va izohni ko'ring."

    result = {
        "is_correct": is_correct,
        "mastered": mastered,
        "attempt_number": attempt_number,
        "show_answer": show_answer,
        "message": message,
        "session_completed": all_done,
    }
    if show_answer:
        result["correct_answer"] = body.correct_answer

    return result


def _check_all_done(session: RecoverySession, db: Session, extra_mastered: int = 0) -> bool:
    """Barcha savollar mastered yoki urinish tugaganligi tekshirish."""
    mastered_ids = set()
    exhausted_ids = set()

    attempts = db.query(RecoveryAttempt).filter(
        RecoveryAttempt.session_id == session.id,
    ).all()

    q_data: Dict[str, Dict] = {}
    for a in attempts:
        qid = a.question_id
        if qid not in q_data:
            q_data[qid] = {"max_attempt": 0, "mastered": False}
        q_data[qid]["max_attempt"] = max(q_data[qid]["max_attempt"], a.attempt_number)
        if a.mastered:
            q_data[qid]["mastered"] = True

    for qid in session.wrong_question_ids:
        data = q_data.get(qid, {"max_attempt": 0, "mastered": False})
        if data["mastered"]:
            mastered_ids.add(qid)
        elif data["max_attempt"] >= MAX_ATTEMPTS:
            exhausted_ids.add(qid)

    done_count = len(mastered_ids) + len(exhausted_ids)
    return done_count >= len(session.wrong_question_ids)


# ══════════════════════════════════════════════════════
# GET /recovery/history
# ══════════════════════════════════════════════════════
@router.get("/history/me")
def get_recovery_history(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    """Foydalanuvchining barcha recovery sessiyalari."""
    user_id = get_current_user_id(authorization)

    sessions = db.query(RecoverySession).filter(
        RecoverySession.user_id == user_id,
    ).order_by(RecoverySession.started_at.desc()).all()

    return [
        {
            "id": s.id,
            "attempt_id": s.attempt_id,
            "test_name": s.test_name,
            "test_section": s.test_section,
            "status": s.status,
            "total_questions": s.total_questions,
            "mastered_count": s.mastered_count,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        }
        for s in sessions
    ]


# ══════════════════════════════════════════════════════
# GET /recovery/{session_id}/summary
# ══════════════════════════════════════════════════════
@router.get("/{session_id}/summary")
def get_recovery_summary(
    session_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    """
    Recovery yakunlangach ko'rsatiladigan statistika:
    - Boshlang'ich natija (attempt dan)
    - Qancha savol o'zlashtirildi
    - O'sish foizi
    - Jami urinishlar soni
    - Eng qiyin savollar (3 urinish talab qilgan)
    """
    user_id = get_current_user_id(authorization)

    session = db.query(RecoverySession).filter(
        RecoverySession.id == session_id,
        RecoverySession.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session topilmadi")

    # Boshlang'ich attempt
    attempt = db.query(TestAttempt).filter(
        TestAttempt.id == session.attempt_id,
    ).first()

    # Barcha urinishlar
    all_attempts = db.query(RecoveryAttempt).filter(
        RecoveryAttempt.session_id == session_id,
    ).all()

    total_tries = len(all_attempts)
    mastered_ids = set()
    hard_questions = []  # 3 urinish talab qilganlar

    q_data: Dict[str, Dict] = {}
    for a in all_attempts:
        qid = a.question_id
        if qid not in q_data:
            q_data[qid] = {"attempts": 0, "mastered": False}
        q_data[qid]["attempts"] = max(q_data[qid]["attempts"], a.attempt_number)
        if a.mastered:
            q_data[qid]["mastered"] = True
            mastered_ids.add(qid)

    for qid, data in q_data.items():
        if data["attempts"] >= MAX_ATTEMPTS and not data["mastered"]:
            hard_questions.append(qid)

    mastered_count = len(mastered_ids)
    original_wrong = session.total_questions
    improvement = round((mastered_count / original_wrong * 100), 1) if original_wrong > 0 else 0

    avg_attempts = round(total_tries / original_wrong, 1) if original_wrong > 0 else 0

    return {
        "session_id": session_id,
        "test_name": session.test_name,
        "test_section": session.test_section,
        "status": session.status,

        # Boshlang'ich natija
        "original_score": attempt.score if attempt else 0,
        "original_total": attempt.total if attempt else 0,
        "original_percent": attempt.percent if attempt else 0,

        # Recovery natijasi
        "wrong_questions": original_wrong,
        "mastered_count": mastered_count,
        "still_wrong_count": original_wrong - mastered_count,
        "improvement_percent": improvement,

        # Urinishlar statistikasi
        "total_tries": total_tries,
        "avg_tries_per_question": avg_attempts,
        "hard_questions": hard_questions,  # 3 urinishdan keyin ham xato

        # Vaqt
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }