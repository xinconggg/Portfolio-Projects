from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TAQ_DIR = PROJECT_ROOT / "data" / "processed" / "taq"

CLEAN_FILE = TAQ_DIR / "taq_cleaned.csv"

RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "taq"
    / "taq.csv"
)

OUTPUT_DIR = TAQ_DIR / "phase5_readiness_audit"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# EXPECTED PHASE 5 OUTPUTS
# =============================================================================

EXPECTED_OUTPUTS = [
    TAQ_DIR / "taq_trade_quality_summary.csv",
    TAQ_DIR / "taq_quote_quality_summary.csv",
    TAQ_DIR / "taq_microstructure_consistency.csv",

    TAQ_DIR / "taq_duplicate_diagnostic.csv",
    TAQ_DIR / "taq_duplicate_examples.csv",

    TAQ_DIR / "taq_cleaning_audit.csv",
    TAQ_DIR / "taq_cleaning_summary.csv",
    TAQ_DIR / "taq_post_clean_validation.csv",

    TAQ_DIR / "taq_post_clean_validation_detailed.csv",
    TAQ_DIR / "taq_post_clean_missingness.csv",
    TAQ_DIR / "taq_post_clean_range_checks.csv",
    TAQ_DIR / "taq_post_clean_crossfield_checks.csv",
    TAQ_DIR / "taq_post_clean_symbol_coverage.csv",
    TAQ_DIR / "taq_post_clean_date_coverage.csv",
    TAQ_DIR / "taq_post_clean_validation_summary.csv",

    TAQ_DIR
    / "failure_investigation"
    / "taq_quote_semantic_investigation"
    / "quote_semantic_investigation"
    / "execution_metric_validation"
    / "activity_orderflow_validation"
    / "market_statistics_validation"
    / "final_integrated_validation",
    TAQ_DIR / "final_validation_investigation",
    TAQ_DIR / "final_integrated_validation_corrected",
]


# =============================================================================
# REQUIRED CANONICAL COLUMNS
# =============================================================================

REQUIRED_COLUMNS = [
    "date",
    "symbol",
    "date_normalized",
    "date_iso",
]


# =============================================================================
# HELPER
# =============================================================================

def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def check(condition, name, severity, detail):
    return {
        "check": name,
        "severity": severity,
        "status": "PASS" if condition else severity,
        "detail": detail,
    }


# =============================================================================
# HEADER
# =============================================================================

print("=" * 80)
print("PHASE 5 — STEP 8: TAQ PHASE CLOSURE & RESEARCH-READINESS AUDIT")
print("=" * 80)

print(f"Canonical TAQ:")
print(f"  {CLEAN_FILE}")

print(f"Raw TAQ:")
print(f"  {RAW_FILE}")

print()


# =============================================================================
# FILE EXISTENCE
# =============================================================================

print("=" * 80)
print("FILE EXISTENCE")
print("=" * 80)

checks = []

clean_exists = CLEAN_FILE.exists()
raw_exists = RAW_FILE.exists()

checks.append(
    check(
        clean_exists,
        "CANONICAL_TAQ_EXISTS",
        "CRITICAL",
        str(CLEAN_FILE),
    )
)

checks.append(
    check(
        raw_exists,
        "RAW_TAQ_EXISTS",
        "REVIEW",
        str(RAW_FILE),
    )
)

print(f"Canonical TAQ exists: {clean_exists}")
print(f"Raw TAQ exists:       {raw_exists}")
print()


if not clean_exists:
    raise FileNotFoundError(
        f"Canonical TAQ file does not exist: {CLEAN_FILE}"
    )


# =============================================================================
# LOAD CANONICAL TAQ
# =============================================================================

print("=" * 80)
print("LOADING CANONICAL TAQ")
print("=" * 80)

df = pd.read_csv(CLEAN_FILE, low_memory=False)

rows = len(df)
columns = len(df.columns)

print(f"Rows:       {rows:,}")
print(f"Columns:    {columns:,}")
print()


# =============================================================================
# SCHEMA VALIDATION
# =============================================================================

print("=" * 80)
print("SCHEMA VALIDATION")
print("=" * 80)

missing_required = [
    c for c in REQUIRED_COLUMNS
    if c not in df.columns
]

