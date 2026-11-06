# Annotation guidelines v1 (settled on the 100-title development pilot)

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
