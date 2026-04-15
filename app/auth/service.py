from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from ..models import User
from ..utils.security import hash_password, verify_password
from ..utils.jwt import create_access_token
from .otp import generate_otp, save_otp, verify_otp
from .email import send_otp_email

def send_otp_to_email(db: Session, email: str):
    code = generate_otp()
    save_otp(db, email, code)
    try:
        send_otp_email(email, code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email yuborishda xato: {str(e)}")
    return {"message": "OTP yuborildi", "email": email}

def verify_user_otp(db: Session, email: str, code: str):
    is_valid = verify_otp(db, email, code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP noto'g'ri yoki muddati o'tgan"
        )
    
    # Email allaqachon ro'yxatdan o'tganmi tekshirish
    existing_user = db.query(User).filter(User.email == email).first()
    
    if existing_user:
        # Mavjud user — to'g'ridan-to'g'ri login
        access_token = create_access_token({"sub": str(existing_user.id), "email": existing_user.email})
        return {"verified": True, "access_token": access_token, "token_type": "bearer"}
    else:
        # Yangi user — register stepiga o'tish
        temp_token = create_access_token(
            {"email": email, "type": "otp_verified"},
            __import__('datetime').timedelta(minutes=15)
        )
        return {"verified": True, "temp_token": temp_token}

def register_user(db: Session, email: str, first_name: str, 
                  last_name: str, password: str, temp_token: str):
    from ..utils.jwt import decode_token
    
    # Temp token tekshirish
    payload = decode_token(temp_token)
    if not payload or payload.get("type") != "otp_verified" or payload.get("email") != email:
        raise HTTPException(status_code=400, detail="Noto'g'ri yoki muddati o'tgan token")
    
    # Foydalanuvchi mavjudligini tekshirish
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bu email allaqachon ro'yxatdan o'tgan")
    
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        hashed_password=hash_password(password),
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    return {"access_token": access_token, "token_type": "bearer", "user": user}

def login_user(db: Session, email: str, password: str, ip: str = None, device: str = None):
    from ..models import UserSession
    
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email yoki parol noto'g'ri")
    
    # Session saqlash
    session = UserSession(user_id=user.id, ip_address=ip, device=device)
    db.add(session)
    db.commit()
    
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    return {"access_token": access_token, "token_type": "bearer", "user": user}