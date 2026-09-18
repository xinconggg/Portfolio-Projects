from pathlib import Path
import pandas as pd
import numpy as np


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"
TIER2_DIR = DATA_DIR / "tier2_historical_universe"

INPUT_PANEL = (
    TIER2_DIR /
    "crsp_tier2_daily_panel.csv"
)

OUTPUT_EXECUTION = (
    TIER2_DIR /
    "crsp_tier2_execution_dataset.csv"
)

OUTPUT_SUMMARY = (
    TIER2_DIR /
    "crsp_tier2_execution_dataset_summary.csv"
)

OUTPUT_REJECTIONS = (
    TIER2_DIR /
    "crsp_tier2_execution_dataset_rejection_audit.csv"
)

OUTPUT_REJECTION_SUMMARY = (
    TIER2_DIR /
    "crsp_tier2_execution_dataset_rejection_summary.csv"
)

OUTPUT_VALIDATION = (
    TIER2_DIR /
    "crsp_tier2_execution_dataset_validation.csv"
)


# =============================================================================
# PARAMETERS
# =============================================================================

RESEARCH_START = pd.Timestamp("1993-01-01")
RESEARCH_END = pd.Timestamp("2018-12-31")


# Fields required to construct the execution dataset.
#
# These are fields used directly or indirectly by the execution analysis.
#
# Do NOT fabricate missing values.
#
REQUIRED_EXECUTION_FIELDS = [
    "dlyprc",
    "dlyvol",
    "dlybid",
    "dlyask",
    "dlyopen",
    "dlyhigh",
    "dlylow",
    "dlynumtrd",
]


# =============================================================================
# HELPERS
# =============================================================================

def normalize_columns(df):
    df.columns = [
        str(col).strip().lower()
        for col in df.columns
    ]
    return df


def normalize_permno(df):

    df["permno"] = pd.to_numeric(
        df["permno"],
        errors="coerce"
    ).astype("Int64")

    return df


def parse_dates(df):

    for col in [
        "dlycaldt",
        "panel_start",
        "panel_end",
    ]:

        if col in df.columns:

            df[col] = pd.to_datetime(
                df[col],
                errors="coerce"
            )

    return df


# =============================================================================
# LOAD TIER 2 PANEL
# =============================================================================

print("=" * 80)
print("LOADING TIER 2 DAILY PANEL")
print("=" * 80)

panel = pd.read_csv(
    INPUT_PANEL,
    low_memory=False
)

panel = normalize_columns(panel)
panel = normalize_permno(panel)
panel = parse_dates(panel)

print(
    f"Panel rows:       {len(panel):,}"
)

print(
    f"Panel PERMNOs:    "
    f"{panel['permno'].nunique():,}"
)

print(
    f"Panel first date: "
    f"{panel['dlycaldt'].min()}"
)

print(
    f"Panel last date:  "
    f"{panel['dlycaldt'].max()}"
)


# =============================================================================
# REQUIRED FIELD CHECK
# =============================================================================

print("\n" + "=" * 80)
print("CHECKING REQUIRED EXECUTION FIELDS")
print("=" * 80)

missing_columns = [
    col
    for col in REQUIRED_EXECUTION_FIELDS
    if col not in panel.columns
]

if missing_columns:

    print("\nMissing columns:")
    print(missing_columns)

    print("\nAvailable columns:")
    print(panel.columns.tolist())

    raise ValueError(
        "Required execution columns missing from Tier 2 panel: "
        + ", ".join(missing_columns)
    )


# =============================================================================
# NUMERIC CONVERSION
# =============================================================================

print("\n" + "=" * 80)
print("NORMALIZING EXECUTION FIELDS")
print("=" * 80)

for col in REQUIRED_EXECUTION_FIELDS:

    panel[col] = pd.to_numeric(
        panel[col],
        errors="coerce"
    )


# =============================================================================
# MISSINGNESS DIAGNOSTIC
# =============================================================================

print("\n" + "=" * 80)
print("EXECUTION FIELD MISSINGNESS")
print("=" * 80)

missingness = []