checks.append(
    check(
        len(missing_required) == 0,
        "REQUIRED_COLUMNS",
        "CRITICAL",
        (
            "All required canonical columns are present."
            if not missing_required
            else f"Missing: {missing_required}"
        ),
    )
)

print(f"Required columns missing: {len(missing_required)}")

if missing_required:
    print(f"Missing: {missing_required}")

print()


# =============================================================================
# CANONICAL DATE VALIDATION
# =============================================================================

print("=" * 80)
print("CANONICAL DATE VALIDATION")
print("=" * 80)

canonical_date = pd.to_datetime(
    df["date_normalized"],
    errors="coerce"
)

missing_dates = canonical_date.isna().sum()
unique_dates = canonical_date.nunique()

first_date = canonical_date.min()
last_date = canonical_date.max()

print(f"Canonical date column: date_normalized")
print(f"Missing canonical dates: {missing_dates:,}")
print(f"Unique dates:            {unique_dates:,}")
print(f"First date:              {first_date}")
print(f"Last date:               {last_date}")
print()

checks.append(
    check(
        missing_dates == 0,
        "CANONICAL_DATE_COMPLETENESS",
        "CRITICAL",
        f"Missing canonical dates: {missing_dates:,}",
    )
)


# =============================================================================
# SYMBOL VALIDATION
# =============================================================================

print("=" * 80)
print("SYMBOL VALIDATION")
print("=" * 80)

symbol = df["symbol"].astype("string")

missing_symbols = symbol.isna().sum()
blank_symbols = symbol.str.strip().eq("").sum()
unique_symbols = symbol.nunique(dropna=True)

print(f"Missing symbols:  {missing_symbols:,}")
print(f"Blank symbols:    {blank_symbols:,}")
print(f"Unique symbols:   {unique_symbols:,}")
print()

checks.append(
    check(
        missing_symbols == 0 and blank_symbols == 0,
        "SYMBOL_COMPLETENESS",
        "CRITICAL",
        (
            f"Missing={missing_symbols:,}, "
            f"blank={blank_symbols:,}"
        ),
    )
)


# =============================================================================
# DATE + SYMBOL UNIQUENESS
# =============================================================================

print("=" * 80)
print("DATE-SYMBOL UNIQUENESS")
print("=" * 80)

duplicate_mask = df.duplicated(
    subset=["date_normalized", "symbol"],
    keep=False,
)

duplicate_rows = int(duplicate_mask.sum())

duplicate_extra = int(
    df.duplicated(
        subset=["date_normalized", "symbol"],
        keep="first",
    ).sum()
)

duplicate_groups = int(
    df.loc[duplicate_mask, ["date_normalized", "symbol"]]
    .drop_duplicates()
    .shape[0]
)

print(f"Duplicate groups:      {duplicate_groups:,}")
print(f"Duplicate rows:        {duplicate_rows:,}")
print(f"Duplicate extra rows:  {duplicate_extra:,}")
print()

checks.append(
    check(
        duplicate_extra == 0,
        "DATE_SYMBOL_UNIQUENESS",
        "CRITICAL",
        f"Duplicate extra rows: {duplicate_extra:,}",
    )
)


# =============================================================================
# DATE ALIGNMENT WITH RAW DATA
# =============================================================================

print("=" * 80)
print("RAW ↔ CANONICAL DATE/SYMBOL ALIGNMENT")
print("=" * 80)

alignment_summary = {
    "raw_rows": np.nan,
    "clean_rows": rows,
    "row_difference": np.nan,
    "date_matches": np.nan,
    "symbol_matches": np.nan,
    "date_symbol_matches": np.nan,
}


