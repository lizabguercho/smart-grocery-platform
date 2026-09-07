"""Promote SuperCompare labels for comparable products to the remote database."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from src.database_loader.connection import get_remote_connection
from src.product_classification.comparable_labels import (
    ClassificationRow,
    SuperCompareProduct,
    category_counts,
    coverage_rows,
    format_share,
    join_to_comparable,
    load_unique_products,
    sample_codes_by_subcategory,
    to_classification_rows,
)
from src.product_classification.supercompare.config import DEFAULT_PRODUCTS_PATH

UPSERT_SQL = """
INSERT INTO grocery.product_classification (
    item_code,
    category,
    subcategory,
    include_in_analysis,
    classification_method,
    classification_confidence
)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (item_code) DO UPDATE SET
    category = EXCLUDED.category,
    subcategory = EXCLUDED.subcategory,
    include_in_analysis = EXCLUDED.include_in_analysis,
    classification_method = EXCLUDED.classification_method,
    classification_confidence = EXCLUDED.classification_confidence
"""


def fetch_comparable_codes() -> list[str]:
    connection = get_remote_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT item_code FROM grocery.price_comparison")
        rows = cursor.fetchall()
    connection.close()
    return [str(row[0]) for row in rows]


def fetch_product_names(item_codes: Sequence[str]) -> dict[str, str]:
    if not item_codes:
        return {}
    connection = get_remote_connection()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT item_code, item_name
            FROM grocery.products
            WHERE item_code = ANY(%s)
            """,
            ([int(code) for code in item_codes],),
        )
        rows = cursor.fetchall()
    connection.close()
    return {str(row[0]): row[1] for row in rows}


def promote_rows(rows: Sequence[ClassificationRow]) -> int:
    connection = get_remote_connection()
    params = [
        (
            row.item_code,
            row.category,
            row.subcategory,
            row.include_in_analysis,
            row.classification_method,
            row.classification_confidence,
        )
        for row in rows
    ]
    with connection.cursor() as cursor:
        cursor.executemany(UPSERT_SQL, params)
        cursor.execute("SELECT COUNT(*) FROM grocery.product_classification")
        count = cursor.fetchone()[0]
    connection.commit()
    connection.close()
    return int(count)


def write_charts(
    matched: Sequence[SuperCompareProduct],
    output_dir: Path,
) -> tuple[Path, Path]:
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    main_counts, sub_counts = category_counts(matched)
    total = len(matched)

    main_sorted = main_counts.most_common()
    labels = [name for name, _ in main_sorted]
    values = [count for _, count in main_sorted]
    percents = [count / total * 100 for count in values]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(labels[::-1], percents[::-1], color="#2f5d50")
    ax.set_xlabel("% of labeled comparable products")
    ax.set_title("Comparable products with SuperCompare labels by main category")
    for bar, count, percent in zip(bars, values[::-1], percents[::-1]):
        ax.text(
            bar.get_width() + 0.2,
            bar.get_y() + bar.get_height() / 2,
            f"{count:,} ({percent:.1f}%)",
            va="center",
            fontsize=8,
        )
    ax.set_xlim(0, max(percents) * 1.25 if percents else 1)
    fig.tight_layout()
    main_path = output_dir / "supercompare_comparable_main_categories.png"
    fig.savefig(main_path, dpi=150)
    plt.close(fig)

    sub_sorted = sub_counts.most_common()
    sub_labels = [name for name, _ in sub_sorted]
    sub_values = [count for _, count in sub_sorted]
    sub_percents = [count / total * 100 for count in sub_values]

    fig_height = max(10, 0.28 * len(sub_labels))
    fig, ax = plt.subplots(figsize=(12, fig_height))
    bars = ax.barh(sub_labels[::-1], sub_percents[::-1], color="#4a7c6f")
    ax.set_xlabel("% of labeled comparable products")
    ax.set_title("Comparable products with SuperCompare labels by subcategory")
    for bar, count, percent in zip(bars, sub_values[::-1], sub_percents[::-1]):
        ax.text(
            bar.get_width() + 0.15,
            bar.get_y() + bar.get_height() / 2,
            f"{count:,} ({percent:.1f}%)",
            va="center",
            fontsize=7,
        )
    ax.set_xlim(0, max(sub_percents) * 1.35 if sub_percents else 1)
    fig.tight_layout()
    sub_path = output_dir / "supercompare_comparable_subcategories.png"
    fig.savefig(sub_path, dpi=150)
    plt.close(fig)
    return main_path, sub_path


def print_review(
    unique_products: Sequence[SuperCompareProduct],
    matched: Sequence[SuperCompareProduct],
    comparable_codes: Sequence[str],
    names: dict[str, str],
) -> None:
    comparable_total = len(set(comparable_codes))
    unique_total = len(unique_products)
    matched_total = len(matched)
    print("=== join summary ===")
    print("SuperCompare unique barcodes:", unique_total)
    print("Comparable products (price_comparison):", comparable_total)
    print("Labeled comparable products:", matched_total)
    print(
        "Share of comparable set labeled:",
        format_share(matched_total, comparable_total),
    )
    print(
        "Share of SuperCompare barcodes that are comparable:",
        format_share(matched_total, unique_total),
    )

    print(
        "\n=== coverage by subcategory (matched comparable / SuperCompare unique) ==="
    )
    for row in coverage_rows(unique_products, matched):
        print(
            f"{row.main_category}\t{row.subcategory}\t"
            f"{row.matched_comparable}/{row.supercompare_unique}\t"
            f"{row.coverage_percent:.1f}%\t{row.status}"
        )

    main_counts, sub_counts = category_counts(matched)
    print("\n=== labeled comparable distribution (main) ===")
    for name, count in main_counts.most_common():
        print(f"{name}\t{count}\t{format_share(count, matched_total)}")

    print("\n=== labeled comparable distribution (sub) ===")
    for name, count in sub_counts.most_common():
        print(f"{name}\t{count}\t{format_share(count, matched_total)}")

    print("\n=== weak-slice name samples ===")
    for subcategory in (
        "Eggs",
        "Fresh Fruit",
        "Fresh Vegetables",
        "Fresh Herbs",
        "Beef & Lamb",
        "Dips & Spreads",
        "Spices & Seasonings",
        "Packaged Salads",
        "Prepared Foods",
        "Hummus & Tahini",
    ):
        samples = sample_codes_by_subcategory(matched, subcategory, limit=6)
        print(
            f"\n-- {subcategory} (n={sum(1 for p in matched if p.subcategory == subcategory)}) --"
        )
        for product in samples:
            print(
                product.item_code,
                "|",
                names.get(product.item_code, "?"),
                "|",
                product.product_name,
            )


def main() -> None:
    unique_products, dropped = load_unique_products(DEFAULT_PRODUCTS_PATH)
    print(f"Dropped duplicate CSV rows: {dropped}")
    comparable_codes = fetch_comparable_codes()
    matched = join_to_comparable(unique_products, comparable_codes)
    names = fetch_product_names([product.item_code for product in matched])
    print_review(unique_products, matched, comparable_codes, names)

    chart_dir = Path("docs/images")
    main_chart, sub_chart = write_charts(matched, chart_dir)
    print("Wrote", main_chart)
    print("Wrote", sub_chart)

    rows = to_classification_rows(matched)
    included = sum(1 for row in rows if row.include_in_analysis)
    print(f"Promoting {len(rows)} rows ({included} include_in_analysis=true)")
    total = promote_rows(rows)
    print("Remote grocery.product_classification row count:", total)


if __name__ == "__main__":
    main()
