from pathlib import Path
import re

import pandas as pd


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TAQ_PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "taq"
)

TAQ_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "taq"
    / "taq.csv"
)

SCHEMA_FILE = (
    TAQ_PROCESSED_DIR
    / "taq_schema_inventory.csv"
)

COLUMN_CLASSIFICATION_FILE = (
    TAQ_PROCESSED_DIR
    / "taq_column_classification.csv"
)

TEMPORAL_OUTPUT = (
    TAQ_PROCESSED_DIR
    / "taq_temporal_coverage.csv"
)

DATE_DIAGNOSTICS_OUTPUT = (
    TAQ_PROCESSED_DIR
    / "taq_date_diagnostics.csv"
)

TIMESTAMP_DIAGNOSTICS_OUTPUT = (
    TAQ_PROCESSED_DIR
    / "taq_timestamp_diagnostics.csv"
)


# =============================================================================
# CONFIGURATION
# =============================================================================

CHUNK_SIZE = 100_000

DATE_COLUMN = "date"

TIMESTAMP_NAME_PATTERNS = [
    "time",
    "timestamp",
    "datetime",
]


# =============================================================================
# HELPERS
# =============================================================================

def print_header(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def normalize_column(column):
    return (
        re.sub(
            r"[^a-z0-9]+",
            "_",
            str(column).strip().lower(),
        )
        .strip("_")
    )


def detect_timestamp_columns(columns):
    """
    Identify columns whose names appear to contain
    time/timestamp/datetime information.
    """

    detected = []

    for column in columns:

        normalized = normalize_column(column)

        if any(
            pattern in normalized
            for pattern in TIMESTAMP_NAME_PATTERNS
        ):
            detected.append(column)

    return detected


def parse_date_series(series):
    """
    Parse date values without modifying the source dataset.

    Invalid values become NaT.
    """

    return pd.to_datetime(
        series,
        errors="coerce",
    )


def parse_timestamp_series(series):
    """
    Parse timestamps while allowing mixed timestamp representations.

    Invalid values become NaT.
    """

    try:
        return pd.to_datetime(
            series,
            errors="coerce",
            format="mixed",
        )

    except TypeError:
        # Compatibility with older pandas versions.
        return pd.to_datetime(
            series,
            errors="coerce",
        )


def infer_timestamp_precision(parsed):
    """
    Infer the finest timestamp precision actually observed.

    Returns one of:

        nanosecond_or_finer
        microsecond
        millisecond
        second_or_coarser
        unknown
    """

    parsed = parsed.dropna()

    if parsed.empty:
        return None

    try:

        values = parsed.astype("int64")

        # Ignore missing values.
        values = values.dropna()

        if values.empty:
            return None

        # If any timestamp has sub-microsecond precision.
        if (values % 1_000 != 0).any():
            return "nanosecond_or_finer"

        # If any timestamp has sub-millisecond precision.
        if (values % 1_000_000 != 0).any():
            return "microsecond"

        # If any timestamp has sub-second precision.
        if (values % 1_000_000_000 != 0).any():
            return "millisecond"

        return "second_or_coarser"

    except Exception:
        return "unknown"


def infer_time_character(series, parsed):
    """
    Determine whether the field appears to contain:

        TIME_ONLY
        DATETIME
        DATE
        DATETIME_OR_DATE_PARSEABLE
        UNCLASSIFIED
    """

    non_null = series.dropna()

    if non_null.empty:
        return "NO_NON_NULL_VALUES"

    text_values = (
        non_null
        .astype(str)
        .str.strip()
    )

    # -------------------------------------------------------------------------
    # TIME ONLY
    # Examples:
    #
    # 09:30:00
    # 09:30:00.123
    # -------------------------------------------------------------------------

    time_only_pattern = text_values.str.match(
        r"^\d{1,2}:\d{2}:\d{2}(?:\.\d+)?$",
        na=False,
    )

    if time_only_pattern.mean() >= 0.80:
        return "TIME_ONLY"

    # -------------------------------------------------------------------------
    # DATETIME
    #
    # Examples:
    #
    # 1993-01-04 09:30:00
    # 1993/01/04 09:30:00
    # 1993-01-04T09:30:00
    # -------------------------------------------------------------------------

    datetime_pattern = text_values.str.match(
        r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}[T\s].*\d{1,2}:\d{2}",
        na=False,
    )

    if datetime_pattern.mean() >= 0.80:
        return "DATETIME"

    # -------------------------------------------------------------------------
    # DATE
    # -------------------------------------------------------------------------

    date_pattern = text_values.str.match(
        r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$",
        na=False,
    )

    if date_pattern.mean() >= 0.80:
        return "DATE"

    # -------------------------------------------------------------------------
    # PARSEABLE
    # -------------------------------------------------------------------------

    if parsed.notna().mean() >= 0.80:
        return "DATETIME_OR_DATE_PARSEABLE"

    return "UNCLASSIFIED"


