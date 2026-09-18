from pathlib import Path
import pandas as pd
import numpy as np

# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "taq"
)

INPUT_FILE = DATA_DIR / "taq_cleaned.csv"

OUTPUT_DIR = DATA_DIR / "quote_semantic_investigation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Output files
SUMMARY_FILE = OUTPUT_DIR / "taq_quote_semantic_summary.csv"
SET_SUMMARY_FILE = OUTPUT_DIR / "taq_quote_set_violation_summary.csv"
SYMBOL_SUMMARY_FILE = OUTPUT_DIR / "taq_quote_violation_by_symbol.csv"
DATE_SUMMARY_FILE = OUTPUT_DIR / "taq_quote_violation_by_date.csv"
EXAMPLE_FILE = OUTPUT_DIR / "taq_quote_violation_examples.csv"
MAGNITUDE_FILE = OUTPUT_DIR / "taq_quote_violation_magnitude.csv"
MIDPOINT_FILE = OUTPUT_DIR / "taq_quote_midpoint_diagnostic.csv"
CONSISTENCY_FILE = OUTPUT_DIR / "taq_quote_semantic_consistency.csv"


# =============================================================================
# CONFIGURATION
# =============================================================================

CHUNK_SIZE = 100_000

QUOTE_SETS = {
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
    "last": {
        "bid": "LBB",
        "ask": "LBO",
        "mid": "LMid",
        "time": "LQTime",
    },
}


# =============================================================================
# HELPERS
# =============================================================================

def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def add_seconds_column(df, time_col):
    """
    Convert a time-only field into seconds from midnight.
    """
    parsed = pd.to_timedelta(df[time_col], errors="coerce")

    return (
        parsed.dt.total_seconds()
        if isinstance(parsed, pd.Series)
        else pd.Series(np.nan, index=df.index)
    )


def build_violation_mask(df, bid_col, ask_col):
    """
    Bid > Ask only when both fields are present.
    """
    bid = safe_numeric(df[bid_col])
    ask = safe_numeric(df[ask_col])

    return (
        bid.notna()
        & ask.notna()
        & (bid > ask)
    )


# =============================================================================
# LOAD / INITIALIZE
# =============================================================================

print("=" * 80)
print("PHASE 5 — STEP 6: TAQ QUOTE SEMANTIC INVESTIGATION")
print("=" * 80)

print(f"Input file:")
print(f"  {INPUT_FILE}")

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Cleaned TAQ file not found:\n{INPUT_FILE}"
    )


required_columns = {
    "date",
    "symbol",
}

for quote_set, fields in QUOTE_SETS.items():
    required_columns.update(fields.values())


# =============================================================================
# STORAGE
# =============================================================================

global_rows = 0

quote_set_records = []
symbol_records = []
date_records = []
magnitude_records = []

example_frames = []

midpoint_records = []

semantic_records = []


# =============================================================================
# CHUNKED PROCESSING
# =============================================================================

reader = pd.read_csv(
    INPUT_FILE,
    chunksize=CHUNK_SIZE,
    low_memory=False,
)

