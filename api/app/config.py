from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


def _database_url() -> str:
    value = os.getenv("DATABASE_URL", "")
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str = _database_url()
    supabase_url: str = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_public_key: str = os.getenv("SUPABASE_PUBLISHABLE_KEY", os.getenv("SUPABASE_ANON_KEY", ""))
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    audio_bucket: str = os.getenv("AUDIO_BUCKET", "episodes")
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    gnani_api_key: str = os.getenv("GNANI_API_KEY", "")
    gnani_model: str = os.getenv("GNANI_MODEL", "timbre-v3.0")
    gnani_voice: str = os.getenv("GNANI_VOICE", "Shivani")
    gnani_language: str = os.getenv("GNANI_LANGUAGE", "en-IN")
    resend_api_key: str = os.getenv("RESEND_API_KEY", "")
    email_from: str = os.getenv("EMAIL_FROM", "")
    app_url: str = os.getenv("APP_URL", "").rstrip("/")
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    worker_poll_seconds: float = float(os.getenv("WORKER_POLL_SECONDS", "3"))


settings = Settings()
