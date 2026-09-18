from pathlib import Path
import pandas as pd
import numpy as np

# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "taq"
    / "taq.csv"
)

CLEAN_FILE = (
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
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# OUTPUT FILES
# =============================================================================

DETAILED_FILE = OUTPUT_DIR / "taq_post_clean_validation_detailed.csv"
MISSINGNESS_FILE = OUTPUT_DIR / "taq_post_clean_missingness.csv"
RANGE_FILE = OUTPUT_DIR / "taq_post_clean_range_checks.csv"
CROSSFIELD_FILE = OUTPUT_DIR / "taq_post_clean_crossfield_checks.csv"
SYMBOL_FILE = OUTPUT_DIR / "taq_post_clean_symbol_coverage.csv"
DATE_FILE = OUTPUT_DIR / "taq_post_clean_date_coverage.csv"
SUMMARY_FILE = OUTPUT_DIR / "taq_post_clean_validation_summary.csv"


# =============================================================================
# CONFIGURATION
# =============================================================================

CHUNK_SIZE = 100_000

DATE_COLUMN = "date"
SYMBOL_COLUMN = "symbol"

TIME_COLUMNS = [
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

# These contain observation counts rather than timestamps.
OBSERVATION_COUNT_COLUMNS = [
    "NObsUsed1",
    "NObsUsed2",
    "NumTimeUnitsWithTrade1",
    "NumTimeUnitsWithTrade2",
]

QUOTE_COLUMNS = [
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
    "CPrc",
    "CPrc2",
]

TRADE_PRICE_COLUMNS = [
    "OPrice",
    "DPrice",
    "LPrice",
    "Price_1pm",
    "Price_4pm",
]

POSITIVE_ACTIVITY_COLUMNS = [
    "Vol_oc",
    "Value_oc",
    "MFCount",
    "NumTrades_t",
    "NumTrades_m",
    "SumVolume_t",
    "SumVolume_m",
    "SumValue_b",
    "SumValue_m",
    "NumISOTrades_m",
    "SumISOVolume_m",
    "SumISOValue_m",
    "NumOddLotTrades_m",
    "SumOddLotVolume_m",
    "SumOddLotValue_m",
    "NumMixedLotTrades_m",
    "SumMixedLotVolume_m",
    "SumMixedLotValue_m",
    "BuyNumTrades_LR1",
    "SellNumTrades_LR1",
    "BuyVol_LR1",
    "SellVol_LR1",
    "BuyDollar_LR1",
    "SellDollar_LR1",
]

EXECUTION_METRIC_COLUMNS = [
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

RETURN_COLUMNS = [
    "Ret_pre_t",
    "Ret_mkt_t",
    "Ret_post_t",
]

MARKET_STAT_COLUMNS = [
    "IVol_t_m",
    "IVol_q_m",
    "VarianceRatio1",
    "VarianceRatio2",
    "HIndex1",
]

TRADE_DIRECTION_COLUMNS = [
    "TSignSqrtDVol1",
    "TSignSqrtDVol2",
]


# =============================================================================
# HELPERS
# =============================================================================

def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def safe_datetime(series):
    return pd.to_datetime(series, errors="coerce")


def add_check(
    records,
    check_name,
    category,
    status,
    observed,
    threshold=None,
    details=""
):
    records.append(
        {
            "check_name": check_name,
            "category": category,
            "status": status,
            "observed": observed,
            "threshold": threshold,
            "details": details,
        }
    )


# =============================================================================
# PRELIMINARY CHECKS
# =============================================================================

print("=" * 80)
print("PHASE 5 — STEP 6: POST-CLEAN TAQ VALIDATION")
print("=" * 80)

if not CLEAN_FILE.exists():
    raise FileNotFoundError(
        f"Cleaned TAQ file not found:\n{CLEAN_FILE}"
    )

if not RAW_FILE.exists():
    raise FileNotFoundError(
        f"Raw TAQ file not found:\n{RAW_FILE}"
    )

print(f"Clean file: {CLEAN_FILE}")
print(f"Raw file:   {RAW_FILE}")
print()


# =============================================================================
# LOAD CLEANED DATA
# =============================================================================

print("=" * 80)
print("LOADING CLEANED TAQ")
print("=" * 80)

clean_header = pd.read_csv(CLEAN_FILE, nrows=0)
clean_columns = list(clean_header.columns)

print(f"Cleaned columns: {len(clean_columns)}")
print()

if DATE_COLUMN not in clean_columns:
    raise ValueError("Cleaned TAQ does not contain 'date'.")

if SYMBOL_COLUMN not in clean_columns:
    raise ValueError("Cleaned TAQ does not contain 'symbol'.")


# =============================================================================
# LOAD RAW HEADER
# =============================================================================

raw_header = pd.read_csv(RAW_FILE, nrows=0)
raw_columns = list(raw_header.columns)

print(f"Raw columns:     {len(raw_columns)}")
print()


# =============================================================================
# SCHEMA VALIDATION
# =============================================================================

validation_records = []

missing_columns = [
    c for c in raw_columns
    if c not in clean_columns
]

unexpected_columns = [
    c for c in clean_columns
    if c not in raw_columns
]

if not missing_columns and not unexpected_columns:
    schema_status = "PASS"
else:
    schema_status = "FAIL"

add_check(
    validation_records,
    "schema_preservation",
    "SCHEMA",
    schema_status,
    len(clean_columns),
    len(raw_columns),
    (
        f"Missing from cleaned: {missing_columns}; "
        f"Unexpected in cleaned: {unexpected_columns}"
    )
)

print("=" * 80)
print("SCHEMA CHECK")
print("=" * 80)
print(f"Raw columns:      {len(raw_columns)}")
print(f"Cleaned columns:  {len(clean_columns)}")
print(f"Missing columns:  {len(missing_columns)}")
print(f"Unexpected cols:  {len(unexpected_columns)}")
print()


# =============================================================================
# ROW COUNT VALIDATION
# =============================================================================

print("=" * 80)
print("ROW COUNT VALIDATION")
print("=" * 80)

raw_rows = 0

for chunk in pd.read_csv(
    RAW_FILE,
    usecols=[DATE_COLUMN, SYMBOL_COLUMN],
    chunksize=CHUNK_SIZE,
    low_memory=False,
):
    raw_rows += len(chunk)

clean_rows = 0

for chunk in pd.read_csv(
    CLEAN_FILE,
    usecols=[DATE_COLUMN, SYMBOL_COLUMN],
    chunksize=CHUNK_SIZE,
    low_memory=False,
):
    clean_rows += len(chunk)

row_difference = clean_rows - raw_rows

row_status = "PASS" if row_difference == 0 else "REVIEW"

add_check(
    validation_records,
    "row_count_preservation",
    "STRUCTURAL",
    row_status,
    clean_rows,
    raw_rows,
    f"Difference = {row_difference}"
)

print(f"Raw rows:       {raw_rows:,}")
print(f"Cleaned rows:   {clean_rows:,}")
print(f"Difference:     {row_difference:,}")
print()


# =============================================================================
# ACCUMULATORS
# =============================================================================

missingness_records = []
range_records = []
crossfield_records = []

symbol_counts = {}
date_counts = {}

clean_date_min = None
clean_date_max = None

duplicate_date_symbol = 0

global_missing_counts = {
    column: 0 for column in clean_columns
}

global_negative_counts = {
    column: 0
    for column in clean_columns
}

global_zero_counts = {
    column: 0
    for column in clean_columns
}

global_non_numeric_counts = {
    column: 0
    for column in clean_columns
}

global_quote_violations = {
    "BB_gt_BO": 0,
    "MID_not_between_bid_ask": 0,
    "BB_nonpositive": 0,
    "BO_nonpositive": 0,
}

global_activity_negative = 0
global_price_negative = 0

date_symbol_seen = set()


# =============================================================================
# CHUNKED VALIDATION
# =============================================================================

print("=" * 80)
print("CHUNKED VALIDATION")
print("=" * 80)

chunk_number = 0

for chunk in pd.read_csv(
    CLEAN_FILE,
    chunksize=CHUNK_SIZE,
    low_memory=False,
):

    chunk_number += 1

    print(
        f"Processing validation chunk {chunk_number}: "
        f"{len(chunk):,} rows"
    )

    # -------------------------------------------------------------------------
    # Date validation
    # -------------------------------------------------------------------------

    dates = pd.to_datetime(
        chunk[DATE_COLUMN],
        errors="coerce"
    )

    if dates.notna().any():

        chunk_min = dates.min()
        chunk_max = dates.max()

        if clean_date_min is None or chunk_min < clean_date_min:
            clean_date_min = chunk_min

        if clean_date_max is None or chunk_max > clean_date_max:
            clean_date_max = chunk_max

    invalid_dates = dates.isna().sum()

    add_check(
        validation_records,
        f"date_parse_chunk_{chunk_number}",
        "DATE",
        "PASS" if invalid_dates == 0 else "FAIL",
        int(invalid_dates),
        0,
        "Date values that cannot be parsed."
    )

    # -------------------------------------------------------------------------
    # Symbol validation
    # -------------------------------------------------------------------------

    symbols = chunk[SYMBOL_COLUMN]

    missing_symbols = symbols.isna().sum()

    add_check(
        validation_records,
        f"symbol_missing_chunk_{chunk_number}",
        "IDENTIFIER",
        "PASS" if missing_symbols == 0 else "FAIL",
        int(missing_symbols),
        0,
        "Missing security identifiers."
    )

    for symbol, count in symbols.value_counts(dropna=False).items():
        if pd.notna(symbol):
            symbol_counts[str(symbol)] = (
                symbol_counts.get(str(symbol), 0) + int(count)
            )

    # -------------------------------------------------------------------------
    # Date counts
    # -------------------------------------------------------------------------

    for date_value, count in dates.value_counts(dropna=True).items():
        date_key = date_value.strftime("%Y-%m-%d")
        date_counts[date_key] = (
            date_counts.get(date_key, 0) + int(count)
        )

    # -------------------------------------------------------------------------
    # Date-symbol uniqueness
    # -------------------------------------------------------------------------

    key_frame = chunk[
        [DATE_COLUMN, SYMBOL_COLUMN]
    ].copy()

    key_frame[DATE_COLUMN] = dates

    duplicated = key_frame.duplicated(
        subset=[DATE_COLUMN, SYMBOL_COLUMN],
        keep=False
    )

    duplicate_count = int(duplicated.sum())

    duplicate_date_symbol += duplicate_count

    # -------------------------------------------------------------------------
    # Missingness
    # -------------------------------------------------------------------------

    missing_counts = chunk.isna().sum()

    for column in clean_columns:
        global_missing_counts[column] += int(
            missing_counts.get(column, 0)
        )

    # -------------------------------------------------------------------------
    # Numeric diagnostics
    # -------------------------------------------------------------------------

    numeric_candidates = (
        QUOTE_COLUMNS
        + TRADE_PRICE_COLUMNS
        + POSITIVE_ACTIVITY_COLUMNS
        + EXECUTION_METRIC_COLUMNS
        + RETURN_COLUMNS
        + MARKET_STAT_COLUMNS
        + TRADE_DIRECTION_COLUMNS
        + OBSERVATION_COUNT_COLUMNS
    )

    numeric_candidates = [
        c for c in numeric_candidates
        if c in chunk.columns
    ]

    for column in numeric_candidates:

        numeric = safe_numeric(chunk[column])

        non_numeric = (
            chunk[column].notna()
            & numeric.isna()
        ).sum()

        global_non_numeric_counts[column] += int(non_numeric)

        negative = (numeric < 0).sum()
        zero = (numeric == 0).sum()

        global_negative_counts[column] += int(negative)
        global_zero_counts[column] += int(zero)

    # -------------------------------------------------------------------------
    # Quote consistency
    # -------------------------------------------------------------------------

    quote_triplets = [
        ("BB_1pm", "BO_1pm", "MID_1pm"),
        ("BB_c1", "BO_c1", "Mid_c1"),
        ("BB_4pm", "BO_4pm", "Mid_4pm"),
        ("LBB", "LBO", "LMid"),
    ]

    for bid_col, ask_col, mid_col in quote_triplets:

        if all(
            c in chunk.columns
            for c in [bid_col, ask_col, mid_col]
        ):

            bid = safe_numeric(chunk[bid_col])
            ask = safe_numeric(chunk[ask_col])
            mid = safe_numeric(chunk[mid_col])

            valid = (
                bid.notna()
                & ask.notna()
            )

            global_quote_violations["BB_gt_BO"] += int(
                ((bid > ask) & valid).sum()
            )

            global_quote_violations["BB_nonpositive"] += int(
                ((bid <= 0) & bid.notna()).sum()
            )

            global_quote_violations["BO_nonpositive"] += int(
                ((ask <= 0) & ask.notna()).sum()
            )

            mid_valid = (
                mid.notna()
                & bid.notna()
                & ask.notna()
            )

            global_quote_violations["MID_not_between_bid_ask"] += int(
                (
                    (
                        (mid < bid)
                        | (mid > ask)
                    )
                    & mid_valid
                ).sum()
            )

    # -------------------------------------------------------------------------
    # Positive-only activity fields
    # -------------------------------------------------------------------------

    for column in POSITIVE_ACTIVITY_COLUMNS:

        if column not in chunk.columns:
            continue

        numeric = safe_numeric(chunk[column])

        global_activity_negative += int(
            (numeric < 0).sum()
        )

    # -------------------------------------------------------------------------
    # Price fields
    # -------------------------------------------------------------------------

    price_columns = [
        c for c in QUOTE_COLUMNS + TRADE_PRICE_COLUMNS
        if c in chunk.columns
    ]

    for column in price_columns:

        numeric = safe_numeric(chunk[column])

        global_price_negative += int(
            (numeric < 0).sum()
        )


# =============================================================================
# MISSINGNESS OUTPUT
# =============================================================================

for column in clean_columns:

    count = global_missing_counts[column]

    missingness_records.append(
        {
            "column": column,
            "missing_count": count,
            "missing_rate": (
                count / clean_rows
                if clean_rows > 0
                else np.nan
            ),
        }
    )

missingness_df = pd.DataFrame(
    missingness_records
).sort_values(
    "missing_rate",
    ascending=False
)


# =============================================================================
# RANGE / NUMERIC OUTPUT
# =============================================================================

for column in clean_columns:

    if column not in (
        QUOTE_COLUMNS
        + TRADE_PRICE_COLUMNS
        + POSITIVE_ACTIVITY_COLUMNS
        + EXECUTION_METRIC_COLUMNS
        + RETURN_COLUMNS
        + MARKET_STAT_COLUMNS
        + TRADE_DIRECTION_COLUMNS
        + OBSERVATION_COUNT_COLUMNS
    ):
        continue

    missing = global_missing_counts[column]
    negative = global_negative_counts[column]
    zero = global_zero_counts[column]
    non_numeric = global_non_numeric_counts[column]

    if column in QUOTE_COLUMNS or column in TRADE_PRICE_COLUMNS:
        rule = "PRICE >= 0"
        violations = negative

    elif column in POSITIVE_ACTIVITY_COLUMNS:
        rule = "ACTIVITY >= 0"
        violations = negative

    elif column in EXECUTION_METRIC_COLUMNS:
        rule = "SIGNED / SEMANTICALLY REVIEWED"
        violations = negative

    elif column in RETURN_COLUMNS:
        rule = "SIGNED / SEMANTICALLY VALID"
        violations = negative

    elif column in TRADE_DIRECTION_COLUMNS:
        rule = "SIGNED / SEMANTICALLY VALID"
        violations = negative

    else:
        rule = "NONNEGATIVE OBSERVATION / MARKET FIELD"
        violations = negative

    range_records.append(
        {
            "column": column,
            "missing_count": missing,
            "negative_count": negative,
            "zero_count": zero,
            "non_numeric_count": non_numeric,
            "validation_rule": rule,
            "rule_violation_count": violations,
        }
    )

range_df = pd.DataFrame(range_records)


# =============================================================================
# CROSS-FIELD CHECKS
# =============================================================================

crossfield_records.extend(
    [
        {
            "check_name": "quote_bid_ask_order",
            "violations": global_quote_violations["BB_gt_BO"],
            "rule": "Bid must not exceed Ask",
            "status": (
                "PASS"
                if global_quote_violations["BB_gt_BO"] == 0
                else "REVIEW"
            ),
        },
        {
            "check_name": "quote_midpoint_bounds",
            "violations": global_quote_violations[
                "MID_not_between_bid_ask"
            ],
            "rule": "Midpoint should lie between Bid and Ask",
            "status": (
                "PASS"
                if global_quote_violations[
                    "MID_not_between_bid_ask"
                ] == 0
                else "REVIEW"
            ),
        },
        {
            "check_name": "quote_bid_positive",
            "violations": global_quote_violations[
                "BB_nonpositive"
            ],
            "rule": "Bid should be positive when observed",
            "status": (
                "PASS"
                if global_quote_violations["BB_nonpositive"] == 0
                else "REVIEW"
            ),
        },
        {
            "check_name": "quote_ask_positive",
            "violations": global_quote_violations[
                "BO_nonpositive"
            ],
            "rule": "Ask should be positive when observed",
            "status": (
                "PASS"
                if global_quote_violations["BO_nonpositive"] == 0
                else "REVIEW"
            ),
        },
        {
            "check_name": "positive_activity_fields",
            "violations": global_activity_negative,
            "rule": "Activity/count/value fields must be nonnegative",
            "status": (
                "PASS"
                if global_activity_negative == 0
                else "FAIL"
            ),
        },
        {
            "check_name": "price_fields_nonnegative",
            "violations": global_price_negative,
            "rule": "Observed price fields must be nonnegative",
            "status": (
                "PASS"
                if global_price_negative == 0
                else "FAIL"
            ),
        },
        {
            "check_name": "date_symbol_duplicate_candidates",
            "violations": duplicate_date_symbol,
            "rule": "One canonical observation per date-symbol",
            "status": (
                "PASS"
                if duplicate_date_symbol == 0
                else "REVIEW"
            ),
        },
    ]
)

crossfield_df = pd.DataFrame(crossfield_records)


# =============================================================================
# SYMBOL COVERAGE
# =============================================================================

symbol_df = pd.DataFrame(
    [
        {
            "symbol": symbol,
            "row_count": count,
            "row_rate": count / clean_rows,
        }
        for symbol, count in sorted(symbol_counts.items())
    ]
)

symbol_df.to_csv(
    SYMBOL_FILE,
    index=False
)


# =============================================================================
# DATE COVERAGE
# =============================================================================

date_df = pd.DataFrame(
    [
        {
            "date": date,
            "row_count": count,
        }
        for date, count in sorted(date_counts.items())
    ]
)

if not date_df.empty:

    date_df["date"] = pd.to_datetime(
        date_df["date"]
    )

    date_df["weekday"] = date_df["date"].dt.day_name()

    date_df["date_gap_days"] = (
        date_df["date"]
        .diff()
        .dt.days
    )

date_df.to_csv(
    DATE_FILE,
    index=False
)


# =============================================================================
# SUMMARY STATUS
# =============================================================================

critical_failures = 0
review_items = 0

for record in validation_records:

    if record["status"] == "FAIL":
        critical_failures += 1

    elif record["status"] == "REVIEW":
        review_items += 1


for record in crossfield_records:

    if record["status"] == "FAIL":
        critical_failures += 1

    elif record["status"] == "REVIEW":
        review_items += 1


# Missing dates
missing_date_rows = (
    global_missing_counts.get(DATE_COLUMN, 0)
)

if missing_date_rows > 0:
    critical_failures += 1


# Missing symbols
missing_symbol_rows = (
    global_missing_counts.get(SYMBOL_COLUMN, 0)
)

if missing_symbol_rows > 0:
    critical_failures += 1


if critical_failures > 0:
    overall_status = "FAIL"

elif review_items > 0:
    overall_status = "REVIEW"

else:
    overall_status = "PASS"


# =============================================================================
# VALIDATION SUMMARY
# =============================================================================

summary_records = [
    {
        "metric": "raw_row_count",
        "value": raw_rows,
    },
    {
        "metric": "cleaned_row_count",
        "value": clean_rows,
    },
    {
        "metric": "row_count_difference",
        "value": row_difference,
    },
    {
        "metric": "cleaned_column_count",
        "value": len(clean_columns),
    },
    {
        "metric": "raw_column_count",
        "value": len(raw_columns),
    },
    {
        "metric": "unique_symbols",
        "value": len(symbol_counts),
    },
    {
        "metric": "unique_dates",
        "value": len(date_counts),
    },
    {
        "metric": "first_date",
        "value": (
            clean_date_min.strftime("%Y-%m-%d")
            if clean_date_min is not None
            else None
        ),
    },
    {
        "metric": "last_date",
        "value": (
            clean_date_max.strftime("%Y-%m-%d")
            if clean_date_max is not None
            else None
        ),
    },
    {
        "metric": "missing_date_rows",
        "value": missing_date_rows,
    },
    {
        "metric": "missing_symbol_rows",
        "value": missing_symbol_rows,
    },
    {
        "metric": "date_symbol_duplicate_candidates",
        "value": duplicate_date_symbol,
    },
    {
        "metric": "quote_bid_gt_ask",
        "value": global_quote_violations["BB_gt_BO"],
    },
    {
        "metric": "midpoint_outside_bid_ask",
        "value": global_quote_violations[
            "MID_not_between_bid_ask"
        ],
    },
    {
        "metric": "nonpositive_bid",
        "value": global_quote_violations[
            "BB_nonpositive"
        ],
    },
    {
        "metric": "nonpositive_ask",
        "value": global_quote_violations[
            "BO_nonpositive"
        ],
    },
    {
        "metric": "negative_activity_values",
        "value": global_activity_negative,
    },
    {
        "metric": "negative_price_values",
        "value": global_price_negative,
    },
    {
        "metric": "critical_failures",
        "value": critical_failures,
    },
    {
        "metric": "review_items",
        "value": review_items,
    },
    {
        "metric": "overall_status",
        "value": overall_status,
    },
]

summary_df = pd.DataFrame(summary_records)


# =============================================================================
# WRITE OUTPUTS
# =============================================================================

validation_df = pd.DataFrame(validation_records)

validation_df.to_csv(
    DETAILED_FILE,
    index=False
)

missingness_df.to_csv(
    MISSINGNESS_FILE,
    index=False
)

range_df.to_csv(
    RANGE_FILE,
    index=False
)

crossfield_df.to_csv(
    CROSSFIELD_FILE,
    index=False
)

summary_df.to_csv(
    SUMMARY_FILE,
    index=False
)


# =============================================================================
# CONSOLE REPORT
# =============================================================================

print()
print("=" * 80)
print("POST-CLEAN VALIDATION SUMMARY")
print("=" * 80)

print(f"Raw rows:                     {raw_rows:,}")
print(f"Cleaned rows:                 {clean_rows:,}")
print(f"Row difference:               {row_difference:,}")
print(f"Columns:                      {len(clean_columns)}")
print(f"Unique symbols:               {len(symbol_counts):,}")
print(f"Unique dates:                 {len(date_counts):,}")

print(
    f"First date:                   "
    f"{clean_date_min}"
)

print(
    f"Last date:                    "
    f"{clean_date_max}"
)

print(
    f"Date-symbol duplicates:       "
    f"{duplicate_date_symbol:,}"
)

print(
    f"Bid > Ask violations:         "
    f"{global_quote_violations['BB_gt_BO']:,}"
)

print(
    f"Midpoint violations:          "
    f"{global_quote_violations['MID_not_between_bid_ask']:,}"
)

print(
    f"Negative activity values:     "
    f"{global_activity_negative:,}"
)

print(
    f"Negative price values:        "
    f"{global_price_negative:,}"
)

print()
print(f"Critical failures:            {critical_failures}")
print(f"Review items:                 {review_items}")

print()
print("=" * 80)
print(f"OVERALL STATUS: {overall_status}")
print("=" * 80)

print()
print("OUTPUTS")
print("=" * 80)

print(f"Detailed validation:")
print(DETAILED_FILE)

print()
print(f"Missingness:")
print(MISSINGNESS_FILE)

print()
print(f"Range checks:")
print(RANGE_FILE)

print()
print(f"Cross-field checks:")
print(CROSSFIELD_FILE)

print()
print(f"Symbol coverage:")
print(SYMBOL_FILE)

print()
print(f"Date coverage:")
print(DATE_FILE)

print()
print(f"Validation summary:")
print(SUMMARY_FILE)

print()
print("=" * 80)
print("STATUS")
print("=" * 80)

if overall_status == "PASS":

    print(
        "PASS — cleaned TAQ passed all automated "
        "post-clean validation checks."
    )

elif overall_status == "REVIEW":

    print(
        "REVIEW — cleaned TAQ contains observations "
        "requiring semantic review."
    )

else:

    print(
        "FAIL — cleaned TAQ contains structural or "
        "data-quality violations requiring investigation."
    )

print()
print("IMPORTANT:")
print("No observations were removed.")
print("No values were modified.")
print("No imputation was performed.")
print("This step is validation only.")