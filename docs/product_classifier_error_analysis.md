# Test error analysis — TF-IDF + Linear SVM

Winner from [ADR 0006](adr/0006-main-category-classifier.md). Metrics from
the untouched Test set (858 products): accuracy **0.871**, Macro F1
**0.862**. This note does **not** change the model.

How to rebuild the mistake list (same split, same winner):

```bash
PYTHONPATH=. .venv/bin/python3 -u scripts/analyze_classifier_test_errors.py
```

Full rows: `data/processed/classifier_test_errors.csv` (gitignored).

---

## How many mistakes?

| | n |
|---|---:|
| Test products | 858 |
| Correct | 747 (87.1%) |
| **Misclassified** | **111 (12.9%)** |

A “mistake” here means: the model’s main category ≠ SuperCompare’s
main category. SuperCompare is silver, not guaranteed truth. Some
“mistakes” are the **model being more reasonable than the label**.

---

## Most common true → predicted pairs

| Rank | True SuperCompare category | Model predicted | n |
|---:|---|---|---:|
| 1 | Snacks & Sweets | Pantry & Cooking | 8 |
| 2 | Bakery | Pantry & Cooking | 7 |
| 3 | Pantry & Cooking | Dairy & Eggs | 7 |
| 4 | Pantry & Cooking | Snacks & Sweets | 7 |
| 5 | Bakery | Snacks & Sweets | 6 |
| 6 | Pantry & Cooking | Bakery | 5 |
| 7 | Personal Care & Hygiene | Household & Cleaning | 5 |
| 8 | Dairy & Eggs | Pantry & Cooking | 4 |
| 9 | Deli & Salads | Pantry & Cooking | 4 |

**Pantry & Cooking is the magnet.** It is the largest class (164 test
rows). Products that sit on a boundary (crackers, baking mix, sauce,
soup almonds) often fall into Pantry, or leak out of Pantry into
Snacks / Bakery / Dairy.

The four weak aisles we cared about (Bakery, Deli, Snacks, Pantry)
account for **the top six pairs**. That is overlap between those
grocery definitions, not a random 12-way scramble.

---

## Focus aisles

### Bakery (test n = 48, 16 errors)

Typical pattern: **baking mixes and crackers**.

- Mixes labeled Bakery are predicted **Pantry** (cake mix, knaidlach
  mix, gluten-free baking mix, pita). A supermarket can honestly put
  “תערובת לעוגה” in either aisle.
- Thin crackers / coated fingers labeled Bakery are predicted
  **Snacks** (קריספיות, דליס שוקולד, קרמוגית בייגלה).

### Deli & Salads (test n = 14, 4 errors)

All four errors go to **Pantry**. Sample is tiny, so F1 is noisy.

Examples: salsa dip, Tabasco, matbucha, **pappardelle pasta**. Pasta
as Deli is a SuperCompare oddity; Pantry is the more natural grocery
class.

### Snacks & Sweets → Pantry (8 errors)

Soup almonds (שקדי מרק), granola, sugar-free candies, “green
shakshuka,” pralines sold by weight. Soup almonds and granola are
classic **snack vs pantry** shelf fights. Two different שקדי מרק
brands made the same mistake, so the model learned “שקדי / מרק” as
pantry language.

### Pantry leaking to Dairy or Snacks (7 + 7)

- **Pantry → Dairy:** vegan “yellow cheese,” plant cream, burrata,
  labneh, granola-with-dairy-brand (פרילי). Several of these **are
  dairy-like**. SuperCompare put them in Pantry; the model followed
  cheese/cream words.
- **Pantry → Snacks:** chocolate, corn kernels, rice cakes, nougat
  spread. Again a real aisle overlap.

---

## Example mistakes (most common pairs)

### Snacks & Sweets → Pantry & Cooking (8)

| item_code | item_name | manufacture_name | Why it may have happened |
|---|---|---|---|
| 7290114606578 | שקדי מרק 400 גר מאסטר שף | *(empty)* | Soup almonds sit next to soup in Pantry |
| 7290003514007 | שקדי מרק 400 גרם | מנה | Same product type, second brand |
| 7290011668587 | גרנולה עשירה 500 גרם | אפקט טבעי | Granola is breakfast pantry *and* a snack |
| 7290011254469 | סוכ.ללא סוכר לימון 80גרם | מיה | Short name (“סוכ.”); pantry brand מיה |
| 7290019233015 | שקשוקה ירוקה | *(empty)* | Sounds like a meal/sauce, not a snack |
| 7290009951424 | פרלינים במשקל | *(empty)* | Almost no text; Pantry is the default |

