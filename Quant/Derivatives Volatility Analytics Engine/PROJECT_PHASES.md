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
Project_Root/
│
├── README.md
├── requirements.txt
├── .gitignore
│
├── data/
│   └── README.md
│
├── research/
│   ├── 01_data_quality/
│   │   ├── README.md
│   │   ├── 01_raw_data_profile.ipynb
│   │   ├── 02_data_quality_analysis.ipynb
│   │   └── checks
|   |        └── 01_ingestion_check.ipynb
│   └── README.md
│
├── src/
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   │
│   │   ├── raw/
│   │   │   └── SPY/
│   │   │       ├── 2010/
│   │   │       │   ├── spy_eod_201001.txt
│   │   │       │   ├── spy_eod_201002.txt
│   │   │       │   ├── ...
│   │   │       │   └── spy_eod_201012.txt
|   |   |       ├── ...
│   │   │       └── 2023
│   │   │             └── ...
│   │   ├── processed/
│   │   │   └── SPY/...
│   │   │
│   │   ├── external/
│   │   │
│   │   ├─ ingestion.py
│   │   │
│   │   ├─ schema.py
│   │   │
│   │   └── quality_checks.py
│   │
│   ├── pricing/
│   │   └── __init__.py
│   │
│   ├── volatility/
│   │   └── __init__.py
│   │
│   ├── calibration/
│   │   └── __init__.py
│   │
│   ├── greeks/
│   │   └── __init__.py
│   │
│   ├── portfolio/
│   │   └── __init__.py
│   │
│   ├── hedging/
│   │   └── __init__.py
│   │
│   ├── execution/
│   │   └── __init__.py
│   │
│   ├── backtesting/
│   │   └── __init__.py
│   │
│   ├── statistics/
│   │   └── __init__.py
│   │
│   └── utils/
│       └── __init__.py
│
└── tests/
    ├── test_data_quality.py
    ├── test_data_loader.py
    └── test_quote_metrics.py
```

### Phase 1 Sub-Phases:
- **Phase 1.1:** Raw Data Profiling
- **Phase 1.2:** Schema & Type Normalization
- **Phase 1.3:** Vendor Convention Audit
- **Phase 1.4:** Timestamp / Contract Normalization
- **Phase 1.5:** Quote Quality
- **Phase 1.6:** Liquidity Quality
- **Phase 1.7:** Financial Consistency
- **Phase 1.8:** Forward / Maturity Framework
- **Phase 1.9:** Derived Volatility Variables
- **Phase 1.10:** Research Dataset
- **Phase 1.11:** Formal Data Quality Report

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

**3) DTE**

Given the following columns in our dataset:
```text
DTE
EXPIRE_DATE
EXPIRE_UNIX
QUOTE_READTIME
```
We should not automatically trust `DTE`, instead we can calculate our own DTE then compare against the vendor's DTE, for example:

$$
T = \frac{t_{\mathrm{expiry}} - t_{\mathrm{quote}}}{\text{year basis}}
$$

Comparison of the DTEs might reveal:
- rounding
- timezone issues
- trading-day conventions
- expiration-time conventions

### Phase 1.1 Checklist

Before moving on, we need to know:
- [ ] exact row & column count
- [ ] data types
- [ ] date coverage
- [ ] missingness
- [ ] duplicate structure
- [ ] quote structure
- [ ] volume structure
- [ ] contract structure
- [ ] timestamp behavior
- [ ] IV units
- [ ] greek units
- [ ] preliminary anomalies
