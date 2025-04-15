from pydantic_settings import BaseSettings
from typing import Optional

# Konfiguracja aplikacji ładowana przy użyciu Pydantic-Settings.
# Umożliwia wczytywanie ustawień ze zmiennych środowiskowych i/lub pliku .env.

class Settings(BaseSettings):
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "Data Management Module"

    MONGODB_URL: str = "mongodb://mongo:27017/"  # "mongodb://localhost:27017"
    DATABASE_NAME: str = "sensitive_data_detection"

    # Google Cloud Storage settings
    GCS_BUCKET_NAME: Optional[str] = None

    class Config:
        env_file = ".env"


settings = Settings()
