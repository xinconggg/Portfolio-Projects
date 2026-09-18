from __future__ import annotations

import sys
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
    / "CRSP_Names.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "crsp"
)

CLEAN_PATH = OUTPUT_DIR / "crsp_names_clean.csv"
REPORT_PATH = OUTPUT_DIR / "crsp_names_cleaning_report.csv"


# =============================================================================
# ACTUAL CRSP NAMES SCHEMA
# =============================================================================

EXPECTED_COLUMNS = [
    "ticker",
    "permno",
    "permco",
    "secinfostartdt",
    "secinfoenddt",
    "securitybegdt",
    "securityenddt",
    "cusip",
    "issuernm",
    "shareclass",
    "usincflg",
    "issuertype",
    "securitytype",
    "securitysubtype",
    "sharetype",
    "siccd",
    "primaryexch",
    "tradingsymbol",
    "naics",
    "tradingstatusflg",
]


DATE_COLUMNS = [
    "secinfostartdt",
    "secinfoenddt",
    "securitybegdt",
    "securityenddt",
]


NUMERIC_COLUMNS = [
    "permno",
    "permco",
    "siccd",
    "naics",
]


STRING_COLUMNS = [
    "ticker",
    "cusip",
    "issuernm",
    "shareclass",
    "usincflg",
    "issuertype",
    "securitytype",
    "securitysubtype",
    "sharetype",
    "primaryexch",
    "tradingsymbol",
    "tradingstatusflg",
]


# =============================================================================
# HELPERS
# =============================================================================

