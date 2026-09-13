# Transaction Cost & Execution Simulator Specification

## 1. Purpose

Define the conceptual transaction-cost framework and future execution simulator.

The central question is:

> Given a security, market state, order size, direction, and execution policy, what execution cost should reasonably be expected?

---

# 2. Implementation Shortfall

Implementation Shortfall measures the economic difference between the decision/arrival benchmark and the eventual execution outcome.

The framework should decompose cost into:

1. Arrival/decision benchmark
2. Market movement
3. Spread/slippage
4. Market impact
5. Opportunity/delay cost
6. Explicit costs
7. Residual/unexplained cost

---

# 3. Arrival Benchmark

Potential benchmarks include:

- decision price
- arrival midpoint
- arrival quote
- beginning-of-execution market price

The benchmark must be explicitly specified before model estimation.

---

# 4. Market Movement Component

The market may move while an order is being executed.

This component represents the portion of implementation shortfall attributable to market movement rather than execution mechanics.

It must not be double-counted with market impact.

---

# 5. Spread / Slippage Component

This represents the cost associated with executing away from a benchmark midpoint or reference price.

It may include:

- quoted spread
- effective spread
- execution slippage

The decomposition must avoid counting the same cost twice.

---

# 6. Market Impact

Market impact represents the price movement associated with the order's interaction with available liquidity.

Potential explanatory variables:

- order size
- order size / ADV
- participation rate
- volatility
- spread
- depth
- liquidity
- market regime
- order-flow state

---

# 7. Opportunity / Delay Cost

Opportunity cost represents the economic cost associated with:

- incomplete execution
- delayed execution
- unfilled shares
- changing market conditions

Opportunity cost must not automatically be treated as realized transaction cost.

---

# 8. Explicit Costs

Where measurable, the model may incorporate:

- commissions
- exchange fees
- rebates
- taxes
- other explicit trading costs

The availability and consistency of these data must be established before inclusion.

---

# 9. Execution Inputs

Minimum conceptual inputs:

- PERMNO
- date
- order side
- order shares
- order notional
- arrival price
- execution horizon
- ADV
- spread
- volatility
- liquidity
- market regime

Potential adaptive inputs:

- current spread
- realized participation
- intraday volume
- current market movement
- order-flow state

---

# 10. Order-Size Variables

Order size should be represented using multiple scales:

```text
shares
notional
order size / ADV
order size / market capitalization
participation rate
```

Order size relative to liquidity is expected to be more informative than absolute size alone.

---

# 11. Candidate Impact Specifications

The project should compare candidate forms rather than assume one is correct.

### Linear

```text
Cost = α + β × OrderSize + Controls + ε
```

### Log-linear

```text
log(Cost) =
α + β × log(OrderSize) + Controls + ε
```

### Power law

```text
Cost ∝ (OrderSize / ADV)^β
```

### Piecewise

Different cost slopes across participation regimes.

### Interaction model

Impact sensitivity may depend on:

- volatility
- spread
- liquidity
- market regime

---

# 12. Execution Simulator Modes

## Mode A — Ex-post estimator

Estimates conditional cost from observed historical market/execution information.

## Mode B — Static pre-trade simulator

Uses only information available before execution begins.

## Mode C — Adaptive simulator

Updates the state using information observed during execution.

The mode must always be recorded with the simulation output.

---

# 13. Simulator Outputs

For each simulated order:

- expected execution price
- expected total cost
- cost in basis points
- spread/slippage component
- market-impact component
- market-movement component
- opportunity/delay component
- explicit cost where available
- completion rate
- participation rate
- uncertainty/risk estimate

---

# 14. Double-Counting Controls

The implementation must verify that:

- spread is not included twice
- market movement is not counted as impact
- opportunity cost is not counted as realized transaction cost
- explicit fees are not counted both explicitly and implicitly
- impact estimates do not already contain a component added separately

---

# 15. Execution Assumptions

The simulator must eventually define:

- order start time
- order end time
- participation policy
- execution frequency
- allowable market information
- order completion rules
- treatment of partial fills

These choices are deferred until the relevant market-data capabilities are known.

---

# 16. Validation

The simulator should eventually be tested for:

### Statistical validity

- prediction error
- calibration
- out-of-sample performance

### Economic validity

- larger participation should generally not reduce expected cost without a documented mechanism
- lower liquidity should generally imply greater execution difficulty
- wider spreads should generally imply greater execution cost

### Regime stability

Test separately across:

- TAQ
- TAQM
- high/low volatility
- high/low liquidity
- market-cap groups
