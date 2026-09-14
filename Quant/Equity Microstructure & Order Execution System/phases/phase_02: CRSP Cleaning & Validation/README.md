# Phase 2 — CRSP Cleaning & Validation
## 1. Objective

The objective of Phase 2 was to transform the raw CRSP daily stock file into a **structurally validated, reproducible, and auditable daily security dataset** suitable for downstream historical universe construction and market microstructure research.

The phase focused on:
- validating CRSP date fields;
- validating PERMNO and PERMCO identifiers;
- establishing the `PERMNO + date` observation key;
- identifying and investigating duplicate observations;
- reconciling duplicate corporate-action information against CRSP Distribution Information;
- standardizing data types;
- removing only demonstrably redundant duplicate observations;
- preserving all unique market observations;
- preserving corporate-action information;
- generating diagnostic quality flags without altering market data;
- validating the final cleaned dataset;
- producing a complete before/after cleaning audit.

### Core principle

>**Clean the structure, not the economics.**

No market-data values were imputed, winsorized, overwritten, or otherwise modified during Phase 2.

## 2. Input Datasets

Phase 2 operated on the CRSP datasets identified during Phase 1.

## Primary input
### CRSP Daily Stock File
```text
data/raw/crsp/CRSP_Daily Stock File.csv
```
This is the primary dataset being cleaned.

#### Original structure
- Rows: **184,053**
- Columns: **40**
- Unique PERMNOs: **41**
- Date range: **1993-01-04 → 2018-12-31**
- Unique observed dates: **6,547**

Important fields include:
```text
PERMNO
PERMCO
Ticker
YYYYMMDD
DlyCalDt
DlyPrc
DlyRet
DlyRetx
DlyRetI
DlyVol
DlyClose
DlyLow
DlyHigh
DlyBid
DlyAsk
DlyOpen
DlyNumTrd
ShrOut
DisExDt
DisDivAmt
DisFacPr
DisFacShr
```

## Supporting Input Datasets
### CRSP Distribution Information
```text
data/raw/crsp/CRSP_Distribution Information.csv
```
Used specifically to investigate and reconcile duplicate observations containing different corporate-action fields.

### Other CRSP reference datasets
The following datasets were inventoried during Phase 2 but were not used to alter the daily observations:
```text
CRSP_Names.csv
CRSP_Share Outstanding.csv
CRSP_Monthly Stock File.csv
CRSP_Daily Stock Market Indexes.csv
CRSP_Monthly Stock Market Indexes.csv
CRSP_Delisting Information.csv
```
These datasets remain available for subsequent universe construction, validation, and historical security-state reconstruction.

## 3. Scripts Created
Phase 2 produced a set of reusable validation, cleaning, and audit scripts.

### 3.1 Inventory
```text
scripts/inventory_crsp.py
```
**Purpose:**
- inventory the available CRSP files;
- identify file sizes;
- identify column counts;
- classify datasets by logical role;
- identify candidate date fields;
- identify candidate identifiers.

**Output:**
```text
data/processed/crsp/crsp_inventory.csv
```

### 3.2 Full-file Validation
```text
scripts/crsp_validate_full.py
```

**Purpose:**
Perform structural validation of the raw CRSP daily file across the entire dataset.

**Checks included:**
- row count;
- column count;
- date validity;
- `YYYYMMDD` validity;
- agreement between `YYYYMMDD` and `DlyCalDt`;
- PERMNO validity;
- PERMNO/PERMCO relationship;
- PERMNO/date uniqueness;
- price validity;
- OHLC consistency;
- bid/ask consistency;
- volume validity;
- trade-count validity;
- return-field missingness;
- corporate-action field missingness.

### 3.3 Identifier Validation
```text
scripts/crsp_validate_identifers.py
```
**Purpose:**

Validate the identity structure of the daily CRSP dataset.

**Checks included:**
- missing PERMNO;
- invalid PERMNO;
- unique PERMNO count;
- PERMNO/PERMCO consistency;
- PERMNO/ticker changes;
- PERMNO/date uniqueness.

