from __future__ import annotations

from pathlib import Path

import pandas as pd


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

NAMES_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "crsp"
    / "crsp_tier1_initial_universe.csv"
)

DAILY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "crsp"
    / "crsp_daily_clean.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "crsp"
)

RECONCILIATION_OUTPUT = (
    OUTPUT_DIR
    / "crsp_tier1_daily_reconciliation.csv"
)

DISCREPANCY_OUTPUT = (
    OUTPUT_DIR
    / "crsp_tier1_daily_discrepancies.csv"
)


# =============================================================================
# EXPECTED COLUMNS
# =============================================================================

NAMES_REQUIRED_COLUMNS = [
    "PERMNO",
]

DAILY_REQUIRED_COLUMNS = [
    "PERMNO",
    "DlyCalDt",
]


# =============================================================================
# HELPERS
# =============================================================================

def print_section(title: str) -> None:
    """Print a formatted section heading."""

    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def validate_columns(
    df: pd.DataFrame,
    required_columns: list[str],
    dataset_name: str,
) -> None:
    """Validate that required columns exist."""

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{dataset_name} is missing required columns: "
            f"{missing}"
        )


def normalize_permno(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalize PERMNO to pandas nullable integer.
    """

    df = df.copy()

    df["PERMNO"] = pd.to_numeric(
        df["PERMNO"],
        errors="coerce",
    ).astype("Int64")

    return df


def normalize_names_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalize CRSP Names column names to the project's
    canonical naming convention.

    Handles both lowercase raw CRSP exports and
    already-normalized files.
    """

    rename_map = {
        "permno": "PERMNO",
        "permco": "PERMCO",
        "ticker": "Ticker",
        "cusip": "CUSIP",
        "secinfostartdt": "SecInfoStartDt",
        "secinfoenddt": "SecInfoEndDt",
        "securitybegdt": "SecurityBegDt",
        "securityenddt": "SecurityEndDt",

        # Possible canonical/alternative fields
        "securitynm": "SecurityNm",
        "primaryexch": "PrimaryExch",
        "securitytype": "SecurityType",
        "securitysubtype": "SecuritySubType",
        "sharetype": "ShareType",
        "siccd": "SICCD",
        "naics": "NAICS",
    }

    # Case-insensitive normalization.
    actual_rename = {}

    for column in df.columns:
        normalized = column.strip().lower()

        if normalized in rename_map:
            actual_rename[column] = rename_map[normalized]

    df = df.rename(
        columns=actual_rename
    )

    return df


def normalize_daily_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalize Phase 2 daily-data column names.

    Handles common lowercase/raw variations.
    """

    rename_map = {
        "permno": "PERMNO",
        "dlycaldt": "DlyCalDt",
        "yyyymmdd": "YYYYMMDD",
    }

    actual_rename = {}

    for column in df.columns:
        normalized = column.strip().lower()

        if normalized in rename_map:
            actual_rename[column] = rename_map[normalized]

    df = df.rename(
        columns=actual_rename
    )

    return df


# =============================================================================
# DATE PARSING
# =============================================================================

def parse_crsp_daily_date(
    series: pd.Series,
) -> pd.Series:
    """
    Parse DlyCalDt robustly.

    The Phase 2 file may contain:
        - datetime-like values
        - DD/MM/YYYY strings
        - YYYY-MM-DD strings
        - YYYYMMDD numeric/string values

    Invalid values remain NaT and are reported by the caller.
    """

    original = series.copy()

    # -------------------------------------------------------------------------
    # First attempt: generic datetime parsing.
    # -------------------------------------------------------------------------

    parsed = pd.to_datetime(
        original,
        errors="coerce",
        dayfirst=True,
    )

    # -------------------------------------------------------------------------
    # Second attempt: YYYYMMDD.
    # -------------------------------------------------------------------------

    unresolved = parsed.isna()

    if unresolved.any():

        yyyymmdd = pd.to_datetime(
            original.loc[unresolved]
            .astype("string")
            .str.strip(),
            format="%Y%m%d",
            errors="coerce",
        )

        parsed.loc[unresolved] = yyyymmdd

    # -------------------------------------------------------------------------
    # Third attempt: explicit DD/MM/YYYY.
    # -------------------------------------------------------------------------

    unresolved = parsed.isna()

    if unresolved.any():

        dmy = pd.to_datetime(
            original.loc[unresolved]
            .astype("string")
            .str.strip(),
            format="%d/%m/%Y",
            errors="coerce",
        )

        parsed.loc[unresolved] = dmy

    return parsed


# =============================================================================
# LOAD NAMES UNIVERSE
# =============================================================================

def load_names_universe() -> pd.DataFrame:
    """
    Load the initial Tier 1 Names universe.

    The input file may use lowercase CRSP column names.
    They are normalized before validation.
    """

    print_section(
        "LOADING TIER 1 NAMES UNIVERSE"
    )

    print(
        f"File: {NAMES_FILE}"
    )

    df = pd.read_csv(
        NAMES_FILE,
        low_memory=False,
    )

    print(
        f"Rows loaded: {len(df):,}"
    )

    print(
        f"Columns loaded: {len(df.columns):,}"
    )

    print()
    print("Original columns:")

    for i, column in enumerate(
        df.columns,
        start=1,
    ):
        print(
            f"{i:>3}. {column!r}"
        )

    # -------------------------------------------------------------------------
    # Normalize schema.
    # -------------------------------------------------------------------------

    df = normalize_names_columns(df)

    print()
    print("Normalized columns:")

    for i, column in enumerate(
        df.columns,
        start=1,
    ):
        print(
            f"{i:>3}. {column!r}"
        )

    # -------------------------------------------------------------------------
    # Validate required columns.
    # -------------------------------------------------------------------------

    validate_columns(
        df,
        NAMES_REQUIRED_COLUMNS,
        "Tier 1 Names universe",
    )

    # -------------------------------------------------------------------------
    # Normalize PERMNO.
    # -------------------------------------------------------------------------

    df = normalize_permno(
        df
    )

    missing_permno = int(
        df["PERMNO"].isna().sum()
    )

    print()
    print(
        f"Missing PERMNO: {missing_permno:,}"
    )

    if missing_permno > 0:
        raise ValueError(
            "Tier 1 Names universe contains "
            "missing PERMNO values."
        )

    # -------------------------------------------------------------------------
    # Check duplicate PERMNO.
    # -------------------------------------------------------------------------

    duplicate_permno = int(
        df["PERMNO"].duplicated().sum()
    )

    print(
        f"Duplicate PERMNO rows: "
        f"{duplicate_permno:,}"
    )

    if duplicate_permno > 0:

        print()
        print(
            "Duplicate PERMNO examples:"
        )

        print(
            df.loc[
                df["PERMNO"].duplicated(
                    keep=False
                )
            ]
            .sort_values("PERMNO")
            .head(20)
            .to_string(index=False)
        )

        raise ValueError(
            "Tier 1 Names universe contains "
            "duplicate PERMNO rows."
        )

    print()
    print(
        f"Unique Names PERMNOs: "
        f"{df['PERMNO'].nunique():,}"
    )

    return df


# =============================================================================
# LOAD CLEAN DAILY FILE
# =============================================================================
def load_daily_file() -> pd.DataFrame:
    """Load the cleaned CRSP daily file."""

    print_section("LOADING CLEAN CRSP DAILY FILE")

    print(f"File: {DAILY_FILE}")

    columns = [
        "PERMNO",
        "DlyCalDt",
    ]

    df = pd.read_csv(
        DAILY_FILE,
        usecols=columns,
        low_memory=False,
    )

    print(f"Rows loaded: {len(df):,}")

    validate_columns(
        df,
        DAILY_REQUIRED_COLUMNS,
        "Clean CRSP daily file",
    )

    # -------------------------------------------------------------------------
    # Normalize PERMNO
    # -------------------------------------------------------------------------

    df = normalize_permno(df)

    missing_permno = int(
        df["PERMNO"].isna().sum()
    )

    print(
        f"Missing PERMNO: {missing_permno:,}"
    )

    if missing_permno > 0:
        raise ValueError(
            "Clean daily file contains missing PERMNO values."
        )

    # -------------------------------------------------------------------------
    # Parse DlyCalDt
    #
    # Phase 2 stores DlyCalDt as ISO YYYY-MM-DD strings.
    # -------------------------------------------------------------------------

    raw_dates = (
        df["DlyCalDt"]
        .astype("string")
        .str.strip()
    )

    df["DlyCalDt"] = pd.to_datetime(
        raw_dates,
        format="%Y-%m-%d",
        errors="coerce",
    )

    invalid_dates = int(
        df["DlyCalDt"].isna().sum()
    )

    print(
        f"Invalid DlyCalDt values: "
        f"{invalid_dates:,}"
    )

    if invalid_dates > 0:

        print()
        print(
            "Examples of invalid DlyCalDt values:"
        )

        print(
            df.loc[
                df["DlyCalDt"].isna(),
                ["PERMNO"],
            ]
            .head(20)
            .to_string(index=False)
        )

        raise ValueError(
            "Clean daily file contains invalid DlyCalDt values."
        )

    # -------------------------------------------------------------------------
    # Report date range
    # -------------------------------------------------------------------------

    print(
        f"Daily date range: "
        f"{df['DlyCalDt'].min().date()} "
        f"to "
        f"{df['DlyCalDt'].max().date()}"
    )

    return df


# =============================================================================
# BUILD DAILY SECURITY SUMMARY
# =============================================================================

def build_daily_summary(
    daily: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build one row per PERMNO summarizing historical daily coverage.
    """

    print_section(
        "BUILDING DAILY HISTORY SUMMARY"
    )

    summary = (
        daily
        .groupby(
            "PERMNO",
            dropna=False,
        )
        .agg(
            daily_first_date=(
                "DlyCalDt",
                "min",
            ),
            daily_last_date=(
                "DlyCalDt",
                "max",
            ),
            daily_observations=(
                "DlyCalDt",
                "size",
            ),
            daily_trading_days=(
                "DlyCalDt",
                "nunique",
            ),
        )
        .reset_index()
    )

    print(
        f"Unique daily PERMNOs: "
        f"{summary['PERMNO'].nunique():,}"
    )

    return summary


# =============================================================================
# RECONCILIATION
# =============================================================================

def reconcile(
    names: pd.DataFrame,
    daily_summary: pd.DataFrame,
) -> pd.DataFrame:
    """
    Reconcile Names universe against daily history.
    """

    print_section(
        "RECONCILING NAMES AGAINST DAILY HISTORY"
    )

    names_permnos = set(
        names["PERMNO"]
        .dropna()
        .astype(int)
    )

    daily_permnos = set(
        daily_summary["PERMNO"]
        .dropna()
        .astype(int)
    )

    names_only = names_permnos - daily_permnos
    daily_only = daily_permnos - names_permnos
    both = names_permnos & daily_permnos

    print(
        f"Names PERMNOs:       {len(names_permnos):,}"
    )

    print(
        f"Daily PERMNOs:       {len(daily_permnos):,}"
    )

    print(
        f"Present in both:    {len(both):,}"
    )

    print(
        f"Names only:         {len(names_only):,}"
    )

    print(
        f"Daily only:         {len(daily_only):,}"
    )

    # -------------------------------------------------------------------------
    # Merge.
    # -------------------------------------------------------------------------

    reconciliation = names.merge(
        daily_summary,
        on="PERMNO",
        how="outer",
        indicator=True,
    )

    reconciliation["in_names_universe"] = (
        reconciliation["_merge"]
        .isin(
            [
                "both",
                "left_only",
            ]
        )
    )

    reconciliation["in_daily_file"] = (
        reconciliation["_merge"]
        .isin(
            [
                "both",
                "right_only",
            ]
        )
    )

    reconciliation["reconciliation_status"] = (
        reconciliation["_merge"]
        .map(
            {
                "both": "NAMES_AND_DAILY",
                "left_only": "NAMES_ONLY",
                "right_only": "DAILY_ONLY",
            }
        )
    )

    reconciliation.drop(
        columns=["_merge"],
        inplace=True,
    )

    # -------------------------------------------------------------------------
    # Determine whether daily history exists.
    # -------------------------------------------------------------------------

    reconciliation["has_daily_history"] = (
        reconciliation[
            "daily_observations"
        ]
        .fillna(0)
        .gt(0)
    )

    # -------------------------------------------------------------------------
    # Order columns.
    # -------------------------------------------------------------------------

    preferred_columns = [
        "PERMNO",
        "PERMCO",
        "Ticker",
        "SecurityNm",
        "PrimaryExch",
        "SecurityType",
        "SecuritySubType",
        "ShareType",
        "SICCD",
        "NAICS",
        "in_names_universe",
        "in_daily_file",
        "has_daily_history",
        "daily_first_date",
        "daily_last_date",
        "daily_observations",
        "daily_trading_days",
        "reconciliation_status",
    ]

    existing_preferred = [
        column
        for column in preferred_columns
        if column in reconciliation.columns
    ]

    remaining_columns = [
        column
        for column in reconciliation.columns
        if column not in existing_preferred
    ]

    reconciliation = reconciliation[
        existing_preferred
        + remaining_columns
    ]

    return reconciliation


# =============================================================================
# VALIDATION
# =============================================================================

def validate_reconciliation(
    reconciliation: pd.DataFrame,
) -> None:
    """
    Validate reconciliation output.
    """

    print_section(
        "VALIDATING RECONCILIATION"
    )

    status_counts = (
        reconciliation[
            "reconciliation_status"
        ]
        .value_counts()
        .sort_index()
    )

    print(
        status_counts.to_string()
    )

    print()

    names_count = int(
        reconciliation[
            "in_names_universe"
        ].sum()
    )

    daily_count = int(
        reconciliation[
            "in_daily_file"
        ].sum()
    )

    both_count = int(
        (
            reconciliation[
                "reconciliation_status"
            ]
            == "NAMES_AND_DAILY"
        ).sum()
    )

    names_only_count = int(
        (
            reconciliation[
                "reconciliation_status"
            ]
            == "NAMES_ONLY"
        ).sum()
    )

    daily_only_count = int(
        (
            reconciliation[
                "reconciliation_status"
            ]
            == "DAILY_ONLY"
        ).sum()
    )

    print(
        f"Names universe securities: "
        f"{names_count:,}"
    )

    print(
        f"Daily securities:           "
        f"{daily_count:,}"
    )

    print(
        f"Present in both:            "
        f"{both_count:,}"
    )

    print(
        f"Names only:                 "
        f"{names_only_count:,}"
    )

    print(
        f"Daily only:                 "
        f"{daily_only_count:,}"
    )

    # -------------------------------------------------------------------------
    # Logical consistency.
    # -------------------------------------------------------------------------

    if (
        both_count
        + names_only_count
        != names_count
    ):
        raise AssertionError(
            "Names universe reconciliation "
            "counts do not agree."
        )

    if (
        both_count
        + daily_only_count
        != daily_count
    ):
        raise AssertionError(
            "Daily universe reconciliation "
            "counts do not agree."
        )

    # -------------------------------------------------------------------------
    # Names without daily history.
    # -------------------------------------------------------------------------

    names_without_daily_history = (
        reconciliation[
            reconciliation["in_names_universe"]
            & ~reconciliation[
                "has_daily_history"
            ]
        ]
    )

    print(
        "Names securities without daily history: "
        f"{len(names_without_daily_history):,}"
    )

    # -------------------------------------------------------------------------
    # PERMNO uniqueness.
    # -------------------------------------------------------------------------

    duplicate_permno = reconciliation[
        reconciliation["PERMNO"].duplicated(
            keep=False
        )
    ]

    if len(duplicate_permno) > 0:

        print()
        print(
            duplicate_permno.to_string(
                index=False
            )
        )

        raise AssertionError(
            "Reconciliation output contains "
            "duplicate PERMNO rows."
        )

    print(
        "PASS   Reconciliation contains "
        "one row per PERMNO."
    )


# =============================================================================
# WRITE OUTPUTS
# =============================================================================

def write_outputs(
    reconciliation: pd.DataFrame,
) -> None:
    """
    Write reconciliation and discrepancy files.
    """

    print_section(
        "WRITING RECONCILIATION OUTPUTS"
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    reconciliation.to_csv(
        RECONCILIATION_OUTPUT,
        index=False,
    )

    discrepancies = reconciliation[
        reconciliation[
            "reconciliation_status"
        ]
        != "NAMES_AND_DAILY"
    ].copy()

    discrepancies.to_csv(
        DISCREPANCY_OUTPUT,
        index=False,
    )

    print(
        f"Reconciliation output:\n"
        f"{RECONCILIATION_OUTPUT}"
    )

    print()

    print(
        f"Discrepancy output:\n"
        f"{DISCREPANCY_OUTPUT}"
    )

    print()

    print(
        f"Total PERMNOs reconciled: "
        f"{len(reconciliation):,}"
    )

    print(
        f"Discrepancies identified: "
        f"{len(discrepancies):,}"
    )


# =============================================================================
# PRINT DISCREPANCIES
# =============================================================================

def print_discrepancies(
    reconciliation: pd.DataFrame,
) -> None:
    """
    Print Names-only and Daily-only securities.
    """

    print_section(
        "PERMNO DISCREPANCIES"
    )

    names_only = reconciliation[
        reconciliation[
            "reconciliation_status"
        ]
        == "NAMES_ONLY"
    ]

    daily_only = reconciliation[
        reconciliation[
            "reconciliation_status"
        ]
        == "DAILY_ONLY"
    ]

    print(
        "NAMES ONLY"
    )

    print(
        "-" * 80
    )

    if names_only.empty:

        print(
            "None"
        )

    else:

        columns = [
            column
            for column in [
                "PERMNO",
                "PERMCO",
                "Ticker",
                "SecurityNm",
                "SecurityType",
                "SecuritySubType",
            ]
            if column in names_only.columns
        ]

        print(
            names_only[columns]
            .to_string(
                index=False
            )
        )

    print()

    print(
        "DAILY ONLY"
    )

    print(
        "-" * 80
    )

    if daily_only.empty:

        print(
            "None"
        )

    else:

        columns = [
            column
            for column in [
                "PERMNO",
                "PERMCO",
                "Ticker",
                "SecurityNm",
                "SecurityType",
                "SecuritySubType",
                "daily_first_date",
                "daily_last_date",
                "daily_observations",
            ]
            if column in daily_only.columns
        ]

        print(
            daily_only[columns]
            .to_string(
                index=False
            )
        )


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    """
    Run the complete reconciliation.
    """

    names = load_names_universe()

    daily = load_daily_file()

    daily_summary = build_daily_summary(
        daily
    )

    reconciliation = reconcile(
        names,
        daily_summary,
    )

    validate_reconciliation(
        reconciliation
    )

    print_discrepancies(
        reconciliation
    )

    write_outputs(
        reconciliation
    )

    print_section(
        "RECONCILIATION COMPLETE"
    )

    print(
        "Names universe has been reconciled "
        "against the cleaned CRSP daily history."
    )

if __name__ == "__main__":
    main()