for col in REQUIRED_EXECUTION_FIELDS:

    missing_count = int(
        panel[col].isna().sum()
    )

    missingness.append({
        "field": col,
        "missing_rows": missing_count,
        "missing_rate": (
            missing_count / len(panel)
            if len(panel) > 0
            else np.nan
        ),
    })

missingness_df = pd.DataFrame(
    missingness
)

print(
    missingness_df.to_string(index=False)
)


# =============================================================================
# BUILD REJECTION REASONS
# =============================================================================

print("\n" + "=" * 80)
print("BUILDING EXECUTION-DATA REJECTION AUDIT")
print("=" * 80)

audit = panel.copy()

audit["rejection_reason"] = pd.NA


# -----------------------------------------------------------------------------
# Missing required execution fields
# -----------------------------------------------------------------------------

missing_reason_parts = []

for col in REQUIRED_EXECUTION_FIELDS:

    missing_mask = audit[col].isna()

    reason = np.where(
        missing_mask,
        "MISSING_" + col.upper(),
        ""
    )

    missing_reason_parts.append(
        pd.Series(
            reason,
            index=audit.index
        )
    )


# Combine missing-field reasons.
#
# An observation may have more than one missing field.
#
# Example:
# MISSING_DLYBID;MISSING_DLYASK

missing_matrix = pd.concat(
    missing_reason_parts,
    axis=1
)

missing_matrix.columns = REQUIRED_EXECUTION_FIELDS


def combine_missing_reasons(row):

    reasons = [
        value
        for value in row
        if value
    ]

    if not reasons:
        return pd.NA

    return ";".join(reasons)


audit["rejection_reason"] = (
    missing_matrix
    .apply(
        combine_missing_reasons,
        axis=1
    )
)


# =============================================================================
# INVALID NUMERIC EXECUTION VALUES
# =============================================================================

print("\n" + "=" * 80)
print("CHECKING INVALID EXECUTION VALUES")
print("=" * 80)


# -----------------------------------------------------------------------------
# Price
# -----------------------------------------------------------------------------

invalid_price = (
    audit["dlyprc"].notna()
    &
    (audit["dlyprc"] <= 0)
)

audit.loc[
    invalid_price
    &
    audit["rejection_reason"].isna(),
    "rejection_reason"
] = "INVALID_DLYPRC"


# -----------------------------------------------------------------------------
# Volume
# -----------------------------------------------------------------------------

invalid_volume = (
    audit["dlyvol"].notna()
    &
    (audit["dlyvol"] < 0)
)

audit.loc[
    invalid_volume
    &
    audit["rejection_reason"].isna(),
    "rejection_reason"
] = "INVALID_DLYVOL"


# -----------------------------------------------------------------------------
# Number of trades
# -----------------------------------------------------------------------------

invalid_numtrd = (
    audit["dlynumtrd"].notna()
    &
    (audit["dlynumtrd"] < 0)
)

audit.loc[
    invalid_numtrd
    &
    audit["rejection_reason"].isna(),
    "rejection_reason"
] = "INVALID_DLYNUMTRD"


# -----------------------------------------------------------------------------
# OHLC
# -----------------------------------------------------------------------------

invalid_open = (
    audit["dlyopen"].notna()
    &
    (audit["dlyopen"] <= 0)
)

audit.loc[
    invalid_open
    &
    audit["rejection_reason"].isna(),
    "rejection_reason"
] = "INVALID_DLYOPEN"


invalid_high = (
    audit["dlyhigh"].notna()
    &
    (audit["dlyhigh"] <= 0)
)

audit.loc[
    invalid_high
    &
    audit["rejection_reason"].isna(),
    "rejection_reason"
] = "INVALID_DLYHIGH"


invalid_low = (
    audit["dlylow"].notna()
    &
    (audit["dlylow"] <= 0)
)

audit.loc[
    invalid_low
    &
    audit["rejection_reason"].isna(),
    "rejection_reason"
] = "INVALID_DLYLOW"


# =============================================================================
# BID / ASK VALIDITY
# =============================================================================

