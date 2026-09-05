"""Dependencies injected into every agent run.

Passed as `Agent(deps_type=AgentDeps)` and reached inside tools through
`ctx.deps`, which is how a tool gets the shared connection pool without any
module-level global.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.agent_platform.grocery.database import AsyncGroceryDatabase


@dataclass(frozen=True)
class AgentDeps:
    """What the grocery tools need in order to run."""

    database: AsyncGroceryDatabase
