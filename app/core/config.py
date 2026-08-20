from pydantic_settings import BaseSettings
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
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000", "http://127.0.0.1:8000"]
    
    # Environment
    environment: str = "development"
    
    # App
    app_name: str = "FlyRank AI Widget Backend"
    app_version: str = "0.1.0"
    
    # Supabase
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_jwt_secret: str = ""
    
    # FastAPI Cloud
    fast_api_cloud_token: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
