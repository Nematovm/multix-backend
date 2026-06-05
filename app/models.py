from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    hashed_password = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    premium_until = Column(DateTime(timezone=True), nullable=True)
    google_id = Column(String, nullable=True, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    code = Column(String(6), nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    ip_address = Column(String, nullable=True)
    device = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    section = Column(String(50), default="reading")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(String(400), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    level = Column(String(20), nullable=True)
    test_type = Column(String(20), nullable=True)
    skill = Column(String(20), nullable=True)
    duration = Column(Integer, nullable=True)
    questions_count = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=True, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    pdf_link = Column(String(500), nullable=True)
    format = Column(String(20), nullable=True, default="full")
    section = Column(String, nullable=True)
    telegram_channel = Column(String(200), nullable=True)
    telegram_link = Column(String(500), nullable=True)
    pdf_filename = Column(String(300), nullable=True)
    json_filename = Column(String(300), nullable=True)
    parts = Column(String(50), nullable=True, default="1,2,3,4,5,6")
    # ── YANGI: Recovery Mode ──
    recovery_enabled = Column(Boolean, nullable=True, default=False)


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, nullable=False, index=True)
    part_number = Column(Integer, nullable=False, default=1)
    question_number = Column(Integer, nullable=False)
    question_type = Column(String(50), nullable=False)
    question_text = Column(Text, nullable=True)
    passage_text = Column(Text, nullable=True)
    option_a = Column(String(500), nullable=True)
    option_b = Column(String(500), nullable=True)
    option_c = Column(String(500), nullable=True)
    option_d = Column(String(500), nullable=True)
    correct_answer = Column(String(200), nullable=False)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    user_name = Column(String(200), nullable=True)
    user_email = Column(String(200), nullable=True)
    message = Column(Text, nullable=False)
    rating = Column(Integer, nullable=True)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TestAttempt(Base):
    __tablename__ = "test_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False, index=True)
    test_name = Column(String(300), nullable=True)
    test_section = Column(String(50), nullable=True)
    score = Column(Integer, nullable=False, default=0)
    total = Column(Integer, nullable=False, default=0)
    percent = Column(Float, nullable=False, default=0.0)
    time_spent_seconds = Column(Integer, nullable=True)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    user_answers = Column(JSON, nullable=True)


class ListeningTest(Base):
    __tablename__ = "listening_tests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(String(400), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    level = Column(String(20), nullable=True)
    test_type = Column(String(20), nullable=True)
    format = Column(String(20), nullable=True)
    parts = Column(String(50), nullable=True, default="1,2,3,4")
    duration = Column(Integer, nullable=True, default=40)
    questions_count = Column(Integer, nullable=True, default=40)
    is_active = Column(Boolean, default=True)
    audio_url = Column(String(500), nullable=True)
    json_filename = Column(String(300), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # ── YANGI: Recovery Mode ──
    recovery_enabled = Column(Boolean, nullable=True, default=False)


# ══════════════════════════════════════════════════════
# ── RECOVERY MODE — 2 ta yangi jadval ──
# ══════════════════════════════════════════════════════

class RecoverySession(Base):
    """
    Foydalanuvchi testni topshirgandan keyin xato savollardan
    avtomatik yaratilgan mashq sessiyasi.
    """
    __tablename__ = "recovery_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Kim, qaysi test attempt dan
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    attempt_id = Column(Integer, ForeignKey("test_attempts.id"), nullable=False, index=True)

    # Test ma'lumotlari (tez o'qish uchun denormalized)
    test_id = Column(Integer, nullable=True)
    test_name = Column(String(300), nullable=True)
    test_section = Column(String(50), nullable=True)  # "reading" | "listening"

    # Xato savollar — JSON array of question IDs
    # Misol: ["q1", "q5", "q12"]  — user_answers dagi kalitlar
    wrong_question_ids = Column(JSON, nullable=False, default=list)

    # Progress
    total_questions = Column(Integer, nullable=False, default=0)
    mastered_count = Column(Integer, nullable=False, default=0)

    # Status
    status = Column(String(20), nullable=False, default="active")
    # "active" | "completed"

    # Vaqt
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class RecoveryAttempt(Base):
    """
    Recovery sessiyasidagi har bir savolga har bir urinish.
    Bir savol uchun maksimal 3 ta qator bo'lishi mumkin.
    """
    __tablename__ = "recovery_attempts"

    id = Column(Integer, primary_key=True, index=True)

    # Qaysi sessiya, qaysi savol
    session_id = Column(Integer, ForeignKey("recovery_sessions.id"), nullable=False, index=True)
    question_id = Column(String(100), nullable=False)  # JSON key (masalan "q1", "p1_q3")

    # Urinish raqami: 1, 2, yoki 3
    attempt_number = Column(Integer, nullable=False, default=1)

    # Foydalanuvchi javobi
    user_answer = Column(String(500), nullable=True)

    # Natija
    is_correct = Column(Boolean, nullable=False, default=False)
    mastered = Column(Boolean, nullable=False, default=False)
    # mastered = True bo'ladi agar: 3-urinishdan oldin to'g'ri topsa

    # Qachon javob berildi
    answered_at = Column(DateTime(timezone=True), server_default=func.now())