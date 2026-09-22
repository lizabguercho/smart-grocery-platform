# Weekly essentials basket results

Related: [Coverage](weekly_basket_coverage.md) ·
[Comparability audit](comparability_audit.md)

Date: 9 September 2026. Illustrative 13-line household basket. Not a
consumption survey. **No change** to the database, `comparability_audit.csv`,
classifications, existing price extracts, or the Tableau workbook.

Tableau file: `data/processed/weekly_basket_comparison.csv` (39 rows: 13
lines × 3 chains). Filter is unnecessary if you sum `line_total` by
`chain`; do not also sum `chain_basket_total`.

---

## Coverage

The intended weekly shop still includes potatoes and fresh chicken
breast. Those two lines are **out of this comparable basket**.

| Count | Set |
|---:|---|
| 13 | Lines in this comparison |
| 11 | Earlier approved staples |
| +2 | Tuna `7290005287930`, lentils `7290001041208` |
| 2 excluded | Potatoes, chicken (pending; `comparable_basket_recommendation=exclude`) |

This is **13 comparable lines**, not 13/13 of the original intended
basket. Original intended staples were 13 before tuna/lentils were
added and potatoes/chicken dropped from the money comparison.

---

## Basket totals

Representative prices × stated quantities. Rounded to agorot
(half-up) at the line, then summed.

| Chain | Basket total |
|---|---:|
| **Rami Levy** | **₪193.70** |
| Shufersal | ₪203.00 |
| Victory | ₪210.00 |

**Cheapest:** Rami Levy.  
**Vs most expensive (Victory):** **₪16.30** cheaper (**7.76%**).  
Vs Shufersal: ₪9.30 cheaper (4.58%).

---

## Line table (₪)

| # | Item | Qty | Code(s) | Shufersal | Rami Levy | Victory |
|---|---|---|---|---:|---:|---:|
| 1 | Milk 3% 1 L carton | 2 | `7290004131074` | 14.70 | 14.40 | 14.70 |
| 2 | Eggs 12 L farm | 1 carton | `7290001201589` | 14.24 | 14.20 | 14.24 |
| 3 | Sliced bread 750 g | 2 | `7290000497112` | 16.76 | 16.40 | 16.76 |
| 4 | Sugat Thai rice 1 kg | 1 | `7290000211169` | 7.90 | 7.90 | 8.90 |
| 5 | Osem spaghetti 500 g | 1 | `7290000060880` | 6.50 | 4.90 | 6.90 |
| 6 | Loose tomatoes | 1 kg | S `7290000000022` / R `7290000000100` / V `2036` | 6.90 | 4.90 | 6.90 |
| 7 | Cucumbers | 1 kg | S `7290000000046` / R `7290000000101` / V `2028` | 7.90 | 5.90 | 7.90 |
| 8 | Bananas | 1 kg | S `7290000964775` / R `7290000000134` / V `2009` | 12.90 | 9.90 | 13.90 |
| 9 | Tnuva bio 1.5% 200 g | 4 | `7290000057132` | 15.60 | 14.40 | 17.60 |
| 10 | Palmolive lemon 1 L | 1 | `7290004078270` | 14.90 | 13.90 | 16.90 |
| 11 | Touch TP 24 rolls | 1 | `7290103704766` | 46.90 | 49.90 | 46.90 |
| 12 | Starkist tuna in water 4×160 g | 1 pack | `7290005287930` | 24.90 | 24.90 | 25.90 |
| 13 | Mia green lentils 1 kg | 1 | `7290001041208` | 12.90 | 12.10 | 12.50 |
| | **Total** | | | **203.00** | **193.70** | **210.00** |

Toilet paper is the only line where Rami Levy is not cheapest (₪49.90 vs
₪46.90). Produce ₪/kg gaps are the other large Rami Levy advantages.

---

## SKU and quantity rules

Packaged lines use **one verified three-chain barcode**
(`tableau_verified_three_chains.csv`). Fresh produce uses **approved
chain-specific PLUs** (`weekly_basket_fresh_matches.csv`,
`approval_status=approved`). Eggs use the **basket-only exception**
(`weekly_basket_exceptions.csv`); the catalog audit is unchanged.

| Line | Why this SKU / qty |
|---|---|
| Milk | Rank-1 verified 1 L carton; **2 ×** unit price |
| Eggs | Same GTIN; carton `ItemPrice` (not Victory ₪1.19/egg) |
| Bread | Verified 750 g loaf; **2 ×** unit price |
| Rice / pasta / lentils | Exact 1 kg / 500 g / 1 kg bags |
| Yogurt | Verified 200 g cup; **4 ×** unit price |
| Dish soap | **Palmolive 1 L** (`7290004078270`), not Fairy 900 ml |
| TP | Verified 24-roll pack; 1 pack |
| Tuna | Approved 4×160 g water multipack; 1 pack (not 4 × a single can) |
| Produce | 1 kg × median ₪/kg; item_price already per kg |

No pack-size substitution (900 ml ≠ 1 L; 500 g lentils ≠ 1 kg).

---

## Representative prices

| Source | What was used |
|---|---|
| Verified extract | Chain median columns `shufersal_price` / `rami_levy_price` / `victory_price` |
| Fresh matches | Store median `item_price` on `grocery.latest_product_prices` (₪/kg) |
| Eggs | PriceFull 2026-08-19 majority **carton** `ItemPrice` (S ₪14.24, R ₪14.20, V ₪14.24) |

These are chain-level representative prices, not a named store’s till.

---

## Egg exception

`7290001201589` is audit `needs_review` (`quantity_ratio_ge_5`) because
Shufersal/Rami store Quantity=1 carton and Victory stores Quantity=12
eggs. Names are 12 L farm eggs (לסר). **Basket-only** approval; do not
treat the audit row as valid for the full catalog.

---

## Excluded (not in the ₪ total)

- **Potatoes:** Shufersal `7290000000596` and Rami `7290000000422` are
  ordinary white kg potatoes; Victory has no equivalent (gourmet David
  Moshe is a different product).
- **Chicken breast:** `7290000616827` (עוף עוז שלי), `7290002610700`
  (עוף ירושלים מהדרין), `2206057` (שלם ארוז) are not shown to be the
  same plant, kashrut, or cut.

---

## Files

| Path | Role |
|---|---|
| `data/processed/weekly_basket_comparison.csv` | 39 Tableau rows |
| `docs/weekly_basket_results.md` | This note |
| `docs/weekly_basket_coverage.md` | How the basket was scoped |
