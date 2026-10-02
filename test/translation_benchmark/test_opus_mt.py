from pathlib import Path

import pandas as pd
from transformers import MarianMTModel, MarianTokenizer

INPUT_FILE = Path("test/translation_benchmark/benchmark_100.csv")
OUTPUT_FILE = Path("test/translation_benchmark/opus_mt_results.csv")

MODEL_ID = "tiedeman/opus-mt-he-en"

df = pd.read_csv(INPUT_FILE)

print(df.head())
print(f"Products loaded: {len(df)}")

print(f"\nLoading model: {MODEL_ID}")

tokenizer = MarianTokenizer.from_pretrained(MODEL_ID)
model = MarianMTModel.from_pretrained(MODEL_ID)

print("Model loaded successfully.")

# Translate the first 5 products
translations = []

for name in df["item_name"]:
    inputs = tokenizer(
        name,
        return_tensors="pt",
        padding=True,
        truncation=True,
    )

    translated_tokens = model.generate(**inputs)

    translation = tokenizer.decode(
        translated_tokens[0],
        skip_special_tokens=True,
    )
    translations.append(translation)
    print(f"\nHE: {name}")
    print(f"EN: {translation}")

df["opus_mt_translation"] = translations

df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8",
)

print(f"\nSaved {len(df)} translations to {OUTPUT_FILE}")