from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # API Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # Database Settings
    DATABASE_URL: str = "sqlite:///./data/match_crew.db"
    
    # Legacy Database (para migração)
    LEGACY_DATABASE_URL: str = "sqlite:///./legacy/data/produtos_tratados.db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Matching Settings
    SIMILARITY_THRESHOLD: float = 0.7
    MAX_MATCHES_PER_PRODUCT: int = 10
    
    # Processing Settings
    BATCH_SIZE: int = 1000
    MAX_WORKERS: int = 4
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()