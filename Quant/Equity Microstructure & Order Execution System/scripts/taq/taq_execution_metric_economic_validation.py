from pathlib import Path
import pandas as pd
import numpy as np


# =============================================================================
# PHASE 5 — STEP 7
# TAQ EXECUTION-METRIC ECONOMIC VALIDATION
# =============================================================================
#
# PURPOSE
# -------
# Validate the economic and internal consistency of execution-related metrics
# contained in the canonical TAQ file.
#
# IMPORTANT
# ---------
# This is a DIAGNOSTIC-ONLY step.
#
# No observations are removed.
# No values are modified.
# No imputation is performed.
# No execution metric is automatically corrected.
#
# Negative realized spreads and price impacts are NOT automatically treated
# as errors.
#
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data" / "processed" / "taq"
INPUT_FILE = DATA_DIR / "taq_cleaned.csv"

OUTPUT_DIR = DATA_DIR / "execution_metric_validation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 100_000


# =============================================================================
# EXECUTION METRIC DEFINITIONS
# =============================================================================

EXECUTION_METRICS = [
    "ESpreadDollar_Avg1",
    "ESpreadPct_Avg1",
    "RSpreadDollar_Avg1",
    "RSpreadPct_Avg1",
    "PriceImpactDollar_Avg1",
    "PriceImpactPct_Avg1",
    "ESpreadDollar_VW1",
    "ESpreadDollar_SW1",
    "ESpreadPct_VW1",
    "ESpreadPct_SW1",
    "RSpreadDollar_SW1",
    "RSpreadDollar_VW1",
    "RSpreadPct_SW1",
    "RSpreadPct_VW1",
    "PriceImpactDollar_VW1",
    "PriceImpactDollar_SW1",
    "PriceImpactPct_VW1",
    "PriceImpactPct_SW1",
]


DOLLAR_METRICS = [
    "ESpreadDollar_Avg1",
    "RSpreadDollar_Avg1",
    "PriceImpactDollar_Avg1",
    "ESpreadDollar_VW1",
    "ESpreadDollar_SW1",
    "RSpreadDollar_SW1",
    "RSpreadDollar_VW1",
    "PriceImpactDollar_VW1",
    "PriceImpactDollar_SW1",
]


PERCENT_METRICS = [
    "ESpreadPct_Avg1",
    "RSpreadPct_Avg1",
    "PriceImpactPct_Avg1",
    "ESpreadPct_VW1",
    "ESpreadPct_SW1",
    "RSpreadPct_SW1",
    "RSpreadPct_VW1",
    "PriceImpactPct_VW1",
    "PriceImpactPct_SW1",
]


TRADE_ACTIVITY_FIELDS = [
    "BuyNumTrades_LR1",
    "SellNumTrades_LR1",
    "BuyVol_LR1",
    "SellVol_LR1",
    "BuyDollar_LR1",
    "SellDollar_LR1",
    "NumTrades_t",
    "NumTrades_m",
    "SumVolume_t",
    "SumVolume_m",
    "SumValue_b",
    "SumValue_m",
]


PRICE_FIELDS = [
    "OPrice",
    "DPrice",
    "LPrice",
    "Price_1pm",
    "Price_4pm",
    "CPrc",
    "CPrc2",
]


QUOTE_FIELDS = [
    "BB_1pm",
    "BO_1pm",
    "MID_1pm",
    "BB_c1",
    "BO_c1",
    "Mid_c1",
    "BB_4pm",
    "BO_4pm",
    "Mid_4pm",
    "LBB",
    "LBO",
    "LMid",
]


# =============================================================================
# HELPERS
# =============================================================================

def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def count_negative(series):
    numeric = safe_numeric(series)
    return int((numeric < 0).sum())


def count_zero(series):
    numeric = safe_numeric(series)
    return int((numeric == 0).sum())


