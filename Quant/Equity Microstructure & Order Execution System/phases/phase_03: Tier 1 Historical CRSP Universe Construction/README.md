# Phase 3 — Tier 1 Historical CRSP Universe Construction

## 1. Phase Objective

The objective of Phase 3 was to construct, validate, and document the **Tier 1 historical CRSP security universe** and transform the validated CRSP daily data into a research-ready, execution-oriented security-day dataset.

The phase establishes the first fully processed research universe for the Equity Microstructure & Order Execution System.

The resulting Tier 1 dataset provides:

* a historically valid security universe,
* CRSP PERMNO/PERMCO identifiers,
* validated daily market observations,
* historical security-date coverage,
* execution-relevant prices, volume, and quotes,
* liquidity and spread measures,
* look-ahead-safe pre-trade features,
* security-level quality diagnostics,
* execution eligibility flags,
* validation outputs for reproducibility.

Phase 3 does **not** attempt to construct the broader Tier 2 historical universe. That work begins in Phase 4.

---

# 2. Research Scope

## Research Window

| Parameter                    | Value      |
| ---------------------------- | ---------- |
| Research start               | 1993-01-01 |
| First available trading date | 1993-01-04 |
| Research end                 | 2018-12-31 |

The effective daily research sample therefore begins on **1993-01-04**, the first available CRSP trading observation within the specified research window.

## Final Tier 1 Universe

| Measure                        | Result |
| ------------------------------ | -----: |
| Historical universe securities |     36 |
| Eligible Tier 1 securities     |     33 |
| Excluded securities            |      3 |
| Unique PERMCOs retained        |     32 |
| Unique tickers retained        |     31 |

The three excluded securities were identified as FUND/ETF securities and removed from the Tier 1 equity execution universe.

---

# 3. Phase 3 Workflow

The phase proceeded through the following major stages.

### 3.1 Initial Tier 1 Universe Construction

CRSP Names was used to establish the initial security universe.

Results:

* CRSP Names rows: 238
* Unique CRSP Names PERMNOs: 38
* Initial Tier 1 universe: 38 securities
* Unique PERMCOs: 37
* Unique tickers: 36

The initial universe was validated for:

* PERMNO uniqueness,
* PERMNO completeness,
* PERMCO completeness,
* agreement with the source CRSP Names universe.

---

### 3.2 Historical Universe Construction

The initial universe was reconciled against:

* CRSP Names,
* CRSP daily data,
* reconciliation outputs,
* historical security dates.

Results:

* Names PERMNOs: 38
* Daily PERMNOs: 41
* Reconciled PERMNOs: 43
* Initial historical universe: 36 securities
* NAMES_ONLY exclusions: 2
* DAILY_ONLY exclusions: 5

Historical date overlap was explicitly evaluated.

No selected historical securities had:

* daily observations before their security beginning date,
* daily observations after their security ending date.

---

### 3.3 Historical Universe Validation

The historical universe was subjected to structural and temporal validation.

Validation results:

* duplicate PERMNOs: 0
* missing PERMNOs: 0
* missing daily history: 0
* invalid historical overlaps: 0
* excluded securities contaminating universe: 0
* missing reconciliation records: 0
* missing CRSP Names records: 0

All required validation checks passed.

---

### 3.4 Tier 1 Eligibility Filtering

The historical universe was filtered to construct the execution-oriented Tier 1 universe.

The primary explicit exclusion criterion at this stage was FUND/ETF contamination.

Results:

* historical securities: 36
* eligible securities: 33
* excluded securities: 3
* excluded FUND/ETF: 3
* excluded for missing daily history: 0
* excluded for research-window incompatibility: 0

Final eligible universe:

**33 securities**

The resulting universe contains:

* 33 unique PERMNOs
* 32 unique PERMCOs
* 31 unique tickers

---

# 4. Daily Dataset Construction

The validated CRSP daily data was filtered to the 33 eligible Tier 1 PERMNOs.

## Final Daily Dataset

