from pathlib import Path
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"
TIER2_DIR = DATA_DIR / "tier2_historical_universe"

MASTER_FILE = (
    TIER2_DIR /
    "crsp_tier2_historical_security_master.csv"
)

DAILY_FILE = (
    DATA_DIR /
    "crsp_daily_clean.csv"
)

OUTPUT_UNIVERSE = (
    TIER2_DIR /
    "crsp_tier2_eligible_universe.csv"
)

OUTPUT_EXCLUSIONS = (
    TIER2_DIR /
    "crsp_tier2_universe_exclusions.csv"
)

OUTPUT_SUMMARY = (
    TIER2_DIR /
    "crsp_tier2_eligible_universe_summary.csv"
)


# =============================================================================
# PARAMETERS
# =============================================================================

RESEARCH_START = pd.Timestamp("1993-01-01")
RESEARCH_END = pd.Timestamp("2018-12-31")


# =============================================================================
# HELPERS
# =============================================================================

def normalize_columns(df):
    df.columns = [
        str(col).strip().lower()
        for col in df.columns
    ]
    return df


def require_columns(df, required, dataset_name):

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:

        print(f"\nAvailable {dataset_name} columns:")
        print(df.columns.tolist())

        raise ValueError(
            f"Required columns missing from {dataset_name}: "
            + ", ".join(missing)
        )


# =============================================================================
# LOAD HISTORICAL SECURITY MASTER
# =============================================================================

print("=" * 80)
print("LOADING TIER 2 HISTORICAL SECURITY MASTER")
print("=" * 80)

master = pd.read_csv(
    MASTER_FILE,
    low_memory=False
)

master = normalize_columns(master)

required_master_columns = [
    "permno",
    "permco",
    "ticker",
    "issuernm",
    "securitytype",
    "securitysubtype",
    "sharetype",
    "issuertype",
    "usincflg",
    "research_classification",
    "securitybegdt",
    "securityenddt",
]

require_columns(
    master,
    required_master_columns,
    "historical security master"
)


# =============================================================================
# NORMALIZE MASTER TYPES
# =============================================================================

master["permno"] = pd.to_numeric(
    master["permno"],
    errors="coerce"
)

master["securitybegdt"] = pd.to_datetime(
    master["securitybegdt"],
    errors="coerce"
)

master["securityenddt"] = pd.to_datetime(
    master["securityenddt"],
    errors="coerce"
)

print(f"Master rows: {len(master):,}")
print(
    f"Master PERMNOs: "
    f"{master['permno'].nunique():,}"
)


# =============================================================================
# LOAD CRSP DAILY
# =============================================================================

print("\n" + "=" * 80)
print("LOADING CRSP DAILY")
print("=" * 80)

daily = pd.read_csv(
    DAILY_FILE,
    low_memory=False
)

daily = normalize_columns(daily)

print(f"Daily rows: {len(daily):,}")
print(f"Daily columns: {len(daily.columns):,}")

required_daily_columns = [
    "permno",
    "dlycaldt",
]

require_columns(
    daily,
    required_daily_columns,
    "CRSP Daily"
)


# =============================================================================
# NORMALIZE DAILY TYPES
# =============================================================================

daily["permno"] = pd.to_numeric(
    daily["permno"],
    errors="coerce"
)

daily["dlycaldt"] = pd.to_datetime(
    daily["dlycaldt"],
    errors="coerce"
)

print(
    f"Daily PERMNOs: "
    f"{daily['permno'].nunique():,}"
)

print(
    f"Daily first date: "
    f"{daily['dlycaldt'].min()}"
)

print(
    f"Daily last date:  "
    f"{daily['dlycaldt'].max()}"
)


# =============================================================================
# RESEARCH-WINDOW DAILY DATA
# =============================================================================

daily_research = daily.loc[
    daily["dlycaldt"].between(
        RESEARCH_START,
        RESEARCH_END
    )
].copy()

print(
    f"Daily rows in research window: "
    f"{len(daily_research):,}"
)


# =============================================================================
# BUILD ONE ROW PER PERMNO
# =============================================================================

print("\n" + "=" * 80)
print("BUILDING SECURITY-LEVEL UNIVERSE")
print("=" * 80)

security = (
    master
    .sort_values(
        [
            "permno",
            "securitybegdt",
            "securityenddt",
        ]
    )
    .groupby(
        "permno",
        as_index=False
    )
    .agg(

        permco=(
            "permco",
            "first"
        ),

        ticker=(
            "ticker",
            "first"
        ),

        issuernm=(
            "issuernm",
            "first"
        ),

        securitytype=(
            "securitytype",
            "first"
        ),

        securitysubtype=(
            "securitysubtype",
            "first"
        ),

        sharetype=(
            "sharetype",
            "first"
        ),

        issuertype=(
            "issuertype",
            "first"
        ),

        usincflg=(
            "usincflg",
            "first"
        ),

        research_classification=(
            "research_classification",
            "first"
        ),

        historical_start=(
            "securitybegdt",
            "min"
        ),

        historical_end=(
            "securityenddt",
            "max"
        ),

        historical_master_rows=(
            "permno",
            "size"
        ),
    )
)


