from pathlib import Path
import pandas as pd
import numpy as np


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"


ELIGIBLE_FILE = DATA_DIR / "crsp_tier1_eligible_universe.csv"
DAILY_FILE = DATA_DIR / "crsp_tier1_daily.csv"
QUALITY_FILE = DATA_DIR / "crsp_tier1_daily_quality_summary.csv"
INTEGRITY_FILE = DATA_DIR / "crsp_tier1_daily_integrity_security_summary.csv"

OUTPUT_DAILY = DATA_DIR / "crsp_tier1_research_dataset.csv"
OUTPUT_SECURITY_SUMMARY = DATA_DIR / "crsp_tier1_research_security_summary.csv"
OUTPUT_VALIDATION = DATA_DIR / "crsp_tier1_research_dataset_validation.csv"


# =============================================================================
# CONFIGURATION
# =============================================================================

RESEARCH_START = pd.Timestamp("1993-01-01")
RESEARCH_END = pd.Timestamp("2018-12-31")


# =============================================================================
# HELPER FUNCTIONS
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


def normalize_permno(df):
    df = df.copy()

    if "permno" not in df.columns:
        raise ValueError("PERMNO column is missing.")

    df["permno"] = pd.to_numeric(
        df["permno"],
        errors="coerce"
    ).astype("Int64")

    return df


# =============================================================================
# LOAD INPUTS
# =============================================================================

section("LOADING ELIGIBLE TIER 1 UNIVERSE")

eligible = pd.read_csv(ELIGIBLE_FILE)
eligible = normalize_columns(eligible)
eligible = normalize_permno(eligible)

print(f"Eligible rows:      {len(eligible):,}")
print(f"Eligible PERMNOs:   {eligible['permno'].nunique():,}")


section("LOADING TIER 1 DAILY DATASET")

daily = pd.read_csv(
    DAILY_FILE,
    low_memory=False
)

daily = normalize_columns(daily)
daily = normalize_permno(daily)

print(f"Daily rows:         {len(daily):,}")
print(f"Daily PERMNOs:      {daily['permno'].nunique():,}")


section("LOADING DAILY QUALITY SUMMARY")

quality = pd.read_csv(QUALITY_FILE)
quality = normalize_columns(quality)
quality = normalize_permno(quality)

print(f"Quality rows:       {len(quality):,}")
print(f"Quality PERMNOs:    {quality['permno'].nunique():,}")


section("LOADING DAILY INTEGRITY SUMMARY")

integrity = pd.read_csv(INTEGRITY_FILE)
integrity = normalize_columns(integrity)
integrity = normalize_permno(integrity)

print(f"Integrity rows:     {len(integrity):,}")
print(f"Integrity PERMNOs:  {integrity['permno'].nunique():,}")


# =============================================================================
# VALIDATE INPUT STRUCTURE
# =============================================================================

section("VALIDATING INPUT STRUCTURE")

required_daily = {
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
}

missing_daily = required_daily - set(daily.columns)

if missing_daily:
    raise ValueError(
        f"Missing required daily columns: {sorted(missing_daily)}"
    )

if "permno" not in eligible.columns:
    raise ValueError("Eligible universe is missing permno.")

print("PASS   Required input columns present.")


# =============================================================================
# PREPARE DATES
# =============================================================================

section("PREPARING DAILY DATES")

daily["dlycaldt"] = pd.to_datetime(
    daily["dlycaldt"],
    errors="coerce"
)

invalid_dates = daily["dlycaldt"].isna().sum()

print(f"Invalid daily dates: {invalid_dates:,}")

if invalid_dates != 0:
    raise ValueError("Invalid daily dates detected.")

print(
    f"Daily date range: "
    f"{daily['dlycaldt'].min().date()} to "
    f"{daily['dlycaldt'].max().date()}"
)


# =============================================================================
# VALIDATE PERMNO SETS
# =============================================================================

section("VALIDATING PERMNO COVERAGE")

eligible_permnos = set(
    eligible["permno"].dropna().astype(int)
)

daily_permnos = set(
    daily["permno"].dropna().astype(int)
)

quality_permnos = set(
    quality["permno"].dropna().astype(int)
)

integrity_permnos = set(
    integrity["permno"].dropna().astype(int)
)

print(f"Eligible PERMNOs:       {len(eligible_permnos):,}")
print(f"Daily PERMNOs:          {len(daily_permnos):,}")
print(f"Quality PERMNOs:        {len(quality_permnos):,}")
print(f"Integrity PERMNOs:      {len(integrity_permnos):,}")

missing_daily = eligible_permnos - daily_permnos
unexpected_daily = daily_permnos - eligible_permnos