def percentile_values(series):
    numeric = safe_numeric(series).dropna()

    if numeric.empty:
        return {
            "p01": np.nan,
            "p05": np.nan,
            "p25": np.nan,
            "p50": np.nan,
            "p75": np.nan,
            "p95": np.nan,
            "p99": np.nan,
        }

    return {
        "p01": numeric.quantile(0.01),
        "p05": numeric.quantile(0.05),
        "p25": numeric.quantile(0.25),
        "p50": numeric.quantile(0.50),
        "p75": numeric.quantile(0.75),
        "p95": numeric.quantile(0.95),
        "p99": numeric.quantile(0.99),
    }


# =============================================================================
# LOAD SCHEMA
# =============================================================================

print("=" * 80)
print("PHASE 5 — STEP 7: TAQ EXECUTION-METRIC ECONOMIC VALIDATION")
print("=" * 80)

print(f"Input file:\n  {INPUT_FILE}")

if not INPUT_FILE.exists():
    raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

schema = pd.read_csv(INPUT_FILE, nrows=0)
columns = schema.columns.tolist()

print(f"Columns found: {len(columns)}")


available_execution_metrics = [
    c for c in EXECUTION_METRICS if c in columns
]

available_dollar_metrics = [
    c for c in DOLLAR_METRICS if c in columns
]

available_percent_metrics = [
    c for c in PERCENT_METRICS if c in columns
]

available_trade_fields = [
    c for c in TRADE_ACTIVITY_FIELDS if c in columns
]

available_price_fields = [
    c for c in PRICE_FIELDS if c in columns
]

available_quote_fields = [
    c for c in QUOTE_FIELDS if c in columns
]

print()
print("Execution metrics found:")
for c in available_execution_metrics:
    print(f"  - {c}")


# =============================================================================
# ACCUMULATORS
# =============================================================================

metric_stats = {}

for column in available_execution_metrics:
    metric_stats[column] = {
        "rows_observed": 0,
        "non_null_count": 0,
        "missing_count": 0,
        "negative_count": 0,
        "zero_count": 0,
        "positive_count": 0,
        "finite_count": 0,
        "non_finite_count": 0,
        "min": np.inf,
        "max": -np.inf,
        "sum": 0.0,
        "sum_abs": 0.0,
        "examples_negative": [],
    }


symbol_metric_stats = {}
date_metric_stats = []

crossfield_rows = []
spread_consistency_rows = []
percentage_consistency_rows = []

example_rows = []

total_rows = 0


# =============================================================================
# PROCESS CHUNKS
# =============================================================================

