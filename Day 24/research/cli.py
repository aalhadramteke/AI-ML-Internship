import argparse

from app.logging_config import setup_logging
from app.settings import settings
from research.service import run_research


def main() -> None:
    p = argparse.ArgumentParser(description="Multi-agent research assistant")
    p.add_argument("query", help="Research question")
    args = p.parse_args()

    setup_logging(settings.log_level, settings.log_dir)
    result = run_research(args.query)

    print("\n" + "=" * 60 + "\n")
    print(result["report"])
