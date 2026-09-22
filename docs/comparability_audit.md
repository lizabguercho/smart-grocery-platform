# Catalog comparability audit

Related: [Documentation map](README.md) ·
[ETL pipeline](etl_pipeline.md) ·
[Remote database](remote_database_architecture.md)

Date of this pass: 9 September 2026. Scope: every eligible comparable
product, not only rows with `price_difference_pct >= 100`.

This is a **read-only** audit. It does not change
`grocery.product_classification`, `include_in_analysis`, analytical
tables, or `data/processed/tableau_price_comparison.csv`. A separate
conservative extract,
`data/processed/tableau_verified_three_chains.csv`, publishes only the
audit-valid three-chain rows.

---

## Question

Matching products by `item_code` assumes that Shufersal, Rami Levy, and
Victory published the same sellable SKU. The 70-product ≥100% review
showed that this is sometimes false: internal PLUs collide, packs
differ, and two Shufersal Cash&Carry stores can set a “chain” median
that no supermarket shopper pays.

This audit asks, for the full eligible catalog:

1. Do chain-specific PriceFull names, quantities, units, or manufacturers
   conflict?
2. Which barcodes look like short/internal PLUs, wholesale-only
   comparisons, or each-vs-kg mismatches?
3. What should be reviewed before Thursday’s dashboard, without treating
   every spelling difference as a bad match?

---

## Eligible catalog

A product is eligible when it appears in
`grocery.v_price_comparison_with_categories` with
`include_in_analysis = true`. That view already requires at least two
strictly positive chain medians.

| Count | Set |
|---:|---|
| 14,816 | Classified comparables in the Tableau view |
| **14,653** | Eligible (`include_in_analysis`) — this is the audit population |
| 70 | Previously reviewed because `price_difference_pct >= 100` |
| 14,583 | Newly scored in this pass |

The 70-product sheet
`data/processed/price_spread_100pct_review.csv` is included as-is.
Those 70 rows keep their human statuses (`valid` / `invalid` /
`uncertain`) and are **not** re-judged.

---

## Method

### Chain-specific metadata

`grocery.products` stores one name per barcode (last ETL write wins).
This audit does **not** use that name as the chain truth.

For every eligible barcode, ItemName, ManufactureName, Quantity,
UnitQty, QtyInPackage, and bIsWeighted were read from the official
**2026-08-19 PriceFull** files (585 gzipped files: 417 Shufersal, 98
Rami Levy, 70 Victory). Per chain, the majority value across stores is
kept, and distinct values are retained to detect within-chain
collisions. Manufacturer is **not** taken from `grocery.products`
(last ETL write wins, same gap as ItemName).

Coverage: **14,650 / 14,653** barcodes were present in those files.
Three barcodes are flagged `missing_pricefull_meta`.

Cleaned manufacturer fill among eligible barcodes that appear in that
chain’s PriceFull extract:

| Chain | Real manufacturer | Of chain-present items |
|---|---:|---|
| Shufersal | 9,556 | 83.7% of 11,416 |
| Victory | 7,830 | 70.6% of 11,085 |
| Rami Levy | 3,864 | 29.4% of 13,146 |

Placeholders (`לא ידוע`, `*`, empty, dash-only strings such as `---`)
are treated as missing via `UNKNOWN_TEXT_VALUES` and the same rules as
`clean_manufacture_name()`. XML entities in manufacturer text are
unescaped before comparison (`PROCTER&amp;GAMBLE` → `PROCTER&GAMBLE`).

Store-level latest prices still come from local PostgreSQL via
`src.database_loader.connection.get_connection()` (read-only).
Wholesale stores used here are only:

- Shufersal 161 המפיץ סיטונאות אשדוד (Cash&Carry)
- Shufersal 737 המפיץ סיטונאות באר שבע (Cash&Carry)

### What is not treated as invalid

Chain names are abbreviated differently (`קולגייט` vs `Colgate`, extra
kashrut words, pack count in the name vs in Quantity). A token-coverage
check treats two names as similar when at least half of the shorter
core-token set overlaps, or when one normalized name contains the
other. **Name difference alone never sets `invalid`.**

Victory often prints `UnitQty = קילוגרם` with `bIsWeighted = 0` on
piece goods. That pattern is ignored unless one chain is genuinely
weighted (`bIsWeighted = 1` and a weight unit) and another is a counted
unit.

Quantity `1` versus `50` on counted items is often “one pack SKU” vs
“fifty pieces in the pack” for the same carton. Those rows are
`needs_review`, not auto-`invalid`.