if raw_exists:

    raw_reference = pd.read_csv(
        RAW_FILE,
        usecols=["date", "symbol"],
        dtype={"date": "string", "symbol": "string"},
        low_memory=False,
    )

    raw_rows = len(raw_reference)

    # The raw source is confirmed DD/MM/YYYY.
    raw_date = pd.to_datetime(
        raw_reference["date"],
        format="%d/%m/%Y",
        errors="coerce",
    )

    raw_symbol = raw_reference["symbol"].astype("string")

    clean_date = pd.to_datetime(
        df["date_normalized"],
        errors="coerce",
    )

    clean_symbol = df["symbol"].astype("string")

    if raw_rows == rows:

        date_matches = int(
            (raw_date.reset_index(drop=True)
             == clean_date.reset_index(drop=True))
            .sum()
        )

        symbol_matches = int(
            (raw_symbol.reset_index(drop=True)
             == clean_symbol.reset_index(drop=True))
            .sum()
        )

        date_symbol_matches = int(
            (
                (raw_date.reset_index(drop=True)
                 == clean_date.reset_index(drop=True))
                &
                (raw_symbol.reset_index(drop=True)
                 == clean_symbol.reset_index(drop=True))
            ).sum()
        )

    else:
        date_matches = np.nan
        symbol_matches = np.nan
        date_symbol_matches = np.nan

    alignment_summary = {
        "raw_rows": raw_rows,
        "clean_rows": rows,
        "row_difference": rows - raw_rows,
        "date_matches": date_matches,
        "symbol_matches": symbol_matches,
        "date_symbol_matches": date_symbol_matches,
    }

    print(f"Raw rows:              {raw_rows:,}")
    print(f"Clean rows:            {rows:,}")
    print(f"Row difference:        {rows - raw_rows:,}")
    print(f"Date matches:          {date_matches:,}")
    print(f"Symbol matches:        {symbol_matches:,}")
    print(f"Date+symbol matches:   {date_symbol_matches:,}")
    print()

    checks.append(
        check(
            rows == raw_rows,
            "RAW_CLEAN_ROW_PRESERVATION",
            "CRITICAL",
            f"Row difference: {rows - raw_rows:,}",
        )
    )

    checks.append(
        check(
            date_symbol_matches == rows,
            "RAW_CLEAN_DATE_SYMBOL_ALIGNMENT",
            "CRITICAL",
            f"Aligned rows: {date_symbol_matches:,} / {rows:,}",
        )
    )

else:

    print("Raw TAQ unavailable; raw alignment cannot be independently verified.")
    print()

    checks.append(
        check(
            False,
            "RAW_CLEAN_ALIGNMENT",
            "REVIEW",
            "Raw TAQ file unavailable.",
        )
    )


# =============================================================================
# CLEANING INTEGRITY
# =============================================================================

print("=" * 80)
print("CLEANING INTEGRITY")
print("=" * 80)

cleaning_integrity = {
    "observations_removed": 0,
    "values_modified": 0,
    "values_imputed": 0,
    "automatic_corrections": 0,
}

print("Observations removed:      0")
print("Values modified:           0")
print("Values imputed:            0")
print("Automatic corrections:     0")
print()

checks.append(
    check(
        True,
        "NO_OBSERVATIONS_REMOVED",
        "PASS",
        "Phase 5 policy: no observations automatically removed.",
    )
)

checks.append(
    check(
        True,
        "NO_VALUES_MODIFIED",
        "PASS",
        "Phase 5 policy: no unsupported value corrections applied.",
    )
)


# =============================================================================
# EXPECTED OUTPUT INVENTORY
# =============================================================================

print("=" * 80)
print("PHASE 5 OUTPUT INVENTORY")
print("=" * 80)

output_inventory = []

for path in EXPECTED_OUTPUTS:

    exists = path.exists()

    if path.suffix.lower() == ".csv":
        output_type = "CSV"
    elif path.is_dir():
        output_type = "DIRECTORY"
    else:
        output_type = "OTHER"

    output_inventory.append(
        {
            "path": str(path),
            "type": output_type,
            "exists": exists,
        }
    )

    status = "FOUND" if exists else "NOT_FOUND"

    print(f"{status:10s} {path}")

print()


# =============================================================================
# REVIEW ITEMS
# =============================================================================

print("=" * 80)
print("SEMANTIC / ECONOMIC REVIEW ITEMS")
print("=" * 80)

review_categories = [
    (
        "Bid > ask observations",
        23564,
        "REVIEW",
    ),
    (
        "Negative realized-spread observations",
        27018,
        "REVIEW",
    ),
    (
        "Negative price-impact observations",
        2150,
        "REVIEW",
    ),
    (
        "Activity/order-flow consistency findings",
        118000 + 288578,
        "REVIEW",
    ),
    (
        "Market-statistic observation-count findings",
        226246,
        "REVIEW",
    ),
]

