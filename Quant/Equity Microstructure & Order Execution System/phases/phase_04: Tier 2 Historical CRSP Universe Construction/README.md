# Phase 4 — Tier 2 Historical CRSP Universe Construction
---

## 1. Phase Objective

Phase 4 constructed a historically valid **Tier 2 CRSP execution universe** and transformed cleaned CRSP Daily data into an execution-oriented dataset suitable for later TAQ/TAQM integration.

The phase established:

- historical security identity and eligibility;
- historical security intervals;
- Daily-to-master reconciliation;
- a validated Tier 2 Daily panel;
- panel rejection diagnostics;
- an execution-ready CRSP subset;
- execution rejection diagnostics;
- reproducible validation artifacts.

---

## 2. Research Design Decisions

### Research Window

- Start: `1993-01-01`
- End: `2018-12-31`

The supplied CRSP Daily data begin on `1993-01-04`.

### Historical Eligibility

Tier 2 eligibility is determined from the **historical CRSP security master**, not merely from Daily-file presence.

Historical existence is represented through the effective historical interval fields.

### Security Classification

The validated execution panel uses:

```text
EQTY_COM_CORP
```

as the valid ordinary corporate common-equity classification.

Explicit exclusions included:

| PERMNO | Ticker | Classification | Decision |
|---:|---|---|---|
| 84398 | SPY | FUND_OR_ETF | Excluded |
| 86755 | QQQ | FUND_OR_ETF | Excluded |
| 88222 | IWM | FUND_OR_ETF | Excluded |
| 88614 | V | ADR_OR_NON_US_EQUITY | Excluded |

`EQTY_COM_ACOR` was retained for diagnostic/review purposes and was not automatically treated as ordinary corporate common equity.

---

## 3. Historical Security Master Findings

The historical security master contained:

- **238 rows**
- **38 unique PERMNOs**

The final eligible universe contained:

- **34 unique PERMNOs**

The eligibility universe was verified as a strict subset of the historical master:

```text
Eligible PERMNOs not in historical master = 0
```

---

## 4. Historical Master ↔ Daily Reconciliation

Research-window CRSP Daily contained:

- **184,041 observations**
- **41 PERMNOs**
- `1993-01-04` through `2018-12-31`

Initial reconciliation:

| Category | Count |
|---|---:|
| Historical master PERMNOs | 38 |
| Research-window Daily PERMNOs | 41 |
| Matched | 36 |
| NAMES_ONLY | 2 |
| DAILY_ONLY | 5 |

### NAMES_ONLY

```text
13407
16424
```

These securities existed in the historical master but had no Daily observations. They were retained in the historical identity layer.

### DAILY_ONLY

```text
11260
48071
50024
58827
75817
```

These securities appeared in Daily but lacked corresponding historical-master identity/classification records. They were not automatically admitted.

**Research-design rule:** Daily-file presence alone is insufficient evidence of historical Tier 2 eligibility.

---

## 5. Tier 2 Daily Panel

The validated Daily panel contains:

| Metric | Count |
|---|---:|
| Historical master PERMNOs | 38 |
| Eligible Tier 2 PERMNOs | 34 |
| Daily panel PERMNOs | 31 |
| Daily panel rows | 131,497 |
| Eligible PERMNOs without Daily history | 3 |

Historical interval matching verified:

- no overlapping master intervals;
- every panel row has an interval;
- every panel date falls inside its matched interval;
- all panel dates remain inside the research window.

---

## 6. Daily Panel Rejection Audit

The panel-building process started with:

```text
160,402 eligible Daily observations
```

and retained:

```text
131,497 valid panel observations
```

Therefore:

```text
28,905 observations rejected
```

The panel rejection rate was approximately:

```text
18.02%
```

The rejection reason was:

```text
NO_HISTORICAL_INTERVAL
```

The rejection audit confirmed that rejected observations were outside a valid historical interval or otherwise unmatched.

Artifact:

```text
crsp_tier2_daily_panel_rejection_audit.csv
```

