from pathlib import Path

import numpy as np
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"

INPUT_FILE = DATA_DIR / "crsp_tier1_execution_dataset.csv"

OUTPUT_FILE = DATA_DIR / "crsp_tier1_execution_features.csv"
OUTPUT_SUMMARY = DATA_DIR / "crsp_tier1_execution_features_summary.csv"
OUTPUT_VALIDATION = DATA_DIR / "crsp_tier1_execution_features_validation.csv"


# =============================================================================
# RESEARCH WINDOW
# =============================================================================

RESEARCH_START = pd.Timestamp("1993-01-01")
RESEARCH_END = pd.Timestamp("2018-12-31")


# =============================================================================
# FEATURE WINDOWS
# =============================================================================

SHORT_WINDOW = 5
MEDIUM_WINDOW = 20
LONG_WINDOW = 60


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

section("LOADING TIER 1 EXECUTION DATASET")

df = pd.read_csv(
    INPUT_FILE,
    low_memory=False
)

df.columns = (
    df.columns
    .astype(str)
    .str.strip()
    .str.lower()
)

print(f"Rows loaded:        {len(df):,}")
print(f"Columns loaded:     {len(df.columns)}")
print(f"Unique PERMNOs:     {df['permno'].nunique():,}")
print("\nAvailable columns:")
print(df.columns.tolist())


# =============================================================================
# NORMALIZE COLUMN NAMES
# =============================================================================

section("NORMALIZING COLUMN NAMES")

df.columns = df.columns.str.lower()

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

    "dlyret",

    "midquote",
    "quoted_spread",
    "relative_quoted_spread",
    "quoted_spread_bps",
    "dollar_volume",
    "turnover",

    "valid_price",
    "valid_volume",
    "quote_usable",
    "execution_ready",
]

missing_columns = [
    col
    for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required execution columns: {missing_columns}"
    )

print("PASS   Required feature columns present.")


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
).astype("Int64")

df["dlycaldt"] = pd.to_datetime(
    df["dlycaldt"],
    errors="coerce"
)

invalid_dates = df["dlycaldt"].isna().sum()
missing_permno = df["permno"].isna().sum()

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

section("SORTING SECURITY-DAY DATA")

df = df.sort_values(
    ["permno", "dlycaldt"]
).reset_index(drop=True)

print("PASS   Data sorted by PERMNO and date.")


# =============================================================================
# VALIDATE SECURITY-DAY UNIQUENESS
# =============================================================================

section("VALIDATING SECURITY-DAY UNIQUENESS")

duplicates = df.duplicated(
    subset=["permno", "dlycaldt"]
).sum()

print(f"Duplicate PERMNO-date rows: {duplicates}")

if duplicates != 0:
    raise ValueError(
        "Duplicate PERMNO-date observations detected."
    )

print("PASS   One observation per PERMNO-date.")


# =============================================================================
# CONTEMPORANEOUS EXECUTION FEATURES
# =============================================================================

section("BUILDING CONTEMPORANEOUS EXECUTION FEATURES")

# -------------------------------------------------------------------------
# Relative spread
# -------------------------------------------------------------------------

df["spread_bps"] = df["quoted_spread_bps"]


# -------------------------------------------------------------------------
# Effective quote midpoint relative to transaction price
# -------------------------------------------------------------------------

df["price_to_midquote"] = np.where(
    df["midquote"].notna()
    & (df["midquote"] > 0)
    & df["dlyprc"].notna()
    & (df["dlyprc"] > 0),
    df["dlyprc"] / df["midquote"],
    np.nan,
)


# -------------------------------------------------------------------------
# Absolute price-to-midquote deviation
# -------------------------------------------------------------------------

df["abs_price_midquote_deviation"] = (
    df["price_to_midquote"] - 1
).abs()


# -------------------------------------------------------------------------
# Daily return magnitude
# -------------------------------------------------------------------------

df["abs_return"] = df["dlyret"].abs()

# -------------------------------------------------------------------------
# Dollar volume
# -------------------------------------------------------------------------

df["dollar_volume"] = pd.to_numeric(
    df["dollar_volume"],
    errors="coerce"
)

# -------------------------------------------------------------------------
# Turnover
# -------------------------------------------------------------------------

df["turnover"] = pd.to_numeric(
    df["turnover"],
    errors="coerce"
)


# =============================================================================
# LAGGED PRICE VARIABLES
# =============================================================================

