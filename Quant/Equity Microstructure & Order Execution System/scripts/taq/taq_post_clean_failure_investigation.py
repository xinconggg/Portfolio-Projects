from pathlib import Path
import pandas as pd
import numpy as np


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

CLEAN_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "taq"
    / "taq_cleaned.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "taq"
    / "failure_investigation"
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


def parse_raw_date_correctly(series):
    """
    Raw TAQ date is confirmed to be DD/MM/YYYY.
    """
    return pd.to_datetime(
        series,
        format="%d/%m/%Y",
        errors="coerce"
    )


def parse_clean_date(series):
    """
    Preserve the cleaned file's existing interpretation.
    We test several possible interpretations below.
    """
    return pd.to_datetime(
        series,
        errors="coerce"
    )


def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def print_section(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


# =============================================================================
# LOAD CLEAN FILE
# =============================================================================

print_section("LOADING CLEANED TAQ")

clean = pd.read_csv(
    CLEAN_FILE,
    low_memory=False
)

print(f"Cleaned rows:     {len(clean):,}")
print(f"Cleaned columns:  {len(clean.columns):,}")


# =============================================================================
# LOAD RAW STRUCTURE
# =============================================================================

print_section("LOADING RAW TAQ SCHEMA")

raw_header = pd.read_csv(
    RAW_FILE,
    nrows=0
)

raw_columns = list(raw_header.columns)
clean_columns = list(clean.columns)

print(f"Raw columns:      {len(raw_columns):,}")
print(f"Cleaned columns:  {len(clean_columns):,}")


# =============================================================================
# EXTRA CLEAN COLUMNS
# =============================================================================

extra_clean_columns = [
    c for c in clean_columns
    if c not in raw_columns
]

extra_df = pd.DataFrame({
    "extra_clean_column": extra_clean_columns
})

extra_df.to_csv(
    OUTPUT_DIR / "taq_clean_extra_columns.csv",
    index=False
)

print_section("EXTRA CLEANED COLUMNS")

for col in extra_clean_columns:
    print(f"  - {col}")


# =============================================================================
# DATE DIAGNOSTIC
# =============================================================================

print_section("DATE TRANSFORMATION DIAGNOSTIC")

raw_date_values = []

for chunk_number, chunk in enumerate(
    pd.read_csv(
        RAW_FILE,
        usecols=["date", "symbol"],
        dtype={"date": "string", "symbol": "string"},
        chunksize=CHUNK_SIZE
    ),
    start=1
):
    print(
        f"Reading raw date chunk {chunk_number}: "
        f"{len(chunk):,} rows"
    )

    raw_date_values.append(chunk)

raw_dates = pd.concat(
    raw_date_values,
    ignore_index=True
)

raw_dates["symbol"] = normalize_symbol(raw_dates["symbol"])

raw_dates["raw_date_string"] = (
    raw_dates["date"]
    .astype("string")
    .str.strip()
)

raw_dates["correct_date_ddmmyyyy"] = parse_raw_date_correctly(
    raw_dates["raw_date_string"]
)

# Different possible interpretations for comparison.
raw_dates["parsed_dayfirst_false"] = pd.to_datetime(
    raw_dates["raw_date_string"],
    dayfirst=False,
    errors="coerce"
)

raw_dates["parsed_dayfirst_true"] = pd.to_datetime(
    raw_dates["raw_date_string"],
    dayfirst=True,
    errors="coerce"
)

print("\nRaw date interpretation:")
print(
    raw_dates[
        [
            "raw_date_string",
            "correct_date_ddmmyyyy",
            "parsed_dayfirst_false",
            "parsed_dayfirst_true",
        ]
    ]
    .drop_duplicates()
    .head(20)
    .to_string(index=False)
)

# Clean date
clean_date = parse_clean_date(clean["date"])

date_summary = pd.DataFrame({
    "dataset": ["RAW_CORRECT_DDMMYYYY", "CLEANED"],
    "rows": [
        len(raw_dates),
        len(clean)
    ],
    "missing_dates": [
        raw_dates["correct_date_ddmmyyyy"].isna().sum(),
        clean_date.isna().sum()
    ],
    "unique_dates": [
        raw_dates["correct_date_ddmmyyyy"].nunique(),
        clean_date.nunique()
    ],
    "first_date": [
        raw_dates["correct_date_ddmmyyyy"].min(),
        clean_date.min()
    ],
    "last_date": [
        raw_dates["correct_date_ddmmyyyy"].max(),
        clean_date.max()
    ]
})

date_summary.to_csv(
    OUTPUT_DIR / "taq_date_transformation_diagnostic.csv",
    index=False
)

print("\nDATE SUMMARY")
print(date_summary.to_string(index=False))


# =============================================================================
# DATE MISMATCH DIAGNOSTIC
# =============================================================================

print_section("DATE MISMATCH DIAGNOSTIC")

comparison = pd.DataFrame({
    "raw_date_string": raw_dates["raw_date_string"],
    "raw_correct_date": raw_dates["correct_date_ddmmyyyy"],
    "raw_dayfirst_false": raw_dates["parsed_dayfirst_false"],
    "raw_dayfirst_true": raw_dates["parsed_dayfirst_true"],
    "symbol": raw_dates["symbol"],
})

# Compare against cleaned rows by row position.
comparison["clean_date"] = clean_date.values[:len(comparison)]

comparison["clean_matches_correct"] = (
    comparison["clean_date"]
    == comparison["raw_correct_date"]
)

comparison["clean_matches_dayfirst_false"] = (
    comparison["clean_date"]
    == comparison["raw_dayfirst_false"]
)

comparison["clean_matches_dayfirst_true"] = (
    comparison["clean_date"]
    == comparison["raw_dayfirst_true"]
)

print(
    f"Clean date matches correct DD/MM/YYYY: "
    f"{comparison['clean_matches_correct'].sum():,} / "
    f"{len(comparison):,}"
)

print(
    f"Clean date matches dayfirst=False: "
    f"{comparison['clean_matches_dayfirst_false'].sum():,} / "
    f"{len(comparison):,}"
)

print(
    f"Clean date matches dayfirst=True: "
    f"{comparison['clean_matches_dayfirst_true'].sum():,} / "
    f"{len(comparison):,}"
)

mismatches = comparison[
    ~comparison["clean_matches_correct"]
].copy()

mismatches[
    [
        "raw_date_string",
        "raw_correct_date",
        "raw_dayfirst_false",
        "raw_dayfirst_true",
        "clean_date",
        "symbol",
    ]
].head(500).to_csv(
    OUTPUT_DIR / "taq_date_mismatch_examples.csv",
    index=False
)


# =============================================================================
# DUPLICATE ROOT-CAUSE ANALYSIS
# =============================================================================

print_section("DUPLICATE ROOT-CAUSE ANALYSIS")

raw_key = pd.DataFrame({
    "date": raw_dates["correct_date_ddmmyyyy"],
    "symbol": raw_dates["symbol"]
})

clean_key = pd.DataFrame({
    "date": clean_date,
    "symbol": normalize_symbol(clean["symbol"])
})

raw_duplicate_count = (
    raw_key
    .duplicated(["date", "symbol"], keep=False)
    .sum()
)

clean_duplicate_count = (
    clean_key
    .duplicated(["date", "symbol"], keep=False)
    .sum()
)

raw_duplicate_groups = (
    raw_key
    .groupby(["date", "symbol"])
    .size()
    .reset_index(name="count")
)

clean_duplicate_groups = (
    clean_key
    .groupby(["date", "symbol"])
    .size()
    .reset_index(name="count")
)

raw_duplicate_groups = raw_duplicate_groups[
    raw_duplicate_groups["count"] > 1
]

clean_duplicate_groups = clean_duplicate_groups[
    clean_duplicate_groups["count"] > 1
]

duplicate_summary = pd.DataFrame({
    "dataset": ["RAW_CORRECT_DATE", "CLEANED"],
    "duplicate_rows": [
        raw_duplicate_count,
        clean_duplicate_count
    ],
    "duplicate_groups": [
        len(raw_duplicate_groups),
        len(clean_duplicate_groups)
    ]
})

duplicate_summary.to_csv(
    OUTPUT_DIR / "taq_duplicate_root_cause.csv",
    index=False
)

print(duplicate_summary.to_string(index=False))

clean_duplicate_examples = (
    clean_key
    .groupby(["date", "symbol"])
    .size()
    .reset_index(name="rows")
)

clean_duplicate_examples = clean_duplicate_examples[
    clean_duplicate_examples["rows"] > 1
]

clean_duplicate_examples.to_csv(
    OUTPUT_DIR / "taq_duplicate_examples.csv",
    index=False
)


# =============================================================================
# QUOTE FIELD IDENTIFICATION
# =============================================================================

print_section("QUOTE FIELD DIAGNOSTIC")

quote_sets = {
    "1pm": ["BB_1pm", "BO_1pm", "MID_1pm"],
    "c1": ["BB_c1", "BO_c1", "Mid_c1"],
    "4pm": ["BB_4pm", "BO_4pm", "Mid_4pm"],
    "last": ["LBB", "LBO", "LMid"],
}

quote_summary_rows = []
quote_violation_examples = []
midpoint_violation_examples = []


for quote_name, fields in quote_sets.items():

    missing_fields = [
        field for field in fields
        if field not in clean.columns
    ]

    if missing_fields:
        print(
            f"{quote_name}: missing fields "
            f"{missing_fields}"
        )
        continue

    bid = safe_numeric(clean[fields[0]])
    ask = safe_numeric(clean[fields[1]])
    mid = safe_numeric(clean[fields[2]])

    bid_ask_violation = (
        bid.notna()
        & ask.notna()
        & (bid > ask)
    )

    expected_mid = (bid + ask) / 2

    midpoint_violation = (
        bid.notna()
        & ask.notna()
        & mid.notna()
        & ~np.isclose(
            mid,
            expected_mid,
            rtol=1e-8,
            atol=1e-8
        )
    )

    quote_summary_rows.append({
        "quote_set": quote_name,
        "bid_column": fields[0],
        "ask_column": fields[1],
        "mid_column": fields[2],
        "bid_ask_violations": int(
            bid_ask_violation.sum()
        ),
        "midpoint_violations": int(
            midpoint_violation.sum()
        ),
        "non_null_bid": int(bid.notna().sum()),
        "non_null_ask": int(ask.notna().sum()),
        "non_null_mid": int(mid.notna().sum()),
    })

    violation_idx = clean.index[
        bid_ask_violation
    ][:500]

    if len(violation_idx):
        temp = clean.loc[
            violation_idx,
            [
                "date",
                "symbol",
                *fields
            ]
        ].copy()

        temp["quote_set"] = quote_name
        temp["violation_type"] = "BID_GREATER_THAN_ASK"

        quote_violation_examples.append(temp)

    midpoint_idx = clean.index[
        midpoint_violation
    ][:500]

    if len(midpoint_idx):
        temp = clean.loc[
            midpoint_idx,
            [
                "date",
                "symbol",
                *fields
            ]
        ].copy()

        temp["quote_set"] = quote_name
        temp["expected_mid"] = (
            safe_numeric(temp[fields[0]])
            + safe_numeric(temp[fields[1]])
        ) / 2

        midpoint_violation_examples.append(temp)


quote_summary = pd.DataFrame(
    quote_summary_rows
)

quote_summary.to_csv(
    OUTPUT_DIR / "taq_quote_violation_summary.csv",
    index=False
)

print("\nQUOTE SUMMARY")
print(quote_summary.to_string(index=False))


if quote_violation_examples:
    pd.concat(
        quote_violation_examples,
        ignore_index=True
    ).to_csv(
        OUTPUT_DIR / "taq_quote_violation_examples.csv",
        index=False
    )
else:
    pd.DataFrame().to_csv(
        OUTPUT_DIR / "taq_quote_violation_examples.csv",
        index=False
    )


if midpoint_violation_examples:
    pd.concat(
        midpoint_violation_examples,
        ignore_index=True
    ).to_csv(
        OUTPUT_DIR / "taq_midpoint_violation_examples.csv",
        index=False
    )
else:
    pd.DataFrame().to_csv(
        OUTPUT_DIR / "taq_midpoint_violation_examples.csv",
        index=False
    )


# =============================================================================
# RAW VS CLEAN QUOTE COMPARISON
# =============================================================================

print_section("RAW VS CLEAN QUOTE COMPARISON")

raw_quote_columns = [
    "BB_1pm",
    "BO_1pm",
    "MID_1pm",
    "BB_c1",
    "BO_c1",
    "Mid_c1",
    "BB_4pm",
    "BO_4pm",
    "Mid_4pm",
    "LBB",
    "LBO",
    "LMid",
]

available_raw_quotes = [
    c for c in raw_quote_columns
    if c in raw_columns
]

raw_quotes = pd.read_csv(
    RAW_FILE,
    usecols=available_raw_quotes,
    chunksize=CHUNK_SIZE
)

raw_quote_parts = []

for chunk_number, chunk in enumerate(
    raw_quotes,
    start=1
):
    print(
        f"Reading raw quote chunk {chunk_number}: "
        f"{len(chunk):,} rows"
    )
    raw_quote_parts.append(chunk)

raw_quotes = pd.concat(
    raw_quote_parts,
    ignore_index=True
)

comparison_rows = []

for column in available_raw_quotes:

    raw_values = safe_numeric(
        raw_quotes[column]
    )

    clean_values = safe_numeric(
        clean[column]
    )

    equal = (
        np.isclose(
            raw_values.fillna(np.nan),
            clean_values.fillna(np.nan),
            equal_nan=True
        )
    )

    comparison_rows.append({
        "column": column,
        "raw_missing": int(raw_values.isna().sum()),
        "clean_missing": int(clean_values.isna().sum()),
        "exact_or_numeric_match_count": int(equal.sum()),
        "mismatch_count": int((~equal).sum()),
        "max_absolute_difference": (
            np.nanmax(
                np.abs(
                    raw_values.to_numpy()
                    - clean_values.to_numpy()
                )
            )
            if np.isfinite(
                raw_values.to_numpy()
                - clean_values.to_numpy()
            ).any()
            else np.nan
        ),
    })

raw_clean_quote_comparison = pd.DataFrame(
    comparison_rows
)

raw_clean_quote_comparison.to_csv(
    OUTPUT_DIR / "taq_raw_clean_row_comparison.csv",
    index=False
)

print(
    raw_clean_quote_comparison.to_string(
        index=False
    )
)


# =============================================================================
# FAILURE SUMMARY
# =============================================================================

print_section("FAILURE INVESTIGATION SUMMARY")

summary_rows = [
    {
        "failure": "DATE_INTERPRETATION",
        "status": (
            "FAIL"
            if not comparison["clean_matches_correct"].all()
            else "PASS"
        ),
        "detail": (
            "Cleaned date does not consistently match "
            "the confirmed DD/MM/YYYY interpretation."
        ),
    },
    {
        "failure": "DATE_SYMBOL_DUPLICATES",
        "status": (
            "FAIL"
            if clean_duplicate_count > 0
            else "PASS"
        ),
        "detail": (
            f"Cleaned duplicate rows: "
            f"{clean_duplicate_count:,}; "
            f"raw duplicate rows under corrected dates: "
            f"{raw_duplicate_count:,}."
        ),
    },
    {
        "failure": "BID_GREATER_THAN_ASK",
        "status": (
            "REVIEW"
            if quote_summary["bid_ask_violations"].sum() > 0
            else "PASS"
        ),
        "detail": (
            "Investigate quote-set-specific violations "
            "before declaring a data error."
        ),
    },
    {
        "failure": "MIDPOINT_CONSISTENCY",
        "status": (
            "REVIEW"
            if quote_summary["midpoint_violations"].sum() > 0
            else "PASS"
        ),
        "detail": (
            "Compare stored midpoint against "
            "(bid + ask) / 2 for each quote snapshot."
        ),
    },
]

failure_summary = pd.DataFrame(summary_rows)

failure_summary.to_csv(
    OUTPUT_DIR / "taq_failure_summary.csv",
    index=False
)

print(
    failure_summary.to_string(
        index=False
    )
)


print_section("INVESTIGATION COMPLETE")

print("No observations were removed.")
print("No values were modified.")
print("No imputation was performed.")
print("No canonical file was overwritten.")

print(
    f"\nInvestigation outputs saved to:\n"
    f"{OUTPUT_DIR}"
)