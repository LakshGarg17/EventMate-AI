import logging
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DB_FILE = Path(__file__).resolve().parent.parent / "eventmate.db"
logger = logging.getLogger("eventmate.config")

DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]


class Settings(BaseSettings):
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
    allowed_origins: Optional[str] = None  # Backward compatibility with Day 1-3
    cors_origin_regex: Optional[str] = None
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: Optional[str] = None
    proposal_ttl_minutes: int = 30
    ai_rate_limit_per_minute: int = 10
    trust_proxy_headers: bool = False
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def effective_database_url(self) -> str:
        if self.database_url and self.database_url.strip():
            return self.database_url.strip()
        return f"sqlite:///{DEFAULT_DB_FILE.as_posix()}"

    @property
    def allowed_origins_list(self) -> List[str]:
        raw = self.allowed_origins if (self.allowed_origins and self.allowed_origins.strip()) else self.cors_origins
        parsed = [
            origin.strip().rstrip("/")
            for origin in raw.split(",")
            if origin.strip()
        ]
        return parsed if parsed else list(DEFAULT_CORS_ORIGINS)

    @property
    def is_ai_configured(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_api_key.strip())

    def log_startup_summary(self):
        """Logs safe startup configuration without exposing secrets."""
        if not self.is_ai_configured:
            logger.warning("No GEMINI_API_KEY detected. AI features will operate in truthful Demo Mode.")
        else:
            logger.info("Gemini API key configured. Active model: %s", self.gemini_model)

        logger.info("CORS allowed origins: %s", self.allowed_origins_list)
        if self.cors_origin_regex:
            logger.info("CORS origin regex: %s", self.cors_origin_regex)
        if self.ai_rate_limit_per_minute > 0:
            logger.info("AI Rate limit enabled: %d requests/min per IP", self.ai_rate_limit_per_minute)
        else:
            logger.info("AI Rate limit disabled (0)")

        db_dialect = "PostgreSQL" if self.effective_database_url.startswith(("postgres://", "postgresql://", "postgresql+")) else "SQLite"
        logger.info("Database dialect configured: %s", db_dialect)


settings = Settings()
