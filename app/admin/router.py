from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Category, Test, Feedback
from ..utils.jwt import decode_token
import os, uuid, json, boto3
from botocore.client import Config
from ..models import Question
from ..schemas import QuestionCreate
from typing import Optional
from datetime import datetime, timedelta, timezone


router = APIRouter(prefix="/admin", tags=["Admin"])

# ── Cloudflare R2 client ──
R2_ACCESS_KEY_ID     = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
R2_ACCOUNT_ID        = os.environ.get("R2_ACCOUNT_ID")
R2_BUCKET_NAME       = os.environ.get("R2_BUCKET_NAME", "multix-files")
R2_PUBLIC_URL        = os.environ.get("R2_PUBLIC_URL", "").rstrip("/")

def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


# TO'G'RI — bu qolsin (fayl boshida)
def upload_to_r2(content: bytes, key: str, content_type: str) -> str:
    client = get_r2_client()   # ← client shu yerda yaratiladi
    client.put_object(
        Bucket=R2_BUCKET_NAME,
        Key=key,
        Body=content,
        ContentType=content_type,
    )
    return f"{R2_PUBLIC_URL}/{key}"

def delete_from_r2(key: str):
    """R2 dan fayl o'chirish"""
    try:
        client = get_r2_client()
        client.delete_object(Bucket=R2_BUCKET_NAME, Key=key)
    except Exception:
        pass


# ── Admin auth ──
def get_admin_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token yo'q")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token noto'g'ri")
    user = db.query(User).filter(User.id == int(payload.get("sub"))).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin huquqi yo'q")
    return user