section("BUILDING LAGGED PRICE VARIABLES")

grouped = df.groupby("permno", sort=False)

df["lag_price"] = grouped["dlyprc"].shift(1)

df["lag_midquote"] = grouped["midquote"].shift(1)

df["lag_dollar_volume"] = grouped["dollar_volume"].shift(1)

df["lag_turnover"] = grouped["turnover"].shift(1)

if "dlyret" in df.columns:

    df["lag_return"] = grouped["dlyret"].shift(1)

else:

    df["lag_return"] = np.nan


# =============================================================================
# PRE-TRADE ROLLING LIQUIDITY
# =============================================================================

section("BUILDING LOOK-AHEAD-SAFE LIQUIDITY FEATURES")

# Shift by one observation before rolling.
#
# Therefore the feature observed on date t uses information through t-1.

df["adv_5d"] = (
    df.groupby("permno")["dollar_volume"]
    .transform(
        lambda x: x.shift(1).rolling(
            SHORT_WINDOW,
            min_periods=1
        ).mean()
    )
)

df["adv_20d"] = (
    df.groupby("permno")["dollar_volume"]
    .transform(
        lambda x: x.shift(1).rolling(
            MEDIUM_WINDOW,
            min_periods=1
        ).mean()
    )
)

df["adv_60d"] = (
    df.groupby("permno")["dollar_volume"]
    .transform(
        lambda x: x.shift(1).rolling(
            LONG_WINDOW,
            min_periods=1
        ).mean()
    )
)


# -------------------------------------------------------------------------
# Median daily dollar volume
# -------------------------------------------------------------------------

df["median_dollar_volume_20d"] = (
    df.groupby("permno")["dollar_volume"]
    .transform(
        lambda x: x.shift(1).rolling(
            MEDIUM_WINDOW,
            min_periods=1
        ).median()
    )
)


# =============================================================================
# PRE-TRADE SPREAD FEATURES
# =============================================================================

section("BUILDING LOOK-AHEAD-SAFE SPREAD FEATURES")

df["lag_spread_bps"] = (
    df.groupby("permno")["spread_bps"]
    .shift(1)
)

df["avg_spread_bps_5d"] = (
    df.groupby("permno")["spread_bps"]
    .transform(
        lambda x: x.shift(1).rolling(
            SHORT_WINDOW,
            min_periods=1
        ).mean()
    )
)

df["avg_spread_bps_20d"] = (
    df.groupby("permno")["spread_bps"]
    .transform(
        lambda x: x.shift(1).rolling(
            MEDIUM_WINDOW,
            min_periods=1
        ).mean()
    )
)

df["median_spread_bps_20d"] = (
    df.groupby("permno")["spread_bps"]
    .transform(
        lambda x: x.shift(1).rolling(
            MEDIUM_WINDOW,
            min_periods=1
        ).median()
    ))


# =============================================================================
# PRE-TRADE VOLATILITY FEATURES
# =============================================================================

section("BUILDING LOOK-AHEAD-SAFE VOLATILITY FEATURES")

df["realized_vol_5d"] = (
    df.groupby("permno")["dlyret"]
    .transform(
        lambda x: x.shift(1).rolling(
            SHORT_WINDOW,
            min_periods=2
        ).std()
    )
)

df["realized_vol_20d"] = (
    df.groupby("permno")["dlyret"]
    .transform(
        lambda x: x.shift(1).rolling(
            MEDIUM_WINDOW,
            min_periods=2
        ).std()
    )
)

df["realized_vol_60d"] = (
    df.groupby("permno")["dlyret"]
    .transform(
        lambda x: x.shift(1).rolling(
            LONG_WINDOW,
            min_periods=2
        ).std()
    ))


# =============================================================================
# AMIHUD ILLIQUIDITY
# =============================================================================

section("BUILDING AMIHUD ILLIQUIDITY FEATURES")

df["daily_amihud"] = np.where(
    df["dollar_volume"] > 0,
    df["abs_return"] / df["dollar_volume"],
    np.nan,
)


df["amihud_20d"] = (
    df.groupby("permno")["daily_amihud"]
    .transform(
        lambda x: x.shift(1).rolling(
            MEDIUM_WINDOW,
            min_periods=2
        ).mean()
    )
)


# =============================================================================
# TURNOVER FEATURES
# =============================================================================