The analysis identified one legitimate-looking ticker transition:
```text
PERMNO 90319:
GOOG → GOOGL
```
This was retained because PERMNO is the primary security identifier.

### 3.4 Duplicate Analysis
```text
scripts/crsp_analyze_duplicates.py
```
**Purpose:**

Identify and investigate duplicate `PERMNO + date` observations.

**The script distinguished:**
- exact duplicates;
- duplicates with differing fields;
- corporate-action-related differences.

### 3.5 Corporate-action Reconciliation
```text
scripts/crsp_reconcile_distribution.py
```
**Purpose:**

Reconcile corporate-action differences within duplicate daily observations against:
```text
CRSP_Distribution Information.csv
```
**Result:**
```text
MATCH    11
```
All 11 duplicate groups were successfully reconciled.

**Output:**
```text
data/processed/crsp/crsp_distribution_reconciliation.csv
```
### 3.6 Daily Cleaning
```text
scripts/crsp_clean_daily.py
```
**Purpose:**

Create the cleaned CRSP daily dataset.

**Operations included:**
- load raw daily file;
- standardize data types;
- parse date fields;
- validate date agreement;
- identify duplicate PERMNO/date groups;
- remove exact redundant rows;
- collapse investigated duplicate groups;
- preserve corporate-action information;
- generate diagnostic quality flags;
- validate the final key;
- write cleaned data and reports.

### 3.7 Clean-file Validation
```text
scripts/crsp_validate_clean.py
```
**Purpose:**
Perform a final independent validation against:
```text
data/processed/crsp/crsp_daily_clean.csv
```
This acts as the acceptance test for the cleaned dataset.

### 3.8 Before/After Audit
```text
scripts/crsp_audit_cleaning.py
```
**Purpose:**
Provide a complete audit trail between the raw and cleaned datasets.

**The audit verifies:**
- row-count changes;
- unique key preservation;
- duplicate removal;
- exact removed observations;
- corporate-action differences;
- PERMNO preservation;
- date preservation;
- absence of unexpected keys.

**Output:**
```text
data/processed/crsp/crsp_cleaning_audit.csv
```

## 4. Validation Results
### 4.1 Raw Dataset
The raw CRSP daily file contained:
```text
Rows:              184,053
Columns:                40
Unique PERMNOs:         41
Unique dates:        6,547
```

Date Range:
```text
1993-01-04
        ↓
2018-12-31
```

### 4.2 Date Validation
**Results:**
```text
Invalid DlyCalDt values:             0
Invalid YYYYMMDD values:             0
YYYYMMDD/DlyCalDt disagreements:     0
```
Therefore:
> Both CRSP date representations are internally consistent across the full dataset.

### 4.3 Identifier Validation
**Results:**
```text
Missing PERMNO:              0
Invalid PERMNO <= 0:         0
Unique PERMNOs:             41
PERMNOs with >1 PERMCO:      0
```
Therefore:
> PERMNO provides a stable security-level identifier for the observed dataset.

One PERMNO exhibited multiple ticker values:
```text
PERMNO 90319
GOOG → GOOGL
```
This was retained and is not treated as a duplicate-security problem.

### 4.4 Final Key Validation
The structural key is:
```text
PERMNO + DlyCalDt
```
Raw dataset:
```text
Unique keys:                  184,041
Duplicate key groups:              11
Rows in duplicate groups:          23
```

Clean dataset:
```text
Unique keys:                  184,041
Duplicate key groups:               0
Rows in duplicate groups:           0
```

### 4.5 Price Validation
Final clean-file validation found:
```text
DlyPrc <= 0:              0
DlyClose <= 0:            0
DlyLow <= 0:              0
DlyHigh <= 0:             0
DlyOpen <= 0:             0

Low > High:               0
Open outside Low/High:    0
Close outside Low/High:   0
```
Missing values were retained where present.

No price values were imputed.

### 4.6 Trading Activity Validation
Final clean-file validation:
```text
Negative DlyVol:          0
Negative DlyNumTrd:       0
```
Missing values were retained.