# =============================================================================
# CLIP HISTORICAL EXISTENCE TO RESEARCH WINDOW
# =============================================================================

security["research_start"] = (
    security["historical_start"]
    .clip(lower=RESEARCH_START)
)

security["research_end"] = (
    security["historical_end"]
    .clip(upper=RESEARCH_END)
)

security["historical_window_valid"] = (
    security["research_start"].notna()
    &
    security["research_end"].notna()
    &
    (
        security["research_start"]
        <=
        security["research_end"]
    )
)


# =============================================================================
# DAILY COVERAGE
# =============================================================================

daily_counts = (
    daily_research
    .groupby("permno")
    .size()
    .rename("daily_rows")
)

daily_start = (
    daily_research
    .groupby("permno")["dlycaldt"]
    .min()
    .rename("daily_start")
)

daily_end = (
    daily_research
    .groupby("permno")["dlycaldt"]
    .max()
    .rename("daily_end")
)

security = security.merge(
    daily_counts,
    on="permno",
    how="left"
)

security = security.merge(
    daily_start,
    on="permno",
    how="left"
)

security = security.merge(
    daily_end,
    on="permno",
    how="left"
)

security["daily_rows"] = (
    security["daily_rows"]
    .fillna(0)
    .astype(int)
)

security["has_daily_history"] = (
    security["daily_rows"] > 0
)


# =============================================================================
# DAILY COVERAGE RELATIVE TO HISTORICAL EXISTENCE
# =============================================================================

security["daily_begins_before_security_start"] = (
    security["daily_start"]
    <
    security["research_start"]
)

security["daily_ends_after_security_end"] = (
    security["daily_end"]
    >
    security["research_end"]
)

security["daily_temporally_consistent"] = (
    security["has_daily_history"]
    &
    ~security["daily_begins_before_security_start"]
    &
    ~security["daily_ends_after_security_end"]
)


# =============================================================================
# CLASSIFICATION RULES
# =============================================================================

security["eligible_security_type"] = (
    security["securitytype"]
    ==
    "EQTY"
)

security["eligible_security_subtype"] = (
    security["securitysubtype"]
    ==
    "COM"
)

security["eligible_sharetype"] = (
    security["sharetype"]
    ==
    "NS"
)

security["eligible_us_security"] = (
    security["usincflg"]
    ==
    "Y"
)


# =============================================================================
# RESEARCH CLASSIFICATION FLAGS
# =============================================================================

security["is_fund_or_etf"] = (
    security["research_classification"]
    ==
    "FUND_OR_ETF"
)

# IMPORTANT:
# The Phase 4 classification script used:
#
#     AD_OR_NON_US_EQUITY
#
# Therefore use that exact value here.

security["is_adr_or_non_us"] = (
    security["research_classification"]
    ==
    "AD_OR_NON_US_EQUITY"
)


# =============================================================================
# FINAL ELIGIBILITY
# =============================================================================

security["eligibility_status"] = (
    "ELIGIBLE"
)


# FUND / ETF

security.loc[
    security["is_fund_or_etf"],
    "eligibility_status"
] = "EXCLUDE_FUND_ETF"


# ADR / NON-US

security.loc[
    security["is_adr_or_non_us"],
    "eligibility_status"
] = "EXCLUDE_ADR_NON_US"


# OTHER CLASSIFICATION

security.loc[
    ~(
        security["eligible_security_type"]
        &
        security["eligible_security_subtype"]
        &
        security["eligible_sharetype"]
        &
        security["eligible_us_security"]
    )
    &
    (
        security["eligibility_status"]
        ==
        "ELIGIBLE"
    ),
    "eligibility_status"
] = "EXCLUDE_CLASSIFICATION"


# =============================================================================
# FINAL ELIGIBILITY FLAG
# =============================================================================

security["eligible_for_tier2"] = (
    security["eligibility_status"]
    ==
    "ELIGIBLE"
)


# =============================================================================
# DAILY COVERAGE STATUS
# =============================================================================

security["daily_coverage_status"] = (
    "HAS_DAILY_HISTORY"
)

security.loc[
    ~security["has_daily_history"],
    "daily_coverage_status"
] = "NO_DAILY_HISTORY"


# =============================================================================
# EXECUTION DATA AVAILABILITY
# =============================================================================

security["execution_data_available"] = (
    security["eligible_for_tier2"]
    &
    security["has_daily_history"]
)


# =============================================================================
# DAILY-ONLY PERMNO FLAG
# =============================================================================

master_permnos = set(
    security["permno"]
    .dropna()
    .astype(int)
)

