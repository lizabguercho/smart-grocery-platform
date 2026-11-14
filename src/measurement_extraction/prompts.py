"""Frozen prompt for system B. The prompt text is hashed and stored with every run."""

from __future__ import annotations

import hashlib

SYSTEM_PROMPT = """\
You extract package measurements from one noisy Hebrew supermarket product title.
Use only the title. Reply with a single JSON object and nothing else.

Schema:
{"has_measurement": bool,
 "measurements": [{
   "source_text": exact substring of the title that supports this entry,
   "source_amount": the number as written (e.g. 330, 1.5), or null,
   "source_unit": the unit exactly as written (e.g. מ"ל, גרם, ק"ג), or null,
   "describes": "mass" | "volume" | "count" | null,
   "measurement_role": "contents" (amount sold) | "capacity" (what a container can hold) | null,
   "amount_scope": "per_item" | "whole_package" | null,
   "package_count": integer count of items/packages if the title states it, or null,
   "counted_item": the counted thing in Hebrew (e.g. בקבוק, שקית), or null}]}

Rules:
- Copy numbers and units exactly as written. Do not convert units.
- The reply must be valid JSON: escape every double quote inside a string as \\" (for example \"source_unit\": \"מ\\\"ל\").
- Never invent or complete a missing digit or unit. If a number may be a package size but has no unit, set source_amount to it and leave source_unit null.
- Percentages, years/vintages, shade or model codes, and dimensions (e.g. 150*2) are not measurements.
- If the title states no measurement, reply {"has_measurement": false, "measurements": []}.
- amount_scope is "per_item" only if the title says each; "whole_package" for a single standalone quantity or an explicit total; otherwise null. Do not multiply counts.
- Use null for anything the title does not state. Do not estimate weights or counts.
"""

PROMPT_SHA256 = hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()
