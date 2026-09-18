# Phase 5 — TAQ/TAQM Data Inventory & Cleaning
---

# 1. Phase Objective

The objective of Phase 5 was to establish a **canonical, structurally valid, normalized TAQ/TAQM dataset** suitable for downstream microstructure-variable construction.

Specifically, Phase 5 was designed to:

1. Inventory the available TAQ/TAQM data.
2. Establish the raw schema and field meanings.
3. Validate dates, symbols, quotes, trades, activity, execution metrics, and market statistics.
4. Identify structural and semantic anomalies.
5. Distinguish genuine data-quality failures from economically valid observations.
6. Correct date interpretation and canonical date selection where required.
7. Preserve economically meaningful negative execution metrics.
8. Investigate bid/ask ordering violations without automatically deleting them.
9. Validate trading activity and order-flow relationships.
10. Validate market-statistic and information-metric fields.
11. Produce a canonical cleaned TAQ file.
12. Complete integrated validation without unresolved **critical structural failures**.

---

# 2. Phase 5 Scope

Phase 5 covered the following major domains:

- TAQ/TAQM file inventory
- Schema validation
- Data-type normalization
- Date normalization
- Symbol normalization
- Time-field normalization
- Missingness diagnostics
- Duplicate diagnostics
- Cross-field validation
- Quote validation
- Quote semantic investigation
- Quote economic validation
- Execution-metric validation
- Trading-activity validation
- Order-flow validation
- Market-statistic validation
- Temporal validation
- Integrated validation
- Final corrected integrated validation

---

# 3. Phase 5 Checklist

## Step 1 — TAQ/TAQM Data Inventory

- [x] Locate raw TAQ file.
- [x] Confirm raw file readability.
- [x] Record row count.
- [x] Record column count.
- [x] Record field names.
- [x] Identify date fields.
- [x] Identify time fields.
- [x] Identify quote fields.
- [x] Identify trade fields.
- [x] Identify execution metrics.
- [x] Identify activity/order-flow fields.
- [x] Identify market-statistic fields.

---

## Step 2 — TAQ Structural Diagnostics

- [x] Validate schema.
- [x] Validate row counts.
- [x] Inspect missingness.
- [x] Inspect numeric ranges.
- [x] Inspect negative values.
- [x] Inspect cross-field relationships.
- [x] Inspect key fields.
- [x] Generate diagnostic outputs.
- [x] Preserve all observations during diagnostic processing.

---

## Step 3 — Duplicate Diagnostics

Duplicate diagnostics were performed using multiple candidate keys.

Candidate keys included:

- `date | symbol`
- `date | symbol | OTime`
- `date | symbol | DTime`
- `date | symbol | LQTime`
- `date | symbol | LTTime`
- `date | symbol | TTime_1pm`
- `date | symbol | TTime_4pm`
- quote-time/price combinations
- full-row equality

The initial duplicate investigation appeared to identify substantial duplication.

However, subsequent investigation established that the apparent duplication was caused by **incorrect interpretation of the raw date field**, rather than actual duplicate observations.

After using the confirmed DD/MM/YYYY interpretation:

- Raw duplicate groups: `0`
- Raw duplicate rows: `0`
- Clean canonical date-symbol duplicate groups: `0`
- Clean canonical date-symbol duplicate rows: `0`

Therefore:

> The apparent duplicate problem was a date-parsing problem rather than a duplicate-observation problem.

No duplicate rows were removed.

---

# 4. Date Interpretation

The raw TAQ date field uses a confirmed **DD/MM/YYYY** interpretation.

Example:

```text
06/04/1993
```

must be interpreted as:

```text
1993-04-06
```

rather than:

```text
1993-06-04
```

The corrected canonical date field is:

```text
date_normalized
```

The canonical date range is:

```text
1993-01-04
through
2012-12-31
```

The canonical date field contains:

- Rows: `122,441`
- Missing dates: `0`
- Unique dates: `5,036`

The raw `date` field is **not** used as the canonical structural date because generic parsing produced substantial missingness and incorrect interpretation.

---

# 5. Canonical Date Validation

The final investigation confirmed:

```text
Canonical date column: date_normalized
Canonical date missing: 0
Canonical date unique: 5,036
Canonical first date: 1993-01-04
Canonical last date: 2012-12-31
```

Raw-to-clean alignment:

```text
Date matches:       122,441 / 122,441
Symbol matches:     122,441 / 122,441
Date+symbol matches:122,441 / 122,441
```

Date distribution comparison:

```text
Dates with distribution mismatch: 0
Maximum absolute count difference: 0
```

Therefore the corrected canonical date transformation preserves the raw observations exactly.

---

# 6. Canonical TAQ File

The canonical cleaned file is:

