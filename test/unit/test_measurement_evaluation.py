"""Evaluator fixtures: each kind of mistake must produce the expected error."""

from __future__ import annotations

from src.measurement_extraction.evaluation import bootstrap_ci, score_title, summarize
from src.measurement_extraction.schema import Annotation, Measurement

TITLE = 'שמפו 225 מ"ל'


def _ann(*entries: dict) -> Annotation:
    return Annotation(
        has_measurement=bool(entries), measurements=[Measurement(**e) for e in entries]
    )


GOLD = _ann(
    {
        "source_text": '225 מ"ל',
        "source_amount": 225,
        "source_unit": "mL",
        "measurement_role": "contents",
        "amount_scope": "whole_package",
    }
)


def _score(pred):
    return score_title(TITLE, GOLD, pred)


def test_correct_prediction_is_exact() -> None:
    same = _ann(
        {
            "source_text": '225 מ"ל',
            "source_amount": 225,
            "source_unit": 'מ"ל',
            "measurement_role": "contents",
            "amount_scope": "whole_package",
        }
    )
    assert _score(same).exact


def test_equivalent_amounts_match_but_wrong_magnitude_does_not() -> None:
    kg = score_title(
        'קמח 1.5 ק"ג',
        _ann({"source_text": '1.5 ק"ג', "source_amount": 1.5, "source_unit": "kg"}),
        _ann({"source_text": '1.5 ק"ג', "source_amount": 1500, "source_unit": "g"}),
    )
    assert kg.pairs[0]["amount"] and kg.pairs[0]["unit"]
    wrong = _score(
        _ann(
            {
                "source_text": '225 מ"ל',
                "source_amount": 225000,
                "source_unit": "mL",
                "measurement_role": "contents",
                "amount_scope": "whole_package",
            }
        )
    )
    assert not wrong.exact and not wrong.pairs[0]["amount"]


def test_wrong_role_unit_and_missing_extra() -> None:
    role = _score(
        _ann(
            {
                "source_text": '225 מ"ל',
                "source_amount": 225,
                "source_unit": "mL",
                "measurement_role": "capacity",
                "amount_scope": "whole_package",
            }
        )
    )
    assert not role.exact and not role.pairs[0]["role"] and role.pairs[0]["unit"]
    unit = _score(
        _ann({"source_text": '225 מ"ל', "source_amount": 225, "source_unit": "g"})
    )
    assert not unit.pairs[0]["unit"]
    missing = _score(_ann())
    assert not missing.exact and missing.pred_has is False
    extra = _score(
        _ann(
            GOLD.measurements[0].model_dump(),
            {"source_text": "225", "source_amount": 5},
        )
    )
    assert not extra.exact and extra.n_pred == 2


def test_failure_is_not_a_correct_negative() -> None:
    failed = _score(None)
    assert failed.failed and not failed.exact
    summary = summarize([failed])
    assert (
        summary["presence"]["fn"] == 1 and summary["presence_failed_predictions"] == 1
    )


def test_false_measurement_and_unsupported_unit() -> None:
    none_gold = score_title(
        "גזר ארוז", _ann(), _ann({"source_text": "ארוז", "source_amount": 1})
    )
    assert summarize([none_gold])["false_measurement_on_none"] == 1
    gold_raw = _ann({"source_text": "500", "source_amount": 500})
    invented = score_title(
        "ממרח 500",
        gold_raw,
        _ann({"source_text": "500", "source_amount": 500, "source_unit": "g"}),
    )
    assert summarize([invented])["unsupported_unit_completion"] == 1


def test_one_to_one_matching_never_double_counts() -> None:
    two = _ann(
        {"source_text": "500", "source_amount": 500},
        {"source_text": "500", "source_amount": 500},
    )
    one = _ann({"source_text": "500", "source_amount": 500})
    result = score_title("ממרח 500 500", two, one)
    assert len(result.pairs) == 1 and not result.exact


def test_counted_item_equivalence_and_bootstrap() -> None:
    a = _ann({"source_text": "20 שקיות", "package_count": 20, "counted_item": "שקיות"})
    b = _ann({"source_text": "20 שקיות", "package_count": 20, "counted_item": "שקית"})
    assert score_title("תה 20 שקיות", a, b).exact
    low, high = bootstrap_ci([1.0, 0.0] * 10)
    assert 0.2 < low < 0.5 < high < 0.8
