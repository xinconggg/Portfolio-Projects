from pathlib import Path
import pandas as pd
import numpy as np


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"

INPUT_FILE = DATA_DIR / "crsp_tier1_research_dataset.csv"
OUTPUT_FILE = DATA_DIR / "crsp_tier1_panel.csv"
OUTPUT_SUMMARY = DATA_DIR / "crsp_tier1_panel_summary.csv"
OUTPUT_VALIDATION = DATA_DIR / "crsp_tier1_panel_validation.csv"


# =============================================================================
# RESEARCH WINDOW
# =============================================================================

RESEARCH_START = pd.Timestamp("1993-01-01")
RESEARCH_END = pd.Timestamp("2018-12-31")


# =============================================================================
# HELPERS
# =============================================================================

def section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def normalize_columns(df):
    df = df.copy()
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )
    return df


# =============================================================================
# LOAD DATA
# =============================================================================

section("LOADING TIER 1 RESEARCH DATASET")

df = pd.read_csv(
    INPUT_FILE,
    low_memory=False
)

df = normalize_columns(df)

print(f"Rows loaded:        {len(df):,}")
print(f"Columns loaded:     {len(df.columns):,}")
print(f"Unique PERMNOs:     {df['permno'].nunique():,}")


# =============================================================================
# VALIDATE REQUIRED COLUMNS
# =============================================================================

section("VALIDATING REQUIRED COLUMNS")

required_columns = {
    "permno",
    "dlycaldt",
    "dlyprc",
    "dlyvol",
    "dlybid",
    "dlyask",
    "dlyopen",
    "dlyhigh",
    "dlylow",
    "dlyclose",
    "dlyret",
    "dlyretx",
    "permco",
    "ticker",
}

missing_columns = required_columns - set(df.columns)

if missing_columns:
    raise ValueError(
        f"Missing required columns: {sorted(missing_columns)}"
    )

print("PASS   Required panel columns present.")


# =============================================================================
# PREPARE IDENTIFIERS AND DATES
# =============================================================================

section("PREPARING IDENTIFIERS AND DATES")

df["permno"] = pd.to_numeric(
    df["permno"],
    errors="coerce"
).astype("Int64")

df["permco"] = pd.to_numeric(
    df["permco"],
    errors="coerce"
)

df["dlycaldt"] = pd.to_datetime(
    df["dlycaldt"],
    errors="coerce"
)

invalid_dates = df["dlycaldt"].isna().sum()
missing_permno = df["permno"].isna().sum()

print(f"Invalid dates:      {invalid_dates:,}")
print(f"Missing PERMNO:     {missing_permno:,}")

if invalid_dates != 0:
    raise ValueError("Invalid daily dates detected.")

if missing_permno != 0:
    raise ValueError("Missing PERMNO values detected.")

print("PASS   Identifiers and dates prepared.")


# =============================================================================
# VALIDATE RESEARCH WINDOW
# =============================================================================

section("VALIDATING RESEARCH WINDOW")

outside_window = (
    (df["dlycaldt"] < RESEARCH_START)
    | (df["dlycaldt"] > RESEARCH_END)
).sum()

print(f"Observations outside window: {outside_window:,}")

if outside_window != 0:
    raise ValueError(
        "Observations outside research window detected."
    )

print("PASS   Research window validated.")


# =============================================================================
# VALIDATE PANEL UNIQUENESS
# =============================================================================

section("VALIDATING SECURITY-DAY UNIQUENESS")

duplicate_panel_rows = df.duplicated(
    subset=["permno", "dlycaldt"]
).sum()

print(
    f"Duplicate PERMNO-date rows: "
    f"{duplicate_panel_rows:,}"
)

if duplicate_panel_rows != 0:
    raise ValueError(
        "Duplicate PERMNO-date observations detected."
    )

print("PASS   One observation per PERMNO-date.")


# =============================================================================
# SORT PANEL
# =============================================================================

section("SORTING SECURITY-DAY PANEL")

df = df.sort_values(
    ["permno", "dlycaldt"]
).reset_index(drop=True)

print("PASS   Panel sorted by PERMNO and date.")


# =============================================================================
# BUILD LAGGED PRICE VARIABLES
# =============================================================================

section("BUILDING LAGGED MARKET VARIABLES")

group = df.groupby("permno", sort=False)

df["lag_dlyprc"] = group["dlyprc"].shift(1)
df["lag_dlyclose"] = group["dlyclose"].shift(1)
df["lag_dlyvol"] = group["dlyvol"].shift(1)
df["lag_dlycap"] = group["dlycap"].shift(1)


# =============================================================================
# DAILY PRICE RETURN
# =============================================================================

section("CALCULATING DAILY PRICE-BASED MEASURES")

valid_lag_price = (
    df["dlyprc"].notna()
    & df["lag_dlyprc"].notna()
    & (df["lag_dlyprc"] != 0)
)

df["price_return"] = np.nan

