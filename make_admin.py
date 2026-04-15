"""
Birinchi adminni qo'lda tayinlash uchun skript.

Ishlatish:
  cd backend
  python make_admin.py your@email.com
"""
import sys
from app.database import SessionLocal
from app.models import User

def make_admin(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"Foydalanuvchi topilmadi: {email}")
            sys.exit(1)
        user.is_admin = True
        db.commit()
        print(f"✅  {email} endi admin!")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Ishlatish: python make_admin.py your@email.com")
        sys.exit(1)
    make_admin(sys.argv[1])