| Measure                    |     Result |
| -------------------------- | ---------: |
| Daily rows                 |    161,883 |
| PERMNOs                    |         33 |
| First date                 | 1993-01-04 |
| Last date                  | 2018-12-31 |
| Duplicate PERMNO-date rows |          0 |
| Missing eligible PERMNOs   |          0 |
| Unexpected PERMNOs         |          0 |

The final dataset contains exactly the eligible Tier 1 securities and no unexpected securities.

---

# 5. Daily Dataset Integrity

The daily dataset was subjected to structural, price, volume, return, quote, and historical coverage checks.

## Structural Checks

| Check                                | Result |
| ------------------------------------ | -----: |
| Duplicate PERMNO-date observations   |      0 |
| Missing PERMNO                       |      0 |
| Unexpected PERMNOs                   |      0 |
| Observations outside research window |      0 |
| PERMNO/PERMCO inconsistencies        |      0 |

All structural checks passed.

---

## Price Integrity

The audit found:

| Field    | Missing | Zero | Negative |
| -------- | ------: | ---: | -------: |
| DlyPrc   |       1 |    0 |        0 |
| DlyOpen  |     110 |    0 |        0 |
| DlyHigh  |      60 |    0 |        0 |
| DlyLow   |      60 |    0 |        0 |
| DlyClose |      60 |    0 |        0 |

OHLC structural checks found:

* High below Low: 0
* Open outside High/Low: 0
* Close outside High/Low: 0

No invalid negative prices were detected.

---

## Volume Integrity

| Measure                      | Result |
| ---------------------------- | -----: |
| Missing volume observations  |      1 |
| Zero-volume observations     |     57 |
| Negative-volume observations |      0 |

Zero volume was retained as an observed condition rather than automatically deleting the associated security-day observations.

---

## Return Integrity

| Measure                          | Result |
| -------------------------------- | -----: |
| Missing DlyRet                   |     10 |
| Missing DlyRetX                  |     10 |
| Returns > +100%                  |      0 |
| Returns < -100%                  |      0 |
| Observations with |DlyRet| > 50% |      9 |
| Price changes exceeding 50%      |     36 |

Large returns and price jumps were treated as **diagnostic observations**, not automatic exclusions.

This preserves the underlying CRSP observations for subsequent research-specific treatment.

---

# 6. Quote Integrity

The final Tier 1 daily dataset contains:

* 161,124 observations with both bid and ask,
* 759 observations with missing bid/ask pairs,
* 3,060 crossed bid/ask observations.

## Crossed Quotes

A crossed quote occurs where:

`bid > ask`

The dataset contains:

**3,060 crossed quote observations**

These observations occur across:

**30 of the 33 securities**

The crossed quotes were **not removed**.

The project decision is to:

1. retain the original CRSP observations,
2. flag crossed quotes explicitly,
3. prevent crossed quotes from being treated as normal executable two-sided quotes,
4. allow downstream execution analyses to apply an explicit quote-quality filter.

This preserves data provenance while preventing quote-quality problems from silently contaminating execution calculations.

---

# 7. Security-Level Quality Assessment

The security-level quality summary contains exactly one row per eligible PERMNO.

Results:

| Measure                              | Result |
| ------------------------------------ | -----: |
| Eligible securities                  |     33 |
| Quality-summary securities           |     33 |
| Missing securities                   |      0 |
| Unexpected securities                |      0 |
| Securities with crossed quotes       |     30 |
| Securities with full price coverage  |     32 |
| Securities with full volume coverage |     32 |
| Securities with full quote coverage  |     14 |
| Securities with full return coverage |     23 |

The quality summary therefore documents substantial variation in data completeness across securities.

This variation is retained rather than using an overly aggressive complete-case filter at the universe-construction stage.

---

# 8. Security-Day Research Panel

The validated daily dataset was transformed into a security-day research panel.

The panel contains:

* one row per PERMNO-date,
* lagged market variables,
* daily price-based measures,
* quote measures,
* quote-quality flags,
* liquidity measures,
* market capitalization,
* observation-availability flags.

Results:

* 161,883 security-day observations
* 33 PERMNOs
* no duplicate PERMNO-date observations

