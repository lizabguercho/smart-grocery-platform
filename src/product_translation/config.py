"""Named settings for Hebrew → English product-name translation.

Keeping these values in one file means the script and the translator
do not hide magic numbers or model names in the middle of the logic.
"""

from __future__ import annotations

# Qwen2.5-1.5B-Instruct is small enough for a laptop, instruction-tuned
# (it follows a "translate this" prompt), and multilingual enough for
# short Hebrew grocery names. First run downloads weights into the
# Hugging Face cache (~3 GB). Swap this string later if you want a
# larger Qwen, for example Qwen/Qwen2.5-3B-Instruct.
QWEN_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"

# Random review batch of Hebrew catalog names.
SAMPLE_BATCH_SIZE = 100

# First larger test batch. Raise this after you like the quality.
TEST_BATCH_SIZE = 100

# How many already-translated rows to re-run after a prompt change.
RETRY_FAILED_BATCH_SIZE = 20

# Product names are short; this is an upper bound, not a target length.
MAX_NEW_TOKENS = 64

# Hebrew letters live in this Unicode block (plus a few nearby marks).
HEBREW_LETTER_RANGE = (0x0590, 0x05FF)

SYSTEM_PROMPT = """\
Translate literally from Hebrew to English. This is a supermarket database.
Never guess or invent a product, brand, quantity, country, or unit.
If a brand is unknown, transliterate it (Hebrew letters to Latin letters). Do not replace it with a famous brand.
Copy numbers, units, and percentages exactly as written.
Output only the translation. No quotes, no explanation.
"""
