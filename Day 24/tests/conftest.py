"""Test environment: fast simulated delays, no auth, logs in a temp folder.

Set BEFORE the app is imported so settings pick these up.
"""
import os
import tempfile

os.environ.update(
    {
        "APP_ENV": "test",
        "LOG_LEVEL": "INFO",
        "LOG_DIR": tempfile.mkdtemp(prefix="ra_test_logs_"),
        "DB_DELAY": "0.01",
        "EXTERNAL_DELAY": "0.01",
        "EMAIL_DELAY": "0.01",
        "API_KEY": "",
        "ALLOWED_ORIGINS": "",
        "MAX_CONCURRENT_RESEARCH": "1",
    }
)
