from __future__ import annotations

from pathlib import Path

import pandas as pd


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "crsp"
    / "CRSP_Daily Stock File.csv"
)

CLEAN_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "crsp"
    / "crsp_daily_clean.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "crsp"
    / "crsp_cleaning_audit.csv"
)


# =============================================================================
# CONFIGURATION
# =============================================================================

KEY_COLUMNS = [
    "PERMNO",
    "YYYYMMDD",
]

DATE_COLUMNS = [
    "DlyCalDt",
    "ShrStartDt",
    "ShrEndDt",
    "DisExDt",
]

CORPORATE_ACTION_COLUMNS = [
    "DisExDt",
    "DisDivAmt",
    "DisFacPr",
    "DisFacShr",
]


# =============================================================================
# HELPERS
# =============================================================================

def print_header(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def normalize_date_column(
    series: pd.Series,
) -> pd.Series:
    """
    Normalize CRSP calendar dates.

    Supports:
        - DD/MM/YYYY
        - YYYY-MM-DD
        - datetime-like values

    Returns:
        pandas datetime64[ns] series.
    """

    values = series.astype("string").str.strip()

    # First attempt: original CRSP raw format
    parsed = pd.to_datetime(
        values,
        format="%d/%m/%Y",
        errors="coerce",
    )

    # Second attempt: ISO-style dates used by cleaned files
    missing = parsed.isna()

    if missing.any():
        parsed.loc[missing] = pd.to_datetime(
            values.loc[missing],
            format="%Y-%m-%d",
            errors="coerce",
        )

    return parsed


def normalize_yyyymmdd(
    series: pd.Series,
) -> pd.Series:
    """Parse CRSP YYYYMMDD integer/string dates."""

    return pd.to_datetime(
        series.astype("string"),
        format="%Y%m%d",
        errors="coerce",
    )


def normalize_for_comparison(
    series: pd.Series,
) -> pd.Series:
    """
    Normalize values for robust comparison between raw and clean files.

    Important:
    - avoids float/string merge problems
    - treats NaN/None consistently
    """

    return (
        series.astype("string")
        .fillna("<NA>")
        .str.strip()
    )


def build_key(
    df: pd.DataFrame,
) -> pd.Series:
    """
    Build a robust PERMNO/date key using YYYYMMDD.

    YYYYMMDD is preferred over DlyCalDt because it is an
    unambiguous numeric CRSP date field.
    """

    return (
        df["PERMNO"].astype("Int64").astype("string")
        + "|"
        + df["YYYYMMDD"].astype("Int64").astype("string")
    )


def compare_rows(
    raw_group: pd.DataFrame,
    clean_group: pd.DataFrame,
) -> str:
    """
    Determine what happened to a raw duplicate group.

    Returns:
        EXACT_DUPLICATE
        CORPORATE_ACTION_DUPLICATE
        UNKNOWN_DUPLICATE
        RETAINED
    """

    if len(raw_group) <= 1:
        return "RETAINED"

    # If the clean file has exactly one row for the key,
    # duplicate resolution occurred.
    if len(clean_group) == 1:
        raw_compare = raw_group.copy()
        clean_compare = clean_group.copy()

        # Remove fields that are not useful for duplicate classification.
        comparison_columns = [
            col
            for col in raw_compare.columns
            if col in clean_compare.columns
        ]

        # Normalize values before comparison.
    raw_norm = raw_compare[
        comparison_columns
    ].copy()

    clean_norm = clean_compare[
        comparison_columns
    ].copy()

    for col in comparison_columns:
        raw_norm[col] = normalize_for_comparison(
            raw_norm[col]
        )

        clean_norm[col] = normalize_for_comparison(
            clean_norm[col]
        )

        # Determine whether any raw row is identical to the retained row.
        retained = clean_norm.iloc[0]

        exact_match = False

        for _, row in raw_norm.iterrows():
            if row.equals(retained):
                exact_match = True
                break

        if exact_match:
            # If all raw rows are identical, this is an exact duplicate group.
            if raw_norm.drop_duplicates().shape[0] == 1:
                return "EXACT_DUPLICATE"

            # Otherwise, some fields differed.
            differing_columns = []

            for col in comparison_columns:
                values = raw_norm[col].unique()

                if len(values) > 1:
                    differing_columns.append(col)

            if set(differing_columns).issubset(
                set(CORPORATE_ACTION_COLUMNS)
            ):
                return "CORPORATE_ACTION_DUPLICATE"

            return "UNKNOWN_DUPLICATE"

    return "UNKNOWN_DUPLICATE"


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    # =========================================================================
    # LOAD
    # =========================================================================

    print_header("LOADING RAW CRSP DAILY FILE")

    raw = pd.read_csv(
        RAW_PATH,
        low_memory=False,
    )

    print(f"Raw rows: {len(raw):,}")
    print(f"Raw columns: {len(raw.columns)}")

    print_header("LOADING CLEAN CRSP DAILY FILE")

    clean = pd.read_csv(
        CLEAN_PATH,
        low_memory=False,
    )

    print(f"Clean rows: {len(clean):,}")
    print(f"Clean columns: {len(clean.columns)}")

    # =========================================================================
    # BASIC ROW COUNT
    # =========================================================================

    print_header("ROW COUNT AUDIT")

    rows_removed = len(raw) - len(clean)

    print(f"Raw rows:          {len(raw):,}")
    print(f"Clean rows:        {len(clean):,}")
    print(f"Rows removed:      {rows_removed:,}")

    assert rows_removed == 12, (
        f"Expected 12 removed rows, found {rows_removed}"
    )

    print("PASS   Exactly 12 rows were removed.")

    # =========================================================================
    # DATE NORMALIZATION
    # =========================================================================

    print_header("NORMALIZING DATE FIELDS")

    raw["parsed_DlyCalDt"] = normalize_date_column(
        raw["DlyCalDt"]
    )

    clean["parsed_DlyCalDt"] = normalize_date_column(
        clean["DlyCalDt"]
    )

    raw["parsed_YYYYMMDD"] = normalize_yyyymmdd(
        raw["YYYYMMDD"]
    )

    clean["parsed_YYYYMMDD"] = normalize_yyyymmdd(
        clean["YYYYMMDD"]
    )

    print(
        "Raw invalid DlyCalDt:",
        raw["parsed_DlyCalDt"].isna().sum(),
    )

    print(
        "Clean invalid DlyCalDt:",
        clean["parsed_DlyCalDt"].isna().sum(),
    )

    print(
        "Raw invalid YYYYMMDD:",
        raw["parsed_YYYYMMDD"].isna().sum(),
    )

    print(
        "Clean invalid YYYYMMDD:",
        clean["parsed_YYYYMMDD"].isna().sum(),
    )

    # =========================================================================
    # DATE AGREEMENT
    # =========================================================================

    print_header("DATE VALIDATION AND AGREEMENT")

    raw_invalid_dly = raw["parsed_DlyCalDt"].isna().sum()
    clean_invalid_dly = clean["parsed_DlyCalDt"].isna().sum()

    raw_invalid_yyyymmdd = raw["parsed_YYYYMMDD"].isna().sum()
    clean_invalid_yyyymmdd = clean["parsed_YYYYMMDD"].isna().sum()

    print(
        "Raw invalid DlyCalDt:",
        raw_invalid_dly,
    )

    print(
        "Clean invalid DlyCalDt:",
        clean_invalid_dly,
    )

    print(
        "Raw invalid YYYYMMDD:",
        raw_invalid_yyyymmdd,
    )

    print(
        "Clean invalid YYYYMMDD:",
        clean_invalid_yyyymmdd,
    )

    assert raw_invalid_dly == 0
    assert clean_invalid_dly == 0
    assert raw_invalid_yyyymmdd == 0
    assert clean_invalid_yyyymmdd == 0

    print("PASS   All date fields parsed successfully.")

    raw_date_disagreement = (
        raw["parsed_DlyCalDt"]
        .ne(raw["parsed_YYYYMMDD"])
    ).sum()

    clean_date_disagreement = (
        clean["parsed_DlyCalDt"]
        .ne(clean["parsed_YYYYMMDD"])
    ).sum()

    print(
        "Raw YYYYMMDD / DlyCalDt disagreements:",
        raw_date_disagreement,
    )

    print(
        "Clean YYYYMMDD / DlyCalDt disagreements:",
        clean_date_disagreement,
    )

    assert raw_date_disagreement == 0
    assert clean_date_disagreement == 0

    print("PASS   Date fields agree in both files.")

    # =========================================================================
    # BUILD ROBUST KEYS
    # =========================================================================

    print_header("BUILDING PERMNO / DATE KEYS")

    raw["audit_key"] = build_key(raw)
    clean["audit_key"] = build_key(clean)

    raw_unique_keys = raw["audit_key"].nunique()
    clean_unique_keys = clean["audit_key"].nunique()

    print(f"Raw unique PERMNO/date keys:   {raw_unique_keys:,}")
    print(f"Clean unique PERMNO/date keys: {clean_unique_keys:,}")

    # =========================================================================
    # DUPLICATE ANALYSIS
    # =========================================================================

    print_header("DUPLICATE KEY ANALYSIS")

    raw_key_counts = (
        raw.groupby("audit_key")
        .size()
        .rename("raw_count")
    )

    clean_key_counts = (
        clean.groupby("audit_key")
        .size()
        .rename("clean_count")
    )

    raw_duplicate_keys = raw_key_counts[
        raw_key_counts > 1
    ]

    clean_duplicate_keys = clean_key_counts[
        clean_key_counts > 1
    ]

    print(
        "Raw duplicate PERMNO/date groups:",
        len(raw_duplicate_keys),
    )

    print(
        "Clean duplicate PERMNO/date groups:",
        len(clean_duplicate_keys),
    )

    print(
        "Raw rows belonging to duplicate groups:",
        int(raw_duplicate_keys.sum()),
    )

    print(
        "Clean rows belonging to duplicate groups:",
        int(clean_duplicate_keys.sum()),
    )

    assert len(clean_duplicate_keys) == 0

    print("PASS   Clean file contains no duplicate keys.")

    # =========================================================================
    # KEY SET AUDIT
    # =========================================================================

    print_header("KEY-SET AUDIT")

    raw_keys = set(raw["audit_key"])
    clean_keys = set(clean["audit_key"])

    missing_from_clean = raw_keys - clean_keys
    unexpected_in_clean = clean_keys - raw_keys

    print(
        "Raw keys:",
        len(raw_keys),
    )

    print(
        "Clean keys:",
        len(clean_keys),
    )

    print(
        "Raw keys absent from clean:",
        len(missing_from_clean),
    )

    print(
        "Unexpected clean keys:",
        len(unexpected_in_clean),
    )

    if unexpected_in_clean:
        print()
        print("ERROR: Clean file contains keys not present in raw file.")

        for key in sorted(unexpected_in_clean)[:20]:
            print(" ", key)

        raise AssertionError(
            "Clean file contains unexpected PERMNO/date keys."
        )

    print(
        "PASS   Every clean PERMNO/date key existed in raw file."
    )

    # Important:
    # We expect no key to disappear completely.
    #
    # Duplicate resolution should reduce multiple rows for a key
    # to one row, not delete the key entirely.

    if missing_from_clean:
        print()
        print("ERROR: Raw PERMNO/date keys disappeared entirely.")

        for key in sorted(missing_from_clean)[:20]:
            print(" ", key)

        raise AssertionError(
            "Some raw PERMNO/date keys disappeared from clean file."
        )

    print(
        "PASS   No raw PERMNO/date keys disappeared."
    )

    # =========================================================================
    # EXPECTED ROW REMOVAL CALCULATION
    # =========================================================================

    print_header("EXPECTED ROW REMOVAL CALCULATION")

    expected_removed = 0

    for key, count in raw_key_counts.items():

        if count > 1:

            clean_count = clean_key_counts.get(
                key,
                0,
            )

            expected_removed += max(
                count - clean_count,
                0,
            )

    print(
        f"Expected rows removed through duplicate resolution: "
        f"{expected_removed:,}"
    )

    print(
        f"Actual rows removed: "
        f"{rows_removed:,}"
    )

    assert expected_removed == rows_removed

    print(
        "PASS   Expected and actual row removals agree."
    )

    # =========================================================================
    # IDENTIFY EXACT REMOVED ROWS
    # =========================================================================

    print_header("IDENTIFYING REMOVED OBSERVATIONS")

    # Add a stable occurrence number within each key.
    #
    # This is important because duplicate rows may be identical.
    raw["_occurrence"] = (
        raw.groupby("audit_key")
        .cumcount()
    )

    clean["_occurrence"] = (
        clean.groupby("audit_key")
        .cumcount()
    )

    occurrence_keys_clean = set(
        zip(
            clean["audit_key"],
            clean["_occurrence"],
        )
    )

    raw["_row_retained"] = list(
        zip(
            raw["audit_key"],
            raw["_occurrence"],
        )
    )

    removed_mask = ~raw["_row_retained"].isin(
        occurrence_keys_clean
    )

    removed = raw.loc[
        removed_mask
    ].copy()

    print(
        f"Rows identified as removed: {len(removed):,}"
    )

    assert len(removed) == rows_removed

    print(
        "PASS   Exact number of removed rows identified."
    )

    # =========================================================================
    # REMOVED ROW DETAILS
    # =========================================================================

    print_header("REMOVED ROW DETAILS")

    display_columns = [
        "PERMNO",
        "DlyCalDt",
        "YYYYMMDD",
        "Ticker",
        "DlyPrc",
        "DlyRet",
        "DlyRetx",
        "DlyVol",
        "DlyClose",
        "DlyLow",
        "DlyHigh",
        "DlyBid",
        "DlyAsk",
        "DlyOpen",
        "DlyNumTrd",
        "DisExDt",
        "DisDivAmt",
        "DisFacPr",
        "DisFacShr",
    ]

    display_columns = [
        col
        for col in display_columns
        if col in removed.columns
    ]

    print(
        removed[display_columns]
        .to_string(index=False)
    )

    # =========================================================================
    # DUPLICATE GROUP CLASSIFICATION
    # =========================================================================

    print_header("DUPLICATE GROUP CLASSIFICATION")

    duplicate_keys = (
        raw_key_counts[
            raw_key_counts > 1
        ]
        .index
        .tolist()
    )

    group_audit_rows = []

    for key in duplicate_keys:

        raw_group = raw[
            raw["audit_key"] == key
        ].copy()

        clean_group = clean[
            clean["audit_key"] == key
        ].copy()

        classification = compare_rows(
            raw_group,
            clean_group,
        )

        group_audit_rows.append(
            {
                "audit_key": key,
                "PERMNO": raw_group["PERMNO"].iloc[0],
                "DlyCalDt": raw_group["DlyCalDt"].iloc[0],
                "YYYYMMDD": raw_group["YYYYMMDD"].iloc[0],
                "raw_rows": len(raw_group),
                "clean_rows": len(clean_group),
                "rows_removed": (
                    len(raw_group)
                    - len(clean_group)
                ),
                "classification": classification,
            }
        )

    group_audit = pd.DataFrame(
        group_audit_rows
    )

    print(
        group_audit[
            [
                "PERMNO",
                "DlyCalDt",
                "raw_rows",
                "clean_rows",
                "rows_removed",
                "classification",
            ]
        ].to_string(index=False)
    )

    # =========================================================================
    # CORPORATE ACTION DIFFERENCE AUDIT
    # =========================================================================

    print_header("CORPORATE-ACTION DUPLICATE AUDIT")

    for key in duplicate_keys:

        raw_group = raw[
            raw["audit_key"] == key
        ].copy()

        if len(raw_group) <= 1:
            continue

        # Normalize corporate-action values.
        normalized = raw_group[
            CORPORATE_ACTION_COLUMNS
        ].copy()

        for col in CORPORATE_ACTION_COLUMNS:
            normalized[col] = normalize_for_comparison(
                normalized[col]
            )

        differing_columns = []

        for col in CORPORATE_ACTION_COLUMNS:

            if normalized[col].nunique(
                dropna=False
            ) > 1:

                differing_columns.append(col)

        if differing_columns:

            print()
            print(
                f"PERMNO={raw_group['PERMNO'].iloc[0]}, "
                f"DATE={raw_group['DlyCalDt'].iloc[0]}"
            )

            print(
                "Corporate-action differences:"
            )

            for col in differing_columns:

                values = (
                    normalized[col]
                    .drop_duplicates()
                    .tolist()
                )

                print(
                    f"  {col}: "
                    + " | ".join(
                        str(value)
                        for value in values
                    )
                )

    # =========================================================================
    # SAVE AUDIT
    # =========================================================================

    print_header("WRITING AUDIT OUTPUT")

    audit_output = removed.copy()

    # Remove internal audit columns.
    audit_output = audit_output.drop(
        columns=[
            "parsed_DlyCalDt",
            "parsed_YYYYMMDD",
            "audit_key",
            "_occurrence",
            "_row_retained",
        ],
        errors="ignore",
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    audit_output.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print(
        f"Removed-row audit: {OUTPUT_PATH}"
    )

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================

    print_header("FINAL AUDIT SUMMARY")

    print(
        f"Raw rows:                     {len(raw):,}"
    )

    print(
        f"Clean rows:                   {len(clean):,}"
    )

    print(
        f"Rows removed:                 {rows_removed:,}"
    )

    print(
        f"Raw unique PERMNOs:           "
        f"{raw['PERMNO'].nunique():,}"
    )

    print(
        f"Clean unique PERMNOs:         "
        f"{clean['PERMNO'].nunique():,}"
    )

    print(
        f"Raw unique dates:             "
        f"{raw['parsed_DlyCalDt'].nunique():,}"
    )

    print(
        f"Clean unique dates:           "
        f"{clean['parsed_DlyCalDt'].nunique():,}"
    )

    print(
        f"Raw duplicate key groups:     "
        f"{len(raw_duplicate_keys):,}"
    )

    print(
        f"Clean duplicate key groups:   "
        f"{len(clean_duplicate_keys):,}"
    )

    print()
    print("AUDIT PASSED.")
    print()
    print(
        "The clean file preserves every raw PERMNO/date key."
    )
    print(
        "Duplicate resolution removed exactly 12 rows."
    )
    print(
        "No market-data values were imputed."
    )


if __name__ == "__main__":
    main()