# Phase 1: Data Engineering
## Phase 1.0: What Phase 1 will Produce
### Aim: 
Produce a research data pipeline

### Pipeline:
```text
                    RAW SPY DATA
                         │
                         ▼
                Schema Validation
                         │
                         ▼
                Type Normalization
                         │
                         ▼
              Timestamp Normalization
                         │
                         ▼
                Contract Identification
                         │
                         ▼
                  Quote Validation
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        Call Validation       Put Validation
              │                     │
              └──────────┬──────────┘
                         ▼
                 Liquidity Filters
                         │
                         ▼
              Financial Consistency
                    Checks
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
     Put-Call Parity                IV / Greeks
       Diagnostics                  Diagnostics
          │                             │
          └──────────────┬──────────────┘
                         ▼
                  Derived Variables
                         │
                         ▼
                 Research Dataset
                         │
                         ▼
              Data Quality Report
```

### Phase 1 Architecture:
``` text
src/
└── data/
    ├── __init__.py
    ├── schema.py
    ├── ingestion.py
    ├── normalization.py
    ├── validation.py
    ├── cleaning.py
    ├── features.py
    └── quality_report.py
```

And:

``` text
research/
└── 01_data_quality/
    ├── README.md
    ├── 01_data_profile.ipynb
    ├── 02_quality_analysis.ipynb
    ├── figures/
    └── tables/
```

### Phase 1 Sub-Phases:
- **Phase 1.1:** Raw Data Profiling
- **Phase 1.2:** Schema & Type Normalization
- **Phase 1.3:** Timestamp / Contract Normalization
- **Phase 1.4:** Quote Quality
- **Phase 1.5:** Liquidity Quality
- **Phase 1.6:** Financial Consistency
- **Phase 1.7:** Forward / Maturity Framework
- **Phase 1.8:** Derived Volatility Variables
- **Phase 1.9:** Research Dataset
- **Phase 1.10:** Formal Data Quality Report

## Phase 1.1: Raw Data Profiling
### Research Question:
What exactly is contained within the SPY options dataset and what data quality problems could affect subsequent volatility research?

### Raw Schema:
For now, columns can be classified as such:
| Category          | Columns                                                              |
| ----------------- | -------------------------------------------------------------------- |
| Timestamp         | `QUOTE_UNIXTIME`, `QUOTE_READTIME`, `QUOTE_DATE`, `QUOTE_TIME_HOURS` |
| Underlying        | `UNDERLYING_LAST`                                                    |
| Contract          | `EXPIRE_DATE`, `EXPIRE_UNIX`, `DTE`, `STRIKE`                        |
| Call Greeks       | `C_DELTA`, `C_GAMMA`, `C_VEGA`, `C_THETA`, `C_RHO`                  |
| Call IV            | `C_IV`                                                               |
| Call Market Data  | `C_VOLUME`, `C_LAST`, `C_SIZE`, `C_BID`, `C_ASK`                    |
| Put Market Data   | `P_BID`, `P_ASK`, `P_SIZE`, `P_LAST`, `P_VOLUME`                    |
| Put Greeks        | `P_DELTA`, `P_GAMMA`, `P_VEGA`, `P_THETA`, `P_RHO`                  |
| Put IV            | `P_IV`                                                               |
| Strike Metrics    | `STRIKE_DISTANCE`, `STRIKE_DISTANCE_PCT`                             |

### Important Observations to look for in Sample:
**1) Quote Validation**
- **Bad:** Bid < 0 or Ask < 0
- **Invalid Crossed Market:** Bid > Ask
- **Potentially Valid:** Bid = 0 or Ask > 0
- **Totally Valid:** 0 < Bid ≤ Ask

**2) Option Price Bounds**

Let:
- **$S_0$ =** Current Underlying Price
- **K =** Strike Price
- **T =** Time to Expiration
- **r =** Continuously-compounded Risk-free Rate
- **q =** Continuous Dividend Yield
- **C =** European Call Price
- **P =** European Put Price

**European Call (with dividends, else q = 0):** $\max(0, S_0e^{-qT} - Ke^{-rT}) \leq C \leq S_0e^{-qT}$

**European Put (with dividends, else q = 0):** $\max(0,  Ke^{-rT} - S_0e^{-qT}) \leq P \leq Ke^{-rT}$

9 
