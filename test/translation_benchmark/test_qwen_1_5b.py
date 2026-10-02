from pathlib import Path

import pandas as pd

from src.product_translation.name_translator import QwenProductNameTranslator


INPUT_FILE = Path("test/translation_benchmark/benchmark_100.csv")
OUTPUT_FILE = Path("test/translation_benchmark/qwen_1_5b_results.csv")


df = pd.read_csv(INPUT_FILE)

print(df.head())
print(f"Products loaded: {len(df)}")

# Translate the first 1 product
translator = QwenProductNameTranslator()

print("\nLoading Qwen...")
translator.load()
print("Qwen loaded.")

translations = []

for index, name in enumerate(df["item_name"], start=1):
    translation = translator.translate(name)
    translations.append(translation)

    print(f"[{index}/{len(df)}] HE: {name}")
    print(f"          EN: {translation}")

df["qwen_1_5b_translation"] = translations

df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8",
)

print(f"\nSaved {len(df)} translations to {OUTPUT_FILE}")