from pathlib import Path
import pandas as pd
import numpy as np

# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_TAQ_DIR = PROJECT_ROOT / "data" / "raw" / "taq"
PROCESSED_TAQ_DIR = PROJECT_ROOT / "data" / "processed" / "taq"

SOURCE_FILE = RAW_TAQ_DIR / "taq.csv"

OUTPUT_FILE = PROCESSED_TAQ_DIR / "taq_cross_field_validation.csv"
SUMMARY_FILE = PROCESSED_TAQ_DIR / "taq_cross_field_validation_summary.csv"
EXAMPLES_FILE = PROCESSED_TAQ_DIR / "taq_cross_field_validation_examples.csv"


# =============================================================================
# CONFIGURATION
# =============================================================================

CHUNK_SIZE = 100_000

# Floating-point tolerance for deterministic price relationships.
PRICE_TOLERANCE = 1e-6

# Slightly wider tolerance for relationships involving aggregated values.
RELATIVE_TOLERANCE = 1e-6

MAX_EXAMPLES_PER_CHECK = 10


# =============================================================================
# FIELD GROUPS
# =============================================================================

QUOTE_GROUPS = {
    "1pm": {
        "bid": "BB_1pm",
        "ask": "BO_1pm",
        "mid": "MID_1pm",
        "time": "QTime_1pm",
    },
    "c1": {
        "bid": "BB_c1",
        "ask": "BO_c1",
        "mid": "Mid_c1",
        "time": "QTime_c1",
    },
    "4pm": {
        "bid": "BB_4pm",
        "ask": "BO_4pm",
        "mid": "Mid_4pm",
        "time": "QTime_4pm",
    },
    "last_quote": {
        "bid": "LBB",
        "ask": "LBO",
        "mid": "LMid",
        "time": "LQTime",
    },
}


TRADE_PRICE_FIELDS = [
    "OPrice",
    "DPrice",
    "LPrice",
    "Price_1pm",
    "Price_4pm",
    "CPrc",
    "CPrc2",
]


VOLUME_FIELDS = [
    "Vol_oc",
    "SumVolume_t",
    "SumVolume_m",
    "SumISOVolume_m",
    "SumOddLotVolume_m",
    "SumMixedLotVolume_m",
    "BuyVol_LR1",
    "SellVol_LR1",
    "TOfrShares_TW_m",
    "TBidShares_TW_m",
    "BOfrShares_TW_m",
    "BBidShares_TW_m",
]


VALUE_FIELDS = [
    "Value_oc",
    "SumValue_b",
    "SumValue_m",
    "SumISOValue_m",
    "SumOddLotValue_m",
    "SumMixedLotValue_m",
    "BuyDollar_LR1",
    "SellDollar_LR1",
    "TOfrDollar_TW_m",
    "TBidDollar_TW_m",
    "BOfrDollar_TW_m",
    "BBidDollar_TW_m",
]


NONNEGATIVE_COUNT_FIELDS = [
    "MFCount",
    "NumTrades_t",
    "NumTrades_m",
    "NumISOTrades_m",
    "NumOddLotTrades_m",
    "NumMixedLotTrades_m",
    "NumExtremeOfr_m",
    "NumExtremeBid_m",
    "NObsUsed1",
    "NObsUsed2",
    "NumTimeUnitsWithTrade1",
    "NumTimeUnitsWithTrade2",
]


TIMESTAMP_FIELDS = [
    "QTime_1pm",
    "QTime_c1",
    "QTime_4pm",
    "LQTime",
    "OTime",
    "DTime",
    "LTTime",
    "TTime_1pm",
    "TTime_4pm",
    "CTime",
    "CTime2",
]


# =============================================================================
# HELPERS
# =============================================================================

def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def add_check(
    summary_rows,
    example_rows,
    check_name,
    category,
    mask,
    df,
    detail_columns=None,
):
    """
    Register a diagnostic check.

    mask:
        Boolean Series indicating rows that violate the relationship.
    """

    mask = mask.fillna(False)

    violation_count = int(mask.sum())
    observed_rows = len(df)

    violation_rate = (
        violation_count / observed_rows
        if observed_rows > 0
        else np.nan
    )

    summary_rows.append(
        {
            "check_name": check_name,
            "category": category,
            "rows_observed": observed_rows,
            "violation_count": violation_count,
            "violation_rate": violation_rate,
        }
    )

    if violation_count > 0 and len(example_rows) < 1000:

        cols = ["date", "symbol"]

        if detail_columns:
            cols.extend(detail_columns)

        cols = [c for c in cols if c in df.columns]

        examples = df.loc[mask, cols].head(MAX_EXAMPLES_PER_CHECK).copy()

        examples.insert(0, "check_name", check_name)
        examples.insert(1, "category", category)

        example_rows.extend(
            examples.to_dict(orient="records")
        )


