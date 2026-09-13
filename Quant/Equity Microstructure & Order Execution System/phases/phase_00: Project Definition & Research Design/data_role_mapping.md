# Data Role Mapping

## 1. Purpose

This document defines the role of each dataset in the Market Microstructure & Order Execution System.

The purpose is to establish clear data provenance before implementation begins.

Each dataset has:

- one primary research role,
- explicitly defined secondary roles,
- known limitations,
- dependencies on later phases.

The project will avoid using a dataset for an economic purpose that has not been documented.

---

## 2. Research Period

The primary research period is:

**1993–2018 inclusive**

subject to:

- actual source coverage,
- historical security availability,
- valid observation dates,
- dataset-specific coverage.

The microstructure data regimes are:

| Period | Regime |
|---|---|
| 1993–2012 | TAQ |
| 2013–2018 | TAQM |

The TAQ/TAQM transition is treated as a potential measurement and market-structure regime change.

---

# 3. CRSP Data Sources

## 3.1 CRSP Daily Stock File

### Primary role

Daily security-level market observations.

### Primary uses

- daily price
- daily return
- daily volume
- daily market capitalization
- daily bid/ask information where appropriate
- daily trading activity
- daily security characteristics
- linkage to historical security identifiers

### Secondary uses

- validation against other CRSP datasets
- historical security availability checks
- daily market-state variables
- construction of lagged explanatory variables

### Important fields

Examples include:

- PERMNO
- PERMCO
- Ticker
- CUSIP
- CUSIP9
- PrimaryExch
- SecurityType
- SecuritySubType
- ShareType
- SICCD
- NAICS
- DlyCalDt
- DlyPrc
- DlyRet
- DlyRetx
- DlyVol
- DlyCap
- DlyBid
- DlyAsk
- DlyOpen
- DlyHigh
- DlyLow
- DlyClose
- DlyNumTrd
- ShrOut

### Methodological note

This dataset is the primary daily CRSP observation layer, but it is not automatically treated as the source of every derived liquidity or microstructure variable.

---

# 4. CRSP Names

## Primary role

Historical security master/reference dataset.

## Primary uses

- security identity
- security classification
- historical identifier validity
- security start/end dates
- exchange classification
- share/security type
- issuer information

## Secondary uses

- validation of Daily Stock File identifiers
- historical universe construction
- identifier conflict diagnostics

## Important principle

CRSP Names should be treated as a historical reference layer rather than merely a lookup table for current ticker symbols.

The validity intervals must be respected.

---

# 5. CRSP Delisting Information

## Primary role

Historical delisting-event and delisting-return information.

## Primary uses

- delisting-event identification
- terminal security-state identification
- delisting-return incorporation
- survivorship-bias control

## Secondary uses

- validation of security end dates
- investigation of extreme terminal observations
- corporate-event interpretation

## Methodological principle

A security disappearing from the daily dataset must not automatically be classified as missing data.

It may represent a genuine delisting event.

Delisted securities must remain available for historical analysis where economically appropriate.

---

# 6. CRSP Distribution Information

## Primary role

Corporate distribution and corporate-action interpretation.

## Primary uses

- dividends
- distributions
- distribution dates
- distribution amounts
- factor information
- security relationships associated with distributions

## Secondary uses

- validation of return adjustments
- investigation of unusual price movements
- corporate-action diagnostics

## Methodological principle

The project should not create an independent corporate-action adjustment methodology merely because distribution data are available.

CRSP-adjusted variables should remain the primary return framework where appropriate.

Distribution data are primarily used to understand, validate, and diagnose corporate actions.

---

# 7. CRSP Share Outstanding

## Primary role

Historical shares-outstanding information.

## Primary uses

- share-count history
- market-cap validation
- turnover calculations
- share-count change diagnostics

## Secondary uses

- corporate-action validation
- comparison against Daily Stock File share counts
- investigation of discontinuities

## Methodological principle

Share counts are time-varying.

The project must not assume that a single contemporary share count represents the historical security.

---

# 8. CRSP Monthly Stock File

## Primary role

Independent monthly validation layer.

## Primary uses

- monthly aggregation validation
- return validation
- market-cap validation
- volume validation
- robustness analysis

## Secondary uses

- independent checks of daily-to-monthly aggregation
- monthly research specifications where appropriate

## Methodological principle

The Monthly Stock File should not simply duplicate the Daily Stock File calculations without purpose.

It provides an independent validation reference.

---

# 9. CRSP Daily Stock Market Indexes

## Primary role

Daily market-level controls and benchmarks.

## Primary uses

- market returns
- value-weighted market conditions
- equal-weighted market conditions
- S&P 500 benchmark
- daily market regime variables

## Secondary uses

- market-control variables
- event/regime analysis
- execution-cost conditioning

Potential variables include:

- VWRETD
- VWRETX
- EWRETD
- EWRETX
- VWTOTVAL
- EWTOTVAL
- SPRTRN
- SPINDX

Exact capitalization/field naming should follow the supplied source schema.

---

# 10. CRSP Monthly Stock Market Indexes

## Primary role

Monthly market-level validation and robustness.

## Primary uses

- monthly market returns
- validation against daily aggregation
- longer-horizon market controls

## Secondary uses

- monthly robustness analyses
- regime classification

---

# 11. TAQ

## Primary role

Historical intraday market-microstructure information for 1993–2012.

## Intended uses

Potentially:

- quote information
- trade information
- spread measures
- effective spread
- realized spread
- depth
- signed order flow
- OFI
- price impact
- intraday volatility
- trading activity

---

# 12. TAQM

## Primary role

Historical intraday market-microstructure information for 2013–2018.

## Intended uses

Potentially:

- quote information
- trade information
- spread measures
- effective spread
- realized spread
- depth
- signed order flow
- OFI
- price impact
- intraday volatility
- trading activity

---

# 13. Data Provenance Requirement

Every final derived variable should eventually have metadata containing:

| Metadata | Requirement |
|---|---|
| Variable name | Required |
| Economic definition | Required |
| Source dataset | Required |
| Source field(s) | Required |
| Transformation | Required |
| Units | Required |
| Observation date | Required |
| Information timestamp/cutoff | Required where relevant |
| Lookback window | Required where relevant |
| Missing-value rule | Required |
| Outlier rule | Required |
| Validation test | Required |
| Code/version reference | Required |

---

# 14. Source-of-Truth Principle

Where multiple CRSP files contain similar information, the project should designate one primary source and use the others for validation.

This avoids silently combining conflicting definitions.

---

# 15. Deferred Decisions

The following remain intentionally unresolved:

- Trade-signing methodology
- Quote/trade matching methodology
- Depth construction
- OFI formula
- Exact realized-spread horizon
- Exact intraday volatility methodology

These decisions belong primarily to Phase 5–7.

---

# 16. Dependency on Later Phases

Phase 1:
- inventory files
- inspect schemas
- establish metadata

Phase 2–4:
- validate and construct CRSP universes

Phase 6:
- integrate CRSP and microstructure data

Phase 7:
- construct final microstructure variables