invalid_bid = (
    audit["dlybid"].notna()
    &
    (audit["dlybid"] <= 0)
)

audit.loc[
    invalid_bid
    &
    audit["rejection_reason"].isna(),
    "rejection_reason"
] = "INVALID_DLYBID"


invalid_ask = (
    audit["dlyask"].notna()
    &
    (audit["dlyask"] <= 0)
)

audit.loc[
    invalid_ask
    &
    audit["rejection_reason"].isna(),
    "rejection_reason"
] = "INVALID_DLYASK"


# -----------------------------------------------------------------------------
# Crossed market
# -----------------------------------------------------------------------------

crossed_market = (
    audit["dlybid"].notna()
    &
    audit["dlyask"].notna()
    &
    (audit["dlybid"] > audit["dlyask"])
)

audit.loc[
    crossed_market
    &
    audit["rejection_reason"].isna(),
    "rejection_reason"
] = "CROSSED_BID_ASK"


# =============================================================================
# OHLC CONSISTENCY
# =============================================================================

invalid_ohlc = (
    audit["dlyhigh"].notna()
    &
    audit["dlylow"].notna()
    &
    (
        audit["dlyhigh"]
        <
        audit["dlylow"]
    )
)

audit.loc[
    invalid_ohlc
    &
    audit["rejection_reason"].isna(),
    "rejection_reason"
] = "INVALID_HIGH_LOW"


# =============================================================================
# MIDQUOTE
# =============================================================================

audit["midquote"] = (
    audit["dlybid"]
    +
    audit["dlyask"]
) / 2


invalid_midquote = (
    audit["midquote"].notna()
    &
    (audit["midquote"] <= 0)
)

audit.loc[
    invalid_midquote
    &
    audit["rejection_reason"].isna(),
    "rejection_reason"
] = "INVALID_MIDQUOTE"


# =============================================================================
# QUOTED SPREAD
# =============================================================================

audit["quoted_spread"] = (
    audit["dlyask"]
    -
    audit["dlybid"]
)

negative_spread = (
    audit["quoted_spread"].notna()
    &
    (audit["quoted_spread"] < 0)
)

audit.loc[
    negative_spread
    &
    audit["rejection_reason"].isna(),
    "rejection_reason"
] = "NEGATIVE_QUOTED_SPREAD"


# =============================================================================
# DOLLAR VOLUME
# =============================================================================

audit["dollar_volume"] = (
    audit["dlyprc"]
    .abs()
    *
    audit["dlyvol"]
)


invalid_dollar_volume = (
    audit["dollar_volume"].notna()
    &
    (audit["dollar_volume"] < 0)
)

audit.loc[
    invalid_dollar_volume
    &
    audit["rejection_reason"].isna(),
    "rejection_reason"
] = "INVALID_DOLLAR_VOLUME"


# =============================================================================
# EXECUTION ELIGIBILITY
# =============================================================================

audit["execution_eligible"] = (
    audit["rejection_reason"].isna()
)


# =============================================================================
# SPLIT VALID / REJECTED
# =============================================================================

execution_dataset = audit[
    audit["execution_eligible"]
].copy()

rejections = audit[
    ~audit["execution_eligible"]
].copy()


print(
    f"Input panel observations: "
    f"{len(panel):,}"
)

print(
    f"Execution-eligible observations: "
    f"{len(execution_dataset):,}"
)

print(
    f"Rejected observations: "
    f"{len(rejections):,}"
)


# =============================================================================
# REJECTION SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("REJECTION SUMMARY")
print("=" * 80)

if not rejections.empty:

    rejection_summary = (
        rejections["rejection_reason"]
        .value_counts(dropna=False)
        .rename_axis("rejection_reason")
        .reset_index(name="rows")
    )

else:

    rejection_summary = pd.DataFrame(
        columns=[
            "rejection_reason",
            "rows",
        ]
    )


print(
    rejection_summary.to_string(index=False)
)


# =============================================================================
# EXECUTION DATASET FINAL FIELDS
# =============================================================================

execution_dataset = execution_dataset.sort_values(
    [
        "permno",
        "dlycaldt",
    ]
).reset_index(
    drop=True
)