```text
data/processed/taq/taq_cleaned.csv
```

Final characteristics:

```text
Rows:       122,441
Columns:    127
Symbols:    29
Dates:      5,036
```

The additional 25 columns are normalization/derived diagnostic fields.

These include:

- `date_normalized`
- `date_iso`
- normalized time fields
- time fields represented in seconds

The raw analytical fields were preserved.

---

# 7. Quote Validation

Quote fields were validated for:

- bid/ask ordering
- midpoint consistency
- missingness
- cross-field relationships
- quote-set behavior

Quote sets include:

- 1pm
- c1
- 4pm
- last

Bid > ask observations were detected.

Final semantic investigation found:

```text
Total bid > ask observations: 23,564
```

However, these observations were **not automatically classified as data errors**.

Quote-set results included:

```text
1pm  | violations ≈ 2,198
c1   | violations ≈ 5,049
4pm  | violations ≈ 5,350
last | violations ≈ 9,119
```

The exact diagnostic outputs should be treated as the authoritative record.

Midpoint consistency was preserved.

No quote values were corrected.

No quote observations were removed.

---

# 8. Quote Economic Validation

Quote economic validation confirmed that:

- bid/ask ordering violations exist;
- negative-spread observations require source-semantic interpretation;
- quote fields remain internally analyzable;
- no unsupported automatic quote correction should be applied.

No quote values were modified.

No observations were removed.

The unresolved quote issue is therefore classified as:

```text
REVIEW — source/economic semantic interpretation
```

rather than:

```text
CRITICAL — structural data failure
```

---

# 9. Execution-Metric Validation

The following execution metrics were evaluated:

- `ESpreadDollar_Avg1`
- `ESpreadPct_Avg1`
- `RSpreadDollar_Avg1`
- `RSpreadPct_Avg1`
- `PriceImpactDollar_Avg1`
- `PriceImpactPct_Avg1`
- `ESpreadDollar_VW1`
- `ESpreadDollar_SW1`
- `ESpreadPct_VW1`
- `ESpreadPct_SW1`
- `RSpreadDollar_SW1`
- `RSpreadDollar_VW1`
- `RSpreadPct_SW1`
- `RSpreadPct_VW1`
- `PriceImpactDollar_VW1`
- `PriceImpactDollar_SW1`
- `PriceImpactPct_VW1`
- `PriceImpactPct_SW1`

Negative realized-spread and price-impact values were observed.

These were retained because signed execution metrics can legitimately be negative depending on the relationship between:

- transaction price,
- quote midpoint,
- execution direction,
- benchmark price,
- subsequent benchmark price.

Therefore:

> Negative execution metrics are not automatically treated as data errors.

No execution metrics were corrected.

No observations were removed.

---

# 10. Trading Activity and Order-Flow Validation

The following domains were investigated:

- trade counts
- market-firm counts
- trade volume
- dollar values
- buy/sell counts
- buy/sell volume
- buy/sell dollar values
- ISO activity
- odd-lot activity
- mixed-lot activity
- order-flow measures

No negative activity values were found.

Some consistency violations were detected.

The important distinction is that these were treated as **semantic/source-definition issues**, not automatic cleaning errors.

No activity values were modified.

No observations were removed.

---

# 11. Market-Statistics Validation

Market-statistic fields included:

- `Ret_pre_t`
- `Ret_mkt_t`
- `Ret_post_t`
- `IVol_t_m`
- `IVol_q_m`
- `VarianceRatio1`
- `VarianceRatio2`
- `HIndex1`
- `NumExtremeOfr_m`
- `NumExtremeBid_m`
- `NObsUsed1`
- `NObsUsed2`
- `NumTimeUnitsWithTrade1`
- `NumTimeUnitsWithTrade2`

Negative returns were retained because negative returns are economically valid.

No negative volatility values were observed.

No invalid information metrics were automatically corrected.

No observations were removed.

---

# 12. Initial Integrated Validation Failure

The first integrated validation reported:

```text
Critical failures: 74,172
Review items:       536,537
```

This appeared to indicate a serious structural failure.

However, investigation showed that the integrated validator was incorrectly using the raw `date` column as the structural date.

Because the raw date had been generically parsed, many dates became missing.

This produced false structural failures and apparent duplicate observations.

---

# 13. Integrated Validation Failure Investigation

The investigation established:

```text
Raw date-symbol duplicates:       0
Clean canonical date-symbol duplicates: 0
Date alignment:                   122,441 / 122,441
Symbol alignment:                 122,441 / 122,441
Date+symbol alignment:            122,441 / 122,441
Date distribution mismatches:     0
```

Therefore:

> The 74,172 critical failures were caused by validator configuration/date-column selection rather than actual canonical TAQ structural corruption.

The canonical structural date is:

