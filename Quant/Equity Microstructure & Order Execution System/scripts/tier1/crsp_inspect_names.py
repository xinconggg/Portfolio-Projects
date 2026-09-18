from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


# =============================================================================
# CONFIGURATION
# =============================================================================

REQUIRED_COLUMNS = [
    "PERMNO",
    "PERMCO",
    "Ticker",
    "CUSIP",
    "SecInfoStartDt",
    "SecInfoEndDt",
    "SecurityBegDt",
    "SecurityEndDt",
]

PHASE2_PERMNO_COLUMN = "PERMNO"
PHASE2_DATE_COLUMN = "DlyCalDt"

DATE_COLUMNS = [
    "SecInfoStartDt",
    "SecInfoEndDt",
    "SecurityBegDt",
    "SecurityEndDt",
]


# =============================================================================
# LOADERS
# =============================================================================

def load_csv(path: Path) -> pd.DataFrame:
    """
    Load a CSV file and fail clearly if it does not exist.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    return pd.read_csv(
        path,
        low_memory=False,
    )


def load_phase2_permnos(path: Path) -> pd.DataFrame:
    """
    Load the Phase 2 cleaned CRSP daily file.

    For Phase 3, YYYYMMDD is the canonical date field because it is
    unambiguous and was already validated during Phase 2.

    DlyCalDt is retained exactly as stored in the Phase 2 file for
    provenance, but is NOT reparsed here.
    """

    df = load_csv(path)

    required = [
        "PERMNO",
        "DlyCalDt",
        "YYYYMMDD",
    ]

    missing = sorted(
        set(required) - set(df.columns)
    )

    if missing:
        raise ValueError(
            "Phase 2 clean file is missing required columns: "
            + ", ".join(missing)
        )

    print()
    print("=== PHASE 2 DATE VALIDATION ===")

    # =========================================================================
    # YYYYMMDD
    # =========================================================================

    parsed_yyyymmdd = pd.to_datetime(
        df["YYYYMMDD"].astype("string").str.strip(),
        format="%Y%m%d",
        errors="coerce",
    )

    invalid_yyyymmdd = int(
        parsed_yyyymmdd.isna().sum()
    )

    print(
        f"Invalid YYYYMMDD values: "
        f"{invalid_yyyymmdd:,}"
    )

    if invalid_yyyymmdd > 0:

        print()
        print("Examples of invalid YYYYMMDD values:")

        print(
            df.loc[
                parsed_yyyymmdd.isna(),
                [
                    "PERMNO",
                    "DlyCalDt",
                    "YYYYMMDD",
                ],
            ]
            .head(20)
            .to_string(index=False)
        )

        raise ValueError(
            f"Phase 2 file contains "
            f"{invalid_yyyymmdd:,} invalid YYYYMMDD values."
        )

    # =========================================================================
    # CANONICAL PHASE 3 DATE
    # =========================================================================
    #
    # Do NOT parse DlyCalDt here.
    #
    # The Phase 2 audit already established that YYYYMMDD and DlyCalDt
    # agree. Phase 3 therefore uses the validated YYYYMMDD representation
    # as the canonical analytical date.
    #
    # DlyCalDt remains untouched in the dataframe.
    # =========================================================================

    df["DlyCalDt_parsed"] = parsed_yyyymmdd

    print(
        "DlyCalDt: retained in original Phase 2 representation."
    )

    print(
        "DlyCalDt_parsed: constructed from validated YYYYMMDD."
    )

    print(
        f"Phase 3 analytical dates: "
        f"{df['DlyCalDt_parsed'].min().date()} "
        f"to "
        f"{df['DlyCalDt_parsed'].max().date()}"
    )

    return df


def load_crsp_names(path: Path) -> pd.DataFrame:
    """
    Load CRSP Names and normalize the lowercase CRSP column names
    to the project's canonical naming convention.
    """

    df = load_csv(path)

    # -------------------------------------------------------------------------
    # Normalize CRSP Names column names
    # -------------------------------------------------------------------------

    df = df.rename(
        columns={
            "ticker": "Ticker",
            "permno": "PERMNO",
            "permco": "PERMCO",
            "secinfostartdt": "SecInfoStartDt",
            "secinfoenddt": "SecInfoEndDt",
            "securitybegdt": "SecurityBegDt",
            "securityenddt": "SecurityEndDt",
            "cusip": "CUSIP",
        }
    )

    # -------------------------------------------------------------------------
    # Validate required columns
    # -------------------------------------------------------------------------

    missing = sorted(
        set(REQUIRED_COLUMNS) - set(df.columns)
    )

    if missing:
        raise ValueError(
            "CRSP Names is missing required columns: "
            + ", ".join(missing)
        )

    # -------------------------------------------------------------------------
    # Normalize date fields
    # -------------------------------------------------------------------------

    for column in DATE_COLUMNS:
        df[column] = pd.to_datetime(
            df[column],
            dayfirst=True,
            errors="coerce",
        )

    return df


# =============================================================================
# OVERVIEW
# =============================================================================

def print_names_overview(
    df: pd.DataFrame,
) -> None:
    """
    Print a basic CRSP Names schema and sample overview.
    """

    print()
    print("=" * 80)
    print("CRSP NAMES OVERVIEW")
    print("=" * 80)

    print(
        f"Rows:       {len(df):,}"
    )

    print(
        f"Columns:    {len(df.columns):,}"
    )

    print()
    print("=== COLUMNS ===")

    for i, column in enumerate(
        df.columns,
        start=1,
    ):
        print(
            f"{i:>3}. {repr(column)}"
        )

    print()
    print("=== FIRST 5 ROWS ===")

    print(
        df.head().to_string(
            index=False
        )
    )


# =============================================================================
# PERMNO COVERAGE
# =============================================================================

def restrict_to_phase2_permnos(
    names: pd.DataFrame,
    phase2: pd.DataFrame,
) -> pd.DataFrame:
    """
    Restrict CRSP Names to PERMNOs observed in the Phase 2
    cleaned daily dataset.
    """

    permnos = (
        phase2["PERMNO"]
        .dropna()
        .drop_duplicates()
    )

    subset = names[
        names["PERMNO"].isin(permnos)
    ].copy()

    return subset


def build_permno_coverage(
    phase2: pd.DataFrame,
    names: pd.DataFrame,
) -> pd.DataFrame:
    """
    Determine whether every Phase 2 PERMNO exists in CRSP Names.
    """

    phase2_permnos = (
        phase2["PERMNO"]
        .dropna()
        .drop_duplicates()
        .sort_values()
    )

    names_permnos = (
        names["PERMNO"]
        .dropna()
        .drop_duplicates()
    )

    coverage = pd.DataFrame(
        {
            "PERMNO": phase2_permnos
        }
    )

    coverage["present_in_crsp_names"] = (
        coverage["PERMNO"].isin(
            names_permnos
        )
    )

    return coverage


# =============================================================================
# CRSP NAMES PROFILE
# =============================================================================

def build_permno_names_profile(
    names_subset: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build a PERMNO-level summary of CRSP Names history.
    """

    profile = (
        names_subset
        .groupby(
            "PERMNO",
            dropna=False,
        )
        .agg(
            names_records=(
                "PERMNO",
                "size",
            ),
            unique_PERMCO=(
                "PERMCO",
                "nunique",
            ),
            unique_Ticker=(
                "Ticker",
                "nunique",
            ),
            unique_CUSIP=(
                "CUSIP",
                "nunique",
            ),
            first_security_beg=(
                "SecurityBegDt",
                "min",
            ),
            last_security_end=(
                "SecurityEndDt",
                "max",
            ),
            first_secinfo_start=(
                "SecInfoStartDt",
                "min",
            ),
            last_secinfo_end=(
                "SecInfoEndDt",
                "max",
            ),
        )
        .reset_index()
        .sort_values(
            "PERMNO"
        )
    )

    return profile


