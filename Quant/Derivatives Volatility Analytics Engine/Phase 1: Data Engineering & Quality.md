# Phase 1: Data Engineering & Quality
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
- **Phase 1.3:** Structural Integrity Checks
- **Phase 1.4:** Timestamp, Expiration & DTE Validation
- **Phase 1.5:** Contract / Expiration Validation
- **Phase 1.6:** Option Price & IV Validation
- **Phase 1.7:** Greeks Validation
- **Phase 1.8:** Put-Call Parity Diagnostic 
- **Phase 1.9:** Forward / Interest Rate Inputs
- **Phase 1.10:** Liquidity & Tradability Filters
- **Phase 1.11:** Processed Data Construction
- **Phase 1.12:** Final Data Quality Report

## Phase 1.1: Raw Data Profiling
### Research Question
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

### Phase 1.1 Findings
- The January 2010 sample contains **18,668 rows and 33 columns**
- The dataset contains both call and put market data, vendor-provided implied volatility, Greeks, volume, quote sizes, and strike-distance metrics
- Several originally string/object fields contain blank values rather than pandas-level `NaN` values. These include `C_IV`, `C_VOLUME`, `P_IV`, and `P_VOLUME`
- After ingestion and type normalization, these blank values are converted into proper pandas missing values
- The quote timestamp occurs at a single time of **16:00** for all observations in this EOD sample
- The underlying price is constant across all contracts sharing the same quote timestamp
- No duplicate contract keys were identified in the January sample
- The sample contains observations with `DTE = 0`, corresponding to contracts observed on their expiration date
- The dataset contains a substantial number of zero-volume observations and missing-volume observations. These should not automatically be interpreted as equivalent.
- Option bid/ask fields contain zero bids and a smaller number of zero asks. These require separate treatment from missing quotes.
- Vendor IV and Greek fields contain unusual values in some observations, including negative or zero values in fields where such values may require validation. These will be investigated further rather than removed at the raw-data stage.
- The raw dataset should therefore be treated as **source data rather than immediately tradable/clean market data**. Subsequent phases must distinguish between valid observations, missing information, illiquid observations, and potentially erroneous observations.

## Phase 1.2: Schema & Type Normalization
### Research Question
How should the options data be standardized so that it can be reliably processed by downstream pricing, volatility, risk and trading models?

### Objective:
Currently, the raw files contain a mixture of numeric values, blank strings, timestamps, dates and structured quote-size fields.
Before performing any analysis, the dataset should be converted into a consistent structure while preserving the distinction between:
- valid numerical observations
- explicitly reported zero values
- missing observations
- structured string fields that requires further parsing

### Normalization Rules:
**1) Column Names:** Raw column names such as `[QUOTE_UNIXTIME]`, `[UNDERLYING_LAST]` and `[C_BID]` are to be normalized to: `quote_unixtime`, `underlying_last` and `c_bid`, without the brackets, unnecessary whitespaces and converted to lowercase while preserving original semantic meaning

**2) Datetime Fields:** The following fields should be converted to pandas datetime: `quote_readtime`, `quote_date` and `expire_date` while `quote_unixtime` and `expire_unix` should remain as integer

**3) Numeric Fields:** Pricing, Greeks, volatility, contract and underlying fields should be converted to numeric type

**4) Blank Values:** Blank values should be converted to pandas `NaN` rather than to `0`

### Phase 1.2 Checklist
- [ ] standardized column names
- [ ] converted datetime fields
- [ ] converted numeric fields
- [ ] converted blank strings to NaN
- [ ] preserved explicit zero values
- [ ] identified remaining structured string fields
- [ ] confirmed normalized schema
- [ ] confirmed normalized data types

### Findings
- The raw column names were normalized from bracketed uppercase names such as `[QUOTE_READTIME]` to lowercase snake_case names such as `quote_readtime`
- Timestamp fields were successfully converted to pandas datetime types:
  - `quote_readtime`
  - `quote_date`
  - `expire_date`
- Numeric market-data fields were successfully converted to appropriate numeric types
- Previously blank string values in IV, volume, price, and quote fields were converted into proper pandas missing values
- `c_size` and `p_size` remain object/string fields because their values represent quote sizes in a compound format such as `"20 x 20"`
- After normalization, missingness is explicitly represented by pandas `NaN`, allowing subsequent quality checks to distinguish missing observations from valid zero values
- No cleaning or imputation of economically meaningful values was performed at this stage. Missing prices, missing IV, zero bids, zero volume, and other potentially problematic observations remain identifiable for later research decisions.

## Phase 1.3: Structural Integrity Checks
### Research Question
Does the normalized options dataset have structural problems such as duplicated observations, inconsistent identifiers, invalid dates or inconsistent underlying prices that could compromise subsequent analysis?

### Objective:
Before investigating the financial properties of individual option quotes, ensure that the dataset is structurally coherent.

Checks should focus on:
- dataset dimensions
- duplicate observations
- duplicate option contracts
- quote timestamps
- underlying price consistency
- expiration structure
- DTE validity
- basic price validity

