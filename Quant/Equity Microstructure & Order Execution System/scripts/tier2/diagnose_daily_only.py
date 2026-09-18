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

DAILY_FILE = DATA_DIR / "crsp_daily_clean.csv"

OUTPUT_FILE = (
    TIER2_DIR /
    "crsp_tier2_daily_only_diagnostic.csv"
)


# =============================================================================
# LOAD MASTER
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

if "permno" not in master.columns:
    raise ValueError(
        "PERMNO column missing from Tier 2 historical security master."
    )

master["permno"] = pd.to_numeric(
    master["permno"],
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

print(f"Daily rows: {len(daily):,}")

print("\nDaily columns:")
print(daily.columns.tolist())


# =============================================================================
# REQUIRED COLUMN VALIDATION
# =============================================================================

required_daily_columns = [
    "permno",
    "dlycaldt",
]

missing_columns = [
    col
    for col in required_daily_columns
    if col not in daily.columns
]

if missing_columns:
    raise ValueError(
        "Required CRSP Daily columns missing: "
        + ", ".join(missing_columns)
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

daily_permnos = set(
    daily["permno"]
    .dropna()
    .astype(int)
)

print(f"Daily PERMNOs: {len(daily_permnos):,}")
print(f"Daily first date: {daily['dlycaldt'].min()}")
print(f"Daily last date:  {daily['dlycaldt'].max()}")


# =============================================================================
# PERMNO RECONCILIATION
# =============================================================================

daily_only = sorted(
    daily_permnos -
    master_permnos
)


print("\n" + "=" * 80)
print("DAILY_ONLY PERMNO DIAGNOSTIC")
print("=" * 80)

print(
    f"DAILY_ONLY securities: "
    f"{len(daily_only):,}"
)

print(daily_only)


# =============================================================================
# DAILY SUMMARY
# =============================================================================

summary = (
    daily[
        daily["permno"].isin(daily_only)
    ]
    .groupby(
        "permno",
        as_index=False
    )
    .agg(
        daily_rows=("permno", "size"),
        daily_start=("dlycaldt", "min"),
        daily_end=("dlycaldt", "max"),
    )
)


# =============================================================================
# SAVE
# =============================================================================

summary.to_csv(
    OUTPUT_FILE,
    index=False
)


# =============================================================================
# REPORT
# =============================================================================

print("\n" + "=" * 80)
print("DAILY_ONLY SUMMARY")
print("=" * 80)

if summary.empty:

    print(
        "PASS: No DAILY_ONLY PERMNOs detected."
    )

else:

    print(
        summary.to_string(index=False)
    )


print(f"\nSaved: {OUTPUT_FILE}")