missing_quality = eligible_permnos - quality_permnos
unexpected_quality = quality_permnos - eligible_permnos

missing_integrity = eligible_permnos - integrity_permnos
unexpected_integrity = integrity_permnos - eligible_permnos

print(f"Missing from daily:     {len(missing_daily):,}")
print(f"Unexpected daily:       {len(unexpected_daily):,}")
print(f"Missing from quality:   {len(missing_quality):,}")
print(f"Unexpected quality:     {len(unexpected_quality):,}")
print(f"Missing from integrity: {len(missing_integrity):,}")
print(f"Unexpected integrity:   {len(unexpected_integrity):,}")

if (
    missing_daily
    or unexpected_daily
    or missing_quality
    or unexpected_quality
    or missing_integrity
    or unexpected_integrity
):
    raise ValueError(
        "PERMNO coverage mismatch detected across Tier 1 inputs."
    )

print("PASS   All Tier 1 inputs contain the same PERMNO universe.")


# =============================================================================
# VALIDATE UNIQUE SECURITY-LEVEL INPUTS
# =============================================================================

section("VALIDATING SECURITY-LEVEL INPUTS")

if eligible["permno"].duplicated().any():
    raise ValueError("Eligible universe contains duplicate PERMNOs.")

if quality["permno"].duplicated().any():
    raise ValueError("Quality summary contains duplicate PERMNOs.")

if integrity["permno"].duplicated().any():
    raise ValueError("Integrity summary contains duplicate PERMNOs.")

print("PASS   Security-level inputs contain one row per PERMNO.")


# =============================================================================
# PREPARE SECURITY MASTER
# =============================================================================

section("BUILDING TIER 1 SECURITY MASTER")

security_columns = [
    "permno",
    "permco",
    "ticker",
    "cusip",
    "issuernm",
    "securitytype",
    "securitysubtype",
    "sharetype",
    "siccd",
    "primaryexch",
    "securitybegdt",
    "securityenddt",
]

available_security_columns = [
    col for col in security_columns
    if col in eligible.columns
]

security_master = eligible[
    available_security_columns
].copy()

security_master = security_master.drop_duplicates(
    subset=["permno"]
)

print(f"Security master rows: {len(security_master):,}")


# =============================================================================
# ATTACH QUALITY AND INTEGRITY METADATA
# =============================================================================

section("ATTACHING SECURITY QUALITY METADATA")

quality_columns = [
    col for col in quality.columns
    if col != "permno"
]

quality_attach = quality[
    ["permno"] + quality_columns
].copy()

integrity_columns = [
    col for col in integrity.columns
    if col != "permno"
]

integrity_attach = integrity[
    ["permno"] + integrity_columns
].copy()

security_summary = security_master.merge(
    quality_attach,
    on="permno",
    how="left",
    validate="one_to_one",
    suffixes=("", "_quality")
)

security_summary = security_summary.merge(
    integrity_attach,
    on="permno",
    how="left",
    validate="one_to_one",
    suffixes=("", "_integrity")
)

print(
    f"Security summary rows: "
    f"{len(security_summary):,}"
)


# =============================================================================
# ATTACH SECURITY IDENTIFIERS TO DAILY DATA
# =============================================================================

section("ATTACHING SECURITY IDENTIFIERS TO DAILY DATA")

identifier_columns = [
    col for col in [
        "permco",
        "ticker",
        "cusip",
        "issuernm",
        "securitytype",
        "securitysubtype",
        "sharetype",
        "siccd",
        "primaryexch",
    ]
    if col in security_master.columns
]

identifier_master = security_master[
    ["permno"] + identifier_columns
].copy()

daily_research = daily.merge(
    identifier_master,
    on="permno",
    how="left",
    validate="many_to_one",
    suffixes=("", "_universe")
)

print(f"Daily rows after merge: {len(daily_research):,}")


# =============================================================================
# BUILD DIAGNOSTIC FLAGS
# =============================================================================

section("BUILDING RESEARCH DIAGNOSTIC FLAGS")

daily_research["has_bid"] = (
    daily_research["dlybid"].notna()
)

daily_research["has_ask"] = (
    daily_research["dlyask"].notna()
)

daily_research["has_two_sided_quote"] = (
    daily_research["has_bid"]
    & daily_research["has_ask"]
)

daily_research["crossed_quote"] = (
    daily_research["has_two_sided_quote"]
    & (daily_research["dlybid"] > daily_research["dlyask"])
)

daily_research["has_price"] = (
    daily_research["dlyprc"].notna()
)

daily_research["has_volume"] = (
    daily_research["dlyvol"].notna()
)

daily_research["has_return"] = (
    daily_research["dlyret"].notna()
)

daily_research["large_return_outlier"] = (
    daily_research["dlyret"].abs() > 0.50
)

