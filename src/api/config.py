import os
from dataclasses import dataclass
from typing import List

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        pass


@dataclass
class Settings:
    """API Configuration settings loaded from environment variables."""

    data_dir: str = os.getenv("CODEMEMORY_DATA_DIR", "data")
    knowledge_dir: str = os.getenv("CODEMEMORY_KNOWLEDGE_DIR", "knowledge")
    db_path: str = os.getenv("CODEMEMORY_DB_PATH", "data/codememory.duckdb")

    host: str = os.getenv("CODEMEMORY_API_HOST", "127.0.0.1")
    port: int = int(os.getenv("CODEMEMORY_API_PORT", "8000"))
    log_level: str = os.getenv("CODEMEMORY_LOG_LEVEL", "INFO").lower()

    cors_origins: List[str] = None

    def __post_init__(self):
        if self.cors_origins is None:
            origins = os.getenv(
                "CODEMEMORY_CORS_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000,tauri://localhost,http://tauri.localhost,http://localhost:1420",
            )
            self.cors_origins = [o.strip() for o in origins.split(",") if o.strip()]

settings = Settings()
