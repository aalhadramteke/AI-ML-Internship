import pytest

from app.settings import Settings


def test_defaults():
    s = Settings.from_env({})
    assert s.app_env == "development"
    assert s.log_level == "INFO"
    assert s.log_dir == "logs"
    assert s.db_delay == 0.3
    assert s.external_delay == 0.2
    assert s.email_delay == 2.0
    assert s.allowed_origins == []
    assert s.api_key == ""
    assert s.max_concurrent_research == 1


def test_reads_values_from_env():
    s = Settings.from_env(
        {
            "APP_ENV": "production",
            "LOG_LEVEL": "debug",
            "DB_DELAY": "0.5",
            "ALLOWED_ORIGINS": "http://a.com, http://b.com ,",
            "API_KEY": "secret",
            "MAX_CONCURRENT_RESEARCH": "3",
        }
    )
    assert s.is_production
    assert s.log_level == "DEBUG"
    assert s.db_delay == 0.5
    assert s.allowed_origins == ["http://a.com", "http://b.com"]
    assert s.api_key == "secret"
    assert s.max_concurrent_research == 3


def test_empty_string_falls_back_to_default():
    assert Settings.from_env({"DB_DELAY": ""}).db_delay == 0.3


@pytest.mark.parametrize(
    "key,value",
    [
        ("DB_DELAY", "abc"),
        ("DB_DELAY", "-1"),
        ("EMAIL_DELAY", "fast"),
        ("MAX_CONCURRENT_RESEARCH", "0"),
        ("MAX_CONCURRENT_RESEARCH", "two"),
        ("LOG_LEVEL", "LOUD"),
    ],
)
def test_invalid_values_fail_fast(key, value):
    with pytest.raises(ValueError):
        Settings.from_env({key: value})


def test_is_production_false_by_default():
    assert not Settings.from_env({}).is_production