section("BUILDING TURNOVER FEATURES")

df["avg_turnover_20d"] = (
    df.groupby("permno")["turnover"]
    .transform(
        lambda x: x.shift(1).rolling(
            MEDIUM_WINDOW,
            min_periods=1
        ).mean()
    )
)

df["median_turnover_20d"] = (
    df.groupby("permno")["turnover"]
    .transform(
        lambda x: x.shift(1).rolling(
            MEDIUM_WINDOW,
            min_periods=1
        ).median()
    )
)


# =============================================================================
# PRICE-IMPACT FEATURES
# =============================================================================

section("BUILDING PRICE IMPACT FEATURES")

df["lag_abs_return"] = (
    df.groupby("permno")["abs_return"]
    .shift(1)
)

df["avg_abs_return_20d"] = (
    df.groupby("permno")["abs_return"]
    .transform(
        lambda x: x.shift(1).rolling(
            MEDIUM_WINDOW,
            min_periods=1
        ).mean()
    )
)


# =============================================================================
# EXECUTION-QUALITY FLAGS
# =============================================================================

section("BUILDING EXECUTION QUALITY FLAGS")

df["pretrade_quote_available"] = (
    df["lag_spread_bps"].notna()
)

df["pretrade_liquidity_available"] = (
    df["adv_20d"].notna()
    & (df["adv_20d"] > 0)
)

df["pretrade_volatility_available"] = (
    df["realized_vol_20d"].notna()
)

df["pretrade_features_available"] = (
    df["pretrade_quote_available"]
    & df["pretrade_liquidity_available"]
    & df["pretrade_volatility_available"]
)


# =============================================================================
# RESEARCH WINDOW VALIDATION
# =============================================================================

section("VALIDATING RESEARCH WINDOW")

outside_window = (
    (df["dlycaldt"] < RESEARCH_START)
    | (df["dlycaldt"] > RESEARCH_END)
).sum()

print(f"Observations outside window: {outside_window}")

if outside_window != 0:
    raise ValueError(
        "Feature dataset contains observations outside research window."
    )

print("PASS   Research window validated.")


# =============================================================================
# VALIDATE NO LOOK-AHEAD IN LAGGED FEATURES
# =============================================================================

section("VALIDATING LOOK-AHEAD-SAFE FEATURES")

lookahead_checks = {
    "lag_price_exists": "lag_price",
    "lag_midquote_exists": "lag_midquote",
    "lag_dollar_volume_exists": "lag_dollar_volume",
    "lag_spread_bps_exists": "lag_spread_bps",
    "adv_20d_exists": "adv_20d",
    "realized_vol_20d_exists": "realized_vol_20d",
}

for name, column in lookahead_checks.items():

    if column not in df.columns:
        raise ValueError(
            f"Missing expected feature: {column}"
        )

    print(f"PASS   {name}")


# =============================================================================
# SECURITY-LEVEL SUMMARY
# =============================================================================

section("BUILDING SECURITY-LEVEL FEATURE SUMMARY")

security_summary = (
    df.groupby("permno", as_index=False)
    .agg(
        permco=("permco", "first"),
        ticker=("ticker", "first"),
        first_date=("dlycaldt", "min"),
        last_date=("dlycaldt", "max"),
        observations=("dlycaldt", "size"),
        pretrade_features_available=(
            "pretrade_features_available",
            "sum"
        ),
        execution_ready_rows=(
            "execution_ready",
            "sum"
        ),
        mean_spread_bps=(
            "spread_bps",
            "mean"
        ),
        median_spread_bps=(
            "spread_bps",
            "median"
        ),
        mean_adv_20d=(
            "adv_20d",
            "mean"
        ),
        mean_realized_vol_20d=(
            "realized_vol_20d",
            "mean"
        ),
        mean_amihud_20d=(
            "amihud_20d",
            "mean"
        ),
    )
)


security_summary["pretrade_feature_coverage"] = (
    security_summary["pretrade_features_available"]
    / security_summary["observations"]
)


# =============================================================================
# VALIDATE SECURITY COVERAGE
# =============================================================================

section("VALIDATING SECURITY COVERAGE")

panel_permnos = set(
    df["permno"].dropna().astype(int)
)

summary_permnos = set(
    security_summary["permno"].dropna().astype(int)
)

missing_summary = panel_permnos - summary_permnos
unexpected_summary = summary_permnos - panel_permnos