for chunk_number, chunk in enumerate(
    pd.read_csv(
        INPUT_FILE,
        chunksize=CHUNK_SIZE,
        low_memory=False,
    ),
    start=1,
):

    print(
        f"Processing chunk {chunk_number}: "
        f"{len(chunk):,} rows"
    )

    total_rows += len(chunk)

    # -------------------------------------------------------------------------
    # Normalize numeric execution metrics
    # -------------------------------------------------------------------------

    for column in available_execution_metrics:

        numeric = safe_numeric(chunk[column])

        stats = metric_stats[column]

        stats["rows_observed"] += len(chunk)
        stats["non_null_count"] += int(numeric.notna().sum())
        stats["missing_count"] += int(numeric.isna().sum())

        finite = numeric[np.isfinite(numeric)]

        stats["finite_count"] += len(finite)
        stats["non_finite_count"] += int(
            numeric.notna().sum() - len(finite)
        )

        if not finite.empty:

            stats["min"] = min(
                stats["min"],
                finite.min()
            )

            stats["max"] = max(
                stats["max"],
                finite.max()
            )

            stats["sum"] += finite.sum()
            stats["sum_abs"] += finite.abs().sum()

        negative_mask = numeric < 0
        zero_mask = numeric == 0
        positive_mask = numeric > 0

        stats["negative_count"] += int(
            negative_mask.sum()
        )

        stats["zero_count"] += int(
            zero_mask.sum()
        )

        stats["positive_count"] += int(
            positive_mask.sum()
        )

        negative_examples = chunk.loc[
            negative_mask,
            ["date", "symbol"] + [
                c for c in available_execution_metrics
                if c in chunk.columns
            ]
        ]

        if len(stats["examples_negative"]) < 10:

            remaining = 10 - len(stats["examples_negative"])

            stats["examples_negative"].extend(
                negative_examples.head(remaining)
                .to_dict("records")
            )


    # -------------------------------------------------------------------------
    # Symbol-level diagnostics
    # -------------------------------------------------------------------------

    if "symbol" in chunk.columns:

        for symbol, group in chunk.groupby("symbol", dropna=False):

            symbol_key = str(symbol)

            if symbol_key not in symbol_metric_stats:
                symbol_metric_stats[symbol_key] = {
                    "rows": 0
                }

            symbol_metric_stats[symbol_key]["rows"] += len(group)

            for column in available_execution_metrics:

                numeric = safe_numeric(group[column])

                prefix = column

                symbol_metric_stats[symbol_key][
                    f"{prefix}_non_null"
                ] = (
                    symbol_metric_stats[symbol_key]
                    .get(f"{prefix}_non_null", 0)
                    + int(numeric.notna().sum())
                )

                symbol_metric_stats[symbol_key][
                    f"{prefix}_negative"
                ] = (
                    symbol_metric_stats[symbol_key]
                    .get(f"{prefix}_negative", 0)
                    + int((numeric < 0).sum())
                )


    # -------------------------------------------------------------------------
    # Date-level diagnostics
    # -------------------------------------------------------------------------

    if "date" in chunk.columns:

        date_group = chunk.groupby("date", dropna=False)

        for date_value, group in date_group:

            row = {
                "date": date_value,
                "rows": len(group),
            }

            for column in available_execution_metrics:

                numeric = safe_numeric(group[column])

                row[f"{column}_non_null"] = int(
                    numeric.notna().sum()
                )

                row[f"{column}_negative"] = int(
                    (numeric < 0).sum()
                )

            date_metric_stats.append(row)


    # =========================================================================
    # DOLLAR / PERCENTAGE INTERNAL CONSISTENCY
    # =========================================================================
    #
    # These measures should generally be related economically, but the exact
    # transformation depends on the benchmark price and source construction.
    #
    # Therefore this step does NOT impose a hard equality rule.
    #
    # It records relationships where both measures are available.
    # =========================================================================

    paired_metrics = [
        (
            "ESpreadDollar_Avg1",
            "ESpreadPct_Avg1",
            "ESpread_Avg"
        ),
        (
            "RSpreadDollar_Avg1",
            "RSpreadPct_Avg1",
            "RSpread_Avg"
        ),
        (
            "PriceImpactDollar_Avg1",
            "PriceImpactPct_Avg1",
            "PriceImpact_Avg"
        ),
        (
            "ESpreadDollar_VW1",
            "ESpreadPct_VW1",
            "ESpread_VW"
        ),
        (
            "ESpreadDollar_SW1",
            "ESpreadPct_SW1",
            "ESpread_SW"
        ),
        (
            "RSpreadDollar_VW1",
            "RSpreadPct_VW1",
            "RSpread_VW"
        ),
        (
            "RSpreadDollar_SW1",
            "RSpreadPct_SW1",
            "RSpread_SW"
        ),
        (
            "PriceImpactDollar_VW1",
            "PriceImpactPct_VW1",
            "PriceImpact_VW"
        ),
        (
            "PriceImpactDollar_SW1",
            "PriceImpactPct_SW1",
            "PriceImpact_SW"
        ),
    ]

    for dollar_col, pct_col, metric_name in paired_metrics:

        if dollar_col not in chunk.columns:
            continue

        if pct_col not in chunk.columns:
            continue

        dollar = safe_numeric(chunk[dollar_col])
        pct = safe_numeric(chunk[pct_col])

        valid = (
            dollar.notna()
            & pct.notna()
            & np.isfinite(dollar)
            & np.isfinite(pct)
        )

        if valid.any():

            dollar_valid = dollar[valid]
            pct_valid = pct[valid]

            ratio = np.where(
                dollar_valid != 0,
                pct_valid / dollar_valid,
                np.nan,
            )

            spread_consistency_rows.append({
                "metric_pair": metric_name,
                "observations": int(valid.sum()),
                "dollar_min": dollar_valid.min(),
                "dollar_max": dollar_valid.max(),
                "pct_min": pct_valid.min(),
                "pct_max": pct_valid.max(),
                "median_pct_to_dollar_ratio": np.nanmedian(ratio),
                "mean_pct_to_dollar_ratio": np.nanmean(ratio),
            })


    # =========================================================================
    # EXECUTION ACTIVITY CROSS-FIELD CHECKS
    # =========================================================================

    if {
        "BuyNumTrades_LR1",
        "SellNumTrades_LR1"
    }.issubset(chunk.columns):

        buy_trades = safe_numeric(chunk["BuyNumTrades_LR1"])
        sell_trades = safe_numeric(chunk["SellNumTrades_LR1"])

        invalid = (
            (buy_trades < 0)
            | (sell_trades < 0)
        )

        crossfield_rows.append({
            "check": "NEGATIVE_TRADE_COUNTS",
            "violations": int(invalid.sum()),
        })


    if {
        "BuyVol_LR1",
        "SellVol_LR1"
    }.issubset(chunk.columns):

        buy_volume = safe_numeric(chunk["BuyVol_LR1"])
        sell_volume = safe_numeric(chunk["SellVol_LR1"])

        invalid = (
            (buy_volume < 0)
            | (sell_volume < 0)
        )

        crossfield_rows.append({
            "check": "NEGATIVE_TRADE_VOLUME",
            "violations": int(invalid.sum()),
        })


    if {
        "BuyDollar_LR1",
        "SellDollar_LR1"
    }.issubset(chunk.columns):

        buy_dollar = safe_numeric(chunk["BuyDollar_LR1"])
        sell_dollar = safe_numeric(chunk["SellDollar_LR1"])

        invalid = (
            (buy_dollar < 0)
            | (sell_dollar < 0)
        )

        crossfield_rows.append({
            "check": "NEGATIVE_TRADE_DOLLAR_VALUE",
            "violations": int(invalid.sum()),
        })


    # =========================================================================
    # EXTREME EXECUTION METRIC EXAMPLES
    # =========================================================================

    if available_execution_metrics:

        for column in available_execution_metrics:

            numeric = safe_numeric(chunk[column])

            valid = numeric.notna()

            if valid.any():

                threshold_low = numeric[valid].quantile(0.001)
                threshold_high = numeric[valid].quantile(0.999)

                extreme_mask = (
                    (numeric < threshold_low)
                    | (numeric > threshold_high)
                )

                examples = chunk.loc[
                    extreme_mask,
                    ["date", "symbol", column]
                ].head(25)

                if not examples.empty:

                    example_rows.extend(
                        examples.assign(
                            metric=column,
                            lower_threshold=threshold_low,
                            upper_threshold=threshold_high,
                        ).to_dict("records")
                    )