**Manufacturer difference alone never sets `invalid`.** If either chain
is missing a real manufacturer, that pair is skipped (neutral). If both
have a cleaned manufacturer, they are compared with the same
substring / token-coverage rule as names. A conflict sets
`manufacturer_conflict`. Status only rises to `needs_review` when that
flag is combined with `name_mismatch`, a short/internal barcode, or a
package-size mismatch (`quantity_ratio_ge_2` / `_ge_5`).
`partial_name_mismatch` is not enough.

### Rules (a row may hit several)

| Flag | Meaning |
|---|---|
| `collision_keyword` | PriceFull name contains דמי משלוח / הנחות / חזרות / הפרשים |
| `wholesale_only` | A chain median is built only from the two Cash&Carry stores, while another chain is retail |
| `each_vs_kg` | One chain is weighted kg, another is counted units |
| `internal_plu_pattern` | Barcode starts with `7290000000` (the collision family from the 70-product review) |
| `short_barcode` | Fewer than 13 digits |
| `quantity_ratio_ge_2` / `_ge_5` | Majority PriceFull quantities differ by that factor on the same unit basis (g, ml, or count) |
| `name_mismatch` | No chain pair is similar under the coverage rule |
| `partial_name_mismatch` | Some pairs similar, some not |
| `manufacturer_conflict` | Two chains have cleaned manufacturers that fail the name-similarity rule; missing manufacturer is not a conflict |
| `within_chain_name_conflict` | One chain published dissimilar ItemName values for the same barcode |
| `wholesale_mixed` | Cash&Carry stores are ≥50% of that chain’s observed stores, or the chain has ≤3 stores including wholesale |
| `missing_pricefull_meta` | Not in the 2026-08-19 PriceFull extract |

### Proposed status

| Status | When |
|---|---|
| `invalid` | Prior-review invalid, **or** `collision_keyword`, `wholesale_only`, or `each_vs_kg` |
| `uncertain` | Only from the prior 70-product review (4 rows) |
| `needs_review` | Internal PLU, short barcode with dissimilar names, real within-chain name split, significant wholesale mix, quantity ratio ≥5, quantity ratio ≥2 with spread ≥50%, name mismatch with spread ≥50%, **manufacturer conflict combined with name mismatch / short-or-PLU barcode / pack mismatch**, or missing PriceFull |
| `valid` | Everything else, including spelling-only name differences, manufacturer conflict by itself, and low-spread quantity quirks |

Auto-`invalid` is conservative on purpose. Extreme gram/ml pack ratios
are `needs_review` until someone looks at them.

---

## Findings

Checked: **14,653** eligible products.

### Proposed status

| proposed_status | n | Of which prior 70 | Newly scored |
|---|---:|---:|---:|
| valid | 13,006 | 39 | 12,967 |
| needs_review | 1,483 | 0 | 1,483 |
| invalid | 160 | 27 | 133 |
| uncertain | 4 | 4 | 0 |

Compared with the previous pass (names/qty/units only): **403** products
moved `valid` → `needs_review`. **None** moved to `invalid`. The prior
70 human statuses are unchanged.

### Rule hits (overlap allowed; flags can sit on `valid` rows)

| Rule | Products |
|---:|---|
| `name_mismatch` | 2,426 |
| `partial_name_mismatch` | 2,398 |
| `manufacturer_conflict` | 2,326 |
| `short_barcode` | 833 |
| `quantity_ratio_ge_5` | 666 |
| `quantity_ratio_ge_2` | 310 |
| `within_chain_name_conflict` | 153 |
| `wholesale_only` | 132 |
| `internal_plu_pattern` | 24 |
| `wholesale_mixed` | 16 |
| `each_vs_kg` | 8 |
| `collision_keyword` | 3 |
| `missing_pricefull_meta` | 3 |

Most `name_mismatch` and most `manufacturer_conflict` rows stay
**`valid`**. Manufacturer was comparable on 6,968 products (at least two
chains with a cleaned manufacturer); 2,326 of those conflict (33.4%).
Of the 2,326 conflicts, **1,665 stay `valid`** (conflict alone), 644
are `needs_review`, and 17 were already `invalid`.

Manufacturer conflict plus another raise-risk flag:

| Combined with | Products |
|---|---:|
| `name_mismatch` | 381 |
| `quantity_ratio_ge_5` | 145 |
| `short_barcode` | 112 |
| `quantity_ratio_ge_2` | 48 |
| `internal_plu_pattern` | 12 |

### Manufacturer conflicts on three-chain products