for chunk_number, df in enumerate(reader, start=1):

    print(
        f"Processing chunk {chunk_number}: "
        f"{len(df):,} rows"
    )

    global_rows += len(df)

    missing_required = required_columns - set(df.columns)

    if missing_required:
        raise ValueError(
            "Missing required columns:\n"
            + "\n".join(sorted(missing_required))
        )

    # -------------------------------------------------------------------------
    # Normalize basic identifiers
    # -------------------------------------------------------------------------

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    df["symbol"] = (
        df["symbol"]
        .astype("string")
        .str.strip()
    )

    # -------------------------------------------------------------------------
    # Investigate each quote set
    # -------------------------------------------------------------------------

    for quote_set, fields in QUOTE_SETS.items():

        bid_col = fields["bid"]
        ask_col = fields["ask"]
        mid_col = fields["mid"]
        time_col = fields["time"]

        bid = safe_numeric(df[bid_col])
        ask = safe_numeric(df[ask_col])
        mid = safe_numeric(df[mid_col])

        non_null = (
            bid.notna()
            & ask.notna()
        )

        violation = (
            non_null
            & (bid > ask)
        )

        violation_count = int(violation.sum())

        # ---------------------------------------------------------------------
        # Basic quote-set statistics
        # ---------------------------------------------------------------------

        quote_set_records.append({
            "quote_set": quote_set,
            "rows": len(df),
            "non_null_bid_ask_rows": int(non_null.sum()),
            "bid_greater_than_ask": violation_count,
            "violation_rate_all_rows": (
                violation_count / len(df)
                if len(df) > 0
                else np.nan
            ),
            "violation_rate_non_null_bid_ask": (
                violation_count / int(non_null.sum())
                if int(non_null.sum()) > 0
                else np.nan
            ),
            "bid_missing": int(bid.isna().sum()),
            "ask_missing": int(ask.isna().sum()),
            "mid_missing": int(mid.isna().sum()),
        })

        # ---------------------------------------------------------------------
        # Midpoint diagnostic
        # ---------------------------------------------------------------------

        midpoint_expected = (bid + ask) / 2

        midpoint_available = (
            bid.notna()
            & ask.notna()
            & mid.notna()
        )

        midpoint_difference = (
            mid - midpoint_expected
        )

        midpoint_consistent = (
            midpoint_available
            & np.isclose(
                mid,
                midpoint_expected,
                rtol=1e-9,
                atol=1e-9,
            )
        )

        midpoint_records.append({
            "quote_set": quote_set,
            "midpoint_observations": int(midpoint_available.sum()),
            "midpoint_consistent": int(midpoint_consistent.sum()),
            "midpoint_inconsistent": int(
                (
                    midpoint_available
                    & ~midpoint_consistent
                ).sum()
            ),
            "midpoint_missing": int(
                (
                    bid.notna()
                    & ask.notna()
                    & mid.isna()
                ).sum()
            ),
            "max_abs_midpoint_difference": (
                float(
                    midpoint_difference[
                        midpoint_available
                    ].abs().max()
                )
                if midpoint_available.any()
                else np.nan
            ),
        })

        # ---------------------------------------------------------------------
        # Violation-specific diagnostics
        # ---------------------------------------------------------------------

        if violation_count > 0:

            violation_df = df.loc[
                violation,
                [
                    "date",
                    "symbol",
                    bid_col,
                    ask_col,
                    mid_col,
                    time_col,
                ]
            ].copy()

            violation_df["quote_set"] = quote_set

            violation_df["bid"] = bid.loc[
                violation
            ].values

            violation_df["ask"] = ask.loc[
                violation
            ].values

            violation_df["mid"] = mid.loc[
                violation
            ].values

            violation_df["bid_minus_ask"] = (
                violation_df["bid"]
                - violation_df["ask"]
            )

            violation_df["relative_bid_ask_inversion"] = (
                violation_df["bid_minus_ask"].abs()
                / (
                    (
                        violation_df["bid"]
                        + violation_df["ask"]
                    )
                    / 2
                )
            )

            violation_df["mid_minus_expected"] = (
                violation_df["mid"]
                - (
                    violation_df["bid"]
                    + violation_df["ask"]
                ) / 2
            )

            # -------------------------------------------------------------
            # Magnitude distribution
            # -------------------------------------------------------------

            difference = (
                violation_df["bid_minus_ask"]
            )

            magnitude_records.append({
                "quote_set": quote_set,
                "violation_count": len(violation_df),
                "min_bid_minus_ask": float(difference.min()),
                "max_bid_minus_ask": float(difference.max()),
                "mean_bid_minus_ask": float(difference.mean()),
                "median_bid_minus_ask": float(
                    difference.median()
                ),
                "p01_abs_inversion": float(
                    difference.abs().quantile(0.01)
                ),
                "p05_abs_inversion": float(
                    difference.abs().quantile(0.05)
                ),
                "p25_abs_inversion": float(
                    difference.abs().quantile(0.25)
                ),
                "p50_abs_inversion": float(
                    difference.abs().quantile(0.50)
                ),
                "p75_abs_inversion": float(
                    difference.abs().quantile(0.75)
                ),
                "p95_abs_inversion": float(
                    difference.abs().quantile(0.95)
                ),
                "p99_abs_inversion": float(
                    difference.abs().quantile(0.99)
                ),
                "max_abs_inversion": float(
                    difference.abs().max()
                ),
            })

            # -------------------------------------------------------------
            # Symbol-level diagnostics
            # -------------------------------------------------------------

            symbol_group = (
                violation_df
                .groupby("symbol", dropna=False)
                .agg(
                    violation_count=("symbol", "size"),
                    mean_bid_minus_ask=(
                        "bid_minus_ask",
                        "mean",
                    ),
                    median_bid_minus_ask=(
                        "bid_minus_ask",
                        "median",
                    ),
                    max_abs_bid_ask_inversion=(
                        "bid_minus_ask",
                        lambda x: x.abs().max(),
                    ),
                )
                .reset_index()
            )

            symbol_group["quote_set"] = quote_set

            symbol_records.append(symbol_group)

            # -------------------------------------------------------------
            # Date-level diagnostics
            # -------------------------------------------------------------

            date_group = (
                violation_df
                .groupby("date", dropna=False)
                .agg(
                    violation_count=("date", "size"),
                    mean_bid_minus_ask=(
                        "bid_minus_ask",
                        "mean",
                    ),
                    max_abs_bid_ask_inversion=(
                        "bid_minus_ask",
                        lambda x: x.abs().max(),
                    ),
                )
                .reset_index()
            )

            date_group["quote_set"] = quote_set

            date_records.append(date_group)

            # -------------------------------------------------------------
            # Keep representative examples
            #
            # Sorted examples help inspect:
            #   1. smallest inversion
            #   2. median-ish inversion
            #   3. largest inversion
            # -------------------------------------------------------------

            example_frames.append(
                violation_df[
                    [
                        "date",
                        "symbol",
                        "quote_set",
                        time_col,
                        "bid",
                        "ask",
                        "mid",
                        "bid_minus_ask",
                        "relative_bid_ask_inversion",
                        "mid_minus_expected",
                    ]
                ]
            )


