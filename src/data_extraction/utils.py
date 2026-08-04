import pandas as pd
from pathlib import Path

def save_to_csv(products: list[dict[str, str | None]],chain_name: str) -> None:
    df = pd.DataFrame(products)
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / f"{chain_name}_products.csv", index=False,encoding="utf-8")