### 4.7 Corporate-action field preservation
The following fields were explicitly checked:
```text
DisExDt
DisDivAmt
DisFacPr
DisFacShr
```
All were preserved in the cleaned dataset.

## 5. Duplicate Findings
The raw daily dataset contained:
```text
Duplicate PERMNO/date groups:        11
Rows belonging to duplicate groups:  23
```

After cleaning:
```text
Duplicate groups:                     0
Rows belonging to duplicate groups:   0
```
### Duplicate Classification
#### Exact Duplicate
One group contained three identical rows:
```text
PERMNO = 10104
Date   = 2012-12-12
Ticker = ORCL
```
Three raw rows were reduced to one.
This resulted in:
```text
2 rows removed
```

#### Corporate-action Duplicate Groups
The remaining ten duplicate groups contained otherwise identical market observations but differing corporate-action fields.

These involved:
```text
PERMNO 10107   MSFT
PERMNO 59328   INTC
PERMNO 69032   MS
PERMNO 70519   C
PERMNO 84398   SPY
PERMNO 88222   IWM
```
**PERMNO 88222** appeared in **five** separate duplicate dates.

The differing fields were primarily:
```text
DisDivAmt
DisFacPr
```
The market-data fields themselves were otherwise consistent.

## 6. Corporate-Action Reconciliation
The duplicate observations were not blindly deduplicated.

Instead, the differing corporate-action information was compared with:
```text
CRSP_Distribution Information.csv
```
The reconciliation produced:
```text
11 duplicate groups examined
11 MATCH
0 unresolved
```
Examples included:
### MSFT
```text
Date: 2004-11-15

Daily corporate-action values:
0.08 | 3.00
```
These matched the two corresponding CRSP distribution records.

### Citigroup
```text
Date: 2002-08-21

DisDivAmt:
0.712871 | 1.561387

DisFacPr:
0.020753 | 0.045455
```
Both values were reconciled against the distribution dataset.

### IWM
Multiple dates contained two dividend/distribution observations on the same trading date.

These were reconciled successfully.

Therefore, the duplicate records were interpreted as **multiple corporate-action records attached to the same daily market observation**, rather than independent market observations.

## 7. Cleaning Policy
The Phase 2 cleaning policy is deliberately conservative.
### 7.1 Structural Cleaning
The following were corrected or resolved:
- inconsistent data types;
- invalid date representations, if present;
- duplicate `PERMNO/date` observations;
- exact duplicate rows.

### 7.2 Market Data Preservation
The following were **not** modified:
```text
DlyPrc
DlyRet
DlyRetx
DlyRetI
DlyVol
DlyClose
DlyLow
DlyHigh
DlyBid
DlyAsk
DlyOpen
DlyNumTrd
```
No:
- interpolation;
- forward filling;
- backward filling;
- winsorization;
- outlier deletion;
- price adjustment;
- return adjustment;
- volume adjustment
was performed.

### 7.3 Missing Values
Missing values were retained.
For example:
```text
DlyOpen
DlyHigh
DlyLow
DlyClose
DlyNumTrd
```
may contain missing observations.

Missingness is considered an empirical property of the CRSP dataset and should not be silently converted into artificial observations.

### 7.4 Quality Flags
Diagnostic flags were generated during cleaning.

However:
>> Quality flags are diagnostic only.

They do not alter the underlying market data.

The final clean file intentionally contains **no diagnostic quality-flag columns**.

The diagnostic information is instead retained in:
```text
crsp_daily_cleaning_report.csv
crsp_daily_flagged_observations.csv
```

### 7.5 Duplicate Policy
The structural daily key is:
```text
PERMNO + date
```
Duplicate observations were investigated before removal.

The final dataset contains exactly one daily market observation per:
```text
PERMNO + date
```
Corporate-action information was reconciled separately rather than treating each corporate-action record as a separate market observation.

## 8. Output Files
Phase 2 produced the following processed outputs.
### Clean Daily Dataset
```text
data/processed/crsp/crsp_daily_clean.csv
```
Final characteristics:
```text
Rows:             184,041
Columns:               40
Unique PERMNOs:         41
Unique dates:        6,547
Duplicate keys:         0
```
This is the primary Phase 3 input.

