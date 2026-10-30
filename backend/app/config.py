from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DB_FILE = Path(__file__).resolve().parent.parent / "eventmate.db"


class Settings(BaseSettings):
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: Optional[str] = None

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
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def is_ai_configured(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_api_key.strip())


settings = Settings()
