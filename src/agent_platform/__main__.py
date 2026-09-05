"""Run the chat service locally.

    uv run python -m src.agent_platform

Mirrors the `python -m src.etl` entrypoint convention.
"""

from __future__ import annotations

import logging

import uvicorn

from src.agent_platform.api.app import create_app
from src.agent_platform.config import AgentPlatformConfig

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
STARTING_MESSAGE = "Starting chat service on http://%s:%s (model %s)"


def main() -> None:
    """Serve the chat service with uvicorn."""

    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    config = AgentPlatformConfig.from_env()
    logging.getLogger(__name__).info(
        STARTING_MESSAGE, config.host, config.port, config.agent.model
    )
    uvicorn.run(create_app(config), host=config.host, port=config.port)


if __name__ == "__main__":
    main()
