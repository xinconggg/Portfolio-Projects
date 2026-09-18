from pathlib import Path
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"

NAMES_FILE = DATA_DIR / "crsp_names_clean.csv"

OUTPUT_DIR = DATA_DIR / "tier2_classification_profiles"
OUTPUT_FILE = OUTPUT_DIR / "crsp_tier2_classification_exception_history.csv"


# =============================================================================
# CONFIGURATION
# =============================================================================

EXCEPTION_PERMNOS = [
    76947,
    84398,
    86755,
    88222,
    88614,
]


# =============================================================================
# LOAD DATA
# =============================================================================

print("=" * 80)
print("LOADING CRSP NAMES")
print("=" * 80)

df = pd.read_csv(NAMES_FILE, low_memory=False)

df.columns = df.columns.str.lower()

print(f"Rows loaded: {len(df):,}")
print(f"Columns loaded: {len(df.columns):,}")


# =============================================================================
# NORMALIZE DATES
# =============================================================================

DATE_COLUMNS = [
    "secinfostartdt",
    "secinfoenddt",
    "securitybegdt",
    "securityenddt",
]

for col in DATE_COLUMNS:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")


# =============================================================================
# VALIDATE REQUIRED COLUMNS
# =============================================================================

REQUIRED_COLUMNS = [
    "permno",
    "permco",
    "ticker",
    "issuernm",
    "shareclass",
    "usincflg",
    "issuertype",
    "securitytype",
    "securitysubtype",
    "sharetype",
    "primaryexch",
    "tradingstatusflg",
    "siccd",
    "tradingsymbol",
    "securitybegdt",
    "securityenddt",
    "secinfostartdt",
    "secinfoenddt",
]

missing_columns = [
    col for col in REQUIRED_COLUMNS
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )


# =============================================================================
# FILTER EXCEPTION SECURITIES
# =============================================================================

exceptions = (
    df[df["permno"].isin(EXCEPTION_PERMNOS)]
    .copy()
    .sort_values(
        ["permno", "secinfostartdt", "secinfoenddt"]
    )
)


# =============================================================================
# DISPLAY HISTORICAL CLASSIFICATION
# =============================================================================

print("=" * 80)
print("TIER 2 CLASSIFICATION EXCEPTION HISTORY")
print("=" * 80)

display_columns = [
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
]

print(
    exceptions[display_columns]
    .to_string(index=False)
)


# =============================================================================
# PERMNO-LEVEL SUMMARY
# =============================================================================

print("=" * 80)
print("EXCEPTION SECURITY SUMMARY")
print("=" * 80)

summary_rows = []

for permno, group in exceptions.groupby("permno"):

    row = {
        "permno": permno,
        "permco": group["permco"].dropna().iloc[0]
        if group["permco"].notna().any()
        else pd.NA,
        "ticker_values": "|".join(
            sorted(group["ticker"].dropna().astype(str).unique())
        ),
        "securitytype_values": "|".join(
            sorted(group["securitytype"].dropna().astype(str).unique())
        ),
        "securitysubtype_values": "|".join(
            sorted(group["securitysubtype"].dropna().astype(str).unique())
        ),
        "sharetype_values": "|".join(
            sorted(group["sharetype"].dropna().astype(str).unique())
        ),
        "issuertype_values": "|".join(
            sorted(group["issuertype"].dropna().astype(str).unique())
        ),
        "usincflg_values": "|".join(
            sorted(group["usincflg"].dropna().astype(str).unique())
        ),
        "primaryexch_values": "|".join(
            sorted(group["primaryexch"].dropna().astype(str).unique())
        ),
        "names_records": len(group),
        "security_start_min": group["securitybegdt"].min(),
        "security_end_max": group["securityenddt"].max(),
        "secinfo_start_min": group["secinfostartdt"].min(),
        "secinfo_end_max": group["secinfoenddt"].max(),
    }

    summary_rows.append(row)

summary = pd.DataFrame(summary_rows)


# =============================================================================
# SAVE
# =============================================================================

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

summary.to_csv(
    OUTPUT_FILE,
    index=False
)

print("=" * 80)
print("SAVED")
print("=" * 80)

print(f"Output: {OUTPUT_FILE}")
print(f"Exception securities: {len(summary):,}")