def relative_difference(a, b):
    denominator = np.maximum(np.abs(b), PRICE_TOLERANCE)
    return np.abs(a - b) / denominator


# =============================================================================
# START
# =============================================================================

print("=" * 80)
print("PHASE 5 — STEP 7: CROSS-FIELD CONSISTENCY VALIDATION")
print("=" * 80)

print(f"Source file:")
print(SOURCE_FILE)
print(f"Chunk size: {CHUNK_SIZE:,}")
print()


if not SOURCE_FILE.exists():
    raise FileNotFoundError(
        f"TAQ source file not found:\n{SOURCE_FILE}"
    )


PROCESSED_TAQ_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# LOAD COLUMN NAMES
# =============================================================================

header = pd.read_csv(
    SOURCE_FILE,
    nrows=0
)

columns = list(header.columns)

print(f"Columns found: {len(columns):,}")
print()


# =============================================================================
# REQUIRED FIELD CHECK
# =============================================================================

required_columns = {
    "date",
    "symbol",
}

for group in QUOTE_GROUPS.values():
    required_columns.update(
        [
            group["bid"],
            group["ask"],
            group["mid"],
        ]
    )

required_columns.update(TRADE_PRICE_FIELDS)
required_columns.update(VOLUME_FIELDS)
required_columns.update(VALUE_FIELDS)
required_columns.update(NONNEGATIVE_COUNT_FIELDS)

missing_required = sorted(
    required_columns - set(columns)
)

if missing_required:

    print("WARNING — missing expected fields:")
    for column in missing_required:
        print(f"  - {column}")

    print()

else:
    print("PASS — all expected cross-field validation fields are present.")
    print()


# =============================================================================
# OUTPUT ACCUMULATORS
# =============================================================================

summary_rows = []
example_rows = []

total_rows = 0


# =============================================================================
# CHUNK PROCESSING
# =============================================================================

