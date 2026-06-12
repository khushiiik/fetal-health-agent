import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from google.adk.models.google_llm import Gemini

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str

    DATA_SOURCE: str

    # Path variables
    MOCK_DATA_PATH: str
    CLINICAL_DATA_PATH: str

    # BigQuery setup
    BIGQUERY_PROJECT_ID: Optional[str] = None
    BIGQUERY_DATASET: Optional[str] = None
    BIGQUERY_TABLE: Optional[str] = None

    # GCP auth credentials
    GOOGLE_CLOUD_PROJECT: Optional[str] = None
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None

    # App env
    APP_ENV: str

    # Logging setup
    LOG_LEVEL: str
    LOG_FORMAT: str

    # Safety and limits
    ADK_MAX_ITERATIONS: int
    AGENT_TIMEOUT_SECONDS: int

    # Port settings
    STREAMLIT_PORT: int

settings = Settings()

if settings.GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY

def get_llm() -> Gemini:
    """Get initialized Gemini LLM connection."""
    return Gemini(model=settings.GEMINI_MODEL)