The Tableau dashboard will focus on barcodes priced in all three chains
(`chains_compared = 3`). That subset is **6,408** of 14,653.

| Metric | n |
|---|---:|
| Three-chain eligible products | 6,408 |
| At least two real manufacturers compared | 4,894 |
| `manufacturer_conflict` | 1,509 (30.8% of compared) |
| Conflict, still `valid` | 1,161 |
| Conflict, `needs_review` | 340 |
| Conflict, already `invalid` | 8 |
| Status moved `valid` → `needs_review` in this pass | 177 |
| High-risk (conflict + name mismatch / short-or-PLU / pack) | 319 |
| High-risk and spread ≥50% | 24 |

No three-chain row became `invalid` because of manufacturer.

Examples in the three-chain high-risk set (spread ≥50%). Several are
still brand vs legal entity and should not be excluded without a name
or pack check:

| Barcode | Spread | Why it is high-risk | Manufacturers (S / R / V) |
|---|---:|---|---|
| 7290000189734 | 85% | Pack ratio ≥5 (Nicole floor wipes) | חוגלה קימברלי / ניקול / עלבד |
| 7290013145840 | 73% | Pack ratio ≥5 (vanilla sugar) | א.ל תבלינים / י. כהן / א.ל תבלינים |
| 7290016197488 | 71% | Name + pack (microfiber cloths) | UFO INC / סטון טכנולגי / UFO INC |
| 7290005610509 | 68% | Pack ratio; different growers | קטיף / ביכורי השקמה / חבל מעון |
| 7290104965661 | 64% | Name mismatch (deodorant) | אמיליה / לא ידוע / אתאק פארמה |
| 80052760 | 61% | Short barcode only; likely Ferrero vs Kinder | פררו / קינדר / פררו |

Three-chain `proposed_status` after this pass: 5,676 valid, 696
needs_review, 35 invalid, 1 uncertain.

Of the 177 newly promoted three-chain rows, **91** also have
`name_mismatch`, **69** are mainly short barcode + manufacturer (often
brand vs legal entity: Kinder/Ferrero, Tic Tac, Mentos, Nature Valley),
and **22** have a pack-size ratio.

Rami Levy frequently puts the **brand** in `ManufactureName` (`עלית`,
`קינדר`, `דאב`) while Shufersal and Victory put the **legal entity**
(`שטראוס`, `פררו`, `יוניליוור`). Token coverage cannot equate those.
That is why manufacturer conflict is a raise-risk signal, not an
auto-invalid.

### New auto-invalid (133), not in the prior 70

- **128** wholesale-only Shufersal Cash&Carry medians
- **4** each-vs-kg (the other 4 each-vs-kg rows were already in the 70)
- **1** collision keyword: Shufersal name `דנונה ביו150ג להחזרות` (returns)

The confirmed aluminum pan `7290103152970` remains `invalid` from the
prior review (`audit_source = prior_70_review`).

### Manual review required

**1,487** rows: 1,483 `needs_review` + 4 prior `uncertain`.

Do not also re-review the 70 unless a status is being changed. Do not
try to read all 1,483 `needs_review` rows. For the Tableau three-chain
view, start with the **24** high-risk manufacturer-conflict rows that
also have spread ≥50%, then the **177** newly promoted three-chain
rows (name mismatch first, short-barcode brand/legal last).

---

## Output

`data/processed/comparability_audit.csv` — one row per eligible
barcode (14,653). Chain-specific names, manufacturers, and quantities
are from PriceFull, not from `grocery.products`. New columns:
`shufersal_manufacturer`, `rami_levy_manufacturer`,
`victory_manufacturer`, `manufacturer_compared`.

`data/processed/price_spread_100pct_review.csv` is unchanged and is
the source of the 70 prior statuses.

---

## Conservative published three-chain dataset

Dashboard methodology for a like-for-like three-chain comparison:

| Filter | Value |
|---|---|
| `include_in_analysis` | `true` |
| `chains_compared` | `3` |
| `proposed_status` | `valid` |

Coverage: **5,676 / 6,408** three-chain eligible products (**88.6%**).
The other 732 barcodes stay in the audit and in
`tableau_price_comparison.csv`, but they are not in the verified
extract:

| Left out of the verified extract | n |
|---|---:|
| `needs_review` (unresolved) | 696 |
| `invalid` | 35 |
| `uncertain` | 1 |

Those 696 review cases are not treated as comparable until someone
accepts or rejects them. Source prices are not capped. Valid spreads
that passed the audit — including the 150% chocolate muffins from the
70-product review — are retained, because a large percent is not
itself evidence of a barcode collision.