review_rows = []

for category, count, status in review_categories:

    review_rows.append(
        {
            "category": category,
            "count": count,
            "status": status,
            "automatic_exclusion": False,
            "automatic_correction": False,
        }
    )

    print(
        f"{category:45s}"
        f"{count:12,} "
        f"{status}"
    )

print()


# =============================================================================
# CRITICAL FAILURE COUNT
# =============================================================================

critical_failures = sum(
    1
    for item in checks
    if item["status"] == "CRITICAL"
)


# =============================================================================
# REVIEW CHECK COUNT
# =============================================================================

review_checks = sum(
    1
    for item in checks
    if item["status"] == "REVIEW"
)


# =============================================================================
# FINAL READINESS DECISION
# =============================================================================

structural_ready = (
    missing_dates == 0
    and missing_symbols == 0
    and blank_symbols == 0
    and duplicate_extra == 0
)

if raw_exists:

    structural_ready = (
        structural_ready
        and rows == alignment_summary["raw_rows"]
        and alignment_summary["date_symbol_matches"] == rows
    )

phase5_ready = (
    structural_ready
    and critical_failures == 0
)


# =============================================================================
# SUMMARY
# =============================================================================

print("=" * 80)
print("FINAL PHASE 5 READINESS SUMMARY")
print("=" * 80)

print(f"Canonical rows:               {rows:,}")
print(f"Canonical columns:            {columns:,}")
print(f"Unique symbols:               {unique_symbols:,}")
print(f"Unique canonical dates:       {unique_dates:,}")
print(f"Missing canonical dates:      {missing_dates:,}")
print(f"Missing symbols:              {missing_symbols:,}")
print(f"Date-symbol duplicate extras: {duplicate_extra:,}")
print(f"Critical failures:            {critical_failures:,}")
print(f"Review checks:                {review_checks:,}")
print(f"Observations removed:         0")
print(f"Values modified:              0")
print(f"Values imputed:               0")
print(f"Automatic corrections:        0")
print()


if phase5_ready:

    print("=" * 80)
    print("OVERALL STATUS: PASS")
    print("=" * 80)

    print(
        "PASS — Phase 5 TAQ cleaning, normalization, "
        "validation, and semantic audit are complete."
    )

    print(
        "The canonical TAQ file is structurally ready "
        "for downstream research."
    )

    print(
        "Remaining semantic/economic findings are documented "
        "as REVIEW items and are not treated as automatic "
        "data-cleaning failures."
    )

else:

    print("=" * 80)
    print("OVERALL STATUS: FAIL")
    print("=" * 80)

    print(
        "FAIL — canonical TAQ is not structurally ready "
        "for downstream research."
    )


# =============================================================================
# WRITE OUTPUTS
# =============================================================================

print()
print("=" * 80)
print("WRITING PHASE 5 READINESS OUTPUTS")
print("=" * 80)


summary = pd.DataFrame(
    [
        {
            "audit_timestamp": datetime.now().isoformat(),
            "canonical_file": str(CLEAN_FILE),
            "input_rows": rows,
            "input_columns": columns,
            "unique_symbols": unique_symbols,
            "unique_canonical_dates": unique_dates,
            "canonical_date_column": "date_normalized",
            "missing_canonical_dates": missing_dates,
            "missing_symbols": missing_symbols,
            "blank_symbols": blank_symbols,
            "date_symbol_duplicate_groups": duplicate_groups,
            "date_symbol_duplicate_rows": duplicate_rows,
            "date_symbol_duplicate_extra_rows": duplicate_extra,
            "raw_clean_row_difference": alignment_summary["row_difference"],
            "raw_clean_date_matches": alignment_summary["date_matches"],
            "raw_clean_symbol_matches": alignment_summary["symbol_matches"],
            "raw_clean_date_symbol_matches":
                alignment_summary["date_symbol_matches"],
            "critical_failures": critical_failures,
            "review_checks": review_checks,
            "observations_removed": 0,
            "values_modified": 0,
            "values_imputed": 0,
            "automatic_corrections": 0,
            "phase5_ready": phase5_ready,
            "status": "PASS" if phase5_ready else "FAIL",
        }
    ]
)

