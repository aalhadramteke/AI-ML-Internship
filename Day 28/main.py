"""CLI entrypoint for running the multi-agent research assistant."""

import argparse

from graph import build_graph


def main():
    p = argparse.ArgumentParser(description="Multi-agent research assistant")
    p.add_argument("query", help="Research question")
    args = p.parse_args()

    app = build_graph()
    final = None
    for update in app.stream({"query": args.query, "log": []}, {"recursion_limit": 40}):
        for node, out in update.items():
            for line in out.get("log", []):
                print(line)
            if "final_report" in out:
                final = out["final_report"]

    print("\n" + "=" * 60 + "\n")
    print(final or "No report produced.")


if __name__ == "__main__":
    main()
