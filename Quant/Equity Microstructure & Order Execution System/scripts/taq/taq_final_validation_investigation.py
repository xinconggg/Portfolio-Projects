from pathlib import Path
import pandas as pd
import numpy as np


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "taq"
    / "taq.csv"
)

CLEAN_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "taq"
    / "taq_cleaned.csv"
)

INTEGRATED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "taq"
    / "final_integrated_validation"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "taq"
    / "final_validation_investigation"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 100_000


# =============================================================================
# HELPERS
# =============================================================================

def normalize_symbol(series):
    return (
        series.astype("string")
        .str.strip()
        .str.upper()
    )


def parse_ddmmyyyy(series):
    """
    Explicitly parse confirmed source format:
        DD/MM/YYYY
    """
    return pd.to_datetime(
        series.astype("string").str.strip(),
        format="%d/%m/%Y",
        errors="coerce",
    )


def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def print_section(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


# =============================================================================
# LOAD CLEANED DATA
# =============================================================================

print_section("PHASE 5 — FINAL VALIDATION FAILURE INVESTIGATION")

print(f"Raw file:")
print(f"  {RAW_FILE}")

print(f"Clean file:")
print(f"  {CLEAN_FILE}")

print(f"Integrated validation directory:")
print(f"  {INTEGRATED_DIR}")

print(f"Investigation output directory:")
print(f"  {OUTPUT_DIR}")


print_section("LOADING CLEANED TAQ")

clean = pd.read_csv(
    CLEAN_FILE,
    low_memory=False,
)

print(f"Rows:       {len(clean):,}")
print(f"Columns:    {len(clean.columns):,}")

print()
print("Date-related columns:")
for c in clean.columns:
    if (
        "date" in c.lower()
        or "time" in c.lower()
    ):
        print(f"  - {c}")


# =============================================================================
# LOAD RAW DATE/SYMBOL REFERENCE
# =============================================================================

print_section("LOADING RAW DATE/SYMBOL REFERENCE")

raw_date_symbol_parts = []

for chunk_no, chunk in enumerate(
    pd.read_csv(
        RAW_FILE,
        usecols=["date", "symbol"],
        chunksize=CHUNK_SIZE,
        low_memory=False,
    ),
    start=1,
):
    print(
        f"Reading raw reference chunk {chunk_no}: "
        f"{len(chunk):,} rows"
    )

    chunk["raw_date_string"] = (
        chunk["date"]
        .astype("string")
        .str.strip()
    )

    chunk["raw_date_ddmmyyyy"] = parse_ddmmyyyy(
        chunk["raw_date_string"]
    )

    chunk["symbol_normalized"] = normalize_symbol(
        chunk["symbol"]
    )

    raw_date_symbol_parts.append(
        chunk[
            [
                "raw_date_string",
                "raw_date_ddmmyyyy",
                "symbol_normalized",
            ]
        ]
    )


raw_ref = pd.concat(
    raw_date_symbol_parts,
    ignore_index=True,
)

del raw_date_symbol_parts

print(f"Raw reference rows: {len(raw_ref):,}")


# =============================================================================
# CLEAN DATE COLUMNS
# =============================================================================

print_section("DATE COLUMN DIAGNOSTICS")

date_candidates = [
    "date",
    "date_normalized",
    "date_iso",
]

date_results = []

for col in date_candidates:

    if col not in clean.columns:
        continue

    parsed = pd.to_datetime(
        clean[col],
        errors="coerce",
    )

    date_results.append(
        {
            "column": col,
            "rows": len(clean),
            "missing_count": int(parsed.isna().sum()),
            "missing_rate": float(parsed.isna().mean()),
            "unique_dates": int(parsed.nunique(dropna=True)),
            "first_date": (
                parsed.min()
                if parsed.notna().any()
                else pd.NaT
            ),
            "last_date": (
                parsed.max()
                if parsed.notna().any()
                else pd.NaT
            ),
        }
    )


date_summary = pd.DataFrame(date_results)

print(date_summary.to_string(index=False))

date_summary.to_csv(
    OUTPUT_DIR / "date_column_summary.csv",
    index=False,
)


# =============================================================================
# DETERMINE CANONICAL CLEAN DATE
# =============================================================================

if "date_normalized" in clean.columns:

    clean_date = pd.to_datetime(
        clean["date_normalized"],
        errors="coerce",
    )

    canonical_date_column = "date_normalized"

elif "date_iso" in clean.columns:

    clean_date = pd.to_datetime(
        clean["date_iso"],
        errors="coerce",
    )

    canonical_date_column = "date_iso"

else:

    clean_date = pd.to_datetime(
        clean["date"],
        errors="coerce",
    )

    canonical_date_column = "date"


print()
print(
    f"Selected canonical clean date column: "
    f"{canonical_date_column}"
)


# =============================================================================
# SYMBOL NORMALIZATION
# =============================================================================

if "symbol_normalized" in clean.columns:

    clean_symbol = normalize_symbol(
        clean["symbol_normalized"]
    )

else:

    clean_symbol = normalize_symbol(
        clean["symbol"]
    )


# =============================================================================
# DUPLICATE TEST — CLEAN CANONICAL DATE
# =============================================================================

print_section(
    "DATE + SYMBOL DUPLICATE TEST — CLEAN CANONICAL DATE"
)

clean_key = pd.DataFrame(
    {
        "date": clean_date,
        "symbol": clean_symbol,
    }
)

clean_key["key_missing"] = (
    clean_key["date"].isna()
    | clean_key["symbol"].isna()
)

duplicate_mask = clean_key.duplicated(
    subset=["date", "symbol"],
    keep=False,
)

duplicate_extra_mask = clean_key.duplicated(
    subset=["date", "symbol"],
    keep="first",
)

clean_duplicate_groups = (
    clean_key.loc[
        duplicate_mask,
        ["date", "symbol"]
    ]
    .drop_duplicates()
    .shape[0]
)

clean_duplicate_rows = int(
    duplicate_mask.sum()
)

clean_duplicate_extra_rows = int(
    duplicate_extra_mask.sum()
)

print(
    f"Duplicate groups:      "
    f"{clean_duplicate_groups:,}"
)

print(
    f"Duplicate rows:        "
    f"{clean_duplicate_rows:,}"
)

print(
    f"Duplicate extra rows:  "
    f"{clean_duplicate_extra_rows:,}"
)


# =============================================================================
# RAW DUPLICATE TEST
# =============================================================================

print_section(
    "DUPLICATE TEST — RAW CONFIRMED DD/MM/YYYY DATE"
)

raw_key = raw_ref[
    [
        "raw_date_ddmmyyyy",
        "symbol_normalized",
    ]
].rename(
    columns={
        "raw_date_ddmmyyyy": "date",
        "symbol_normalized": "symbol",
    }
)

raw_duplicate_mask = raw_key.duplicated(
    subset=["date", "symbol"],
    keep=False,
)

raw_duplicate_extra_mask = raw_key.duplicated(
    subset=["date", "symbol"],
    keep="first",
)

raw_duplicate_groups = (
    raw_key.loc[
        raw_duplicate_mask,
        ["date", "symbol"]
    ]
    .drop_duplicates()
    .shape[0]
)

raw_duplicate_rows = int(
    raw_duplicate_mask.sum()
)

raw_duplicate_extra_rows = int(
    raw_duplicate_extra_mask.sum()
)

print(
    f"Duplicate groups:      "
    f"{raw_duplicate_groups:,}"
)

print(
    f"Duplicate rows:        "
    f"{raw_duplicate_rows:,}"
)

print(
    f"Duplicate extra rows:  "
    f"{raw_duplicate_extra_rows:,}"
)


# =============================================================================
# RAW/CLEAN DATE ALIGNMENT
# =============================================================================

print_section(
    "RAW ↔ CLEAN DATE ALIGNMENT"
)

if len(raw_ref) != len(clean):

    print(
        "CRITICAL: raw and clean row counts differ."
    )

else:

    alignment = pd.DataFrame(
        {
            "raw_date": raw_ref[
                "raw_date_ddmmyyyy"
            ].reset_index(drop=True),

            "clean_date": clean_date.reset_index(
                drop=True
            ),

            "raw_symbol": raw_ref[
                "symbol_normalized"
            ].reset_index(drop=True),

            "clean_symbol": clean_symbol.reset_index(
                drop=True
            ),
        }
    )

    alignment["date_match"] = (
        alignment["raw_date"]
        == alignment["clean_date"]
    )

    alignment["symbol_match"] = (
        alignment["raw_symbol"]
        == alignment["clean_symbol"]
    )

    alignment["full_key_match"] = (
        alignment["date_match"]
        & alignment["symbol_match"]
    )

    print(
        "Date matches:       "
        f"{alignment['date_match'].sum():,}"
        f" / {len(alignment):,}"
    )

    print(
        "Symbol matches:     "
        f"{alignment['symbol_match'].sum():,}"
        f" / {len(alignment):,}"
    )

    print(
        "Date+symbol matches:"
        f" {alignment['full_key_match'].sum():,}"
        f" / {len(alignment):,}"
    )

    alignment.to_csv(
        OUTPUT_DIR / "raw_clean_date_symbol_alignment.csv",
        index=False,
    )


# =============================================================================
# DATE DISTRIBUTION COMPARISON
# =============================================================================

print_section(
    "DATE DISTRIBUTION COMPARISON"
)

raw_dates = (
    raw_ref["raw_date_ddmmyyyy"]
    .dropna()
    .value_counts()
    .sort_index()
    .rename("raw_count")
)

clean_dates = (
    clean_date
    .dropna()
    .value_counts()
    .sort_index()
    .rename("clean_count")
)

date_distribution = pd.concat(
    [
        raw_dates,
        clean_dates,
    ],
    axis=1,
).fillna(0)

date_distribution["count_difference"] = (
    date_distribution["clean_count"]
    - date_distribution["raw_count"]
)

date_distribution["mismatch"] = (
    date_distribution["count_difference"] != 0
)

print(
    f"Dates with distribution mismatch: "
    f"{date_distribution['mismatch'].sum():,}"
)

print(
    f"Maximum absolute count difference: "
    f"{date_distribution['count_difference'].abs().max():,.0f}"
)

date_distribution.to_csv(
    OUTPUT_DIR / "date_distribution_comparison.csv"
)


# =============================================================================
# IDENTIFY DUPLICATE ROOT CAUSE
# =============================================================================

print_section(
    "DUPLICATE ROOT-CAUSE CLASSIFICATION"
)

root_cause = []

root_cause.append(
    {
        "check": "RAW_DATE_SYMBOL_DUPLICATES",
        "value": raw_duplicate_extra_rows,
        "status": (
            "PASS"
            if raw_duplicate_extra_rows == 0
            else "FAIL"
        ),
    }
)

root_cause.append(
    {
        "check": "CLEAN_DATE_SYMBOL_DUPLICATES",
        "value": clean_duplicate_extra_rows,
        "status": (
            "PASS"
            if clean_duplicate_extra_rows == 0
            else "FAIL"
        ),
    }
)

root_cause.append(
    {
        "check": "DATE_ALIGNMENT",
        "value": int(
            (~alignment["date_match"]).sum()
        ) if len(raw_ref) == len(clean)
        else np.nan,
        "status": (
            "PASS"
            if len(raw_ref) == len(clean)
            and alignment["date_match"].all()
            else "FAIL"
        ),
    }
)

root_cause_df = pd.DataFrame(root_cause)

print(
    root_cause_df.to_string(index=False)
)

root_cause_df.to_csv(
    OUTPUT_DIR / "duplicate_root_cause_classification.csv",
    index=False,
)


# =============================================================================
# LOAD INTEGRATED VALIDATION OUTPUTS
# =============================================================================

print_section(
    "INTEGRATED VALIDATION OUTPUT INSPECTION"
)

integrated_summary_file = (
    INTEGRATED_DIR
    / "taq_final_integrated_validation_summary.csv"
)

if integrated_summary_file.exists():

    integrated_summary = pd.read_csv(
        integrated_summary_file
    )

    print(
        integrated_summary.to_string(index=False)
    )

else:

    print(
        "Integrated validation summary not found."
    )


# =============================================================================
# DOMAIN SUMMARY
# =============================================================================

domain_file = (
    INTEGRATED_DIR
    / "taq_final_integrated_validation_by_domain.csv"
)

if domain_file.exists():

    print_section(
        "INTEGRATED REVIEW ITEMS BY DOMAIN"
    )

    domain_summary = pd.read_csv(
        domain_file
    )

    print(
        domain_summary.to_string(index=False)
    )

    domain_summary.to_csv(
        OUTPUT_DIR
        / "integrated_domain_summary_copy.csv",
        index=False,
    )


# =============================================================================
# STRUCTURAL CHECKS
# =============================================================================

structural_file = (
    INTEGRATED_DIR
    / "taq_final_structural_checks.csv"
)

if structural_file.exists():

    print_section(
        "INTEGRATED STRUCTURAL CHECKS"
    )

    structural = pd.read_csv(
        structural_file
    )

    print(
        structural.to_string(index=False)
    )

    structural.to_csv(
        OUTPUT_DIR
        / "integrated_structural_checks_copy.csv",
        index=False,
    )


# =============================================================================
# IDENTIFY 74,172 FAILURE SOURCE
# =============================================================================

print_section(
    "74,172 CRITICAL-FAILURE INVESTIGATION"
)

expected_failure_count = 74_172

if clean_duplicate_extra_rows == expected_failure_count:

    print(
        "CONFIRMED:"
    )

    print(
        "The 74,172 critical failures exactly match "
        "the cleaned date+symbol duplicate count."
    )

    duplicate_root_cause_confirmed = True

else:

    print(
        "NOT CONFIRMED:"
    )

    print(
        f"Expected critical failures: "
        f"{expected_failure_count:,}"
    )

    print(
        f"Observed clean duplicate extras: "
        f"{clean_duplicate_extra_rows:,}"
    )

    duplicate_root_cause_confirmed = False


# =============================================================================
# DUPLICATE EXAMPLES
# =============================================================================

if clean_duplicate_rows > 0:

    duplicate_examples = (
        clean.loc[
            duplicate_mask
        ].copy()
    )

    duplicate_examples.insert(
        0,
        "_clean_row_index",
        duplicate_examples.index,
    )

    duplicate_examples[
        [
            canonical_date_column,
            "symbol",
        ]
    ].to_csv(
        OUTPUT_DIR
        / "clean_duplicate_examples.csv",
        index=False,
    )


# =============================================================================
# FINAL DIAGNOSTIC STATUS
# =============================================================================

print_section(
    "FINAL INVESTIGATION STATUS"
)

if (
    raw_duplicate_extra_rows == 0
    and clean_duplicate_extra_rows == 0
    and len(raw_ref) == len(clean)
    and alignment["date_match"].all()
):

    print(
        "PASS — canonical date/symbol structure is internally consistent."
    )

    print(
        "The integrated validation failure is likely caused by "
        "validator logic/configuration rather than the canonical TAQ data."
    )

    investigation_status = "PASS"

elif duplicate_root_cause_confirmed:

    print(
        "FAIL — the current canonical TAQ still contains "
        "the 74,172 date/symbol duplicate failures."
    )

    print(
        "The integrated validator is detecting a real structural issue."
    )

    investigation_status = "FAIL"

else:

    print(
        "REVIEW — critical failures require additional "
        "validator-level investigation."
    )

    investigation_status = "REVIEW"


# =============================================================================
# INVESTIGATION SUMMARY
# =============================================================================

summary = pd.DataFrame(
    [
        {
            "input_rows": len(clean),
            "input_columns": len(clean.columns),
            "canonical_date_column": canonical_date_column,
            "raw_duplicate_extra_rows": raw_duplicate_extra_rows,
            "clean_duplicate_extra_rows": clean_duplicate_extra_rows,
            "clean_duplicate_groups": clean_duplicate_groups,
            "raw_unique_dates": raw_ref[
                "raw_date_ddmmyyyy"
            ].nunique(dropna=True),
            "clean_unique_dates": clean_date.nunique(
                dropna=True
            ),
            "date_mismatch_rows": (
                int((~alignment["date_match"]).sum())
                if len(raw_ref) == len(clean)
                else np.nan
            ),
            "symbol_mismatch_rows": (
                int((~alignment["symbol_match"]).sum())
                if len(raw_ref) == len(clean)
                else np.nan
            ),
            "expected_integrated_critical_failures": expected_failure_count,
            "duplicate_root_cause_confirmed": duplicate_root_cause_confirmed,
            "investigation_status": investigation_status,
            "observations_removed": 0,
            "values_modified": 0,
            "values_imputed": 0,
        }
    ]
)

summary.to_csv(
    OUTPUT_DIR
    / "taq_final_validation_investigation_summary.csv",
    index=False,
)


# =============================================================================
# FINAL MESSAGE
# =============================================================================

print()
print("=" * 80)
print("OUTPUTS")
print("=" * 80)

print(
    f"Date column summary:\n"
    f"  {OUTPUT_DIR / 'date_column_summary.csv'}"
)

print(
    f"Raw/clean date-symbol alignment:\n"
    f"  {OUTPUT_DIR / 'raw_clean_date_symbol_alignment.csv'}"
)

print(
    f"Date distribution comparison:\n"
    f"  {OUTPUT_DIR / 'date_distribution_comparison.csv'}"
)

print(
    f"Duplicate root-cause classification:\n"
    f"  {OUTPUT_DIR / 'duplicate_root_cause_classification.csv'}"
)

print(
    f"Investigation summary:\n"
    f"  {OUTPUT_DIR / 'taq_final_validation_investigation_summary.csv'}"
)

print(
    f"Output directory:\n"
    f"  {OUTPUT_DIR}"
)

print()
print("=" * 80)
print("STATUS")
print("=" * 80)

print(
    f"{investigation_status} — "
    "final integrated validation failure investigation completed."
)

print()
print("IMPORTANT:")
print("No observations were removed.")
print("No values were modified.")
print("No imputation was performed.")
print("No canonical TAQ file was overwritten.")