import logging

from app.logging_config import setup_logging


def test_setup_logging_writes_file(tmp_path):
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    try:
        setup_logging(level="INFO", log_dir=str(tmp_path / "logs"))
        logging.getLogger("unit.test").info("hello-log-line")
        for h in root.handlers:
            h.flush()
        text = (tmp_path / "logs" / "app.log").read_text(encoding="utf-8")
        assert "hello-log-line" in text
        assert "INFO" in text
    finally:
        for h in root.handlers[:]:
            root.removeHandler(h)
            if h not in saved_handlers:
                h.close()
        for h in saved_handlers:
            root.addHandler(h)
        root.setLevel(saved_level)


def test_setup_logging_respects_level(tmp_path):
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    try:
        setup_logging(level="WARNING", log_dir=str(tmp_path / "logs"))
        assert root.level == logging.WARNING
    finally:
        for h in root.handlers[:]:
            root.removeHandler(h)
            if h not in saved_handlers:
                h.close()
        for h in saved_handlers:
            root.addHandler(h)
        root.setLevel(saved_level)
