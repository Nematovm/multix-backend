from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080
    resend_api_key: str
    from_email: str
    app_name: str = "./Logo/MultiX.svg"
    frontend_url: str = "http://localhost:5500"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    class Config:
        env_file = ".env"

settings = Settings()