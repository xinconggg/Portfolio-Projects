# Preliminary Microstructure Variable Specification

## 1. Purpose

This document defines the economic meaning of the major market-microstructure variables.

It deliberately does **not** assign exact TAQ/TAQM field names.

Those mappings will be determined after schema inspection in Phase 5.

---

# 2. Price and Quote Concepts

## 2.1 Bid

The best available displayed buying price at the relevant observation time.

## 2.2 Ask

The best available displayed selling price at the relevant observation time.

## 2.3 Midpoint

Conceptually:

```text
Midpoint = (Bid + Ask) / 2
```

The actual implementation must define treatment of:

- missing quotes
- stale quotes
- locked markets
- crossed markets
- quote timestamps

---

# 3. Quoted Spread

Absolute quoted spread:

```text
Ask - Bid
```

It represents the displayed price difference between the best ask and best bid.

---

# 4. Relative Quoted Spread

A normalized spread measure.

Conceptually:

```text
Relative Spread = (Ask - Bid) / Price Reference
```

The price reference must be selected consistently.

Possible reference:

- midpoint
- bid
- ask

The final choice will be documented after reviewing the available data and research convention.

---

# 5. Effective Spread

Effective spread measures the cost of a transaction relative to the contemporaneous midpoint.

Conceptually:

```text
Effective Spread = 2 × Direction × (Execution Price - Midpoint)
```

where transaction direction determines whether the execution occurred above or below the midpoint.

The exact signing and quote-matching procedure is deferred until Phase 5.

---

# 6. Realized Spread

Realized spread measures the portion of execution-price deviation that remains after a specified future horizon.

Conceptually:

```text
Realized Spread = 2 × Direction × (Execution Price - Future Midpoint)
```

The final methodology must specify:

- future horizon
- quote reference
- trade direction
- treatment of missing future quotes

---

# 7. Price Impact

Price impact represents the adverse price movement associated with trading.

Potential measures include:

- contemporaneous price response
- short-horizon post-trade price movement
- permanent price impact
- regression-based price response

The final measure must distinguish price impact from spread cost.

---

# 8. Depth

Depth represents available displayed quantity at one or more quote levels.

Candidate measures include:

- best-bid depth
- best-ask depth
- two-sided depth
- multi-level depth

The available depth fields are unknown until TAQ/TAQM schema inspection.

---

# 9. Trading Activity

Potential variables:

- share volume
- dollar volume
- number of trades
- average trade size
- turnover
- ADV

ADV must be constructed with an explicit:

- lookback period
- information cutoff
- missing-data rule

---

# 10. Order Flow

Order flow represents signed trading activity.

Candidate measures:

- signed volume
- buy volume
- sell volume
- buy-minus-sell volume
- trade imbalance

The trade-signing methodology must be explicitly documented.

---

# 11. Order Flow Imbalance

OFI is intended to capture changes in buying and selling pressure using quote/trade information.

The exact formula is **not selected in Phase 0**.

Before selection, Phase 5 must establish:

- available quote fields
- available depth fields
- timestamp resolution
- update frequency
- trade information
- market-state conventions

---

# 12. Kyle's Lambda

Conceptually:

```text
ΔPrice_t = α + λ × SignedOrderFlow_t + ε_t
```

where:

- `λ` = price sensitivity to signed order flow

Lambda can be interpreted as an inverse-liquidity/price-impact measure.

The final specification must define:

- price interval
- order-flow interval
- units
- scaling
- estimation window
- minimum observations
- treatment of zero-flow periods
- outlier treatment
- estimator

---

# 13. Volatility

Candidate measures:

### Daily volatility

Derived from daily returns.

### Rolling volatility

Historical volatility over a specified lookback.

### Intraday realized volatility

Constructed from intraday price information.

### Range-based volatility

Based on high/low information where appropriate.

The final measure depends on the research question and timing requirements.

---

# 14. Liquidity

Liquidity is multidimensional.

Potential dimensions:

- spread
- depth
- dollar volume
- turnover
- trade frequency
- market capitalization
- price impact

No single measure should automatically be treated as the complete definition of liquidity.

---

# 15. Market Controls

Potential controls:

- CRSP value-weighted market return
- CRSP equal-weighted market return
- S&P 500 return
- market volatility
- market trading activity
- market regime

---

# 16. Microstructure Regime

At minimum:

```text
1993–2012 → TAQ
2013–2018 → TAQM
```

Additional market-structure regime indicators may eventually include:

- decimalization
- Reg NMS
- exchange fragmentation
- odd-lot changes
- reporting changes

These should be treated as potential explanatory variables rather than automatically interpreted as causal breaks.

---

# 17. Variable Metadata

Each final variable must document:

- economic definition
- mathematical definition
- units
- source
- source fields
- aggregation interval
- timestamp convention
- information class
- lookback
- missing-value rule
- outlier rule
- validation tests

---

# 18. Deferred Decisions

The following cannot be finalized until Phase 5:

- exact TAQ/TAQM fields
- exact quote/trade matching
- trade-signing algorithm
- OFI implementation
- depth methodology
- realized-spread horizon
- intraday volatility estimator
- treatment of odd lots
- locked/crossed quote handling