# =============================================================================
# LOAD COLUMN INFORMATION
# =============================================================================

def load_schema_information():

    if not SCHEMA_FILE.exists():

        raise FileNotFoundError(
            f"Schema inventory not found:\n"
            f"{SCHEMA_FILE}\n\n"
            f"Run inspect_taq_schema.py first."
        )

    schema = pd.read_csv(
        SCHEMA_FILE
    )

    if schema.empty:

        raise ValueError(
            "Schema inventory is empty."
        )

    return schema


def load_column_classification():

    if not COLUMN_CLASSIFICATION_FILE.exists():

        raise FileNotFoundError(
            f"Column classification not found:\n"
            f"{COLUMN_CLASSIFICATION_FILE}\n\n"
            f"Run classify_taq_data.py first."
        )

    classification = pd.read_csv(
        COLUMN_CLASSIFICATION_FILE
    )

    return classification


# =============================================================================
# DATE + TIMESTAMP DISCOVERY
# =============================================================================

def discover_columns(
    schema,
    classification,
):

    columns = (
        schema["column"]
        .dropna()
        .astype(str)
        .tolist()
    )

    if DATE_COLUMN not in columns:

        raise ValueError(
            f"Required date column '{DATE_COLUMN}' "
            f"was not found in the observed schema."
        )

    timestamp_columns = detect_timestamp_columns(
        columns
    )

    # -------------------------------------------------------------------------
    # Include columns explicitly classified as timestamp fields.
    # -------------------------------------------------------------------------

    if not classification.empty:

        required_classification_columns = {
            "column",
            "column_class",
        }

        missing = (
            required_classification_columns
            - set(classification.columns)
        )

        if not missing:

            classified_timestamp_columns = (
                classification.loc[
                    classification["column_class"].isin(
                        [
                            "QUOTE_TIMESTAMP",
                            "TRADE_OR_EVENT_TIMESTAMP",
                        ]
                    ),
                    "column",
                ]
                .dropna()
                .astype(str)
                .tolist()
            )

            timestamp_columns.extend(
                classified_timestamp_columns
            )

    timestamp_columns = sorted(
        set(timestamp_columns)
    )

    return columns, timestamp_columns


# =============================================================================
# TEMPORAL SCAN
# =============================================================================