---

# 9. Execution Dataset

The security-day panel was transformed into the execution-oriented dataset.

The execution dataset contains variables including:

* price,
* volume,
* bid,
* ask,
* return,
* midquote,
* quoted spread,
* relative quoted spread,
* quoted spread in basis points,
* dollar volume,
* log dollar volume,
* turnover,
* market-cap validity,
* quote availability,
* quote usability,
* crossed-quote flags,
* return-validity flags,
* large-return flags,
* large-price-jump flags,
* execution-readiness flags.

## Execution Dataset Results

| Measure                        |  Result |
| ------------------------------ | ------: |
| Securities                     |      33 |
| Daily observations             | 161,883 |
| Two-sided quote rows           | 161,124 |
| Normal quote rows              | 158,064 |
| Crossed quote rows             |   3,060 |
| Execution-ready rows           | 158,064 |
| Positive-volume execution rows | 158,007 |

The distinction between the full dataset and execution-ready observations is intentional.

The full dataset remains the canonical historical research dataset, while execution flags identify observations appropriate for particular downstream analyses.

---

# 10. Look-Ahead-Safe Feature Engineering

The execution dataset was extended with pre-trade features designed to avoid look-ahead bias.

The feature engineering stage included:

* lagged price variables,
* lagged midquote,
* lagged dollar volume,
* lagged spread,
* rolling average daily volume,
* rolling spread,
* rolling volatility,
* Amihud illiquidity,
* turnover features,
* price-impact measures,
* execution-quality flags.

The following look-ahead-safety checks passed:

* `lag_price_exists`
* `lag_midquote_exists`
* `lag_dollar_volume_exists`
* `lag_spread_bps_exists`
* `adv_20d_exists`
* `realized_vol_20d_exists`

This establishes the foundation for using historical information available **before the execution observation** when constructing subsequent execution models.

---

# 11. Final Feature Dataset

The final Tier 1 execution-feature dataset contains:

| Measure                |         Result |
| ---------------------- | -------------: |
| Securities             |             33 |
| Daily observations     |        161,883 |
| Execution-ready rows   |        158,064 |
| Pre-trade feature rows |        161,049 |
| Mean 20-day ADV        | 840,643,460.22 |
| Mean 20-day spread     |      41.41 bps |
| Mean 20-day volatility |       0.020555 |

The first observations of each security naturally have incomplete lagged/rolling features because sufficient historical observations are not yet available.

These observations are retained rather than artificially backfilled.

---

# 12. Final Phase 3 Output Files

The following processed files were generated during Phase 3.

## Universe Construction

```text
crsp_tier1_initial_universe.csv
crsp_tier1_historical_universe.csv
crsp_tier1_universe_summary.csv
crsp_tier1_universe_exclusions.csv
crsp_tier1_eligible_universe.csv
crsp_tier1_eligible_universe_exclusions.csv
crsp_tier1_eligible_universe_summary.csv
```

## Daily Dataset

```text
crsp_tier1_daily.csv
crsp_tier1_daily_summary.csv
crsp_tier1_daily_validation.csv
crsp_tier1_daily_quality_summary.csv
crsp_tier1_daily_integrity_security_summary.csv
crsp_tier1_daily_integrity_summary.csv
```

## Research Dataset

```text
crsp_tier1_research_dataset.csv
crsp_tier1_research_security_summary.csv
crsp_tier1_research_dataset_validation.csv
```

## Security-Day Panel

```text
crsp_tier1_panel.csv
crsp_tier1_panel_summary.csv
crsp_tier1_panel_validation.csv
```

## Execution Dataset

```text
crsp_tier1_execution_dataset.csv
crsp_tier1_execution_dataset_summary.csv
crsp_tier1_execution_dataset_validation.csv
```

## Execution Features

```text
crsp_tier1_execution_features.csv
crsp_tier1_execution_features_summary.csv
crsp_tier1_execution_features_validation.csv
```

---

# 13. Major Findings

## 13.1 Tier 1 Universe Size

The final Tier 1 historical universe contains **33 securities**.