These observations are preserved diagnostically rather than silently dropped.

---

## 7. Execution Dataset

The execution-oriented filtering began from:

```text
131,497 Daily-panel observations
```

and produced:

```text
40,067 execution-eligible observations
12 PERMNOS
```

Thus:

```text
31 panel PERMNOS
        ↓
12 execution-eligible PERMNOS
```

The reduction of 19 PERMNOS is an **execution-data availability/quality result**, not a historical Tier 2 eligibility decision.

A security may therefore be:

1. historically Tier 2 eligible;
2. represented in the Daily panel;
3. but absent from the execution-ready subset because required execution fields are unavailable or invalid.

---

## 8. Execution Rejection Findings

Execution-field validation produced:

```text
Input panel observations:        131,497
Execution-eligible observations:  40,067
Rejected observations:             91,430
```

Execution rejection rate:

```text
91,430 / 131,497 ≈ 69.53%
```

The dominant documented rejection reason was:

```text
MISSING_DLYNUMTRD
```

with:

```text
88,764 observations
```

Other rejection causes included:

- crossed bid/ask markets;
- missing bid/ask;
- missing OHLC fields;
- combinations of missing execution fields.

The execution rejection artifacts are:

```text
crsp_tier2_execution_dataset_rejection_audit.csv
crsp_tier2_execution_dataset_rejection_summary.csv
```

They must remain first-class diagnostic artifacts.

---

## 9. Final Execution-Dataset Validation

The final successful execution-dataset validation passed:

| Check | Result |
|---|---|
| No missing PERMNO | PASS |
| No missing date | PASS |
| No duplicate PERMNO-date | PASS |
| Dates within research window | PASS |
| Historical interval present | PASS |
| Dates within historical interval | PASS |
| Common-equity classification | PASS |
| Required execution fields present | PASS |
| No crossed bid/ask markets | PASS |
| Quoted spread nonnegative | PASS |
| Positive midquote | PASS |
| Dollar-volume calculation consistent | PASS |
| Valid + rejected = panel input | PASS |

The final authoritative CRSP execution dataset is therefore:

```text
crsp_tier2_execution_dataset.csv
```

with:

```text
40,067 rows
12 PERMNOS
```

---

## 10. Important Final-QA Artifact Reconciliation Issue

The first attempt at the Phase 4 final QA failed because it mixed two different rejection layers.

The QA compared:

```text
131,497 panel rows
40,067 execution rows
28,905 rejection rows
```

but the `28,905` rows are **historical panel-construction rejections**, not execution rejections.

The correct execution reconciliation is:

```text
131,497 panel observations
-
40,067 execution-eligible observations
=
91,430 execution-rejected observations
```

Therefore:

```text
40,067 + 91,430 = 131,497
```

The correct historical-panel reconciliation is:

```text
160,402 eligible Daily observations
=
131,497 valid panel observations
+
28,905 panel rejection observations
```

Accordingly, the failed final-QA checks concerning:

- execution plus rejections;
- execution rejection rate;
- missing `dlynumtrd` rejection count;
- rejection row count;

were caused by selecting the wrong rejection artifact for the execution-level reconciliation.

This is a **QA bookkeeping/artifact-selection issue**, not evidence that the final execution dataset failed its own execution-level validation.

Before declaring Phase 4 completely closed, rerun final QA after correcting the artifact references.

---

## 11. Reproducibility Requirements

The intended Phase 4 dependency chain is:

```text
CRSP source data
      ↓
crsp_tier2_historical_security_master.csv
      ↓
crsp_tier2_eligible_universe.csv
      ↓
crsp_daily_clean.csv
      ↓
crsp_tier2_daily_panel.csv
      ↓
crsp_tier2_execution_dataset.csv
```

Supporting diagnostics exist at each stage.

The final QA must preserve the distinction between:

```text
Panel construction rejection = 28,905
Execution eligibility rejection = 91,430
```

Do not modify data merely to make the QA counts reconcile.

---

