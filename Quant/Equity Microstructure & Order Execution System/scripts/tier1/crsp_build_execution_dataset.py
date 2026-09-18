from pathlib import Path
import pandas as pd
import numpy as np


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"

PANEL_FILE = DATA_DIR / "crsp_tier1_panel.csv"
PANEL_SUMMARY_FILE = DATA_DIR / "crsp_tier1_panel_summary.csv"

OUTPUT_FILE = DATA_DIR / "crsp_tier1_execution_dataset.csv"
OUTPUT_SUMMARY = DATA_DIR / "crsp_tier1_execution_dataset_summary.csv"
OUTPUT_VALIDATION = DATA_DIR / "crsp_tier1_execution_dataset_validation.csv"


# =============================================================================
# RESEARCH WINDOW
# =============================================================================

RESEARCH_START = pd.Timestamp("1993-01-01")
RESEARCH_END = pd.Timestamp("2018-12-31")


# =============================================================================
# HELPER
# =============================================================================

def section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


# =============================================================================
# LOAD DATA
# =============================================================================

section("LOADING TIER 1 SECURITY-DAY PANEL")

panel = pd.read_csv(PANEL_FILE, low_memory=False)

print(f"Rows loaded:        {len(panel):,}")
print(f"Columns loaded:     {len(panel.columns)}")
print(f"Unique PERMNOs:     {panel['permno'].nunique()}")


section("LOADING PANEL SUMMARY")

panel_summary = pd.read_csv(PANEL_SUMMARY_FILE)

print(f"Summary rows:       {len(panel_summary):,}")
print(f"Summary PERMNOs:    {panel_summary['permno'].nunique()}")


# =============================================================================
# NORMALIZE COLUMN NAMES
# =============================================================================

section("NORMALIZING COLUMN NAMES")

panel.columns = panel.columns.str.lower()
panel_summary.columns = panel_summary.columns.str.lower()

print("PASS   Column names standardized to lowercase.")


# =============================================================================
# REQUIRED COLUMNS
# =============================================================================

section("VALIDATING REQUIRED COLUMNS")

required_columns = [
    "permno",
    "permco",
    "ticker",
    "dlycaldt",
    "dlyprc",
    "dlyvol",
    "dlybid",
    "dlyask",
]

missing_columns = [
    col for col in required_columns
    if col not in panel.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required panel columns: {missing_columns}"
    )

print("PASS   Required execution columns present.")


# =============================================================================
# PREPARE IDENTIFIERS AND DATES
# =============================================================================

section("PREPARING IDENTIFIERS AND DATES")

panel["permno"] = pd.to_numeric(
    panel["permno"],
    errors="coerce"
).astype("Int64")

panel["permco"] = pd.to_numeric(
    panel["permco"],
    errors="coerce"
).astype("Int64")

panel["dlycaldt"] = pd.to_datetime(
    panel["dlycaldt"],
    errors="coerce"
)

invalid_dates = panel["dlycaldt"].isna().sum()
missing_permno = panel["permno"].isna().sum()

print(f"Invalid dates:      {invalid_dates}")
print(f"Missing PERMNO:     {missing_permno}")

if invalid_dates != 0:
    raise ValueError("Invalid daily dates detected.")

if missing_permno != 0:
    raise ValueError("Missing PERMNO values detected.")

print("PASS   Identifiers and dates prepared.")


# =============================================================================
# SORT PANEL
# =============================================================================

panel = panel.sort_values(
    ["permno", "dlycaldt"]
).reset_index(drop=True)


# =============================================================================
# BASIC EXECUTION VARIABLES
# =============================================================================

section("BUILDING EXECUTION VARIABLES")

# -------------------------------------------------------------------------
# Midquote
# -------------------------------------------------------------------------

panel["midquote"] = np.where(
    panel["dlybid"].notna()
    & panel["dlyask"].notna()
    & (panel["dlybid"] > 0)
    & (panel["dlyask"] > 0),
    (panel["dlybid"] + panel["dlyask"]) / 2,
    np.nan,
)


# -------------------------------------------------------------------------
# Quoted spread
# -------------------------------------------------------------------------

panel["quoted_spread"] = np.where(
    panel["midquote"].notna()
    & (panel["midquote"] > 0),
    panel["dlyask"] - panel["dlybid"],
    np.nan,
)


# -------------------------------------------------------------------------
# Relative quoted spread
# -------------------------------------------------------------------------

panel["relative_quoted_spread"] = np.where(
    panel["midquote"].notna()
    & (panel["midquote"] > 0),
    panel["quoted_spread"] / panel["midquote"],
    np.nan,
)


# -------------------------------------------------------------------------
# Quoted spread in basis points
# -------------------------------------------------------------------------

