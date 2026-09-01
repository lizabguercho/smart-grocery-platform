from pathlib import Path

from src.product_classification.comparable_labels import (
    SuperCompareProduct,
    ComparableProduct,
    coverage_rows,
    deduplicate_products,
    include_in_analysis,
    join_to_comparable,
    to_classification_rows,
    write_combined_csv,
)


def _product(code: str, category: str, subcategory: str) -> SuperCompareProduct:
    return SuperCompareProduct(
        item_code=code,
        product_name="n",
        manufacturer=None,
        main_category=category,
        subcategory=subcategory,
        source_url="https://example.test",
    )


def test_deduplicate_keeps_first_row() -> None:
    first = _product("1", "Dairy & Eggs", "Milk")
    second = _product("1", "Dairy & Eggs", "Milk")
    unique, dropped = deduplicate_products([first, second, _product("2", "Baby", "Diapers")])
    assert dropped == 1
    assert [product.item_code for product in unique] == ["1", "2"]


def test_join_keeps_only_comparable_barcodes() -> None:
    products = [_product("1", "Dairy & Eggs", "Milk"), _product("2", "Baby", "Diapers")]
    matched = join_to_comparable(products, ["2"])
    assert [product.item_code for product in matched] == ["2"]


def test_coverage_and_exclusion_flags() -> None:
    unique = [
        _product("1", "Dairy & Eggs", "Eggs"),
        _product("2", "Dairy & Eggs", "Eggs"),
        _product("3", "Dairy & Eggs", "Milk"),
    ]
    matched = [_product("1", "Dairy & Eggs", "Eggs"), _product("3", "Dairy & Eggs", "Milk")]
    rows = {row.subcategory: row for row in coverage_rows(unique, matched)}
    assert rows["Eggs"].matched_comparable == 1
    assert rows["Eggs"].supercompare_unique == 2
    assert rows["Eggs"].status == "low"
    assert rows["Milk"].coverage_percent == 100.0

    promoted = to_classification_rows(matched)
    flags = {row.item_code: row.include_in_analysis for row in promoted}
    assert flags[1] is True
    assert flags[3] is True
    assert include_in_analysis("7290013083999") is False
    assert include_in_analysis("1", "Spices & Seasonings") is True
    assert include_in_analysis("7290013116024") is True


def test_write_combined_csv_includes_unlabeled_comparable_products(
    tmp_path: Path,
) -> None:
    comparable = [
        ComparableProduct("1", 10, 9, None, 9, "Rami Levy"),
        ComparableProduct("2", 5, 6, 7, 5, "Shufersal"),
    ]
    labels = {"1": _product("1", "Dairy & Eggs", "Milk")}
    output = tmp_path / "combined.csv"
    written = write_combined_csv(comparable, labels, {"1": "milk", "2": "bread"}, output)
    text = output.read_text(encoding="utf-8")
    assert written == 2
    assert "Dairy & Eggs" in text
    assert "Milk" in text
    assert "bread" in text
    assert text.splitlines()[2].startswith("2,bread,,,")


def test_write_combined_csv_can_keep_only_labeled_rows(tmp_path: Path) -> None:
    comparable = [
        ComparableProduct("1", 10, 9, None, 9, "Rami Levy"),
        ComparableProduct("2", 5, 6, 7, 5, "Shufersal"),
    ]
    labels = {"1": _product("1", "Dairy & Eggs", "Milk")}
    output = tmp_path / "analysis.csv"
    written = write_combined_csv(
        comparable,
        labels,
        {"1": "milk", "2": "bread"},
        output,
        require_label=True,
    )
    text = output.read_text(encoding="utf-8")
    assert written == 1
    assert "bread" not in text
    assert "Dairy & Eggs" in text
