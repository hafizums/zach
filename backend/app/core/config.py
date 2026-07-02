import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "AI 3D Explainer Shorts Generator"
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./test.sqlite")
    storage_dir: str = os.getenv("STORAGE_DIR", "./storage")

settings = Settings()