def scan_dataset(
    columns,
    timestamp_columns,
):

    if not TAQ_FILE.exists():

        raise FileNotFoundError(
            f"TAQ source file not found:\n"
            f"{TAQ_FILE}"
        )

    print()
    print(f"Source file: {TAQ_FILE}")
    print(f"Chunk size: {CHUNK_SIZE:,}")

    date_records = []

    timestamp_records = []

    total_rows = 0

    malformed_date_rows = 0

    missing_date_rows = 0

    date_counts = {}

    symbol_counts = {}

    date_symbol_counts = {}

    # -------------------------------------------------------------------------
    # Only load fields necessary for this stage.
    # -------------------------------------------------------------------------

    usecols = [
        DATE_COLUMN,
        "symbol",
    ]

    for column in timestamp_columns:

        if column not in usecols:

            usecols.append(column)

    # -------------------------------------------------------------------------
    # Verify requested columns exist.
    # -------------------------------------------------------------------------

    missing_columns = [
        column
        for column in usecols
        if column not in columns
    ]

    if missing_columns:

        raise ValueError(
            "Required columns missing from source:\n"
            + "\n".join(
                f"  - {column}"
                for column in missing_columns
            )
        )

    # -------------------------------------------------------------------------
    # Chunked scan
    # -------------------------------------------------------------------------

    reader = pd.read_csv(
        TAQ_FILE,
        usecols=usecols,
        chunksize=CHUNK_SIZE,
        low_memory=False,
    )

    for chunk_number, chunk in enumerate(
        reader,
        start=1,
    ):

        print(
            f"Processing chunk {chunk_number:,} "
            f"({len(chunk):,} rows)"
        )

        total_rows += len(chunk)

        # =====================================================================
        # DATE
        # =====================================================================

        original_date = chunk[
            DATE_COLUMN
        ]

        parsed_date = parse_date_series(
            original_date
        )

        missing_mask = original_date.isna()

        malformed_mask = (
            original_date.notna()
            & parsed_date.isna()
        )

        missing_date_rows += int(
            missing_mask.sum()
        )

        malformed_date_rows += int(
            malformed_mask.sum()
        )

        valid_dates = parsed_date[
            parsed_date.notna()
        ]

        if not valid_dates.empty:

            date_counts_chunk = (
                valid_dates
                .dt.normalize()
                .value_counts()
            )

            for date, count in date_counts_chunk.items():

                key = date.date()

                date_counts[key] = (
                    date_counts.get(
                        key,
                        0,
                    )
                    + int(count)
                )

        # =====================================================================
        # SYMBOL
        # =====================================================================

        symbol = chunk[
            "symbol"
        ]

        symbol_counts_chunk = (
            symbol
            .dropna()
            .astype(str)
            .value_counts()
        )

        for symbol_value, count in (
            symbol_counts_chunk.items()
        ):

            symbol_counts[symbol_value] = (
                symbol_counts.get(
                    symbol_value,
                    0,
                )
                + int(count)
            )

        # =====================================================================
        # DATE + SYMBOL
        # =====================================================================

        valid_mask = (
            parsed_date.notna()
            & symbol.notna()
        )

        if valid_mask.any():

            date_symbol = pd.DataFrame(
                {
                    "date": (
                        parsed_date[
                            valid_mask
                        ]
                        .dt.normalize()
                    ),
                    "symbol": (
                        symbol[
                            valid_mask
                        ]
                        .astype(str)
                    ),
                }
            )

            grouped = (
                date_symbol
                .value_counts()
            )

            for (
                date_value,
                symbol_value,
            ), count in grouped.items():

                key = (
                    date_value.date(),
                    symbol_value,
                )

                date_symbol_counts[key] = (
                    date_symbol_counts.get(
                        key,
                        0,
                    )
                    + int(count)
                )

        # =====================================================================
        # TIMESTAMP DIAGNOSTICS
        # =====================================================================

        for timestamp_column in timestamp_columns:

            series = chunk[
                timestamp_column
            ]

            parsed = parse_timestamp_series(
                series
            )

            non_null = int(
                series.notna().sum()
            )

            parse_failures = int(
                (
                    series.notna()
                    & parsed.isna()
                ).sum()
            )

            timestamp_records.append(
                {
                    "column": timestamp_column,

                    "chunk_rows": len(chunk),

                    "non_null_count": non_null,

                    "parse_failure_count": (
                        parse_failures
                    ),

                    "parse_failure_rate": (
                        parse_failures / non_null
                        if non_null > 0
                        else None
                    ),

                    "min_timestamp": (
                        parsed.min()
                        if parsed.notna().any()
                        else None
                    ),

                    "max_timestamp": (
                        parsed.max()
                        if parsed.notna().any()
                        else None
                    ),

                    "timestamp_precision": (
                        infer_timestamp_precision(
                            parsed
                        )
                    ),

                    "time_character": (
                        infer_time_character(
                            series,
                            parsed,
                        )
                    ),
                }
            )

    # =========================================================================
    # CONSOLIDATE TIMESTAMP DIAGNOSTICS
    # =========================================================================

    timestamp_df = pd.DataFrame(
        timestamp_records
    )

    if not timestamp_df.empty:

        timestamp_summary = (
            timestamp_df
            .groupby(
                "column",
                as_index=False,
            )
            .agg(
                chunks_processed=(
                    "chunk_rows",
                    "count",
                ),

                rows_observed=(
                    "chunk_rows",
                    "sum",
                ),

                non_null_count=(
                    "non_null_count",
                    "sum",
                ),

                parse_failure_count=(
                    "parse_failure_count",
                    "sum",
                ),

                min_timestamp=(
                    "min_timestamp",
                    "min",
                ),

                max_timestamp=(
                    "max_timestamp",
                    "max",
                ),
            )
        )

        timestamp_summary[
            "parse_failure_rate"
        ] = (
            timestamp_summary[
                "parse_failure_count"
            ]
            /
            timestamp_summary[
                "non_null_count"
            ].replace(0, pd.NA)
        )

        # ---------------------------------------------------------------------
        # Precision observed across chunks.
        # ---------------------------------------------------------------------

        precision_map = (
            timestamp_df
            .groupby("column")[
                "timestamp_precision"
            ]
            .agg(
                lambda x:
                ";".join(
                    sorted(
                        set(
                            str(v)
                            for v in x
                            if pd.notna(v)
                        )
                    )
                )
            )
        )

        # ---------------------------------------------------------------------
        # Time character observed across chunks.
        # ---------------------------------------------------------------------

        character_map = (
            timestamp_df
            .groupby("column")[
                "time_character"
            ]
            .agg(
                lambda x:
                ";".join(
                    sorted(
                        set(
                            str(v)
                            for v in x
                            if pd.notna(v)
                        )
                    )
                )
            )
        )

        timestamp_summary[
            "timestamp_precision_observed"
        ] = timestamp_summary[
            "column"
        ].map(
            precision_map
        )

        timestamp_summary[
            "time_character_observed"
        ] = timestamp_summary[
            "column"
        ].map(
            character_map
        )

    else:

        timestamp_summary = pd.DataFrame()

    # =========================================================================
    # DATE SUMMARY
    # =========================================================================

    if date_counts:

        date_series = pd.Series(
            date_counts,
            name="record_count",
        )

        date_series.index = pd.to_datetime(
            date_series.index
        )

        date_series = (
            date_series
            .sort_index()
        )

        date_df = (
            date_series
            .rename_axis("date")
            .reset_index()
        )

    else:

        date_df = pd.DataFrame(
            columns=[
                "date",
                "record_count",
            ]
        )

    # =========================================================================
    # DUPLICATE DATE + SYMBOL CANDIDATES
    # =========================================================================

    duplicate_pairs = {
        key: count
        for key, count
        in date_symbol_counts.items()
        if count > 1
    }

    duplicate_date_symbol_candidates = sum(
        count - 1
        for count in duplicate_pairs.values()
    )

    return {
        "total_rows": total_rows,

        "date_counts": date_counts,

        "symbol_counts": symbol_counts,

        "date_symbol_counts": date_symbol_counts,

        "date_df": date_df,

        "timestamp_summary": timestamp_summary,

        "missing_date_rows": missing_date_rows,

        "malformed_date_rows": malformed_date_rows,

        "duplicate_date_symbol_candidates": (
            duplicate_date_symbol_candidates
        ),
    }


