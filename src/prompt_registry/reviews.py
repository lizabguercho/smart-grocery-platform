"""Parse docs/prompts/<category>/<prompt-id>/REVIEWS.md and render docs/PROMPT_STATUS.md.

The REVIEWS.md files are the source of truth (written by the prompt-review
skill and by people). PROMPT_STATUS.md is generated and never edited by hand.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from src.prompt_registry.extract import extract_prompt, fingerprint

CATEGORIES = ("preprocessing", "classification", "agentic", "evaluation")
# Independent recommended actions, never ranked against each other. The order
# in an entry is the recommended order of work, justified in the entry.
ACTIONS = (
    "SPLIT",  # too many constraints or chained decisions for one call
    "MOVE-TO-CODE",  # a compute/derivable decision the code can own
    "FIX-COHERENCE",  # contradictions, schema/guideline mismatch
    "CLARIFY",  # ambiguity: undefined terms, missing null policy
    "REORDER",  # structure/position
    "TRIM",  # redundancy, extraneous load
    "NONE",
)
VALIDITY = (
    "valid",
    "invalid",
)  # invalid: scores from this prompt cannot be trusted (e.g. leakage)
DIMENSIONS = ("load", "coherence", "ambiguity", "structure", "efficiency", "hygiene")
SEVERITIES = ("ok", "watch", "fix", "blocker")
HEADER_KEYS = ("Category", "Prompt", "Model", "Owner", "Purpose", "Next step")
ENTRY = re.compile(
    r"^## (\d{4}-\d{2}-\d{2}) — actions: ([A-Z, -]+) — validity: ([a-z]+) — tier: ([a-z]+)"
    r" — prompt-sha: ([0-9a-f]{12})\s*$"
)
MEASURED = re.compile(r"^- Measured:\s*(.+)$", re.MULTILINE)
LOAD = re.compile(r"^- Load:.*?K=(\d+).*?band (\d+)/(\d+)", re.MULTILINE)
DIMS = re.compile(r"^- Dimensions:\s*(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class Review:
    date: str
    actions: tuple[str, ...]
    validity: str
    measured: str
    tier: str
    sha: str
    k: int
    comfortable: int
    risky: int
    dims: dict[str, str]


@dataclass(frozen=True)
class PromptRecord:
    prompt_id: str
    category: str
    prompt_path: str
    model: str
    model_doc: str
    owner: str
    purpose: str
    next_step: str
    reviews_path: str
    reviews: int
    last: Review | None
    current_sha: str


def _header(text: str, path: Path) -> dict[str, str]:
    out = {}
    for key in (*HEADER_KEYS, "Symbol", "Model doc"):
        m = re.search(rf"^{key}:[ \t]*(.*)$", text, re.MULTILINE)
        out[key] = m.group(1).strip() if m else ""
    missing = [k for k in HEADER_KEYS if not out[k]]
    if missing:
        raise ValueError(f"{path}: missing header field(s) {missing}")
    return out


def _parse_entry(body: str, head: re.Match, path: Path) -> Review:
    date, raw_actions, validity, tier, sha = head.groups()
    actions = tuple(a.strip() for a in raw_actions.split(",") if a.strip())
    if not actions or not set(actions) <= set(ACTIONS):
        raise ValueError(f"{path}: actions must be a comma list from {ACTIONS}")
    if "NONE" in actions and len(actions) > 1:
        raise ValueError(f"{path}: NONE cannot be combined with other actions")
    if validity not in VALIDITY:
        raise ValueError(f"{path}: validity must be one of {VALIDITY}")
    load, dims = LOAD.search(body), DIMS.search(body)
    if not load or not dims:
        raise ValueError(
            f"{path}: entry {date} needs '- Load: K=<n> ... band <a>/<b>' and '- Dimensions: ...'"
        )
    parsed = dict(re.findall(r"([a-z]+)=([a-z]+)", dims.group(1)))
    if set(parsed) != set(DIMENSIONS) or not set(parsed.values()) <= set(SEVERITIES):
        raise ValueError(
            f"{path}: entry {date} Dimensions must give {DIMENSIONS} each as one of {SEVERITIES}"
        )
    measured = MEASURED.search(body)
    return Review(
        date,
        actions,
        validity,
        measured.group(1).strip() if measured else "not measured",
        tier,
        sha,
        *(int(g) for g in load.groups()),
        parsed,
    )


def parse_reviews(path: Path, root: Path, prompts_dir: Path) -> PromptRecord:
    text = path.read_text(encoding="utf-8")
    h = _header(text, path)
    rel = path.relative_to(prompts_dir).parent  # <category>/<sub...>/<id>
    top = rel.parts[0]
    if top not in CATEGORIES:
        raise ValueError(f"{path}: folder {top!r} is not one of {CATEGORIES}")
    if h["Category"].split("/")[0] != top:
        raise ValueError(f"{path}: Category header must start with the folder '{top}'")
    prompt_file = root / h["Prompt"]
    if not prompt_file.exists():
        raise ValueError(f"{path}: Prompt file {h['Prompt']} does not exist")
    prompt_text, _, _ = extract_prompt(prompt_file, h["Symbol"] or None)
    lines = text.splitlines()
    heads = [(i, m) for i, line in enumerate(lines) if (m := ENTRY.match(line))]
    reviews = []
    for n, (i, m) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        reviews.append(_parse_entry("\n".join(lines[i + 1 : end]), m, path))
    return PromptRecord(
        rel.name,
        h["Category"],
        h["Prompt"],
        h["Model"],
        h["Model doc"],
        h["Owner"],
        h["Purpose"],
        h["Next step"],
        str(path.relative_to(root)),
        len(reviews),
        reviews[0] if reviews else None,
        fingerprint(prompt_text),
    )


def collect(prompts_dir: Path, root: Path) -> list[PromptRecord]:
    return sorted(
        (parse_reviews(p, root, prompts_dir) for p in prompts_dir.rglob("REVIEWS.md")),
        key=lambda r: (r.category, r.prompt_id),
    )


def state(r: PromptRecord) -> str:
    if r.last is None:
        return "unreviewed"
    if r.last.sha != r.current_sha:
        return "changed since review"
    if r.last.validity == "invalid":
        return "invalid"
    return "no action" if r.last.actions == ("NONE",) else "action needed"


def render_status(records: list[PromptRecord]) -> str:
    short = {
        "ok": "ok",
        "watch": "watch",
        "fix": "FIX",
        "blocker": "BLOCK",
    }
    letters = dict(zip(DIMENSIONS, "LCASEH"))
    lines = [
        "# Prompt status",
        "",
        "<!-- GENERATED by scripts/build_prompt_status.py from docs/prompts/**/REVIEWS.md. Do not edit by hand. -->",
        "",
        (
            "Where each prompt stands. Source of truth: the `REVIEWS.md` next to each prompt's entry "
            "(see [CONTRIBUTING.md](../CONTRIBUTING.md#prompts)). Review with `/prompt-review <path>`."
        ),
        "",
    ]
    attention = [r for r in records if state(r) != "no action"]
    lines += ["## Needs attention", ""]
    if attention:
        lines += [
            "| Prompt | State | Actions (recommended order) | Next step |",
            "|---|---|---|---|",
        ]
        lines += [
            f"| `{r.prompt_id}` | **{state(r)}** | {', '.join(r.last.actions) if r.last else '–'} | {r.next_step} |"
            for r in attention
        ]
    else:
        lines.append(
            "Nothing: every prompt has been reviewed, needs no action and is unchanged since its review."
        )
    lines += [
        "",
        "## All prompts",
        "",
        "| Category | Prompt | Model | State | Actions | Validity | Constraints K (comfortable/risky) | Dimensions | Measured | Reviewed | Reviews |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in records:
        last = r.last
        k = f"{last.k} ({last.comfortable}/{last.risky}, {last.tier})" if last else "–"
        dims = (
            " ".join(f"{letters[d]}:{short[last.dims[d]]}" for d in DIMENSIONS)
            if last
            else "–"
        )
        link = f"[{r.reviews}]({r.reviews_path.removeprefix('docs/')})"
        model = r.model + (
            f" ([model doc]({r.model_doc.removeprefix('docs/')}))"
            if r.model_doc
            else ""
        )
        lines.append(
            f"| {r.category} | [`{r.prompt_id}`](../{r.prompt_path}) | {model} | **{state(r)}** | "
            f"{', '.join(last.actions) if last else '–'} | {last.validity if last else '–'} | "
            f"{k} | {dims} | {last.measured if last else '–'} | {last.date if last else '–'} | {link} |"
        )
    lines += [
        "",
        (
            "Dimensions: L load, C coherence, A ambiguity, S structure, E efficiency, H hygiene; "
            "each `ok` / `watch` / `FIX` / `BLOCK`. **Actions are independent recommendations, not a ranking**: "
            "a prompt can need SPLIT and FIX-COHERENCE at once, and which is worth doing first depends on "
            "measured evidence (the `Measured` column: consistency and accuracy), not on the label. "
            "`Validity: invalid` means scores from this prompt cannot be trusted (for example leakage). "
            "`changed since review` means the prompt text differs from the one last reviewed. "
            "Rubric: `.claude/skills/prompt-review/references/rubric.md`."
        ),
        "",
        "Categories: " + ", ".join(f"`{c}`" for c in CATEGORIES) + ".",
        "",
    ]
    return "\n".join(lines)
