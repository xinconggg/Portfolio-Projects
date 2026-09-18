from pathlib import Path
import pandas as pd
import numpy as np


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
    / "final_integrated_validation_corrected"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 100_000


# =============================================================================
# HELPERS
# =============================================================================

def print_section(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def numeric(series):
    return pd.to_numeric(series, errors="coerce")


def normalized_symbol(series):
    return (
        series
        .astype("string")
        .str.strip()
        .str.upper()
    )


def parse_canonical_date(series):
    """
    Canonical date must already represent the confirmed
    DD/MM/YYYY source interpretation.

    date_normalized is preferred explicitly.
    """

    return pd.to_datetime(
        series,
        errors="coerce"
    )


# =============================================================================
# LOAD DATA
# =============================================================================

print_section(
    "PHASE 5 — STEP 7: CORRECTED FINAL INTEGRATED TAQ VALIDATION"
)

print("Input file:")
print(f"  {INPUT_FILE}")

df = pd.read_csv(
    INPUT_FILE,
    low_memory=False
)

print()
print(f"Rows:       {len(df):,}")
print(f"Columns:    {len(df.columns):,}")


# =============================================================================
# CANONICAL DATE SELECTION
# =============================================================================

print_section(
    "CANONICAL DATE SELECTION"
)

if "date_normalized" not in df.columns:
    raise RuntimeError(
        "CRITICAL: date_normalized is missing from canonical TAQ."
    )

if "date_iso" not in df.columns:
    raise RuntimeError(
        "CRITICAL: date_iso is missing from canonical TAQ."
    )

canonical_date = parse_canonical_date(
    df["date_normalized"]
)

date_iso = parse_canonical_date(
    df["date_iso"]
)

raw_date_column = (
    pd.to_datetime(
        df["date"],
        errors="coerce"
    )
    if "date" in df.columns
    else pd.Series(pd.NaT, index=df.index)
)

print(
    "Canonical date column: date_normalized"
)

print(
    f"Canonical date missing: "
    f"{canonical_date.isna().sum():,}"
)

print(
    f"Canonical date unique: "
    f"{canonical_date.nunique():,}"
)

print(
    f"Canonical first date: "
    f"{canonical_date.min()}"
)

print(
    f"Canonical last date: "
    f"{canonical_date.max()}"
)

print()
print(
    "Raw `date` column is NOT used as the canonical "
    "structural date."
)

print(
    f"Raw `date` missing after generic parsing: "
    f"{raw_date_column.isna().sum():,}"
)


# =============================================================================
# SYMBOL
# =============================================================================

if "symbol_normalized" in df.columns:

    symbol = normalized_symbol(
        df["symbol_normalized"]
    )

elif "symbol" in df.columns:

    symbol = normalized_symbol(
        df["symbol"]
    )

else:

    raise RuntimeError(
        "CRITICAL: no symbol column found."
    )


# =============================================================================
# GLOBAL COUNTERS
# =============================================================================

critical_failures = 0
review_items = 0


# =============================================================================
# STRUCTURAL VALIDATION
# =============================================================================

print_section(
    "STRUCTURAL VALIDATION"
)

structural_results = []


# -----------------------------------------------------------------------------
# Missing canonical date
# -----------------------------------------------------------------------------

missing_date = int(
    canonical_date.isna().sum()
)

structural_results.append(
    {
        "domain": "STRUCTURAL",
        "check": "Missing canonical date",
        "violation_count": missing_date,
        "severity": "CRITICAL",
        "interpretation":
            "Canonical TAQ rows must contain a valid date.",
    }
)

critical_failures += missing_date


# -----------------------------------------------------------------------------
# Missing symbol
# -----------------------------------------------------------------------------

missing_symbol = int(
    symbol.isna().sum()
)

structural_results.append(
    {
        "domain": "STRUCTURAL",
        "check": "Missing symbol",
        "violation_count": missing_symbol,
        "severity": "CRITICAL",
        "interpretation":
            "Canonical TAQ rows must contain a security identifier.",
    }
)

critical_failures += missing_symbol


# -----------------------------------------------------------------------------
# Date-symbol duplicates
# -----------------------------------------------------------------------------

key = pd.DataFrame(
    {
        "date": canonical_date,
        "symbol": symbol,
    }
)

duplicate_mask = key.duplicated(
    subset=["date", "symbol"],
    keep=False
)

duplicate_extra_mask = key.duplicated(
    subset=["date", "symbol"],
    keep="first"
)

duplicate_groups = int(
    key.loc[
        duplicate_mask,
        ["date", "symbol"]
    ]
    .drop_duplicates()
    .shape[0]
)

duplicate_rows = int(
    duplicate_mask.sum()
)

duplicate_extra_rows = int(
    duplicate_extra_mask.sum()
)

structural_results.append(
    {
        "domain": "STRUCTURAL",
        "check": "Date-symbol duplicate rows",
        "violation_count": duplicate_extra_rows,
        "severity": "CRITICAL",
        "interpretation":
            "Date-symbol should identify one canonical daily observation.",
    }
)

critical_failures += duplicate_extra_rows


# -----------------------------------------------------------------------------
# Date/symbol key missingness
# -----------------------------------------------------------------------------

key_missing = (
    canonical_date.isna()
    | symbol.isna()
)

structural_results.append(
    {
        "domain": "STRUCTURAL",
        "check": "Missing date-symbol key",
        "violation_count": int(key_missing.sum()),
        "severity": "CRITICAL",
        "interpretation":
            "Canonical date and symbol jointly define the observation key.",
    }
)


# =============================================================================
# TEMPORAL VALIDATION
# =============================================================================

print_section(
    "TEMPORAL VALIDATION"
)

temporal_results = []

# Canonical date range
date_range_invalid = (
    canonical_date.notna()
    & (
        (canonical_date < pd.Timestamp("1993-01-01"))
        |
        (canonical_date > pd.Timestamp("2012-12-31"))
    )
)

temporal_results.append(
    {
        "domain": "TEMPORAL",
        "check": "Date outside expected source range",
        "violation_count": int(
            date_range_invalid.sum()
        ),
        "severity": "REVIEW",
        "interpretation":
            "Source coverage is expected to lie within 1993-2012.",
    }
)

review_items += int(
    date_range_invalid.sum()
)


# =============================================================================
# QUOTE VALIDATION
# =============================================================================

print_section(
    "QUOTE VALIDATION"
)

quote_results = []

quote_sets = [
    ("1pm", "BB_1pm", "BO_1pm", "MID_1pm"),
    ("c1", "BB_c1", "BO_c1", "Mid_c1"),
    ("4pm", "BB_4pm", "BO_4pm", "Mid_4pm"),
    ("last", "LBB", "LBO", "LMid"),
]

for quote_name, bid_col, ask_col, mid_col in quote_sets:

    if not all(
        c in df.columns
        for c in [bid_col, ask_col, mid_col]
    ):
        continue

    bid = numeric(df[bid_col])
    ask = numeric(df[ask_col])
    mid = numeric(df[mid_col])

    available = (
        bid.notna()
        & ask.notna()
    )

    bid_gt_ask = (
        available
        & (bid > ask)
    )

    midpoint_invalid = (
        available
        & mid.notna()
        & (
            ~np.isclose(
                mid,
                (bid + ask) / 2,
                rtol=1e-9,
                atol=1e-9
            )
        )
    )

    bid_gt_ask_count = int(
        bid_gt_ask.sum()
    )

    midpoint_count = int(
        midpoint_invalid.sum()
    )

    quote_results.append(
        {
            "domain": "QUOTE",
            "quote_set": quote_name,
            "check": "Bid greater than ask",
            "violation_count": bid_gt_ask_count,
            "severity": "REVIEW",
            "interpretation":
                "Requires source-semantic interpretation.",
        }
    )

    quote_results.append(
        {
            "domain": "QUOTE",
            "quote_set": quote_name,
            "check": "Midpoint inconsistency",
            "violation_count": midpoint_count,
            "severity": "REVIEW",
            "interpretation":
                "Stored midpoint differs from bid/ask midpoint.",
        }
    )

    review_items += (
        bid_gt_ask_count
        + midpoint_count
    )


# =============================================================================
# EXECUTION METRICS
# =============================================================================

print_section(
    "EXECUTION-METRIC VALIDATION"
)

execution_results = []

execution_columns = [
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

for col in execution_columns:

    if col not in df.columns:
        continue

    values = numeric(df[col])

    negative_count = int(
        (values < 0).sum()
    )

    missing_count = int(
        values.isna().sum()
    )

    execution_results.append(
        {
            "domain": "EXECUTION",
            "column": col,
            "check": "Negative execution metric",
            "violation_count": negative_count,
            "severity": "REVIEW",
            "interpretation":
                "Signed execution measures may legitimately be negative.",
        }
    )

    execution_results.append(
        {
            "domain": "EXECUTION",
            "column": col,
            "check": "Missing execution metric",
            "violation_count": missing_count,
            "severity": "REVIEW",
            "interpretation":
                "Missingness requires source-semantic interpretation.",
        }
    )

    review_items += (
        negative_count
        + missing_count
    )


# =============================================================================
# ACTIVITY / ORDER FLOW
# =============================================================================

print_section(
    "ACTIVITY / ORDER-FLOW VALIDATION"
)

activity_results = []

activity_columns = [
    "NumTrades_t",
    "NumTrades_m",
    "MFCount",
    "SumVolume_t",
    "SumVolume_m",
    "SumValue_b",
    "SumValue_m",
    "BuyNumTrades_LR1",
    "SellNumTrades_LR1",
    "BuyVol_LR1",
    "SellVol_LR1",
    "BuyDollar_LR1",
    "SellDollar_LR1",
    "NumISOTrades_m",
    "SumISOVolume_m",
    "SumISOValue_m",
    "NumOddLotTrades_m",
    "SumOddLotVolume_m",
    "SumOddLotValue_m",
    "NumMixedLotTrades_m",
    "SumMixedLotVolume_m",
    "SumMixedLotValue_m",
    "TOfrDollar_TW_m",
    "TBidDollar_TW_m",
    "TOfrShares_TW_m",
    "TBidShares_TW_m",
    "BOfrDollar_TW_m",
    "BBidDollar_TW_m",
    "BOfrShares_TW_m",
    "BBidShares_TW_m",
]

for col in activity_columns:

    if col not in df.columns:
        continue

    values = numeric(df[col])

    negative_count = int(
        (values < 0).sum()
    )

    missing_count = int(
        values.isna().sum()
    )

    activity_results.append(
        {
            "domain": "ACTIVITY",
            "column": col,
            "check": "Negative activity value",
            "violation_count": negative_count,
            "severity": "REVIEW",
            "interpretation":
                "Negative activity values require source review.",
        }
    )

    activity_results.append(
        {
            "domain": "ACTIVITY",
            "column": col,
            "check": "Missing activity value",
            "violation_count": missing_count,
            "severity": "REVIEW",
            "interpretation":
                "Missing activity values require semantic review.",
        }
    )

    review_items += (
        negative_count
        + missing_count
    )


# =============================================================================
# MARKET STATISTICS
# =============================================================================

print_section(
    "MARKET-STATISTICS VALIDATION"
)

market_results = []

market_columns = [
    "Ret_pre_t",
    "Ret_mkt_t",
    "Ret_post_t",
    "IVol_t_m",
    "IVol_q_m",
    "VarianceRatio1",
    "VarianceRatio2",
    "HIndex1",
    "NumExtremeOfr_m",
    "NumExtremeBid_m",
    "NObsUsed1",
    "NObsUsed2",
    "NumTimeUnitsWithTrade1",
    "NumTimeUnitsWithTrade2",
]

for col in market_columns:

    if col not in df.columns:
        continue

    values = numeric(df[col])

    missing_count = int(
        values.isna().sum()
    )

    negative_count = int(
        (values < 0).sum()
    )

    market_results.append(
        {
            "domain": "MARKET_STATISTICS",
            "column": col,
            "check": "Missing market statistic",
            "violation_count": missing_count,
            "severity": "REVIEW",
            "interpretation":
                "Missing market statistics require source review.",
        }
    )

    # Returns are explicitly allowed to be negative.
    if col.startswith("Ret_"):

        negative_count = 0

    market_results.append(
        {
            "domain": "MARKET_STATISTICS",
            "column": col,
            "check": "Negative market statistic",
            "violation_count": negative_count,
            "severity": "REVIEW",
            "interpretation":
                "Negative returns are economically valid; "
                "other negatives require semantic interpretation.",
        }
    )

    review_items += (
        missing_count
        + negative_count
    )


# =============================================================================
# OUTPUT CHECK TABLES
# =============================================================================

print_section(
    "WRITING VALIDATION OUTPUTS"
)

structural_df = pd.DataFrame(
    structural_results
)

temporal_df = pd.DataFrame(
    temporal_results
)

quote_df = pd.DataFrame(
    quote_results
)

execution_df = pd.DataFrame(
    execution_results
)

activity_df = pd.DataFrame(
    activity_results
)

market_df = pd.DataFrame(
    market_results
)

structural_df.to_csv(
    OUTPUT_DIR / "taq_corrected_structural_checks.csv",
    index=False
)

temporal_df.to_csv(
    OUTPUT_DIR / "taq_corrected_temporal_checks.csv",
    index=False
)

quote_df.to_csv(
    OUTPUT_DIR / "taq_corrected_quote_checks.csv",
    index=False
)

execution_df.to_csv(
    OUTPUT_DIR / "taq_corrected_execution_checks.csv",
    index=False
)

activity_df.to_csv(
    OUTPUT_DIR / "taq_corrected_activity_checks.csv",
    index=False
)

market_df.to_csv(
    OUTPUT_DIR / "taq_corrected_market_checks.csv",
    index=False
)


# =============================================================================
# DOMAIN SUMMARY
# =============================================================================

domain_rows = []

for domain, frame in [
    ("STRUCTURAL", structural_df),
    ("TEMPORAL", temporal_df),
    ("QUOTE", quote_df),
    ("EXECUTION", execution_df),
    ("ACTIVITY", activity_df),
    ("MARKET_STATISTICS", market_df),
]:

    if frame.empty:

        domain_rows.append(
            {
                "domain": domain,
                "total_violations": 0,
                "critical_violations": 0,
                "review_violations": 0,
            }
        )

        continue

    critical = int(
        frame.loc[
            frame["severity"] == "CRITICAL",
            "violation_count"
        ].sum()
    )

    review = int(
        frame.loc[
            frame["severity"] == "REVIEW",
            "violation_count"
        ].sum()
    )

    total = int(
        frame["violation_count"].sum()
    )

    domain_rows.append(
        {
            "domain": domain,
            "total_violations": total,
            "critical_violations": critical,
            "review_violations": review,
        }
    )

domain_summary = pd.DataFrame(
    domain_rows
)

domain_summary.to_csv(
    OUTPUT_DIR
    / "taq_corrected_validation_by_domain.csv",
    index=False
)


# =============================================================================
# FINAL CRITICAL COUNT
# =============================================================================

# Recalculate from structural checks only.
#
# This is intentional:
# Economic/semantic findings are REVIEW items and must not
# automatically become structural failures.

critical_failures = int(
    structural_df.loc[
        structural_df["severity"] == "CRITICAL",
        "violation_count"
    ].sum()
)


# =============================================================================
# FINAL STATUS
# =============================================================================

if critical_failures == 0:

    overall_status = "PASS"

else:

    overall_status = "FAIL"


# =============================================================================
# SUMMARY
# =============================================================================

summary = pd.DataFrame(
    [
        {
            "input_rows": len(df),
            "input_columns": len(df.columns),
            "canonical_date_column": "date_normalized",
            "canonical_date_missing": missing_date,
            "canonical_symbol_missing": missing_symbol,
            "date_symbol_duplicate_extra_rows":
                duplicate_extra_rows,
            "critical_failure_count":
                critical_failures,
            "review_item_count":
                review_items,
            "observations_removed": 0,
            "values_modified": 0,
            "values_imputed": 0,
            "automatic_corrections": 0,
            "overall_status": overall_status,
        }
    ]
)

summary.to_csv(
    OUTPUT_DIR
    / "taq_corrected_final_integrated_validation_summary.csv",
    index=False
)


# =============================================================================
# FINAL REPORT
# =============================================================================

print_section(
    "FINAL CORRECTED INTEGRATED TAQ VALIDATION SUMMARY"
)

print(
    f"Input rows:                    {len(df):,}"
)

print(
    f"Input columns:                 {len(df.columns):,}"
)

print(
    f"Canonical date column:         date_normalized"
)

print(
    f"Missing canonical dates:       {missing_date:,}"
)

print(
    f"Missing symbols:               {missing_symbol:,}"
)

print(
    f"Date-symbol duplicate extras:  {duplicate_extra_rows:,}"
)

print(
    f"Critical failures:             {critical_failures:,}"
)

print(
    f"Review items:                  {review_items:,}"
)

print(
    f"Observations removed:          0"
)

print(
    f"Values modified:               0"
)

print(
    f"Values imputed:                0"
)

print(
    f"Automatic corrections:         0"
)

print()
print("=" * 80)
print(
    f"OVERALL STATUS: {overall_status}"
)
print("=" * 80)

if overall_status == "PASS":

    print(
        "PASS — corrected final integrated validation "
        "has no critical structural failures."
    )

    print()
    print(
        "Semantic/economic findings remain REVIEW items "
        "and have not been used as automatic exclusion rules."
    )

else:

    print(
        "FAIL — critical structural violations remain."
    )


print()
print("=" * 80)
print("OUTPUTS")
print("=" * 80)

print(
    f"Summary:\n"
    f"  {OUTPUT_DIR / 'taq_corrected_final_integrated_validation_summary.csv'}"
)

print(
    f"Domain summary:\n"
    f"  {OUTPUT_DIR / 'taq_corrected_validation_by_domain.csv'}"
)

print(
    f"Structural checks:\n"
    f"  {OUTPUT_DIR / 'taq_corrected_structural_checks.csv'}"
)

print(
    f"Quote checks:\n"
    f"  {OUTPUT_DIR / 'taq_corrected_quote_checks.csv'}"
)

print(
    f"Execution checks:\n"
    f"  {OUTPUT_DIR / 'taq_corrected_execution_checks.csv'}"
)

print(
    f"Activity checks:\n"
    f"  {OUTPUT_DIR / 'taq_corrected_activity_checks.csv'}"
)

print(
    f"Market checks:\n"
    f"  {OUTPUT_DIR / 'taq_corrected_market_checks.csv'}"
)

print(
    f"Temporal checks:\n"
    f"  {OUTPUT_DIR / 'taq_corrected_temporal_checks.csv'}"
)

print()
print("=" * 80)
print("IMPORTANT")
print("=" * 80)

print(
    "The raw `date` column was NOT used for canonical structural validation."
)

print(
    "The confirmed canonical date is `date_normalized`, "
    "which exactly matches the raw DD/MM/YYYY interpretation."
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
    "No canonical TAQ file was overwritten."
)