# =============================================================================
# BUILD TEMPORAL COVERAGE
# =============================================================================

def build_temporal_coverage(results):

    date_df = results[
        "date_df"
    ]

    total_rows = results[
        "total_rows"
    ]

    if date_df.empty:

        first_date = None
        last_date = None
        unique_dates = 0
        date_gaps = None

    else:

        first_date = date_df[
            "date"
        ].min()

        last_date = date_df[
            "date"
        ].max()

        unique_dates = date_df[
            "date"
        ].nunique()

        full_calendar = pd.date_range(
            first_date,
            last_date,
            freq="D",
        )

        observed_dates = pd.DatetimeIndex(
            date_df["date"]
        )

        missing_calendar_dates = (
            full_calendar
            .difference(observed_dates)
        )

        date_gaps = len(
            missing_calendar_dates
        )

    unique_symbols = len(
        results[
            "symbol_counts"
        ]
    )

    coverage = pd.DataFrame(
        [
            {
                "dataset": "taq.csv",

                "source_path": str(
                    TAQ_FILE
                ),

                "total_rows": total_rows,

                "first_date": first_date,

                "last_date": last_date,

                "unique_dates": unique_dates,

                "unique_symbols": unique_symbols,

                "missing_date_rows": (
                    results[
                        "missing_date_rows"
                    ]
                ),

                "malformed_date_rows": (
                    results[
                        "malformed_date_rows"
                    ]
                ),

                "date_symbol_duplicate_candidates": (
                    results[
                        "duplicate_date_symbol_candidates"
                    ]
                ),

                "calendar_date_gaps": date_gaps,

                "expected_or_observed_frequency": (
                    "OBSERVED_DAILY_SECURITY_LEVEL"
                ),

                "timestamp_columns": (
                    ", ".join(
                        results[
                            "timestamp_summary"
                        ]["column"].tolist()
                    )
                    if not results[
                        "timestamp_summary"
                    ].empty
                    else None
                ),
            }
        ]
    )

    return coverage


