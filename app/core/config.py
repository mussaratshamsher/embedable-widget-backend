from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """Application configuration from environment variables."""
    
    # Database
    database_url: str
    
    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # Groq
    groq_api_key: str
    
    # Gemini
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")

    
    # CORS
    cors_origins: List[str] = ["*"]
    
    # Environment
    environment: str = "development"
    
    # App
    app_name: str = "FlyRank AI Widget Backend"
    app_version: str = "0.1.0"
    
    # Supabase
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    supabase_jwt_secret: str = ""
    
    # FastAPI Cloud
    fast_api_cloud_token: str = ""
    
    # reCAPTCHA
    recaptcha_secret_key: str = Field(default="", validation_alias="SECRET_KEY")
    recaptcha_site_key: str = Field(default="", validation_alias="PROJECT_ID")
    
    class Config:
        import os
        from pathlib import Path
        _env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        env_file = str(_env_path) if _env_path.exists() else ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()