# =============================================================================
# COMBINE RESULTS
# =============================================================================

quote_set_summary = pd.DataFrame(
    quote_set_records
)

midpoint_summary = pd.DataFrame(
    midpoint_records
)

magnitude_summary = pd.DataFrame(
    magnitude_records
)

if symbol_records:
    symbol_summary = pd.concat(
        symbol_records,
        ignore_index=True,
    )
else:
    symbol_summary = pd.DataFrame()

if date_records:
    date_summary = pd.concat(
        date_records,
        ignore_index=True,
    )
else:
    date_summary = pd.DataFrame()


# =============================================================================
# REPRESENTATIVE EXAMPLES
# =============================================================================

if example_frames:

    all_examples = pd.concat(
        example_frames,
        ignore_index=True,
    )

    # Keep a useful number of examples per quote set:
    #
    # - 20 smallest inversions
    # - 20 largest inversions
    # - 20 largest relative inversions
    #

    example_parts = []

    for quote_set, group in all_examples.groupby(
        "quote_set",
        dropna=False,
    ):

        group = group.copy()

        smallest = group.nsmallest(
            20,
            "bid_minus_ask",
        )

        largest = group.nlargest(
            20,
            "bid_minus_ask",
        )

        largest_relative = group.nlargest(
            20,
            "relative_bid_ask_inversion",
        )

        example_parts.extend([
            smallest,
            largest,
            largest_relative,
        ])

    examples = pd.concat(
        example_parts,
        ignore_index=True,
    ).drop_duplicates()

    examples = examples.sort_values(
        [
            "quote_set",
            "date",
            "symbol",
            "bid_minus_ask",
        ]
    )

else:
    examples = pd.DataFrame()


# =============================================================================
# GLOBAL SUMMARY
# =============================================================================

total_violations = int(
    quote_set_summary["bid_greater_than_ask"].sum()
)

total_non_null_bid_ask = int(
    quote_set_summary["non_null_bid_ask_rows"].sum()
)

summary_rows = []

