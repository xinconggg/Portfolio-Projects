from pathlib import Path
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"


INPUT_UNIVERSE = DATA_DIR / "crsp_tier1_historical_universe.csv"

OUTPUT_UNIVERSE = DATA_DIR / "crsp_tier1_eligible_universe.csv"
OUTPUT_EXCLUSIONS = DATA_DIR / "crsp_tier1_eligible_universe_exclusions.csv"
OUTPUT_SUMMARY = DATA_DIR / "crsp_tier1_eligible_universe_summary.csv"


# =============================================================================
# RESEARCH WINDOW
# =============================================================================

RESEARCH_START = pd.Timestamp("1993-01-01")
RESEARCH_END = pd.Timestamp("2018-12-31")


# =============================================================================
# REQUIRED COLUMNS
# =============================================================================

REQUIRED_COLUMNS = [
    "permno",
    "permco",
    "ticker",
    "cusip",
    "issuernm",
    "securitytype",
    "securitysubtype",
    "sharetype",
    "usincflg",
    "issuertype",
    "securitybegdt",
    "securityenddt",
    "daily_first_date",
    "daily_last_date",
    "daily_observations",
    "daily_trading_days",
    "has_daily_history",
    "eligible_initial",
]


# =============================================================================
# HELPERS
# =============================================================================

def normalize_columns(df):
    """
    Standardize all column names to lowercase.

    Examples:
        PERMNO       -> permno
        PERMCO       -> permco
        Ticker       -> ticker
        SecurityType -> securitytype
    """

    df = df.copy()

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
    )

    return df


def normalize_identifiers(df):
    """
    Normalize identifier columns after column names
    have been standardized to lowercase.
    """

    df = df.copy()

    if "permno" in df.columns:
        df["permno"] = pd.to_numeric(
            df["permno"],
            errors="coerce"
        )

    if "permco" in df.columns:
        df["permco"] = pd.to_numeric(
            df["permco"],
            errors="coerce"
        )

    string_columns = [
        "ticker",
        "cusip",
        "issuernm",
        "securitytype",
        "securitysubtype",
        "sharetype",
        "usincflg",
        "issuertype",
    ]

    for col in string_columns:

        if col in df.columns:

            df[col] = (
                df[col]
                .astype("string")
                .str.strip()
                .str.upper()
            )

    return df


def prepare_dates(df):
    """
    Convert all relevant date columns to pandas datetime.
    """

    df = df.copy()

    date_columns = [
        "securitybegdt",
        "securityenddt",
        "daily_first_date",
        "daily_last_date",
    ]

    for col in date_columns:

        if col in df.columns:

            df[col] = pd.to_datetime(
                df[col],
                errors="coerce"
            )

    return df


def build_exclusion_reason(row):

    reasons = []

    if row["exclude_fund_etf"]:
        reasons.append("FUND_OR_ETF")

    if row["exclude_no_daily_history"]:
        reasons.append("NO_DAILY_HISTORY")

    if row["exclude_outside_research_window"]:
        reasons.append("OUTSIDE_RESEARCH_WINDOW")

    if not reasons:
        return ""

    return ";".join(reasons)


# =============================================================================
# LOAD DATA
# =============================================================================

print("=" * 80)
print("LOADING HISTORICAL TIER 1 UNIVERSE")
print("=" * 80)

df = pd.read_csv(
    INPUT_UNIVERSE,
    low_memory=False
)

print(f"Rows loaded:        {len(df):,}")


# =============================================================================
# NORMALIZE COLUMN NAMES
# =============================================================================

print("\n" + "=" * 80)
print("NORMALIZING COLUMN NAMES")
print("=" * 80)

df = normalize_columns(df)

print("PASS   All column names standardized to lowercase.")


# =============================================================================
# SHOW COLUMN STRUCTURE
# =============================================================================

print("\n" + "=" * 80)
print("VALIDATING COLUMN STRUCTURE")
print("=" * 80)

