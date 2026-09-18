from __future__ import annotations

"""
CRSP Daily Stock File Cleaning
==============================

Purpose
-------
Create a cleaned CRSP daily stock file suitable for downstream
historical-universe construction and market-data analysis.

Design principles
-----------------
1. Preserve raw CRSP observations whenever possible.
2. Do not fabricate or impute market data.
3. Treat PERMNO + date as the intended security-date key.
4. Remove exact duplicate rows only.
5. Collapse duplicate security-date observations only when their
   differences are attributable to multiple corporate-action records.
6. Preserve corporate-action information through aggregation.
7. Flag suspicious observations rather than silently correcting them.
8. Produce an auditable cleaning report.

Input
-----
data/raw/crsp/CRSP_Daily Stock File.csv

Supporting reconciliation
-------------------------
data/processed/crsp/crsp_distribution_reconciliation.csv

Outputs
-------
data/processed/crsp/crsp_daily_clean.csv
data/processed/crsp/crsp_daily_cleaning_report.csv
data/processed/crsp/crsp_daily_flagged_observations.csv
"""

from pathlib import Path
import sys

import numpy as np
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

RECONCILIATION_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "crsp"
    / "crsp_distribution_reconciliation.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "crsp"
)

CLEAN_PATH = OUTPUT_DIR / "crsp_daily_clean.csv"
REPORT_PATH = OUTPUT_DIR / "crsp_daily_cleaning_report.csv"
FLAGGED_PATH = OUTPUT_DIR / "crsp_daily_flagged_observations.csv"


# =============================================================================
# CONFIGURATION
# =============================================================================

DATE_COLUMNS = [
    "DlyCalDt",
    "ShrStartDt",
    "ShrEndDt",
    "DisExDt",
]

NUMERIC_COLUMNS = [
    "PERMNO",
    "PERMCO",
    "SICCD",
    "NAICS",
    "YYYYMMDD",
    "DlyPrc",
    "DlyCap",
    "DlyRet",
    "DlyRetx",
    "DlyRetI",
    "DlyFacPrc",
    "DlyVol",
    "DlyClose",
    "DlyLow",
    "DlyHigh",
    "DlyBid",
    "DlyAsk",
    "DlyOpen",
    "DlyNumTrd",
    "ShrOut",
    "DisDivAmt",
    "DisFacPr",
    "DisFacShr",
    "sprtrn",
]


# Fields describing the actual market observation.
MARKET_DATA_COLUMNS = [
    "DlyPrc",
    "DlyCap",
    "DlyRet",
    "DlyRetx",
    "DlyRetI",
    "DlyFacPrc",
    "DlyVol",
    "DlyClose",
    "DlyLow",
    "DlyHigh",
    "DlyBid",
    "DlyAsk",
    "DlyOpen",
    "DlyNumTrd",
    "ShrOut",
    "sprtrn",
]


# Fields that should agree inside a PERMNO/date duplicate group.
CORE_DUPLICATE_COLUMNS = [
    "PERMNO",
    "PERMCO",
    "Ticker",
    "TradingSymbol",
    "PrimaryExch",
    "SecurityType",
    "SecuritySubType",
    "ShareType",
    "DlyCalDt",
    "YYYYMMDD",
    "DlyDelFlg",
    "DlyPrc",
    "DlyCap",
    "DlyRet",
    "DlyRetx",
    "DlyRetI",
    "DlyFacPrc",
    "DlyVol",
    "DlyClose",
    "DlyLow",
    "DlyHigh",
    "DlyBid",
    "DlyAsk",
    "DlyOpen",
    "DlyNumTrd",
    "ShrOut",
    "sprtrn",
]


# =============================================================================
# HELPERS
# =============================================================================

