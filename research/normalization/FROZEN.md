# Frozen sets (2026-11-14)

Recorded before drawing a fresh test sample. These files are not edited again; later work uses new files.

| File | sha256 |
|---|---|
| samples/dev.csv | 9c5c0161f72e0e05046dd2a7e7daa5df3dfa724c57fc94af48bed439f043980a |
| samples/test.csv (first 100-title test, **retired**) | 82d9a94de06f0cf699caf8673fd648e25e51b093533353ed3d0461d0566da594 |
| gold/annotations.jsonl (dev gold, 100 saved items, guidelines v1) | 746fa7be8374af0cc9cb95d48de2988968260c228717d266f216a1fa1d9a48eb |

Systems at the freeze: measurement-rules 0.2.0, measurement-qwen 0.2.0 (prompt sha256 `b9d56bee8179f8fc8085dbe8031c1d1a151eb2f77b7a939e92a4c5799dd62ad0`), measurement-cascade 0.2.0.

Status of the sets:
- **dev** (100): development data, spent on tuning. Not usable for an independent claim.
- **old test** (100, never annotated or scored): its titles sit in the repo and its predictions were generated with the v0.1.0 prompts, but it was never labelled, scored or read for tuning. Retired as a test set; the new independent test is a fresh sample, drawn after this freeze. The old titles stay excluded from the new draw.
- **new test** (100): to be drawn with `scripts/draw_measurement_sample.py` (needs working remote DB credentials), labelled under guidelines v2 (assistant drafts for obvious items, marked `claude-draft`, confirmed by the human; the rest human), then scored once.

## New test set "test2" (drawn 2026-11-14, after the freeze above)
- Files: `samples/test2.csv` (titles only), `samples/test2_strata.csv` (stratum per item, kept out of the annotation page), `samples/test2_meta.json`; sha256 of `test2.csv`: `baa73bed38a153bb8ff1845277ea8c9a566ca7d8db60ea9f6792581c5e9737ce`. Drawn with `scripts/draw_measurement_test2.py` (seeded, immutable, refuses to redraw).
- Composition: 60 random titles (population claims) + 40 targeted stress titles (15 multi-pack `N*M` with unit, 15 count plus amount, 10 capacity container). Targeted items are reported separately from the random part.
- Excludes the original inspected 100, dev and the retired test (by code and folded name); verified no overlap.
- Labelled under guidelines v2. 52 of 100 titles have **assistant drafts** (`annotator: claude-draft`, state `draft`): single amounts, clear `N*M` multi-packs, containers with a stated capacity, and clear no-measurement titles (by-weight lines, shade codes, no number). The human confirms or corrects each in the annotation page (Test 2 split); the other 48 (count plus amount, unresolved abbreviations, ambiguous bare numbers) are left to the human. Results will be reported separately for drafted and human-labelled items.
- **Exposure note:** the assistant read the 100 test2 titles to draft labels. No rule, prompt or parser change may be made from them; systems are frozen at rules 0.2.0 / qwen 0.2.0 / cascade 0.2.0 (or newer versions frozen *before* test2 predictions exist). No predictions for test2 exist yet.

## Freeze before test2 predictions (2026-11-17)
- Labelling finished: all 100 test2 items saved by the human (23 of 52 drafts corrected, 29 confirmed). Gold log sha256 at freeze: `41c041e388e57132d406b9792662e64223863ebcc90087c77d470cabe84f2206` (the log also holds dev records).
- Systems run exactly as at the freeze above: rules 0.2.0, qwen 0.2.0 (prompt sha256 `b9d56bee...2ad0`), cascade 0.2.0. No system D. Predictions are generated once; no edits after seeing them.

## test2 first scoring (2026-11-17) and gold corrections made after it
- Predictions generated once (rules/qwen/cascade, versions above). First scoring gave joint entry P/R ≈ 0%: the test2 gold had `package_count=1` on 22 items and `counted_item` (the product noun) on 21 single mass/volume amounts, contrary to the guidelines and to dev gold.
- The annotator (who had forgotten the guidelines) instructed the removal of both. Applied by the assistant as logged revisions (every record has a `reason`), **after predictions existed**. The edits are convention fixes, made from the guidelines and not from system output; a system-output-driven change would not be allowed. Treat the post-fix scores as the test2 result and mention this order of events whenever quoting them.
- Scoring script changes (no system change): strata "started from an assistant draft" (52, 23 later corrected), "random part" (60) and "targeted part" (40).

## Status change (2026-11-18): test2 is development data
- After the first scoring, test2 was used for error analysis and a post-hoc run of Qwen 0.3.0; Qwen 0.4.0, guidelines v2.1, units-v2 and the evaluator's `counted_item` rule were all written from it. test2 therefore **stops being an independent test set**. Treat dev (100) + test2 (100) as one 200-title development set.
- The first (rules 0.2.0 / Qwen 0.2.0 / cascade 0.2.0) test2 numbers stay on record above as the only independent measurement ever taken; later numbers on test2 are development numbers.
- A fresh 100-title test sample is drawn only after the systems are frozen (rule 6 applies to it).
- Predictions kept for traceability: `qwen_test2_v0.2.0.jsonl`, `qwen_test2_v0.3.0.jsonl`, `cascade_test2_v0.2.0.jsonl`, `cascade_test2_v0.3.0.jsonl`, `qwen_dev_v0.{1,2,3}.0.jsonl`; current files are Qwen 0.4.0.