print("Columns loaded:")

for col in df.columns:
    print(f"  {col}")


# =============================================================================
# CHECK REQUIRED COLUMNS
# =============================================================================

print("\n" + "=" * 80)
print("CHECKING REQUIRED COLUMNS")
print("=" * 80)

missing_columns = [
    col
    for col in REQUIRED_COLUMNS
    if col not in df.columns
]

if missing_columns:

    print("FAIL   Missing required columns:")

    for col in missing_columns:
        print(f"  {col}")

    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )

print("PASS   All required columns present.")


# =============================================================================
# NORMALIZE IDENTIFIERS
# =============================================================================

print("\n" + "=" * 80)
print("NORMALIZING IDENTIFIERS")
print("=" * 80)

df = normalize_identifiers(df)

print("PASS   Identifier columns normalized.")

print(
    f"Unique PERMNOs:     "
    f"{df['permno'].nunique():,}"
)


# =============================================================================
# PREPARE DATE COLUMNS
# =============================================================================

print("\n" + "=" * 80)
print("PREPARING DATE COLUMNS")
print("=" * 80)

df = prepare_dates(df)

for col in [
    "securitybegdt",
    "securityenddt",
    "daily_first_date",
    "daily_last_date",
]:
    print(f"Parsed: {col}")


# =============================================================================
# BASIC STRUCTURAL VALIDATION
# =============================================================================

print("\n" + "=" * 80)
print("BASIC STRUCTURAL VALIDATION")
print("=" * 80)

duplicate_permnos = df["permno"].duplicated().sum()
missing_permno = df["permno"].isna().sum()

print(
    f"Duplicate PERMNO rows: {duplicate_permnos:,}"
)

print(
    f"Missing PERMNO values: {missing_permno:,}"
)

if duplicate_permnos > 0:

    raise ValueError(
        "Historical universe contains duplicate PERMNO rows."
    )

if missing_permno > 0:

    raise ValueError(
        "Historical universe contains missing PERMNO values."
    )

print("PASS   Structural validation passed.")


# =============================================================================
# IDENTIFY SECURITY TYPES
# =============================================================================

print("\n" + "=" * 80)
print("IDENTIFYING SECURITY TYPES")
print("=" * 80)

print("\nSecurity type:")
print(
    df["securitytype"]
    .value_counts(dropna=False)
    .to_string()
)

print("\nSecurity subtype:")
print(
    df["securitysubtype"]
    .value_counts(dropna=False)
    .to_string()
)

print("\nIssuer type:")
print(
    df["issuertype"]
    .value_counts(dropna=False)
    .to_string()
)


# =============================================================================
# CONSTRUCT ELIGIBILITY FLAGS
# =============================================================================

print("\n" + "=" * 80)
print("CONSTRUCTING ELIGIBILITY FLAGS")
print("=" * 80)


# -----------------------------------------------------------------------------
# FUND / ETF EXCLUSION
# -----------------------------------------------------------------------------

df["exclude_fund_etf"] = (
    (df["securitytype"] == "FUND")
    | (df["securitysubtype"] == "ETF")
)


# -----------------------------------------------------------------------------
# DAILY HISTORY EXCLUSION
# -----------------------------------------------------------------------------

df["exclude_no_daily_history"] = (
    ~df["has_daily_history"]
    .fillna(False)
    .astype(bool)
)


# -----------------------------------------------------------------------------
# RESEARCH WINDOW EXCLUSION
# -----------------------------------------------------------------------------

df["exclude_outside_research_window"] = (
    (df["daily_first_date"] > RESEARCH_END)
    | (df["daily_last_date"] < RESEARCH_START)
)


# -----------------------------------------------------------------------------
# ELIGIBILITY COMPONENTS
# -----------------------------------------------------------------------------

df["eligible_security_type"] = (
    ~df["exclude_fund_etf"]
)

df["eligible_daily_history"] = (
    ~df["exclude_no_daily_history"]
)