daily_research["large_price_jump"] = False

daily_research = daily_research.sort_values(
    ["permno", "dlycaldt"]
).reset_index(drop=True)

daily_research["previous_price"] = (
    daily_research
    .groupby("permno")["dlyprc"]
    .shift(1)
)

valid_price_pair = (
    daily_research["dlyprc"].notna()
    & daily_research["previous_price"].notna()
    & (daily_research["previous_price"] != 0)
)

daily_research.loc[
    valid_price_pair,
    "large_price_jump"
] = (
    (
        daily_research.loc[valid_price_pair, "dlyprc"]
        / daily_research.loc[valid_price_pair, "previous_price"]
        - 1
    ).abs() > 0.50
)

daily_research.drop(
    columns=["previous_price"],
    inplace=True
)

print(
    f"Crossed quote rows:       "
    f"{daily_research['crossed_quote'].sum():,}"
)

print(
    f"Large return outlier rows: "
    f"{daily_research['large_return_outlier'].sum():,}"
)

print(
    f"Large price jump rows:      "
    f"{daily_research['large_price_jump'].sum():,}"
)


# =============================================================================
# RESEARCH WINDOW VALIDATION
# =============================================================================

section("VALIDATING RESEARCH WINDOW")

outside_window = (
    (daily_research["dlycaldt"] < RESEARCH_START)
    | (daily_research["dlycaldt"] > RESEARCH_END)
).sum()

print(f"Observations outside window: {outside_window:,}")

if outside_window != 0:
    raise ValueError(
        "Daily observations fall outside the research window."
    )

print("PASS   All observations lie within research window.")


# =============================================================================
# VALIDATE DAILY ROW STRUCTURE
# =============================================================================

section("VALIDATING DAILY DATA STRUCTURE")

duplicate_keys = daily_research.duplicated(
    subset=["permno", "dlycaldt"]
).sum()

missing_permno = daily_research["permno"].isna().sum()

unexpected_permnos = (
    set(daily_research["permno"].dropna().astype(int))
    - eligible_permnos
)

print(f"Duplicate PERMNO-date rows: {duplicate_keys:,}")
print(f"Missing PERMNO values:      {missing_permno:,}")
print(f"Unexpected PERMNOs:         {len(unexpected_permnos):,}")

if duplicate_keys != 0:
    raise ValueError("Duplicate PERMNO-date observations detected.")

if missing_permno != 0:
    raise ValueError("Missing PERMNO values detected.")

if unexpected_permnos:
    raise ValueError("Unexpected PERMNOs detected.")

print("PASS   Daily research dataset structure validated.")


# =============================================================================
# VALIDATE SECURITY METADATA ATTACHMENT
# =============================================================================

section("VALIDATING SECURITY METADATA")

missing_ticker = daily_research["ticker"].isna().sum()

if "permco" in daily_research.columns:
    missing_permco = daily_research["permco"].isna().sum()
else:
    missing_permco = len(daily_research)

print(f"Rows missing ticker: {missing_ticker:,}")
print(f"Rows missing PERMCO: {missing_permco:,}")

if missing_ticker != 0 or missing_permco != 0:
    raise ValueError(
        "Security metadata attachment is incomplete."
    )

print("PASS   Security metadata attached to all observations.")


# =============================================================================
# BUILD SECURITY-LEVEL RESEARCH SUMMARY
# =============================================================================

section("BUILDING SECURITY-LEVEL RESEARCH SUMMARY")

daily_counts = (
    daily_research
    .groupby("permno")
    .agg(
        research_first_date=("dlycaldt", "min"),
        research_last_date=("dlycaldt", "max"),
        daily_observations=("dlycaldt", "size"),
        price_observations=("has_price", "sum"),
        volume_observations=("has_volume", "sum"),
        return_observations=("has_return", "sum"),
        two_sided_quote_observations=(
            "has_two_sided_quote",
            "sum"
        ),
        crossed_quote_observations=(
            "crossed_quote",
            "sum"
        ),
        large_return_outlier_observations=(
            "large_return_outlier",
            "sum"
        ),
        large_price_jump_observations=(
            "large_price_jump",
            "sum"
        ),
    )
    .reset_index()
)

research_security_summary = security_master.merge(
    daily_counts,
    on="permno",
    how="left",
    validate="one_to_one"
)

research_security_summary[
    "price_coverage_pct"
] = (
    research_security_summary["price_observations"]
    / research_security_summary["daily_observations"]
    * 100
)

research_security_summary[
    "volume_coverage_pct"
] = (
    research_security_summary["volume_observations"]
    / research_security_summary["daily_observations"]
    * 100
)

