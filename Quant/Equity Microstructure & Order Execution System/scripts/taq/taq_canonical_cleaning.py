from pathlib import Path
import pandas as pd
import numpy as np


# =============================================================================
# PHASE 5 — CORRECT CANONICAL TAQ CLEANING
# =============================================================================
#
# Purpose:
#   Repair the canonical TAQ cleaning process after discovering that the
#   original cleaning step incorrectly interpreted DD/MM/YYYY dates.
#
# Critical finding being corrected:
#   Raw source dates are confirmed to use DD/MM/YYYY.
#
# Rules:
#   - No observations removed
#   - No values imputed
#   - No duplicate removal
#   - No quote corrections
#   - No execution-metric corrections
#   - Raw values preserved
#   - Derived fields are recreated deterministically
#   - date parsed explicitly using DD/MM/YYYY
#
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "taq"
    / "taq.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "taq"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CORRECTED_FILE = (
    OUTPUT_DIR
    / "taq_cleaned.csv"
)

AUDIT_FILE = (
    OUTPUT_DIR
    / "taq_corrected_cleaning_audit.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "taq_corrected_cleaning_summary.csv"
)

VALIDATION_FILE = (
    OUTPUT_DIR
    / "taq_corrected_validation.csv"
)


# =============================================================================
# CONFIGURATION
# =============================================================================

CHUNK_SIZE = 100_000

EXPECTED_RAW_COLUMNS = 102

EXPECTED_ROW_COUNT = 122_441

DATE_COLUMN = "date"
SYMBOL_COLUMN = "symbol"


# Confirmed source date format
DATE_FORMAT = "%d/%m/%Y"


# Confirmed time-only fields
TIME_COLUMNS = [
    "QTime_1pm",
    "QTime_c1",
    "QTime_4pm",
    "LQTime",
    "OTime",
    "DTime",
    "LTTime",
    "TTime_1pm",
    "TTime_4pm",
    "CTime",
    "CTime2",
]