```text
date_normalized
```

---

# 14. Corrected Final Integrated Validation

The corrected integrated validator explicitly selected:

```text
date_normalized
```

as the canonical structural date.

Final results:

```text
Input rows:                    122,441
Input columns:                 127
Missing canonical dates:       0
Missing symbols:               0
Date-symbol duplicate extras:  0
Critical failures:             0
Review items:                  345,840
Observations removed:          0
Values modified:               0
Values imputed:                0
Automatic corrections:         0
```

Final status:

```text
PASS
```

Interpretation:

> The canonical TAQ dataset contains no unresolved critical structural failures.

The remaining review items are semantic/economic diagnostics and are not automatically interpreted as invalid data.

---

# 15. Important Data-Handling Principles Established in Phase 5

The following principles must carry forward into Phase 6.

## 15.1 Do not use raw `date` as the canonical date

Use:

```text
date_normalized
```

for all downstream temporal grouping.

---

## 15.2 Do not remove bid > ask observations automatically

Bid > ask observations require semantic interpretation.

Do not silently swap:

```text
bid
ask
```

and do not automatically discard observations.

---

## 15.3 Do not remove negative realized spreads

Negative realized spreads may be economically meaningful.

---

## 15.4 Do not remove negative price impacts

Negative price impact may be economically meaningful depending on trade direction and benchmark construction.

---

## 15.5 Do not infer errors solely from accounting identities

TAQ/TAQM fields can represent different measurement windows, aggregation rules, classifications, or source definitions.

A failed identity is therefore not automatically evidence of corruption.

---

## 15.6 Preserve the canonical source fields

Phase 6 should construct research variables without overwriting the underlying source variables.

Derived variables should be explicitly named and documented.

---

# 16. Phase 5 Outputs

Major outputs include:

```text
data/processed/taq/taq_cleaned.csv
data/processed/taq/taq_cleaning_audit.csv
data/processed/taq/taq_cleaning_summary.csv
data/processed/taq/taq_post_clean_validation.csv
```

Duplicate diagnostics:

```text
data/processed/taq/taq_duplicate_diagnostic.csv
data/processed/taq/taq_duplicate_examples.csv
```

Quote diagnostics:

```text
data/processed/taq/quote_semantic_investigation/
```

Execution diagnostics:

```text
data/processed/taq/execution_metric_validation/
```

Activity/order-flow diagnostics:

```text
data/processed/taq/activity_orderflow_validation/
```

Market-statistics diagnostics:

```text
data/processed/taq/market_statistics_validation/
```

Final validation:

```text
data/processed/taq/final_integrated_validation_corrected/
```

Final validation investigation:

```text
data/processed/taq/final_validation_investigation/
```

---

# 17. Phase 5 Final Findings

## Structural

**PASS**

- Canonical dates are valid.
- Canonical dates are complete.
- Symbols are complete.
- Date-symbol duplicates are absent.
- Raw and canonical observations align exactly.
- No observations were removed.

## Temporal

**PASS**

- Canonical dates span 1993-01-04 through 2012-12-31.
- Date distribution matches the corrected raw interpretation.

## Quotes

**PASS with REVIEW**

- Quote fields are preserved.
- Bid > ask observations exist.
- Midpoint relationships are internally diagnosable.
- No automatic quote correction was applied.

## Execution Metrics

**PASS with REVIEW**

- Negative realized spreads exist.
- Negative price impacts exist.
- These were retained as economically meaningful signed metrics.

## Activity / Order Flow

**PASS with REVIEW**

- No negative activity values.
- Some consistency relationships require source-semantic interpretation.

## Market Statistics

**PASS with REVIEW**

- Negative returns are retained.
- No negative volatility values.
- Observation-count relationships require semantic interpretation.

## Integrated Validation

**PASS**

- Critical structural failures after corrected canonical-date validation: `0`.

---

# 18. Phase 5 Closure Criteria

Phase 5 is considered complete because:

- [x] Raw TAQ data is inventoried.
- [x] Schema is documented.
- [x] Canonical date interpretation is established.
- [x] Canonical date field is complete.
- [x] Canonical symbol field is complete.
- [x] Date-symbol duplicates are resolved as a validator/date-parsing issue.
- [x] No unexplained structural duplicates remain.
- [x] Quote diagnostics are complete.
- [x] Quote semantic investigation is complete.
- [x] Quote economic validation is complete.
- [x] Execution-metric validation is complete.
- [x] Activity/order-flow validation is complete.
- [x] Market-statistic validation is complete.
- [x] Final integrated validation has been corrected.
- [x] Critical structural failures = `0`.
- [x] Canonical TAQ file established.
- [x] No unjustified observations were removed.
- [x] No unsupported economic corrections were applied.
