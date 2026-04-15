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
    parts = Column(String(50), nullable=True, default="1,2,3,4,5")


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


# ── TEST ATTEMPT ──
class TestAttempt(Base):
    __tablename__ = "test_attempts"

    id = Column(Integer, primary_key=True, index=True)

    # Kim topshirdi
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Qaysi test
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False, index=True)
    test_name = Column(String(300), nullable=True)       # tez o'qish uchun denormalized
    test_section = Column(String(50), nullable=True)     # "reading", "listening", ...

    # Natijalar
    score = Column(Integer, nullable=False, default=0)         # to'g'ri javoblar soni
    total = Column(Integer, nullable=False, default=0)         # jami savollar soni
    percent = Column(Float, nullable=False, default=0.0)       # foiz

    # Vaqt
    time_spent_seconds = Column(Integer, nullable=True)        # sarflangan vaqt (sekund)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Foydalanuvchi javoblari (JSON) — review uchun
    user_answers = Column(JSON, nullable=True)   # { "q1": "A", "q2": "mental", ... }