from pathlib import Path
import pandas as pd
import numpy as np


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"
OUTPUT_DIR = DATA_DIR / "tier2_historical_universe"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NAMES_FILE = DATA_DIR / "crsp_names_clean.csv"

OUTPUT_FILE = OUTPUT_DIR / "crsp_tier2_historical_security_master.csv"
SUMMARY_FILE = OUTPUT_DIR / "crsp_tier2_historical_security_master_summary.csv"
VALIDATION_FILE = OUTPUT_DIR / "crsp_tier2_historical_security_master_validation.csv"


# =============================================================================
# RESEARCH WINDOW
# =============================================================================

RESEARCH_START = pd.Timestamp("1993-01-01")
RESEARCH_END = pd.Timestamp("2018-12-31")


# =============================================================================
# LOAD
# =============================================================================

print("=" * 80)
print("LOADING CRSP NAMES")
print("=" * 80)

df = pd.read_csv(NAMES_FILE, low_memory=False)

print(f"Rows loaded: {len(df):,}")
print(f"Unique PERMNOs: {df['permno'].nunique():,}")


# =============================================================================
# DATE CONVERSION
# =============================================================================

date_columns = [
    "secinfostartdt",
    "secinfoenddt",
    "securitybegdt",
    "securityenddt",
]

for col in date_columns:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")


# =============================================================================
# BASIC STRUCTURAL VALIDATION
# =============================================================================

required_columns = [
    "permno",
    "permco",
    "ticker",
    "issuernm",
    "securitytype",
    "securitysubtype",
    "sharetype",
    "issuertype",
    "usincflg",
    "primaryexch",
    "tradingstatusflg",
    "siccd",
    "secinfostartdt",
    "secinfoenddt",
    "securitybegdt",
    "securityenddt",
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required CRSP Names columns: {missing_columns}"
    )


# =============================================================================
# VALIDITY INTERVAL CHECK
# =============================================================================

df["names_interval_valid"] = (
    df["secinfostartdt"].notna()
    & df["secinfoenddt"].notna()
    & (df["secinfostartdt"] <= df["secinfoenddt"])
)

print("\nNAMES INTERVAL VALIDITY")
print(
    df["names_interval_valid"]
    .value_counts(dropna=False)
)


# =============================================================================
# RESEARCH-WINDOW OVERLAP
# =============================================================================

# A NAMES interval overlaps the research window when:
#
# interval_start <= research_end
# AND
# interval_end >= research_start

df["research_window_overlap"] = (
    df["secinfostartdt"].notna()
    & df["secinfoenddt"].notna()
    & (df["secinfostartdt"] <= RESEARCH_END)
    & (df["secinfoenddt"] >= RESEARCH_START)
)

df = df[df["research_window_overlap"]].copy()


# =============================================================================
# CLIP INTERVAL TO RESEARCH WINDOW
# =============================================================================

df["research_start"] = df["secinfostartdt"].clip(
    lower=RESEARCH_START
)

df["research_end"] = df["secinfoenddt"].clip(
    upper=RESEARCH_END
)


# =============================================================================
# SECURITY EXISTENCE INTERVAL
# =============================================================================

df["security_interval_valid"] = (
    df["securitybegdt"].notna()
    & df["securityenddt"].notna()
    & (df["securitybegdt"] <= df["securityenddt"])
)

df["security_overlaps_research"] = (
    df["securitybegdt"].notna()
    & df["securityenddt"].notna()
    & (df["securitybegdt"] <= RESEARCH_END)
    & (df["securityenddt"] >= RESEARCH_START)
)


# =============================================================================
# CLIPPED SECURITY EXISTENCE
# =============================================================================

df["security_research_start"] = df["securitybegdt"].clip(
    lower=RESEARCH_START
)

df["security_research_end"] = df["securityenddt"].clip(
    upper=RESEARCH_END
)


# =============================================================================
# EFFECTIVE HISTORICAL INTERVAL
# =============================================================================

df["effective_start"] = df[
    ["research_start", "security_research_start"]
].max(axis=1)

df["effective_end"] = df[
    ["research_end", "security_research_end"]
].min(axis=1)

df["effective_interval_valid"] = (
    df["effective_start"].notna()
    & df["effective_end"].notna()
    & (df["effective_start"] <= df["effective_end"])
)


# =============================================================================
# HISTORICAL EXISTENCE FLAG
# =============================================================================

df["historically_exists"] = (
    df["research_window_overlap"]
    & df["security_overlaps_research"]
    & df["effective_interval_valid"]
)


# =============================================================================
# CLASSIFICATION FLAGS
# =============================================================================

df["is_fund"] = (
    df["securitytype"].astype("string").str.upper() == "FUND"
)

df["is_etf"] = (
    df["securitysubtype"].astype("string").str.upper() == "ETF"
)

df["is_equity"] = (
    df["securitytype"].astype("string").str.upper() == "EQTY"
)

df["is_common"] = (
    df["securitysubtype"].astype("string").str.upper() == "COM"
)

df["is_adr"] = (
    df["sharetype"].astype("string").str.upper() == "AD"
)

