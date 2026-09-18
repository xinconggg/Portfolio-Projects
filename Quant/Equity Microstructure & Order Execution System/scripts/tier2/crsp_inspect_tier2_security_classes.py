from pathlib import Path
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"

NAMES_FILE = DATA_DIR / "crsp_names_clean.csv"

OUTPUT_FILE = (
    DATA_DIR
    / "tier2_classification_profiles"
    / "crsp_tier2_security_class_inspection.csv"
)


# =============================================================================
# HELPERS
# =============================================================================

def print_header(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


# =============================================================================
# LOAD
# =============================================================================

print_header("LOADING CRSP NAMES")

if not NAMES_FILE.exists():
    raise FileNotFoundError(f"CRSP Names file not found: {NAMES_FILE}")

df = pd.read_csv(NAMES_FILE, low_memory=False)

df.columns = [str(col).strip().lower() for col in df.columns]

print(f"Rows loaded: {len(df):,}")
print(f"Unique PERMNOs: {df['permno'].nunique():,}")


# =============================================================================
# REQUIRED COLUMNS
# =============================================================================

required_columns = [
    "permno",
    "permco",
    "ticker",
    "tradingsymbol",
    "cusip",
    "issuernm",
    "securitytype",
    "securitysubtype",
    "sharetype",
    "issuertype",
    "usincflg",
    "primaryexch",
    "tradingstatusflg",
    "securitybegdt",
    "securityenddt",
    "secinfostartdt",
    "secinfoenddt",
    "siccd",
    "naics",
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        "Required columns missing from CRSP Names: "
        + ", ".join(missing_columns)
    )


# =============================================================================
# SELECT RELEVANT COLUMNS
# =============================================================================

inspection = df[required_columns].copy()


# =============================================================================
# NORMALIZE DATE DISPLAY
# =============================================================================

date_columns = [
    "securitybegdt",
    "securityenddt",
    "secinfostartdt",
    "secinfoenddt",
]

for col in date_columns:
    inspection[col] = inspection[col].astype(str)


# =============================================================================
# PERMNO-LEVEL CLASSIFICATION SUMMARY
# =============================================================================

print_header("BUILDING PERMNO-LEVEL CLASSIFICATION SUMMARY")

# CRSP Names can contain multiple historical records per PERMNO.
# We therefore summarize the historical records rather than blindly
# assuming one row per security.

summary_records = []

for permno, group in inspection.groupby("permno", sort=True):

    record = {
        "permno": permno,
        "permco": group["permco"].iloc[0],
        "ticker_values": "|".join(
            sorted(group["ticker"].dropna().astype(str).unique())
        ),
        "tradingsymbol_values": "|".join(
            sorted(group["tradingsymbol"].dropna().astype(str).unique())
        ),
        "cusip_values": "|".join(
            sorted(group["cusip"].dropna().astype(str).unique())
        ),
        "issuernm_values": "|".join(
            sorted(group["issuernm"].dropna().astype(str).unique())
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
        "tradingstatusflg_values": "|".join(
            sorted(group["tradingstatusflg"].dropna().astype(str).unique())
        ),
        "siccd_values": "|".join(
            sorted(group["siccd"].dropna().astype(str).unique())
        ),
        "naics_values": "|".join(
            sorted(group["naics"].dropna().astype(str).unique())
        ),
        "names_rows": len(group),
        "securitybegdt_min": group["securitybegdt"].min(),
        "securityenddt_max": group["securityenddt"].max(),
        "secinfostartdt_min": group["secinfostartdt"].min(),
        "secinfoenddt_max": group["secinfoenddt"].max(),
    }

    summary_records.append(record)


summary = pd.DataFrame(summary_records)


# =============================================================================
# CLASSIFICATION FLAGS
# =============================================================================

summary["is_eqty"] = (
    summary["securitytype_values"].str.contains(
        r"(?:^|\|)EQTY(?:\||$)",
        regex=True,
        na=False,
    )
)

summary["is_fund"] = (
    summary["securitytype_values"].str.contains(
        r"(?:^|\|)FUND(?:\||$)",
        regex=True,
        na=False,
    )
)

summary["is_common_subtype"] = (
    summary["securitysubtype_values"].str.contains(
        r"(?:^|\|)COM(?:\||$)",
        regex=True,
        na=False,
    )
)

summary["is_etf_subtype"] = (
    summary["securitysubtype_values"].str.contains(
        r"(?:^|\|)ETF(?:\||$)",
        regex=True,
        na=False,
    )
)

summary["is_non_us"] = (
    summary["usincflg_values"].str.contains(
        r"(?:^|\|)N(?:\||$)",
        regex=True,
        na=False,
    )
)

summary["is_ad_sharetype"] = (
    summary["sharetype_values"].str.contains(
        r"(?:^|\|)AD(?:\||$)",
        regex=True,
        na=False,
    )
)

summary["is_acor"] = (
    summary["issuertype_values"].str.contains(
        r"(?:^|\|)ACOR(?:\||$)",
        regex=True,
        na=False,
    )
)


# =============================================================================
# CLASSIFICATION CATEGORY
# =============================================================================

def classify(row):

    if row["is_fund"] or row["is_etf_subtype"]:
        return "FUND_OR_ETF"

    if row["is_ad_sharetype"] or row["is_non_us"]:
        return "AD_OR_NON_US_EQUITY"

    if row["is_eqty"] and row["is_common_subtype"]:
        if row["is_acor"]:
            return "EQTY_COM_ACOR"
        return "EQTY_COM_CORP"

    return "OTHER"


summary["inspection_category"] = summary.apply(
    classify,
    axis=1,
)


# =============================================================================
# PRINT SUMMARY
# =============================================================================

print_header("SECURITY CLASSIFICATION SUMMARY")

print(
    summary[
        [
            "inspection_category",
            "permno",
            "ticker_values",
            "issuernm_values",
            "securitytype_values",
            "securitysubtype_values",
            "sharetype_values",
            "issuertype_values",
            "usincflg_values",
            "primaryexch_values",
            "siccd_values",
        ]
    ].to_string(index=False)
)


# =============================================================================
# PRINT AMBIGUOUS SECURITIES
# =============================================================================

print_header("AMBIGUOUS / SPECIAL CLASSIFICATION SECURITIES")

special = summary[
    (summary["is_fund"])
    | (summary["is_etf_subtype"])
    | (summary["is_ad_sharetype"])
    | (summary["is_non_us"])
    | (summary["is_acor"])
]

print(
    special[
        [
            "permno",
            "permco",
            "ticker_values",
            "issuernm_values",
            "securitytype_values",
            "securitysubtype_values",
            "sharetype_values",
            "issuertype_values",
            "usincflg_values",
            "primaryexch_values",
            "siccd_values",
            "inspection_category",
        ]
    ].to_string(index=False)
)


# =============================================================================
# SAVE
# =============================================================================

print_header("SAVING")

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

summary.to_csv(OUTPUT_FILE, index=False)

print(f"Saved: {OUTPUT_FILE}")

print_header("SECURITY CLASS INSPECTION COMPLETE")