for chunk_number, df in enumerate(
    pd.read_csv(
        SOURCE_FILE,
        chunksize=CHUNK_SIZE,
        low_memory=False,
    ),
    start=1,
):

    print(
        f"Processing chunk {chunk_number}: "
        f"{len(df):,} rows"
    )

    total_rows += len(df)


    # =========================================================================
    # NUMERIC CONVERSION
    # =========================================================================

    numeric_columns = list(
        set(
            TRADE_PRICE_FIELDS
            + VOLUME_FIELDS
            + VALUE_FIELDS
            + NONNEGATIVE_COUNT_FIELDS
            + [
                group["bid"]
                for group in QUOTE_GROUPS.values()
            ]
            + [
                group["ask"]
                for group in QUOTE_GROUPS.values()
            ]
            + [
                group["mid"]
                for group in QUOTE_GROUPS.values()
            ]
        )
        & set(df.columns)
    )

    numeric = {}

    for column in numeric_columns:
        numeric[column] = safe_numeric(df[column])


    # =========================================================================
    # 1. QUOTE BID/ASK ORDER
    # =========================================================================

    for name, group in QUOTE_GROUPS.items():

        bid = group["bid"]
        ask = group["ask"]

        if bid not in numeric or ask not in numeric:
            continue

        bid_values = numeric[bid]
        ask_values = numeric[ask]

        mask = (
            bid_values.notna()
            & ask_values.notna()
            & (bid_values > ask_values)
        )

        add_check(
            summary_rows,
            example_rows,
            check_name=f"{name}_bid_greater_than_ask",
            category="QUOTE_ORDER",
            mask=mask,
            df=df,
            detail_columns=[bid, ask],
        )


    # =========================================================================
    # 2. QUOTE MIDPOINT CONSISTENCY
    # =========================================================================

    for name, group in QUOTE_GROUPS.items():

        bid = group["bid"]
        ask = group["ask"]
        mid = group["mid"]

        if not all(
            column in numeric
            for column in [bid, ask, mid]
        ):
            continue

        expected_mid = (
            numeric[bid] + numeric[ask]
        ) / 2.0

        difference = (
            numeric[mid] - expected_mid
        ).abs()

        valid = (
            numeric[bid].notna()
            & numeric[ask].notna()
            & numeric[mid].notna()
        )

        mask = (
            valid
            & (difference > PRICE_TOLERANCE)
        )

        add_check(
            summary_rows,
            example_rows,
            check_name=f"{name}_midpoint_inconsistency",
            category="QUOTE_MIDPOINT",
            mask=mask,
            df=df,
            detail_columns=[bid, ask, mid],
        )


    # =========================================================================
    # 3. QUOTE SPREAD NON-POSITIVITY
    # =========================================================================

    for name, group in QUOTE_GROUPS.items():

        bid = group["bid"]
        ask = group["ask"]

        if bid not in numeric or ask not in numeric:
            continue

        spread = (
            numeric[ask] - numeric[bid]
        )

        valid = (
            numeric[bid].notna()
            & numeric[ask].notna()
        )

        mask = (
            valid
            & (spread <= 0)
        )

        add_check(
            summary_rows,
            example_rows,
            check_name=f"{name}_nonpositive_quote_spread",
            category="QUOTE_SPREAD",
            mask=mask,
            df=df,
            detail_columns=[bid, ask],
        )


    # =========================================================================
    # 4. NEGATIVE TRADE / EVENT PRICES
    # =========================================================================

    for column in TRADE_PRICE_FIELDS:

        if column not in numeric:
            continue

        values = numeric[column]

        mask = (
            values.notna()
            & (values <= 0)
        )

        add_check(
            summary_rows,
            example_rows,
            check_name=f"{column}_nonpositive_price",
            category="TRADE_PRICE",
            mask=mask,
            df=df,
            detail_columns=[column],
        )


    # =========================================================================
    # 5. NEGATIVE QUOTE PRICES
    # =========================================================================

    for name, group in QUOTE_GROUPS.items():

        for column in [
            group["bid"],
            group["ask"],
            group["mid"],
        ]:

            if column not in numeric:
                continue

            values = numeric[column]

            mask = (
                values.notna()
                & (values <= 0)
            )

            add_check(
                summary_rows,
                example_rows,
                check_name=f"{column}_nonpositive_quote_price",
                category="QUOTE_PRICE",
                mask=mask,
                df=df,
                detail_columns=[column],
            )


    # =========================================================================
    # 6. NEGATIVE VOLUMES
    # =========================================================================

    for column in VOLUME_FIELDS:

        if column not in numeric:
            continue

        values = numeric[column]

        mask = (
            values.notna()
            & (values < 0)
        )

        add_check(
            summary_rows,
            example_rows,
            check_name=f"{column}_negative_volume",
            category="VOLUME",
            mask=mask,
            df=df,
            detail_columns=[column],
        )


    # =========================================================================
    # 7. NEGATIVE VALUES / DOLLAR AMOUNTS
    # =========================================================================

    for column in VALUE_FIELDS:

        if column not in numeric:
            continue

        values = numeric[column]

        mask = (
            values.notna()
            & (values < 0)
        )

        add_check(
            summary_rows,
            example_rows,
            check_name=f"{column}_negative_value",
            category="DOLLAR_VALUE",
            mask=mask,
            df=df,
            detail_columns=[column],
        )


    # =========================================================================
    # 8. NON-NEGATIVE COUNT VALIDATION
    # =========================================================================

    for column in NONNEGATIVE_COUNT_FIELDS:

        if column not in numeric:
            continue

        values = numeric[column]

        mask = (
            values.notna()
            & (values < 0)
        )

        add_check(
            summary_rows,
            example_rows,
            check_name=f"{column}_negative_count",
            category="OBSERVATION_COUNT",
            mask=mask,
            df=df,
            detail_columns=[column],
        )


    # =========================================================================
    # 9. BUY/SELL TRADE COUNT CONSISTENCY
    # =========================================================================

    if all(
        column in numeric
        for column in [
            "BuyNumTrades_LR1",
            "SellNumTrades_LR1",
            "NumTrades_t",
        ]
    ):

        buy = numeric["BuyNumTrades_LR1"]
        sell = numeric["SellNumTrades_LR1"]
        total = numeric["NumTrades_t"]

        classified_total = buy + sell

        valid = (
            buy.notna()
            & sell.notna()
            & total.notna()
        )

        mask = (
            valid
            & (classified_total > total + PRICE_TOLERANCE)
        )

        add_check(
            summary_rows,
            example_rows,
            check_name="classified_trade_count_exceeds_total",
            category="TRADE_CLASSIFICATION",
            mask=mask,
            df=df,
            detail_columns=[
                "BuyNumTrades_LR1",
                "SellNumTrades_LR1",
                "NumTrades_t",
            ],
        )


    # =========================================================================
    # 10. BUY/SELL VOLUME CONSISTENCY
    # =========================================================================

    if all(
        column in numeric
        for column in [
            "BuyVol_LR1",
            "SellVol_LR1",
            "SumVolume_t",
        ]
    ):

        buy = numeric["BuyVol_LR1"]
        sell = numeric["SellVol_LR1"]
        total = numeric["SumVolume_t"]

        classified_total = buy + sell

        valid = (
            buy.notna()
            & sell.notna()
            & total.notna()
        )

        mask = (
            valid
            & (classified_total > total + PRICE_TOLERANCE)
        )

        add_check(
            summary_rows,
            example_rows,
            check_name="classified_trade_volume_exceeds_total",
            category="TRADE_CLASSIFICATION",
            mask=mask,
            df=df,
            detail_columns=[
                "BuyVol_LR1",
                "SellVol_LR1",
                "SumVolume_t",
            ],
        )


    # =========================================================================
    # 11. BUY/SELL DOLLAR CONSISTENCY
    # =========================================================================

    if all(
        column in numeric
        for column in [
            "BuyDollar_LR1",
            "SellDollar_LR1",
            "SumValue_t",
        ]
    ):

        buy = numeric["BuyDollar_LR1"]
        sell = numeric["SellDollar_LR1"]
        total = numeric["SumValue_t"]

        classified_total = buy + sell

        valid = (
            buy.notna()
            & sell.notna()
            & total.notna()
        )

        mask = (
            valid
            & (classified_total > total + PRICE_TOLERANCE)
        )

        add_check(
            summary_rows,
            example_rows,
            check_name="classified_trade_value_exceeds_total",
            category="TRADE_CLASSIFICATION",
            mask=mask,
            df=df,
            detail_columns=[
                "BuyDollar_LR1",
                "SellDollar_LR1",
                "SumValue_t",
            ],
        )


    # =========================================================================
    # 12. ISO / ODD-LOT / MIXED-LOT VOLUME COMPONENT CHECK
    # =========================================================================

    volume_components = [
        "SumISOVolume_m",
        "SumOddLotVolume_m",
        "SumMixedLotVolume_m",
    ]

    if all(
        column in numeric
        for column in volume_components + ["SumVolume_m"]
    ):

        components = sum(
            numeric[column]
            for column in volume_components
        )

        total = numeric["SumVolume_m"]

        valid = (
            components.notna()
            & total.notna()
        )

        mask = (
            valid
            & (components > total + PRICE_TOLERANCE)
        )

        add_check(
            summary_rows,
            example_rows,
            check_name="lot_classification_volume_exceeds_total",
            category="LOT_CLASSIFICATION",
            mask=mask,
            df=df,
            detail_columns=[
                "SumVolume_m",
                *volume_components,
            ],
        )


    # =========================================================================
    # 13. ISO / ODD-LOT / MIXED-LOT VALUE COMPONENT CHECK
    # =========================================================================

    value_components = [
        "SumISOValue_m",
        "SumOddLotValue_m",
        "SumMixedLotValue_m",
    ]

    if all(
        column in numeric
        for column in value_components + ["SumValue_m"]
    ):

        components = sum(
            numeric[column]
            for column in value_components
        )

        total = numeric["SumValue_m"]

        valid = (
            components.notna()
            & total.notna()
        )

        mask = (
            valid
            & (components > total + PRICE_TOLERANCE)
        )

        add_check(
            summary_rows,
            example_rows,
            check_name="lot_classification_value_exceeds_total",
            category="LOT_CLASSIFICATION",
            mask=mask,
            df=df,
            detail_columns=[
                "SumValue_m",
                *value_components,
            ],
        )


    # =========================================================================
    # 14. TRADE TIMESTAMP ORDERING
    #
    # Only test relationships where ordering is conceptually meaningful.
    # These are diagnostics, not assumed cleaning rules.
    # =========================================================================

    timestamp_data = {}

    for column in TIMESTAMP_FIELDS:

        if column not in df.columns:
            continue

        timestamp_data[column] = pd.to_timedelta(
            df[column].astype(str),
            errors="coerce",
        )


    timestamp_pairs = [
        ("OTime", "DTime", "open_time_after_d_time"),
        ("DTime", "TTime_4pm", "d_time_after_4pm_trade_time"),
        ("TTime_1pm", "TTime_4pm", "1pm_trade_after_4pm_trade"),
    ]

    for first, second, check_name in timestamp_pairs:

        if first not in timestamp_data or second not in timestamp_data:
            continue

        first_time = timestamp_data[first]
        second_time = timestamp_data[second]

        valid = (
            first_time.notna()
            & second_time.notna()
        )

        mask = (
            valid
            & (first_time > second_time)
        )

        add_check(
            summary_rows,
            example_rows,
            check_name=check_name,
            category="TIMESTAMP_ORDER",
            mask=mask,
            df=df,
            detail_columns=[first, second],
        )


    # =========================================================================
    # 15. TTIME 1PM SHOULD NOT BE AFTER 4PM
    # =========================================================================

    if (
        "TTime_1pm" in timestamp_data
        and "TTime_4pm" in timestamp_data
    ):

        first = timestamp_data["TTime_1pm"]
        second = timestamp_data["TTime_4pm"]

        valid = (
            first.notna()
            & second.notna()
        )

        mask = (
            valid
            & (first > second)
        )

        add_check(
            summary_rows,
            example_rows,
            check_name="TTime_1pm_after_TTime_4pm",
            category="TIMESTAMP_ORDER",
            mask=mask,
            df=df,
            detail_columns=[
                "TTime_1pm",
                "TTime_4pm",
            ],
        )


    # =========================================================================
    # 16. QUOTE TIME ORDERING
    # =========================================================================

    quote_time_pairs = [
        ("QTime_1pm", "QTime_c1", "QTime_1pm_after_QTime_c1"),
        ("QTime_c1", "QTime_4pm", "QTime_c1_after_QTime_4pm"),
    ]

    for first, second, check_name in quote_time_pairs:

        if first not in timestamp_data or second not in timestamp_data:
            continue

        first_time = timestamp_data[first]
        second_time = timestamp_data[second]

        valid = (
            first_time.notna()
            & second_time.notna()
        )

        mask = (
            valid
            & (first_time > second_time)
        )

        add_check(
            summary_rows,
            example_rows,
            check_name=check_name,
            category="QUOTE_TIME_ORDER",
            mask=mask,
            df=df,
            detail_columns=[first, second],
        )


