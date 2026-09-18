from pathlib import Path
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

NAMES_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "crsp"
    / "crsp_names_clean.csv"
)

DAILY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "crsp"
    / "crsp_daily_clean.csv"
)

RECON_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "crsp"
    / "crsp_tier1_daily_reconciliation.csv"
)

DISCREPANCY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "crsp"
    / "crsp_tier1_discrepancy_investigation.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "crsp"
)

OUTPUT_UNIVERSE = OUTPUT_DIR / "crsp_tier1_historical_universe.csv"
OUTPUT_SUMMARY = OUTPUT_DIR / "crsp_tier1_universe_summary.csv"
OUTPUT_EXCLUSIONS = OUTPUT_DIR / "crsp_tier1_universe_exclusions.csv"


# =============================================================================
# CONFIGURATION
# =============================================================================

START_DATE = pd.Timestamp("1993-01-04")
END_DATE = pd.Timestamp("2018-12-31")


# =============================================================================
# HELPERS
# =============================================================================
def normalize_columns(df):
    """
    Normalize column names to the project's canonical naming convention.

    CRSP Names may contain lowercase CRSP field names, while downstream
    Phase 3 scripts use canonical names such as PERMNO, PERMCO, Ticker, etc.
    """

    df = df.copy()

    df.columns = [
        str(c).strip()
        for c in df.columns
    ]

    rename_map = {
        # CRSP Names
        "permno": "PERMNO",
        "permco": "PERMCO",
        "ticker": "Ticker",
        "cusip": "CUSIP",

        "issuernm": "IssuerNm",
        "shareclass": "ShareClass",
        "usincflg": "USIncFlg",
        "issuertype": "IssuerType",
        "securitytype": "SecurityType",
        "securitysubtype": "SecuritySubType",
        "sharetype": "ShareType",
        "siccd": "SICCD",
        "primaryexch": "PrimaryExch",
        "tradingstatusflg": "TradingStatusFlg",
        "tradingsymbol": "TradingSymbol",
        "naics": "NAICS",

        "secinfostartdt": "SecInfoStartDt",
        "secinfoenddt": "SecInfoEndDt",
        "securitybegdt": "SecurityBegDt",
        "securityenddt": "SecurityEndDt",

        # Daily CRSP
        "dlycaldt": "DlyCalDt",
        "yyyymmdd": "YYYYMMDD",
    }

    df = df.rename(
        columns=rename_map
    )

    return df


def normalize_permno(df, column="PERMNO"):
    df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def parse_date_column(df, column):
    if column in df.columns:
        df[column] = pd.to_datetime(
            df[column],
            errors="coerce"
        )
    return df


# =============================================================================
# LOAD DATA
# =============================================================================

print("=" * 80)
print("LOADING VALIDATED CRSP DATA")
print("=" * 80)

names = pd.read_csv(NAMES_FILE, low_memory=False)
daily = pd.read_csv(DAILY_FILE, low_memory=False)
recon = pd.read_csv(RECON_FILE, low_memory=False)
discrepancies = pd.read_csv(DISCREPANCY_FILE, low_memory=False)

names = normalize_columns(names)
daily = normalize_columns(daily)
recon = normalize_columns(recon)
discrepancies = normalize_columns(discrepancies)

print(f"Names rows:          {len(names):,}")
print(f"Daily rows:          {len(daily):,}")
print(f"Reconciliation rows: {len(recon):,}")
print(f"Discrepancy rows:    {len(discrepancies):,}")


# =============================================================================
# NORMALIZE IDENTIFIERS
# =============================================================================

print()
print("=" * 80)
print("NORMALIZING IDENTIFIERS")
print("=" * 80)

for df in [names, daily, recon, discrepancies]:

    if "PERMNO" in df.columns:
        df["PERMNO"] = pd.to_numeric(
            df["PERMNO"],
            errors="coerce"
        ).astype("Int64")


# =============================================================================
# VALIDATE DAILY DATE FIELD
# =============================================================================
print()
print("=" * 80)
print("VALIDATING DAILY DATE RANGE")
print("=" * 80)


daily["DlyCalDt"] = pd.to_datetime(
    daily["DlyCalDt"].astype("string").str.strip(),
    format="%Y-%m-%d",
    errors="coerce",
)

invalid_dates = int(
    daily["DlyCalDt"].isna().sum()
)

print(
    f"Invalid DlyCalDt values: "
    f"{invalid_dates:,}"
)