def print_section(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse CRSP date fields using day-first format."""

    for column in DATE_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_datetime(
                df[column],
                errors="coerce",
                dayfirst=True,
            )

    return df


def coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure expected numeric fields are numeric."""

    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    return df


def normalize_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize string fields without changing substantive values."""

    string_columns = [
        "HdrCUSIP",
        "CUSIP",
        "CUSIP9",
        "PrimaryExch",
        "SecurityNm",
        "SecurityType",
        "SecuritySubType",
        "ShareType",
        "Ticker",
        "TradingSymbol",
        "IssuerNm",
        "DlyDelFlg",
    ]

    for column in string_columns:
        if column in df.columns:
            df[column] = df[column].astype("string").str.strip()

    return df


def is_equal_with_nan(a: pd.Series, b: pd.Series) -> pd.Series:
    """
    Element-wise equality treating NaN/NA in both fields as equal.
    """

    return a.eq(b) | (a.isna() & b.isna())


def get_duplicate_groups(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows belonging to duplicate PERMNO/date groups."""

    duplicate_mask = df.duplicated(
        subset=["PERMNO", "DlyCalDt"],
        keep=False,
    )

    return df.loc[duplicate_mask].copy()


def aggregate_values(values: pd.Series) -> str | float | int | None:
    """
    Aggregate duplicate corporate-action values.

    Multiple values are represented as pipe-delimited strings.

    Example:
        0.08, 3.0 -> "0.08|3.0"
    """

    values = values.dropna()

    if values.empty:
        return np.nan

    unique_values = []

    for value in values:
        if value not in unique_values:
            unique_values.append(value)

    if len(unique_values) == 1:
        return unique_values[0]

    return "|".join(str(value) for value in unique_values)


def aggregate_duplicate_group(group: pd.DataFrame) -> pd.Series:
    """
    Collapse a duplicate PERMNO/date group into one row.

    Market-data fields must agree across duplicate observations.
    Corporate-action fields may legitimately contain multiple values.

    The first observation supplies the base row. Corporate-action
    information is aggregated rather than discarded.
    """

    group = group.sort_index()

    base = group.iloc[0].copy()

    # -------------------------------------------------------------------------
    # Validate market fields
    # -------------------------------------------------------------------------

    for column in MARKET_DATA_COLUMNS:
        if column not in group.columns:
            continue

        values = group[column]

        non_missing = values.dropna()

        if non_missing.empty:
            continue

        # All non-null values should agree.
        if not np.allclose(
            non_missing.astype(float),
            non_missing.iloc[0],
            equal_nan=True,
        ):
            raise ValueError(
                "Unsafe duplicate group encountered: "
                f"PERMNO={group['PERMNO'].iloc[0]}, "
                f"DATE={group['DlyCalDt'].iloc[0]}, "
                f"field={column}"
            )

        base[column] = non_missing.iloc[0]

    # -------------------------------------------------------------------------
    # Aggregate corporate-action fields
    # -------------------------------------------------------------------------

    for column in [
        "DisExDt",
        "DisDivAmt",
        "DisFacPr",
        "DisFacShr",
    ]:
        if column in group.columns:
            base[column] = aggregate_values(group[column])

    return base


def collapse_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Resolve duplicate PERMNO/date observations.

    Exact duplicate rows are removed first.

    Remaining duplicate PERMNO/date groups are collapsed only when
    market-data fields agree and the differences are confined to
    corporate-action fields.
    """

    before = len(df)

    # -------------------------------------------------------------------------
    # Remove exact duplicates
    # -------------------------------------------------------------------------

    exact_duplicate_mask = df.duplicated(
        keep="first",
    )

    exact_duplicate_rows = int(exact_duplicate_mask.sum())

    df = df.loc[~exact_duplicate_mask].copy()

    # -------------------------------------------------------------------------
    # Identify remaining PERMNO/date duplicates
    # -------------------------------------------------------------------------

    duplicate_mask = df.duplicated(
        subset=["PERMNO", "DlyCalDt"],
        keep=False,
    )

    duplicate_groups = (
        df.loc[duplicate_mask]
        .groupby(
            ["PERMNO", "DlyCalDt"],
            sort=False,
        )
    )

    remaining_duplicate_groups = len(duplicate_groups)

    collapsed_rows = []

    duplicate_keys = set()

    for (permno, date), group in duplicate_groups:
        duplicate_keys.add((permno, date))

        # Verify that the duplicate differences are only corporate-action
        # differences.
        for column in CORE_DUPLICATE_COLUMNS:
            if column not in group.columns:
                continue

            first = group[column].iloc[0]

            for value in group[column].iloc[1:]:
                if pd.isna(first) and pd.isna(value):
                    continue

                if pd.isna(first) != pd.isna(value):
                    raise ValueError(
                        "Unsafe duplicate group: differing core field "
                        f"{column}; PERMNO={permno}; DATE={date}"
                    )

                if isinstance(first, (int, float, np.number)):
                    if not np.isclose(
                        float(first),
                        float(value),
                        equal_nan=True,
                    ):
                        raise ValueError(
                            "Unsafe duplicate group: differing core field "
                            f"{column}; PERMNO={permno}; DATE={date}"
                        )
                else:
                    if first != value:
                        raise ValueError(
                            "Unsafe duplicate group: differing core field "
                            f"{column}; PERMNO={permno}; DATE={date}"
                        )

        collapsed_rows.append(
            aggregate_duplicate_group(group)
        )

    # -------------------------------------------------------------------------
    # Remove duplicate groups from the main frame
    # -------------------------------------------------------------------------

    unique_rows = df.loc[
        ~df.set_index(["PERMNO", "DlyCalDt"]).index.isin(
            duplicate_keys
        )
    ].copy()

    collapsed_df = pd.DataFrame(collapsed_rows)

    cleaned = pd.concat(
        [unique_rows, collapsed_df],
        ignore_index=True,
    )

    cleaned = cleaned.sort_values(
        ["PERMNO", "DlyCalDt"],
        kind="stable",
    ).reset_index(drop=True)

    stats = {
        "rows_before_cleaning": before,
        "exact_duplicate_rows_removed": exact_duplicate_rows,
        "remaining_duplicate_groups": remaining_duplicate_groups,
        "rows_after_duplicate_resolution": len(cleaned),
        "duplicate_groups_collapsed": remaining_duplicate_groups,
    }

    return cleaned, stats


# =============================================================================
# VALIDATION / FLAGS
# =============================================================================

def generate_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate non-destructive quality flags.

    These flags do not modify the observations.
    """

    flags = pd.DataFrame(index=df.index)

    flags["flag_missing_price"] = df["DlyPrc"].isna()

    flags["flag_missing_open"] = df["DlyOpen"].isna()

    flags["flag_missing_high"] = df["DlyHigh"].isna()

    flags["flag_missing_low"] = df["DlyLow"].isna()

    flags["flag_missing_close"] = df["DlyClose"].isna()

    flags["flag_missing_volume"] = df["DlyVol"].isna()

    flags["flag_missing_num_trades"] = df["DlyNumTrd"].isna()

    flags["flag_missing_return"] = (
        df["DlyRet"].isna()
        | df["DlyRetx"].isna()
    )

    flags["flag_bad_price"] = (
        df["DlyPrc"].notna()
        & (df["DlyPrc"] <= 0)
    )

    flags["flag_bad_volume"] = (
        df["DlyVol"].notna()
        & (df["DlyVol"] < 0)
    )

    flags["flag_bad_num_trades"] = (
        df["DlyNumTrd"].notna()
        & (df["DlyNumTrd"] < 0)
    )

    flags["flag_low_gt_high"] = (
        df["DlyLow"].notna()
        & df["DlyHigh"].notna()
        & (df["DlyLow"] > df["DlyHigh"])
    )

    flags["flag_open_outside_range"] = (
        df["DlyOpen"].notna()
        & df["DlyLow"].notna()
        & df["DlyHigh"].notna()
        & (
            (df["DlyOpen"] < df["DlyLow"])
            | (df["DlyOpen"] > df["DlyHigh"])
        )
    )

    flags["flag_close_outside_range"] = (
        df["DlyClose"].notna()
        & df["DlyLow"].notna()
        & df["DlyHigh"].notna()
        & (
            (df["DlyClose"] < df["DlyLow"])
            | (df["DlyClose"] > df["DlyHigh"])
        )
    )

    flags["flag_bid_gt_ask"] = (
        df["DlyBid"].notna()
        & df["DlyAsk"].notna()
        & (df["DlyBid"] > df["DlyAsk"])
    )

    flags["flag_invalid_permno"] = (
        df["PERMNO"].isna()
        | (df["PERMNO"] <= 0)
    )

    flags["flag_invalid_date"] = df["DlyCalDt"].isna()

    flags["flag_date_key_disagreement"] = (
        df["YYYYMMDD"].notna()
        & df["DlyCalDt"].notna()
        & (
            pd.to_datetime(
                df["YYYYMMDD"].astype("Int64").astype(str),
                format="%Y%m%d",
                errors="coerce",
            )
            != df["DlyCalDt"]
        )
    )

    return flags


def build_flagged_observations(
    df: pd.DataFrame,
    flags: pd.DataFrame,
) -> pd.DataFrame:
    """Return observations with at least one quality flag."""

    any_flag = flags.any(axis=1)

    flagged = pd.concat(
        [
            df.loc[any_flag].copy(),
            flags.loc[any_flag].copy(),
        ],
        axis=1,
    )

    return flagged.reset_index(drop=True)


# =============================================================================
# CLEANING REPORT
# =============================================================================

def build_cleaning_report(
    original: pd.DataFrame,
    cleaned: pd.DataFrame,
    duplicate_stats: dict,
    flags: pd.DataFrame,
) -> pd.DataFrame:
    """Build a machine-readable cleaning summary."""

    report_rows = []

    def add(metric: str, value) -> None:
        report_rows.append(
            {
                "metric": metric,
                "value": value,
            }
        )

    add("input_rows", len(original))
    add("output_rows", len(cleaned))
    add(
        "rows_removed_total",
        len(original) - len(cleaned),
    )

    add(
        "exact_duplicate_rows_removed",
        duplicate_stats["exact_duplicate_rows_removed"],
    )

    add(
        "duplicate_groups_collapsed",
        duplicate_stats["duplicate_groups_collapsed"],
    )

    add(
        "unique_permnos",
        cleaned["PERMNO"].nunique(),
    )

    add(
        "unique_dates",
        cleaned["DlyCalDt"].nunique(),
    )

    add(
        "duplicate_permno_date_keys_after_cleaning",
        int(
            cleaned.duplicated(
                ["PERMNO", "DlyCalDt"]
            ).sum()
        ),
    )

    add(
        "missing_dlyprc",
        int(cleaned["DlyPrc"].isna().sum()),
    )

    add(
        "missing_dlyopen",
        int(cleaned["DlyOpen"].isna().sum()),
    )

    add(
        "missing_dlyhigh",
        int(cleaned["DlyHigh"].isna().sum()),
    )

    add(
        "missing_dlylow",
        int(cleaned["DlyLow"].isna().sum()),
    )

    add(
        "missing_dlyclose",
        int(cleaned["DlyClose"].isna().sum()),
    )

    add(
        "missing_dlyvol",
        int(cleaned["DlyVol"].isna().sum()),
    )

    add(
        "missing_dlynumtrd",
        int(cleaned["DlyNumTrd"].isna().sum()),
    )

    add(
        "missing_dlyret",
        int(cleaned["DlyRet"].isna().sum()),
    )

    add(
        "bid_gt_ask",
        int(flags["flag_bid_gt_ask"].sum()),
    )

    add(
        "low_gt_high",
        int(flags["flag_low_gt_high"].sum()),
    )

    add(
        "open_outside_range",
        int(flags["flag_open_outside_range"].sum()),
    )

    add(
        "close_outside_range",
        int(flags["flag_close_outside_range"].sum()),
    )

    add(
        "invalid_permno",
        int(flags["flag_invalid_permno"].sum()),
    )

    add(
        "invalid_date",
        int(flags["flag_invalid_date"].sum()),
    )

    add(
        "date_key_disagreements",
        int(flags["flag_date_key_disagreement"].sum()),
    )

    add(
        "earliest_date",
        cleaned["DlyCalDt"].min(),
    )

    add(
        "latest_date",
        cleaned["DlyCalDt"].max(),
    )

    return pd.DataFrame(report_rows)


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -------------------------------------------------------------------------
    # LOAD
    # -------------------------------------------------------------------------

    print_section("LOADING CRSP DAILY STOCK FILE")

    if not RAW_PATH.exists():
        raise FileNotFoundError(
            f"CRSP daily file not found:\n{RAW_PATH}"
        )

    df = pd.read_csv(
        RAW_PATH,
        low_memory=False,
    )

    print(f"Rows loaded: {len(df):,}")
    print(f"Columns loaded: {len(df.columns)}")

    original = df.copy()

    # -------------------------------------------------------------------------
    # STANDARDIZE TYPES
    # -------------------------------------------------------------------------

    print_section("STANDARDIZING DATA TYPES")

    df = normalize_strings(df)
    df = coerce_numeric(df)
    df = parse_dates(df)

    print("Date fields parsed.")
    print("Numeric fields coerced.")
    print("String fields normalized.")

    # -------------------------------------------------------------------------
    # DATE AGREEMENT
    # -------------------------------------------------------------------------

    print_section("DATE VALIDATION")

    expected_dates = pd.to_datetime(
        df["YYYYMMDD"].astype("Int64").astype(str),
        format="%Y%m%d",
        errors="coerce",
    )

    date_disagreement = (
        expected_dates.notna()
        & df["DlyCalDt"].notna()
        & (expected_dates != df["DlyCalDt"])
    )

    print(
        "YYYYMMDD / DlyCalDt disagreements:",
        int(date_disagreement.sum()),
    )

    # -------------------------------------------------------------------------
    # DUPLICATE RESOLUTION
    # -------------------------------------------------------------------------

    print_section("RESOLVING DUPLICATE PERMNO/DATE OBSERVATIONS")

    duplicate_before = get_duplicate_groups(df)

    print(
        "Rows belonging to duplicate groups:",
        len(duplicate_before),
    )

    print(
        "Duplicate PERMNO/date groups:",
        duplicate_before.groupby(
            ["PERMNO", "DlyCalDt"]
        ).ngroups,
    )

    cleaned, duplicate_stats = collapse_duplicates(df)

    print(
        "Exact duplicate rows removed:",
        duplicate_stats["exact_duplicate_rows_removed"],
    )

    print(
        "Duplicate groups collapsed:",
        duplicate_stats["duplicate_groups_collapsed"],
    )

    print(
        "Rows after duplicate resolution:",
        f"{len(cleaned):,}",
    )

    # -------------------------------------------------------------------------
    # FINAL KEY CHECK
    # -------------------------------------------------------------------------

    print_section("FINAL KEY VALIDATION")

    remaining_duplicates = cleaned.duplicated(
        subset=["PERMNO", "DlyCalDt"],
        keep=False,
    )

    remaining_duplicate_count = int(
        remaining_duplicates.sum()
    )

    print(
        "Rows in remaining duplicate groups:",
        remaining_duplicate_count,
    )

    if remaining_duplicate_count != 0:
        raise RuntimeError(
            "CRITICAL: PERMNO/date duplicates remain after cleaning."
        )

    # -------------------------------------------------------------------------
    # QUALITY FLAGS
    # -------------------------------------------------------------------------

    print_section("GENERATING QUALITY FLAGS")

    flags = generate_quality_flags(cleaned)

    flagged = build_flagged_observations(
        cleaned,
        flags,
    )

    print(
        "Rows with at least one quality flag:",
        len(flagged),
    )

    print(
        "Bid > Ask observations:",
        int(flags["flag_bid_gt_ask"].sum()),
    )

    print(
        "Low > High observations:",
        int(flags["flag_low_gt_high"].sum()),
    )

    print(
        "Open outside Low/High:",
        int(flags["flag_open_outside_range"].sum()),
    )

    print(
        "Close outside Low/High:",
        int(flags["flag_close_outside_range"].sum()),
    )

    # -------------------------------------------------------------------------
    # CLEANING REPORT
    # -------------------------------------------------------------------------

    print_section("BUILDING CLEANING REPORT")

    report = build_cleaning_report(
        original=original,
        cleaned=cleaned,
        duplicate_stats=duplicate_stats,
        flags=flags,
    )

    # -------------------------------------------------------------------------
    # SAVE
    # -------------------------------------------------------------------------

    print_section("WRITING OUTPUTS")

    cleaned.to_csv(
        CLEAN_PATH,
        index=False,
    )

    report.to_csv(
        REPORT_PATH,
        index=False,
    )

    flagged.to_csv(
        FLAGGED_PATH,
        index=False,
    )

    print(f"Clean dataset: {CLEAN_PATH}")
    print(f"Cleaning report: {REPORT_PATH}")
    print(f"Flagged observations: {FLAGGED_PATH}")

    # -------------------------------------------------------------------------
    # FINAL SUMMARY
    # -------------------------------------------------------------------------

    print_section("CLEANING COMPLETE")

    print(f"Input rows:       {len(original):,}")
    print(f"Output rows:      {len(cleaned):,}")
    print(
        f"Rows removed:     "
        f"{len(original) - len(cleaned):,}"
    )
    print(
        f"Unique PERMNOs:   "
        f"{cleaned['PERMNO'].nunique():,}"
    )
    print(
        f"Unique dates:     "
        f"{cleaned['DlyCalDt'].nunique():,}"
    )
    print(
        f"Duplicate keys:   "
        f"{cleaned.duplicated(['PERMNO', 'DlyCalDt']).sum():,}"
    )

    print()
    print("IMPORTANT:")
    print(
        "Quality flags are diagnostic only. "
        "No market-data values were imputed."
    )
    print(
        "Corporate-action differences inside duplicate "
        "PERMNO/date groups were preserved."
    )


if __name__ == "__main__":
    main()