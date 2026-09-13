# Phase 1 — Local Data Inventory & Infrastructure

## 1. Objective
The objective of Phase 1 was to establish a **minimal, reproducible** local data infrastructure for the project before performing substantive dataset cleaning or empirical analysis.

The phase was intentionally designed to answer:
- Where are the raw datasets located?
- What files are available?
- What are their structures and schemas?
- What date conventions do they use?
- How should the datasets be accessed without repeatedly loading extremely large files?
- What reusable infrastructure is required by later phases?
- What assumptions and limitations must be recorded before cleaning begins?

The objective was **not** to fully clean TAQ, TAQM, or CRSP during this phase.

## 2. Phase Scope
Phase 1 covered:
- project/data directory structure
- configuration management
- raw-data path management
- lightweight data readers
- dataset inventory
- schema inspection
- sample-based validation
- date-format identification
- basic automated testing
- documentation of important dataset characteristics

Phase 1 deliberately avoided:
- full-file processing
- expensive repeated scans of TAQ/TAQM
- detailed anomaly detection
- extensive feature engineering
- cross-dataset merging
- research-variable construction
- CRSP cleaning
- TAQ/TAQM cleaning

Those activities belong to subsequent phases.

## 3. Target Architecture
The project infrastructure established during Phase 1 follows the intended package structure:
```text
root/
│
├── README.md
├── LICENSE
├── requirements.txt
├── pyproject.toml
├── setup.py
├── .gitignore
│
├── docs/
│   ├── data_dictionary.md
│   └── methodology_notes.md
│
├── notebooks/
│   └── ...
│
├── src/
│   └── equity_microstructure/
│       ├── __init__.py
│       ├── config.py
│       │
│       └── data/
│           ├── __init__.py
│           ├── readers.py
│           │
│           └── inventory/
│               ├── __init__.py
│               └── inventory.py
│
├── data/
│   ├── raw/
│   │   ├── crsp/
│   │   ├── taq/
│   │   └── taqm/
│   │
│   └── processed/
│
├── tests/
│   ├── unit/
│   │   └── test_config.py
│   └── ...
│
└── reports/
    ├── figures/
    └── tables/
```

## 4. Data Infrastructure Established
### 4.1 Configuration
The project contains a centralized configuration layer through:
```text
src/equity_microstructure/config.py
```
Its purpose is to prevent hard-coded paths and research parameters from being scattered throughout notebooks and scripts.

Configuration is intended to contain items such as:
- project root
- raw-data directory
- processed-data directory
- TAQ path
- TAQM path
- CRSP path
- sample date ranges
- relevant PERMNO/security lists where applicable

This allows subsequent phases to reference the same project configuration.

## 5. Data Infrastructure Infrastructure
A reusable reader layer was established:
```text
src/equity_microstructure/data/readers.py
```
The reader infrastructure allows samples of large datasets to be inspected without loading the entire dataset into memory.

For example:
```python
from pathlib import Path
from equity_microstructure.data.readers import read_sample

path = Path("data/raw/taq/taq.csv")

df = read_sample(path, nrows=5)
```
This approach is particularly important because the TAQ and TAQM datasets are large and should not be repeatedly loaded in full merely for inspection.

## 6. Dataset Structure Findings
### 6.1 TAQ
The TAQ dataset is stored as **one consolidated file:**
```text
data/raw/taq/taq.csv
```
It contains the available year ranges within the same file.
#### Observed sample characteristics
The inspected TAQ sample contained:
```text
5 rows
102 columns
```
The dataset contains variables relating to:
- dates
- securities
- intraday quote information
- opening/closing prices
- trading activity
- trade counts
- trading volume
- trading value
- ISO trades
- odd-lot trades
- mixed-lot trades
- buy/sell classifications
- effective spreads
- quoted spreads
- realized spreads
- price impacts
- order-flow measures
- volatility measures
- variance ratios
- signed volume measures
- other market-microstructure statistics

Representative fields include:
```text
date
symbol
QTime_1pm
BB_1pm
BO_1pm
MID_1pm
QTime_4pm
BB_4pm
BO_4pm
Mid_4pm
OTime
OPrice
DTime
DPrice
Vol_oc
Value_oc
Ret_pre_t
Ret_mkt_t
Ret_post_t
NumTrades_t
SumVolume_t
SumValue_m
BuyNumTrades_LR1
SellNumTrades_LR1
BuyVol_LR1
SellVol_LR1
ESpreadDollar_Avg1
RSpreadDollar_Avg1
PriceImpactDollar_Avg1
VarianceRatio1
TSignSqrtDVol1
HIndex1
```
The full schema should be treated as authoritative from the actual file rather than reconstructed manually from memory.

### 6.2 TAQM
The TAQM dataset is also stored as **one consolidated file:**
```text
data/raw/taqm/taqm.csv
```
It likewise contains the available year ranges within the same file.

#### Observed sample characteristics
The inspected TAQM sample contained:
```text
5 rows
149 columns
```
The dataset includes:
- daily trading activity
- buy/sell classification
- trade counts
- trade volume
- dollar volume
- opening/closing information
- intraday quote snapshots
- bid/ask prices
- bid/ask depth
- quoted spreads
- effective spreads
- realized spreads
- price impact
- volatility
- order-flow imbalance measures
- retail trading measures
- institutional trading measures

