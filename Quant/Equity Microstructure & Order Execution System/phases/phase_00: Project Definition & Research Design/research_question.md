# Research Questions & Hypotheses

## Central Research Objective

Estimate and explain expected execution cost as a function of:

- security characteristics,
- liquidity,
- volatility,
- spread,
- order-flow conditions,
- order size,
- participation rate,
- market regime,
- execution policy.

The framework should ultimately connect daily CRSP characteristics with aggregated intraday TAQ/TAQM information.

---

## RQ1 — Daily Market-Microstructure Conditions

**Question:** How do market-microstructure conditions vary across securities, liquidity states, and historical market regimes?

Candidate outcomes include:

- quoted spread
- effective spread
- realized spread
- depth
- trading volume
- trade count
- volatility
- order-flow measures

**Hypothesis:** Microstructure conditions exhibit substantial cross-sectional and temporal heterogeneity.

---

## RQ2 — Spread and Price-Impact Decomposition

**Question:** How are quoted, effective, realized spreads and price impact related?

**Hypothesis:** These measures capture economically distinct components of trading cost and should not be treated as interchangeable.

---

## RQ3 — Order-Flow Imbalance

**Question:** How does order-flow imbalance relate to price movement and liquidity?

**Hypothesis:** Stronger signed imbalance is associated with stronger price movement, with the relationship depending on liquidity and volatility.

---

## RQ4 — Kyle's Lambda

**Question:** How does price sensitivity to signed order flow vary across securities and market conditions?

**Hypothesis:** Kyle's lambda is generally larger for less-liquid and more volatile securities/regimes.

---

## RQ5 — Order Size Relative to Liquidity

**Question:** How does execution cost scale with order size relative to available liquidity?

**Hypothesis:** Execution cost rises as order size becomes large relative to ADV and available liquidity.

---

## RQ6 — Nonlinear Market Impact

**Question:** Is market impact nonlinear in order size or participation?

Candidate specifications:

- linear
- log-linear
- power-law
- piecewise
- interaction models
- quantile specifications

**Hypothesis:** A nonlinear relationship will better describe a broad range of institutional order sizes.

---

## RQ7 — Implementation Shortfall

**Question:** How does implementation shortfall vary with volatility, liquidity, spread, and order size?

**Hypothesis:** Expected cost and execution uncertainty increase under adverse liquidity/volatility conditions and higher participation.

---

## RQ8 — Strategy-Cost Robustness

**Question:** How much do realistic execution costs reduce naive strategy returns?

**Hypothesis:** High-turnover and low-liquidity strategies will experience materially larger performance degradation.

---

## RQ9 — TAQ vs TAQM

**Question:** Do microstructure relationships differ between the TAQ and TAQM eras?

**Hypothesis:** Differences may exist, but they cannot automatically be interpreted as economic regime changes because measurement definitions and data coverage may also differ.

---

## RQ10 — Historical Generalization

**Question:** Are relationships discovered in the 33-security development universe robust across the broader historical CRSP universe?

**Hypothesis:** Directional relationships should generalize, while coefficient magnitudes and distributions may differ.

---

# Cross-Cutting Hypotheses

### H1 — Liquidity
Lower liquidity is associated with wider spreads and greater price impact.

### H2 — Volatility
Higher volatility is associated with greater execution uncertainty and potentially greater market impact.

### H3 — Relative Order Size
Higher order size relative to liquidity increases expected execution cost.

### H4 — Nonlinearity
Execution cost is not globally linear in order size/ADV.

### H5 — Regime Dependence
Microstructure relationships vary across historical regimes.

### H6 — Security Heterogeneity
Security-specific characteristics remain important after controlling for common market conditions.

### H7 — Timing
Using information unavailable at the decision time creates biased execution-cost estimates.

---

# Interpretation Rules

1. Association does not imply causation.
2. Statistical significance does not imply economic significance.
3. Regime differences must be distinguished from measurement changes.
4. Predictive performance must be assessed out of sample.
5. Economic magnitudes should accompany statistical tests.
6. Exploratory findings must be distinguished from pre-specified hypotheses.