def print_header(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names without changing the underlying raw data.

    CRSP Names was supplied with lowercase field names. We standardize:
    - whitespace
    - capitalization
    - accidental surrounding spaces
    """

    df = df.copy()

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
    )

    return df


def normalize_strings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize string fields conservatively.

    Missing values remain missing.
    No identifier values are imputed or otherwise reconstructed.
    """

    for column in STRING_COLUMNS:

        if column not in df.columns:
            continue

        df[column] = df[column].astype("string")

        df[column] = (
            df[column]
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
        )

        df[column] = df[column].replace(
            "",
            pd.NA,
        )

    return df


def parse_dates(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:

    invalid_counts: dict[str, int] = {}

    for column in DATE_COLUMNS:

        original = df[column]

        parsed = pd.to_datetime(
            original,
            errors="coerce",
            dayfirst=True,
        )

        invalid = int(
            (
                original.notna()
                & parsed.isna()
            ).sum()
        )

        invalid_counts[column] = invalid

        df[column] = parsed

    return df, invalid_counts


# =============================================================================
# MAIN
# =============================================================================

def clean_names() -> None:

    # =========================================================================
    # LOAD
    # =========================================================================

    print_header("LOADING CRSP NAMES FILE")

    if not RAW_PATH.exists():
        raise FileNotFoundError(
            f"CRSP Names file does not exist:\n{RAW_PATH}"
        )

    df = pd.read_csv(
        RAW_PATH,
        dtype="string",
        low_memory=False,
    )

    raw_rows = len(df)
    raw_columns = len(df.columns)

    print(f"File: {RAW_PATH}")
    print(f"Rows loaded: {raw_rows:,}")
    print(f"Columns loaded: {raw_columns}")

    # =========================================================================
    # NORMALIZE COLUMN NAMES
    # =========================================================================

    print_header("NORMALIZING COLUMN NAMES")

    original_columns = df.columns.tolist()

    df = normalize_column_names(df)

    print("Original columns:")
    print(" | ".join(original_columns))

    print()
    print("Normalized columns:")
    print(" | ".join(df.columns.tolist()))

    # =========================================================================
    # COLUMN VALIDATION
    # =========================================================================

    print_header("COLUMN VALIDATION")

    missing_columns = [
        column
        for column in EXPECTED_COLUMNS
        if column not in df.columns
    ]

    unexpected_columns = [
        column
        for column in df.columns
        if column not in EXPECTED_COLUMNS
    ]

    print(
        f"Missing expected columns: "
        f"{len(missing_columns)}"
    )

    if missing_columns:
        for column in missing_columns:
            print(f"  MISSING: {column}")

    print(
        f"Unexpected columns: "
        f"{len(unexpected_columns)}"
    )

    if unexpected_columns:
        for column in unexpected_columns:
            print(f"  EXTRA: {column}")

    if missing_columns:
        raise ValueError(
            "CRSP Names schema validation failed."
        )

    # =========================================================================
    # STANDARDIZATION
    # =========================================================================

    print_header("STANDARDIZING DATA TYPES")

    # Numeric fields.
    for column in NUMERIC_COLUMNS:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    # String fields.
    df = normalize_strings(df)

    # Date fields.
    df, invalid_date_counts = parse_dates(df)

    print("Numeric fields coerced.")
    print("String fields normalized.")
    print("Date fields parsed.")

    # =========================================================================
    # IDENTIFIER VALIDATION
    # =========================================================================

    print_header("IDENTIFIER VALIDATION")

    missing_permno = int(
        df["permno"].isna().sum()
    )

    invalid_permno = int(
        (
            df["permno"].notna()
            & (df["permno"] <= 0)
        ).sum()
    )

    missing_permco = int(
        df["permco"].isna().sum()
    )

    invalid_permco = int(
        (
            df["permco"].notna()
            & (df["permco"] <= 0)
        ).sum()
    )

    unique_permnos = int(
        df["permno"].nunique(
            dropna=True
        )
    )

    unique_permcos = int(
        df["permco"].nunique(
            dropna=True
        )
    )

    print(
        f"Missing PERMNO:       "
        f"{missing_permno:,}"
    )

    print(
        f"Invalid PERMNO <= 0:  "
        f"{invalid_permno:,}"
    )

    print(
        f"Unique PERMNOs:       "
        f"{unique_permnos:,}"
    )

    print()

    print(
        f"Missing PERMCO:       "
        f"{missing_permco:,}"
    )

    print(
        f"Invalid PERMCO <= 0:  "
        f"{invalid_permco:,}"
    )

    print(
        f"Unique PERMCOs:       "
        f"{unique_permcos:,}"
    )

    # =========================================================================
    # DATE VALIDATION
    # =========================================================================

    print_header("DATE VALIDATION")

    for column in DATE_COLUMNS:

        print(
            f"{column} invalid: "
            f"{invalid_date_counts[column]:,}"
        )

    # Security-information interval.
    invalid_secinfo_interval = int(
        (
            df["secinfostartdt"].notna()
            & df["secinfoenddt"].notna()
            & (
                df["secinfostartdt"]
                > df["secinfoenddt"]
            )
        ).sum()
    )

    # Security trading interval.
    invalid_security_interval = int(
        (
            df["securitybegdt"].notna()
            & df["securityenddt"].notna()
            & (
                df["securitybegdt"]
                > df["securityenddt"]
            )
        ).sum()
    )

    print(
        "SecInfoStartDt > SecInfoEndDt: "
        f"{invalid_secinfo_interval:,}"
    )

    print(
        "SecurityBegDt > SecurityEndDt: "
        f"{invalid_security_interval:,}"
    )

    # =========================================================================
    # PERMNO / PERMCO RELATIONSHIP
    # =========================================================================

    print_header("PERMNO / PERMCO RELATIONSHIP")

    permno_permco = (
        df.dropna(
            subset=["permno", "permco"]
        )
        .groupby("permno")["permco"]
        .nunique()
    )

    permnos_multiple_permco = int(
        (permno_permco > 1).sum()
    )

    print(
        "PERMNOs associated with >1 PERMCO: "
        f"{permnos_multiple_permco:,}"
    )

    # =========================================================================
    # PERMNO / TICKER RELATIONSHIP
    # =========================================================================

    print_header("PERMNO / TICKER RELATIONSHIP")

    permno_ticker = (
        df.dropna(
            subset=["permno", "ticker"]
        )
        .groupby("permno")["ticker"]
        .nunique()
    )

    permnos_multiple_ticker = int(
        (permno_ticker > 1).sum()
    )

    print(
        "PERMNOs associated with >1 ticker: "
        f"{permnos_multiple_ticker:,}"
    )

    if permnos_multiple_ticker:

        print()
        print(
            "Examples of PERMNOs with multiple "
            "tickers:"
        )

        examples = (
            permno_ticker[
                permno_ticker > 1
            ]
            .head(10)
        )

        for permno in examples.index:

            tickers = sorted(
                df.loc[
                    df["permno"] == permno,
                    "ticker",
                ]
                .dropna()
                .unique()
                .tolist()
            )

            print(
                f"  PERMNO {int(permno)}: "
                f"{tickers}"
            )

    # =========================================================================
    # SECURITY INTERVAL OVERLAP ANALYSIS
    # =========================================================================

    print_header("SECURITY INTERVAL ANALYSIS")

    interval_df = (
        df[
            [
                "permno",
                "secinfostartdt",
                "secinfoenddt",
            ]
        ]
        .dropna(
            subset=[
                "permno",
                "secinfostartdt",
                "secinfoenddt",
            ]
        )
        .sort_values(
            [
                "permno",
                "secinfostartdt",
                "secinfoenddt",
            ]
        )
    )

    overlapping_intervals = 0

    for _, group in interval_df.groupby(
        "permno",
        sort=False,
    ):

        previous_end = None

        for row in group.itertuples():

            start = row.secinfostartdt
            end = row.secinfoenddt

            if (
                previous_end is not None
                and start <= previous_end
            ):
                overlapping_intervals += 1

            if (
                previous_end is None
                or end > previous_end
            ):
                previous_end = end

    print(
        "Overlapping security-information "
        f"intervals: {overlapping_intervals:,}"
    )

    # =========================================================================
    # EXACT DUPLICATES
    # =========================================================================

    print_header("EXACT DUPLICATE ANALYSIS")

    exact_duplicate_mask = df.duplicated(
        keep=False
    )

    exact_duplicate_rows = int(
        exact_duplicate_mask.sum()
    )

    exact_duplicate_records = int(
        df[
            exact_duplicate_mask
        ]
        .drop_duplicates()
        .shape[0]
    )

    print(
        "Rows belonging to exact duplicate "
        f"groups: {exact_duplicate_rows:,}"
    )

    print(
        "Distinct duplicated records: "
        f"{exact_duplicate_records:,}"
    )

    # =========================================================================
    # CLEANING POLICY
    # =========================================================================

    print_header("CLEANING POLICY")

    print(
        "Column names standardized to lowercase."
    )

    print(
        "String fields stripped and normalized."
    )

    print(
        "Numeric fields coerced to numeric."
    )

    print(
        "Date fields parsed without changing "
        "their semantic values."
    )

    print(
        "No identifiers are imputed."
    )

    print(
        "No historical security intervals are "
        "modified."
    )

    print(
        "Only exact duplicate records are removed."
    )

    # =========================================================================
    # REMOVE EXACT DUPLICATES
    # =========================================================================

    before_dedup = len(df)

    df = (
        df
        .drop_duplicates(
            keep="first"
        )
        .reset_index(drop=True)
    )

    exact_duplicates_removed = (
        before_dedup - len(df)
    )

    print(
        f"Exact duplicate rows removed: "
        f"{exact_duplicates_removed:,}"
    )

    print(
        f"Rows after duplicate resolution: "
        f"{len(df):,}"
    )

    # =========================================================================
    # FINAL DUPLICATE VALIDATION
    # =========================================================================

    print_header("FINAL DUPLICATE VALIDATION")

    remaining_exact_duplicates = int(
        df.duplicated(
            keep=False
        ).sum()
    )

    print(
        "Remaining exact duplicate rows: "
        f"{remaining_exact_duplicates:,}"
    )

    # =========================================================================
    # QUALITY FLAGS
    # =========================================================================

    print_header("GENERATING QUALITY FLAGS")

    quality_flags = pd.DataFrame(
        {
            "invalid_secinfo_interval": (
                df["secinfostartdt"].notna()
                & df["secinfoenddt"].notna()
                & (
                    df["secinfostartdt"]
                    > df["secinfoenddt"]
                )
            ),

            "invalid_security_interval": (
                df["securitybegdt"].notna()
                & df["securityenddt"].notna()
                & (
                    df["securitybegdt"]
                    > df["securityenddt"]
                )
            ),

            "missing_permno": (
                df["permno"].isna()
            ),

            "invalid_permno": (
                df["permno"].notna()
                & (df["permno"] <= 0)
            ),

            "missing_permco": (
                df["permco"].isna()
            ),

            "invalid_permco": (
                df["permco"].notna()
                & (df["permco"] <= 0)
            ),
        },
        index=df.index,
    )

    rows_with_quality_flags = int(
        quality_flags.any(axis=1).sum()
    )

    print(
        "Rows with at least one quality flag: "
        f"{rows_with_quality_flags:,}"
    )

    # =========================================================================
    # BUILD REPORT
    # =========================================================================

    print_header("BUILDING CLEANING REPORT")

    report_rows: list[dict[str, object]] = []

    def add_report(
        check: str,
        value: object,
        status: str,
    ) -> None:

        report_rows.append(
            {
                "check": check,
                "value": value,
                "status": status,
            }
        )

    add_report(
        "raw_rows",
        raw_rows,
        "INFO",
    )

    add_report(
        "raw_columns",
        raw_columns,
        "INFO",
    )

    add_report(
        "clean_rows",
        len(df),
        "INFO",
    )

    add_report(
        "clean_columns",
        len(df.columns),
        "INFO",
    )

    add_report(
        "exact_duplicate_rows_removed",
        exact_duplicates_removed,
        "INFO",
    )

    add_report(
        "remaining_exact_duplicates",
        remaining_exact_duplicates,
        (
            "PASS"
            if remaining_exact_duplicates == 0
            else "FAIL"
        ),
    )

    add_report(
        "missing_permno",
        missing_permno,
        (
            "PASS"
            if missing_permno == 0
            else "FAIL"
        ),
    )

    add_report(
        "invalid_permno",
        invalid_permno,
        (
            "PASS"
            if invalid_permno == 0
            else "FAIL"
        ),
    )

    add_report(
        "missing_permco",
        missing_permco,
        "INFO",
    )

    add_report(
        "invalid_permco",
        invalid_permco,
        (
            "PASS"
            if invalid_permco == 0
            else "FAIL"
        ),
    )

    add_report(
        "unique_permnos",
        unique_permnos,
        "INFO",
    )

    add_report(
        "unique_permcos",
        unique_permcos,
        "INFO",
    )

    add_report(
        "permnos_multiple_permco",
        permnos_multiple_permco,
        (
            "PASS"
            if permnos_multiple_permco == 0
            else "WARN"
        ),
    )

    add_report(
        "permnos_multiple_ticker",
        permnos_multiple_ticker,
        (
            "INFO"
            if permnos_multiple_ticker > 0
            else "PASS"
        ),
    )

    for column, count in invalid_date_counts.items():

        add_report(
            f"{column}_invalid",
            count,
            (
                "PASS"
                if count == 0
                else "FAIL"
            ),
        )

    add_report(
        "invalid_secinfo_interval",
        invalid_secinfo_interval,
        (
            "PASS"
            if invalid_secinfo_interval == 0
            else "FAIL"
        ),
    )

    add_report(
        "invalid_security_interval",
        invalid_security_interval,
        (
            "PASS"
            if invalid_security_interval == 0
            else "FAIL"
        ),
    )

    add_report(
        "overlapping_security_info_intervals",
        overlapping_intervals,
        (
            "PASS"
            if overlapping_intervals == 0
            else "WARN"
        ),
    )

    add_report(
        "rows_with_quality_flags",
        rows_with_quality_flags,
        "INFO",
    )

    report = pd.DataFrame(
        report_rows
    )

    # =========================================================================
    # WRITE OUTPUTS
    # =========================================================================

    print_header("WRITING OUTPUTS")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        CLEAN_PATH,
        index=False,
        date_format="%Y-%m-%d",
    )

    report.to_csv(
        REPORT_PATH,
        index=False,
    )

    print(
        f"Clean Names file:\n"
        f"{CLEAN_PATH}"
    )

    print(
        f"Cleaning report:\n"
        f"{REPORT_PATH}"
    )

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================

    print_header("CRSP NAMES CLEANING COMPLETE")

    print(
        f"Input rows:              {raw_rows:,}"
    )

    print(
        f"Output rows:             {len(df):,}"
    )

    print(
        f"Rows removed:            "
        f"{exact_duplicates_removed:,}"
    )

    print(
        f"Unique PERMNOs:          "
        f"{df['permno'].nunique(dropna=True):,}"
    )

    print(
        f"Unique PERMCOs:          "
        f"{df['permco'].nunique(dropna=True):,}"
    )

    print(
        f"Remaining exact duplicates: "
        f"{remaining_exact_duplicates:,}"
    )

    print()
    print("IMPORTANT:")
    print(
        "No identifiers were imputed."
    )
    print(
        "No historical security intervals "
        "were modified."
    )
    print(
        "Only exact duplicate records were removed."
    )


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    try:
        clean_names()

    except Exception as exc:

        print()
        print("=" * 80)
        print("CRSP NAMES CLEANING FAILED")
        print("=" * 80)
        print(str(exc))

        sys.exit(1)