## 12. Phase 4 Artifact Inventory

Major outputs:

```text
crsp_tier2_historical_security_master.csv

crsp_tier2_eligible_universe.csv
crsp_tier2_universe_exclusions.csv
crsp_tier2_eligible_universe_summary.csv
crsp_tier2_reconciliation_exceptions.csv

crsp_tier2_daily_coverage_diagnostic.csv
crsp_tier2_daily_only_diagnostic.csv

crsp_tier2_daily_panel.csv
crsp_tier2_daily_panel_summary.csv
crsp_tier2_daily_panel_coverage.csv
crsp_tier2_daily_panel_validation.csv

crsp_tier2_daily_panel_rejection_audit.csv
crsp_tier2_daily_panel_rejection_summary.csv
crsp_tier2_daily_panel_rejection_permno_summary.csv
crsp_tier2_daily_panel_rejection_validation.csv

crsp_tier2_execution_dataset.csv
crsp_tier2_execution_dataset_summary.csv
crsp_tier2_execution_dataset_rejection_audit.csv
crsp_tier2_execution_dataset_rejection_summary.csv
crsp_tier2_execution_dataset_validation.csv
```

---

## 13. Phase 4 Checklist

### Historical Universe

- [x] Research window fixed.
- [x] Historical security master constructed.
- [x] Historical PERMNO identity preserved.
- [x] Historical intervals validated.
- [x] No overlapping intervals.
- [x] Eligibility derived from historical master.
- [x] Funds/ETFs excluded.
- [x] ADR/non-US securities excluded.
- [x] DAILY_ONLY securities not automatically admitted.

### Daily Panel

- [x] Daily restricted to research window.
- [x] Duplicate PERMNO-date observations checked.
- [x] Daily restricted to eligible PERMNOS.
- [x] Historical interval matching performed.
- [x] Out-of-interval observations rejected.
- [x] Panel rejection audit created.
- [x] Daily panel validated.

### Execution Dataset

- [x] Required execution fields checked.
- [x] Execution fields normalized.
- [x] Missingness measured.
- [x] Invalid execution values audited.
- [x] Crossed markets rejected.
- [x] Quoted spread validated.
- [x] Positive midquotes validated.
- [x] Dollar volume validated.
- [x] Execution rejection audit preserved.
- [x] Final execution dataset validated.

### Final QA

- [x] Universe subset relationships validated.
- [x] Panel uniqueness validated.
- [x] Execution uniqueness validated.
- [x] Date ranges validated.
- [x] Historical intervals validated.
- [ ] Correct final QA rejection-artifact references.
- [ ] Rerun final QA after correction.

---

# 14. Key Phase 4 Findings

### Finding 1 — Multiple universe layers must not be conflated

```text
38 historical-master PERMNOS
        ↓
34 eligible Tier 2 PERMNOS
        ↓
31 Daily-panel PERMNOS
        ↓
12 execution-ready PERMNOS
```

Each reduction has a different reason.

### Finding 2 — Daily-only securities are unresolved at the identity layer

Five Daily-only PERMNOS were identified and excluded because their historical-master identity/classification was not established.

### Finding 3 — Missing Daily history does not invalidate historical eligibility

Two historical-master securities lacked Daily observations but remained represented in the historical universe.

### Finding 4 — Historical interval matching removes 28,905 observations

These are panel-construction rejections, not execution-quality rejections.

### Finding 5 — Execution-field availability is the main CRSP bottleneck

`91,430` of `131,497` panel observations were rejected for execution eligibility, approximately `69.53%`.

Missing `dlynumtrd` is the dominant documented cause.

### Finding 6 — Rejection audits are essential

Both rejection layers are preserved and must remain distinct in future phases.

---

# 15. Phase 5 — TAQ/TAQM Data Inventory & Cleaning

## Objective

Phase 5 will establish a clean, documented, reproducible TAQ/TAQM data layer that can eventually be linked to the validated CRSP Tier 2 universe.

The phase must answer:

