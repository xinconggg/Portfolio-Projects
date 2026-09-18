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

OUTPUT_FILE = (
    TIER2_DIR /
    "crsp_tier2_daily_coverage_diagnostic.csv"
)


# =============================================================================
# PARAMETERS
# =============================================================================

RESEARCH_START = pd.Timestamp("1993-01-01")
RESEARCH_END = pd.Timestamp("2018-12-31")


# =============================================================================
# LOAD TIER 2 HISTORICAL SECURITY MASTER
# =============================================================================

print("=" * 80)
print("LOADING TIER 2 HISTORICAL SECURITY MASTER")
print("=" * 80)

master = pd.read_csv(
    MASTER_FILE,
    low_memory=False
)

master.columns = [
    str(col).strip().lower()
    for col in master.columns
]

required_master_columns = [
    "permno",
    "permco",
    "ticker",
    "issuernm",
    "research_classification",
    "effective_start",
    "effective_end",
    "securitybegdt",
    "securityenddt",
]

missing_master_columns = [
    col
    for col in required_master_columns
    if col not in master.columns
]

if missing_master_columns:
    print("\nAvailable master columns:")
    print(master.columns.tolist())

    raise ValueError(
        "Required columns missing from historical security master: "
        + ", ".join(missing_master_columns)
    )


# =============================================================================
# NORMALIZE MASTER TYPES
# =============================================================================

master["permno"] = pd.to_numeric(
    master["permno"],
    errors="coerce"
).astype("Int64")

master["effective_start"] = pd.to_datetime(
    master["effective_start"],
    errors="coerce"
)

