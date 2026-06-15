import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from google.adk.models.google_llm import Gemini

# Force loading environment variables from .env to override system environment
load_dotenv(override=True)

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
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        project_id = settings.GOOGLE_CLOUD_PROJECT or "fetal-health-agent"
        model_name = f"projects/{project_id}/locations/us-central1/publishers/google/models/{settings.GEMINI_MODEL}"
        return Gemini(model=model_name)
    return Gemini(model=settings.GEMINI_MODEL)