> What TAQ/TAQM data are available, what do the files contain, what are their temporal and security coverage, how are securities identified, what quality problems exist, and what subset can be reliably linked to CRSP?

---

# 16. Handoff Prompt — Phase 5

Continue the **Equity Microstructure & Order Execution System** project.

The next phase is:

# Phase 5 — TAQ/TAQM Data Inventory & Cleaning

Do not redesign the research objective. Continue from the CRSP foundation created in Phase 4.

## Phase 5 Step 1 — Inventory all TAQ/TAQM files

Inspect the local project directories and identify all TAQ/TAQM-related files.

Do not assume filenames, schemas, formats, or coverage.

For each file record:

- filename;
- path;
- extension;
- file size;
- row count where feasible;
- date fields;
- apparent date range;
- security identifiers;
- trade/quote classification;
- major columns;
- compression;
- likely duplicate keys;
- source/vendor conventions.

For huge files, use header inspection, sampling, chunked processing, and explicit dtypes.

Create:

```text
taq_taqm_file_inventory.csv
```

and a reproducible inventory script.

---

## Phase 5 Step 2 — Establish the TAQ/TAQM data architecture

Determine whether files contain:

- trades;
- quotes;
- TAQ;
- TAQM;
- consolidated quotes;
- exchange-specific records;
- daily summaries;
- intraday observations;
- reference/security-master information;
- corrections/cancellations;
- metadata.

Document each file's semantic role before merging anything.

---

## Phase 5 Step 3 — Inspect schemas

For every file:

1. Inspect headers/sample rows.
2. Normalize column names for analysis only.
3. Preserve original column names.
4. Determine data types.
5. Identify candidate keys.
6. Determine timestamp precision.
7. Identify security identifiers.
8. Identify trade/quote condition fields.
9. Identify exchange fields.
10. Identify correction/cancellation indicators.

Create:

```text
taq_taqm_schema_inventory.csv
```

---

## Phase 5 Step 4 — Determine temporal coverage

For every file determine:

- earliest date/timestamp;
- latest date/timestamp;
- trading dates represented;
- observations per date;
- missing dates;
- partial dates;
- sparse dates;
- continuity.

Compare coverage with:

```text
1993-01-01 through 2018-12-31
```

Do not assume TAQ/TAQM coverage matches CRSP.

Create:

```text
taq_taqm_date_coverage.csv
```

---

## Phase 5 Step 5 — Determine security identifier structure

Identify every available identifier, including where applicable:

- PERMNO;
- CUSIP;
- CUSIP8;
- CUSIP9;
- ticker;
- exchange symbol;
- issue identifier;
- vendor-specific identifier.

Do not assume ticker is stable.

Document identifier availability by file and date.

The eventual linkage target is:

```text
TAQ/TAQM observation
        ↓
TAQ identifier
        ↓
CRSP security identity
        ↓
PERMNO
```

---

## Phase 5 Step 6 — Build identifier coverage diagnostics

Using the Phase 4 historical master as the reference layer, measure:

- direct PERMNO matches, if available;
- CUSIP matches;
- CUSIP9 matches;
- ticker matches;
- exchange + ticker matches;
- ambiguous matches;
- unmatched records;
- identifier changes over time.

Do not use ticker-only matching as the final linkage method without explicit validation.

Create:

```text
taq_taqm_identifier_coverage.csv
```

---

## Phase 5 Step 7 — Inspect timestamps

Determine:

- timestamp resolution;
- timezone;
- exchange-local vs normalized time;
- millisecond/microsecond precision;
- sortability;
- date/timestamp consistency;
- malformed timestamps;
- observations outside expected trading hours.

Do not automatically remove pre-market, after-hours, or unusual records until their role is understood.

Create diagnostics for:

```text
invalid timestamp
duplicate timestamp
non-monotonic timestamp
unexpected date
```

---

## Phase 5 Step 8 — Inspect trade records

For trades identify and profile:

- price;
- size;
- timestamp;
- exchange;
- trade condition;
- correction indicator;
- cancellation indicator;
- sale condition;
- sequence number;
- security identifier.

