"""Run the local labeling desk.

  PYTHONPATH=. uv run python -m src.slm_benchmark.labeling
  # then open http://127.0.0.1:8765/
"""

from __future__ import annotations

import argparse

import uvicorn

from src.slm_benchmark.labeling.app import DEFAULT_HOST, DEFAULT_PORT, create_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local labeling desk UI")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