if invalid_dates > 0:

    print()
    print("Examples of invalid DlyCalDt values:")

    print(
        daily.loc[
            daily["DlyCalDt"].isna(),
            ["PERMNO"],
        ]
        .head(20)
        .to_string(index=False)
    )

    raise ValueError(
        f"Daily file contains "
        f"{invalid_dates:,} invalid DlyCalDt values."
    )

# -------------------------------------------------------------------------
# Validate observed daily date range.
# -------------------------------------------------------------------------

daily_first_date = daily["DlyCalDt"].min()
daily_last_date = daily["DlyCalDt"].max()

print(
    f"Daily date range: "
    f"{daily_first_date.date()} "
    f"to "
    f"{daily_last_date.date()}"
)

if daily_first_date != START_DATE:
    raise ValueError(
        f"Unexpected daily start date: "
        f"{daily_first_date.date()} "
        f"(expected {START_DATE.date()})."
    )

if daily_last_date != END_DATE:
    raise ValueError(
        f"Unexpected daily end date: "
        f"{daily_last_date.date()} "
        f"(expected {END_DATE.date()})."
    )

print("PASS   Daily date range validated.")


# =============================================================================
# BUILD DAILY SECURITY HISTORY
# =============================================================================

print()
print("=" * 80)
print("BUILDING DAILY SECURITY HISTORY")
print("=" * 80)

daily_history = (
    daily
    .groupby("PERMNO", dropna=False)
    .agg(
        daily_first_date=("DlyCalDt", "min"),
        daily_last_date=("DlyCalDt", "max"),
        daily_observations=("DlyCalDt", "size"),
        daily_trading_days=("DlyCalDt", "nunique"),
        daily_unique_tickers=("Ticker", "nunique"),
        daily_unique_permcos=("PERMCO", "nunique"),
    )
    .reset_index()
)

print(
    f"Unique daily PERMNOs: "
    f"{daily_history['PERMNO'].nunique()}"
)


# =============================================================================
# BUILD NAMES SECURITY HISTORY
# =============================================================================

print()
print("=" * 80)
print("BUILDING NAMES SECURITY HISTORY")
print("=" * 80)

# =============================================================================
# BUILD NAMES SECURITY HISTORY
# =============================================================================

print()
print("=" * 80)
print("BUILDING NAMES SECURITY HISTORY")
print("=" * 80)

required_names_history_columns = [
    "PERMNO",
    "SecurityBegDt",
    "SecurityEndDt",
    "Ticker",
    "PERMCO",
]

missing_names_history_columns = [
    column
    for column in required_names_history_columns
    if column not in names.columns
]

if missing_names_history_columns:
    raise ValueError(
        "CRSP Names file is missing required canonical columns: "
        + ", ".join(missing_names_history_columns)
    )

names["SecurityBegDt"] = pd.to_datetime(
    names["SecurityBegDt"],
    errors="coerce",
)

names["SecurityEndDt"] = pd.to_datetime(
    names["SecurityEndDt"],
    errors="coerce",
)

names_history = (
    names
    .groupby(
        "PERMNO",
        dropna=False,
    )
    .agg(
        names_first_date=(
            "SecurityBegDt",
            "min",
        ),
        names_last_date=(
            "SecurityEndDt",
            "max",
        ),
        names_records=(
            "PERMNO",
            "size",
        ),
        names_unique_tickers=(
            "Ticker",
            "nunique",
        ),
        names_unique_permcos=(
            "PERMCO",
            "nunique",
        ),
    )
    .reset_index()
)

print(
    f"Unique Names PERMNOs: "
    f"{names_history['PERMNO'].nunique():,}"
)

names_history = (
    names
    .groupby("PERMNO", dropna=False)
    .agg(
        names_first_date=("SecurityBegDt", "min"),
        names_last_date=("SecurityEndDt", "max"),
        names_records=("PERMNO", "size"),
        names_unique_tickers=("Ticker", "nunique"),
        names_unique_permcos=("PERMCO", "nunique"),
    )
    .reset_index()
)

print(
    f"Unique Names PERMNOs: "
    f"{names_history['PERMNO'].nunique()}"
)


# =============================================================================
# CREATE PERMNO MASTER
# =============================================================================

print()
print("=" * 80)
print("CREATING PERMNO MASTER")
print("=" * 80)

name_permnos = set(
    names["PERMNO"]
    .dropna()
    .astype(int)
)

daily_permnos = set(
    daily["PERMNO"]
    .dropna()
    .astype(int)
)

all_permnos = sorted(
    name_permnos.union(daily_permnos)
)