### Cleaning Report
```text
data/processed/crsp/crsp_daily_cleaning_report.csv
```
Contains summary information regarding the cleaning process.

### Flagged Observations
```text
data/processed/crsp/crsp_daily_flagged_observations.csv
```
Contains observations identified by diagnostic quality checks.

### Distribution reconciliation
```text
data/processed/crsp/crsp_distribution_reconciliation.csv
```
Documents the reconciliation between duplicate daily observations and CRSP Distribution Information.

### Cleaning audit
```text
data/processed/crsp/crsp_cleaning_audit.csv
```
Documents exactly what changed between the raw and clean datasets.

### Inventory
```text
data/processed/crsp/crsp_inventory.csv
```
Documents the CRSP input-file inventory established during the data-infrastructure stage.

## 9. Known Retained Diagnostic Issues
The clean dataset is structurally valid, but **structurally valid does not mean every observation is economically perfect.**

Several diagnostic conditions remain intentionally retained.

### 9.1 Bid > Ask
The final validation found:
```text
Bid > Ask observations: 3,725
```
These observations were **not deleted or corrected.**

They are treated as diagnostic observations because historical CRSP bid/ask fields can contain data-quality or reporting peculiarities.

For Phase 2:
>> No assumption was made that every crossed quote represents an erroneous observation.

Future execution-modeling phases should determine how these observations affect quote-based measures such as:
- spread;
- quoted spread;
- effective spread;
- midpoint;
- execution-cost estimates.

### 9.2 Missing prices
The clean file contains some missing price observations:
```text
DlyPrc:       1
DlyClose:    61
DlyLow:      61
DlyHigh:     61
DlyOpen:    120
```
These were retained.

### 9.3 Missing trade counts
The clean dataset contains substantial missingness in:
```text
DlyNumTrd
```
This was not imputed.

Downstream analyses must explicitly determine whether trade-count-based metrics require non-missing values.

### 9.4 Missing corporate-action fields

Most observations naturally have no corporate action on a given date.

Therefore, missing:
```text
DisExDt
DisDivAmt
DisFacPr
DisFacShr
```
is not automatically treated as a data-quality failure.

### 9.5 Ticker changes

Ticker changes remain possible within a PERMNO.

For example:
```text
PERMNO 90319
GOOG → GOOGL
```
Downstream security identification should therefore use:
```text
PERMNO
```
rather than ticker as the primary identity key.

## 10. Phase 2 Acceptance Criteria
Phase 2 is considered complete when all of the following conditions are satisfied:
- [ ] Raw CRSP daily file successfully loaded
- [ ] Required columns present
- [ ] Dates parse successfully
- [ ] `YYYYMMDD` agrees with `DlyCalDt`
- [ ] No invalid PERMNO values
- [ ] PERMNO/PERMCO relationship validated
- [ ] Duplicate PERMNO/date groups identified
- [ ] Duplicate groups investigated
- [ ] Corporate-action duplicates reconciled
- [ ] No unresolved duplicate groups
- [ ] Clean dataset has unique PERMNO/date keys
- [ ] Raw unique keys preserved
- [ ] No market-data values imputed
- [ ] Corporate-action fields preserved
- [ ] Clean-file validation passed
- [ ] Before/after audit passed
- [ ] Exactly 12 rows removed
- [ ] Diagnostic issues documented

## 11. Key Quantitative Results
```text
Raw rows:                    184,053
Clean rows:                  184,041
Rows removed:                     12

Raw unique PERMNO/date keys: 184,041
Clean unique PERMNO/date keys:
                             184,041

Raw duplicate groups:             11
Clean duplicate groups:            0

Raw unique PERMNOs:               41
Clean unique PERMNOs:             41

Raw unique dates:              6,547
Clean unique dates:            6,547
```
Most importantly:
```text
Raw keys absent from clean:        0
Unexpected clean keys:             0
```