# =============================================================================
# BUILD DATE DIAGNOSTICS
# =============================================================================

def build_date_diagnostics(results):

    date_df = results[
        "date_df"
    ].copy()

    if date_df.empty:
        return pd.DataFrame()

    # -------------------------------------------------------------------------
    # Calendar information
    # -------------------------------------------------------------------------

    date_df[
        "day_of_week"
    ] = (
        date_df[
            "date"
        ]
        .dt.day_name()
    )

    date_df[
        "year"
    ] = (
        date_df[
            "date"
        ]
        .dt.year
    )

    date_df[
        "month"
    ] = (
        date_df[
            "date"
        ]
        .dt.month
    )

    date_df[
        "year_month"
    ] = (
        date_df[
            "date"
        ]
        .dt.to_period("M")
        .astype(str)
    )

    # -------------------------------------------------------------------------
    # Difference from previous observed date
    # -------------------------------------------------------------------------

    date_df[
        "days_since_previous_observed_date"
    ] = (
        date_df[
            "date"
        ]
        .diff()
        .dt.days
    )

    date_df[
        "gap_after_previous_date"
    ] = (
        date_df[
            "days_since_previous_observed_date"
        ]
        > 1
    )

    # -------------------------------------------------------------------------
    # Record-count diagnostics
    # -------------------------------------------------------------------------

    median_count = date_df[
        "record_count"
    ].median()

    if (
        pd.notna(median_count)
        and median_count > 0
    ):

        date_df[
            "record_count_vs_median"
        ] = (
            date_df[
                "record_count"
            ]
            / median_count
        )

        date_df[
            "unusually_low_record_count"
        ] = (
            date_df[
                "record_count"
            ]
            < 0.50 * median_count
        )

        date_df[
            "unusually_high_record_count"
        ] = (
            date_df[
                "record_count"
            ]
            > 2.00 * median_count
        )

    else:

        date_df[
            "record_count_vs_median"
        ] = None

        date_df[
            "unusually_low_record_count"
        ] = False

        date_df[
            "unusually_high_record_count"
        ] = False

    return date_df


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_header(
        "PHASE 5 — STEP 4: "
        "TEMPORAL COVERAGE & TIMESTAMP VALIDATION"
    )

    # =========================================================================
    # LOAD METADATA
    # =========================================================================

    schema = load_schema_information()

    classification = (
        load_column_classification()
    )

    columns, timestamp_columns = (
        discover_columns(
            schema,
            classification,
        )
    )

    print()

    print(
        f"Observed columns: "
        f"{len(columns)}"
    )

    print(
        f"Date column: "
        f"{DATE_COLUMN}"
    )

    print(
        "Timestamp columns:"
    )

    for column in timestamp_columns:

        print(
            f"  - {column}"
        )

    # =========================================================================
    # SCAN DATASET
    # =========================================================================

    results = scan_dataset(
        columns,
        timestamp_columns,
    )

    # =========================================================================
    # BUILD OUTPUTS
    # =========================================================================

    temporal_coverage = (
        build_temporal_coverage(
            results
        )
    )

    date_diagnostics = (
        build_date_diagnostics(
            results
        )
    )

    timestamp_diagnostics = (
        results[
            "timestamp_summary"
        ]
    )

    # =========================================================================
    # SAVE OUTPUTS
    # =========================================================================

    TAQ_PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporal_coverage.to_csv(
        TEMPORAL_OUTPUT,
        index=False,
    )

    date_diagnostics.to_csv(
        DATE_DIAGNOSTICS_OUTPUT,
        index=False,
    )

    timestamp_diagnostics.to_csv(
        TIMESTAMP_DIAGNOSTICS_OUTPUT,
        index=False,
    )

    # =========================================================================
    # CONSOLE SUMMARY
    # =========================================================================

    print_header(
        "TEMPORAL COVERAGE SUMMARY"
    )

    if not temporal_coverage.empty:

        row = (
            temporal_coverage
            .iloc[0]
        )

        print(
            f"Total rows:              "
            f"{row['total_rows']:,}"
        )

        print(
            f"First date:              "
            f"{row['first_date']}"
        )

        print(
            f"Last date:               "
            f"{row['last_date']}"
        )

        print(
            f"Unique dates:            "
            f"{row['unique_dates']:,}"
        )

        print(
            f"Unique symbols:          "
            f"{row['unique_symbols']:,}"
        )

        print(
            f"Missing date rows:       "
            f"{row['missing_date_rows']:,}"
        )

        print(
            f"Malformed date rows:     "
            f"{row['malformed_date_rows']:,}"
        )

        print(
            f"Date+symbol duplicate "
            f"candidates:             "
            f"{row['date_symbol_duplicate_candidates']:,}"
        )

        print(
            f"Calendar gaps:           "
            f"{row['calendar_date_gaps']}"
        )

    # =========================================================================
    # TIMESTAMP SUMMARY
    # =========================================================================

    print_header(
        "TIMESTAMP SUMMARY"
    )

    if timestamp_diagnostics.empty:

        print(
            "No timestamp columns detected."
        )

    else:

        display_columns = [
            "column",
            "rows_observed",
            "non_null_count",
            "parse_failure_count",
            "parse_failure_rate",
            "min_timestamp",
            "max_timestamp",
            "timestamp_precision_observed",
            "time_character_observed",
        ]

        print(
            timestamp_diagnostics[
                display_columns
            ].to_string(
                index=False
            )
        )

    # =========================================================================
    # OUTPUTS
    # =========================================================================

    print_header(
        "OUTPUTS"
    )

    print(
        f"Temporal coverage:\n"
        f"{TEMPORAL_OUTPUT}"
    )

    print(
        f"\nDate diagnostics:\n"
        f"{DATE_DIAGNOSTICS_OUTPUT}"
    )

    print(
        f"\nTimestamp diagnostics:\n"
        f"{TIMESTAMP_DIAGNOSTICS_OUTPUT}"
    )


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()