from dataclasses import dataclass
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


@dataclass(frozen=True)
class Settings:
    db_path: Path
    storage_dir: Path
    max_upload_bytes: int
    cors_origins: tuple[str, ...]
    demo_user_id: str
    openai_api_key: str
    openai_model: str


def get_settings() -> Settings:
    max_upload_bytes = int(os.getenv("LEGALLENS_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))
    if max_upload_bytes < 1:
        raise ValueError("LEGALLENS_MAX_UPLOAD_BYTES must be positive")
    return Settings(
        db_path=Path(os.getenv("LEGALLENS_DB_PATH", "var/legallens.db")),
        storage_dir=Path(os.getenv("LEGALLENS_STORAGE_DIR", "var/documents")),
        max_upload_bytes=max_upload_bytes,
        cors_origins=_csv(os.getenv("LEGALLENS_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")),
        demo_user_id=os.getenv("LEGALLENS_DEMO_USER_ID", "demo-user"),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-6-luna").strip(),
    )


settings = get_settings()
