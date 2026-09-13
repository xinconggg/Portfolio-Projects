# Information Timing & Bias-Control Framework

## 1. Purpose

This document establishes the information set available to research models and execution decisions.

The central rule is:

> A variable cannot be used as a decision input unless the information would have been available at the modeled decision time.

---

# 2. Information Classes

## 2.1 Pre-Trade Information

Information available before execution begins.

Examples may include:

- prior-day price
- prior-day volume
- historical ADV
- lagged volatility
- lagged spread
- historical liquidity
- historical market returns
- historical market volatility

These variables are generally eligible for pre-trade models, subject to exact timestamps and lookback construction.

---

## 2.2 During-Trade Information

Information revealed while the order is being executed.

Examples may include:

- observed intraday volume
- current spread
- current midpoint
- realized participation
- contemporaneous market movement
- contemporaneous order-flow state

These variables may be used only by a simulator explicitly designed to model adaptive execution.

---

## 2.3 Post-Trade Information

Information known only after execution.

Examples:

- final daily volume
- end-of-day realized spread
- future return
- future volatility
- final execution outcome

These may be used for:

- evaluation
- labels
- ex-post analysis
- validation

They must not silently become decision inputs.

---

# 3. Look-Ahead Bias

Look-ahead bias occurs when information from the future enters a decision or prediction that supposedly occurs earlier.

Examples include:

- using same-day closing volume to predict a morning execution
- using future volatility in a pre-trade model
- using future returns as predictors
- calculating rolling statistics using observations after the decision timestamp

---

# 4. Rolling-Window Rule

For a decision at time `t`:

```text
Feature(t)
=
function(
    observations strictly available by t
)
```

A rolling statistic must not include future observations.

---

# 5. Daily Aggregation Rule

Daily variables require an explicit timing interpretation.

For example:

### Prior-day ADV

Potentially valid for beginning-of-day execution.

### Same-day final ADV

Not valid as a beginning-of-day predictor.

### Intraday realized volume

Potentially valid for an adaptive execution algorithm if the simulator observes it sequentially.

---

# 6. Execution Modes

The project should distinguish three execution-model modes.

### Mode A — Ex-post estimator

Uses observed execution information to estimate historical cost.

### Mode B — Static pre-trade simulator

Uses only information known before execution.

### Mode C — Adaptive simulator

Uses information revealed during execution according to a predefined observation/update schedule.

The distinction must be explicit in all empirical outputs.

---

# 7. Survivorship Bias

Controls:

- date-dependent universe
- historical security eligibility
- inclusion of delisted securities
- historical identifiers
- delisting returns
- no current-constituent backfill

---

# 8. Delisting Bias

A delisted security should not disappear from the research sample simply because it no longer trades.

Where the research outcome requires it:

- retain the historical observations
- identify the delisting event
- incorporate appropriate delisting return information
- document the terminal observation

---

# 9. Corporate-Action Bias

Corporate events can create large apparent price movements.

Potential events include:

- stock splits
- reverse splits
- dividends
- distributions
- mergers
- acquisitions
- security substitutions

The project should distinguish corporate-action effects from genuine market-microstructure effects.

---

# 10. Selection Bias

Potential selection mechanisms must be documented.

Examples:

- minimum trading volume
- minimum observation count
- minimum price
- minimum market capitalization
- data availability
- valid quote requirements

Filters should not be introduced merely because they improve model results.

---

# 11. Temporal Leakage

Predictive models must use chronological validation.

Preferred structure:

```text
Historical period
       ↓
Training
       ↓
Validation
       ↓
Test
```

Random row-level train/test splitting is generally inappropriate for this project.

---

# 12. Measurement-Regime Bias

The transition:

```text
1993–2012 → TAQ
2013–2018 → TAQM
```

may contain:

- true market-structure changes
- reporting changes
- data-definition changes
- coverage changes
- methodological differences

Therefore a coefficient difference between eras cannot automatically be interpreted as an economic causal effect.

---

# 13. Data-Quality vs Economic Extremes

Extreme values should not automatically be removed.

Potential legitimate extremes:

- market stress
- genuine illiquidity
- corporate events
- large price movements

Potential data-quality errors:

- impossible prices
- malformed timestamps
- invalid quotes
- crossed markets
- stale observations
- duplicate records

The pipeline must distinguish these categories.

---

# 14. Information-Set Metadata

Final derived variables should eventually record:

- observation date
- observation timestamp where available
- information cutoff
- lookback period
- whether pre-trade/during-trade/post-trade
- source dataset
- source fields

---

# 15. Required Model Documentation

Every predictive/execution model must state:

1. Decision timestamp
2. Prediction horizon
3. Available information
4. Excluded future information
5. Feature construction window
6. Target construction window
7. Validation methodology
