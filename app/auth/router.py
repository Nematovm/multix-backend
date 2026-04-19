from fastapi import APIRouter, Depends, HTTPException, Header, Body
from fastapi.responses import RedirectResponse
from fastapi import Request as FastAPIRequest
from .google import get_google_auth_url, get_google_user_info
from ..models import User, UserSession
from ..utils.jwt import decode_token, create_access_token
from ..config import settings
from ..schemas import EmailRequest, OTPVerifyRequest, RegisterRequest, LoginRequest, UpdateProfileRequest, ChangePasswordRequest
from sqlalchemy.orm import Session
from ..database import get_db
from . import service
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/google/login")
def google_login():
    url = get_google_auth_url()
    return {"url": url}

@router.get("/google/callback")
def google_callback(code: str, db: Session = Depends(get_db)):
    info = get_google_user_info(code)
    if not info or "email" not in info:
        raise HTTPException(status_code=400, detail="Google login xato")
    
    email = info.get("email")
    google_id = info.get("sub")
    first_name = info.get("given_name", "")
    last_name = info.get("family_name", "")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, first_name=first_name, last_name=last_name,
                    google_id=google_id, is_verified=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    return RedirectResponse(
        url=f"{settings.frontend_url}/Pages/auth.html?token={access_token}&logged_in=true"
    )

@router.post("/send-otp")
def send_otp(request: EmailRequest, db: Session = Depends(get_db)):
    return service.send_otp_to_email(db, request.email)

@router.post("/verify-otp")
def verify_otp(request: OTPVerifyRequest, db: Session = Depends(get_db)):
    return service.verify_user_otp(db, request.email, request.code)

@router.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    return service.register_user(
        db, request.email, request.first_name,
        request.last_name, request.password, request.otp_verified_token
    )

@router.post("/login")
def login(request: LoginRequest, req: FastAPIRequest, db: Session = Depends(get_db)):
    ip = req.client.host
    ua = req.headers.get("user-agent", "")
    return service.login_user(db, request.email, request.password, ip=ip, device=ua[:200])



# YANGI (to'g'ri)
@router.get("/me")
def get_me(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token yo'q")
    
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token noto'g'ri")
    
    user = db.query(User).filter(User.id == int(payload.get("sub"))).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    # Premium muddatini tekshirish
    if user.is_premium and user.premium_until:
        if datetime.now(timezone.utc) > user.premium_until:
            user.is_premium = False
            user.premium_until = None
            db.commit()
    
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_verified": user.is_verified,
        "is_premium": user.is_premium,
        "is_admin": user.is_admin,
    }

@router.put("/me/profile")
def update_profile(
    request: UpdateProfileRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token noto'g'ri")
    
    user = db.query(User).filter(User.id == int(payload.get("sub"))).first()
    if not user:
        raise HTTPException(status_code=404, detail="User topilmadi")
    
    user.first_name = request.first_name
    user.last_name = request.last_name
    db.commit()
    db.refresh(user)
    
    return {"message": "Profil yangilandi", "first_name": user.first_name, "last_name": user.last_name}

@router.post("/me/change-password")
def change_password(
    request: ChangePasswordRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    from ..utils.security import verify_password, hash_password
    
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token noto'g'ri")
    
    user = db.query(User).filter(User.id == int(payload.get("sub"))).first()
    if not user:
        raise HTTPException(status_code=404, detail="User topilmadi")
    
    if user.hashed_password and not verify_password(request.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Eski parol noto'g'ri")
    
    user.hashed_password = hash_password(request.new_password)
    db.commit()
    return {"message": "Parol o'zgartirildi"}

@router.get("/me/sessions")
def get_sessions(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token noto'g'ri")
    
    sessions = db.query(UserSession).filter(
        UserSession.user_id == int(payload.get("sub")),
        UserSession.is_active == True
    ).order_by(UserSession.created_at.desc()).all()
    
    return sessions



# auth/router.py ga qo'shing (eng pastga)

@router.post("/admin/set-premium")
def set_premium(
    email: str = Body(..., embed=True),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    # Admin tekshirish
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token noto'g'ri")
    
    admin = db.query(User).filter(User.id == int(payload.get("sub"))).first()
    if not admin or not admin.is_admin:
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")
    
    # Targetni topish
    target = db.query(User).filter(User.email == email).first()
    if not target:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    target.is_premium = True
    db.commit()
    return {"message": f"{email} - Pro planga o'tkazildi!"}