The reduction from the initial historical universe of 36 securities was entirely attributable to the explicit FUND/ETF exclusion.

---

## 13.2 ETF/FUND Contamination

Three securities were identified as FUND/ETF securities:

* SPY — PERMNO 84398
* QQQ — PERMNO 86755
* IWM — PERMNO 88222

All three were removed from the eligible Tier 1 equity universe.

No FUND/ETF observations remain in the final Tier 1 daily dataset.

---

## 13.3 Historical Coverage

All 33 eligible securities have daily history within the research window.

There are:

* no missing eligible PERMNOs,
* no unexpected PERMNOs,
* no duplicate security-day observations,
* no observations outside the research window.

---

## 13.4 Quote Quality

Crossed quotes are present in the underlying CRSP data.

The project does **not** treat this as evidence that the securities themselves should be excluded.

Instead:

* the underlying observations remain available,
* crossed quotes are explicitly flagged,
* execution-ready definitions exclude crossed quotes where appropriate.

This preserves both data completeness and execution-analysis discipline.

---

## 13.5 Extreme Returns and Price Movements

A small number of unusually large returns and price movements were identified.

These observations were retained because extreme movements can represent genuine market events, corporate actions, low-priced securities, or other legitimate CRSP observations.

They are therefore flagged for downstream analysis rather than deleted during universe construction.

---

## 13.6 Missingness

Core price and volume fields exhibit extremely low overall missingness.

Quote coverage is less complete:

* 161,124 observations have both bid and ask,
* 14 of 33 securities have full quote coverage.

This means quote-dependent analyses should use the explicit quote-availability and quote-usability flags rather than assuming universal quote coverage.

---

# 14. Methodological Decisions Locked in Phase 3

The following decisions are considered part of the Phase 3 data specification.

### Decision 1 — PERMNO as the security identifier

PERMNO is the primary security-level identifier.

PERMCO is retained for issuer/company-level aggregation.

Ticker and CUSIP are retained as descriptive/reference identifiers rather than primary longitudinal identifiers.

---

### Decision 2 — Preserve underlying CRSP observations

The project does not delete observations merely because they contain:

* crossed quotes,
* large returns,
* large price jumps,
* zero volume.

Instead, such observations receive explicit diagnostic or eligibility flags.

---

### Decision 3 — FUND/ETF exclusion

FUND/ETF securities are excluded from the Tier 1 equity execution universe.

---

### Decision 4 — Separate historical universe from execution eligibility

The canonical historical dataset contains the full validated Tier 1 universe.

Execution eligibility is represented through flags.

This prevents the research dataset from being irreversibly reduced by assumptions that may differ across future execution experiments.

---

### Decision 5 — Look-ahead-safe feature construction

Rolling and lagged execution features must use only information available prior to the relevant observation.

This requirement was explicitly validated for the initial feature set.

---

### Decision 6 — No automatic outlier deletion

Extreme returns and price changes are retained and flagged.

Any future exclusion based on return magnitude, price level, liquidity, or other criteria must be explicitly defined by the relevant research experiment.

---

# 15. Validation Status

## Universe Validation

* [x] PERMNO uniqueness
* [x] PERMNO completeness
* [x] PERMCO completeness
* [x] Historical date overlap
* [x] Daily history coverage
* [x] CRSP Names reconciliation
* [x] Exclusion contamination check
* [x] FUND/ETF identification

## Daily Dataset Validation

* [x] Required columns
* [x] Valid dates
* [x] Research-window coverage
* [x] PERMNO coverage
* [x] PERMNO-date uniqueness
* [x] PERMCO consistency
* [x] Price integrity
* [x] Volume integrity
* [x] OHLC consistency
* [x] Return integrity
* [x] Quote diagnostics
* [x] Security-level coverage

## Research Panel Validation

* [x] Security-day uniqueness
* [x] PERMNO coverage
* [x] Date coverage
* [x] Security metadata
* [x] Security-level summary completeness
* [x] Research-window integrity

## Execution Dataset Validation

