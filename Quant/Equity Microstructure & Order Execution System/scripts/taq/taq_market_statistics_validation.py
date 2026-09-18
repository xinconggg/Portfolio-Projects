from pathlib import Path
import pandas as pd
import numpy as np


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "taq"
    / "taq_cleaned.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "taq"
    / "market_statistics_validation"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 100_000

DATE_COL = "date"
SYMBOL_COL = "symbol"


# =============================================================================
# EXPECTED MARKET-STATISTIC FIELDS
# =============================================================================

RETURN_FIELDS = [
    "Ret_pre_t",
    "Ret_mkt_t",
    "Ret_post_t",
]

VOLATILITY_FIELDS = [
    "IVol_t_m",
    "IVol_q_m",
]

VARIANCE_RATIO_FIELDS = [
    "VarianceRatio1",
    "VarianceRatio2",
]

INFORMATION_FIELDS = [
    "HIndex1",
]

EXTREME_QUOTE_FIELDS = [
    "NumExtremeOfr_m",
    "NumExtremeBid_m",
]

OBSERVATION_COUNT_FIELDS = [
    "NObsUsed1",
    "NObsUsed2",
    "NumTimeUnitsWithTrade1",
    "NumTimeUnitsWithTrade2",
]

MARKET_STAT_FIELDS = (
    RETURN_FIELDS
    + VOLATILITY_FIELDS
    + VARIANCE_RATIO_FIELDS
    + INFORMATION_FIELDS
    + EXTREME_QUOTE_FIELDS
    + OBSERVATION_COUNT_FIELDS
)


# =============================================================================
# HELPERS
# =============================================================================

def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def pct(value, denominator):
    if denominator == 0:
        return 0.0
    return value / denominator


# =============================================================================
# LOAD SCHEMA
# =============================================================================

print("=" * 80)
print("PHASE 5 — STEP 9: MARKET STATISTICS & INFORMATION-METRIC VALIDATION")
print("=" * 80)

print(f"Input file:")
print(f"  {INPUT_FILE}")

header = pd.read_csv(INPUT_FILE, nrows=0)

columns = list(header.columns)

print(f"Columns found: {len(columns)}")

available_fields = [
    col for col in MARKET_STAT_FIELDS
    if col in columns
]

missing_expected_fields = [
    col for col in MARKET_STAT_FIELDS
    if col not in columns
]

print("\nMarket-statistic fields found:")
for col in available_fields:
    print(f"  - {col}")

if missing_expected_fields:
    print("\nExpected fields not found:")
    for col in missing_expected_fields:
        print(f"  - {col}")


# =============================================================================
# FIELD GROUPS PRESENT IN FILE
# =============================================================================

return_fields = [
    col for col in RETURN_FIELDS
    if col in columns
]

volatility_fields = [
    col for col in VOLATILITY_FIELDS
    if col in columns
]

variance_ratio_fields = [
    col for col in VARIANCE_RATIO_FIELDS
    if col in columns
]

information_fields = [
    col for col in INFORMATION_FIELDS
    if col in columns
]

extreme_quote_fields = [
    col for col in EXTREME_QUOTE_FIELDS
    if col in columns
]

observation_count_fields = [
    col for col in OBSERVATION_COUNT_FIELDS
    if col in columns
]


# =============================================================================
# GLOBAL ACCUMULATORS
# =============================================================================

field_stats = {
    col: {
        "rows_observed": 0,
        "non_null_count": 0,
        "missing_count": 0,
        "negative_count": 0,
        "zero_count": 0,
        "positive_count": 0,
        "finite_count": 0,
        "non_finite_count": 0,
        "minimum": np.nan,
        "maximum": np.nan,
    }
    for col in available_fields
}


# =============================================================================
# CONSISTENCY COUNTERS
# =============================================================================

negative_volatility = 0
negative_variance_ratio = 0
negative_information_metric = 0
negative_extreme_quote_counts = 0
negative_observation_counts = 0