Representative fields include:
```text
DATE
SYM_ROOT
SYM_SUFFIX
symbol
CPrc
OTime
OPrc
size_1pm
ttime_1pm
ptime_1pm
ttime_4pm
ptime_4pm
mid_1pm
mid_4pm
price_low_m
price_high_m
avg_price_m
total_vol_m
total_dollar_m
total_n_trades_m
QuotedSpread_Dollar_tw
QuotedSpread_Percent_tw
EffectiveSpread_Dollar_Ave
EffectiveSpread_Percent_Ave
DollarRealizedSpread_LR_Ave
DollarPriceImpact_LR_Ave
ivol_t
ivol_q
bs_ratio_num
bs_ratio_vol
HIndex
var_ratio1
var_ratio2
var_ratio3
var_ratio4
var_ratio5
BuyNumTrades_Retail
BuyVol_Retail
SellNumTrades_Retail
SellVol_Retail
BuyNumTrades_Inst20k
BuyVol_Inst20k
BuyNumTrades_Inst50k
BuyVol_Inst50k
```

## 7. Date Conversion
A critical finding during Phase 1 is that the dataset date convention is:
```text
DD/MM/YYYY
```
This applies to the relevant TAQ and TAQM date fields examined.

Examples include:
```text
06/04/1993
07/04/1993
08/04/1993
12/04/1993
13/04/1993
```
#### Required parsing convention
Future cleaning code should explicitly use:
```python
pd.to_datetime(
    df["date"],
    dayfirst=True,
    errors="coerce"
)
```
or the equivalent for TAQM's `DATE` field.

This is an important data-integrity rule and should be preserved throughout the project.

## 8. Testing
The configuration layer has been tested using PyTest.

Current test result:
```text
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.15.1, cov-7.1.0
collected 33 items

tests\integration\test_inventory.py ..                                                                                                                       [  6%]
tests\unit\test_config.py ............                                                                                                                       [ 42%]
tests\unit\test_discovery.py ..........                                                                                                                      [ 72%]
tests\unit\test_inventory.py .                                                                                                                               [ 75%]
tests\unit\test_loaders.py .                                                                                                                                 [ 78%]
tests\unit\test_normalize.py ....                                                                                                                            [ 90%]
tests\unit\test_readers.py .                                                                                                                                 [ 93%]
tests\unit\test_validate.py ..

33 passed in 0.90s
```
Therefore:
```text
Phase 1 configuration tests: PASS
```
The test suite is functioning correctly under the project's current Python environment.

## 9. Phase 1 Checklist
#### Project Infrastructure
- [ ] Project root established
- [ ] Python package established
- [ ] `src/equity_microstructure/` established
- [ ] Configuration module established
- [ ] Data package established
- [ ] Reader module established
- [ ] Inventory module established
- [ ] Inventory module moved into `data/inventory/`

#### Raw Data
- [ ] TAQ raw-data location established
- [ ] TAQM raw-data location established
- [ ] CRSP raw-data location accounted for
- [ ] TAQ consolidated-file structure identified
- [ ] TAQM consolidated-file structure identified

#### Dataset Understanding
- [ ] TAQ sample inspected
- [ ] TAQ column structure recorded
- [ ] TAQM sample inspected
- [ ] TAQM column structure recorded
- [ ] Date convention identified
- [ ] Important microstructure variable groups identified

#### Reproducibility
- [ ] Reusable sample reader established
- [ ] Central configuration established
- [ ] Basic tests established
- [ ] Configuration tests passing

#### Scope Control
- [ ] Avoided unnecessary full-file scans
- [ ] Avoided premature feature engineering
- [ ] Avoided premature cross-dataset integration
- [ ] Avoided unnecessary infrastructure complexity

## 10. Key Findings
### Finding 1 — TAQ is consolidated
TAQ consists of a single raw file containing multiple year ranges.

**Implication:** downstream code must filter by date rather than expect yearly raw files.

### Finding 2 — TAQM is consolidated
TAQM likewise consists of a single raw file containing multiple year ranges.

**Implication:** the same date-filtering approach applies.

### Finding 3 — Date format is DD/MM/YYYY
The date convention is:
```text
DD/MM/YYYY
```
**Implication:** explicit dayfirst=True parsing is required.

### Finding 4 — TAQ and TAQM are already highly engineered datasets
The samples contain many variables directly related to the research objectives, including:
- spreads
- price impact
- realized spread
- trading volume
- order flow
- volatility
- imbalance
- retail/institutional activity
**Implication:** we should avoid unnecessarily reconstructing measures that are already provided and validated against the source methodology. However, independently calculated measures may still be required where the research design calls for them.

## Finding 5 — Large-file processing must be deliberate
The raw datasets are sufficiently large that indiscriminate full-file loading is inefficient.

**Implication:** later phases should use:
- chunking
- column selection
- date filtering
- symbol filtering
- processed intermediate datasets
where appropriate.

## 11. Phase 1 Exit Criteria
Phase 1 is considered complete because the project now has enough infrastructure and dataset knowledge to begin actual data cleaning.

The following criteria have been satisfied:
- [✓] Know where the data lives
- [✓] Know how the data is organized
- [✓] Know the basic schemas
- [✓] Know the date convention
- [✓] Know TAQ/TAQM are consolidated files
- [✓] Have reusable readers
- [✓] Have centralized configuration
- [✓] Have basic automated tests
- [✓] Tests pass
- [✓] No major unresolved infrastructure issue