panel["quoted_spread_bps"] = (
    panel["relative_quoted_spread"] * 10_000
)


# -------------------------------------------------------------------------
# Quote midpoint validity
# -------------------------------------------------------------------------

panel["valid_two_sided_quote"] = (
    panel["dlybid"].notna()
    & panel["dlyask"].notna()
    & (panel["dlybid"] > 0)
    & (panel["dlyask"] > 0)
)


# -------------------------------------------------------------------------
# Normal execution quote
#
# A crossed quote is retained in the dataset but is not execution-ready.
# -------------------------------------------------------------------------

panel["normal_quote"] = (
    panel["valid_two_sided_quote"]
    & (panel["dlybid"] <= panel["dlyask"])
)


# -------------------------------------------------------------------------
# Crossed quote
# -------------------------------------------------------------------------

panel["crossed_quote"] = (
    panel["valid_two_sided_quote"]
    & (panel["dlybid"] > panel["dlyask"])
)


# =============================================================================
# PRICE / VOLUME EXECUTION FLAGS
# =============================================================================

section("BUILDING PRICE AND VOLUME FLAGS")

panel["valid_price"] = (
    panel["dlyprc"].notna()
    & (panel["dlyprc"] > 0)
)

panel["valid_volume"] = (
    panel["dlyvol"].notna()
    & (panel["dlyvol"] >= 0)
)

panel["positive_volume"] = (
    panel["dlyvol"].notna()
    & (panel["dlyvol"] > 0)
)


# =============================================================================
# MARKET CAP FLAG
# =============================================================================

section("BUILDING MARKET-CAPITALIZATION FLAGS")

if "dlycap" in panel.columns:

    panel["valid_market_cap"] = (
        panel["dlycap"].notna()
        & (panel["dlycap"] > 0)
    )

else:

    panel["valid_market_cap"] = False

    print("WARNING  DlyCap not available.")


# =============================================================================
# EXECUTION ELIGIBILITY
# =============================================================================

section("CONSTRUCTING EXECUTION ELIGIBILITY FLAGS")

# -------------------------------------------------------------------------
# Basic execution-ready observation
#
# This is deliberately conservative:
#   1. valid price
#   2. valid volume
#   3. two-sided quote
#   4. non-crossed quote
#
# We do not require positive volume because zero-volume observations
# may still be useful for certain daily panel analyses.
# -------------------------------------------------------------------------

panel["execution_ready"] = (
    panel["valid_price"]
    & panel["valid_volume"]
    & panel["normal_quote"]
)


# -------------------------------------------------------------------------
# Strict execution-ready observation
#
# Requires positive reported volume.
# -------------------------------------------------------------------------

panel["execution_ready_positive_volume"] = (
    panel["valid_price"]
    & panel["positive_volume"]
    & panel["normal_quote"]
)


# =============================================================================
# LIQUIDITY MEASURES
# =============================================================================

section("BUILDING EXECUTION LIQUIDITY MEASURES")

# Dollar trading volume
panel["dollar_volume"] = np.where(
    panel["dlyprc"].notna()
    & panel["dlyvol"].notna()
    & (panel["dlyprc"] > 0)
    & (panel["dlyvol"] >= 0),
    panel["dlyprc"] * panel["dlyvol"],
    np.nan,
)


# Log dollar volume
panel["log_dollar_volume"] = np.nan

positive_dollar_volume = (
    panel["dollar_volume"].notna()
    & (panel["dollar_volume"] > 0)
)

panel.loc[
    positive_dollar_volume,
    "log_dollar_volume"
] = np.log(
    panel.loc[
        positive_dollar_volume,
        "dollar_volume"
    ]
)


# Turnover proxy when market capitalization is available
if "dlycap" in panel.columns:

    panel["turnover"] = np.where(
        panel["dlycap"].notna()
        & (panel["dlycap"] > 0)
        & panel["dlyvol"].notna()
        & (panel["dlyvol"] >= 0),
        panel["dlyvol"] / panel["dlycap"],
        np.nan,
    )

else:

    panel["turnover"] = np.nan


# =============================================================================
# RETURN / VOLATILITY FLAGS
# =============================================================================

section("BUILDING RETURN AND PRICE-JUMP FLAGS")

if "dlyret" in panel.columns:

    panel["valid_return"] = panel["dlyret"].notna()

    panel["large_return_outlier"] = (
        panel["dlyret"].abs() > 0.50
    )

else:

    panel["valid_return"] = False
    panel["large_return_outlier"] = False


if "large_price_jump" in panel.columns:

    panel["large_price_jump_flag"] = (
        panel["large_price_jump"].fillna(False).astype(bool)
    )

