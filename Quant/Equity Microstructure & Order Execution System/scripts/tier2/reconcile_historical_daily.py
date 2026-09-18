from pathlib import Path
import pandas as pd
import numpy as np


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"

MASTER_FILE = (
    DATA_DIR
    / "tier2_historical_universe"
    / "crsp_tier2_historical_security_master.csv"
)

DAILY_FILE = DATA_DIR / "crsp_daily_clean.csv"

OUTPUT_DIR = DATA_DIR / "tier2_historical_universe"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "crsp_tier2_historical_daily_reconciliation.csv"
)


# =============================================================================
# LOAD
# =============================================================================

print("=" * 80)
print("LOADING HISTORICAL SECURITY MASTER")
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
    "effective_start",
    "effective_end",
]

missing_master_columns = [
    col
    for col in required_master_columns
    if col not in master.columns
]

if missing_master_columns:
    raise ValueError(
        "Required columns missing from historical security master: "
        + ", ".join(missing_master_columns)
    )

master["effective_start"] = pd.to_datetime(
    master["effective_start"],
    errors="coerce"
)

master["effective_end"] = pd.to_datetime(
    master["effective_end"],
    errors="coerce"
)

print(f"Master rows: {len(master):,}")
print(f"Master PERMNOs: {master['permno'].nunique():,}")


# =============================================================================
# NORMALIZE MASTER DATES
# =============================================================================

master["securitybegdt"] = pd.to_datetime(
    master["securitybegdt"],
    errors="coerce"
)

master["securityenddt"] = pd.to_datetime(
    master["securityenddt"],
    errors="coerce"
)

master["effective_start"] = pd.to_datetime(
    master["effective_start"],
    errors="coerce"
)

master["effective_end"] = pd.to_datetime(
    master["effective_end"],
    errors="coerce"
)


# =============================================================================
# RESEARCH WINDOW
# =============================================================================

RESEARCH_START = pd.Timestamp("1993-01-01")
RESEARCH_END = pd.Timestamp("2018-12-31")


# =============================================================================
# BUILD SECURITY-LEVEL EXISTENCE WINDOWS
# =============================================================================

security_windows = (
    master
    .groupby("permno", as_index=False)
    .agg(
        security_begin=("securitybegdt", "min"),
        security_end=("securityenddt", "max"),
        classification_count=(
            "research_classification",
            "nunique"
        ),
    )
)

# Restrict the CRSP security existence window to the research period.
security_windows["historical_start"] = (
    security_windows["security_begin"]
    .clip(lower=RESEARCH_START)
)

security_windows["historical_end"] = (
    security_windows["security_end"]
    .clip(upper=RESEARCH_END)
)