zero_or_negative_variance_ratio = 0

invalid_hindex = 0

return_nonfinite = 0

observation_count_relationship_violations = 0

volatility_vs_returns_review = 0

extreme_quote_relationship_violations = 0


# =============================================================================
# EXAMPLES
# =============================================================================

examples = []

MAX_EXAMPLES = 500


def collect_examples(frame, mask, diagnostic_type, fields):
    global examples

    if len(examples) >= MAX_EXAMPLES:
        return

    subset = frame.loc[mask, fields].copy()

    if subset.empty:
        return

    subset.insert(0, "diagnostic_type", diagnostic_type)

    remaining = MAX_EXAMPLES - len(examples)

    examples.extend(
        subset.head(remaining).to_dict("records")
    )


# =============================================================================
# SYMBOL / DATE AGGREGATION
# =============================================================================

symbol_records = []
date_records = []


# =============================================================================
# CHUNKED PROCESSING
# =============================================================================

reader = pd.read_csv(
    INPUT_FILE,
    chunksize=CHUNK_SIZE,
    low_memory=False,
)

total_rows = 0

for chunk_number, chunk in enumerate(reader, start=1):

    print(
        f"Processing market-statistics chunk "
        f"{chunk_number}: {len(chunk):,} rows"
    )

    total_rows += len(chunk)

    # -------------------------------------------------------------------------
    # NUMERIC CONVERSION
    # -------------------------------------------------------------------------

    numeric = {}

    for col in available_fields:
        numeric[col] = safe_numeric(chunk[col])

        s = numeric[col]

        stats = field_stats[col]

        stats["rows_observed"] += len(s)

        non_null = s.notna()

        stats["non_null_count"] += int(non_null.sum())
        stats["missing_count"] += int(s.isna().sum())

        finite = np.isfinite(s.fillna(0))

        stats["finite_count"] += int(
            (non_null & finite).sum()
        )

        stats["non_finite_count"] += int(
            (non_null & ~finite).sum()
        )

        stats["negative_count"] += int(
            (s < 0).sum()
        )

        stats["zero_count"] += int(
            (s == 0).sum()
        )

        stats["positive_count"] += int(
            (s > 0).sum()
        )

        valid_values = s[np.isfinite(s)]

        if len(valid_values) > 0:

            current_min = valid_values.min()
            current_max = valid_values.max()

            if pd.isna(stats["minimum"]):
                stats["minimum"] = current_min
            else:
                stats["minimum"] = min(
                    stats["minimum"],
                    current_min
                )

            if pd.isna(stats["maximum"]):
                stats["maximum"] = current_max
            else:
                stats["maximum"] = max(
                    stats["maximum"],
                    current_max
                )

    # -------------------------------------------------------------------------
    # RETURNS
    #
    # Negative returns are economically valid.
    # Therefore negative values are NOT violations.
    # -------------------------------------------------------------------------

    for col in return_fields:

        s = numeric[col]

        mask = ~np.isfinite(
            s.fillna(0)
        ) & s.notna()

        return_nonfinite += int(mask.sum())

        collect_examples(
            chunk,
            mask,
            f"NONFINITE_RETURN_{col}",
            [DATE_COL, SYMBOL_COL, col]
            if DATE_COL in chunk.columns
            and SYMBOL_COL in chunk.columns
            else [col],
        )

    # -------------------------------------------------------------------------
    # VOLATILITY
    #
    # Volatility should not normally be negative.
    # Zero can be economically possible.
    # -------------------------------------------------------------------------

    for col in volatility_fields:

        s = numeric[col]

        mask = s < 0

        count = int(mask.sum())

        negative_volatility += count

        collect_examples(
            chunk,
            mask,
            f"NEGATIVE_VOLATILITY_{col}",
            [DATE_COL, SYMBOL_COL, col]
            if DATE_COL in chunk.columns
            and SYMBOL_COL in chunk.columns
            else [col],
        )

    # -------------------------------------------------------------------------
    # VARIANCE RATIOS
    #
    # Variance ratios are generally expected to be non-negative.
    # We diagnose rather than impose a hard economic range.
    # -------------------------------------------------------------------------

    for col in variance_ratio_fields:

        s = numeric[col]

        negative_mask = s < 0

        negative_count = int(
            negative_mask.sum()
        )

        negative_variance_ratio += negative_count

        zero_negative_mask = s <= 0

        zero_or_negative_variance_ratio += int(
            zero_negative_mask.sum()
        )

        collect_examples(
            chunk,
            negative_mask,
            f"NEGATIVE_VARIANCE_RATIO_{col}",
            [DATE_COL, SYMBOL_COL, col]
            if DATE_COL in chunk.columns
            and SYMBOL_COL in chunk.columns
            else [col],
        )

    # -------------------------------------------------------------------------
    # H-INDEX / INFORMATION METRIC
    #
    # Do not assume a specific theoretical range unless source documentation
    # establishes one. Diagnose negative and non-finite values separately.
    # -------------------------------------------------------------------------

    for col in information_fields:

        s = numeric[col]

        mask = (s < 0) | (~np.isfinite(s.fillna(0)) & s.notna())

        count = int(mask.sum())

        invalid_hindex += count

        collect_examples(
            chunk,
            mask,
            f"INVALID_INFORMATION_METRIC_{col}",
            [DATE_COL, SYMBOL_COL, col]
            if DATE_COL in chunk.columns
            and SYMBOL_COL in chunk.columns
            else [col],
        )

    # -------------------------------------------------------------------------
    # EXTREME QUOTE COUNTS
    #
    # These are counts and therefore negative values are structurally suspect.
    # -------------------------------------------------------------------------

    for col in extreme_quote_fields:

        s = numeric[col]

        mask = s < 0

        count = int(mask.sum())

        negative_extreme_quote_counts += count

        collect_examples(
            chunk,
            mask,
            f"NEGATIVE_EXTREME_QUOTE_COUNT_{col}",
            [DATE_COL, SYMBOL_COL, col]
            if DATE_COL in chunk.columns
            and SYMBOL_COL in chunk.columns
            else [col],
        )

    # -------------------------------------------------------------------------
    # OBSERVATION COUNTS
    # -------------------------------------------------------------------------

    for col in observation_count_fields:

        s = numeric[col]

        mask = s < 0

        count = int(mask.sum())

        negative_observation_counts += count

        collect_examples(
            chunk,
            mask,
            f"NEGATIVE_OBSERVATION_COUNT_{col}",
            [DATE_COL, SYMBOL_COL, col]
            if DATE_COL in chunk.columns
            and SYMBOL_COL in chunk.columns
            else [col],
        )

    # -------------------------------------------------------------------------
    # OBSERVATION COUNT RELATIONSHIPS
    # -------------------------------------------------------------------------

    if (
        "NObsUsed1" in numeric
        and "NumTimeUnitsWithTrade1" in numeric
    ):

        mask = (
            numeric["NObsUsed1"].notna()
            & numeric["NumTimeUnitsWithTrade1"].notna()
            & (
                numeric["NObsUsed1"]
                > numeric["NumTimeUnitsWithTrade1"]
            )
        )

        count = int(mask.sum())

        observation_count_relationship_violations += count

        collect_examples(
            chunk,
            mask,
            "NOBS_USED1_GT_TIME_UNITS",
            [
                DATE_COL,
                SYMBOL_COL,
                "NObsUsed1",
                "NumTimeUnitsWithTrade1",
            ]
            if DATE_COL in chunk.columns
            and SYMBOL_COL in chunk.columns
            else [
                "NObsUsed1",
                "NumTimeUnitsWithTrade1",
            ],
        )

    if (
        "NObsUsed2" in numeric
        and "NumTimeUnitsWithTrade2" in numeric
    ):

        mask = (
            numeric["NObsUsed2"].notna()
            & numeric["NumTimeUnitsWithTrade2"].notna()
            & (
                numeric["NObsUsed2"]
                > numeric["NumTimeUnitsWithTrade2"]
            )
        )

        count = int(mask.sum())

        observation_count_relationship_violations += count

        collect_examples(
            chunk,
            mask,
            "NOBS_USED2_GT_TIME_UNITS",
            [
                DATE_COL,
                SYMBOL_COL,
                "NObsUsed2",
                "NumTimeUnitsWithTrade2",
            ]
            if DATE_COL in chunk.columns
            and SYMBOL_COL in chunk.columns
            else [
                "NObsUsed2",
                "NumTimeUnitsWithTrade2",
            ],
        )

    # -------------------------------------------------------------------------
    # EXTREME QUOTE RELATIONSHIP
    # -------------------------------------------------------------------------

    if (
        "NumExtremeBid_m" in numeric
        and "NumExtremeOfr_m" in numeric
        and "NumTrades_m" in numeric
    ):

        combined_extreme = (
            numeric["NumExtremeBid_m"]
            + numeric["NumExtremeOfr_m"]
        )

        mask = (
            combined_extreme.notna()
            & numeric["NumTrades_m"].notna()
            & (
                combined_extreme
                > numeric["NumTrades_m"]
            )
        )

        count = int(mask.sum())

        extreme_quote_relationship_violations += count

        collect_examples(
            chunk,
            mask,
            "EXTREME_QUOTE_COUNT_GT_TRADES",
            [
                DATE_COL,
                SYMBOL_COL,
                "NumExtremeBid_m",
                "NumExtremeOfr_m",
                "NumTrades_m",
            ]
            if DATE_COL in chunk.columns
            and SYMBOL_COL in chunk.columns
            else [
                "NumExtremeBid_m",
                "NumExtremeOfr_m",
                "NumTrades_m",
            ],
        )

    # -------------------------------------------------------------------------
    # SYMBOL AGGREGATION
    # -------------------------------------------------------------------------

    if SYMBOL_COL in chunk.columns:

        for symbol, group in chunk.groupby(
            SYMBOL_COL,
            dropna=False
        ):

            record = {
                "symbol": symbol,
                "rows": len(group),
            }

            for col in available_fields:

                s = numeric[col].loc[group.index]

                record[f"{col}_non_null"] = int(
                    s.notna().sum()
                )

                record[f"{col}_negative"] = int(
                    (s < 0).sum()
                )

            symbol_records.append(record)

    # -------------------------------------------------------------------------
    # DATE AGGREGATION
    # -------------------------------------------------------------------------

    if DATE_COL in chunk.columns:

        for date_value, group in chunk.groupby(
            DATE_COL,
            dropna=False
        ):

            record = {
                "date": date_value,
                "rows": len(group),
            }

            for col in available_fields:

                s = numeric[col].loc[group.index]

                record[f"{col}_non_null"] = int(
                    s.notna().sum()
                )

                record[f"{col}_negative"] = int(
                    (s < 0).sum()
                )

            date_records.append(record)


