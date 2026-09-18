from pathlib import Path
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"

NAMES_FILE = DATA_DIR / "crsp_names_clean.csv"


# =============================================================================
# CONFIGURATION
# =============================================================================

OUTPUT_FILE = DATA_DIR / "crsp_tier2_names_schema_profile.csv"


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
print(f"Columns loaded: {len(df.columns):,}")
print(f"Unique PERMNOs: {df['permno'].nunique(dropna=True):,}"
      if "permno" in df.columns else "PERMNO column not found")


# =============================================================================
# SCHEMA PROFILE
# =============================================================================

print_header("CRSP NAMES COLUMN PROFILE")

records = []

for col in df.columns:
    records.append(
        {
            "column": col,
            "dtype": str(df[col].dtype),
            "non_null": int(df[col].notna().sum()),
            "missing": int(df[col].isna().sum()),
            "unique_non_null": int(df[col].nunique(dropna=True)),
        }
    )

profile = pd.DataFrame(records)

print(profile.to_string(index=False))


# =============================================================================
# KEY CLASSIFICATION FIELDS
# =============================================================================

classification_fields = [
    "securitytype",
    "securitysubtype",
    "sharetype",
    "issuertype",
    "usincflg",
    "primaryexch",
    "tradingstatusflg",
    "siccd",
]

print_header("CLASSIFICATION FIELD AVAILABILITY")

for col in classification_fields:
    if col in df.columns:
        print(
            f"FOUND  {col:<20} "
            f"unique={df[col].nunique(dropna=True):>6,} "
            f"missing={df[col].isna().sum():>8,}"
        )
    else:
        print(f"MISSING {col:<20}")


# =============================================================================
# SAVE
# =============================================================================

profile.to_csv(OUTPUT_FILE, index=False)

print_header("SAVING")

print(f"Saved: {OUTPUT_FILE}")
print("Schema profile completed successfully.")