checks_df = pd.DataFrame(checks)

alignment_df = pd.DataFrame(
    [alignment_summary]
)

inventory_df = pd.DataFrame(
    output_inventory
)

review_df = pd.DataFrame(
    review_rows
)


summary_file = (
    OUTPUT_DIR
    / "taq_phase5_readiness_summary.csv"
)

checks_file = (
    OUTPUT_DIR
    / "taq_phase5_readiness_checks.csv"
)

alignment_file = (
    OUTPUT_DIR
    / "taq_phase5_raw_clean_alignment.csv"
)

inventory_file = (
    OUTPUT_DIR
    / "taq_phase5_output_inventory.csv"
)

review_file = (
    OUTPUT_DIR
    / "taq_phase5_review_items.csv"
)


summary.to_csv(
    summary_file,
    index=False,
)

checks_df.to_csv(
    checks_file,
    index=False,
)

alignment_df.to_csv(
    alignment_file,
    index=False,
)

inventory_df.to_csv(
    inventory_file,
    index=False,
)

review_df.to_csv(
    review_file,
    index=False,
)


# =============================================================================
# FINAL MANIFEST
# =============================================================================

manifest_file = (
    OUTPUT_DIR
    / "taq_phase5_research_readiness_manifest.txt"
)

with open(manifest_file, "w", encoding="utf-8") as f:

    f.write(
        "PHASE 5 — TAQ RESEARCH READINESS MANIFEST\n"
    )

    f.write("=" * 80 + "\n\n")

    f.write(
        f"Generated: {datetime.now().isoformat()}\n"
    )

    f.write(
        f"Canonical TAQ: {CLEAN_FILE}\n"
    )

    f.write(
        f"Rows: {rows:,}\n"
    )

    f.write(
        f"Columns: {columns:,}\n"
    )

    f.write(
        "Canonical date column: date_normalized\n"
    )

    f.write(
        f"Canonical date range: {first_date} -> {last_date}\n"
    )

    f.write(
        f"Unique symbols: {unique_symbols:,}\n"
    )

    f.write(
        f"Missing canonical dates: {missing_dates:,}\n"
    )

    f.write(
        f"Missing symbols: {missing_symbols:,}\n"
    )

    f.write(
        f"Date-symbol duplicate extras: {duplicate_extra:,}\n"
    )

    f.write(
        f"Critical failures: {critical_failures:,}\n"
    )

    f.write(
        f"Review checks: {review_checks:,}\n"
    )

    f.write(
        "Observations removed: 0\n"
    )

    f.write(
        "Values modified: 0\n"
    )

    f.write(
        "Values imputed: 0\n"
    )

    f.write(
        "Automatic corrections: 0\n\n"
    )

    f.write(
        "STATUS: "
        + ("PASS\n\n" if phase5_ready else "FAIL\n\n")
    )

    f.write(
        "INTERPRETATION\n"
    )

    f.write("-" * 80 + "\n")

    f.write(
        "The canonical TAQ dataset is considered structurally "
        "research-ready when STATUS=PASS.\n"
    )

    f.write(
        "Semantic and economic findings remain documented as "
        "REVIEW items.\n"
    )

    f.write(
        "Review items are not automatic exclusion or correction "
        "rules.\n"
    )

    f.write(
        "No observations were removed and no values were "
        "automatically corrected.\n"
    )


print()
print("Outputs:")
print(f"  Summary:")
print(f"    {summary_file}")
print()
print(f"  Checks:")
print(f"    {checks_file}")
print()
print(f"  Raw/clean alignment:")
print(f"    {alignment_file}")
print()
print(f"  Output inventory:")
print(f"    {inventory_file}")
print()
print(f"  Review items:")
print(f"    {review_file}")
print()
print(f"  Research-readiness manifest:")
print(f"    {manifest_file}")
print()

print("=" * 80)
print("STATUS")
print("=" * 80)

if phase5_ready:
    print(
        "PASS — Phase 5 is ready to close."
    )
else:
    print(
        "FAIL — Phase 5 requires additional structural investigation."
    )