# =============================================================================
# FIELD SUMMARY
# =============================================================================

field_summary = pd.DataFrame(
    [
        {
            "column": col,
            **stats,
            "missing_rate": pct(
                stats["missing_count"],
                stats["rows_observed"],
            ),
            "negative_rate": pct(
                stats["negative_count"],
                stats["non_null_count"],
            ),
        }
        for col, stats in field_stats.items()
    ]
)


# =============================================================================
# CONSISTENCY SUMMARY
# =============================================================================

consistency_summary = pd.DataFrame(
    [
        {
            "diagnostic": "NEGATIVE_VOLATILITY",
            "count": negative_volatility,
            "interpretation":
                "Potentially invalid because volatility should not be negative.",
        },
        {
            "diagnostic": "NEGATIVE_VARIANCE_RATIO",
            "count": negative_variance_ratio,
            "interpretation":
                "Requires semantic/source-definition review.",
        },
        {
            "diagnostic": "NONPOSITIVE_VARIANCE_RATIO",
            "count": zero_or_negative_variance_ratio,
            "interpretation":
                "Diagnostic only; no automatic validity range imposed.",
        },
        {
            "diagnostic": "INVALID_INFORMATION_METRIC",
            "count": invalid_hindex,
            "interpretation":
                "Requires source-semantic review.",
        },
        {
            "diagnostic": "NEGATIVE_EXTREME_QUOTE_COUNT",
            "count": negative_extreme_quote_counts,
            "interpretation":
                "Negative counts are structurally suspect.",
        },
        {
            "diagnostic": "NEGATIVE_OBSERVATION_COUNT",
            "count": negative_observation_counts,
            "interpretation":
                "Negative counts are structurally suspect.",
        },
        {
            "diagnostic": "OBSERVATION_COUNT_RELATIONSHIP",
            "count": observation_count_relationship_violations,
            "interpretation":
                "Requires review of the exact source definitions.",
        },
        {
            "diagnostic": "EXTREME_QUOTE_GT_TRADE_COUNT",
            "count": extreme_quote_relationship_violations,
            "interpretation":
                "Requires semantic review of extreme-quote definitions.",
        },
        {
            "diagnostic": "NONFINITE_RETURN",
            "count": return_nonfinite,
            "interpretation":
                "Non-finite return observations require investigation.",
        },
    ]
)


