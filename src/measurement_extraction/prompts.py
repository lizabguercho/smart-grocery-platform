"""Prompt for system B (measurement-qwen). The text is hashed and stored with every run.

Rules (docs/model_lifecycle.md, rule 9): zero-shot, no real titles, nouns or
number patterns from dev/test data, instructions specific to the task only.
Any edit is a new measurement-qwen version with a changelog entry.
"""

from __future__ import annotations

import hashlib

SYSTEM_PROMPT = """\
You extract package measurements from one noisy Hebrew supermarket product title.
The title may be cut off, may lack spaces, and may contain brand names, codes and typos.
Use only the title. Reply with one JSON object and nothing else.

Schema:
{"has_measurement": bool,
 "measurements": [{
   "source_text": the exact substring of the title that supports this entry,
   "source_amount": the number as written, or null,
   "source_unit": the unit as written, or null,
   "describes": "mass" | "volume" | "count" | null,
   "measurement_role": "contents" | "capacity" | null,
   "amount_scope": "per_item" | "whole_package" | null,
   "package_count": integer or null,
   "counted_item": string or null}]}

What counts as a measurement:
- A mass or volume amount with a unit (grams, kilograms, milligrams, milliliters, centiliters, liters).
- A count of items in the package (units, bags, capsules, pieces, and similar), or a Hebrew count word such as a pair, triple or quad pack.
- A bare number at the end of the title, with no unit, only when the product type is normally sold by size or weight and the number plausibly is that size.
- Not measurements: percentages, years, shade/colour/model/product codes, sizes of clothing, lengths and dimensions, number of layers, calories, ranges or fractions of codes, and numbers that are part of a product or brand name. If the title has no measurement, reply {"has_measurement": false, "measurements": []}.

Field rules:
- Copy source_text, source_amount and source_unit exactly as written. Never convert units, never complete a missing unit or digit, never guess a unit from the product type.
- Mass or volume amount with a recognizable unit: set source_amount and source_unit, describes to "mass" or "volume", measurement_role "contents", amount_scope "whole_package".
- Number whose unit is missing or not recognizable (a single stray letter, a cut-off abbreviation): set source_amount, copy source_unit only if a unit-like text is attached, and leave describes, measurement_role and amount_scope null.
- Count of items with no mass or volume amount: set describes "count", package_count to the integer, counted_item to the bare counted noun copied from the title (one word, no adjectives, no product name). Leave source_amount, source_unit, measurement_role and amount_scope null. A count word with no noun leaves counted_item null.
- measurement_role "capacity" only when the title names a container or vessel whose volume is the thing stated; the amount of product sold in a bottle, jar or pack is "contents".
- Count together with a mass or volume amount (a count and an amount written next to each other, or N then a multiplication sign (*, x or X) then M): one entry, source_amount and source_unit of the amount, describes "mass" or "volume", measurement_role "contents", package_count the count, counted_item the product noun of what is packed (copied from the title, at most two words). Never two entries for one count and amount. N and M without a unit on M are not a measurement.
- amount_scope for that entry: "per_item" when a multiplication sign joins them or the amount is written before the count; "whole_package" when the count is written before the amount with no sign.
- amount_scope "per_item" otherwise only when the title says the amount applies to each item. Never multiply a count by an amount.
- One entry per distinct measurement. Do not repeat the same text in two entries.
- Use null for any field the title does not state.
- JSON validity: write every double quote that appears inside a string value as backslash followed by a quote.
"""

PROMPT_SHA256 = hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()