### Bakery → Pantry & Cooking (7)

| item_code | item_name | manufacture_name | Why it may have happened |
|---|---|---|---|
| 7290000453330 | תערובת לעוגת וניל 500 גר | *(empty)* | Baking mix lives in Pantry dry goods |
| 7290112193582 | תערובת עוגה ללג | אשבל | Same: mix, not a baked loaf |
| 7290015879729 | תערובת לאפיה ללא גלוטן | כללי | Mix + generic manufacturer |
| 43427195119 | תערובת לקניידלך לא שרויה | אימפריאל | Mix |
| 7290000481029 | פיתות ביתי 10×100ג דגנית | דגנית | Bread *can* be Bakery; model chose Pantry |
| 8000380215799 | ברייק3 | *(empty)* | Name has almost no grocery meaning |

### Pantry & Cooking → Dairy & Eggs (7)

| item_code | item_name | manufacture_name | Why it may have happened |
|---|---|---|---|
| 7290019635802 | בוראטה כמהין 24% 125ג גד | MKN | Burrata is cheese; label as Pantry looks wrong |
| 7290019635901 | פילגד סגנ.לאבנה 5% 170ג | EDNK | Labneh is dairy |
| 8000215204370 | תחליף שמנת צמחי אורג200 | *(empty)* | “שמנת” pulls Dairy |
| 7290015599078 | צהובה טבעו.עשבי תיבול200 | *(empty)* | Vegan yellow “cheese” |
| 72964132 | פרילי טבע גרנולה 200 גרם | מחלבת אלון תבור | Dairy manufacturer + yogurt brand |

Here the **label looks more suspicious than the model**.

### Bakery → Snacks & Sweets (6)

| item_code | item_name | manufacture_name | Why it may have happened |
|---|---|---|---|
| 7290119373048 | אצבעות ש.קרמל פ.זמן108ג | שטראוס | Coated sweet fingers |
| 7290012022005 | קריספיות חיטה טבעי 60 גר | דילייט | Cracker / crisp |
| 8423207208260 | ס.דליס שוק.חלב ל.ג6*13גר | ביסצורי | Chocolate-coated; abbreviated name |
| 7290118420057 | קרמוגית קרם בייגלה 200גר | הגביע | Pretzel cream snack |
| 7290119385546 | פריכיות משולשות תירס 30 | פרח | Corn cakes = snacks *or* bakery-adjacent |

### Deli & Salads → Pantry & Cooking (all 4)

| item_code | item_name | manufacture_name | Why it may have happened |
|---|---|---|---|
| 37600297943 | מטבל סלסה חריפה 439 גרם | --- | Dip / sauce → Pantry |
| 11210618503 | רוטב טבסקו חריף אקסטרא | *(empty)* | Hot sauce is pantry |
| 7290119373925 | אחלה סלט מטבוחה חריפה אש | שטראוס | Jarred salad vs pantry condiment |
| 7290119389872 | פפרדלה פסטה 400 גר | דה אנגליס | **Pasta labeled Deli** — likely a SuperCompare error |

---

## Simple patterns

**1. Overlapping category definitions (main issue)**

Bakery vs Pantry vs Snacks share mixes, crackers, pita, granola, and
chocolate-coated biscuits. A linear model on word counts cannot invent
a shelf planogram. Macro F1 will stay soft on these aisles even with a
better model unless we tighten the taxonomy (or only report a merged
“dry goods / bakery-snacks” bucket in analysis).

**2. Abbreviated or empty names (model weakness)**

`ברייק3`, `סוכ.ללא סוכר`, `ס.דליס`, empty manufacturer. TF-IDF has
almost nothing distinctive to work with. Manufacturer placeholders
(`---`, `כללי`) were cleaned to empty, which is correct, but then X is
name-only.

**3. Possible incorrect SuperCompare labels (label noise)**

| item_code | Name | SuperCompare | Model | Likely better class |
|---|---|---|---|---|
| 8700216237239 | פיירי אורגינל קפסולות 41 | Beverages | Household & Cleaning | Household (dish capsules) |
| 7290119389872 | פפרדלה פסטה | Deli & Salads | Pantry & Cooking | Pantry |
| 7290019635802 | בוראטה כמהין | Pantry | Dairy & Eggs | Dairy |
| 7290108352153 | סנובון ג'ל לניקוי אסלות | Personal Care | Household | Household (already on the denylist) |
| 5208049015312 | פאלמאל כחול ארוך חפיסה | Beverages | Personal Care | Tobacco — exclude, not a grocery class |
| 7290000204147 | כריות יפניות דו צדדיות | Dairy & Eggs | Pantry | Cleaning pads, not dairy |

