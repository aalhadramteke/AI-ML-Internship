import importlib
import os
import pytest


def test_env_example_contains_required_keys():
    """Verify .env.example documents all required API and Research Assistant keys."""
    required_keys = {
        "APP_ENV",
        "LOG_LEVEL",
        "LOG_DIR",
        "ALLOWED_ORIGINS",
        "API_KEY",
        "MAX_CONCURRENT_RESEARCH",
        "DB_DELAY",
        "EXTERNAL_DELAY",
        "EMAIL_DELAY",
        "RA_BACKEND",
        "RA_OLLAMA_MODEL",
        "RA_OLLAMA_HOST",
        "RA_SOURCE",
        "RA_DOCS_DIR",
        "RA_OUTPUT_DIR",
    }
    assert os.path.exists(".env.example"), ".env.example must exist in project root"
    with open(".env.example", "r", encoding="utf-8") as f:
        lines = [
            line.strip().split("=", 1)[0]
            for line in f
            if line.strip() and not line.strip().startswith("#") and "=" in line
        ]
    missing = required_keys - set(lines)
    assert not missing, f"Missing keys in .env.example: {missing}"


def test_settings_module_loads(monkeypatch):
    """Verify app.settings loads environment variables cleanly."""
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("API_KEY", "unit-test-secret-key-1234567890")

    settings_mod = importlib.import_module("app.settings")
    importlib.reload(settings_mod)

    # Support either a `settings` object or module-level constants
    cfg = getattr(settings_mod, "settings", settings_mod)
    app_env = getattr(cfg, "APP_ENV", getattr(cfg, "app_env", None))
    assert app_env == "testing"


def test_research_config_loads(monkeypatch):
    """Verify research.config loads multi-agent assistant configuration."""
    monkeypatch.setenv("RA_BACKEND", "ollama")
    monkeypatch.setenv("RA_OLLAMA_MODEL", "qwen2.5:3b")
    monkeypatch.setenv("RA_MAX_SOURCES", "5")

    config_mod = importlib.import_module("research.config")
    importlib.reload(config_mod)
    assert config_mod is not None


def test_logging_config_initializes(tmp_path, monkeypatch):
    """Verify app.logging_config sets up logging without raising errors."""
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_LEVEL", "INFO")

    log_mod = importlib.import_module("app.logging_config")
    importlib.reload(log_mod)
    setup_fn = getattr(log_mod, "setup_logging", getattr(log_mod, "configure_logging", None))
    if callable(setup_fn):
        setup_fn()
