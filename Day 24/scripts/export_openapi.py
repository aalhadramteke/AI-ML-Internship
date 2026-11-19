"""Regenerate openapi.json from the running code:  python scripts/export_openapi.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402

Path("openapi.json").write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
print("Wrote openapi.json")
