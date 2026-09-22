# Weekly grocery basket coverage

Related: [Documentation map](README.md) ·
[Comparability audit](comparability_audit.md) ·
[Project roadmap](project-roadmap.md)

Date: 9 September 2026. This is a **read-only** coverage study. It does
not change the database, classification labels, existing CSVs, or the
Tableau workbook. It does **not** compute or publish basket totals.

Candidate barcodes and chain coverage:
`data/processed/weekly_basket_candidates.csv`.

---

## Question

A useful weekly basket should look like a household shop, not like
whatever happens to survive a three-chain barcode filter. This note
proposes an illustrative 13-item basket, then asks:

1. Which lines already have a like-for-like `item_code` in the verified
   three-chain extract?
2. Which exist in the broader price-comparison / audit set, or only as
   store-level PriceFull rows?
3. For missing fresh produce and chicken: are they absent from the
   source files, or excluded because chains use different codes /
   weighted PLUs / audit flags?
4. How to compare a realistic basket **without** weakening the
   comparability audit (exact `item_code`, no automatic name join)?

---

## Illustrative weekly basket

**This basket is illustrative.** Quantities are a reasonable one-week
shop for a small household. They are not a survey of Israeli
consumption and are not a recommendation to buy these brands.

| Line | Proposed item | Illustrative quantity | Typical sell unit |
|---|---|---|---|
| 1 | Cow’s milk, 3% | 2 × 1 L | carton or bag |
| 2 | Farm eggs, size L | 1 × 12 | carton |
| 3 | Sliced white bread | 2 × ~750 g | loaf |
| 4 | Fresh chicken breast | ~1 kg | priced per kg |
| 5 | White rice | 1 × 1 kg | bag |
| 6 | Spaghetti | 1 × 500 g | pack |
| 7 | Potatoes | ~1 kg | loose / per kg |
| 8 | Tomatoes | ~1 kg loose, or 1 × 460 g cherry pack | per kg or pack |
| 9 | Cucumbers | ~1 kg | loose / per kg |
| 10 | Bananas | ~1 kg | loose / per kg |
| 11 | Plain / bio yogurt | 4 × ~200 g | cup |
| 12 | Dish soap | 1 × ~1 L | bottle |
| 13 | Toilet paper | 1 × 24 rolls | pack |

Thirteen lines sit in the requested 12–15 range and include the named
staples plus potatoes and two household products.

---

## Data layers checked

| Layer | What it is | Role here |
|---|---|---|
| PriceFull 2026-08-19 | Official chain files | Chain-specific names, `bIsWeighted`, quantity, unit, item price |
| `grocery.products` + `grocery.latest_product_prices` | Catalog + store prices | Whether an item exists at all, store counts, per-kg pricing |
| `grocery.price_comparison` | Same `item_code`, ≥2 positive chain medians | Cross-chain barcode match |
| `tableau_price_comparison.csv` / view | Classified comparables | Broader extract (~14,816) |
| `comparability_audit.csv` | Eligible comparables scored | Why a barcode is valid / needs_review / invalid |
| `tableau_verified_three_chains.csv` | `include_in_analysis`, 3 chains, audit `valid` | Conservative 5,676-product publish set |

Matching remains **exact `item_code`**. Different codes with the same
Hebrew name are **not** treated as the same product.

---

## Coverage summary

| Proposed item | Reliable 3-chain barcode today? | What exists instead |
|---|---|---|
| Milk 3% 1 L | Yes — verified | Several cartons/bags |
| Eggs 12 L farm | Same barcode in 3 chains, **audit `needs_review`** | Encoding 1 carton vs 12 eggs; free-range 12 L is the only verified egg |
| Bread ~750 g | Yes — verified | Regulated sliced loaf |
| Fresh chicken breast | **No** | Weighted per-kg SKUs, almost all 1- or 2-chain and brand-specific |
| Rice 1 kg | Yes — verified | Sugat / basmati bags |
| Spaghetti 500 g | Yes — verified | Osem / Barilla |
| Potatoes per kg | **No** 3-chain | 2-chain PLUs + chain-only PLUs |
| Tomatoes | Cherry **packs** yes; loose kg **no** | Chain-specific tomato PLUs |
| Cucumbers | **No** | Chain-specific PLUs; one 2-chain name is mixed vegetables |
| Bananas | **No** | Chain-specific weighted PLUs (product is on shelves) |
| Yogurt 200 g | Yes — verified | Tnuva / Danone cups |
| Dish soap ~1 L | Yes — verified | Fairy / Palmolive / Spark |
| Toilet paper 24 rolls | Yes — verified | Touch / Sano packs |

