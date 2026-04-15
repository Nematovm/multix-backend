from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# ── Auth schemas ──────────────────────────────────────
class EmailRequest(BaseModel):
    email: EmailStr

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    code: str

class RegisterRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    password: str
    otp_verified_token: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    is_verified: bool
    is_admin: bool = False
    is_premium: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

class UpdateProfileRequest(BaseModel):
    first_name: str
    last_name: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class SessionResponse(BaseModel):
    id: int
    ip_address: Optional[str]
    device: Optional[str]
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

# ── Admin — Category schemas ──────────────────────────
class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    tests_count: Optional[int] = 0
    class Config:
        from_attributes = True

class TestCreate(BaseModel):
    name: str
    category_id: int
    level: str = "medium"
    type: str = "free"
    description: Optional[str] = None
    duration: int = 60
    questions_count: int = 40
    format: str = "full"
    parts: str = "1,2,3"
    pdf_link: Optional[str] = None

class TestResponse(BaseModel):
    id: int
    name: str
    category_id: int
    category_name: Optional[str] = None
    level: str
    type: str
    description: Optional[str]
    duration: int
    questions_count: int
    parts: str
    class Config:
        from_attributes = True

class UserAdminResponse(BaseModel):
    id: int
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    is_verified: bool
    is_premium: bool
    is_admin: bool
    created_at: datetime
    class Config:
        from_attributes = True

class PremiumUpdate(BaseModel):
    is_premium: bool

# ── Admin — Stats schema ──────────────────────────────
class StatsResponse(BaseModel):
    total_users: int
    total_tests: int
    premium_users: int
    total_categories: int

class QuestionCreate(BaseModel):
    test_id: int
    part_number: int = 1
    question_number: int
    question_type: str
    question_text: Optional[str] = None
    passage_text: Optional[str] = None
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct_answer: str
    explanation: Optional[str] = None

class QuestionResponse(BaseModel):
    id: int
    test_id: int
    part_number: int
    question_number: int
    question_type: str
    question_text: Optional[str]
    passage_text: Optional[str]
    option_a: Optional[str]
    option_b: Optional[str]
    option_c: Optional[str]
    option_d: Optional[str]
    correct_answer: str
    explanation: Optional[str]

    class Config:
        from_attributes = True