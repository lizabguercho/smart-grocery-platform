"""Measured consistency of a prompt, and what the pattern points to.

Pure functions over outputs you already collected (no model calls here):
- run-to-run: k samples per item at the same prompt (sampling noise);
- prompt sensitivity: scores of intent-preserving variants of the prompt;
- model sensitivity: the same measurements on a smaller and a reference model.

Answer-level agreement and entropy are used because the outputs are short,
discrete field values that can be compared exactly (structured extraction).
Sources: see .claude/skills/prompt-review/references/rubric.md.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass


def agreement(answers: Sequence[Hashable]) -> float:
    """Share of samples that give the most common answer (1.0 = fully consistent)."""

    return max(Counter(answers).values()) / len(answers)


def entropy_bits(answers: Sequence[Hashable]) -> float:
    n = len(answers)
    return -sum(c / n * math.log2(c / n) for c in Counter(answers).values())


def field_consistency(
    samples: Mapping[str, Sequence[Mapping[str, Hashable]]],
) -> dict[str, dict[str, float]]:
    """samples[item] = list of k outputs (field -> value). Returns per-field mean agreement/entropy.

    A failed output (invalid JSON) should be passed as the value "<failed>" so it counts as a
    disagreement, never as an empty answer.
    """

    fields = sorted({f for outs in samples.values() for o in outs for f in o})
    out = {}
    for f in fields:
        per_item = [[o.get(f) for o in outs] for outs in samples.values()]
        out[f] = {
            "agreement": sum(agreement(a) for a in per_item) / len(per_item),
            "entropy_bits": sum(entropy_bits(a) for a in per_item) / len(per_item),
            "unstable_items": sum(agreement(a) < 1.0 for a in per_item),
        }
    return out


def prompt_spread(score_by_variant: Mapping[str, float]) -> dict[str, float]:
    """Report the range over intent-preserving variants, never a single score."""

    v = list(score_by_variant.values())
    return {"min": min(v), "max": max(v), "range": max(v) - min(v)}


@dataclass(frozen=True)
class Reading:
    consistency: float  # mean answer agreement across samples (0-1)
    accuracy: float  # against gold (0-1)


@dataclass(frozen=True)
class Hint:
    pattern: str
    points_to: str
    action: str


def diagnose(
    small: Reading,
    reference: Reading | None = None,
    spread_range: float | None = None,
    consistent_at: float = 0.9,
    accurate_at: float = 0.85,
    gap_at: float = 0.1,
) -> list[Hint]:
    """Map the consistency x accuracy x model pattern to likely causes. Hypotheses, not proof."""

    hints: list[Hint] = []
    steady, right = small.consistency >= consistent_at, small.accuracy >= accurate_at
    if steady and right:
        hints.append(
            Hint("consistent and accurate", "no prompt problem visible", "NONE")
        )
    if steady and not right:
        hints.append(
            Hint(
                "consistent but wrong",
                "systematic misreading: prompt and guideline/gold disagree, or a contradiction the model resolves the same way every time. Self-consistency cannot see this.",
                "FIX-COHERENCE",
            )
        )
    if not steady:
        if reference is None:
            hints.append(
                Hint(
                    "inconsistent on the small model, no reference measured",
                    "ambiguity or capacity: cannot tell which without a larger model",
                    "measure a reference model",
                )
            )
        elif reference.consistency >= consistent_at:
            hints.append(
                Hint(
                    "inconsistent small, consistent reference",
                    "capacity: too much per call for this model",
                    "SPLIT / MOVE-TO-CODE",
                )
            )
        else:
            hints.append(
                Hint(
                    "inconsistent on both models",
                    "ambiguity: the prompt underdetermines the answer",
                    "CLARIFY",
                )
            )
    if reference is not None and (reference.accuracy - small.accuracy) >= gap_at:
        hints.append(
            Hint(
                "accuracy gap to reference",
                "the task fits a bigger model; check load",
                "SPLIT",
            )
        )
    if spread_range is not None and spread_range >= gap_at:
        hints.append(
            Hint(
                "score moves with harmless rewrites",
                "fragile prompt: format- or order-sensitive",
                "REORDER (and enforce structure in the parser or decoding)",
            )
        )
    return hints
