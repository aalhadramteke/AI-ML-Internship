import logging.config
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(level: str = "INFO", log_dir: str = "logs") -> None:
    """Console + rotating file logging. Safe to call more than once."""
    handlers = {"console": {"class": "logging.StreamHandler", "formatter": "std"}}
    try:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(Path(log_dir) / "app.log"),
            "maxBytes": 5_000_000,
            "backupCount": 5,
            "formatter": "std",
            "encoding": "utf-8",
        }
    except OSError:  # read-only filesystem etc. -> keep console logging working
        pass

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"std": {"format": LOG_FORMAT}},
            "handlers": handlers,
            "root": {"level": level, "handlers": list(handlers)},
        }
    )
