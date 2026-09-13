# Universe & Identifier Specification

## 1. Purpose

This document defines the security universe architecture and identifier hierarchy.

The central principle is:

> Historical eligibility and security identity must be determined from historical CRSP information rather than current identifiers or surviving securities.

---

# 2. Tier 1 — Fixed Computational Universe

The Tier 1 development universe contains 33 securities:

### Technology / Communication

- AAPL
- MSFT
- AMZN
- GOOGL
- GOOG
- META
- NVDA
- INTC
- CSCO
- ORCL

### Financials

- JPM
- BAC
- GS
- MS
- WFC
- C

### Energy

- XOM
- CVX

### Consumer / Retail

- WMT
- HD
- KO
- PEP

### Healthcare

- JNJ
- PFE
- UNH

### Payments

- V
- MA

### Media / Industrials

- DIS
- NFLX
- GE

### ETFs

- SPY
- QQQ
- IWM

---

# 3. Tier 1 Interpretation

Tier 1 is a:

> **fixed computational/development universe**

It is not a claim that all 33 securities existed throughout 1993–2018.

For each security:

```text
Research membership
        ≠
Historical availability
```

A security is included in a given date's analytical sample only if CRSP supports its historical existence and eligibility.

---

# 4. Historical Eligibility

For security `s` and date `t`:

```text
Tier1Member(s) = True
```

does not imply:

```text
Eligible(s,t) = True
```

Historical eligibility must respect:

- security inception
- security termination
- CRSP security information
- trading status
- security type
- share type
- relevant research-universe rules

No observations should be fabricated before a security existed.

---

# 5. Tier 2 — Historical CRSP Universe

Tier 2 represents the broader:

> **historical, date-dependent CRSP security universe**

The exact eligibility filters will be finalized during the relevant CRSP-universe phases after the actual CRSP classification fields are inspected.

The universe must preserve:

- historical securities
- delisted securities
- historical identifiers
- historical start/end dates
- relevant security classifications

---

# 6. Survivorship Principle

The project must not construct Tier 2 using:

> securities surviving at the end of 2018.

Nor should it use:

> today's constituents backfilled into the historical sample.

Instead:

```text
Eligible securities at date t
=
securities historically eligible at date t
```

---

# 7. Primary Identifier

## PERMNO

PERMNO is the primary security-level research identifier.

It should be used as the principal key for:

- CRSP joins
- historical panels
- security-level modeling
- microstructure integration
- execution research

---

# 8. Company-Level Identifier

## PERMCO

PERMCO identifies the CRSP company/issuer grouping.

It should be used when the research question explicitly concerns:

- issuer-level aggregation
- company-level exposure
- multiple securities belonging to one issuer

PERMCO should not replace PERMNO when the research object is the individual security.

---

# 9. Ticker

Ticker is a descriptive trading identifier.

Ticker must not be treated as a stable longitudinal security key.

A ticker can:

- change
- be reused
- differ across historical periods
- fail to uniquely identify a security through corporate events

---

# 10. CUSIP / CUSIP9

CUSIP fields are useful historical identifiers and validation attributes.

They should not replace PERMNO as the primary longitudinal identifier.

CUSIP changes must be interpreted using CRSP security-reference information.

---

# 11. Trading Symbol

Trading symbol is treated similarly to ticker:

- descriptive
- potentially time-varying
- useful for presentation
- unsuitable as the sole historical key

---

# 12. Identifier Hierarchy

The conceptual hierarchy is:

```text
PERMNO
  │
  ├── security-level research identity
  │
  ├── historical ticker/trading symbol
  │
  ├── historical CUSIP/CUSIP9
  │
  └── PERMCO
          │
          └── issuer/company grouping
```

---

# 13. Identifier Rules

1. Join longitudinal security data primarily through PERMNO.
2. Use PERMCO only for issuer-level questions.
3. Never assume ticker continuity.
4. Never infer security identity solely from ticker.
5. Never infer security continuity solely from CUSIP.
6. Historical identifier intervals must be respected.
7. Identifier conflicts must be logged.
8. Mapping decisions must be reproducible.

---

# 14. Tier 1 Mapping

The eventual Tier 1 mapping should produce:

```text
research_symbol
        ↓
PERMNO
        ↓
historical valid date interval
```

The mapping must support:

- ticker changes
- multiple historical identifiers
- security inception
- security termination
- corporate events

---

# 15. ETFs

SPY, QQQ and IWM are part of Tier 1.

They must not automatically be treated as equivalent to common operating companies.

ETF-specific behavior should be documented where it affects:

- liquidity
- trading volume
- spreads
- market impact
- price formation
- interpretation of market microstructure

---

# 16. Deferred Decisions

The following will be finalized during later CRSP phases:

- exact Tier 2 security-type filters
- exact exchange eligibility
- treatment of special security classes
- treatment of ETFs in Tier 2
- treatment of ADRs/foreign issuers
- exact historical trading-status criteria

These should not be guessed before inspecting the relevant CRSP fields.