# =============================================================================
# VALIDATION
# =============================================================================

print("\n" + "=" * 80)
print("VALIDATION")
print("=" * 80)

validation = []


# -----------------------------------------------------------------------------
# 1. No missing PERMNO
# -----------------------------------------------------------------------------

missing_permno = int(
    execution_dataset["permno"].isna().sum()
)

validation.append({
    "check": "no_missing_permno",
    "passed": missing_permno == 0,
    "value": missing_permno,
})


# -----------------------------------------------------------------------------
# 2. No missing date
# -----------------------------------------------------------------------------

missing_date = int(
    execution_dataset["dlycaldt"].isna().sum()
)

validation.append({
    "check": "no_missing_date",
    "passed": missing_date == 0,
    "value": missing_date,
})


# -----------------------------------------------------------------------------
# 3. No duplicate PERMNO-date
# -----------------------------------------------------------------------------

duplicates = int(
    execution_dataset
    .duplicated(
        ["permno", "dlycaldt"]
    )
    .sum()
)

validation.append({
    "check": "no_duplicate_permno_date",
    "passed": duplicates == 0,
    "value": duplicates,
})


# -----------------------------------------------------------------------------
# 4. Research window
# -----------------------------------------------------------------------------

outside_window = int(
    (
        ~execution_dataset["dlycaldt"].between(
            RESEARCH_START,
            RESEARCH_END,
            inclusive="both"
        )
    ).sum()
)

validation.append({
    "check": "all_dates_within_research_window",
    "passed": outside_window == 0,
    "value": outside_window,
})


# -----------------------------------------------------------------------------
# 5. Historical interval
# -----------------------------------------------------------------------------

missing_interval = int(
    (
        execution_dataset["panel_start"].isna()
        |
        execution_dataset["panel_end"].isna()
    ).sum()
)

validation.append({
    "check": "all_rows_have_historical_interval",
    "passed": missing_interval == 0,
    "value": missing_interval,
})


outside_interval = int(
    (
        (
            execution_dataset["dlycaldt"]
            <
            execution_dataset["panel_start"]
        )
        |
        (
            execution_dataset["dlycaldt"]
            >
            execution_dataset["panel_end"]
        )
    ).sum()
)

validation.append({
    "check": "all_dates_within_historical_interval",
    "passed": outside_interval == 0,
    "value": outside_interval,
})


# -----------------------------------------------------------------------------
# 6. Common equity only
# -----------------------------------------------------------------------------

if "research_classification" in execution_dataset.columns:

    invalid_classification = int(
        (
            execution_dataset["research_classification"]
            !=
            "COMMON_EQUITY"
        ).sum()
    )

else:

    invalid_classification = len(
        execution_dataset
    )


validation.append({
    "check": "only_common_equity",
    "passed": invalid_classification == 0,
    "value": invalid_classification,
})


# -----------------------------------------------------------------------------
# 7. Required execution fields
# -----------------------------------------------------------------------------

required_missing = int(
    execution_dataset[
        REQUIRED_EXECUTION_FIELDS
    ]
    .isna()
    .any(axis=1)
    .sum()
)

validation.append({
    "check": "required_execution_fields_present",
    "passed": required_missing == 0,
    "value": required_missing,
})


# -----------------------------------------------------------------------------
# 8. Bid / ask
# -----------------------------------------------------------------------------

crossed = int(
    (
        execution_dataset["dlybid"]
        >
        execution_dataset["dlyask"]
    ).sum()
)

validation.append({
    "check": "no_crossed_bid_ask_markets",
    "passed": crossed == 0,
    "value": crossed,
})


# -----------------------------------------------------------------------------
# 9. Spread
# -----------------------------------------------------------------------------

negative_spread_count = int(
    (
        execution_dataset["quoted_spread"]
        <
        0
    ).sum()
)

validation.append({
    "check": "quoted_spread_nonnegative",
    "passed": negative_spread_count == 0,
    "value": negative_spread_count,
})


# -----------------------------------------------------------------------------
# 10. Midquote
# -----------------------------------------------------------------------------

