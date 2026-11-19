import os
from dataclasses import dataclass, field
from typing import List, Mapping, Optional

from dotenv import load_dotenv

load_dotenv()  # .env is optional; real environment variables win

_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def _get_float(env: Mapping[str, str], key: str, default: float) -> float:
    raw = env.get(key)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{key} must be a number, got {raw!r}") from None
    if value < 0:
        raise ValueError(f"{key} must be >= 0, got {value}")
    return value


def _get_int(env: Mapping[str, str], key: str, default: int, minimum: int = 1) -> int:
    raw = env.get(key)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{key} must be an integer, got {raw!r}") from None
    if value < minimum:
        raise ValueError(f"{key} must be >= {minimum}, got {value}")
    return value


@dataclass
class Settings:
    app_env: str = "development"
    log_level: str = "INFO"
    log_dir: str = "logs"
    db_delay: float = 0.3          # simulated DB latency (seconds)
    external_delay: float = 0.2    # simulated external-service latency
    email_delay: float = 2.0       # simulated email latency
    allowed_origins: List[str] = field(default_factory=list)
    api_key: str = ""              # empty = research endpoint is open (dev only)
    max_concurrent_research: int = 1

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "Settings":
        env = os.environ if env is None else env
        level = env.get("LOG_LEVEL", "INFO").upper()
        if level not in _LOG_LEVELS:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(_LOG_LEVELS)}, got {level!r}")
        origins = [o.strip() for o in env.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
        return cls(
            app_env=env.get("APP_ENV", "development"),
            log_level=level,
            log_dir=env.get("LOG_DIR", "logs"),
            db_delay=_get_float(env, "DB_DELAY", 0.3),
            external_delay=_get_float(env, "EXTERNAL_DELAY", 0.2),
            email_delay=_get_float(env, "EMAIL_DELAY", 2.0),
            allowed_origins=origins,
            api_key=env.get("API_KEY", ""),
            max_concurrent_research=_get_int(env, "MAX_CONCURRENT_RESEARCH", 1),
        )


settings = Settings.from_env()
