# Phase 0 — Project Definition & Research Design

## 1. Objective

Formalize the research problem, research questions, data roles, universe definitions, identifier hierarchy, information-timing rules, bias controls, microstructure-variable definitions, transaction-cost framework, execution-simulator specification, statistical-validation principles, and phase-gate criteria for the Market Microstructure & Order Execution System.

Phase 0 is a **design and specification phase**. It does not process the large CRSP or TAQ/TAQM datasets.

## 2. Scope

### In scope

- Research objective formalization
- Research questions and hypotheses
- CRSP data-role mapping
- Tier 1 and Tier 2 universe specification
- PERMNO/PERMCO/ticker/CUSIP identifier architecture
- Temporal and information-availability framework
- Survivorship and look-ahead controls
- Corporate-action and delisting framework
- Preliminary microstructure-variable taxonomy
- Transaction-cost / Implementation Shortfall framework
- Execution-simulator specification
- Statistical-validation principles
- Phase-gate criteria

### Out of scope

- Raw-file ingestion
- Large-file cleaning
- TAQ/TAQM field mapping
- Final microstructure variable construction
- Empirical estimation
- Transaction-cost model estimation
- Execution simulation
- Strategy backtesting
- Final empirical conclusions

## 3. Required Sub-Phases

- [ ] 0.1 Research Objective Formalization
- [ ] 0.2 Research Questions & Hypotheses
- [ ] 0.3 Data Architecture
- [ ] 0.4 Universe Definition
- [ ] 0.5 Identifier Architecture
- [ ] 0.6 Temporal & Information Architecture
- [ ] 0.7 Bias-Control Framework
- [ ] 0.8 Microstructure Variable Specification
- [ ] 0.9 Transaction-Cost Framework
- [ ] 0.10 Execution Simulator Specification
- [ ] 0.11 Statistical/Validation Framework
- [ ] 0.12 Phase-Gate Review

## 4. Core Design Principles

1. **PERMNO-first security identity.**
2. Historical eligibility is date-dependent.
3. Tier 1 is a computational universe, not a survivorship-based historical universe.
4. Tier 2 must preserve historically existing securities, including securities that later delisted.
5. Delisting events must not be silently treated as missing data.
6. CRSP-adjusted return variables are primary return inputs where appropriate.
7. Corporate-action files are used for validation and interpretation.
8. TAQ and TAQM are separate measurement regimes.
9. Exact TAQ/TAQM fields must not be invented before schema inspection.
10. Every model variable must have an explicit information-timing classification.
11. Post-trade information cannot silently become a pre-trade model input.
12. Extreme observations must be investigated before filtering.
13. Temporal validation is preferred to random splitting for predictive applications.
14. Raw data remain immutable.
15. Every major methodological decision requires a rationale, alternatives, bias assessment, and validation plan.

## 5. Research Period

Primary period:

**1993–2018 inclusive**

Microstructure regimes:

- 1993–2012: TAQ
- 2013–2018: TAQM

The transition is treated as a potential structural and measurement regime change.

## 6. Data Architecture

CRSP Daily Stock File:
- primary daily security observations
- prices
- returns
- volume
- market capitalization
- quotes
- trading activity

CRSP Names:
- historical security master
- security classifications
- identifier validity intervals
- security status

CRSP Delisting Information:
- delisting events
- delisting returns
- terminal security outcomes

CRSP Distribution Information:
- distributions
- corporate-action interpretation
- validation

CRSP Share Outstanding:
- historical share counts
- share-count validation

CRSP Monthly Stock File:
- independent aggregation checks
- robustness analysis

CRSP Daily/Monthly Market Indexes:
- market controls
- benchmark returns
- regime variables

TAQ/TAQM:
- intraday quote/trade information
- aggregated daily microstructure measures

Exact TAQ/TAQM field mappings are deferred to Phase 5.

## 7. Universe Architecture

### Tier 1

The fixed 33-security development universe is used for:

- prototyping
- debugging
- visualization
- model development
- computational testing

However:

> Membership in Tier 1 does not imply historical existence.

Each security must be historically filtered using CRSP.

### Tier 2

Tier 2 is a dynamic historical CRSP universe.

It must be:

- date-dependent
- identifier-based
- survivorship-bias controlled
- inclusive of historically relevant delisted securities

Current survivors must never be substituted for the historical universe.

## 8. Identifier Architecture

Primary security key:

**PERMNO**

Issuer/company key:

**PERMCO**

Descriptive identifiers:

- ticker
- trading symbol
- CUSIP
- CUSIP9

Rules:

- PERMNO is the longitudinal security key.
- Ticker is never assumed to be stable.
- PERMCO is used only for issuer-level analysis.
- CUSIP changes must not automatically imply a new security.
- Identifier conflicts are logged rather than silently resolved.

## 9. Information-Timing Architecture

Every variable must eventually be classified as:

### Pre-trade

Known before execution begins.

### During-trade

Observed while execution is occurring and potentially available to an adaptive execution algorithm.

### Post-trade

Useful for evaluating execution but unavailable to the decision process.

A full-day volume measure, for example, may be valid for ex-post analysis but cannot automatically be used as a beginning-of-day predictor.

## 10. Bias-Control Requirements

The research must explicitly control:

- survivorship bias
- look-ahead bias
- delisting bias
- corporate-action bias
- selection bias
- temporal leakage
- measurement-regime bias

## 11. Validation Principles

A phase does not pass because code executes.

It passes only when:

1. Required work is complete.
2. Documentation is reproducible.
3. Validation checks pass.
4. Results are economically plausible.
5. Exceptions are documented.
6. Decisions are recorded.
7. Findings are written.

## 12. Phase 0 Exit Criteria

The following must exist:

- `research_question.md`: formalize the research question
- `data_role_mapping.md`: define the role of each dataset for the project
- `universe_and_identifiers.md`: define the security universe architecture and identifier hierarchy
- `information_timing_and_bias_controls.md`: establish the information set available to research models and execution decisions
- `microstructure_variable_spec.md`: define the economic meaning of the major market-microstructure variables
- `transaction_cost_and_execution_spec.md`: define the conceptual transaction-cost framework and future execution simulator
- `statistical_validation_framework.md`: establish the standards used to evaluate empirical relationships, transaction-cost models, execution models, and robustness