Two of these barcodes were **already** in
`incorrect_category_labels.csv`. The model “failed” the silver label
and matched common sense.

**4. Surprising / worth a second look**

- Frozen tofu (תנובה) predicted Dairy — brand cue overrode “frozen.”
- Frozen chips predicted Snacks — frozen vs snack aisle.
- Baby fruit pouches vs Dairy vs Snacks (גמדים) — brand spans baby and
  dairy.
- `עלית ארק 40%` labeled Snacks, predicted Beverages — the name looks
  like arak (alcohol), not a chocolate bar.

**5. Personal Care ↔ Household (5 + 3)**

Toilet gel, Palmolive dish soap, floor wipes, deodorant spray. Same
story as the known SuperCompare personal-care / cleaning mix-ups. Not
a Bakery problem, but it shows silver labels and the model disagree on
non-food cleaning products.

---

## What this is *not*

It is not “the SVM is broken.” 87% of Test is correct. The remaining
errors concentrate where **humans also disagree on the shelf**, plus a
visible minority of **bad SuperCompare labels**.

A Hebrew transformer might help abbreviated names. It will **not**
resolve “is granola pantry or snacks?” until we decide the rule.

---

## Reporting choices

The published Test metrics (accuracy 0.871, Macro F1 0.862) use
**uncorrected** SuperCompare labels. Grocery analysis that needs
cleaner names uses the **correction overlay** below and drops
`include_in_analysis=false` barcodes. Bakery + Pantry + Snacks can be
grouped or footnoted when the question is “dry sweet/salty goods.”

---

## Approved label overlay (13 recodes + 1 exclusion)

Reviewed in `data/processed/classifier_label_error_review.csv`.
**97 uncertain** rows were left unchanged.

The SuperCompare crawl CSV is **not** edited. Corrections live in a
separate, git-tracked overlay:

`src/product_classification/manual_category_corrections.csv`

| item_code | Original SuperCompare | Corrected | Reason (short) |
|---|---|---|---|
| 8700216237239 | Beverages | Household & Cleaning | Fairy dish capsules |
| 7290000484648 | Snacks & Sweets | Beverages | Arak 40%, winery |
| 7290000204147 | Dairy & Eggs | Household & Cleaning | Japanese scouring pads |
| 7290019635802 | Pantry & Cooking | Dairy & Eggs | Burrata |
| 7290019635901 | Pantry & Cooking | Dairy & Eggs | Labneh |
| 7290017457710 | Personal Care & Hygiene | Household & Cleaning | Fabric softener |
| 7290013269003 | Baby | Household & Cleaning | Baby-scented laundry softener |
| 7290010065332 | Dairy & Eggs | Baby | Fruit puree (baby food) |
| 7290004575373 | Bakery | Frozen | Rio ice cream |
| 7290010193882 | Snacks & Sweets | Frozen | Frozen fries |
| 7290108352153 | Personal Care & Hygiene | Household & Cleaning | Toilet gel (also still on the denylist) |
| 7290119389872 | Deli & Salads | Pantry & Cooking | Dry pasta |
| 7290119375257 | Snacks & Sweets | Dairy & Eggs | Gamadim yogurt pouch |

**Not recoded:** `5208049015312` (Pall Mall cigarettes). SuperCompare
still says Beverages. It stays in `EXCLUDED_ITEM_CODES`, so
`include_in_analysis=false` and it is dropped from grocery analysis.
There is no Tobacco class among the 12.

How a **final modeling category** is chosen:

```text
if item_code in EXCLUDED_ITEM_CODES:
    do not use for grocery analysis
elif item_code in manual_category_corrections.csv:
    y = corrected_category
else:
    y = SuperCompare main_category
```

`effective_main_category()` implements the overlay.
`include_in_analysis()` implements the exclusion.

Nothing was written to PostgreSQL. When labels are later promoted,
`to_classification_rows()` will store the **corrected** category in
`grocery.product_classification.category` and keep
`include_in_analysis=false` for denylist barcodes. The crawl file
`data/processed/supercompare_products.csv` remains the silver source.

The published Test Accuracy 0.871 / Macro F1 0.862 were measured
**before** this overlay.

---

## Appendix — all 111 Test mistakes