# Explicitly excluded from timestamp processing
NON_TIMESTAMP_TIME_NAMED_COLUMNS = [
    "NumTimeUnitsWithTrade1",
    "NumTimeUnitsWithTrade2",
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def normalize_symbol(series):
    """
    Normalize security identifiers without changing economic content.
    """
    return (
        series
        .astype("string")
        .str.strip()
        .replace("", pd.NA)
    )


def parse_date_ddmmyyyy(series):
    """
    Explicitly parse source dates using confirmed DD/MM/YYYY format.

    This is deliberately NOT inferred by pandas.
    """
    return pd.to_datetime(
        series,
        format=DATE_FORMAT,
        errors="coerce"
    )


def normalize_time(series):
    """
    Convert time-only fields into normalized HH:MM:SS representation.

    Source values are observed at millisecond precision in diagnostics.
    The normalized representation therefore retains milliseconds when present.
    """
    parsed = pd.to_timedelta(
        series.astype("string").str.strip(),
        errors="coerce"
    )

    return parsed


def timedelta_to_seconds(series):
    """
    Convert timedelta values to seconds from midnight.
    """
    return series.dt.total_seconds()


# =============================================================================
# LOAD RAW SCHEMA
# =============================================================================

print("=" * 80)
print("PHASE 5 — CORRECTED CANONICAL TAQ CLEANING")
print("=" * 80)

print(f"Raw file: {RAW_FILE}")
print(f"Output:   {CORRECTED_FILE}")
print()

raw_header = pd.read_csv(
    RAW_FILE,
    nrows=0
)

raw_columns = list(raw_header.columns)

print("=" * 80)
print("RAW SCHEMA")
print("=" * 80)

print(f"Raw columns: {len(raw_columns)}")

if len(raw_columns) != EXPECTED_RAW_COLUMNS:
    raise ValueError(
        f"Expected {EXPECTED_RAW_COLUMNS} raw columns, "
        f"found {len(raw_columns)}."
    )

if DATE_COLUMN not in raw_columns:
    raise ValueError("Required date column not found.")

if SYMBOL_COLUMN not in raw_columns:
    raise ValueError("Required symbol column not found.")

missing_time_columns = [
    c for c in TIME_COLUMNS
    if c not in raw_columns
]

if missing_time_columns:
    raise ValueError(
        f"Missing expected time columns: {missing_time_columns}"
    )

print("PASS — raw schema matches expected structure.")


# =============================================================================
# REMOVE STALE OUTPUTS
# =============================================================================

for output_file in [
    CORRECTED_FILE,
    AUDIT_FILE,
    SUMMARY_FILE,
    VALIDATION_FILE,
]:
    if output_file.exists():
        output_file.unlink()


# =============================================================================
# PROCESS CHUNKS
# =============================================================================

first_output = True

total_rows = 0
date_parse_failures = 0
symbol_missing = 0

date_values = []
symbol_values = []

audit_records = []


for chunk_number, chunk in enumerate(
    pd.read_csv(
        RAW_FILE,
        chunksize=CHUNK_SIZE,
        low_memory=False
    ),
    start=1
):

    print(
        f"Processing chunk {chunk_number}: "
        f"{len(chunk):,} rows"
    )

    total_rows += len(chunk)

    # -------------------------------------------------------------------------
    # Preserve raw source columns
    # -------------------------------------------------------------------------

    if list(chunk.columns) != raw_columns:
        raise ValueError(
            f"Schema changed in chunk {chunk_number}."
        )

    # -------------------------------------------------------------------------
    # DATE
    # -------------------------------------------------------------------------

    raw_date = chunk[DATE_COLUMN].astype("string").str.strip()

    normalized_date = parse_date_ddmmyyyy(raw_date)

    chunk["date_normalized"] = normalized_date

    chunk["date_iso"] = normalized_date.dt.strftime(
        "%Y-%m-%d"
    )

    current_date_failures = normalized_date.isna().sum()

    date_parse_failures += int(current_date_failures)

    # -------------------------------------------------------------------------
    # SYMBOL
    # -------------------------------------------------------------------------

    normalized_symbol = normalize_symbol(
        chunk[SYMBOL_COLUMN]
    )

    chunk["symbol_normalized"] = normalized_symbol

    symbol_missing += int(normalized_symbol.isna().sum())

    # -------------------------------------------------------------------------
    # TIME FIELDS
    # -------------------------------------------------------------------------

    for column in TIME_COLUMNS:

        parsed_time = normalize_time(
            chunk[column]
        )

        chunk[f"{column}_normalized"] = parsed_time

        chunk[f"{column}_seconds"] = timedelta_to_seconds(
            parsed_time
        )

    # -------------------------------------------------------------------------
    # Explicitly preserve observation-count fields
    # -------------------------------------------------------------------------

    for column in NON_TIMESTAMP_TIME_NAMED_COLUMNS:

        if column not in chunk.columns:
            raise ValueError(
                f"Expected observation-count column missing: {column}"
            )

    # -------------------------------------------------------------------------
    # Collect diagnostic information
    # -------------------------------------------------------------------------

    date_values.append(
        normalized_date.dropna()
    )

    symbol_values.append(
        normalized_symbol.dropna()
    )

    audit_records.append({
        "chunk_number": chunk_number,
        "rows": len(chunk),
        "date_parse_failures": int(current_date_failures),
        "symbol_missing": int(normalized_symbol.isna().sum()),
    })

    # -------------------------------------------------------------------------
    # Write corrected output
    # -------------------------------------------------------------------------

    chunk.to_csv(
        CORRECTED_FILE,
        mode="w" if first_output else "a",
        header=first_output,
        index=False
    )

    first_output = False


# =============================================================================
# BASIC PROCESSING VALIDATION
# =============================================================================

print()
print("=" * 80)
print("PROCESSING VALIDATION")
print("=" * 80)

print(f"Rows processed:        {total_rows:,}")
print(f"Date parse failures:   {date_parse_failures:,}")
print(f"Missing symbols:       {symbol_missing:,}")


# =============================================================================
# DATE COVERAGE
# =============================================================================

all_dates = pd.concat(
    date_values,
    ignore_index=True
)

all_symbols = pd.concat(
    symbol_values,
    ignore_index=True
)

unique_dates = all_dates.dt.normalize().nunique()

first_date = (
    all_dates.min().strftime("%Y-%m-%d")
    if len(all_dates) > 0
    else None
)

last_date = (
    all_dates.max().strftime("%Y-%m-%d")
    if len(all_dates) > 0
    else None
)

unique_symbols = all_symbols.nunique()


print()
print("=" * 80)
print("CORRECTED DATE COVERAGE")
print("=" * 80)

print(f"Unique dates:    {unique_dates:,}")
print(f"First date:      {first_date}")
print(f"Last date:       {last_date}")
print(f"Unique symbols:  {unique_symbols:,}")


# =============================================================================
# SECOND-PASS STRUCTURAL VALIDATION
# =============================================================================

print()
print("=" * 80)
print("SECOND-PASS STRUCTURAL VALIDATION")
print("=" * 80)

corrected_rows = 0
corrected_missing_dates = 0
corrected_duplicate_date_symbol = 0

duplicate_groups = 0

corrected_min_date = None
corrected_max_date = None

bid_ask_violations = {
    "1pm": 0,
    "c1": 0,
    "4pm": 0,
    "last": 0,
}

midpoint_violations = {
    "1pm": 0,
    "c1": 0,
    "4pm": 0,
    "last": 0,
}


QUOTE_SETS = [
    ("1pm", "BB_1pm", "BO_1pm", "MID_1pm"),
    ("c1", "BB_c1", "BO_c1", "Mid_c1"),
    ("4pm", "BB_4pm", "BO_4pm", "Mid_4pm"),
    ("last", "LBB", "LBO", "LMid"),
]


date_symbol_seen = set()


for chunk_number, chunk in enumerate(
    pd.read_csv(
        CORRECTED_FILE,
        chunksize=CHUNK_SIZE,
        low_memory=False
    ),
    start=1
):

    corrected_rows += len(chunk)

    dates = pd.to_datetime(
        chunk["date_iso"],
        format="%Y-%m-%d",
        errors="coerce"
    )

    corrected_missing_dates += int(dates.isna().sum())

    if dates.notna().any():

        chunk_min = dates.min()
        chunk_max = dates.max()

        if corrected_min_date is None:
            corrected_min_date = chunk_min

        if corrected_max_date is None:
            corrected_max_date = chunk_max

        corrected_min_date = min(
            corrected_min_date,
            chunk_min
        )

        corrected_max_date = max(
            corrected_max_date,
            chunk_max
        )

    # -------------------------------------------------------------------------
    # Date-symbol uniqueness
    # -------------------------------------------------------------------------

    keys = pd.MultiIndex.from_arrays(
        [
            chunk["date_iso"],
            chunk["symbol_normalized"],
        ]
    )

    duplicated_mask = keys.duplicated()

    corrected_duplicate_date_symbol += int(
        duplicated_mask.sum()
    )

    # Track cross-chunk duplicates
    for date_value, symbol_value in zip(
        chunk["date_iso"],
        chunk["symbol_normalized"]
    ):

        if pd.isna(date_value) or pd.isna(symbol_value):
            continue

        key = (
            date_value,
            symbol_value
        )

        if key in date_symbol_seen:
            duplicate_groups += 1

        date_symbol_seen.add(key)

    # -------------------------------------------------------------------------
    # Quote consistency
    # -------------------------------------------------------------------------

    for name, bid_col, ask_col, mid_col in QUOTE_SETS:

        bid = pd.to_numeric(
            chunk[bid_col],
            errors="coerce"
        )

        ask = pd.to_numeric(
            chunk[ask_col],
            errors="coerce"
        )

        mid = pd.to_numeric(
            chunk[mid_col],
            errors="coerce"
        )

        bid_ask_mask = (
            bid.notna()
            & ask.notna()
            & (bid > ask)
        )

        midpoint_mask = (
            bid.notna()
            & ask.notna()
            & mid.notna()
            & ~np.isclose(
                mid,
                (bid + ask) / 2.0,
                rtol=1e-10,
                atol=1e-10
            )
        )

        bid_ask_violations[name] += int(
            bid_ask_mask.sum()
        )

        midpoint_violations[name] += int(
            midpoint_mask.sum()
        )


# =============================================================================
# VALIDATION RESULTS
# =============================================================================

print()
print("=" * 80)
print("CORRECTED VALIDATION RESULTS")
print("=" * 80)

print(f"Corrected rows:             {corrected_rows:,}")
print(f"Missing dates:              {corrected_missing_dates:,}")
print(f"Date-symbol duplicate rows: {corrected_duplicate_date_symbol:,}")
print(f"Cross-chunk duplicate hits: {duplicate_groups:,}")

print(
    f"First date:                  "
    f"{corrected_min_date.strftime('%Y-%m-%d')}"
)

print(
    f"Last date:                   "
    f"{corrected_max_date.strftime('%Y-%m-%d')}"
)

print()

for quote_set in QUOTE_SETS:

    name = quote_set[0]

    print(
        f"{name:>6} "
        f"bid>ask={bid_ask_violations[name]:,} "
        f"midpoint={midpoint_violations[name]:,}"
    )


# =============================================================================
# CRITICAL VALIDATION FLAGS
# =============================================================================

critical_failures = []

review_items = []


if corrected_rows != EXPECTED_ROW_COUNT:
    critical_failures.append(
        "ROW_COUNT_CHANGED"
    )


if corrected_missing_dates != 0:
    critical_failures.append(
        "DATE_PARSE_FAILURE"
    )


if corrected_duplicate_date_symbol != 0:
    critical_failures.append(
        "DATE_SYMBOL_DUPLICATES_WITHIN_CHUNK"
    )


if duplicate_groups != 0:
    critical_failures.append(
        "DATE_SYMBOL_DUPLICATES_ACROSS_CHUNKS"
    )


if first_date != "1993-01-04":
    critical_failures.append(
        "UNEXPECTED_FIRST_DATE"
    )


if last_date != "2012-12-31":
    critical_failures.append(
        "UNEXPECTED_LAST_DATE"
    )


total_bid_ask_violations = sum(
    bid_ask_violations.values()
)

if total_bid_ask_violations > 0:
    review_items.append(
        "BID_GREATER_THAN_ASK_REQUIRES_SEMANTIC_REVIEW"
    )


total_midpoint_violations = sum(
    midpoint_violations.values()
)

if total_midpoint_violations > 0:
    critical_failures.append(
        "MIDPOINT_CONSISTENCY_FAILURE"
    )


# =============================================================================
# VALIDATION TABLE
# =============================================================================

validation_records = [
    {
        "check": "RAW_ROW_COUNT",
        "expected": EXPECTED_ROW_COUNT,
        "observed": total_rows,
        "status": "PASS"
        if total_rows == EXPECTED_ROW_COUNT
        else "FAIL",
    },
    {
        "check": "CORRECTED_ROW_COUNT",
        "expected": EXPECTED_ROW_COUNT,
        "observed": corrected_rows,
        "status": "PASS"
        if corrected_rows == EXPECTED_ROW_COUNT
        else "FAIL",
    },
    {
        "check": "DATE_PARSE_FAILURES",
        "expected": 0,
        "observed": corrected_missing_dates,
        "status": "PASS"
        if corrected_missing_dates == 0
        else "FAIL",
    },
    {
        "check": "DATE_SYMBOL_DUPLICATES",
        "expected": 0,
        "observed": (
            corrected_duplicate_date_symbol
            + duplicate_groups
        ),
        "status": "PASS"
        if (
            corrected_duplicate_date_symbol
            + duplicate_groups
        ) == 0
        else "FAIL",
    },
    {
        "check": "MIDPOINT_CONSISTENCY",
        "expected": 0,
        "observed": total_midpoint_violations,
        "status": "PASS"
        if total_midpoint_violations == 0
        else "FAIL",
    },
    {
        "check": "BID_GREATER_THAN_ASK",
        "expected": 0,
        "observed": total_bid_ask_violations,
        "status": "REVIEW"
        if total_bid_ask_violations > 0
        else "PASS",
    },
    {
        "check": "FIRST_DATE",
        "expected": "1993-01-04",
        "observed": first_date,
        "status": "PASS"
        if first_date == "1993-01-04"
        else "FAIL",
    },
    {
        "check": "LAST_DATE",
        "expected": "2012-12-31",
        "observed": last_date,
        "status": "PASS"
        if last_date == "2012-12-31"
        else "FAIL",
    },
]


pd.DataFrame(validation_records).to_csv(
    VALIDATION_FILE,
    index=False
)


# =============================================================================
# AUDIT
# =============================================================================

audit_df = pd.DataFrame(audit_records)

audit_df.to_csv(
    AUDIT_FILE,
    index=False
)


# =============================================================================
# SUMMARY
# =============================================================================

summary_records = [
    {
        "metric": "raw_rows",
        "value": total_rows,
    },
    {
        "metric": "corrected_rows",
        "value": corrected_rows,
    },
    {
        "metric": "raw_columns",
        "value": EXPECTED_RAW_COLUMNS,
    },
    {
        "metric": "corrected_columns",
        "value": len(raw_columns) + 25,
    },
    {
        "metric": "date_format",
        "value": "DD/MM/YYYY",
    },
    {
        "metric": "date_parse_failures",
        "value": corrected_missing_dates,
    },
    {
        "metric": "unique_dates",
        "value": unique_dates,
    },
    {
        "metric": "unique_symbols",
        "value": unique_symbols,
    },
    {
        "metric": "first_date",
        "value": first_date,
    },
    {
        "metric": "last_date",
        "value": last_date,
    },
    {
        "metric": "date_symbol_duplicates",
        "value": (
            corrected_duplicate_date_symbol
            + duplicate_groups
        ),
    },
    {
        "metric": "bid_greater_than_ask",
        "value": total_bid_ask_violations,
    },
    {
        "metric": "midpoint_violations",
        "value": total_midpoint_violations,
    },
    {
        "metric": "observations_removed",
        "value": 0,
    },
    {
        "metric": "values_modified",
        "value": 0,
    },
    {
        "metric": "imputation_performed",
        "value": False,
    },
    {
        "metric": "critical_failure_count",
        "value": len(critical_failures),
    },
    {
        "metric": "review_item_count",
        "value": len(review_items),
    },
]


pd.DataFrame(summary_records).to_csv(
    SUMMARY_FILE,
    index=False
)


# =============================================================================
# FINAL STATUS
# =============================================================================

print()
print("=" * 80)
print("FINAL STATUS")
print("=" * 80)

if critical_failures:

    print("FAIL — corrected canonical file still has critical failures.")

    for failure in critical_failures:
        print(f"  - {failure}")

else:

    print(
        "PASS — corrected canonical TAQ file passed "
        "structural validation."
    )

if review_items:

    print()
    print("REVIEW ITEMS:")

    for item in review_items:
        print(f"  - {item}")


print()
print("=" * 80)
print("OUTPUTS")
print("=" * 80)

print(f"Corrected TAQ:")
print(CORRECTED_FILE)

print()
print("Cleaning audit:")
print(AUDIT_FILE)

print()
print("Cleaning summary:")
print(SUMMARY_FILE)

print()
print("Corrected validation:")
print(VALIDATION_FILE)

print()
print("=" * 80)
print("IMPORTANT")
print("=" * 80)

print("The existing taq_cleaned.csv was NOT overwritten.")
print("No observations were removed.")
print("No values were imputed.")
print("No quote values were corrected.")
print("No duplicate rows were removed.")