Eight packaged lines can already be compared like-for-like on the
verified extract. Five fresh lines (chicken, potatoes, loose tomatoes,
cucumbers, bananas) fail a three-chain barcode test even though the
goods are sold. Eggs fail the **audit**, not the source files.

---

## Line-by-line candidates

Prices below are **chain medians from the extracts / comparison table**,
or store-level averages for single-chain PLUs. They are shown so a
reviewer can see coverage, not to total a basket.

### 1. Milk — 2 × 1 L, 3%

**Available.** Same barcodes in all three chains; audit valid.

| Rank | `item_code` | Package | Chains | Stores (S/R/V) | Status |
|---|---|---|---|---|---|
| 1 | `7290004131074` | 1 L carton 3% | 3 | 274 / 39 / 68 | verified |
| 2 | `7290000042015` | 1 L 3% bag | 3 | 199 / 8 / 33 | verified |
| 3 | `7290000522319` | 1 L Golan 3% | 3 | 59 / 21 / 68 | verified |

### 2. Eggs — 1 × carton 12 size L

Farm eggs **are** in PriceFull and in the three-chain Tableau extract.
They were **excluded from the verified set by the audit**, not missing.

| Rank | `item_code` | Package | Chains | Stores | Notes |
|---|---|---|---|---|---|
| 1 | `7290001201589` | 12 L farm (לסר) | 3 | 271 / 64 / 39 | Tableau prices ~₪14.24 / 14.20 / 14.24. Audit `needs_review`: `quantity_ratio_ge_5` + `partial_name_mismatch` |
| 2 | `7290001201862` | 12 L free-range | 3 | 210 / 17 / 33 | Only egg in the verified extract. Different product from farm eggs. Classifier currently puts it in Snacks & Sweets — do not retag here. |
| 3 | `7290001201572` | 12 XL | 3 | 108 / 14 / 32 | Same 1-vs-12 quantity flag |
| 4 | `742259241901` | 12 L | Rami only | 87 | Different code. Do not join to `7290001201589`. |

PriceFull 2026-08-19 for `7290001201589`:

- Shufersal: `bIsWeighted=0`, Quantity **1**, UnitQty יחידות, name `12 ביצי משק טריות L לסר`, price ₪14.24
- Rami Levy: Quantity **1**, name `ביצים 12 יח L`, price ₪14.20
- Victory: Quantity **12**, name `ביצים 12 יח ארוזות L פיקוח מ.לסר`, price ₪14.24

The 12× quantity ratio is **carton vs egg count**, not a 12-pack vs
1-egg SKU. Names describe the same regulated 12 L farm carton.

**Basket-only exception (approved):** `7290001201589` may be used in
the weekly basket. Full PriceFull 2026-08-19 scan: Shufersal 313/313
name `12 ביצי משק טריות L לסר`, Quantity=1, ItemPrice **₪14.24**;
Rami Levy 89/89 name `ביצים 12 יח L`, Quantity=1, ItemPrice **₪14.20**;
Victory 70/70 name `ביצים 12 יח ארוזות L פיקוח מ.לסר`, Quantity=12,
ItemPrice **₪14.24**, UnitOfMeasurePrice ₪1.19 (= carton/12). Record:
`data/processed/weekly_basket_exceptions.csv`. The global audit flag
`quantity_ratio_ge_5` and `comparability_audit.csv` are unchanged.

### 3. Bread — 2 × sliced white ~750 g

**Available.** Verified three-chain barcodes.

| Rank | `item_code` | Package | Stores | Status |
|---|---|---|---|---|
| 1 | `7290000497112` | Regulated sliced 750 g | 171 / 49 / 30 | verified |
| 2 | `7290018500361` | Sliced 900 g | 224 / 94 / 31 | verified (larger loaf) |
| 3 | `7290000379142` | Einan 750 g | 30 / 22 / 3 | verified; fewer Victory stores |

### 4. Fresh chicken breast — ~1 kg, per kg

**Not comparable on a shared barcode across three chains.** Fresh
breast is sold as **weighted** (`bIsWeighted=1`) per kg. Chains use
**butcher / brand item codes**. Same Hebrew “חזה עוף טרי” does not
mean the same SKU.

