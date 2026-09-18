from pathlib import Path

import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"


ELIGIBLE_UNIVERSE_FILE = DATA_DIR / "crsp_tier1_eligible_universe.csv"
DAILY_FILE = DATA_DIR / "crsp_daily_clean.csv"

OUTPUT_DAILY_FILE = DATA_DIR / "crsp_tier1_daily.csv"
OUTPUT_SUMMARY_FILE = DATA_DIR / "crsp_tier1_daily_summary.csv"


# =============================================================================
# RESEARCH WINDOW
# =============================================================================

RESEARCH_START = pd.Timestamp("1993-01-01")
RESEARCH_END = pd.Timestamp("2018-12-31")


# =============================================================================
# HELPERS
# =============================================================================

def normalize_columns(df):
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )
    return df


def normalize_permno(series):
    return pd.to_numeric(series, errors="coerce").astype("Int64")


# =============================================================================
# LOAD ELIGIBLE UNIVERSE
# =============================================================================

print("=" * 80)
print("LOADING ELIGIBLE TIER 1 UNIVERSE")
print("=" * 80)

universe = pd.read_csv(ELIGIBLE_UNIVERSE_FILE)
universe = normalize_columns(universe)

print(f"Rows loaded:        {len(universe):,}")
print(f"Unique PERMNOs:     {universe['permno'].nunique():,}")


# =============================================================================
# LOAD DAILY DATA
# =============================================================================

print("\n" + "=" * 80)
print("LOADING CLEAN CRSP DAILY DATA")
print("=" * 80)

daily = pd.read_csv(DAILY_FILE)
daily = normalize_columns(daily)

print(f"Rows loaded:        {len(daily):,}")
print(f"Unique PERMNOs:     {daily['permno'].nunique():,}")


# =============================================================================
# VALIDATE REQUIRED COLUMNS
# =============================================================================

print("\n" + "=" * 80)
print("VALIDATING REQUIRED COLUMNS")
print("=" * 80)

required_universe_columns = {
    "permno",
    "securitytype",
    "securitysubtype",
    "daily_first_date",
    "daily_last_date",
    "has_daily_history",
}

required_daily_columns = {
    "permno",
    "dlycaldt",
}

missing_universe_columns = (
    required_universe_columns - set(universe.columns)
)

missing_daily_columns = (
    required_daily_columns - set(daily.columns)
)

if missing_universe_columns:
    raise ValueError(
        f"Missing required universe columns: "
        f"{sorted(missing_universe_columns)}"
    )

if missing_daily_columns:
    raise ValueError(
        f"Missing required daily columns: "
        f"{sorted(missing_daily_columns)}"
    )

print("PASS   Required columns present.")


# =============================================================================
# NORMALIZE IDENTIFIERS
# =============================================================================

print("\n" + "=" * 80)
print("NORMALIZING IDENTIFIERS")
print("=" * 80)

universe["permno"] = normalize_permno(universe["permno"])
daily["permno"] = normalize_permno(daily["permno"])

if universe["permno"].isna().any():
    raise ValueError("Eligible universe contains missing PERMNO values.")

if daily["permno"].isna().any():
    raise ValueError("Daily data contains missing PERMNO values.")

print("PASS   PERMNO identifiers normalized.")


# =============================================================================
# PREPARE DATES
# =============================================================================

print("\n" + "=" * 80)
print("PREPARING DAILY DATES")
print("=" * 80)

daily["dlycaldt"] = pd.to_datetime(
    daily["dlycaldt"],
    errors="coerce"
)

invalid_dates = daily["dlycaldt"].isna().sum()

print(f"Invalid DlyCalDt values: {invalid_dates:,}")

if invalid_dates > 0:
    raise ValueError("Daily data contains invalid DlyCalDt values.")

print(
    f"Daily date range: "
    f"{daily['dlycaldt'].min().date()} to "
    f"{daily['dlycaldt'].max().date()}"
)


# =============================================================================
# VALIDATE ELIGIBLE UNIVERSE
# =============================================================================

print("\n" + "=" * 80)
print("VALIDATING ELIGIBLE UNIVERSE")
print("=" * 80)

duplicate_universe_permnos = universe["permno"].duplicated().sum()

print(f"Duplicate eligible PERMNO rows: {duplicate_universe_permnos:,}")

if duplicate_universe_permnos > 0:
    raise ValueError(
        "Eligible universe contains duplicate PERMNO rows."
    )

eligible_permnos = set(
    universe["permno"].dropna().astype(int)
)

print(f"Eligible PERMNOs: {len(eligible_permnos):,}")


# =============================================================================
# VALIDATE DAILY COVERAGE
# =============================================================================

print("\n" + "=" * 80)
print("VALIDATING DAILY COVERAGE")
print("=" * 80)