# ── STATS ──
@router.get("/stats")
def get_stats(db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    return {
        "total_users": db.query(User).count(),
        "total_tests": db.query(Test).filter(Test.is_active == True).count(),
        "premium_users": db.query(User).filter(User.is_premium == True).count(),
        "total_categories": db.query(Category).count(),
        "pending_feedbacks": db.query(Feedback).filter(Feedback.is_approved == False).count(),
        "user_growth": [12, 18, 25, 32, 45, 62, 95, db.query(User).count()],
        "premium_growth": [1, 2, 3, 5, 7, 10, 15, db.query(User).filter(User.is_premium == True).count()],
    }


# ── CATEGORIES ──
@router.get("/categories")
def get_categories(section: str = None, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    query = db.query(Category)
    if section:
        query = query.filter(Category.section == section)
    cats = query.all()
    result = []
    for c in cats:
        count = db.query(Test).filter(Test.category_id == c.id, Test.is_active == True).count()
        result.append({
            "id": c.id, "name": c.name,
            "description": c.description,
            "section": c.section,
            "tests_count": count
        })
    return result


@router.post("/categories")
def create_category(
    name: str = Form(...),
    description: str = Form(""),
    section: str = Form("reading"),
    db: Session = Depends(get_db),
    admin=Depends(get_admin_user)
):
    existing = db.query(Category).filter(Category.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bu nom allaqachon mavjud")
    cat = Category(name=name, description=description, section=section)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/categories/{cat_id}")
def delete_category(cat_id: int, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Topilmadi")
    tests = db.query(Test).filter(Test.category_id == cat_id).all()
    for test in tests:
        if test.pdf_filename:
            delete_from_r2(f"pdfs/{test.pdf_filename}")
        if test.json_filename:
            delete_from_r2(f"jsons/{test.json_filename}")
        db.delete(test)
    db.flush()
    db.delete(cat)
    db.commit()
    return {"message": "O'chirildi"}


# ── TESTS ──
@router.get("/tests")
def get_tests(section: str = None, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    query = db.query(Test).filter(Test.is_active == True)
    if section:
        query = query.filter(Test.section == section)
    tests = query.all()
    result = []
    for t in tests:
        cat = db.query(Category).filter(Category.id == t.category_id).first()
        result.append({
            "id": t.id,
            "name": t.name,
            "category_id": t.category_id,
            "category_name": cat.name if cat else "—",
            "section": t.skill,
            "level": t.level,
            "type": t.test_type,
            "parts": t.parts or "1,2,3,4,5",
            "duration": t.duration,
            "questions_count": t.questions_count,
            "telegram_channel": t.telegram_channel,
            "telegram_link": t.telegram_link,
            "pdf_filename": t.pdf_filename,
            "has_pdf": bool(t.pdf_filename),
            "json_filename": t.json_filename,
            "has_json": bool(t.json_filename),
        })
    return result


@router.post("/tests")
async def create_test(
    name: str = Form(...),
    category_id: int = Form(...),
    section: str = Form("reading"),
    level: str = Form("medium"),
    type: str = Form("free"),
    format: str = Form("full"),
    parts: str = Form("1,2,3,4,5"),
    duration: int = Form(60),
    questions_count: int = Form(35),
    telegram_channel: str = Form(""),
    telegram_link: str = Form(""),
    pdf_file: UploadFile = File(None),
    json_file: UploadFile = File(None),
    db: Session = Depends(get_db),
    admin=Depends(get_admin_user)
):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=400, detail="Kategoriya topilmadi")

    # ── PDF → R2 ga yuklash ──
    pdf_filename = None
    if pdf_file and pdf_file.filename:
        ext = pdf_file.filename.split('.')[-1]
        unique_name = f"{uuid.uuid4()}.{ext}"
        content = await pdf_file.read()
        upload_to_r2(content, f"pdfs/{unique_name}", "application/pdf")
        pdf_filename = unique_name

    # ── JSON → R2 ga yuklash ──
    json_filename = None
    if json_file and json_file.filename:
        if not json_file.filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="Faqat .json fayl yuklang")
        content = await json_file.read()
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="JSON fayl noto'g'ri formatda")
        if "parts" not in parsed:
            raise HTTPException(status_code=400, detail="JSON da 'parts' array bo'lishi kerak")
        unique_name = f"{uuid.uuid4()}.json"
        upload_to_r2(content, f"jsons/{unique_name}", "application/json")
        json_filename = unique_name

    test = Test(
        name=name,
        category_id=category_id,
        skill=section,
        level=level,
        test_type=type,
        duration=duration,
        questions_count=questions_count,
        telegram_channel=telegram_channel,
        telegram_link=telegram_link,
        pdf_filename=pdf_filename,
        json_filename=json_filename,
        parts=parts,
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return {"message": "Test qo'shildi", "id": test.id}


# ── Bu qismni admin/router.py ga qo'shing (create_test dan keyin) ──

@router.post("/upload-audio")
async def upload_audio(
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(get_admin_user)
):
    """Audio faylni R2 ga yuklash va public URL qaytarish"""
    allowed = ['.mp3', '.wav', '.ogg', '.m4a', '.aac']
    ext = os.path.splitext(audio_file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Faqat audio fayl: {', '.join(allowed)}")

    content     = await audio_file.read()
    unique_name = f"{uuid.uuid4()}{ext}"
    content_type_map = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.ogg': 'audio/ogg',
        '.m4a': 'audio/mp4',
        '.aac': 'audio/aac',
    }
    upload_to_r2(content, f"audios/{unique_name}", content_type_map.get(ext, 'audio/mpeg'))
    public_url = f"{R2_PUBLIC_URL}/audios/{unique_name}"

    return {
        "message": "Audio yuklandi",
        "filename": unique_name,
        "url": public_url
    }


# ── JSON FAYL OLISH — R2 dan redirect ──
@router.get("/tests/{test_id}/json-data")
def get_test_json(test_id: int, db: Session = Depends(get_db)):
    test = db.query(Test).filter(Test.id == test_id, Test.is_active == True).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    if not test.json_filename:
        raise HTTPException(status_code=404, detail="Bu test uchun JSON fayl yo'q")

    # R2 public URL ga redirect
    r2_url = f"{R2_PUBLIC_URL}/jsons/{test.json_filename}"
    return RedirectResponse(url=r2_url)


@router.delete("/tests/{test_id}")
def delete_test(test_id: int, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    test = db.query(Test).filter(Test.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Topilmadi")
    if test.pdf_filename:
        delete_from_r2(f"pdfs/{test.pdf_filename}")
    if test.json_filename:
        delete_from_r2(f"jsons/{test.json_filename}")
    test.is_active = False
    db.commit()
    return {"message": "O'chirildi"}


# ── USERS ──
@router.get("/users")
def get_users(db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.put("/users/{user_id}/premium")
def update_premium(
    user_id: int,
    is_premium: bool = Form(...),
    db: Session = Depends(get_db),
    admin=Depends(get_admin_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User topilmadi")

    if is_premium:
        user.is_premium = True
        user.premium_until = datetime.now(timezone.utc) + timedelta(days=30)
    else:
        user.is_premium = False
        user.premium_until = None

    db.commit()
    return {
        "message": "Yangilandi",
        "is_premium": user.is_premium,
        "premium_until": user.premium_until.isoformat() if user.premium_until else None
    }


# ── QUESTIONS ──
@router.get("/tests/{test_id}/questions")
def get_questions(test_id: int, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    questions = db.query(Question).filter(
        Question.test_id == test_id
    ).order_by(Question.part_number, Question.question_number).all()
    return questions


@router.post("/questions")
def create_question(data: QuestionCreate, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    q = Question(
        test_id=data.test_id,
        part_number=data.part_number,
        question_number=data.question_number,
        question_type=data.question_type,
        question_text=data.question_text,
        passage_text=data.passage_text,
        option_a=data.option_a,
        option_b=data.option_b,
        option_c=data.option_c,
        option_d=data.option_d,
        correct_answer=data.correct_answer,
        explanation=data.explanation
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


@router.delete("/questions/{q_id}")
def delete_question(q_id: int, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    q = db.query(Question).filter(Question.id == q_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Topilmadi")
    db.delete(q)
    db.commit()
    return {"message": "O'chirildi"}


# ── FEEDBACKS ──
@router.get("/feedbacks")
def get_feedbacks(
    approved: Optional[bool] = None,
    db: Session = Depends(get_db),
    admin=Depends(get_admin_user)
):
    query = db.query(Feedback).order_by(Feedback.created_at.desc())
    if approved is not None:
        query = query.filter(Feedback.is_approved == approved)
    feedbacks = query.all()
    return [
        {
            "id": fb.id,
            "user_name": fb.user_name or "Anonymous",
            "user_email": fb.user_email,
            "message": fb.message,
            "rating": fb.rating or 0,
            "is_approved": fb.is_approved,
            "created_at": fb.created_at.isoformat() if fb.created_at else None,
        }
        for fb in feedbacks
    ]


@router.put("/feedbacks/{feedback_id}/approve")
def approve_feedback(feedback_id: int, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    fb = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not fb:
        raise HTTPException(status_code=404, detail="Topilmadi")
    fb.is_approved = True
    db.commit()
    return {"message": "Tasdiqlandi", "id": fb.id}


@router.put("/feedbacks/{feedback_id}/reject")
def reject_feedback(feedback_id: int, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    fb = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not fb:
        raise HTTPException(status_code=404, detail="Topilmadi")
    fb.is_approved = False
    db.commit()
    return {"message": "Rad etildi"}


@router.delete("/feedbacks/{feedback_id}")
def delete_feedback(feedback_id: int, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    fb = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not fb:
        raise HTTPException(status_code=404, detail="Topilmadi")
    db.delete(fb)
    db.commit()
    return {"message": "O'chirildi"}



# ═══════════════════════════════════════════════
# ── LISTENING TESTS ──
# ═══════════════════════════════════════════════

@router.get("/listening-tests")
def get_listening_tests(db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    from ..models import ListeningTest
    tests = db.query(ListeningTest).filter(ListeningTest.is_active == True).all()
    result = []
    for t in tests:
        cat = db.query(Category).filter(Category.id == t.category_id).first()
        result.append({
            "id":           t.id,
            "name":         t.name,
            "category_id":  t.category_id,
            "category_name": cat.name if cat else "—",
            "level":        t.level,
            "type":         t.test_type,
            "format":       t.format,
            "parts":        t.parts or "1,2,3,4",
            "duration":     t.duration,
            "audio_url":    t.audio_url,
            "has_audio":    bool(t.audio_url),
            "json_filename": t.json_filename,
            "has_json":     bool(t.json_filename),
        })
    return result


@router.post("/listening-tests")
async def create_listening_test(
    name:         str        = Form(...),
    category_id:  int        = Form(...),
    level:        str        = Form("medium"),
    type:         str        = Form("free"),
    format:       str        = Form("full"),
    parts:        str        = Form("1,2,3,4"),
    duration:     int        = Form(40),
    audio_file:   UploadFile = File(None),
    json_file:    UploadFile = File(None),
    db: Session = Depends(get_db),
    admin=Depends(get_admin_user)
):
    from ..models import ListeningTest

    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=400, detail="Kategoriya topilmadi")

    # ── Audio → R2 ──
    audio_url = None
    if audio_file and audio_file.filename:
        allowed_audio = ['.mp3', '.wav', '.ogg', '.m4a', '.aac']
        ext = os.path.splitext(audio_file.filename)[1].lower()
        if ext not in allowed_audio:
            raise HTTPException(status_code=400, detail=f"Faqat audio fayl: {', '.join(allowed_audio)}")
        content = await audio_file.read()
        unique_name = f"{uuid.uuid4()}{ext}"
        ct_map = {'.mp3':'audio/mpeg','.wav':'audio/wav','.ogg':'audio/ogg','.m4a':'audio/mp4','.aac':'audio/aac'}
        upload_to_r2(content, f"audios/{unique_name}", ct_map.get(ext, 'audio/mpeg'))
        audio_url = f"{R2_PUBLIC_URL}/audios/{unique_name}"

    # ── JSON → R2 ──
    json_filename = None
    if json_file and json_file.filename:
        if not json_file.filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="Faqat .json fayl yuklang")
        content = await json_file.read()
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="JSON fayl noto'g'ri formatda")
        if "parts" not in parsed:
            raise HTTPException(status_code=400, detail="JSON da 'parts' array bo'lishi kerak")
        unique_name = f"{uuid.uuid4()}.json"
        upload_to_r2(content, f"jsons/{unique_name}", "application/json")
        json_filename = unique_name

    test = ListeningTest(
        name=name,
        category_id=category_id,
        level=level,
        test_type=type,
        format=format,
        parts=parts,
        duration=duration,
        audio_url=audio_url,
        json_filename=json_filename,
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return {"message": "Listening test qo'shildi", "id": test.id}


@router.delete("/listening-tests/{test_id}")
def delete_listening_test(test_id: int, db: Session = Depends(get_db), admin=Depends(get_admin_user)):
    from ..models import ListeningTest
    test = db.query(ListeningTest).filter(ListeningTest.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Topilmadi")
    # R2 dan o'chirish
    if test.json_filename:
        delete_from_r2(f"jsons/{test.json_filename}")
    if test.audio_url:
        # audio URL dan fayl nomini ajratib olish
        audio_key = "audios/" + test.audio_url.split("/audios/")[-1]
        delete_from_r2(audio_key)
    test.is_active = False
    db.commit()
    return {"message": "O'chirildi"}


@router.get("/listening-tests/{test_id}/json-data")
def get_listening_test_json(test_id: int, db: Session = Depends(get_db)):
    from ..models import ListeningTest
    test = db.query(ListeningTest).filter(ListeningTest.id == test_id, ListeningTest.is_active == True).first()
    if not test or not test.json_filename:
        raise HTTPException(status_code=404, detail="JSON topilmadi")
    return RedirectResponse(url=f"{R2_PUBLIC_URL}/jsons/{test.json_filename}")





