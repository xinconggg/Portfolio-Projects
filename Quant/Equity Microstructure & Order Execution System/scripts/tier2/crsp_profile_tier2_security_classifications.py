from pathlib import Path
import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "crsp"

NAMES_FILE = DATA_DIR / "crsp_names_clean.csv"

OUTPUT_DIR = DATA_DIR / "tier2_classification_profiles"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# HELPERS
# =============================================================================

def print_header(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def profile_field(df: pd.DataFrame, field: str) -> pd.DataFrame:
    result = (
        df.groupby(field, dropna=False)
        .agg(
            names_rows=(field, "size"),
            unique_permnos=("permno", "nunique"),
        )
        .reset_index()
        .sort_values(
            ["unique_permnos", "names_rows"],
            ascending=[False, False],
        )
    )

    return result


# =============================================================================
# LOAD
# =============================================================================

print_header("LOADING CRSP NAMES")

if not NAMES_FILE.exists():
    raise FileNotFoundError(f"File not found: {NAMES_FILE}")

df = pd.read_csv(NAMES_FILE, low_memory=False)
df.columns = [str(col).strip().lower() for col in df.columns]

print(f"Rows loaded: {len(df):,}")
print(f"Unique PERMNOs: {df['permno'].nunique(dropna=True):,}")


# =============================================================================
# CLASSIFICATION FIELDS
# =============================================================================

fields = [
    "securitytype",
    "securitysubtype",
    "sharetype",
    "issuertype",
    "usincflg",
    "primaryexch",
    "tradingstatusflg",
]


# =============================================================================
# PROFILE INDIVIDUAL FIELDS
# =============================================================================

for field in fields:

    if field not in df.columns:
        print(f"WARNING: {field} not found")
        continue

    print_header(f"PROFILE: {field.upper()}")

    result = profile_field(df, field)

    print(result.to_string(index=False))

    output_file = OUTPUT_DIR / f"crsp_tier2_profile_{field}.csv"

    result.to_csv(output_file, index=False)

    print(f"\nSaved: {output_file}")


# =============================================================================
# COMBINED SECURITY CLASSIFICATION PROFILE
# =============================================================================

available = [
    field
    for field in fields
    if field in df.columns
]

print_header("COMBINED SECURITY CLASSIFICATION PROFILE")

combined = (
    df.groupby(available, dropna=False)
    .agg(
        names_rows=("permno", "size"),
        unique_permnos=("permno", "nunique"),
    )
    .reset_index()
    .sort_values(
        ["unique_permnos", "names_rows"],
        ascending=[False, False],
    )
)

print(combined.to_string(index=False))

combined_file = OUTPUT_DIR / "crsp_tier2_security_classification_combinations.csv"

combined.to_csv(combined_file, index=False)

print(f"\nSaved: {combined_file}")


# =============================================================================
# BASIC SECURITY-LEVEL CLASSIFICATION SUMMARY
# =============================================================================

print_header("PERMNO-LEVEL CLASSIFICATION COVERAGE")

security_summary = (
    df.groupby("permno", dropna=False)
    .agg(
        names_rows=("permno", "size"),
        permco_count=("permco", "nunique") if "permco" in df.columns else ("permno", "size"),
        securitytype_count=("securitytype", "nunique") if "securitytype" in df.columns else ("permno", "size"),
        securitysubtype_count=("securitysubtype", "nunique") if "securitysubtype" in df.columns else ("permno", "size"),
        sharetype_count=("sharetype", "nunique") if "sharetype" in df.columns else ("permno", "size"),
        issuertype_count=("issuertype", "nunique") if "issuertype" in df.columns else ("permno", "size"),
    )
    .reset_index()
)

print(security_summary.describe(include="all").to_string())

security_file = OUTPUT_DIR / "crsp_tier2_permno_classification_summary.csv"

security_summary.to_csv(security_file, index=False)

print(f"\nSaved: {security_file}")

print_header("CLASSIFICATION PROFILING COMPLETE")