daily_permnos = set(
    daily["permno"].dropna().astype(int)
)

missing_daily_permnos = sorted(
    eligible_permnos - daily_permnos
)

print(
    f"Eligible PERMNOs missing from daily data: "
    f"{len(missing_daily_permnos):,}"
)

if missing_daily_permnos:
    raise ValueError(
        "Eligible securities are missing from daily data: "
        f"{missing_daily_permnos}"
    )

print("PASS   All eligible securities exist in daily data.")


# =============================================================================
# FILTER TO ELIGIBLE PERMNOS
# =============================================================================

print("\n" + "=" * 80)
print("FILTERING DAILY DATA TO ELIGIBLE TIER 1 SECURITIES")
print("=" * 80)

eligible_mask = daily["permno"].isin(eligible_permnos)

tier1_daily = daily.loc[eligible_mask].copy()

print(f"Daily rows before filter: {len(daily):,}")
print(f"Daily rows after filter:  {len(tier1_daily):,}")
print(
    f"Unique PERMNOs retained:  "
    f"{tier1_daily['permno'].nunique():,}"
)


# =============================================================================
# RESTRICT TO RESEARCH WINDOW
# =============================================================================

print("\n" + "=" * 80)
print("RESTRICTING TO RESEARCH WINDOW")
print("=" * 80)

before_window_rows = len(tier1_daily)

window_mask = (
    (tier1_daily["dlycaldt"] >= RESEARCH_START)
    & (tier1_daily["dlycaldt"] <= RESEARCH_END)
)

tier1_daily = tier1_daily.loc[window_mask].copy()

removed_window_rows = before_window_rows - len(tier1_daily)

print(f"Research start:       {RESEARCH_START.date()}")
print(f"Research end:         {RESEARCH_END.date()}")
print(f"Rows removed:         {removed_window_rows:,}")
print(f"Rows retained:        {len(tier1_daily):,}")


# =============================================================================
# VALIDATE FINAL PERMNO COVERAGE
# =============================================================================

print("\n" + "=" * 80)
print("VALIDATING FINAL PERMNO COVERAGE")
print("=" * 80)

final_daily_permnos = set(
    tier1_daily["permno"].dropna().astype(int)
)

missing_after_filter = sorted(
    eligible_permnos - final_daily_permnos
)

unexpected_permnos = sorted(
    final_daily_permnos - eligible_permnos
)

print(
    f"Eligible PERMNOs missing after filtering: "
    f"{len(missing_after_filter):,}"
)

print(
    f"Unexpected PERMNOs in final dataset: "
    f"{len(unexpected_permnos):,}"
)

if missing_after_filter:
    raise ValueError(
        "Some eligible PERMNOs have no observations in the "
        f"final daily dataset: {missing_after_filter}"
    )

if unexpected_permnos:
    raise ValueError(
        "Unexpected PERMNOs found in final daily dataset: "
        f"{unexpected_permnos}"
    )

print("PASS   Final PERMNO coverage validated.")


# =============================================================================
# VALIDATE FINAL DATE RANGE
# =============================================================================

print("\n" + "=" * 80)
print("VALIDATING FINAL DATE RANGE")
print("=" * 80)

final_first_date = tier1_daily["dlycaldt"].min()
final_last_date = tier1_daily["dlycaldt"].max()

print(f"Final first date: {final_first_date.date()}")
print(f"Final last date:  {final_last_date.date()}")

dates_outside_window = (
    (tier1_daily["dlycaldt"] < RESEARCH_START)
    | (tier1_daily["dlycaldt"] > RESEARCH_END)
).sum()

print(f"Observations outside window: {dates_outside_window:,}")

if dates_outside_window > 0:
    raise ValueError(
        "Final Tier 1 daily dataset contains observations "
        "outside the research window."
    )

print("PASS   Final date range validated.")


# =============================================================================
# VALIDATE SECURITY TYPE CONTAMINATION
# =============================================================================

print("\n" + "=" * 80)
print("VALIDATING SECURITY TYPE CONTAMINATION")
print("=" * 80)

security_type_lookup = (
    universe[
        [
            "permno",
            "securitytype",
            "securitysubtype",
            "issuertype",
        ]
    ]
    .drop_duplicates("permno")
)

tier1_daily = tier1_daily.merge(
    security_type_lookup,
    on="permno",
    how="left",
    validate="many_to_one",
    suffixes=("", "_universe")
)

missing_security_type = tier1_daily["securitytype"].isna().sum()

if missing_security_type > 0:
    raise ValueError(
        "Some daily observations could not be matched "
        "to eligible universe security types."
    )

fund_etf_mask = (
    tier1_daily["securitytype"].eq("FUND")
    | tier1_daily["securitysubtype"].eq("ETF")
)