# =============================================================================
# BUILD METRIC SUMMARY
# =============================================================================

metric_summary_rows = []

for column, stats in metric_stats.items():

    minimum = (
        stats["min"]
        if stats["min"] != np.inf
        else np.nan
    )

    maximum = (
        stats["max"]
        if stats["max"] != -np.inf
        else np.nan
    )

    non_null = stats["non_null_count"]

    metric_summary_rows.append({
        "column": column,
        "rows_observed": stats["rows_observed"],
        "non_null_count": non_null,
        "missing_count": stats["missing_count"],
        "missing_rate": (
            stats["missing_count"] / stats["rows_observed"]
            if stats["rows_observed"] > 0
            else np.nan
        ),
        "negative_count": stats["negative_count"],
        "negative_rate": (
            stats["negative_count"] / non_null
            if non_null > 0
            else np.nan
        ),
        "zero_count": stats["zero_count"],
        "zero_rate": (
            stats["zero_count"] / non_null
            if non_null > 0
            else np.nan
        ),
        "positive_count": stats["positive_count"],
        "positive_rate": (
            stats["positive_count"] / non_null
            if non_null > 0
            else np.nan
        ),
        "finite_count": stats["finite_count"],
        "non_finite_count": stats["non_finite_count"],
        "minimum": minimum,
        "maximum": maximum,
        "mean": (
            stats["sum"] / stats["finite_count"]
            if stats["finite_count"] > 0
            else np.nan
        ),
        "mean_absolute_value": (
            stats["sum_abs"] / stats["finite_count"]
            if stats["finite_count"] > 0
            else np.nan
        ),
    })