# =============================================================================
# IDENTIFIER HISTORY
# =============================================================================

def build_identifier_history(
    names_subset: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the historical identifier record for every PERMNO.
    """

    columns = [
        "PERMNO",
        "PERMCO",
        "Ticker",
        "CUSIP",
        "SecInfoStartDt",
        "SecInfoEndDt",
        "SecurityBegDt",
        "SecurityEndDt",
    ]

    identifier_history = (
        names_subset[columns]
        .sort_values(
            [
                "PERMNO",
                "SecInfoStartDt",
                "SecInfoEndDt",
            ],
            kind="mergesort",
        )
        .reset_index(drop=True)
    )

    return identifier_history


# =============================================================================
# MULTIPLE TICKERS
# =============================================================================

def find_multiple_ticker_permnos(
    names_subset: pd.DataFrame,
) -> list[int]:
    """
    Identify PERMNOs associated with more than one ticker
    across their CRSP Names history.
    """

    ticker_counts = (
        names_subset
        .groupby("PERMNO")["Ticker"]
        .nunique(
            dropna=True
        )
    )

    return (
        ticker_counts[
            ticker_counts > 1
        ]
        .index
        .tolist()
    )


# =============================================================================
# MULTIPLE CUSIPS
# =============================================================================

def find_multiple_cusip_permnos(
    names_subset: pd.DataFrame,
) -> list[int]:
    """
    Identify PERMNOs associated with more than one CUSIP
    across their CRSP Names history.
    """

    cusip_counts = (
        names_subset
        .groupby("PERMNO")["CUSIP"]
        .nunique(
            dropna=True
        )
    )

    return (
        cusip_counts[
            cusip_counts > 1
        ]
        .index
        .tolist()
    )


# =============================================================================
# DAILY DATE RANGES
# =============================================================================

def build_daily_ranges(
    phase2: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the observed daily-data date range for every PERMNO.

    Uses the validated normalized DlyCalDt_parsed field.
    """

    daily_ranges = (
        phase2
        .groupby("PERMNO")
        .agg(
            daily_first_date=(
                "DlyCalDt_parsed",
                "min",
            ),
            daily_last_date=(
                "DlyCalDt_parsed",
                "max",
            ),
            daily_observations=(
                "DlyCalDt_parsed",
                "size",
            ),
        )
        .reset_index()
    )

    return daily_ranges


# =============================================================================
# DATE COMPARISON
# =============================================================================

def build_date_comparison(
    phase2: pd.DataFrame,
    names_subset: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compare observed Phase 2 daily-data ranges with the
    CRSP Names security and security-information intervals.
    """

    daily_ranges = build_daily_ranges(
        phase2
    )

    names_profile = build_permno_names_profile(
        names_subset
    )

    date_comparison = daily_ranges.merge(
        names_profile,
        on="PERMNO",
        how="left",
    )

    # -------------------------------------------------------------------------
    # Date boundary flags
    # -------------------------------------------------------------------------

    date_comparison[
        "daily_before_security_beg"
    ] = (
        date_comparison["daily_first_date"]
        < date_comparison["first_security_beg"]
    )

    date_comparison[
        "daily_after_security_end"
    ] = (
        date_comparison["daily_last_date"]
        > date_comparison["last_security_end"]
    )

    date_comparison[
        "daily_before_secinfo_start"
    ] = (
        date_comparison["daily_first_date"]
        < date_comparison["first_secinfo_start"]
    )

    date_comparison[
        "daily_after_secinfo_end"
    ] = (
        date_comparison["daily_last_date"]
        > date_comparison["last_secinfo_end"]
    )

    return date_comparison


# =============================================================================
# SECURITY INTERVALS
# =============================================================================

def build_security_intervals(
    names_subset: pd.DataFrame,
) -> pd.DataFrame:
    """
    Extract distinct CRSP security intervals for each PERMNO.
    """

    security_intervals = (
        names_subset[
            [
                "PERMNO",
                "PERMCO",
                "SecurityBegDt",
                "SecurityEndDt",
            ]
        ]
        .drop_duplicates()
        .sort_values(
            [
                "PERMNO",
                "SecurityBegDt",
                "SecurityEndDt",
            ],
            kind="mergesort",
        )
        .reset_index(drop=True)
    )

    return security_intervals


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Inspect CRSP Names for Phase 3 Tier 1 "
            "historical universe construction."
        )
    )

    parser.add_argument(
        "--names",
        type=Path,
        default=Path(
            "data/raw/crsp/CRSP_Names.csv"
        ),
    )

    parser.add_argument(
        "--phase2",
        type=Path,
        default=Path(
            "data/processed/crsp/crsp_daily_clean.csv"
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            "data/processed/crsp"
        ),
    )

    args = parser.parse_args()

    # =========================================================================
    # OUTPUT DIRECTORY
    # =========================================================================

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # =========================================================================
    # LOAD CRSP NAMES
    # =========================================================================

    print()
    print("=" * 80)
    print("LOADING CRSP NAMES")
    print("=" * 80)

    names = load_crsp_names(
        args.names
    )

    print_names_overview(
        names
    )

    # =========================================================================
    # LOAD PHASE 2
    # =========================================================================

    print()
    print("=" * 80)
    print("LOADING PHASE 2 CLEAN CRSP DAILY DATA")
    print("=" * 80)

    phase2 = load_phase2_permnos(
        args.phase2
    )

    print(
        f"Rows: {len(phase2):,}"
    )

    print(
        f"Unique PERMNOs: "
        f"{phase2['PERMNO'].nunique():,}"
    )

    # =========================================================================
    # PERMNO COVERAGE
    # =========================================================================

    print()
    print("=" * 80)
    print("CRSP NAMES PERMNO COVERAGE")
    print("=" * 80)

    coverage = build_permno_coverage(
        phase2,
        names,
    )

    coverage_counts = (
        coverage[
            "present_in_crsp_names"
        ]
        .value_counts()
    )

    print(
        coverage_counts
    )

    missing_permnos = (
        coverage.loc[
            ~coverage[
                "present_in_crsp_names"
            ],
            "PERMNO",
        ]
        .tolist()
    )

    print()
    print("Missing PERMNOs:")

    print(
        missing_permnos
    )

    print()
    print(
        f"PERMNOs in Phase 2: "
        f"{len(coverage):,}"
    )

    print(
        f"PERMNOs found in CRSP Names: "
        f"{int(coverage['present_in_crsp_names'].sum()):,}"
    )

    print(
        f"PERMNOs missing from CRSP Names: "
        f"{len(missing_permnos):,}"
    )

    # =========================================================================
    # SAVE COVERAGE
    # =========================================================================

    coverage_path = (
        args.output_dir
        / "crsp_tier1_names_coverage.csv"
    )

    coverage.to_csv(
        coverage_path,
        index=False,
    )

    print()
    print(
        f"Saved: {coverage_path}"
    )

    # =========================================================================
    # RESTRICT CRSP NAMES TO PHASE 2 PERMNOS
    # =========================================================================

    print()
    print("=" * 80)
    print("RESTRICTING CRSP NAMES TO PHASE 2 PERMNOS")
    print("=" * 80)

    names_subset = restrict_to_phase2_permnos(
        names,
        phase2,
    )

    print(
        f"CRSP Names rows: "
        f"{len(names):,}"
    )

    print(
        f"Restricted rows: "
        f"{len(names_subset):,}"
    )

    print(
        f"Restricted unique PERMNOs: "
        f"{names_subset['PERMNO'].nunique():,}"
    )

    # =========================================================================
    # PERMNO PROFILE
    # =========================================================================

    print()
    print("=" * 80)
    print("BUILDING PERMNO NAMES PROFILE")
    print("=" * 80)

    profile = build_permno_names_profile(
        names_subset
    )

    print(
        profile.to_string(
            index=False
        )
    )

    profile_path = (
        args.output_dir
        / "crsp_tier1_names_profile.csv"
    )

    profile.to_csv(
        profile_path,
        index=False,
    )

    print()
    print(
        f"Saved: {profile_path}"
    )

    # =========================================================================
    # IDENTIFIER HISTORY
    # =========================================================================

    print()
    print("=" * 80)
    print("BUILDING IDENTIFIER HISTORY")
    print("=" * 80)

    identifier_history = (
        build_identifier_history(
            names_subset
        )
    )

    identifier_history_path = (
        args.output_dir
        / "crsp_tier1_names_identifier_history.csv"
    )

    identifier_history.to_csv(
        identifier_history_path,
        index=False,
    )

    print(
        f"Saved: {identifier_history_path}"
    )

    # =========================================================================
    # PERMNO 90319 IDENTIFIER HISTORY
    # =========================================================================

    print()
    print("=" * 80)
    print("PERMNO 90319 IDENTIFIER HISTORY")
    print("=" * 80)

    permno_90319 = identifier_history[
        identifier_history["PERMNO"] == 90319
    ]

    if permno_90319.empty:
        print(
            "PERMNO 90319 not found."
        )
    else:
        print(
            permno_90319.to_string(
                index=False
            )
        )

    # =========================================================================
    # MULTIPLE TICKERS
    # =========================================================================

    print()
    print("=" * 80)
    print("PERMNOS WITH MULTIPLE TICKERS")
    print("=" * 80)

    multi_ticker_permnos = (
        find_multiple_ticker_permnos(
            names_subset
        )
    )

    print(
        multi_ticker_permnos
    )

    print(
        f"Count: "
        f"{len(multi_ticker_permnos):,}"
    )

    if multi_ticker_permnos:

        print()

        print(
            identifier_history[
                identifier_history[
                    "PERMNO"
                ].isin(
                    multi_ticker_permnos
                )
            ].to_string(
                index=False
            )
        )

    # =========================================================================
    # MULTIPLE CUSIPS
    # =========================================================================

    print()
    print("=" * 80)
    print("PERMNOS WITH MULTIPLE CUSIPS")
    print("=" * 80)

    multi_cusip_permnos = (
        find_multiple_cusip_permnos(
            names_subset
        )
    )

    print(
        multi_cusip_permnos
    )

    print(
        f"Count: "
        f"{len(multi_cusip_permnos):,}"
    )

    if multi_cusip_permnos:

        print()

        print(
            identifier_history[
                identifier_history[
                    "PERMNO"
                ].isin(
                    multi_cusip_permnos
                )
            ].to_string(
                index=False
            )
        )

    # =========================================================================
    # DAILY DATE RANGES
    # =========================================================================

    print()
    print("=" * 80)
    print("BUILDING DAILY DATE RANGES")
    print("=" * 80)

    daily_ranges = build_daily_ranges(
        phase2
    )

    print(
        daily_ranges.head(
            10
        ).to_string(
            index=False
        )
    )

    # =========================================================================
    # DATE COMPARISON
    # =========================================================================

    print()
    print("=" * 80)
    print("COMPARING DAILY DATA WITH CRSP NAMES DATES")
    print("=" * 80)

    date_comparison = build_date_comparison(
        phase2,
        names_subset,
    )

    flag_columns = [
        "daily_before_security_beg",
        "daily_after_security_end",
        "daily_before_secinfo_start",
        "daily_after_secinfo_end",
    ]

    print()
    print("=== DATE COMPARISON FLAGS ===")

    for column in flag_columns:

        print(
            f"{column}: "
            f"{int(date_comparison[column].sum()):,}"
        )

    # =========================================================================
    # SUSPICIOUS / INTERESTING CASES
    # =========================================================================

    suspicious = date_comparison[
        date_comparison[
            flag_columns
        ].any(axis=1)
    ].copy()

    print()
    print(
        "=== POTENTIALLY INTERESTING DATE CASES ==="
    )

    if suspicious.empty:

        print(
            "No date-boundary cases identified."
        )

    else:

        print(
            suspicious.to_string(
                index=False
            )
        )

    # =========================================================================
    # SAVE DATE COMPARISON
    # =========================================================================

    date_comparison_path = (
        args.output_dir
        / "crsp_tier1_names_date_comparison.csv"
    )

    date_comparison.to_csv(
        date_comparison_path,
        index=False,
    )

    print()
    print(
        f"Saved: {date_comparison_path}"
    )

    # =========================================================================
    # SECURITY INTERVALS
    # =========================================================================

    print()
    print("=" * 80)
    print("BUILDING SECURITY INTERVALS")
    print("=" * 80)

    security_intervals = (
        build_security_intervals(
            names_subset
        )
    )

    print(
        security_intervals.to_string(
            index=False
        )
    )

    security_intervals_path = (
        args.output_dir
        / "crsp_tier1_names_security_intervals.csv"
    )

    security_intervals.to_csv(
        security_intervals_path,
        index=False,
    )

    print()
    print(
        f"Saved: {security_intervals_path}"
    )

    # =========================================================================
    # PERMNO 88614
    # =========================================================================

    print()
    print("=" * 80)
    print("PERMNO 88614")
    print("=" * 80)

    permno_88614 = names_subset[
        names_subset["PERMNO"] == 88614
    ]

    if permno_88614.empty:

        print(
            "PERMNO 88614 not found."
        )

    else:

        print(
            permno_88614.to_string(
                index=False
            )
        )

    # =========================================================================
    # ETF PERMNOS
    # =========================================================================

    etf_permnos = [
        84398,
        86755,
        88222,
    ]

    print()
    print("=" * 80)
    print("ETF PERMNOS")
    print("=" * 80)

    etf_rows = names_subset[
        names_subset[
            "PERMNO"
        ].isin(
            etf_permnos
        )
    ]

    if etf_rows.empty:

        print(
            "None of the specified ETF PERMNOs "
            "were found in the Phase 2 universe."
        )

    else:

        print(
            etf_rows.to_string(
                index=False
            )
        )

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================

    print()
    print("=" * 80)
    print("FINAL CRSP NAMES INSPECTION SUMMARY")
    print("=" * 80)

    print(
        f"CRSP Names rows:              "
        f"{len(names):,}"
    )

    print(
        f"Phase 2 unique PERMNOs:       "
        f"{phase2['PERMNO'].nunique():,}"
    )

    print(
        f"CRSP Names matched PERMNOs:   "
        f"{names_subset['PERMNO'].nunique():,}"
    )

    print(
        f"Missing PERMNOs:              "
        f"{len(missing_permnos):,}"
    )

    print(
        f"Multiple-ticker PERMNOs:      "
        f"{len(multi_ticker_permnos):,}"
    )

    print(
        f"Multiple-CUSIP PERMNOs:       "
        f"{len(multi_cusip_permnos):,}"
    )

    print(
        f"Date-boundary cases:          "
        f"{len(suspicious):,}"
    )

    print()
    print(
        "CRSP Names inspection completed."
    )


if __name__ == "__main__":
    main()