# =============================================================================
# SUMMARY
# =============================================================================

summary_df = pd.DataFrame(summary_rows)

if not summary_df.empty:

    summary_df = (
        summary_df
        .groupby(
            [
                "check_name",
                "category",
            ],
            as_index=False
        )
        .agg(
            rows_observed=("rows_observed", "sum"),
            violation_count=("violation_count", "sum"),
        )
    )

    summary_df["violation_rate"] = (
        summary_df["violation_count"]
        / summary_df["rows_observed"]
    )

else:

    summary_df = pd.DataFrame(
        columns=[
            "check_name",
            "category",
            "rows_observed",
            "violation_count",
            "violation_rate",
        ]
    )


# =============================================================================
# EXAMPLES
# =============================================================================

examples_df = pd.DataFrame(example_rows)


# =============================================================================
# SAVE OUTPUTS
# =============================================================================

summary_df.to_csv(
    SUMMARY_FILE,
    index=False,
)

examples_df.to_csv(
    EXAMPLES_FILE,
    index=False,
)

summary_df.to_csv(
    OUTPUT_FILE,
    index=False,
)


# =============================================================================
# REPORT
# =============================================================================

print()
print("=" * 80)
print("CROSS-FIELD VALIDATION SUMMARY")
print("=" * 80)