| Rank | `item_code` | Name (catalog) | Chains | Stores | Audit |
|---|---|---|---|---|---|
| 1 | `7290002939108` | חזה עוף טרי ארוז עטרה | S+R | 88 / 5 / — | 2-chain, valid |
| 2 | `7290008455831` | חזה עוף טרי לנדא | S+R | 38 / 3 / — | 2-chain, valid |
| 3 | `7290003751334` | חזה עוף טרי ארוז העה"ח | S+R | 2 / 1 / — | 2-chain, valid; sparse |
| 4 | `2206057` | חזה עוף טרי שלם ארוז | Victory | — / — / 63 | not in `price_comparison` |
| 5 | `7290000616827` | חזה עוף טרי ארוז שלי לקג | Shufersal | 110 / — / — | not in `price_comparison` |
| 6 | `7290002105671` | טחון עוף 500 g | 3 | 2 / 69 / 20 | verified **ground chicken**, not breast |

Atara, Landa, and HaVaad HaArtzi are **different branded packs**.
Victory `2206057` is a Victory-only code. Store-level unit-of-measure
price equals item price for these weighted rows (price is already ₪/kg).

Verified three-chain “chicken” in the conservative extract is packed
frozen ground / schnitzel, not a fresh cut.

**Manual matching required** before any “1 kg chicken breast” line.
Do not auto-join these codes.

### 5. Rice — 1 × 1 kg

**Available.** Verified.

| Rank | `item_code` | Package | Stores |
|---|---|---|---|
| 1 | `7290000211169` | Sugat Thai 1 kg | 255 / 77 / 28 |
| 2 | `7290000211442` | Sugat Persian 1 kg | 268 / 54 / 57 |
| 3 | `7290113196414` | Basmati 1 kg | 67 / 81 / 23 |

### 6. Pasta — 1 × 500 g spaghetti

**Available.** Verified. Osem `7290000060880` has `manufacturer_conflict`
(brand vs company) and remains audit **valid**.

| Rank | `item_code` | Package | Stores |
|---|---|---|---|
| 1 | `7290000060880` | Osem spaghetti no.8 500 g | 263 / 93 / 22 |
| 2 | `8076800195057` | Barilla spaghetti no.5 500 g | 245 / 93 / 17 |
| 3 | `8076802085981` | Barilla fusilli 500 g | 245 / 90 / 27 (different shape) |

### 7. Potatoes — ~1 kg loose

**No three-chain barcode.** Weighted PLUs; chains invent their own
codes. A 2-chain PLU exists but is flagged `internal_plu_pattern`.

| Rank | `item_code` | Name | Chains | Stores | Status |
|---|---|---|---|---|---|
| 1 | `7290000000503` | תפוח אדמה קטן לאפיה | S+R | 239 / 17 | audit `needs_review` (`internal_plu_pattern`); variety names may differ |
| 2 | `7290018825020` | תפוח אדמה לבן גורמה | S+V | 204 / — / 39 | 2-chain, audit valid; missing Rami |
| 3 | `7290000000422` | תפוח אדמה לבן במשקל | Rami | 97 | single-chain PLU |
| 4 | `7290000000306` | תפוח אדמה אדום במשקל | Rami | 97 | red, not white |

**Uncertain without a human pair:** white vs red vs baking vs gourmet.
Do not treat `7290000000503` as identical to `7290018825020`.

### 8. Tomatoes — ~1 kg loose **or** 460 g cherry pack

**Cherry packs:** three-chain, verified. **Loose salad tomatoes:** sold
everywhere, **different PLUs**, not in `price_comparison`.

| Rank | `item_code` | Package | Chains | Stores | Status |
|---|---|---|---|---|---|
| 1 | `7290000993560` | Cherry shoko 460 g | 3 | 218 / 1 / 67 | verified; Rami 1 store |
| 2 | `7290000979427` | Cherry orange 460 g | 3 | 188 / 1 / 64 | verified |
| 3 | `7290002766056` | Cherry date 460 g | 3 | 287 / 1 / 33 | verified |
| 4 | `7290000000022` | עגבניה per kg | Shufersal | 316 | PriceFull w=1, ₪~6.90–6.76/kg |
| 5 | `7290000000100` | עגבניה per kg | Rami | 97 | PriceFull w=1, sample ₪4.90 |
| 6 | `7290016945041` | עגבניה מגי per kg | R+V | 63 / 1 | 2-chain Maggi; not generic tomato |

Cherry 460 g is **not** the same as 1 kg loose tomatoes. If the basket
uses cherry, label it as a pack, not as salad tomatoes.

### 9. Cucumbers — ~1 kg loose

**Genuinely no shared `item_code`.** Product is on shelves as weighted
kg. Shufersal and Rami use different PLUs with the **same** ItemName
`מלפפון`.