Measure:

- missing prices;
- missing sizes;
- zero/negative prices;
- zero/negative sizes;
- duplicates;
- corrections;
- cancellations;
- unusual conditions.

Do not silently delete condition-coded trades. Classify and audit them.

---

## Phase 5 Step 9 — Inspect quote records

For quotes identify and profile:

- bid;
- ask;
- bid size;
- ask size;
- timestamp;
- exchange;
- quote condition;
- sequence number;
- security identifier.

Measure:

- missing bid;
- missing ask;
- zero/negative bid;
- zero/negative ask;
- crossed quotes;
- locked quotes;
- abnormal spreads;
- missing quote sizes;
- duplicate records.

Separate:

```text
valid quote
locked quote
crossed quote
invalid quote
```

Do not automatically discard locked/crossed quotes without documenting the rule.

---

## Phase 5 Step 10 — Define explicit cleaning rules

Before final cleaning, create a rule table:

```text
rule_id
field
condition
action
reason
expected_impact
```

Potential rules include:

```text
INVALID_PRICE
INVALID_SIZE
MALFORMED_TIMESTAMP
CROSSED_QUOTE
LOCKED_QUOTE
CANCELLED_TRADE
CORRECTED_TRADE
DUPLICATE_RECORD
UNKNOWN_IDENTIFIER
OUTSIDE_RESEARCH_WINDOW
```

Avoid irreversible transformations unless justified.

---

## Phase 5 Step 11 — Build rejection audits

Every excluded observation should receive a documented reason.

Recommended artifacts:

```text
taq_trade_rejection_audit.csv
taq_trade_rejection_summary.csv
taq_quote_rejection_audit.csv
taq_quote_rejection_summary.csv
```

Core project principle:

> Never silently drop observations when the reason can be measured and documented.

---

## Phase 5 Step 12 — Quantify data quality

Produce absolute counts and percentages for:

- missingness;
- duplicates;
- invalid values;
- timestamp problems;
- identifier coverage;
- trade/quote condition coverage;
- daily observation counts;
- security coverage;
- exchange coverage;
- research-window coverage.

---

## Phase 5 Step 13 — Preserve raw/interim/processed layers

Never overwrite raw TAQ/TAQM files.

Prefer:

```text
data/
    raw/
        taq/
        taqm/

    interim/
        taq/
        taqm/

    processed/
        taq/
        taqm/
```

All transformations must be reproducible from raw inputs.

---

## Phase 5 Step 14 — Implement a reproducible cleaning pipeline

Suggested structure:

```text
scripts/taq/
    inventory_taq_taqm.py
    profile_taq_schema.py
    analyze_taq_coverage.py
    analyze_taq_identifiers.py
    clean_taq_trades.py
    clean_taq_quotes.py
    validate_taq_cleaning.py
```

Adapt to the actual repository structure.

For very large datasets:

- use chunks;
- partition outputs where appropriate;
- use explicit dtypes;
- avoid unnecessary full-data copies;
- log progress;
- make outputs deterministic.

---

## Phase 5 Step 15 — Build validation tests

### Structural

- required fields exist;
- expected types;
- core identifiers present after cleaning;
- timestamps valid;
- dates valid.

### Trade

- prices valid;
- sizes valid;
- correction/cancellation handling documented;
- duplicates handled.

### Quote

- bid/ask valid;
- spreads nonnegative;
- locked/crossed quotes classified;
- duplicates handled.

### Identifier

- normalization deterministic;
- CRSP linkability quantified;
- ambiguous mappings isolated.

### Temporal

- observations remain inside research window;
- timestamp/date consistency holds.

### Reproducibility

- cleaned counts reproduce from raw inputs;
- rejection counts reconcile;
- outputs are deterministic.

---

**Begin Phase 5 with inventory, schema discovery, coverage analysis, identifier analysis, and cleaning. Do not begin modeling or final CRSP–TAQ merging until those foundations are validated.**