# =============================================================================
# EXAMPLES OUTPUT
# =============================================================================

examples_df = pd.DataFrame(examples)

if examples_df.empty:
    examples_df = pd.DataFrame(
        columns=[
            "diagnostic_type",
            DATE_COL,
            SYMBOL_COL,
        ]
    )


# =============================================================================
# SYMBOL SUMMARY
# =============================================================================

if symbol_records:

    symbol_summary = (
        pd.DataFrame(symbol_records)
        .groupby("symbol", dropna=False)
        .sum(numeric_only=True)
        .reset_index()
    )

else:

    symbol_summary = pd.DataFrame()


# =============================================================================
# DATE SUMMARY
# =============================================================================

if date_records:

    date_summary = (
        pd.DataFrame(date_records)
        .groupby("date", dropna=False)
        .sum(numeric_only=True)
        .reset_index()
    )

else:

    date_summary = pd.DataFrame()


# =============================================================================
# GLOBAL SUMMARY
# =============================================================================

total_non_null_market_values = sum(
    stats["non_null_count"]
    for stats in field_stats.values()
)

total_missing_market_values = sum(
    stats["missing_count"]
    for stats in field_stats.values()
)

summary = pd.DataFrame(
    [
        {
            "input_rows": total_rows,
            "market_statistics_fields": len(available_fields),
            "return_fields": len(return_fields),
            "volatility_fields": len(volatility_fields),
            "variance_ratio_fields": len(variance_ratio_fields),
            "information_metric_fields": len(information_fields),
            "extreme_quote_fields": len(extreme_quote_fields),
            "observation_count_fields": len(observation_count_fields),
            "non_null_market_stat_values":
                total_non_null_market_values,
            "missing_market_stat_values":
                total_missing_market_values,
            "negative_volatility":
                negative_volatility,
            "negative_variance_ratio":
                negative_variance_ratio,
            "invalid_information_metric":
                invalid_hindex,
            "negative_extreme_quote_counts":
                negative_extreme_quote_counts,
            "negative_observation_counts":
                negative_observation_counts,
            "observation_count_relationship_violations":
                observation_count_relationship_violations,
            "extreme_quote_relationship_violations":
                extreme_quote_relationship_violations,
            "nonfinite_returns":
                return_nonfinite,
        }
    ]
)