df["is_non_us"] = (
    df["usincflg"].astype("string").str.upper() == "N"
)


# =============================================================================
# INITIAL RESEARCH CLASSIFICATION
# =============================================================================

def classify_security(row):

    if not row["historically_exists"]:
        return "OUTSIDE_RESEARCH_WINDOW"

    if row["is_fund"] or row["is_etf"]:
        return "FUND_OR_ETF"

    if row["is_adr"] or row["is_non_us"]:
        return "ADR_OR_NON_US_EQUITY"

    if row["is_equity"] and row["is_common"]:
        return "COMMON_EQUITY"

    return "OTHER_EQUITY"


df["research_classification"] = df.apply(
    classify_security,
    axis=1
)


# =============================================================================
# SORT
# =============================================================================

df = df.sort_values(
    [
        "permno",
        "effective_start",
        "effective_end",
        "secinfostartdt",
    ]
).reset_index(drop=True)


# =============================================================================
# OUTPUT COLUMNS
# =============================================================================

output_columns = [
    "permno",
    "permco",
    "ticker",
    "tradingsymbol",
    "issuernm",

    "securitytype",
    "securitysubtype",
    "sharetype",
    "shareclass",
    "issuertype",
    "usincflg",
    "primaryexch",
    "tradingstatusflg",
    "siccd",

    "secinfostartdt",
    "secinfoenddt",

    "securitybegdt",
    "securityenddt",

    "effective_start",
    "effective_end",

    "historically_exists",
    "is_fund",
    "is_etf",
    "is_equity",
    "is_common",
    "is_adr",
    "is_non_us",

    "research_classification",
]

output_columns = [
    c for c in output_columns
    if c in df.columns
]

master = df[output_columns].copy()


# =============================================================================
# SAVE MASTER
# =============================================================================

master.to_csv(
    OUTPUT_FILE,
    index=False
)


# =============================================================================
# SUMMARY
# =============================================================================

summary = pd.DataFrame({
    "metric": [
        "rows",
        "unique_permnos",
        "unique_permcos",
        "common_equity_permnos",
        "fund_or_etf_permnos",
        "adr_or_non_us_permnos",
        "other_equity_permnos",
        "historically_existing_permnos",
        "research_start",
        "research_end",
    ],
    "value": [
        len(master),
        master["permno"].nunique(),
        master["permco"].nunique(),
        master.loc[
            master["research_classification"] == "COMMON_EQUITY",
            "permno"
        ].nunique(),
        master.loc[
            master["research_classification"] == "FUND_OR_ETF",
            "permno"
        ].nunique(),
        master.loc[
            master["research_classification"] == "ADR_OR_NON_US_EQUITY",
            "permno"
        ].nunique(),
        master.loc[
            master["research_classification"] == "OTHER_EQUITY",
            "permno"
        ].nunique(),
        master.loc[
            master["historically_exists"],
            "permno"
        ].nunique(),
        RESEARCH_START.date(),
        RESEARCH_END.date(),
    ]
})

summary.to_csv(
    SUMMARY_FILE,
    index=False
)


# =============================================================================
# VALIDATION
# =============================================================================

validation = []

def add_check(name, passed, value):
    validation.append({
        "check": name,
        "passed": bool(passed),
        "value": value,
    })


add_check(
    "no_missing_permno",
    master["permno"].notna().all(),
    int(master["permno"].isna().sum())
)

add_check(
    "effective_start_not_after_end",
    (
        master["effective_start"]
        <= master["effective_end"]
    ).all(),
    int(
        (
            master["effective_start"]
            > master["effective_end"]
        ).sum()
    )
)

add_check(
    "historical_dates_within_research_window",
    (
        master["effective_start"].min() >= RESEARCH_START
        and master["effective_end"].max() <= RESEARCH_END
    ),
    True
)

add_check(
    "classification_complete",
    master["research_classification"].notna().all(),
    int(master["research_classification"].isna().sum())
)

validation_df = pd.DataFrame(validation)

validation_df.to_csv(
    VALIDATION_FILE,
    index=False
)


# =============================================================================
# REPORT
# =============================================================================

print("\n" + "=" * 80)
print("HISTORICAL SECURITY MASTER")
print("=" * 80)

print(f"Rows:                    {len(master):,}")
print(f"Unique PERMNOs:          {master['permno'].nunique():,}")
print(f"Unique PERMCOs:          {master['permco'].nunique():,}")

print("\nClassification:")
print(
    master.groupby(
        "research_classification"
    )["permno"]
    .nunique()
    .sort_values(ascending=False)
)

print("\nSpecial securities:")
print(
    master.loc[
        master["research_classification"] != "COMMON_EQUITY",
        [
            "permno",
            "ticker",
            "issuernm",
            "securitytype",
            "securitysubtype",
            "sharetype",
            "usincflg",
            "research_classification",
            "effective_start",
            "effective_end",
        ]
    ].drop_duplicates()
    .to_string(index=False)
)

print("\nVALIDATION")
print(validation_df.to_string(index=False))

print(f"\nSaved: {OUTPUT_FILE}")
print(f"Saved: {SUMMARY_FILE}")
print(f"Saved: {VALIDATION_FILE}")