df["eligible_research_window"] = (
    ~df["exclude_outside_research_window"]
)


# =============================================================================
# DETERMINE FINAL ELIGIBILITY
# =============================================================================

df["eligible_tier1"] = (
    df["eligible_security_type"]
    & df["eligible_daily_history"]
    & df["eligible_research_window"]
)


# =============================================================================
# BUILD EXCLUSION REASONS
# =============================================================================

df["eligibility_exclusion_reason"] = df.apply(
    build_exclusion_reason,
    axis=1
)


# =============================================================================
# BUILD ELIGIBLE UNIVERSE
# =============================================================================

print("\n" + "=" * 80)
print("BUILDING ELIGIBLE TIER 1 UNIVERSE")
print("=" * 80)

eligible = df[
    df["eligible_tier1"]
].copy()

exclusions = df[
    ~df["eligible_tier1"]
].copy()

print(
    f"Historical universe:      {len(df):,}"
)

print(
    f"Eligible securities:      {len(eligible):,}"
)

print(
    f"Excluded securities:      {len(exclusions):,}"
)


# =============================================================================
# VALIDATE FUND / ETF REMOVAL
# =============================================================================

print("\n" + "=" * 80)
print("VALIDATING FUND / ETF REMOVAL")
print("=" * 80)

remaining_fund_etf = eligible[
    (eligible["securitytype"] == "FUND")
    | (eligible["securitysubtype"] == "ETF")
]

print(
    f"FUND/ETF securities remaining: "
    f"{len(remaining_fund_etf):,}"
)

if len(remaining_fund_etf) > 0:

    print(
        remaining_fund_etf[
            [
                "permno",
                "permco",
                "ticker",
                "securitytype",
                "securitysubtype",
                "issuertype",
            ]
        ].to_string(index=False)
    )

    raise ValueError(
        "FUND/ETF securities remain in the eligible universe."
    )

print("PASS   No FUND/ETF securities remain.")


# =============================================================================
# VALIDATE DAILY HISTORY
# =============================================================================

print("\n" + "=" * 80)
print("VALIDATING DAILY HISTORY")
print("=" * 80)

missing_daily = eligible[
    ~eligible["has_daily_history"]
    .fillna(False)
    .astype(bool)
]

print(
    f"Eligible securities without daily history: "
    f"{len(missing_daily):,}"
)

if len(missing_daily) > 0:

    raise ValueError(
        "Eligible universe contains securities without daily history."
    )

print("PASS   All eligible securities have daily history.")


# =============================================================================
# VALIDATE RESEARCH WINDOW
# =============================================================================

print("\n" + "=" * 80)
print("VALIDATING RESEARCH WINDOW")
print("=" * 80)

invalid_window = eligible[
    (eligible["daily_first_date"] > RESEARCH_END)
    | (eligible["daily_last_date"] < RESEARCH_START)
]

print(
    f"Eligible securities outside research window: "
    f"{len(invalid_window):,}"
)

if len(invalid_window) > 0:

    raise ValueError(
        "Eligible universe contains securities outside "
        "the research window."
    )

print("PASS   All eligible securities overlap research window.")


# =============================================================================
# VALIDATE PERMNO UNIQUENESS
# =============================================================================

print("\n" + "=" * 80)
print("VALIDATING PERMNO UNIQUENESS")
print("=" * 80)

duplicate_eligible_permnos = (
    eligible["permno"]
    .duplicated()
    .sum()
)

print(
    f"Duplicate eligible PERMNO rows: "
    f"{duplicate_eligible_permnos:,}"
)

if duplicate_eligible_permnos > 0:

    raise ValueError(
        "Eligible universe contains duplicate PERMNO rows."
    )

print("PASS   Eligible PERMNOs are unique.")


# =============================================================================
# BUILD CLEAN OUTPUT
# =============================================================================

print("\n" + "=" * 80)
print("PREPARING OUTPUT DATA")
print("=" * 80)