master = pd.DataFrame({
    "PERMNO": all_permnos
})

print(f"Total PERMNOs: {len(master)}")


# =============================================================================
# ATTACH NAMES INFORMATION
# =============================================================================

print()
print("=" * 80)
print("ATTACHING CRSP NAMES INFORMATION")
print("=" * 80)

# One representative Names row per PERMNO.
#
# This is intentionally NOT treated as a complete historical
# time-varying security master yet. It is only the current
# source record available in the supplied Names file.

names_representative = (
    names
    .sort_values(
        ["PERMNO", "SecurityBegDt", "SecurityEndDt"]
    )
    .groupby("PERMNO", as_index=False)
    .first()
)

names_columns = [
    "PERMNO",
    "PERMCO",
    "Ticker",
    "CUSIP",
    "IssuerNm",
    "ShareClass",
    "USIncFlg",
    "IssuerType",
    "SecurityType",
    "SecuritySubType",
    "ShareType",
    "SICCD",
    "PrimaryExch",
    "TradingStatusFlg",
    "TradingSymbol",
    "NAICS",
    "SecurityBegDt",
    "SecurityEndDt",
]

names_columns = [
    column
    for column in names_columns
    if column in names_representative.columns
]

names_representative = names_representative[
    names_columns
]

master = master.merge(
    names_representative,
    on="PERMNO",
    how="left"
)


# =============================================================================
# ATTACH DAILY HISTORY
# =============================================================================

print()
print("=" * 80)
print("ATTACHING DAILY HISTORY")
print("=" * 80)

master = master.merge(
    daily_history,
    on="PERMNO",
    how="left"
)


# =============================================================================
# CLASSIFY SOURCE PRESENCE
# =============================================================================

print()
print("=" * 80)
print("CLASSIFYING SOURCE PRESENCE")
print("=" * 80)

master["in_names_file"] = master["PERMNO"].isin(
    name_permnos
)

master["in_daily_file"] = master["PERMNO"].isin(
    daily_permnos
)

master["has_daily_history"] = (
    master["daily_observations"].fillna(0) > 0
)


def classify_source(row):

    if row["in_names_file"] and row["in_daily_file"]:
        return "NAMES_AND_DAILY"

    if row["in_names_file"] and not row["in_daily_file"]:
        return "NAMES_ONLY"

    if not row["in_names_file"] and row["in_daily_file"]:
        return "DAILY_ONLY"

    return "UNKNOWN"


master["source_class"] = master.apply(
    classify_source,
    axis=1
)


# =============================================================================
# HISTORICAL DATE OVERLAP
# =============================================================================

print()
print("=" * 80)
print("CALCULATING HISTORICAL DATE OVERLAP")
print("=" * 80)

master["overlap_start"] = master[
    ["SecurityBegDt", "daily_first_date"]
].max(axis=1)

master["overlap_end"] = master[
    ["SecurityEndDt", "daily_last_date"]
].min(axis=1)

master["date_range_overlap"] = (
    master["overlap_start"].notna()
    &
    master["overlap_end"].notna()
    &
    (
        master["overlap_start"]
        <=
        master["overlap_end"]
    )
)


# =============================================================================
# INITIAL TIER 1 ELIGIBILITY
# =============================================================================

print()
print("=" * 80)
print("CONSTRUCTING INITIAL HISTORICAL ELIGIBILITY")
print("=" * 80)

master["eligible_initial"] = (
    master["in_names_file"]
    &
    master["has_daily_history"]
)


master["exclusion_reason"] = ""

master.loc[
    master["source_class"] == "DAILY_ONLY",
    "exclusion_reason"
] = "DAILY_ONLY_NO_NAMES_RECORD"

master.loc[
    master["source_class"] == "NAMES_ONLY",
    "exclusion_reason"
] = "NAMES_ONLY_NO_DAILY_HISTORY"


# =============================================================================
# CREATE HISTORICAL UNIVERSE
# =============================================================================

print()
print("=" * 80)
print("BUILDING HISTORICAL TIER 1 UNIVERSE")
print("=" * 80)

universe = master[
    master["eligible_initial"]
].copy()

universe = universe.sort_values(
    "PERMNO"
).reset_index(drop=True)

print(
    f"Initial historical universe: "
    f"{len(universe)} securities"
)

print(
    f"Unique PERMCOs: "
    f"{universe['PERMCO'].nunique()}"
)

print(
    f"Unique tickers: "
    f"{universe['Ticker'].nunique()}"
)


