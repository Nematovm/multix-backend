from pydantic_settings import BaseSettings

# config.py
class Settings(BaseSettings):
    # Majburiy o'zgaruvchilar (Render'da aniqlangan bo'lishi shart)
    database_url: str
    secret_key: str
    resend_api_key: str
    from_email: str
    
    # Default qiymatlar
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080
    app_name: str = "MultiX"  # Fayl yo'li emas, nom bo'lgani ma'qul
    
    # Bularni Render'da o'zgartirish kerak:
    frontend_url: str = "http://localhost:5500" 
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    
    google_client_id: str = ""
    google_client_secret: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = "ignore" # Qo'shimcha o'zgaruvchilar bo'lsa xato bermasligi uchun

settings = Settings()