metric_summary = pd.DataFrame(metric_summary_rows)


# =============================================================================
# SYMBOL SUMMARY
# =============================================================================

symbol_summary = pd.DataFrame.from_dict(
    symbol_metric_stats,
    orient="index"
)

if not symbol_summary.empty:
    symbol_summary.index.name = "symbol"
    symbol_summary = symbol_summary.reset_index()


# =============================================================================
# DATE SUMMARY
# =============================================================================

date_summary = pd.DataFrame(date_metric_stats)

if not date_summary.empty:
    date_summary = (
        date_summary
        .sort_values("date")
        .reset_index(drop=True)
    )


# =============================================================================
# CROSS-FIELD SUMMARY
# =============================================================================

if crossfield_rows:

    crossfield_summary = (
        pd.DataFrame(crossfield_rows)
        .groupby("check", as_index=False)["violations"]
        .sum()
    )

else:

    crossfield_summary = pd.DataFrame(
        columns=["check", "violations"]
    )


# =============================================================================
# SPREAD CONSISTENCY
# =============================================================================

if spread_consistency_rows:

    spread_consistency = pd.DataFrame(
        spread_consistency_rows
    )

    spread_consistency = (
        spread_consistency
        .groupby("metric_pair", as_index=False)
        .agg({
            "observations": "sum",
            "dollar_min": "min",
            "dollar_max": "max",
            "pct_min": "min",
            "pct_max": "max",
            "median_pct_to_dollar_ratio": "median",
            "mean_pct_to_dollar_ratio": "mean",
        })
    )

else:

    spread_consistency = pd.DataFrame()


# =============================================================================
# EXTREME EXAMPLES
# =============================================================================

examples = pd.DataFrame(example_rows)

if not examples.empty:

    examples = examples.drop_duplicates()

    examples = examples.head(500)


# =============================================================================
# OVERALL SUMMARY
# =============================================================================

total_execution_negative = int(
    sum(
        stats["negative_count"]
        for stats in metric_stats.values()
    )
)

total_execution_missing = int(
    sum(
        stats["missing_count"]
        for stats in metric_stats.values()
    )
)

summary = pd.DataFrame([
    {
        "input_file": str(INPUT_FILE),
        "total_rows": total_rows,
        "execution_metrics_evaluated": len(
            available_execution_metrics
        ),
        "dollar_metrics_evaluated": len(
            available_dollar_metrics
        ),
        "percentage_metrics_evaluated": len(
            available_percent_metrics
        ),
        "total_execution_metric_negative_values": (
            total_execution_negative
        ),
        "total_execution_metric_missing_values": (
            total_execution_missing
        ),
        "negative_execution_values_interpretation": (
            "REVIEW_REQUIRED"
        ),
        "automatic_removals": 0,
        "automatic_corrections": 0,
        "imputations": 0,
        "status": "PASS — diagnostic validation completed",
        "review_status": (
            "Execution metrics require semantic interpretation; "
            "negative signed realized-spread and price-impact values "
            "are not automatically classified as errors."
        ),
    }
])


# =============================================================================
# SAVE OUTPUTS
# =============================================================================

summary_file = (
    OUTPUT_DIR /
    "taq_execution_metric_validation_summary.csv"
)

