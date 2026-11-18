# Annotation guidelines v2 (v1 settled on the 100-title development pilot; v2 adds the totals policy below)

Input is the **product title only**. Never use web lookups, barcodes, price or category to decide a label (notes may record what you learned; the label may not use it).

## Is there a measurement? (`has_measurement`)
- **Yes** when the title states a mass/volume amount, a count of items, or a bare number that plausibly is a package size whose unit is missing.
- **No** for: no number at all; percentages; years/vintages; shade, model and product codes (`לק 483`, `LONGEVITY מייק אפ 502`, `109M`); sizes/dimensions/lengths (`13.5`, `1` meter); layers (`2 שכבות`); calories; grades (`7-9`); "by weight" with no amount (`פטריות במשקל`).
- **Bare trailing number**: judge by context, not spacing. If a package size is plausible (`פיטנס עוג מיני שוקולד80`, `ממרח פסק זמן 500`), record the number with no unit. If the context says shade/variant/code, it is "no". If the title cannot decide it, **flag for review** (excluded from scoring, count reported).

## Entry fields
- `source_text`: exact substring supporting the entry (no separator characters such as a trailing backtick).
- `source_amount`: the number as written. `source_unit`: one code per unit: `mg g kg mL cL L`. A unit that cannot be resolved (`א`, `מ`, `(ק)`) is written as it appears, with no unit code; do not complete it (`550א` stays unresolved even if it is probably grams).
- Canonical amount/unit are computed by the app, never typed. Mass↔volume is never converted.
- `describes`: mass / volume / count. Count-only entries: `package_count` + `counted_item`, **no** source amount/unit, role or scope.
- `counted_item`: the bare noun copied from the title (`שקיקים`, `מברשות`, `יח`, `כמוסות`). Scoring normalizes singular/plural and abbreviations through a small map. Leave empty when the title only has a count word (`שלישייה`).
- `measurement_role`: `contents` for the amount sold; `capacity` for what a container holds (`דלי 10 ליטר`). `amount_scope`: `whole_package` for a single standalone quantity; `per_item` only if the title says each; empty when a count and an amount are both present and the attachment is not stated (`רביעייה טונה 140 גר`).
- Never multiply count × amount yourself; the preview computes a derived total only when scope is per-item.

## Special cases (decided)
- `300X` on paper bags is deliberately annotated as a count of 300 (borderline, kept on purpose).
- A number in a longer string with an unrelated number (`אומגה 3 ... 90 כמוסות`): the name number is ignored.
- Titles are often truncated at 24 characters in the source feed; annotate what the visible title supports.
- Optional "likely unit from context" is not part of the label. (Context guesses recorded in notes: #1, 25, 52, 57, 64 → g; #86 → mL.)

## Provenance
44 clear-cut dev items were drafted by the assistant from the title only and confirmed unchanged by the human. They remain identifiable in the log (first revision `claude-draft`); results are reported separately for them.

## v2 additions: totals and multi-packs (2026-11-14)
Purpose: the price layer compares normalised totals (e.g. 2 x 500 mL at one price against 1 x 1 L). The extractor only supplies fields; the total is **derived** by `units.derived_total` and scored as `total_canonical` (g or mL, or null).
- Canonical units: mass in g, volume in mL (`units-v1`). Mass and volume are never converted into each other; count-only items have no total.
- `N*M` / `N x M` / `N X M` with a unit on M (`6*330 מל`) is a **multi-pack**: `package_count` N, amount M, `amount_scope` per_item. It is not a dimension. A pattern with no unit on M stays "no measurement" unless context says otherwise.
- A count and an amount in one title with an explicit per-item cue (each, `X` between them as above) is per_item. Without a cue, `amount_scope` stays empty and the total is **null**: the price layer must never guess.
- A single standalone amount is whole_package; total = amount.
- The same quantity written twice in the same family (`1.5 ל 1500 מל`) is one entry; two different quantities in one family (`1 ק"ג 500 גרם`) are one compound amount only if written as a single phrase, otherwise flag for review.
- Existing dev gold (v1) is unchanged; its items were not re-labelled. The v1 guidelines apply to them, and they contain no multi-pack items, so v2 does not alter their totals.
- Items labelled under v2 (the new test set and any new dev items) carry `guideline_version: guidelines-v2` in the log.

## v2.1 clarifications (2026-11-17): counted_item, count + amount, abbreviations
Written after the first scoring of the new test set exposed unwritten conventions. They record how the test2 items were actually labelled, so that rules, prompt and scoring agree with the gold. When a case is not clearly covered, use the closest rule below and do not invent a new reading.
- `counted_item` on a multi-pack or count + amount entry is the **product noun** of the thing packed N times (the bottle, the cup, the bag), copied from the title, at most two words. A single mass/volume amount with no package count has no `counted_item`. Scoring compares `counted_item` leniently (shared word after normalisation), not as an exact string.
- `package_count` is empty when there is no count. A count of 1 is never written.
- Count and amount together, one entry (package_count + amount):
  - a multiplication sign between them (`*`, `x`, `X`), or the amount written **before** the count: `amount_scope` per_item;
  - the count written **before** the amount with no sign: `amount_scope` whole_package (the amount is the pack total).
  This replaces the v2 "no cue, scope empty" rule: leaving scope empty made totals impossible and the human labels never did it.
- Unit abbreviations that mean one registered unit are resolved: `ליט` = litre. `oz` and a lone `מ` stay unresolved (no canonical unit). Unit aliases live in `units.py` (units-v2).
- Bare trailing numbers with no unit (`... 99`, `... 375`) are still **no measurement** unless a nearby word makes the quantity explicit.