df.loc[
    valid_lag_price,
    "price_return"
] = (
    df.loc[valid_lag_price, "dlyprc"]
    / df.loc[valid_lag_price, "lag_dlyprc"]
    - 1
)

df["log_price_return"] = np.nan

valid_log_return = (
    valid_lag_price
    & (df["dlyprc"] > 0)
    & (df["lag_dlyprc"] > 0)
)

df.loc[
    valid_log_return,
    "log_price_return"
] = np.log(
    df.loc[valid_log_return, "dlyprc"]
    / df.loc[valid_log_return, "lag_dlyprc"]
)


# =============================================================================
# MIDPOINT AND SPREAD MEASURES
# =============================================================================

section("CALCULATING QUOTE MEASURES")

valid_quotes = (
    df["dlybid"].notna()
    & df["dlyask"].notna()
)

df["midpoint"] = np.nan
df["quoted_spread"] = np.nan
df["relative_quoted_spread"] = np.nan

df.loc[
    valid_quotes,
    "midpoint"
] = (
    df.loc[valid_quotes, "dlybid"]
    + df.loc[valid_quotes, "dlyask"]
) / 2

df.loc[
    valid_quotes,
    "quoted_spread"
] = (
    df.loc[valid_quotes, "dlyask"]
    - df.loc[valid_quotes, "dlybid"]
)

valid_midpoint = (
    valid_quotes
    & df["midpoint"].notna()
    & (df["midpoint"] > 0)
)

df.loc[
    valid_midpoint,
    "relative_quoted_spread"
] = (
    df.loc[valid_midpoint, "quoted_spread"]
    / df.loc[valid_midpoint, "midpoint"]
)


# =============================================================================
# QUOTE QUALITY FLAGS
# =============================================================================

section("BUILDING QUOTE QUALITY FLAGS")

df["has_two_sided_quote"] = (
    df["dlybid"].notna()
    & df["dlyask"].notna()
)

df["crossed_quote"] = (
    df["has_two_sided_quote"]
    & (df["dlybid"] > df["dlyask"])
)

df["locked_quote"] = (
    df["has_two_sided_quote"]
    & (df["dlybid"] == df["dlyask"])
)

df["normal_quote"] = (
    df["has_two_sided_quote"]
    & (df["dlybid"] < df["dlyask"])
)


# =============================================================================
# LIQUIDITY VARIABLES
# =============================================================================

section("CALCULATING DAILY LIQUIDITY MEASURES")

df["dollar_volume"] = np.nan

valid_dollar_volume = (
    df["dlyprc"].notna()
    & df["dlyvol"].notna()
    & (df["dlyprc"] > 0)
    & (df["dlyvol"] >= 0)
)

df.loc[
    valid_dollar_volume,
    "dollar_volume"
] = (
    df.loc[valid_dollar_volume, "dlyprc"]
    * df.loc[valid_dollar_volume, "dlyvol"]
)

df["amihud_illiquidity"] = np.nan

valid_amihud = (
    df["dlyret"].notna()
    & df["dollar_volume"].notna()
    & (df["dollar_volume"] > 0)
)

df.loc[
    valid_amihud,
    "amihud_illiquidity"
] = (
    df.loc[valid_amihud, "dlyret"].abs()
    / df.loc[valid_amihud, "dollar_volume"]
)


# =============================================================================
# MARKET CAPITALIZATION
# =============================================================================

section("PREPARING MARKET CAPITALIZATION")

if "dlycap" in df.columns:

    df["market_cap"] = pd.to_numeric(
        df["dlycap"],
        errors="coerce"
    )

    print("PASS   DlyCap retained as market-cap field.")

else:

    df["market_cap"] = np.nan

    print(
        "WARNING   DlyCap unavailable; "
        "market capitalization not constructed."
    )


# =============================================================================
# OBSERVATION FLAGS
# =============================================================================

section("BUILDING OBSERVATION AVAILABILITY FLAGS")

df["has_price"] = df["dlyprc"].notna()
df["has_volume"] = df["dlyvol"].notna()
df["has_return"] = df["dlyret"].notna()
df["has_bid"] = df["dlybid"].notna()
df["has_ask"] = df["dlyask"].notna()
df["has_market_cap"] = df["market_cap"].notna()

df["execution_quote_ready"] = (
    df["has_price"]
    & df["has_two_sided_quote"]
    & df["normal_quote"]
)

df["liquidity_measure_ready"] = (
    df["has_price"]
    & df["has_volume"]
    & (df["dlyvol"] >= 0)
)


# =============================================================================
# SECURITY-DAY PANEL VALIDATION
# =============================================================================

section("VALIDATING FINAL PANEL")

duplicate_panel_rows = df.duplicated(
    subset=["permno", "dlycaldt"]
).sum()

unique_permnos = df["permno"].nunique()

first_date = df["dlycaldt"].min()
last_date = df["dlycaldt"].max()