else:

    panel["large_price_jump_flag"] = False


# =============================================================================
# EXECUTION DIAGNOSTIC FLAGS
# =============================================================================

section("BUILDING EXECUTION DIAGNOSTIC FLAGS")

panel["quote_available"] = panel["valid_two_sided_quote"]

panel["quote_usable"] = panel["normal_quote"]

panel["price_available"] = panel["valid_price"]

panel["volume_available"] = panel["valid_volume"]

panel["execution_observation"] = panel["execution_ready"]


# =============================================================================
# RESEARCH WINDOW VALIDATION
# =============================================================================

section("VALIDATING RESEARCH WINDOW")

outside_window = (
    (panel["dlycaldt"] < RESEARCH_START)
    | (panel["dlycaldt"] > RESEARCH_END)
).sum()

print(f"Observations outside window: {outside_window}")

if outside_window != 0:
    raise ValueError(
        "Execution dataset contains observations outside research window."
    )

print("PASS   Research window validated.")


# =============================================================================
# VALIDATE SECURITY-DAY UNIQUENESS
# =============================================================================

section("VALIDATING SECURITY-DAY UNIQUENESS")

duplicates = panel.duplicated(
    subset=["permno", "dlycaldt"]
).sum()

print(f"Duplicate PERMNO-date rows: {duplicates}")

if duplicates != 0:
    raise ValueError(
        "Duplicate PERMNO-date observations detected."
    )

print("PASS   One observation per PERMNO-date.")


# =============================================================================
# VALIDATE PERMNO COVERAGE
# =============================================================================

section("VALIDATING PERMNO COVERAGE")

panel_permnos = set(panel["permno"].dropna().astype(int))
summary_permnos = set(
    panel_summary["permno"].dropna().astype(int)
)

missing_from_panel = summary_permnos - panel_permnos
unexpected_in_panel = panel_permnos - summary_permnos

print(f"Summary PERMNOs:          {len(summary_permnos)}")
print(f"Panel PERMNOs:            {len(panel_permnos)}")
print(f"Missing from panel:       {len(missing_from_panel)}")
print(f"Unexpected in panel:      {len(unexpected_in_panel)}")

if missing_from_panel or unexpected_in_panel:
    raise ValueError(
        "PERMNO coverage does not match panel summary."
    )

print("PASS   PERMNO coverage validated.")


# =============================================================================
# BUILD SECURITY-LEVEL SUMMARY
# =============================================================================

section("BUILDING EXECUTION DATASET SUMMARY")

security_summary = (
    panel.groupby("permno", as_index=False)
    .agg(
        permco=("permco", "first"),
        ticker=("ticker", "first"),
        first_date=("dlycaldt", "min"),
        last_date=("dlycaldt", "max"),
        observations=("dlycaldt", "size"),
        valid_price_rows=("valid_price", "sum"),
        valid_volume_rows=("valid_volume", "sum"),
        two_sided_quote_rows=("valid_two_sided_quote", "sum"),
        normal_quote_rows=("normal_quote", "sum"),
        crossed_quote_rows=("crossed_quote", "sum"),
        execution_ready_rows=("execution_ready", "sum"),
        positive_volume_rows=("positive_volume", "sum"),
        positive_volume_execution_rows=(
            "execution_ready_positive_volume",
            "sum",
        ),
        mean_relative_quoted_spread=(
            "relative_quoted_spread",
            "mean",
        ),
        median_relative_quoted_spread=(
            "relative_quoted_spread",
            "median",
        ),
        mean_dollar_volume=(
            "dollar_volume",
            "mean",
        ),
        median_dollar_volume=(
            "dollar_volume",
            "median",
        ),
    )
)

security_summary["quote_coverage"] = (
    security_summary["two_sided_quote_rows"]
    / security_summary["observations"]
)

security_summary["execution_coverage"] = (
    security_summary["execution_ready_rows"]
    / security_summary["observations"]
)

security_summary["positive_volume_execution_coverage"] = (
    security_summary["positive_volume_execution_rows"]
    / security_summary["observations"]
)


# =============================================================================
# VALIDATE SUMMARY
# =============================================================================

section("VALIDATING EXECUTION SUMMARY")

expected_permnos = set(panel_permnos)
summary_permnos_final = set(
    security_summary["permno"].astype(int)
)

missing_summary = expected_permnos - summary_permnos_final
unexpected_summary = summary_permnos_final - expected_permnos

print(f"Panel securities:          {len(expected_permnos)}")
print(f"Summary securities:        {len(summary_permnos_final)}")
print(f"Missing securities:        {len(missing_summary)}")
print(f"Unexpected securities:     {len(unexpected_summary)}")