metric_file = (
    OUTPUT_DIR /
    "taq_execution_metric_validation_by_metric.csv"
)

symbol_file = (
    OUTPUT_DIR /
    "taq_execution_metric_validation_by_symbol.csv"
)

date_file = (
    OUTPUT_DIR /
    "taq_execution_metric_validation_by_date.csv"
)

examples_file = (
    OUTPUT_DIR /
    "taq_execution_metric_validation_examples.csv"
)

spread_file = (
    OUTPUT_DIR /
    "taq_execution_metric_spread_consistency.csv"
)

percentage_file = (
    OUTPUT_DIR /
    "taq_execution_metric_percentage_consistency.csv"
)

crossfield_file = (
    OUTPUT_DIR /
    "taq_execution_metric_crossfield.csv"
)


summary.to_csv(
    summary_file,
    index=False
)

metric_summary.to_csv(
    metric_file,
    index=False
)

symbol_summary.to_csv(
    symbol_file,
    index=False
)

date_summary.to_csv(
    date_file,
    index=False
)

examples.to_csv(
    examples_file,
    index=False
)

spread_consistency.to_csv(
    spread_file,
    index=False
)

# Keep a dedicated percentage-consistency file.
percentage_consistency = (
    spread_consistency.copy()
    if not spread_consistency.empty
    else pd.DataFrame()
)

if not percentage_consistency.empty:
    percentage_consistency[
        "diagnostic_type"
    ] = "DOLLAR_PERCENTAGE_RELATIONSHIP"

percentage_consistency.to_csv(
    percentage_file,
    index=False
)

crossfield_summary.to_csv(
    crossfield_file,
    index=False
)


# =============================================================================
# CONSOLE REPORT
# =============================================================================

print()
print("=" * 80)
print("EXECUTION-METRIC ECONOMIC VALIDATION SUMMARY")
print("=" * 80)

print(
    f"Input rows:                         {total_rows:,}"
)

print(
    f"Execution metrics evaluated:        "
    f"{len(available_execution_metrics)}"
)

print(
    f"Negative execution-metric values:   "
    f"{total_execution_negative:,}"
)

print(
    f"Missing execution-metric values:    "
    f"{total_execution_missing:,}"
)

print()
print("METRIC RESULTS")
print("-" * 80)

display_columns = [
    "column",
    "non_null_count",
    "missing_count",
    "negative_count",
    "negative_rate",
    "minimum",
    "maximum",
]

print(
    metric_summary[display_columns]
    .to_string(index=False)
)

print()
print("=" * 80)
print("INTERPRETATION")
print("=" * 80)

print(
    "Negative realized-spread and price-impact values were "
    "retained and are NOT treated as automatic data errors."
)

print(
    "Dollar/percentage relationships were diagnosed without "
    "imposing a hard transformation rule."
)

print(
    "Execution activity fields were checked for negative "
    "counts, volumes, and dollar values."
)

print()
print("No observations were removed.")
print("No values were modified.")
print("No imputation was performed.")
print("No execution metrics were corrected.")
print()
print("STATUS")
print("=" * 80)
print(
    "PASS — execution-metric economic validation completed."
)
print(
    "REVIEW — execution metrics require semantic interpretation "
    "before any exclusion or correction."
)

print()
print("OUTPUTS")
print("=" * 80)

print(f"Summary:")
print(f"  {summary_file}")

print(f"Metric summary:")
print(f"  {metric_file}")

print(f"Symbol summary:")
print(f"  {symbol_file}")

print(f"Date summary:")
print(f"  {date_file}")

print(f"Violation/extreme examples:")
print(f"  {examples_file}")

print(f"Spread consistency:")
print(f"  {spread_file}")

print(f"Percentage consistency:")
print(f"  {percentage_file}")

print(f"Cross-field diagnostics:")
print(f"  {crossfield_file}")

print()
print("=" * 80)
print("IMPORTANT")
print("=" * 80)
print(
    "This stage is diagnostic only. No canonical TAQ data was changed."
)