print(f"Rows:                       {len(df):,}")
print(f"Unique PERMNOs:             {unique_permnos:,}")
print(f"Duplicate PERMNO-date rows: {duplicate_panel_rows:,}")
print(f"First date:                 {first_date.date()}")
print(f"Last date:                  {last_date.date()}")

if duplicate_panel_rows != 0:
    raise ValueError(
        "Final panel contains duplicate PERMNO-date rows."
    )

if unique_permnos != 33:
    raise ValueError(
        f"Expected 33 PERMNOs, found {unique_permnos}."
    )

print("PASS   Final security-day panel validated.")


# =============================================================================
# BUILD SECURITY-LEVEL SUMMARY
# =============================================================================

section("BUILDING SECURITY-LEVEL PANEL SUMMARY")

summary = (
    df.groupby("permno")
    .agg(
        first_date=("dlycaldt", "min"),
        last_date=("dlycaldt", "max"),
        observations=("dlycaldt", "size"),
        price_observations=("has_price", "sum"),
        volume_observations=("has_volume", "sum"),
        return_observations=("has_return", "sum"),
        two_sided_quote_observations=(
            "has_two_sided_quote",
            "sum"
        ),
        normal_quote_observations=(
            "normal_quote",
            "sum"
        ),
        crossed_quote_observations=(
            "crossed_quote",
            "sum"
        ),
        execution_quote_ready_observations=(
            "execution_quote_ready",
            "sum"
        ),
        liquidity_ready_observations=(
            "liquidity_measure_ready",
            "sum"
        ),
    )
    .reset_index()
)

summary["price_coverage_pct"] = (
    summary["price_observations"]
    / summary["observations"]
    * 100
)

summary["volume_coverage_pct"] = (
    summary["volume_observations"]
    / summary["observations"]
    * 100
)

summary["quote_coverage_pct"] = (
    summary["two_sided_quote_observations"]
    / summary["observations"]
    * 100
)

summary["execution_quote_ready_pct"] = (
    summary["execution_quote_ready_observations"]
    / summary["observations"]
    * 100
)

summary["liquidity_ready_pct"] = (
    summary["liquidity_ready_observations"]
    / summary["observations"]
    * 100
)

print(
    f"Security summary rows: "
    f"{len(summary):,}"
)


# =============================================================================
# BUILD VALIDATION TABLE
# =============================================================================

section("BUILDING PANEL VALIDATION SUMMARY")

validation = {
    "row_count_positive": len(df) > 0,
    "expected_permnos": unique_permnos == 33,
    "no_duplicate_permno_date": duplicate_panel_rows == 0,
    "no_missing_permno": df["permno"].isna().sum() == 0,
    "no_missing_dates": df["dlycaldt"].isna().sum() == 0,
    "within_research_window": outside_window == 0,
    "sorted_by_permno_date": (
        df[["permno", "dlycaldt"]]
        .equals(
            df[["permno", "dlycaldt"]]
            .sort_values(["permno", "dlycaldt"])
            .reset_index(drop=True)
        )
    ),
    "security_summary_complete": (
        summary["permno"].nunique() == 33
    ),
}

validation_df = pd.DataFrame(
    [
        {
            "check": key,
            "status": "PASS" if value else "FAIL",
        }
        for key, value in validation.items()
    ]
)

for _, row in validation_df.iterrows():
    print(
        f"{row['status']:4}   {row['check']}"
    )

if not validation_df["status"].eq("PASS").all():
    raise ValueError(
        "Panel validation failed."
    )


# =============================================================================
# SAVE OUTPUTS
# =============================================================================

section("SAVING OUTPUTS")

df.to_csv(
    OUTPUT_FILE,
    index=False
)

summary.to_csv(
    OUTPUT_SUMMARY,
    index=False
)

validation_df.to_csv(
    OUTPUT_VALIDATION,
    index=False
)

print(f"Panel:")
print(f"  {OUTPUT_FILE}")
print(f"Rows: {len(df):,}")

print(f"\nSecurity summary:")
print(f"  {OUTPUT_SUMMARY}")
print(f"Rows: {len(summary):,}")

print(f"\nValidation:")
print(f"  {OUTPUT_VALIDATION}")
print(f"Rows: {len(validation_df):,}")


# =============================================================================
# FINAL SUMMARY
# =============================================================================

section("SECURITY-DAY PANEL ASSEMBLY COMPLETE")

print(f"PERMNOs:                  {unique_permnos:,}")
print(f"Daily observations:      {len(df):,}")
print(f"First date:              {first_date.date()}")
print(f"Last date:               {last_date.date()}")
print(
    f"Two-sided quote rows:    "
    f"{df['has_two_sided_quote'].sum():,}"
)
print(
    f"Normal quote rows:       "
    f"{df['normal_quote'].sum():,}"
)
print(
    f"Crossed quote rows:      "
    f"{df['crossed_quote'].sum():,}"
)
print(
    f"Execution-ready rows:    "
    f"{df['execution_quote_ready'].sum():,}"
)

print("\nPASS   Security-day research panel assembled and validated.")  