# =============================================================================
# FINAL UNIVERSE VALIDATION
# =============================================================================

print()
print("=" * 80)
print("VALIDATING HISTORICAL TIER 1 UNIVERSE")
print("=" * 80)

duplicate_permnos = (
    universe["PERMNO"]
    .duplicated()
    .sum()
)

missing_permno = universe["PERMNO"].isna().sum()

missing_daily_history = (
    universe["daily_observations"]
    .isna()
    .sum()
)

print(f"Duplicate PERMNOs:       {duplicate_permnos}")
print(f"Missing PERMNOs:         {missing_permno}")
print(f"Missing daily history:   {missing_daily_history}")

if duplicate_permnos != 0:
    raise ValueError(
        "Historical universe contains duplicate PERMNOs."
    )

if missing_permno != 0:
    raise ValueError(
        "Historical universe contains missing PERMNO."
    )

if missing_daily_history != 0:
    raise ValueError(
        "Historical universe contains securities without daily history."
    )

print("PASS   Historical universe validation passed.")


# =============================================================================
# BUILD EXCLUSION FILE
# =============================================================================

print()
print("=" * 80)
print("BUILDING EXCLUSION FILE")
print("=" * 80)

exclusions = master[
    ~master["eligible_initial"]
].copy()

exclusions = exclusions[
    [
        "PERMNO",
        "PERMCO",
        "Ticker",
        "IssuerNm",
        "source_class",
        "in_names_file",
        "in_daily_file",
        "has_daily_history",
        "daily_first_date",
        "daily_last_date",
        "daily_observations",
        "SecurityBegDt",
        "SecurityEndDt",
        "date_range_overlap",
        "exclusion_reason",
    ]
].sort_values("PERMNO")


# =============================================================================
# BUILD SUMMARY
# =============================================================================

print()
print("=" * 80)
print("BUILDING UNIVERSE SUMMARY")
print("=" * 80)

summary_rows = [
    {
        "metric": "names_unique_permnos",
        "value": len(name_permnos),
    },
    {
        "metric": "daily_unique_permnos",
        "value": len(daily_permnos),
    },
    {
        "metric": "total_reconciled_permnos",
        "value": len(all_permnos),
    },
    {
        "metric": "historical_universe_permnos",
        "value": len(universe),
    },
    {
        "metric": "names_only_permnos",
        "value": (
            master["source_class"]
            .eq("NAMES_ONLY")
            .sum()
        ),
    },
    {
        "metric": "daily_only_permnos",
        "value": (
            master["source_class"]
            .eq("DAILY_ONLY")
            .sum()
        ),
    },
    {
        "metric": "names_and_daily_permnos",
        "value": (
            master["source_class"]
            .eq("NAMES_AND_DAILY")
            .sum()
        ),
    },
    {
        "metric": "universe_unique_permcos",
        "value": universe["PERMCO"].nunique(),
    },
    {
        "metric": "universe_unique_tickers",
        "value": universe["Ticker"].nunique(),
    },
]

summary = pd.DataFrame(summary_rows)


# =============================================================================
# WRITE OUTPUTS
# =============================================================================

print()
print("=" * 80)
print("WRITING OUTPUTS")
print("=" * 80)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

universe.to_csv(
    OUTPUT_UNIVERSE,
    index=False
)

summary.to_csv(
    OUTPUT_SUMMARY,
    index=False
)

exclusions.to_csv(
    OUTPUT_EXCLUSIONS,
    index=False
)

print(f"Historical universe:")
print(f"  {OUTPUT_UNIVERSE}")

print(f"Summary:")
print(f"  {OUTPUT_SUMMARY}")

print(f"Exclusions:")
print(f"  {OUTPUT_EXCLUSIONS}")


# =============================================================================
# FINAL SUMMARY
# =============================================================================

print()
print("=" * 80)
print("INITIAL HISTORICAL UNIVERSE BUILD COMPLETE")
print("=" * 80)

print(
    f"Names PERMNOs:             {len(name_permnos)}"
)

print(
    f"Daily PERMNOs:             {len(daily_permnos)}"
)

print(
    f"Reconciled PERMNOs:        {len(all_permnos)}"
)

print(
    f"Historical universe:       {len(universe)}"
)

print(
    f"NAMES_ONLY exclusions:     "
    f"{master['source_class'].eq('NAMES_ONLY').sum()}"
)

print(
    f"DAILY_ONLY exclusions:     "
    f"{master['source_class'].eq('DAILY_ONLY').sum()}"
)