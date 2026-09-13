# Equity Microstructure & Order Execution Framework

Research infrastructure for empirical equity market microstructure and
order-execution research using CRSP, TAQ, and TAQM data.

## Research Period

1993–2018 inclusive.

## Microstructure Regimes

- TAQ: 1993–2012
- TAQM: 2013–2018

The TAQ/TAQM boundary is treated as a potential measurement and
market-structure regime change.

## Project Architecture

- `docs/` — research documentation and methodological notes
- `notebooks/` — reproducible research notebooks
- `src/` — reusable Python research infrastructure
- `tests/` — unit and integration tests
- `data/raw/` — immutable source data
- `data/interim/` — intermediate datasets
- `data/processed/` — processed research datasets
- `data/metadata/` — machine-readable data metadata
- `data/validation/` — validation outputs
- `reports/` — human-readable research outputs

## Current Phase

Phase 1 — Local Data Inventory & Infrastructure.

The current objective is to establish a transparent, reproducible,
and auditable map of the locally available CRSP, TAQ, and TAQM data
before substantive empirical analysis begins.
