"""CLI entry point (spec section 18): run the platform from the command line.

Usage:
    python -m app.cli run --objective "smoke" --url https://example.com --priority P0 --limit 5
"""
from __future__ import annotations

import argparse
import asyncio
import json


async def _run(args) -> None:
    from .graph import run_workflow

    application = {
        "url": args.url,
        "name": args.name or args.url,
        "source": "url",
    }
    result = await run_workflow(args.objective, application)
    final = result.get("final_result", {})
    print(json.dumps(final, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(prog="ai-e2e-platform")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run the E2E pipeline against a URL")
    run_p.add_argument("--objective", required=True)
    run_p.add_argument("--url", required=True)
    run_p.add_argument("--name")
    run_p.add_argument("--priority", default="P0")
    run_p.add_argument("--limit", type=int, default=5)

    token_p = sub.add_parser("token", help="Mint a JWT for API access")
    token_p.add_argument("--role", default="engineer", choices=["admin", "engineer", "viewer"])
    token_p.add_argument("--user", default="cli")
    token_p.add_argument("--expires", type=int, default=120)

    args = parser.parse_args()
    if args.command == "run":
        asyncio.run(_run(args))
    elif args.command == "token":
        from .security import create_token

        print(create_token(args.user, args.role, args.expires))


if __name__ == "__main__":
    main()