| Rank | `item_code` | Chains | Stores | PriceFull (sample 2026-08-19) |
|---|---|---|---|---|
| 1 | `7290000000046` | Shufersal | 318 | w=1, 1 kg, ₪7.90 (file sample); store avg ₪7.95 |
| 2 | `7290000000101` | Rami | 97 | w=1, UnitQty לא ידוע, ₪4.90 sample; store avg ₪5.37 |
| 3 | `7290009077667` | S+R | 58 / 3 | Tableau ₪35 / ₪48; name `מלפפון/ירקות במשקל` |

`7290009077667` is in the audit as **valid** two-chain, but the name
mixes cucumber with vegetables and the ₪/kg level does not match the
staple PLUs. **Do not use it as the cucumber line** without review.

Victory cucumbers were not found under these PLUs in the sampled
PriceFull files; they use other chain codes. **Manual matching
required** for a three-chain cucumber kg.

### 10. Bananas — ~1 kg

**Same pattern as cucumbers:** sold, weighted, **chain-specific codes**.
Not in the verified extract. Not missing from PriceFull.

| Rank | `item_code` | Chains | Stores | Notes |
|---|---|---|---|---|
| 1 | `7290000000134` | Rami | 97 | PriceFull name `בננה`, w=1, sample ₪7.90 |
| 2 | `2009` | Victory | 69 | Catalog `בננות ישראל`; short code; not in `price_comparison` |
| 3 | `7290000964775` | Shufersal | 278 | Catalog `בננה`, w=1; store avg ~₪13.43/kg; not in `price_comparison` |

These three codes must **not** be treated as one SKU. A basket line
would need an explicit human-approved triple (or a documented
“produce index” that is not barcode identity).

### 11. Yogurt — 4 × ~200 g

**Available.** Verified cups.

| Rank | `item_code` | Package | Stores |
|---|---|---|---|
| 1 | `7290000057132` | Tnuva bio 1.5% 200 g | 255 / 96 / 14 |
| 2 | `7290000057149` | Tnuva bio 3% 200 g | 248 / 96 / 18 |
| 3 | `7290000408316` | Danone bio 3% 200 g | 252 / 56 / 70 |

### 12. Dish soap — 1 × ~1 L

**Available.** Verified. Fairy is 900 ml, close to 1 L; Palmolive and
Spark are 1 L. Palmolive carries `name_mismatch` but stayed audit
**valid** — keep the existing status; do not re-score here.

| Rank | `item_code` | Package | Stores |
|---|---|---|---|
| 1 | `8001090184375` | Fairy original 900 ml | 128 / 81 / 34 |
| 2 | `7290004078270` | Palmolive lemon 1 L | 106 / 70 / 23 |
| 3 | `7290108350531` | Spark classic 1 L | 2 / 89 / 32 |

### 13. Toilet paper — 1 × 24 rolls

**Available.** Verified. UnitQty in the catalog is metres of paper, not
roll count; names still say 24 rolls. Touch vs Sano are different
brands/specs (792 m vs 441 m). Pick one SKU; do not mix packs.

| Rank | `item_code` | Name | Stores |
|---|---|---|---|
| 1 | `7290103704766` | Touch 24 double rolls | 35 / 11 / 50 |
| 2 | `7290107280112` | Sano Soft 24 rolls | 2 / 61 / 11 |
| 3 | `7290103704759` | Touch white **16** rolls | smaller pack |

---

## Missing vs excluded

| Basket line | In PriceFull / store prices? | In 3-chain comparison? | Why not in verified extract |
|---|---|---|---|
| Farm eggs 12 L `7290001201589` | Yes, all three chains | Yes | Audit `needs_review` (quantity 1 vs 12) |
| Loose cucumber / banana / tomato / potato | Yes, weighted kg | Usually **no** (single-chain codes) | No shared `item_code`; PLUs would also trip `internal_plu_pattern` |
| Fresh chicken breast | Yes, many weighted SKUs | At most **two** chains, brand-specific | Not three-chain; different brands must not be collapsed |
| Cherry tomato packs, milk, bread, rice, pasta, yogurt, soap, TP | Yes | Yes | Already verified (packaged) |
| `7290009077667` “cucumber/vegetables” | Yes, 2 chains | Yes, 2 chains | Not a clean staple; do not use as cucumber |

**Unavailable** here means “no like-for-like three-chain barcode,” not
“the chain does not sell cucumbers.”

---

## How to get a reliable basket without weakening the audit

