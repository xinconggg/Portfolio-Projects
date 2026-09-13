# Statistical & Validation Framework

## 1. Purpose

Establish the standards used to evaluate empirical relationships, transaction-cost models, execution models, and robustness.

---

# 2. Statistical vs Economic Significance

The project will distinguish:

### Statistical significance

Whether an estimated relationship is unlikely to arise from sampling variation under the model assumptions.

### Economic significance

Whether the magnitude is meaningful for actual trading and execution.

A statistically significant effect may still be economically irrelevant.

---

# 3. Candidate Model Families

Depending on the research question:

- pooled regression
- security fixed effects
- date fixed effects
- two-way fixed effects
- cross-sectional regression
- Fama-MacBeth-style estimation
- nonlinear regression
- quantile regression
- predictive machine-learning models where justified

The simplest defensible model should be preferred.

---

# 4. Fixed Effects

Potential fixed effects include:

- security
- date
- market regime

The choice must correspond to the research question.

Fixed effects should not be added automatically merely to improve fit.

---

# 5. Standard Errors

Potential approaches:

- heteroskedasticity-robust
- security-clustered
- date-clustered
- two-way clustered

The clustering structure must reflect the expected dependence in the data.

---

# 6. Temporal Validation

Predictive models must preserve chronology.

A conceptual split is:

```text
Early history
    ↓
Training

Later history
    ↓
Validation

Final unseen history
    ↓
Test
```

Exact boundaries will be chosen after understanding sample coverage.

---

# 7. No Random Row-Level Splitting

Randomly distributing observations across train/test sets is generally inappropriate because:

- adjacent dates are dependent
- the same security appears repeatedly
- market regimes persist
- future information can indirectly enter training

---

# 8. Out-of-Sample Metrics

Depending on the model:

- MAE
- RMSE
- median absolute error
- mean prediction error
- bias
- R² where appropriate
- rank correlation
- calibration
- tail error

For execution models, cost-in-basis-points error should be emphasized.

---

# 9. Economic Validation

Expected relationships should be tested.

Examples:

```text
higher spread
      ↓
higher execution cost
```

```text
lower liquidity
      ↓
higher impact
```

```text
larger order / ADV
      ↓
higher expected cost
```

```text
higher volatility
      ↓
greater execution uncertainty
```

Unexpected relationships require investigation.

They should not simply be filtered away.

---

# 10. Robustness Dimensions

At minimum:

- TAQ vs TAQM
- Tier 1 vs Tier 2
- large vs small securities
- high vs low liquidity
- high vs low volatility
- different order-size buckets
- alternative lookback windows
- alternative outlier treatments
- alternative model specifications

---

# 11. Multiple Testing

The project will distinguish:

### Primary hypotheses

Specified before empirical testing.

### Secondary hypotheses

Pre-specified but less central.

### Exploratory analyses

Discovered through empirical investigation.

The interpretation of statistical significance should account for multiple comparisons where appropriate.

---

# 12. Missing Data

Missingness must be classified.

Potential categories:

- structurally unavailable
- security not trading
- data source missing
- invalid observation
- not applicable

The project should not automatically impute missing market-microstructure data.

---

# 13. Outliers

Outliers should be investigated before removal.

Possible approaches:

- no transformation
- winsorization
- trimming
- robust regression
- log transformation
- regime-specific treatment

Any selected treatment must be documented.

---

# 14. Model Stability

Model results should be examined across:

- time
- securities
- liquidity
- market capitalization
- volatility
- TAQ/TAQM regimes

A model that works only in one narrow regime should not be presented as universally valid.

---

# 15. Reproducibility

Every empirical result must be traceable to:

- source-data version
- sample definition
- filtering rules
- feature construction
- model specification
- software environment
- configuration
- random seed where applicable

---

# 16. Validation Hierarchy

Validation should proceed from:

```text
Data validity
      ↓
Variable validity
      ↓
Economic plausibility
      ↓
Statistical validity
      ↓
Out-of-sample validity
      ↓
Robustness
      ↓
Economic usefulness
```

A model should not be considered successful merely because it produces a high in-sample R².