DROP_COLUMNS = [
    "exclude_fund_etf",
    "exclude_no_daily_history",
    "exclude_outside_research_window",
    "eligible_security_type",
    "eligible_daily_history",
    "eligible_research_window",
    "eligible_tier1",
    "eligibility_exclusion_reason",
]

eligible_output = eligible.drop(
    columns=DROP_COLUMNS,
    errors="ignore"
).copy()


# =============================================================================
# BUILD EXCLUSION OUTPUT
# =============================================================================

exclusion_columns = [
    "permno",
    "permco",
    "ticker",
    "cusip",
    "issuernm",
    "securitytype",
    "securitysubtype",
    "issuertype",
    "daily_first_date",
    "daily_last_date",
    "daily_observations",
    "daily_trading_days",
    "has_daily_history",
    "eligibility_exclusion_reason",
]

exclusions_output = exclusions[
    exclusion_columns
].copy()

exclusions_output = exclusions_output.rename(
    columns={
        "eligibility_exclusion_reason": "exclusion_reason"
    }
)


# =============================================================================
# BUILD SUMMARY
# =============================================================================

summary_rows = [
    {
        "metric": "historical_universe_securities",
        "value": len(df),
    },
    {
        "metric": "eligible_tier1_securities",
        "value": len(eligible_output),
    },
    {
        "metric": "excluded_securities",
        "value": len(exclusions_output),
    },
    {
        "metric": "excluded_fund_etf",
        "value": int(df["exclude_fund_etf"].sum()),
    },
    {
        "metric": "excluded_no_daily_history",
        "value": int(df["exclude_no_daily_history"].sum()),
    },
    {
        "metric": "excluded_outside_research_window",
        "value": int(
            df["exclude_outside_research_window"].sum()
        ),
    },
    {
        "metric": "eligible_unique_permnos",
        "value": eligible_output["permno"].nunique(),
    },
    {
        "metric": "eligible_unique_permcos",
        "value": eligible_output["permco"].nunique(),
    },
    {
        "metric": "eligible_unique_tickers",
        "value": eligible_output["ticker"].nunique(),
    },
]

summary = pd.DataFrame(summary_rows)


# =============================================================================
# SAVE OUTPUTS
# =============================================================================

print("\n" + "=" * 80)
print("SAVING OUTPUTS")
print("=" * 80)

eligible_output.to_csv(
    OUTPUT_UNIVERSE,
    index=False
)

exclusions_output.to_csv(
    OUTPUT_EXCLUSIONS,
    index=False
)

summary.to_csv(
    OUTPUT_SUMMARY,
    index=False
)

print(
    "Eligible universe:"
)

print(
    f"  {OUTPUT_UNIVERSE}"
)

print(
    "Exclusions:"
)

print(
    f"  {OUTPUT_EXCLUSIONS}"
)

print(
    "Summary:"
)

print(
    f"  {OUTPUT_SUMMARY}"
)


# =============================================================================
# FINAL SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("ELIGIBILITY FILTER SUMMARY")
print("=" * 80)

print(
    f"Historical universe:       {len(df):,}"
)

print(
    f"Eligible Tier 1 universe:  {len(eligible_output):,}"
)

print(
    f"Excluded securities:       {len(exclusions_output):,}"
)

print(
    f"Excluded FUND/ETF:         "
    f"{int(df['exclude_fund_etf'].sum()):,}"
)

print(
    f"Excluded no daily history: "
    f"{int(df['exclude_no_daily_history'].sum()):,}"
)

print(
    f"Excluded outside window:   "
    f"{int(df['exclude_outside_research_window'].sum()):,}"
)

print(
    f"Unique PERMCOs retained:   "
    f"{eligible_output['permco'].nunique():,}"
)

print(
    f"Unique tickers retained:   "
    f"{eligible_output['ticker'].nunique():,}"
)

print(
    "\nEligibility filtering completed successfully."
)