for quote_set, fields in QUOTE_SETS.items():

    row = quote_set_summary[
        quote_set_summary["quote_set"] == quote_set
    ]

    if row.empty:
        continue

    row = row.iloc[0]

    midpoint_row = midpoint_summary[
        midpoint_summary["quote_set"] == quote_set
    ]

    midpoint_row = (
        midpoint_row.iloc[0]
        if not midpoint_row.empty
        else None
    )

    magnitude_row = magnitude_summary[
        magnitude_summary["quote_set"] == quote_set
    ]

    magnitude_row = (
        magnitude_row.iloc[0]
        if not magnitude_row.empty
        else None
    )

    summary_rows.append({
        "quote_set": quote_set,
        "bid_column": fields["bid"],
        "ask_column": fields["ask"],
        "mid_column": fields["mid"],
        "time_column": fields["time"],
        "rows": int(row["rows"]),
        "non_null_bid_ask_rows": int(
            row["non_null_bid_ask_rows"]
        ),
        "bid_greater_than_ask": int(
            row["bid_greater_than_ask"]
        ),
        "violation_rate_all_rows": row[
            "violation_rate_all_rows"
        ],
        "violation_rate_non_null_bid_ask": row[
            "violation_rate_non_null_bid_ask"
        ],
        "midpoint_observations": (
            midpoint_row["midpoint_observations"]
            if midpoint_row is not None
            else np.nan
        ),
        "midpoint_inconsistent": (
            midpoint_row["midpoint_inconsistent"]
            if midpoint_row is not None
            else np.nan
        ),
        "median_abs_inversion": (
            magnitude_row["p50_abs_inversion"]
            if magnitude_row is not None
            else np.nan
        ),
        "p95_abs_inversion": (
            magnitude_row["p95_abs_inversion"]
            if magnitude_row is not None
            else np.nan
        ),
        "max_abs_inversion": (
            magnitude_row["max_abs_inversion"]
            if magnitude_row is not None
            else np.nan
        ),
    })

semantic_summary = pd.DataFrame(
    summary_rows
)


# =============================================================================
# GLOBAL SEMANTIC CONSISTENCY CHECKS
# =============================================================================

consistency_records = []

for quote_set, fields in QUOTE_SETS.items():

    subset = semantic_summary[
        semantic_summary["quote_set"] == quote_set
    ]

    if subset.empty:
        continue

    row = subset.iloc[0]

    violation_count = int(
        row["bid_greater_than_ask"]
    )

    midpoint_inconsistent = int(
        row["midpoint_inconsistent"]
    )

    # -------------------------------------------------------------------------
    # Important interpretation:
    #
    # A bid > ask observation is not automatically classified as an error.
    #
    # We only classify the diagnostic state:
    #
    #   NO_VIOLATIONS
    #   VIOLATIONS_PRESENT_MIDPOINT_CONSISTENT
    #   VIOLATIONS_PRESENT_MIDPOINT_INCONSISTENT
    #
    # The final decision remains semantic/manual review.
    # -------------------------------------------------------------------------

    if violation_count == 0:

        status = "NO_VIOLATIONS"

    elif midpoint_inconsistent == 0:

        status = (
            "VIOLATIONS_PRESENT_"
            "MIDPOINT_CONSISTENT"
        )

    else:

        status = (
            "VIOLATIONS_PRESENT_"
            "MIDPOINT_INCONSISTENT"
        )

    consistency_records.append({
        "quote_set": quote_set,
        "bid_column": fields["bid"],
        "ask_column": fields["ask"],
        "mid_column": fields["mid"],
        "bid_greater_than_ask_count": violation_count,
        "midpoint_inconsistent_count": midpoint_inconsistent,
        "semantic_diagnostic_status": status,
        "automatic_cleaning_decision": (
            "NO_ACTION"
        ),
        "manual_review_required": (
            violation_count > 0
        ),
        "interpretation": (
            "Bid greater than ask observations "
            "require semantic review. No quote "
            "values should be changed solely from "
            "this diagnostic."
        ),
    })

consistency_summary = pd.DataFrame(
    consistency_records
)


# =============================================================================
# SAVE OUTPUTS
# =============================================================================

quote_set_summary.to_csv(
    SET_SUMMARY_FILE,
    index=False,
)

symbol_summary.to_csv(
    SYMBOL_SUMMARY_FILE,
    index=False,
)

