from dataclasses import asdict, is_dataclass
from pathlib import Path

import pandas as pd


def _drop_empty_columns(df: pd.DataFrame) -> pd.DataFrame:
    non_empty_columns = [
        column
        for column in df.columns
        if df[column].notna().any() and df[column].astype(str).str.strip().ne("").any()
    ]
    return df[non_empty_columns]


def save_to_csv(products, chain_name: str) -> None:
    rows = [asdict(product) if is_dataclass(product) else product for product in products]

    df = pd.DataFrame(rows)
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / f"{chain_name}_products.csv", index=False, encoding="utf-8")