invalid_midquote_count = int(
    (
        execution_dataset["midquote"]
        <=
        0
    ).sum()
)

validation.append({
    "check": "positive_midquote",
    "passed": invalid_midquote_count == 0,
    "value": invalid_midquote_count,
})


# -----------------------------------------------------------------------------
# 11. Dollar volume
# -----------------------------------------------------------------------------

expected_dollar_volume = (
    execution_dataset["dlyprc"].abs()
    *
    execution_dataset["dlyvol"]
)

dollar_volume_matches = np.isclose(
    execution_dataset["dollar_volume"],
    expected_dollar_volume,
    rtol=1e-10,
    atol=1e-10,
    equal_nan=False,
)

dollar_volume_mismatch = int(
    (~dollar_volume_matches).sum()
)

validation.append({
    "check": "dollar_volume_calculation_consistent",
    "passed": dollar_volume_mismatch == 0,
    "value": dollar_volume_mismatch,
})


# -----------------------------------------------------------------------------
# 12. Accounting identity
# -----------------------------------------------------------------------------

accounting_difference = (
    len(execution_dataset)
    +
    len(rejections)
    -
    len(panel)
)

validation.append({
    "check": "valid_plus_rejected_equals_input",
    "passed": accounting_difference == 0,
    "value": len(panel),
})


validation_df = pd.DataFrame(
    validation
)


# =============================================================================
# SUMMARY
# =============================================================================

summary = pd.DataFrame({
    "metric": [
        "input_panel_rows",
        "execution_eligible_rows",
        "rejected_rows",
        "execution_rejection_rate",
        "execution_eligible_permnos",
        "rejected_permnos",
        "research_start",
        "research_end",
    ],

    "value": [
        len(panel),
        len(execution_dataset),
        len(rejections),
        (
            len(rejections) / len(panel)
            if len(panel) > 0
            else np.nan
        ),
        execution_dataset["permno"].nunique(),
        rejections["permno"].nunique(),
        RESEARCH_START.date(),
        RESEARCH_END.date(),
    ],
})


# =============================================================================
# REPORT
# =============================================================================

print("\n" + "=" * 80)
print("EXECUTION DATASET SUMMARY")
print("=" * 80)

print(
    summary.to_string(index=False)
)


print("\n" + "=" * 80)
print("VALIDATION RESULTS")
print("=" * 80)

print(
    validation_df.to_string(index=False)
)


# =============================================================================
# HARD FAIL
# =============================================================================

if not validation_df["passed"].all():

    print("\n" + "=" * 80)
    print("CRITICAL: EXECUTION DATASET VALIDATION FAILED")
    print("=" * 80)

    failed = validation_df[
        ~validation_df["passed"]
    ]

    print(
        failed.to_string(index=False)
    )

    raise ValueError(
        "Tier 2 execution dataset validation failed."
    )


# =============================================================================
# SAVE
# =============================================================================

execution_dataset.to_csv(
    OUTPUT_EXECUTION,
    index=False
)

summary.to_csv(
    OUTPUT_SUMMARY,
    index=False
)

rejections.to_csv(
    OUTPUT_REJECTIONS,
    index=False
)

rejection_summary.to_csv(
    OUTPUT_REJECTION_SUMMARY,
    index=False
)

validation_df.to_csv(
    OUTPUT_VALIDATION,
    index=False
)


# =============================================================================
# FINAL
# =============================================================================

print("\n" + "=" * 80)
print("SAVED")
print("=" * 80)

print(
    f"Execution dataset: "
    f"{OUTPUT_EXECUTION}"
)

print(
    f"Summary:           "
    f"{OUTPUT_SUMMARY}"
)

print(
    f"Rejection audit:   "
    f"{OUTPUT_REJECTIONS}"
)

print(
    f"Rejection summary: "
    f"{OUTPUT_REJECTION_SUMMARY}"
)

print(
    f"Validation:        "
    f"{OUTPUT_VALIDATION}"
)

print(
    "\nPASS: Tier 2 execution dataset "
    "successfully constructed and validated."
)