fund_etf_rows = fund_etf_mask.sum()
fund_etf_permnos = (
    tier1_daily.loc[fund_etf_mask, "permno"]
    .dropna()
    .unique()
)

print(f"FUND/ETF daily rows:   {fund_etf_rows:,}")
print(f"FUND/ETF PERMNOs:      {len(fund_etf_permnos):,}")

if fund_etf_rows > 0:
    raise ValueError(
        "FUND/ETF observations detected in final Tier 1 daily dataset: "
        f"{fund_etf_permnos.tolist()}"
    )

print("PASS   No FUND/ETF contamination detected.")


# =============================================================================
# REMOVE TEMPORARY MERGE COLUMNS
# =============================================================================

tier1_daily = tier1_daily.drop(
    columns=[
        "securitytype",
        "securitysubtype",
        "issuertype",
    ]
)


# =============================================================================
# SORT DATA
# =============================================================================

print("\n" + "=" * 80)
print("SORTING FINAL DAILY DATA")
print("=" * 80)

tier1_daily = tier1_daily.sort_values(
    ["permno", "dlycaldt"]
).reset_index(drop=True)

print("PASS   Daily data sorted by PERMNO and date.")


# =============================================================================
# CHECK DUPLICATE PERMNO-DATE OBSERVATIONS
# =============================================================================

print("\n" + "=" * 80)
print("CHECKING DAILY OBSERVATION UNIQUENESS")
print("=" * 80)

duplicate_daily_keys = tier1_daily.duplicated(
    subset=["permno", "dlycaldt"]
).sum()

print(
    f"Duplicate PERMNO-date observations: "
    f"{duplicate_daily_keys:,}"
)

if duplicate_daily_keys > 0:
    raise ValueError(
        "Duplicate PERMNO-date observations detected."
    )

print("PASS   PERMNO-date observations are unique.")


# =============================================================================
# BUILD SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("BUILDING DAILY DATASET SUMMARY")
print("=" * 80)

summary = (
    tier1_daily
    .groupby("permno", as_index=False)
    .agg(
        daily_first_date=("dlycaldt", "min"),
        daily_last_date=("dlycaldt", "max"),
        daily_observations=("dlycaldt", "size"),
        daily_trading_days=("dlycaldt", "nunique"),
        daily_unique_tickers=("ticker", "nunique"),
        daily_unique_permcos=("permco", "nunique"),
    )
)

summary = summary.merge(
    universe[
        [
            "permno",
            "permco",
            "ticker",
            "cusip",
            "securitybegdt",
            "securityenddt",
        ]
    ],
    on="permno",
    how="left",
    validate="one_to_one",
)

summary = summary[
    [
        "permno",
        "permco",
        "ticker",
        "cusip",
        "securitybegdt",
        "securityenddt",
        "daily_first_date",
        "daily_last_date",
        "daily_observations",
        "daily_trading_days",
        "daily_unique_tickers",
        "daily_unique_permcos",
    ]
]

print(f"Summary rows: {len(summary):,}")


# =============================================================================
# FINAL VALIDATION
# =============================================================================

print("\n" + "=" * 80)
print("FINAL VALIDATION")
print("=" * 80)

checks = {
    "row_count_positive": len(tier1_daily) > 0,
    "unique_permnos_match": (
        tier1_daily["permno"].nunique()
        == len(eligible_permnos)
    ),
    "no_duplicate_permno_date": (
        duplicate_daily_keys == 0
    ),
    "no_missing_permno": (
        tier1_daily["permno"].isna().sum() == 0
    ),
    "no_fund_etf": (
        fund_etf_rows == 0
    ),
    "all_within_window": (
        dates_outside_window == 0
    ),
    "all_eligible_present": (
        len(missing_after_filter) == 0
    ),
    "no_unexpected_permnos": (
        len(unexpected_permnos) == 0
    ),
}

for name, passed in checks.items():
    status = "PASS" if passed else "FAIL"
    print(f"{status:<6} {name}")

if not all(checks.values()):
    raise ValueError(
        "Final validation failed."
    )

# =============================================================================
# SAVE OUTPUTS
# =============================================================================

print("\n" + "=" * 80)
print("SAVING OUTPUTS")
print("=" * 80)

tier1_daily.to_csv(
    OUTPUT_DAILY_FILE,
    index=False
)

summary.to_csv(
    OUTPUT_SUMMARY_FILE,
    index=False
)

print(f"Daily dataset:")
print(f"  {OUTPUT_DAILY_FILE}")
print(f"Rows: {len(tier1_daily):,}")
print(f"PERMNOs: {tier1_daily['permno'].nunique():,}")

print(f"\nSummary:")
print(f"  {OUTPUT_SUMMARY_FILE}")
print(f"Rows: {len(summary):,}")