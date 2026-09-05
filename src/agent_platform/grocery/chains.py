"""How the three chains appear in the analytical tables.

`grocery.price_comparison` stores one price column per chain, so a chain is
identified by a column name in SQL and by a display label in prose. Keeping
both next to the `Chain` enum avoids raw chain strings spread across queries
and tool results.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.etl.enums import Chain


@dataclass(frozen=True)
class ChainProfile:
    """A chain's identity across the analytical layer."""

    chain: Chain
    display_name: str
    price_column: str


SHUFERSAL_PROFILE = ChainProfile(
    chain=Chain.SHUFERSAL,
    display_name="Shufersal",
    price_column="shufersal_price",
)
RAMI_LEVY_PROFILE = ChainProfile(
    chain=Chain.RAMI_LEVY,
    display_name="Rami Levy",
    price_column="rami_levy_price",
)
VICTORY_PROFILE = ChainProfile(
    chain=Chain.VICTORY,
    display_name="Victory",
    price_column="victory_price",
)

CHAIN_PROFILES: tuple[ChainProfile, ...] = (
    SHUFERSAL_PROFILE,
    RAMI_LEVY_PROFILE,
    VICTORY_PROFILE,
)

CHAIN_COUNT = len(CHAIN_PROFILES)


def profile_for(chain: Chain) -> ChainProfile:
    """Return the analytical-layer profile for a chain."""

    for profile in CHAIN_PROFILES:
        if profile.chain is chain:
            return profile
    raise ValueError(f"No profile is defined for chain {chain!r}.")
