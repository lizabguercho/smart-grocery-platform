import csv
import os
from collections import Counter
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parents[1]
csv_path = root / "data/processed/price_comparison_with_categories.csv"
out = root / "docs/images"
out.mkdir(parents=True, exist_ok=True)

with csv_path.open(encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))

n = len(rows)
main = Counter(row["category"] for row in rows)
sub = Counter(f"{row['category']} / {row['subcategory']}" for row in rows)

items = main.most_common()
labels = [name for name, _ in items][::-1]
counts = [count for _, count in items][::-1]
pcts = [count / n * 100 for count in counts]
fig, ax = plt.subplots(figsize=(10, 6.5))
bars = ax.barh(labels, pcts, color="#2f5d50")
ax.axvline(100 / n * 100, color="#b45309", linestyle="--", linewidth=1, label="100 examples")
ax.set_xlabel("% of labeled comparable products (n = 5,718)")
ax.set_title("Labeled comparable products by main category")
for bar, count, pct in zip(bars, counts, pcts):
    ax.text(
        bar.get_width() + 0.15,
        bar.get_y() + bar.get_height() / 2,
        f"{count:,} ({pct:.1f}%)",
        va="center",
        fontsize=8,
    )
ax.set_xlim(0, max(pcts) * 1.28)
ax.legend(loc="lower right", fontsize=8)
fig.tight_layout()
fig.savefig(out / "labeled_comparable_main_categories.png", dpi=150)
plt.close(fig)

items = sub.most_common()
labels = [name for name, _ in items][::-1]
counts = [count for _, count in items][::-1]
pcts = [count / n * 100 for count in counts]
colors = ["#2f5d50" if c >= 100 else "#b45309" if c >= 50 else "#9b1c1c" for c in counts]
fig, ax = plt.subplots(figsize=(11, 14))
bars = ax.barh(labels, pcts, color=colors)
ax.axvline(50 / n * 100, color="#b45309", linestyle="--", linewidth=1, label="50 examples")
ax.axvline(100 / n * 100, color="#2f5d50", linestyle=":", linewidth=1, label="100 examples")
ax.set_xlabel("% of labeled comparable products (n = 5,718)")
ax.set_title("Labeled comparable products by subcategory")
for bar, count, pct in zip(bars, counts, pcts):
    ax.text(
        bar.get_width() + 0.08,
        bar.get_y() + bar.get_height() / 2,
        f"{count:,} ({pct:.1f}%)",
        va="center",
        fontsize=6.5,
    )
ax.set_xlim(0, max(pcts) * 1.32)
ax.legend(loc="lower right", fontsize=8)
fig.tight_layout()
fig.savefig(out / "labeled_comparable_subcategories.png", dpi=150)
plt.close(fig)
print("wrote charts")
