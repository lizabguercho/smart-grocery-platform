"""Parse raw model text into GroceryUnderstandingPrediction without crashing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pydantic import ValidationError

from src.slm_benchmark.schema import GroceryUnderstandingPrediction

_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


@dataclass(frozen=True)
class ParseResult:
    parse_success: bool
    prediction: GroceryUnderstandingPrediction | None
    error_message: str | None
    extracted_json_text: str | None


def _extract_json_candidate(raw_text: str) -> str | None:
    stripped = (raw_text or "").strip()
    if not stripped:
        return None

    fenced = _FENCE.search(stripped)
    if fenced:
        return fenced.group(1).strip()

    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return stripped[start : end + 1]
    return None


def parse_model_output(raw_text: str) -> ParseResult:
    """Validate model output. Parsing failures are results, not exceptions."""

    candidate = _extract_json_candidate(raw_text)
    if candidate is None:
        return ParseResult(
            parse_success=False,
            prediction=None,
            error_message="no_json_object_found",
            extracted_json_text=None,
        )

    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return ParseResult(
            parse_success=False,
            prediction=None,
            error_message=f"json_decode_error:{exc.msg}",
            extracted_json_text=candidate,
        )

    if not isinstance(payload, dict):
        return ParseResult(
            parse_success=False,
            prediction=None,
            error_message="json_not_object",
            extracted_json_text=candidate,
        )

    try:
        prediction = GroceryUnderstandingPrediction.model_validate(payload)
    except ValidationError as exc:
        return ParseResult(
            parse_success=False,
            prediction=None,
            error_message=f"schema_validation_error:{exc.error_count()}",
            extracted_json_text=candidate,
        )

    # Prompt requires category=null when is_product=false. Coerce so JSON
    # that only violates that cross-field rule still counts as parsed;
    # the wrong is_product / category values remain visible for metrics.
    prediction = prediction.with_non_product_category_cleared()

    return ParseResult(
        parse_success=True,
        prediction=prediction,
        error_message=None,
        extracted_json_text=candidate,
    )