File: `data/processed/tableau_verified_three_chains.csv`. Columns match
the current Tableau extract / `grocery.v_price_comparison_with_categories`.
The workbook `Smart_Grocery_Dashboard.twb` is unchanged and still reads
`tableau_price_comparison.csv` until it is pointed at this file.

On this verified set (9 September 2026): mean
`price_difference_pct` is **19.14**. Category counts: Pantry & Cooking
1,123; Dairy & Eggs 792; Snacks & Sweets 759; Beverages 728; Personal
Care & Hygiene 645; Household & Cleaning 447; Bakery 388; Frozen 346;
Meat & Fish 174; Fresh Produce 98; Baby 93; Deli & Salads 83.

---

## Thursday dashboard strategy

Time-box. Do **not** try to read 1,483 rows, and do **not** exclude
anything until you approve it.

**Must-do (already judged or high confidence):**

1. Keep the prior 27 `invalid` and 4 `uncertain` decisions. Do not
   headline the 3,822% pan gap or the other ≥100% collisions.
2. Glance at the 8 `each_vs_kg` and 3 `collision_keyword` rows.
3. Glance at the 24 `7290000000…` internal PLU barcodes.
4. **Three-chain dashboard:** the 24 high-risk
   `manufacturer_conflict` rows with spread ≥50%. These are the ones
   that can still move a three-chain KPI.

**Should-do if there is a second hour:**

5. The 177 three-chain rows newly moved `valid` → `needs_review`.
   Start with `name_mismatch` (91). Treat short-barcode + manufacturer
   (69; Kinder/Ferrero, Tic Tac, Mentos) as likely brand vs company
   unless the names also diverge.
6. Filter remaining `needs_review` with `price_difference_pct >= 50`
   (170 rows catalog-wide, 47 in the three-chain subset).
7. Sample 15 of the 128 new wholesale-only `invalid` rows.

**Do not do before Thursday:**

- Re-score 13,006 `valid` rows by eye.
- Exclude a row only because manufacturers differ (Elite vs Strauss,
  Kinder vs Ferrero).
- Treat every Hebrew abbreviation as a collision.
- Cap prices, flip `include_in_analysis`, or overwrite
  `tableau_price_comparison.csv`.
- Treat a valid large spread as a collision. The verified extract keeps
  those rows.

The conservative three-chain extract
(`tableau_verified_three_chains.csv`) is the publishable subset. Point
the dashboard at that file if the workbook should show only like-for-like
SKU matches. The full extract and the audit CSV remain the complete
record, including the 696 unresolved `needs_review` barcodes.

---

## Limitations

- Snapshot is 2026-08-19 files only, not full history.
- Majority PriceFull name can hide a minority collision in one chain
  unless `within_chain_name_conflict` fires.
- Only two wholesale stores are identified. Other Cash&Carry or
  online-only branches are not modeled.
- Quantity `1` vs pack-count remains ambiguous on counted goods.
- Token coverage will miss some real collisions with shared generic
  words (`תבנית`, `חלב`) and will still flag some true matches with
  disjoint marketing copy.
- Rami Levy `QtyInPackage` is often `לא ידוע`; pack detection leans on
  Quantity and ItemName.
- Rami Levy `ManufactureName` is filled on only 29% of chain-present
  eligible items, and often holds the brand rather than the legal
  manufacturer. Brand vs company is a common false `manufacturer_conflict`.
- Token coverage cannot map `שטראוס` to `עלית` or `פררו` to `קינדר`.
- `grocery.products.manufacture_name` is still one overwritten value
  and was not used.

---

## Not implemented (needs approval)

These are recommendations only. None of them have been applied.

1. Stop using short `7290000000…` barcodes as cross-chain keys.
2. Exclude Shufersal stores 161 and 737 from chain medians used for
   consumer dashboards.
3. Persist chain-specific ItemName / Quantity / ManufactureName instead
   of overwriting `grocery.products`.
4. Flip `include_in_analysis` or drop rows from
   `grocery.product_classification` for audit `invalid` / `needs_review`
   barcodes. The verified Tableau extract filters them for publishing
   only.
5. Add a brand↔legal-entity alias list if manufacturer matching is
   used in the pipeline (Elite/Strauss, Kinder/Ferrero, Dove/Unilever).
6. Repoint `Smart_Grocery_Dashboard.twb` from
   `tableau_price_comparison.csv` to `tableau_verified_three_chains.csv`.

Classification flags and the original Tableau extract are unchanged.
Repoint the workbook only after you accept this publishing policy.
