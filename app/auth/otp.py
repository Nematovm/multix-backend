import random
import string
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from ..models import OTPCode

def generate_otp(length: int = 6) -> str:
    return ''.join(random.choices(string.digits, k=length))

def save_otp(db: Session, email: str, code: str):
    # Eski OTP'larni o'chirish
    db.query(OTPCode).filter(OTPCode.email == email).delete()
    
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    otp = OTPCode(email=email, code=code, expires_at=expires_at)
    db.add(otp)
    db.commit()
    return otp

def verify_otp(db: Session, email: str, code: str) -> bool:
    otp = db.query(OTPCode).filter(
        OTPCode.email == email,
        OTPCode.code == code,
        OTPCode.is_used == False,
        OTPCode.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if not otp:
        return False
    
    otp.is_used = True
    db.commit()
    return True