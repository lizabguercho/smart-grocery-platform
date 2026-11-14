"""Named settings for the measurement annotation and extraction experiments."""

from __future__ import annotations

from pathlib import Path

SCHEMA_VERSION = "measurement-schema-v1"
GUIDELINE_VERSION = "guidelines-v1"
UNITS_REGISTRY_VERSION = "units-v1"

SAMPLE_FILE = Path("research/samples_product.txt")
NORMALIZATION_DIR = Path("research/normalization")
SAMPLES_DIR = NORMALIZATION_DIR / "samples"
PREDICTIONS_DIR = NORMALIZATION_DIR / "predictions"
GOLD_PATH = NORMALIZATION_DIR / "gold" / "annotations.jsonl"

# Annotation budget: the human labels at most this many distinct products.
DEV_SIZE = 100
TEST_SIZE = 100
SPLIT_SEED = 20261027

# Pilot slice of the development set used to settle the guideline.
PILOT_SIZE = 20