if missing_summary or unexpected_summary:
    raise ValueError(
        "Execution security summary does not match panel universe."
    )

print("PASS   Execution summary contains exactly one row per PERMNO.")


# =============================================================================
# FINAL VALIDATION
# =============================================================================

section("FINAL EXECUTION DATASET VALIDATION")

validation_results = {
    "row_count_positive": len(panel) > 0,
    "expected_permnos": len(panel_permnos) == 33,
    "no_duplicate_permno_date": duplicates == 0,
    "no_missing_permno": missing_permno == 0,
    "all_within_research_window": outside_window == 0,
    "security_summary_complete": (
        len(summary_permnos_final) == len(expected_permnos)
    ),
    "execution_flags_present": (
        panel["execution_ready"].notna().all()
    ),
}

validation_rows = []

for check, passed in validation_results.items():

    print(
        f"{'PASS' if passed else 'FAIL'}   {check}"
    )

    validation_rows.append(
        {
            "check": check,
            "passed": passed,
        }
    )

if not all(validation_results.values()):
    raise ValueError(
        "Execution dataset validation failed."
    )


# =============================================================================
# FINAL OUTPUT COLUMNS
# =============================================================================

section("PREPARING OUTPUT DATA")

preferred_columns = [
    "permno",
    "permco",
    "ticker",
    "dlycaldt",

    "dlyprc",
    "dlyvol",
    "dlybid",
    "dlyask",
    "dlyret",

    "midquote",
    "quoted_spread",
    "relative_quoted_spread",
    "quoted_spread_bps",

    "dollar_volume",
    "log_dollar_volume",
    "turnover",

    "valid_price",
    "valid_volume",
    "positive_volume",
    "valid_market_cap",

    "quote_available",
    "quote_usable",
    "crossed_quote",

    "valid_return",
    "large_return_outlier",
    "large_price_jump_flag",

    "execution_ready",
    "execution_ready_positive_volume",
]

available_columns = [
    col for col in preferred_columns
    if col in panel.columns
]

execution_dataset = panel[available_columns].copy()


# =============================================================================
# BUILD OVERALL SUMMARY
# =============================================================================

section("BUILDING OVERALL EXECUTION SUMMARY")

summary_rows = [
    ("total_observations", len(panel)),
    ("total_securities", panel["permno"].nunique()),
    ("two_sided_quote_rows", int(panel["quote_available"].sum())),
    ("normal_quote_rows", int(panel["quote_usable"].sum())),
    ("crossed_quote_rows", int(panel["crossed_quote"].sum())),
    ("execution_ready_rows", int(panel["execution_ready"].sum())),
    (
        "execution_ready_positive_volume_rows",
        int(panel["execution_ready_positive_volume"].sum()),
    ),
    ("valid_price_rows", int(panel["valid_price"].sum())),
    ("valid_volume_rows", int(panel["valid_volume"].sum())),
    ("positive_volume_rows", int(panel["positive_volume"].sum())),
]

overall_summary = pd.DataFrame(
    summary_rows,
    columns=["metric", "value"]
)


# =============================================================================
# SAVE OUTPUTS
# =============================================================================

section("SAVING OUTPUTS")

execution_dataset.to_csv(
    OUTPUT_FILE,
    index=False
)

security_summary.to_csv(
    OUTPUT_SUMMARY,
    index=False
)

pd.DataFrame(validation_rows).to_csv(
    OUTPUT_VALIDATION,
    index=False
)

print(f"Execution dataset:")
print(f"  {OUTPUT_FILE}")
print(f"Rows: {len(execution_dataset):,}")

print(f"\nExecution summary:")
print(f"  {OUTPUT_SUMMARY}")
print(f"Rows: {len(security_summary):,}")

print(f"\nValidation:")
print(f"  {OUTPUT_VALIDATION}")
print(f"Rows: {len(validation_rows):,}")


# =============================================================================
# FINAL STATUS
# =============================================================================

section("EXECUTION DATASET ASSEMBLY COMPLETE")

print(
    f"Tier 1 securities:             "
    f"{panel['permno'].nunique()}"
)

print(
    f"Daily observations:            "
    f"{len(panel):,}"
)

print(
    f"Two-sided quote rows:          "
    f"{panel['quote_available'].sum():,}"
)

print(
    f"Normal quote rows:             "
    f"{panel['quote_usable'].sum():,}"
)

print(
    f"Crossed quote rows:            "
    f"{panel['crossed_quote'].sum():,}"
)

print(
    f"Execution-ready rows:          "
    f"{panel['execution_ready'].sum():,}"
)

print(
    f"Positive-volume execution rows:"
    f" {panel['execution_ready_positive_volume'].sum():,}"
)

print("\nPASS   Execution dataset assembled and validated.")