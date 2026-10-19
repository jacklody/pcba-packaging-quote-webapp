import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is declared in requirements.txt
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


BASE_DIR = Path(__file__).resolve().parent


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class AppConfig:
    env: str
    quote_history_db: Path
    cors_origins: tuple[str, ...]

    @property
    def is_development(self) -> bool:
        return self.env.lower() in {"dev", "development", "local"}


def load_config() -> AppConfig:
    env = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "development"))
    default_db = BASE_DIR / "data" / "quote_history.sqlite3"
    default_cors = "http://127.0.0.1:5173,http://localhost:5173" if env.lower() in {"dev", "development", "local"} else ""
    return AppConfig(
        env=env,
        quote_history_db=Path(os.getenv("QUOTE_HISTORY_DB", str(default_db))),
        cors_origins=_split_csv(os.getenv("CORS_ORIGINS", default_cors)),
    )