### Phase 1.3 Checklist
- [ ] exact duplicate rows checked
- [ ] duplicate contract keys checked
- [ ] quote timestamp structure checked
- [ ] underlying price consistency checked
- [ ] negative DTE checked
- [ ] zero DTE identified
- [ ] negative option prices checked
- [ ] crossed quotes identified
- [ ] zero bid/ask observations identified
- [ ] midpoint calculated
- [ ] bid-ask spread calculated
- [ ] relative spread calculated

## Phase 1.4: Timestamp, Expiration & DTE Validation
### Research Question
Are the quote timestamps, expiration timestamps and vendor-provided `DTE` values internally consistent? What time-to-expiration convention does the dataset actually use?

### Why this phase is important
Time to expiration is fundamental to almost every subsequent component of this project:
- Black-Scholes pricing
- Implied volatility calculation
- Volatility surface construction
- SVI calibration
- Greeks
- Hedging
- Volatility forecasting
- Historical strategy backtesting

A small error in `T` can affect short-dated option pricing and implied volatility. Hence, we should not automatically assume that the vendor-provided `DTE` is correct and should construct time-to-expiration independently from the available timestamps and determine how closely it agrees with the provided value.

### Relevant Raw Columns:
| Category          | Columns                                                              |
| ----------------- | -------------------------------------------------------------------- |
| Quote Timestamp         | `QUOTE_UNIXTIME`, `QUOTE_READTIME`, `QUOTE_DATE`, `QUOTE_TIME_HOURS` |
| Expiration Timestamp        | `EXPIRE_UNIX`, `EXPIRE_DATE`                                                    |
| Vendor time-to-expiration | DTE |

### Phase 1.4 Checklist
- [ ] quote timestamp consistency
- [ ] quote date consistency
- [ ] quote time consistency
- [ ] expiration timestamp consistency
- [ ] expiration date consistency
- [ ] vendor DTE consistency
- [ ] independently calculated DTE
- [ ] vendor vs calculated DTE differences
- [ ] DTE = 0 behavior
- [ ] DTE < 0 behavior
- [ ] same-expiration DTE consistency
- [ ] expiration-date structure
- [ ] final time-to-expiration convention for downstream pricing

### Phase 1.4 Findings
- Vendor DTE is consistent with the difference between `EXPIRE_UNIX` and `QUOTE_UNIXTIME`
- Maximum observed difference is 0.001667 days, which is equivalent to one minute
- Only 2 difference values occur: 0 and 0.001667
- Above point indicates that the vendor DTE is effectively consistent with timestamp-based time-to-expiration, subject to rounding/time precision
- DTE = 0 observations occur when quote and expiration timestamps are identical on expiration date
- No negative DTE observations were found

As such, for downstream pricing the revised formula will be used, rather than relying on the rounded vendor `DTE`:

$$
T_{\mathrm{year}} =
\frac{\mathrm{EXPIRE\_UNIX} - \mathrm{QUOTE\_UNIXTIME}}
{\text{seconds per year}}
$$

## Phase 1.5: Option Price & Market Consistency
### Research Question
Are the observed option prices and quotes economically consistent with the underlying price, strike, time to expiration and basic no-arbitrage relationships?

### Scope
We should investigate four areas:

**1) Option Price Bounds:** For European-style options, using the appropriate discounting assumptions:
  - **European Call (with dividends, else q = 0):** $\max(0, S_0e^{-qT} - Ke^{-rT}) \leq C \leq S_0e^{-qT}$
  - **European Put (with dividends, else q = 0):** $\max(0,  Ke^{-rT} - S_0e^{-qT}) \leq P \leq Ke^{-rT}$
    
**2) Call/Put Quote Relationships:** Examine whether call and put prices behave sensibly relative to each other.  
Eventually, leading to put-call parity: $C - P = S_0e^{-qT} - Ke^{-rT})$

**3) Price Monotonicity:** Option prices should generally exhibit sensible relationships with strike:  
  - **Call:** $K_1 < K_2 \Rightarrow C(K_1) \geq C(K_2)$
  - **Put:** $K_1 < K_2 \Rightarrow P(K_1) \leq P(K_2)$

**4) Vendor IV & Greek Sanity:** Even though the dataset already contains vendor-provided IV and greeks, but before trusting these fields, we have to investigate:
  - negative/zero/extremely-large IV
  - delta outside theoretical ranges
  - call/put delta relationships
  - negative gamma
  - negative/positive vega inconsistencies
  - suspicious Greek values near expiration
  - Greeks associated with missing/invalid quotes

### Phase 1.5 Checklist
- [ ] call/put price lower-bound/upper-bound sanity check
- [ ] identify observations requiring discounting assumptions
- [ ] call/put price monotonicity checked
- [ ] call/put price relationship examined
- [ ] preliminary put-call parity diagnostics
- [ ] negative/zero/extremely-large IV checked
- [ ] call/put delta bounds checked
- [ ] gamma sanity checked
- [ ] vega sanity checked
- [ ] theta sanity checked
- [ ] rho sanity checked
- [ ] vendor Greek anomalies documented
- [ ] no-arbitrage violations separated from data-quality errors