Columns: `item_code`, `item_name`, `manufacture_name`, true SuperCompare
category, predicted category.

| item_code | item_name | manufacture_name | true | predicted |
|---|---|---|---|---|
| 7290005576164 | בזיליקום גלאט עלים | קטיף | Pantry & Cooking | Fresh Produce |
| 7290010193905 | נקנקיות עוף 800 גרם | כללי | Meat & Fish | Frozen |
| 37600297943 | מטבל סלסה חריפה 439 גרם | --- | Deli & Salads | Pantry & Cooking |
| 7290101114703 | דובונים קרחון וגומי | | Frozen | Snacks & Sweets |
| 9000100886383 | פאלטה נטורלס4-65זהוב | הנקל סוד | Personal Care & Hygiene | Household & Cleaning |
| 8700216237239 | פיירי אורגינל קפסולות 41 | --- | Beverages | Household & Cleaning |
| 7290114606578 | שקדי מרק 400 גר מאסטר שף | | Snacks & Sweets | Pantry & Cooking |
| 7290110328641 | טופו טבעי 500 גרם תנובה | תנובה | Frozen | Dairy & Eggs |
| 8423207210928 | סלים טופינג אג.לוז | נוטרישן אנד סנטה | Pantry & Cooking | Dairy & Eggs |
| 7290000484648 | עלית ארק 40% 200 מ״ל | יקב הגליל | Snacks & Sweets | Beverages |
| 8000380215799 | ברייק3 | | Bakery | Pantry & Cooking |
| 7290019603801 | גלילנד קרנבל 100 גרם | --- | Snacks & Sweets | Dairy & Eggs |
| 43427263009 | לבבות דקל בצורת ספגטי | כללי | Pantry & Cooking | Snacks & Sweets |
| 7290015599078 | צהובה טבעו.עשבי תיבול | | Pantry & Cooking | Dairy & Eggs |
| 7290122590722 | חמוציות מצופות שקדיה | דין שיווק | Snacks & Sweets | Fresh Produce |
| 7290115203486 | פירורית בטעם ביסלי | אסם | Pantry & Cooking | Bakery |
| 7290119373048 | אצבעות ש.קרמל פ.זמן | שטראוס | Bakery | Snacks & Sweets |
| 7290015652506 | נוזל קוקוס 400 מ״ל | --- | Pantry & Cooking | Household & Cleaning |
| 7290018359358 | פריכוז שלשות | זנלכל | Snacks & Sweets | Pantry & Cooking |
| 8000215204370 | תחליף שמנת צמחי אורג | --- | Pantry & Cooking | Dairy & Eggs |
| 7290012022005 | קריספיות חיטה טבעי | דילייט | Bakery | Snacks & Sweets |
| 4053700292455 | ויט רצועות שעווה צמחית | רקיט בנקיזר | Personal Care & Hygiene | Household & Cleaning |
| 11210618503 | רוטב טבסקו חריף אקסטרא | | Deli & Salads | Pantry & Cooking |
| 8423207208260 | ס.דליס שוק.חלב | ביסצורי | Bakery | Snacks & Sweets |
| 43427195119 | תערובת לקניידלך לא שרויה | אימפריאל | Bakery | Pantry & Cooking |
| 7290017894270 | אבקת אפייה ללא אלומיניום | דגש | Pantry & Cooking | Household & Cleaning |
| 7290011254469 | סוכ.ללא סוכר לימון | מיה | Snacks & Sweets | Pantry & Cooking |
| 72964132 | פרילי טבע גרנולה | מחלבת אלון תבור | Pantry & Cooking | Dairy & Eggs |
| 7290000536743 | קריספי סטיקס תירס | זוגלובק | Snacks & Sweets | Frozen |
| 7290107877619 | במבה מילוי קרם נוגט | אסם | Snacks & Sweets | Bakery |
| 7290019233015 | שקשוקה ירוקה | | Snacks & Sweets | Pantry & Cooking |
| 7290017140766 | זוג פיצות מרגריטה ללא גלוטן | שי של הטבע | Frozen | Pantry & Cooking |
| 7290119760244 | שווארמה על בסיס רכיבים צמחיים | רידיפיין מיט | Meat & Fish | Pantry & Cooking |
| 7290112355102 | גמדים לדרך סלט פירות | שטראוס בריאות | Baby | Dairy & Eggs |
| 7290109580487 | חטיפי תירס מן הצומח | זוגלובק | Snacks & Sweets | Frozen |
| 7290000204147 | כריות יפניות דו צדדיות | פלסטופוליש | Dairy & Eggs | Pantry & Cooking |
| 7290000469638 | מריטו ענק 500 מ״ל | בולטון | Household & Cleaning | Pantry & Cooking |
| 7290019635802 | בוראטה כמהין 24% | MKN | Pantry & Cooking | Dairy & Eggs |
| 7290002253174 | דורות שמיר קצוץ | דורות | Fresh Produce | Pantry & Cooking |
| 7290016505023 | ממתק שוק.קרם נוגט | פנדה | Pantry & Cooking | Snacks & Sweets |
| 7290109923697 | אבקת הפלא מקציפה לאסלה | אורו | Household & Cleaning | Pantry & Cooking |
| 7290017457710 | מרכך כביסה מרוכז ארומתרפי | | Personal Care & Hygiene | Household & Cleaning |
| 7290019205043 | פסטרמה מהמעשנה | מוצרי עוף טוב | Meat & Fish | Frozen |
| 7290119375257 | גמדים אפרסק משמש | שטראוס בריאות | Snacks & Sweets | Dairy & Eggs |
| 7290000072968 | סיני מיניס 500 גרם | סי.פי. צרפת | Pantry & Cooking | Snacks & Sweets |
| 7290002757672 | המבורגר 400 גרם | טיבון ויל | Frozen | Meat & Fish |
| 7290119373925 | אחלה סלט מטבוחה חריפה | שטראוס | Deli & Salads | Pantry & Cooking |
| 7290015324540 | טימין מיכל גדול | תבליני טעם וריח | Fresh Produce | Pantry & Cooking |
| 7290000209371 | גרעיני תירס 3×165ג יכין | קשקמט | Pantry & Cooking | Snacks & Sweets |
| 7290013269003 | מקסימה מרכך בייבי | סנו | Baby | Household & Cleaning |
| 7290010065332 | מחית תפו״ע בננה פרינוק | פרוטה | Dairy & Eggs | Baby |
| 7290003514007 | שקדי מרק 400 גרם | מנה | Snacks & Sweets | Pantry & Cooking |
| 7290112193582 | תערובת עוגה ללג | אשבל | Bakery | Pantry & Cooking |
| 7290101114598 | חמישיה קרם לימון | פלקו | Snacks & Sweets | Frozen |
| 7290100680711 | פירורית זהב 350ג אסם | עינת | Pantry & Cooking | Bakery |
| 7290019603528 | שוקו של מיה 800 גרם | מיה | Beverages | Pantry & Cooking |
| 7290118428480 | אסם ערגליות תפוח קינמון | אסם נסטלה | Pantry & Cooking | Bakery |
| 5200133120926 | גליליות קרם אגוזים | --- | Pantry & Cooking | Bakery |
| 8024985008037 | סמוזי תפוח אורגני | נטורה נובה | Dairy & Eggs | Beverages |
| 7290017068251 | אננס מיובש ומסוכר | מיה | Fresh Produce | Pantry & Cooking |
| 8710908404184 | דאב ספריי 0% אלומיניום | פרמול | Personal Care & Hygiene | Household & Cleaning |
| 7290000481029 | פיתות ביתי דגנית | דגנית | Bakery | Pantry & Cooking |
| 8024985002967 | סמוזי תפוח בננה תרד | נטורה נובה | Dairy & Eggs | Beverages |
| 5608246606076 | פור פט גאטו מזון יבש | --- | Household & Cleaning | Beverages |
| 7290000453866 | נטורינה בשמן קוקוס | בלום פוד | Pantry & Cooking | Meat & Fish |
| 7290119385546 | פריכיות משולשות תירס | פרח | Bakery | Snacks & Sweets |
| 7290015879705 | תערובתאיטלקית לאפיה לל״ג | כללי | Bakery | Snacks & Sweets |
| 7290110572532 | שוקולית כשל״פ | שטראוס קפה | Dairy & Eggs | Snacks & Sweets |
| 7290011732271 | אבקה ט.פרי חמצמץ | | Snacks & Sweets | Household & Cleaning |
| 7290006920836 | פרוסות מעושנת | צי תעשיות | Meat & Fish | Dairy & Eggs |
| 7290019635031 | בוראטה 125 גרם | --- | Dairy & Eggs | Pantry & Cooking |
| 7290018249727 | סוויטאנגו תחליף סוכר | דרך לחיות | Pantry & Cooking | Dairy & Eggs |
| 7290000453330 | תערובת לעוגת וניל | --- | Bakery | Pantry & Cooking |
| 7290019603726 | גלילנד לבבות 150 גרם | מיה | Snacks & Sweets | Pantry & Cooking |
| 7290020449733 | מזרק קרם לבן | --- | Dairy & Eggs | Pantry & Cooking |
| 7290019293415 | מאג.מיני מילקה וניל | --- | Snacks & Sweets | Dairy & Eggs |
| 7290106775053 | מחית נוגט פרווה | | Pantry & Cooking | Snacks & Sweets |
| 7290016087994 | ציפס קלאסי 1.5 ק״ג | פריניר | Frozen | Snacks & Sweets |
| 7290110555795 | קפוצ׳ינו בטעם קלאסי | מוקטה | Beverages | Snacks & Sweets |
| 8004030845046 | סלט אורז עם טונה | --- | Meat & Fish | Bakery |
| 7290015879729 | תערובת לאפיה ללא גלוטן | כללי | Bakery | Pantry & Cooking |
| 7290118420057 | קרמוגית קרם בייגלה | הגביע | Bakery | Snacks & Sweets |
| 8423207208703 | סלים דליס שוקולד מריר | נוטרישן | Pantry & Cooking | Snacks & Sweets |
| 7290108070316 | בלונים איכותיים 50 יחי | כללי | Household & Cleaning | Snacks & Sweets |
| 7290111355295 | יוגטה גלי בטעם פירות | סרגיאטו | Dairy & Eggs | Snacks & Sweets |
| 7290015599054 | צהובה טבעונית צדר | | Frozen | Dairy & Eggs |
| 7290000692227 | פלמוליב לשטיפת כלים | קולגייט-פלמוליב | Household & Cleaning | Personal Care & Hygiene |
| 7290011668587 | גרנולה עשירה 500 גרם | אפקט טבעי | Snacks & Sweets | Pantry & Cooking |
| 7290004575373 | מאגדת מצופים ריאו | ריאוגלידות | Bakery | Frozen |
| 7290002753995 | סט דרזה צבעוני קישוט | וורנר | Snacks & Sweets | Fresh Produce |
| 7290010193882 | ציפס קפוא 1.5 ק״ג | גלאט עוף | Snacks & Sweets | Meat & Fish |
| 7290110560317 | פריכיות משולש מלח ים | פרח | Pantry & Cooking | Snacks & Sweets |
| 7290108352153 | סנובון ג׳ל לניקוי אסלות | סנו | Personal Care & Hygiene | Household & Cleaning |
| 7290003220519 | קרם קוקוס גולד | תאי קוקונט | Dairy & Eggs | Pantry & Cooking |
| 7290019635901 | פילגד לאבנה 5% | EDNK | Pantry & Cooking | Dairy & Eggs |
| 7290101114109 | מסקרפונה עוג+שוק.חלב | --- | Dairy & Eggs | Bakery |
| 7290013472892 | הבולגריה בקוביות | קוליוס | Dairy & Eggs | Snacks & Sweets |
| 5208049015312 | פאלמאל כחול ארוך חפיסה | BAT | Beverages | Personal Care & Hygiene |
| 7290011622428 | כתמטמינים חטיף בריאות | אשבל | Baby | Snacks & Sweets |
| 7290000415666 | קובה חמוסטה | נ.ר.ג יסמין | Bakery | Deli & Salads |
| 7290108356885 | סבון אסלה בניחוח יערות | | Household & Cleaning | Personal Care & Hygiene |
| 4009300527909 | חליטת גינגר כורכום | טיקנה | Pantry & Cooking | Beverages |
| 7290012022067 | קריספיות קידס | דילייט | Bakery | Pantry & Cooking |
| 8024985003988 | סמוזי תפוח בננה אורג | נטורה נובה | Baby | Beverages |
| 7290019233107 | זית ירוק עם עשבי תיבול | | Pantry & Cooking | Fresh Produce |
| 7290019014997 | מ.לחות לרצפה TNXפרש | --- | Household & Cleaning | Personal Care & Hygiene |
| 8410376040135 | בסקוויט מריה | גאלטס | Bakery | Frozen |
| 7290018400470 | כרישה חתוכה ומוקפאת | --- | Frozen | Meat & Fish |
| 7290009951424 | פרלינים במשקל | | Snacks & Sweets | Pantry & Cooking |
| 7290008867511 | מקלונאש בצל | געשמאק | Pantry & Cooking | Bakery |
| 7290119389872 | פפרדלה פסטה 400 גר | דה אנגליס | Deli & Salads | Pantry & Cooking |