print(
    f"Total rows processed: {total_rows:,}"
)

print(
    f"Validation checks:    {len(summary_df):,}"
)

total_violations = (
    int(summary_df["violation_count"].sum())
    if not summary_df.empty
    else 0
)

print(
    f"Total violations:     {total_violations:,}"
)

print()

if not summary_df.empty:

    display_df = (
        summary_df[
            summary_df["violation_count"] > 0
        ]
        .sort_values(
            "violation_count",
            ascending=False
        )
    )

    if display_df.empty:

        print(
            "PASS — no cross-field violations detected "
            "under the defined diagnostic rules."
        )

    else:

        print(
            "CHECK — cross-field exceptions detected:"
        )

        print(
            display_df.to_string(
                index=False
            )
        )

else:

    print(
        "WARNING — no validation results generated."
    )


print()
print("=" * 80)
print("OUTPUTS")
print("=" * 80)

print("Cross-field validation:")
print(OUTPUT_FILE)

print("Cross-field validation summary:")
print(SUMMARY_FILE)

print("Cross-field validation examples:")
print(EXAMPLES_FILE)

print()
print("=" * 80)
print("STATUS")
print("=" * 80)

print(
    "PASS — cross-field diagnostic processing completed."
)

print()
print(
    "IMPORTANT:"
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
    "No cleaning rules were applied."
)

print(
    "Any detected violations require semantic review "
    "before exclusion or correction."
)