daily_permnos = set(
    daily_research["permno"]
    .dropna()
    .astype(int)
)

daily_only_permnos = (
    daily_permnos -
    master_permnos
)

security["daily_only"] = False


# No DAILY_ONLY securities are added to the historical universe.
#
# They remain outside the validated Tier 2 universe until their identity
# and historical classification are reconciled.


# =============================================================================
# SPLIT UNIVERSE / EXCLUSIONS
# =============================================================================

eligible = security.loc[
    security["eligible_for_tier2"]
].copy()

exclusions = security.loc[
    ~security["eligible_for_tier2"]
].copy()


# =============================================================================
# SORT
# =============================================================================

security = security.sort_values(
    "permno"
)

eligible = eligible.sort_values(
    "permno"
)

exclusions = exclusions.sort_values(
    "permno"
)


# =============================================================================
# SAVE ELIGIBLE UNIVERSE
# =============================================================================

eligible.to_csv(
    OUTPUT_UNIVERSE,
    index=False
)


# =============================================================================
# SAVE EXCLUSIONS
# =============================================================================

exclusions.to_csv(
    OUTPUT_EXCLUSIONS,
    index=False
)


# =============================================================================
# SUMMARY
# =============================================================================

summary = pd.DataFrame({

    "metric": [

        "historical_master_permnos",

        "eligible_tier2_permnos",

        "excluded_permnos",

        "fund_etf_exclusions",

        "adr_non_us_exclusions",

        "classification_exclusions",

        "eligible_with_daily_history",

        "eligible_without_daily_history",

        "eligible_with_temporally_consistent_daily_history",

        "daily_only_not_in_master",

    ],

    "value": [

        security["permno"].nunique(),

        eligible["permno"].nunique(),

        exclusions["permno"].nunique(),

        (
            security["eligibility_status"]
            ==
            "EXCLUDE_FUND_ETF"
        ).sum(),

        (
            security["eligibility_status"]
            ==
            "EXCLUDE_ADR_NON_US"
        ).sum(),

        (
            security["eligibility_status"]
            ==
            "EXCLUDE_CLASSIFICATION"
        ).sum(),

        (
            eligible["has_daily_history"]
        ).sum(),

        (
            ~eligible["has_daily_history"]
        ).sum(),

        (
            eligible[
                "daily_temporally_consistent"
            ]
        ).sum(),

        len(daily_only_permnos),

    ]
})


summary.to_csv(
    OUTPUT_SUMMARY,
    index=False
)


# =============================================================================
# REPORT
# =============================================================================

print("\n" + "=" * 80)
print("TIER 2 ELIGIBILITY SUMMARY")
print("=" * 80)

print(
    summary.to_string(
        index=False
    )
)


print("\n" + "=" * 80)
print("ELIGIBLE TIER 2 SECURITIES")
print("=" * 80)

print(
    eligible[
        [
            "permno",
            "permco",
            "ticker",
            "research_classification",
            "historical_start",
            "historical_end",
            "research_start",
            "research_end",
            "daily_start",
            "daily_end",
            "daily_rows",
            "daily_coverage_status",
            "daily_temporally_consistent",
            "execution_data_available",
        ]
    ].to_string(
        index=False
    )
)


print("\n" + "=" * 80)
print("EXCLUDED SECURITIES")
print("=" * 80)

print(
    exclusions[
        [
            "permno",
            "ticker",
            "research_classification",
            "securitytype",
            "securitysubtype",
            "sharetype",
            "issuertype",
            "usincflg",
            "eligibility_status",
        ]
    ].to_string(
        index=False
    )
)


print("\n" + "=" * 80)
print("DAILY_ONLY SECURITIES")
print("=" * 80)

print(
    f"DAILY_ONLY PERMNOs: "
    f"{len(daily_only_permnos)}"
)

if daily_only_permnos:

    print(
        sorted(
            daily_only_permnos
        )
    )

else:

    print(
        "PASS: No DAILY_ONLY PERMNOs."
    )


print("\n" + "=" * 80)
print("PASS / REVIEW")
print("=" * 80)

print(
    "PASS: Tier 2 eligibility is determined from the "
    "historical CRSP security-master classification."
)

print(
    "PASS: Historical security existence is based on "
    "securitybegdt/securityenddt."
)

print(
    "PASS: Research dates are restricted to 1993-01-01 "
    "through 2018-12-31."
)

print(
    "PASS: Missing daily history does not remove a "
    "historically eligible security."
)

print(
    "PASS: FUND/ETF securities are explicitly excluded."
)

print(
    "PASS: ADR/non-US securities are explicitly excluded."
)

print(
    "PASS: DAILY_ONLY securities remain outside the "
    "validated Tier 2 universe."
)

print("\nSaved:")
print(OUTPUT_UNIVERSE)
print(OUTPUT_EXCLUSIONS)
print(OUTPUT_SUMMARY)