* [x] Execution variables
* [x] Price/volume flags
* [x] Market-cap flags
* [x] Quote flags
* [x] Execution eligibility flags
* [x] Security coverage
* [x] Research-window integrity

## Feature Dataset Validation

* [x] Lagged variables
* [x] Rolling liquidity features
* [x] Rolling spread features
* [x] Rolling volatility features
* [x] Amihud features
* [x] Turnover features
* [x] Price-impact features
* [x] Execution flags
* [x] Pre-trade feature flags
* [x] Security-level feature coverage

---

# 16. Known Diagnostics and Limitations

Phase 3 passed its core validation checks, but several observations should remain documented.

### Crossed quotes

3,060 observations contain bid > ask.

These are retained but should not be interpreted as normal executable two-sided quotes.

### Missing observations

A small number of observations contain missing price, volume, return, or quote fields.

These are handled through validity flags rather than global deletion.

### Zero volume

57 zero-volume observations remain.

These may be relevant for understanding trading inactivity and should not automatically be interpreted as erroneous records.

### Extreme returns

9 observations have absolute daily returns greater than 50%.

These remain available for event-level investigation.

### Large price jumps

36 observations exhibit price changes exceeding 50%.

These remain flagged rather than deleted.

### Rolling-feature warm-up

Pre-trade rolling variables are naturally unavailable at the beginning of individual security histories.

These observations remain in the dataset but should not be treated as having valid rolling estimates.

---

# 17. Canonical Dataset Hierarchy

The Phase 3 outputs should be understood hierarchically:

```text
CRSP Raw / Clean Data
        │
        ▼
Historical Tier 1 Universe
        │
        ▼
Eligible Tier 1 Universe
        │
        ▼
Tier 1 Daily Dataset
        │
        ▼
Tier 1 Research Dataset
        │
        ▼
Security-Day Panel
        │
        ▼
Execution Dataset
        │
        ▼
Execution Feature Dataset
```

The **execution feature dataset** is the most analysis-ready Phase 3 output, while the earlier datasets remain important provenance and validation layers.

---

# 18. Phase 3 Completion Criteria

Phase 3 is considered complete because:

* [x] Tier 1 historical universe constructed
* [x] Historical universe validated
* [x] FUND/ETF contamination removed
* [x] Eligible Tier 1 universe constructed
* [x] Daily data filtered to eligible securities
* [x] Daily dataset validated
* [x] Security-level quality documented
* [x] Daily integrity audited
* [x] Research dataset assembled
* [x] Security-day panel constructed
* [x] Execution dataset constructed
* [x] Execution features constructed
* [x] Look-ahead-safe features validated
* [x] Security-level summaries generated
* [x] Validation outputs generated
* [x] Diagnostic observations retained and documented

---

# 19. Phase 3 Final State

The completed Tier 1 research infrastructure consists of:

**33 securities**

**161,883 daily security observations**

**158,064 execution-ready observations**

**158,007 positive-volume execution observations**

**161,049 observations with pre-trade feature availability**

The dataset is structurally validated and ready to serve as the Tier 1 benchmark universe for subsequent market-microstructure and order-execution research.

The presence of diagnostic observations such as crossed quotes, extreme returns, price jumps, missing values, and zero-volume days has been explicitly documented rather than silently removed.

---

# 20. Handoff to Phase 4

Phase 3 establishes the **Tier 1 benchmark universe**.

Phase 4 will construct the **Tier 2 Historical CRSP Universe** using the same general principles of:

* historical identity preservation,
* CRSP identifier integrity,
* date-aware security histories,
* explicit eligibility rules,
* reproducible filtering,
* structural validation,
* diagnostic retention.

The key distinction is that Tier 2 should broaden the historical security universe beyond the deliberately restricted Tier 1 execution universe.

Phase 4 should therefore begin from the validated CRSP source infrastructure rather than modifying the finalized Tier 1 datasets.

The Tier 1 outputs produced in Phase 3 should be treated as **frozen reference datasets** unless a documented data-quality defect is subsequently discovered.

**Phase 4 — Tier 2 Historical CRSP Universe Construction**