date_summary.to_csv(
    DATE_SUMMARY_FILE,
    index=False,
)

examples.to_csv(
    EXAMPLE_FILE,
    index=False,
)

magnitude_summary.to_csv(
    MAGNITUDE_FILE,
    index=False,
)

midpoint_summary.to_csv(
    MIDPOINT_FILE,
    index=False,
)

consistency_summary.to_csv(
    CONSISTENCY_FILE,
    index=False,
)


# =============================================================================
# HIGH-LEVEL SUMMARY FILE
# =============================================================================

summary = pd.DataFrame([
    {
        "metric": "input_rows",
        "value": global_rows,
    },
    {
        "metric": "total_bid_greater_than_ask",
        "value": total_violations,
    },
    {
        "metric": "total_non_null_bid_ask_observations",
        "value": total_non_null_bid_ask,
    },
    {
        "metric": "overall_violation_rate",
        "value": (
            total_violations
            / total_non_null_bid_ask
            if total_non_null_bid_ask > 0
            else np.nan
        ),
    },
    {
        "metric": "quote_sets_investigated",
        "value": len(QUOTE_SETS),
    },
    {
        "metric": "automatic_cleaning_applied",
        "value": False,
    },
    {
        "metric": "observations_removed",
        "value": 0,
    },
    {
        "metric": "values_modified",
        "value": 0,
    },
    {
        "metric": "imputation_performed",
        "value": False,
    },
    {
        "metric": "canonical_file_overwritten",
        "value": False,
    },
])

summary.to_csv(
    SUMMARY_FILE,
    index=False,
)


# =============================================================================
# CONSOLE REPORT
# =============================================================================

print()
print("=" * 80)
print("QUOTE SEMANTIC INVESTIGATION SUMMARY")
print("=" * 80)

print(
    f"Input rows:                         "
    f"{global_rows:,}"
)

print(
    f"Total bid > ask observations:       "
    f"{total_violations:,}"
)

print(
    f"Non-null bid/ask observations:      "
    f"{total_non_null_bid_ask:,}"
)

if total_non_null_bid_ask > 0:

    print(
        f"Overall bid > ask rate:             "
        f"{total_violations / total_non_null_bid_ask:.6%}"
    )

print()
print("QUOTE-SET RESULTS")
print("-" * 80)

for _, row in semantic_summary.iterrows():

    print(
        f"{row['quote_set']:>6} | "
        f"violations={int(row['bid_greater_than_ask']):>7,} | "
        f"rate={row['violation_rate_non_null_bid_ask']:.6%} | "
        f"midpoint_inconsistent="
        f"{int(row['midpoint_inconsistent']):>7,}"
    )

print()
print("=" * 80)
print("INTERPRETATION")
print("=" * 80)

print(
    "Bid > ask observations have been retained for semantic review."
)

print(
    "No observations were removed."
)

print(
    "No quote values were modified."
)

print(
    "No imputation was performed."
)

print(
    "No automatic quote correction was applied."
)

print()
print(
    "A bid > ask observation should NOT be treated as an "
    "automatic data-cleaning error without confirming the "
    "economic meaning and source construction of the quote fields."
)

print()
print("=" * 80)
print("OUTPUTS")
print("=" * 80)

print(f"Summary:")
print(f"  {SUMMARY_FILE}")

print(f"Quote-set summary:")
print(f"  {SET_SUMMARY_FILE}")

print(f"Symbol summary:")
print(f"  {SYMBOL_SUMMARY_FILE}")

print(f"Date summary:")
print(f"  {DATE_SUMMARY_FILE}")

print(f"Violation examples:")
print(f"  {EXAMPLE_FILE}")

print(f"Magnitude diagnostics:")
print(f"  {MAGNITUDE_FILE}")

print(f"Midpoint diagnostics:")
print(f"  {MIDPOINT_FILE}")

print(f"Semantic consistency:")
print(f"  {CONSISTENCY_FILE}")

print()
print("=" * 80)
print("STATUS")
print("=" * 80)

print(
    "PASS — quote semantic investigation completed."
)

print(
    "REVIEW — BID_GREATER_THAN_ASK observations require "
    "semantic interpretation before any exclusion or correction."
)