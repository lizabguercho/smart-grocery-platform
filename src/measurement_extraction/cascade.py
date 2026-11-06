"""System C: rules accept narrowly eligible complete cases; Qwen handles the rest.

The whole result of one system is used per title, never a field-wise merge.
"""

from __future__ import annotations

from src.measurement_extraction.rules import RuleResult


def route(rule_result: RuleResult) -> str:
    """'rules' if the whitelist accepts the title, otherwise 'qwen'.

    Whitelist (frozen before final evaluation): exactly one number+registered
    unit match, amount and canonical unit resolved, no other digits left in
    the title, and no container-capacity word. A no-match is never trusted.
    """

    return "rules" if rule_result.eligible else "qwen"