master["effective_end"] = pd.to_datetime(
    master["effective_end"],
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

master_permnos = set(
    master["permno"]
    .dropna()
    .astype(int)
)

print(f"Master rows: {len(master):,}")
print(f"Master PERMNOs: {len(master_permnos):,}")


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

daily.columns = [
    str(col).strip().lower()
    for col in daily.columns
]

required_daily_columns = [
    "permno",
    "dlycaldt",
]

missing_daily_columns = [
    col
    for col in required_daily_columns
    if col not in daily.columns
]

if missing_daily_columns:
    print("\nAvailable Daily columns:")
    print(daily.columns.tolist())

    raise ValueError(
        "Required columns missing from CRSP Daily: "
        + ", ".join(missing_daily_columns)
    )


# =============================================================================
# NORMALIZE DAILY TYPES
# =============================================================================

daily["permno"] = pd.to_numeric(
    daily["permno"],
    errors="coerce"
).astype("Int64")

daily["dlycaldt"] = pd.to_datetime(
    daily["dlycaldt"],
    errors="coerce"
)

print(f"Daily rows before research-window filter: {len(daily):,}")
print(f"Daily PERMNOs: {daily['permno'].nunique():,}")
print(f"Daily first date: {daily['dlycaldt'].min()}")
print(f"Daily last date:  {daily['dlycaldt'].max()}")


# =============================================================================
# APPLY RESEARCH WINDOW
# =============================================================================

daily = daily.loc[
    daily["dlycaldt"].between(
        RESEARCH_START,
        RESEARCH_END
    )
].copy()

print(
    f"Daily rows within research window "
    f"({RESEARCH_START.date()} to {RESEARCH_END.date()}): "
    f"{len(daily):,}"
)

print(
    f"Research-window Daily PERMNOs: "
    f"{daily['permno'].nunique():,}"
)


# =============================================================================
# PERMNO SETS
# =============================================================================

daily_permnos = set(
    daily["permno"]
    .dropna()
    .astype(int)
)

matched_permnos = (
    master_permnos &
    daily_permnos
)

names_only = (
    master_permnos -
    daily_permnos
)

daily_only = (
    daily_permnos -
    master_permnos
)


# =============================================================================
# PERMNO RECONCILIATION
# =============================================================================

print("\n" + "=" * 80)
print("PERMNO RECONCILIATION")
print("=" * 80)

print(
    f"Historical master PERMNOs: {len(master_permnos):,}"
)

print(
    f"Research-window Daily PERMNOs: {len(daily_permnos):,}"
)

print(
    f"Matched: {len(matched_permnos):,}"
)

print(
    f"NAMES_ONLY: {len(names_only):,}"
)

print(
    f"DAILY_ONLY: {len(daily_only):,}"
)

if names_only:
    print("\nNAMES_ONLY:")
    print(sorted(names_only))

if daily_only:
    print("\nDAILY_ONLY:")
    print(sorted(daily_only))


# =============================================================================
# PERMNO-LEVEL SECURITY EXISTENCE WINDOWS
# =============================================================================
#
# IMPORTANT:
#
# securitybegdt / securityenddt represent the CRSP security existence
# window.
#
# effective_start / effective_end represent classification intervals.
#
# This diagnostic uses the security existence window.
# =============================================================================

master_ranges = (
    master
    .groupby("permno", as_index=False)
    .agg(
        historical_start=("securitybegdt", "min"),
        historical_end=("securityenddt", "max"),
        historical_rows=("permno", "size"),
    )
)

# Restrict security existence window to the research period.

master_ranges["historical_start"] = (
    master_ranges["historical_start"].clip(
        lower=RESEARCH_START
    )
)

master_ranges["historical_end"] = (
    master_ranges["historical_end"].clip(
        upper=RESEARCH_END
    )
)

master_ranges["historical_interval_valid"] = (
    master_ranges["historical_start"].notna()
    &
    master_ranges["historical_end"].notna()
    &
    (
        master_ranges["historical_start"]
        <=
        master_ranges["historical_end"]
    )
)


# =============================================================================
# DAILY PERMNO-LEVEL RANGES
# =============================================================================

daily_ranges = (
    daily
    .groupby("permno", as_index=False)
    .agg(
        daily_start=("dlycaldt", "min"),
        daily_end=("dlycaldt", "max"),
        daily_rows=("permno", "size"),
    )
)


# =============================================================================
# MERGE MASTER AND DAILY RANGES
# =============================================================================

diagnostic = master_ranges.merge(
    daily_ranges,
    on="permno",
    how="left"
)


# =============================================================================
# SECURITY METADATA
# =============================================================================

metadata_cols = [
    "permno",
    "permco",
    "ticker",
    "issuernm",
    "research_classification",
]

metadata = (
    master[metadata_cols]
    .drop_duplicates("permno")
)

diagnostic = diagnostic.merge(
    metadata,
    on="permno",
    how="left"
)


# =============================================================================
# COVERAGE FLAGS
# =============================================================================

diagnostic["has_daily_history"] = (
    diagnostic["daily_rows"]
    .fillna(0)
    > 0
)

diagnostic["missing_daily_history"] = (
    ~diagnostic["has_daily_history"]
)


# -----------------------------------------------------------------------------
# Daily begins before security existence window
# -----------------------------------------------------------------------------

diagnostic["daily_begins_before_historical"] = (
    diagnostic["daily_start"]
    <
    diagnostic["historical_start"]
)


# -----------------------------------------------------------------------------
# Daily ends after security existence window
# -----------------------------------------------------------------------------

diagnostic["daily_ends_after_historical"] = (
    diagnostic["daily_end"]
    >
    diagnostic["historical_end"]
)


# -----------------------------------------------------------------------------
# Daily start within security existence window
# -----------------------------------------------------------------------------

diagnostic["daily_start_within_history"] = (
    diagnostic["daily_start"]
    >=
    diagnostic["historical_start"]
)


# -----------------------------------------------------------------------------
# Daily end within security existence window
# -----------------------------------------------------------------------------

diagnostic["daily_end_within_history"] = (
    diagnostic["daily_end"]
    <=
    diagnostic["historical_end"]
)


# -----------------------------------------------------------------------------
# Overall temporal consistency
# -----------------------------------------------------------------------------

diagnostic["daily_within_security_life"] = (
    diagnostic["has_daily_history"]
    &
    diagnostic["historical_interval_valid"]
    &
    diagnostic["daily_start_within_history"]
    &
    diagnostic["daily_end_within_history"]
)


# =============================================================================
# CLASSIFICATION
# =============================================================================

def classify(row):

    if row["missing_daily_history"]:
        return "MISSING_DAILY_HISTORY"

    if not row["historical_interval_valid"]:
        return "INVALID_HISTORICAL_INTERVAL"

    if row["daily_begins_before_historical"]:
        return "DAILY_BEFORE_HISTORICAL_START"

    if row["daily_ends_after_historical"]:
        return "DAILY_AFTER_HISTORICAL_END"

    return "TEMPORALLY_CONSISTENT"


diagnostic["coverage_status"] = diagnostic.apply(
    classify,
    axis=1
)


# =============================================================================
# ADD DAILY-ONLY PERMNOs
# =============================================================================

daily_only_rows = []

for permno in sorted(daily_only):

    d = daily.loc[
        daily["permno"] == permno
    ]

    daily_only_rows.append({
        "permno": permno,

        "historical_start": pd.NaT,
        "historical_end": pd.NaT,
        "historical_rows": 0,
        "historical_interval_valid": False,

        "daily_start": d["dlycaldt"].min(),
        "daily_end": d["dlycaldt"].max(),
        "daily_rows": len(d),

        "permco": pd.NA,
        "ticker": pd.NA,
        "issuernm": pd.NA,
        "research_classification": pd.NA,

        "has_daily_history": True,
        "missing_daily_history": False,

        "daily_begins_before_historical": False,
        "daily_ends_after_historical": False,

        "daily_start_within_history": False,
        "daily_end_within_history": False,

        "daily_within_security_life": False,

        "coverage_status": "DAILY_ONLY",
    })


if daily_only_rows:

    daily_only_df = pd.DataFrame(
        daily_only_rows
    )

    diagnostic = pd.concat(
        [
            diagnostic,
            daily_only_df
        ],
        ignore_index=True
    )


# =============================================================================
# OUTPUT
# =============================================================================

diagnostic = diagnostic.sort_values(
    "permno"
)

diagnostic.to_csv(
    OUTPUT_FILE,
    index=False
)


# =============================================================================
# REPORT
# =============================================================================

print("\n" + "=" * 80)
print("DAILY COVERAGE DIAGNOSTIC")
print("=" * 80)

print(
    diagnostic[
        [
            "permno",
            "ticker",
            "research_classification",
            "historical_start",
            "historical_end",
            "daily_start",
            "daily_end",
            "daily_rows",
            "coverage_status",
        ]
    ].to_string(index=False)
)


# =============================================================================
# STATUS SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("COVERAGE STATUS SUMMARY")
print("=" * 80)

print(
    diagnostic["coverage_status"]
    .value_counts()
    .sort_index()
    .to_string()
)


# =============================================================================
# MISSING DAILY HISTORY
# =============================================================================

print("\n" + "=" * 80)
print("MISSING DAILY HISTORY")
print("=" * 80)

missing = diagnostic[
    diagnostic["missing_daily_history"]
]

if len(missing) == 0:

    print(
        "PASS: No historical-master securities "
        "have missing daily history."
    )

else:

    print(
        missing[
            [
                "permno",
                "ticker",
                "research_classification",
                "historical_start",
                "historical_end",
            ]
        ].to_string(index=False)
    )


# =============================================================================
# TEMPORAL EXCEPTIONS
# =============================================================================

print("\n" + "=" * 80)
print("TEMPORAL EXCEPTIONS")
print("=" * 80)

temporal_exceptions = diagnostic[
    diagnostic["coverage_status"].isin(
        [
            "DAILY_BEFORE_HISTORICAL_START",
            "DAILY_AFTER_HISTORICAL_END",
            "INVALID_HISTORICAL_INTERVAL",
        ]
    )
]

if len(temporal_exceptions) == 0:

    print(
        "PASS: No temporal inconsistencies detected."
    )

else:

    print(
        temporal_exceptions[
            [
                "permno",
                "ticker",
                "historical_start",
                "historical_end",
                "daily_start",
                "daily_end",
                "coverage_status",
            ]
        ].to_string(index=False)
    )


# =============================================================================
# FINAL SUMMARY
# =============================================================================

print("\n" + "=" * 80)
print("FINAL SUMMARY")
print("=" * 80)

print(
    f"Historical master PERMNOs:       "
    f"{len(master_permnos):,}"
)

print(
    f"Research-window Daily PERMNOs:   "
    f"{len(daily_permnos):,}"
)

print(
    f"Matched PERMNOs:                  "
    f"{len(matched_permnos):,}"
)

print(
    f"NAMES_ONLY:                       "
    f"{len(names_only):,}"
)

print(
    f"DAILY_ONLY:                       "
    f"{len(daily_only):,}"
)

print(
    f"Missing Daily history:            "
    f"{diagnostic['missing_daily_history'].sum():,}"
)

print(
    f"Temporally consistent:             "
    f"{(
        diagnostic['coverage_status']
        == 'TEMPORALLY_CONSISTENT'
    ).sum():,}"
)

print(
    f"Temporal exceptions:              "
    f"{len(temporal_exceptions):,}"
)

print("\nSaved:")
print(OUTPUT_FILE)