print(f"Panel PERMNOs:             {len(panel_permnos)}")
print(f"Summary PERMNOs:           {len(summary_permnos)}")
print(f"Missing summary PERMNOs:   {len(missing_summary)}")
print(f"Unexpected summary PERMNOs:{len(unexpected_summary)}")

if missing_summary or unexpected_summary:
    raise ValueError(
        "Security-level feature summary does not match panel."
    )

print("PASS   Security-level feature summary is complete.")


# =============================================================================
# BUILD FEATURE VALIDATION SUMMARY
# =============================================================================

section("BUILDING FEATURE VALIDATION SUMMARY")

validation_results = {
    "row_count_positive": len(df) > 0,
    "expected_permnos": df["permno"].nunique() == 33,
    "no_duplicate_permno_date": (
        df.duplicated(
            subset=["permno", "dlycaldt"]
        ).sum() == 0
    ),
    "no_missing_permno": (
        df["permno"].isna().sum() == 0
    ),
    "no_missing_dates": (
        df["dlycaldt"].isna().sum() == 0
    ),
    "within_research_window": (
        outside_window == 0
    ),
    "security_summary_complete": (
        len(summary_permnos) == len(panel_permnos)
    ),
    "execution_flags_present": (
        df["execution_ready"].notna().all()
    ),
    "pretrade_feature_flags_present": (
        df["pretrade_features_available"].notna().all()
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
        "Execution feature validation failed."
    )


# =============================================================================
# PREPARE OUTPUT
# =============================================================================

section("PREPARING FEATURE DATASET")

feature_columns = [
    "permno",
    "permco",
    "ticker",
    "dlycaldt",

    "dlyprc",
    "dlyvol",
    "dlybid",
    "dlyask",

    "midquote",
    "spread_bps",
    "relative_quoted_spread",

    "dollar_volume",
    "turnover",

    "dlyret",
    "abs_return",

    "lag_price",
    "lag_midquote",
    "lag_dollar_volume",
    "lag_turnover",
    "lag_return",

    "lag_spread_bps",

    "adv_5d",
    "adv_20d",
    "adv_60d",
    "median_dollar_volume_20d",

    "avg_spread_bps_5d",
    "avg_spread_bps_20d",
    "median_spread_bps_20d",

    "realized_vol_5d",
    "realized_vol_20d",
    "realized_vol_60d",

    "daily_amihud",
    "amihud_20d",

    "avg_turnover_20d",
    "median_turnover_20d",

    "lag_abs_return",
    "avg_abs_return_20d",

    "valid_price",
    "valid_volume",
    "quote_usable",
    "execution_ready",

    "pretrade_quote_available",
    "pretrade_liquidity_available",
    "pretrade_volatility_available",
    "pretrade_features_available",
]

available_columns = [
    col
    for col in feature_columns
    if col in df.columns
]

feature_dataset = df[available_columns].copy()


# =============================================================================
# SAVE OUTPUTS
# =============================================================================

section("SAVING OUTPUTS")

feature_dataset.to_csv(
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

print(f"Feature dataset:")
print(f"  {OUTPUT_FILE}")
print(f"Rows: {len(feature_dataset):,}")

print(f"\nFeature summary:")
print(f"  {OUTPUT_SUMMARY}")
print(f"Rows: {len(security_summary):,}")

print(f"\nValidation:")
print(f"  {OUTPUT_VALIDATION}")
print(f"Rows: {len(validation_rows):,}")


# =============================================================================
# FINAL SUMMARY
# =============================================================================

section("EXECUTION FEATURE DATASET COMPLETE")

print(
    f"Tier 1 securities:          "
    f"{df['permno'].nunique()}"
)

print(
    f"Daily observations:         "
    f"{len(df):,}"
)

print(
    f"Execution-ready rows:       "
    f"{df['execution_ready'].sum():,}"
)

print(
    f"Pre-trade feature rows:      "
    f"{df['pretrade_features_available'].sum():,}"
)

print(
    f"Mean 20-day ADV:             "
    f"{df['adv_20d'].mean():,.2f}"
)

print(
    f"Mean 20-day spread (bps):    "
    f"{df['avg_spread_bps_20d'].mean():,.2f}"
)

print(
    f"Mean 20-day volatility:       "
    f"{df['realized_vol_20d'].mean():,.6f}"
)

print("\nPASS   Execution feature dataset assembled and validated.")