research_security_summary[
    "quote_coverage_pct"
] = (
    research_security_summary[
        "two_sided_quote_observations"
    ]
    / research_security_summary["daily_observations"]
    * 100
)

research_security_summary[
    "return_coverage_pct"
] = (
    research_security_summary["return_observations"]
    / research_security_summary["daily_observations"]
    * 100
)


# =============================================================================
# FINAL SECURITY COVERAGE VALIDATION
# =============================================================================

section("VALIDATING SECURITY COVERAGE")

summary_permnos = set(
    research_security_summary["permno"]
    .dropna()
    .astype(int)
)

missing_summary = eligible_permnos - summary_permnos
unexpected_summary = summary_permnos - eligible_permnos

print(f"Eligible PERMNOs:        {len(eligible_permnos):,}")
print(f"Summary PERMNOs:         {len(summary_permnos):,}")
print(f"Missing summary PERMNOs: {len(missing_summary):,}")
print(f"Unexpected PERMNOs:      {len(unexpected_summary):,}")

if missing_summary or unexpected_summary:
    raise ValueError(
        "Security-level research summary does not match universe."
    )

print("PASS   Security-level research summary is complete.")


# =============================================================================
# FINAL VALIDATION FLAGS
# =============================================================================

section("BUILDING FINAL VALIDATION SUMMARY")

validation = {
    "daily_rows_positive": len(daily_research) > 0,
    "daily_permnos_match": (
        set(daily_research["permno"].astype(int))
        == eligible_permnos
    ),
    "no_duplicate_permno_date": duplicate_keys == 0,
    "no_missing_permno": missing_permno == 0,
    "no_unexpected_permnos": len(unexpected_permnos) == 0,
    "all_within_research_window": outside_window == 0,
    "security_metadata_complete": (
        missing_ticker == 0
        and missing_permco == 0
    ),
    "security_summary_complete": (
        not missing_summary
        and not unexpected_summary
    ),
    "diagnostics_retained": True,
}

validation_df = pd.DataFrame(
    [
        {
            "check": check,
            "status": "PASS" if passed else "FAIL",
        }
        for check, passed in validation.items()
    ]
)

for _, row in validation_df.iterrows():
    print(
        f"{row['status']:4}   {row['check']}"
    )

if not validation_df["status"].eq("PASS").all():
    raise ValueError(
        "Final research dataset validation failed."
    )


# =============================================================================
# PREPARE OUTPUT COLUMNS
# =============================================================================

section("PREPARING OUTPUT DATA")

daily_research = daily_research.sort_values(
    ["permno", "dlycaldt"]
).reset_index(drop=True)

research_security_summary = (
    research_security_summary
    .sort_values("permno")
    .reset_index(drop=True)
)

print(
    f"Final daily rows:       "
    f"{len(daily_research):,}"
)

print(
    f"Final daily PERMNOs:    "
    f"{daily_research['permno'].nunique():,}"
)

print(
    f"Security summary rows:  "
    f"{len(research_security_summary):,}"
)


# =============================================================================
# SAVE OUTPUTS
# =============================================================================

section("SAVING OUTPUTS")

daily_research.to_csv(
    OUTPUT_DAILY,
    index=False
)

research_security_summary.to_csv(
    OUTPUT_SECURITY_SUMMARY,
    index=False
)

validation_df.to_csv(
    OUTPUT_VALIDATION,
    index=False
)

print(f"Research dataset:")
print(f"  {OUTPUT_DAILY}")
print(f"Rows: {len(daily_research):,}")

print(f"\nSecurity summary:")
print(f"  {OUTPUT_SECURITY_SUMMARY}")
print(f"Rows: {len(research_security_summary):,}")

print(f"\nValidation:")
print(f"  {OUTPUT_VALIDATION}")
print(f"Rows: {len(validation_df):,}")


# =============================================================================
# FINAL SUMMARY
# =============================================================================

section("TIER 1 RESEARCH DATASET ASSEMBLY COMPLETE")

print(
    f"Tier 1 securities:       "
    f"{daily_research['permno'].nunique():,}"
)

print(
    f"Daily observations:      "
    f"{len(daily_research):,}"
)

print(
    f"Research start:          "
    f"{daily_research['dlycaldt'].min().date()}"
)

print(
    f"Research end:            "
    f"{daily_research['dlycaldt'].max().date()}"
)

print(
    f"Crossed quote rows:      "
    f"{daily_research['crossed_quote'].sum():,}"
)

print(
    f"Return outlier rows:     "
    f"{daily_research['large_return_outlier'].sum():,}"
)

print(
    f"Large price jump rows:   "
    f"{daily_research['large_price_jump'].sum():,}"
)

print("\nPASS   Tier 1 research dataset assembled and validated.")