# =============================================================================
# OUTPUTS
# =============================================================================

summary_file = (
    OUTPUT_DIR
    / "taq_market_statistics_validation_summary.csv"
)

field_file = (
    OUTPUT_DIR
    / "taq_market_statistics_validation_by_field.csv"
)

symbol_file = (
    OUTPUT_DIR
    / "taq_market_statistics_validation_by_symbol.csv"
)

date_file = (
    OUTPUT_DIR
    / "taq_market_statistics_validation_by_date.csv"
)

examples_file = (
    OUTPUT_DIR
    / "taq_market_statistics_validation_examples.csv"
)

consistency_file = (
    OUTPUT_DIR
    / "taq_market_statistics_consistency.csv"
)


summary.to_csv(
    summary_file,
    index=False
)

field_summary.to_csv(
    field_file,
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

examples_df.to_csv(
    examples_file,
    index=False
)

consistency_summary.to_csv(
    consistency_file,
    index=False
)


# =============================================================================
# REPORT
# =============================================================================

print("\n" + "=" * 80)
print("MARKET STATISTICS & INFORMATION-METRIC VALIDATION SUMMARY")
print("=" * 80)

print(
    f"Input rows:                         "
    f"{total_rows:,}"
)

print(
    f"Market-statistic fields:            "
    f"{len(available_fields):,}"
)

print(
    f"Negative volatility values:         "
    f"{negative_volatility:,}"
)

print(
    f"Negative variance-ratio values:     "
    f"{negative_variance_ratio:,}"
)

print(
    f"Invalid information metrics:        "
    f"{invalid_hindex:,}"
)

print(
    f"Negative extreme-quote counts:      "
    f"{negative_extreme_quote_counts:,}"
)

print(
    f"Negative observation counts:        "
    f"{negative_observation_counts:,}"
)

print(
    f"Observation-count violations:       "
    f"{observation_count_relationship_violations:,}"
)

print(
    f"Extreme-quote relationship issues:  "
    f"{extreme_quote_relationship_violations:,}"
)

print(
    f"Non-finite returns:                  "
    f"{return_nonfinite:,}"
)


# =============================================================================
# INTERPRETATION
# =============================================================================

print("\n" + "=" * 80)
print("INTERPRETATION")
print("=" * 80)

print(
    "Negative return values were retained because negative returns "
    "are economically valid."
)

print(
    "Negative volatility, count, and observation-count values were "
    "diagnosed as potential structural issues."
)

print(
    "Variance-ratio and information-metric values were diagnosed "
    "without imposing unsupported source-specific bounds."
)

print(
    "No observations were removed."
)

print(
    "No values were modified."
)

print(
    "No imputation was performed."
)

print(
    "No market-statistic fields were corrected."
)


# =============================================================================
# STATUS
# =============================================================================

print("\n" + "=" * 80)
print("STATUS")
print("=" * 80)

print(
    "PASS — market statistics and information-metric validation completed."
)

print(
    "REVIEW — detected market-statistic inconsistencies require "
    "semantic/source interpretation before any exclusion or correction."
)


# =============================================================================
# OUTPUT PATHS
# =============================================================================

print("\n" + "=" * 80)
print("OUTPUTS")
print("=" * 80)

print("Summary:")
print(f"  {summary_file}")

print("Field summary:")
print(f"  {field_file}")

print("Symbol summary:")
print(f"  {symbol_file}")

print("Date summary:")
print(f"  {date_file}")

print("Violation examples:")
print(f"  {examples_file}")

print("Consistency diagnostics:")
print(f"  {consistency_file}")

print("\n" + "=" * 80)
print("IMPORTANT")
print("=" * 80)

print(
    "This stage is diagnostic only."
)

print(
    "The canonical TAQ file was not changed."
)