Do **not**: auto-join on Hebrew name; treat `7290000000…` PLUs as
universal produce codes; drop `internal_plu_pattern` or
`quantity_ratio_ge_5`; mix Atara / Landa / Victory butcher codes; swap
cherry packs for loose tomatoes silently; publish a ₪ total until
matches are approved.

Do:

1. **Packaged core (now).** Build a barcode basket from verified SKUs:
   milk `7290004131074`, bread `7290000497112`, rice `7290000211169`,
   pasta `7290000060880`, yogurt `7290000057132`, dish soap
   `8001090184375` or Palmolive 1 L, toilet paper `7290103704766`.
   Optional tomato **pack**: `7290000993560`, labelled as cherry 460 g.

2. **Eggs (documented basket exception, approved).** Use
   `7290001201589` only in the basket exception list. Leave
   `quantity_ratio_ge_5` and `comparability_audit.csv` unchanged.

3. **Fresh produce and chicken (separate matching table).** Draft rows
   are in `data/processed/weekly_basket_fresh_matches.csv`. Proposed
   triples for cucumbers, loose tomatoes, and bananas are
   `approved`. Potatoes, chicken, and all alternative rows stay
   `pending`. Comparison is ₪/kg within a reviewed triple, not “same
   barcode.” Eggs `7290001201589` are a separate basket-only exception
   (approved). Potatoes and chicken stay pending and should be
   **excluded** from the comparable basket (Victory has no ordinary
   white potato; chicken plants/kashrut/cut are not shown to match).
   Do not publish basket totals in this pass.

4. **Two published stories, if needed.** (A) like-for-like packaged
   basket on verified barcodes; (B) fresh staples as a qualitative
   coverage note. That keeps the dashboard honest without pretending
   PLUs are GTIN identity.

5. **Store support filters.** Prefer candidates with stores in all
   three chains (Rami cherry tomatoes at 1 store is a weak 3-chain
   row even when the barcode matches).

No basket totals are calculated in this pass.

---

## Fresh matching table

File: `data/processed/weekly_basket_fresh_matches.csv`. One **proposed**
SKU per chain for cucumbers, loose tomatoes, white potatoes, bananas,
and fresh packed chicken breast, plus close **alternatives**. Prices are
store medians normalized to ₪/kg. Evidence columns are unchanged.

**Approved** (proposed rows only): cucumbers, loose tomatoes, bananas.

**Pending and excluded from the comparable basket:** potatoes and
chicken breast (`comparable_basket_recommendation=exclude`). Every
`alternative` row stays `pending` / `not_used`.

Final potato/chicken review (PriceFull 2026-08-19, not name/price
alone):

- **Potatoes — exclude.** Shufersal `7290000000596` (לבן תפזורת) and
  Rami `7290000000422` (לבן במשקל) are ordinary white potatoes by kg.
  Victory has **no** comparable bulk white SKU. The proposed Victory
  code `7290018825020` is PriceFull `תפוח אדמה גורמה - דוד משה`
  (branded gourmet). Other Victory weighted potatoes are frying,
  baby gourmet, cooking (4 files), or packed unnamed (3 files).
- **Chicken — exclude.** Proposed `7290000616827` (Shufersal, עוף עוז
  שלי packed), `7290002610700` (Rami, עוף ירושלים מהדרין, חת"),
  `2206057` (Victory, חזה עוף טרי שלם ארוז, manufacturer empty).
  All are fresh packed breast per kg, but plant, kashrut, and
  whole vs unspecified cut are not shown to be the same product.
  Similar ₪39.90–41.90/kg is not treated as equivalence.
- **Victory produce PLUs** `2028` / `2036` / `2009` are short internal
  codes; names add `ישראל` while other chains often omit origin.
- **Rami UnitQty** is often `לא ידוע` even when unit of measure is kg.
- Same Hebrew name with a second barcode (Rami cucumber, Shufersal
  banana) was not merged.

---

## Files

| Path | Role |
|---|---|
| `docs/weekly_basket_coverage.md` | This report |
| `data/processed/weekly_basket_candidates.csv` | 47 candidate rows (rank, codes, units, chain prices/stores, audit flags, match status) |
| `data/processed/weekly_basket_fresh_matches.csv` | Pending human matches for fresh basket lines (₪/kg) |
| `data/processed/weekly_basket_exceptions.csv` | Basket-only approvals that do not change the catalog audit (eggs 12 L) |

Unchanged: database, classifications, `comparability_audit.csv`,
`tableau_price_comparison.csv`, `tableau_verified_three_chains.csv`,
Tableau workbook.
