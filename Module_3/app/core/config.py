from pydantic_settings import BaseSettings
from typing import Optional

# Konfiguracja aplikacji ładowana przy użyciu Pydantic-Settings.
# Umożliwia wczytywanie ustawień ze zmiennych środowiskowych i/lub pliku .env.

class Settings(BaseSettings):
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "Data_Management_Module"

    MONGODB_URL: str = "mongodb://mongo:27017/tioch?replicaSet=rs0 "  # "mongodb://localhost:27017"
    DATABASE_NAME: str = "tioch"
    
    # Module 2
    CONVERSION_SERVICE_URL: str = "http://extractor:8000/file"

    # Module 4
    DETECTION_SERVICE_URL: str = "http://detector-api:8000/detect"

    # Module 5
    NOTIFICATION_SERVICE_URL: str = "http://notifications:8765/api/send-notification/"

settings = Settings()