security_windows["historical_interval_valid"] = (
    security_windows["historical_start"].notna()
    & security_windows["historical_end"].notna()
    & (
        security_windows["historical_start"]
        <= security_windows["historical_end"]
    )
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

# Normalize column names
daily.columns = [
    str(col).strip().lower()
    for col in daily.columns
]

print(f"Daily rows: {len(daily):,}")
print(f"Daily columns: {len(daily.columns):,}")

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

daily["dlycaldt"] = pd.to_datetime(
    daily["dlycaldt"],
    errors="coerce"
)

print(f"Daily PERMNOs: {daily['permno'].nunique():,}")
print(f"Daily first date: {daily['dlycaldt'].min()}")
print(f"Daily last date:  {daily['dlycaldt'].max()}")


# =============================================================================
# DAILY PERMNO COVERAGE
# =============================================================================

daily_permnos = set(
    daily["permno"].dropna().astype(int)
)

master_permnos = set(
    master["permno"].dropna().astype(int)
)


print("\n" + "=" * 80)
print("PERMNO RECONCILIATION")
print("=" * 80)

names_only = sorted(master_permnos - daily_permnos)
daily_only = sorted(daily_permnos - master_permnos)
matched = sorted(master_permnos & daily_permnos)

print(f"Historical master PERMNOs: {len(master_permnos)}")
print(f"Daily PERMNOs:             {len(daily_permnos)}")
print(f"Matched:                   {len(matched)}")
print(f"NAMES_ONLY:                {len(names_only)}")
print(f"DAILY_ONLY:                {len(daily_only)}")

if names_only:
    print("\nNAMES_ONLY:")
    print(names_only)

if daily_only:
    print("\nDAILY_ONLY:")
    print(daily_only)


# =============================================================================
# SECURITY-LEVEL DAILY COVERAGE
# =============================================================================

rows = []

for _, security in security_windows.iterrows():

    permno = int(security["permno"])

    d = daily.loc[
        daily["permno"] == permno
    ]

    rows.append({
        "permno": permno,

        "master_intervals": int(
            (
                master["permno"] == permno
            ).sum()
        ),

        "security_begin": security["security_begin"],

        "security_end": security["security_end"],

        "historical_start": security["historical_start"],

        "historical_end": security["historical_end"],

        "classification_count": security[
            "classification_count"
        ],

        "historical_interval_valid": security[
            "historical_interval_valid"
        ],

        "daily_first_dlycaldt": (
            d["dlycaldt"].min()
            if not d.empty
            else pd.NaT
        ),

        "daily_last_dlycaldt": (
            d["dlycaldt"].max()
            if not d.empty
            else pd.NaT
        ),

        "daily_rows": len(d),

        "daily_exists": not d.empty,
    })


coverage = pd.DataFrame(rows)

# =============================================================================
# COVERAGE FLAGS
# =============================================================================

coverage["daily_before_historical_start"] = (
    coverage["daily_first_dlycaldt"]
    < coverage["historical_start"]
)

coverage["daily_after_historical_end"] = (
    coverage["daily_last_dlycaldt"]
    > coverage["historical_end"]
)

coverage["history_temporally_consistent"] = ~(
    coverage["daily_before_historical_start"]
    | coverage["daily_after_historical_end"]
)

# =============================================================================
# TEMPORAL VALIDATION
# =============================================================================

coverage["daily_before_security_begin"] = (
    coverage["daily_first_dlycaldt"]
    < coverage["historical_start"]
)

coverage["daily_after_security_end"] = (
    coverage["daily_last_dlycaldt"]
    > coverage["historical_end"]
)

coverage["daily_within_security_life"] = ~(
    coverage["daily_before_security_begin"]
    | coverage["daily_after_security_end"]
)

coverage["history_temporally_consistent"] = (
    coverage["daily_exists"]
    & coverage["historical_interval_valid"]
    & coverage["daily_within_security_life"]
)

# =============================================================================
# CLASSIFICATION
# =============================================================================

def reconciliation_status(row):

    if not row["daily_exists"]:
        return "NAMES_ONLY"

    if not row["historical_interval_valid"]:
        return "INVALID_SECURITY_INTERVAL"

    if row["daily_before_security_begin"]:
        return "DAILY_BEFORE_SECURITY_BEGIN"

    if row["daily_after_security_end"]:
        return "DAILY_AFTER_SECURITY_END"

    return "TEMPORALLY_CONSISTENT"


coverage["reconciliation_status"] = coverage.apply(
    reconciliation_status,
    axis=1
)


# =============================================================================
# ADD DAILY-ONLY RECORDS
# =============================================================================

daily_only_rows = []

for permno in daily_only:

    d = daily.loc[
        daily["permno"] == permno
    ]

    daily_only_rows.append({
        "permno": permno,

        "master_intervals": 0,

        "security_begin": pd.NaT,
        "security_end": pd.NaT,

        "historical_start": pd.NaT,
        "historical_end": pd.NaT,

        "classification_count": 0,
        "historical_interval_valid": False,

        "daily_first_dlycaldt": (
            d["dlycaldt"].min()
            if not d.empty
            else pd.NaT
        ),

        "daily_last_dlycaldt": (
            d["dlycaldt"].max()
            if not d.empty
            else pd.NaT
        ),

        "daily_rows": len(d),
        "daily_exists": True,

        "daily_before_security_begin": False,
        "daily_after_security_end": False,
        "daily_within_security_life": False,

        "history_temporally_consistent": False,

        "reconciliation_status": "DAILY_ONLY",
    })


if daily_only_rows:

    daily_only_df = pd.DataFrame(
        daily_only_rows
    )

    coverage = pd.concat(
        [
            coverage,
            daily_only_df
        ],
        ignore_index=True
    )
# =============================================================================
# SAVE
# =============================================================================

coverage.to_csv(
    OUTPUT_FILE,
    index=False
)


# =============================================================================
# REPORT
# =============================================================================

print("\n" + "=" * 80)
print("TEMPORAL COVERAGE VALIDATION")
print("=" * 80)

print(
    f"Missing daily history: "
    f"{(~coverage['daily_exists']).sum()}"
)

print(
    f"Daily begins before historical start: "
    f"{coverage['daily_before_historical_start'].sum()}"
)

print(
    f"Daily ends after historical end: "
    f"{coverage['daily_after_historical_end'].sum()}"
)

print(
    f"Temporally consistent securities: "
    f"{coverage['history_temporally_consistent'].sum()}"
)

print("\nSaved:")
print(OUTPUT_FILE)