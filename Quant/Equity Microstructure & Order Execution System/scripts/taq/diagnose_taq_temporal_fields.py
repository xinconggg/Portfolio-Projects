from pathlib import Path

import pandas as pd


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TAQ_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "taq"
    / "taq.csv"
)

TAQ_PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "taq"
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

SYMBOL_COLUMN = "symbol"


# =============================================================================
# CONFIRMED TEMPORAL FIELDS
# =============================================================================
#
# These were established from the actual source values during Step 4A.
#
# They contain clock times without embedded dates.
#
# Do NOT infer timestamp columns merely because "time" appears in the
# column name.
#

TIME_ONLY_COLUMNS = [
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


# Explicitly excluded from timestamp processing.
NON_TIMESTAMP_TIME_NAMED_COLUMNS = [
    "NumTimeUnitsWithTrade1",
    "NumTimeUnitsWithTrade2",
]


# =============================================================================
# HELPERS
# =============================================================================

def print_header(title):

    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def parse_date(series):

    """
    Parse the confirmed source date format.

    The source is DD/MM/YYYY.

    This explicit format is essential because the default pandas parser
    can incorrectly interpret dates such as 13/04/1993 or produce
    inconsistent results when day/month ordering is ambiguous.
    """

    return pd.to_datetime(
        series,
        format="%d/%m/%Y",
        errors="coerce",
    )


def parse_time(series):

    """
    Parse a time-only TAQ field.

    The source fields contain clock times such as:

        09:30:00
        13:00:00.000
        15:59:59.000

    The resulting pandas object may carry an arbitrary anchor date.

    That anchor date must NOT be interpreted as the trading date.
    """

    return pd.to_timedelta(
        series.astype("string"),
        errors="coerce",
    )


def classify_time_precision(series):

    """
    Determine observed precision from raw clock-time strings.
    """

    values = (
        series
        .dropna()
        .astype(str)
        .str.strip()
    )

    if values.empty:

        return "NO_NON_NULL_VALUES"

    has_fraction = (
        values.str.contains(
            r"\.",
            regex=True,
        )
    )

    if not has_fraction.any():

        return "SECOND"

    fractional = (
        values[
            has_fraction
        ]
        .str.extract(
            r"\.(\d+)",
            expand=False,
        )
        .dropna()
    )

    if fractional.empty:

        return "UNKNOWN"

    max_digits = (
        fractional
        .str.len()
        .max()
    )

    if max_digits <= 3:
        return "MILLISECOND"

    if max_digits <= 6:
        return "MICROSECOND"

    if max_digits <= 9:
        return "NANOSECOND"

    return "SUB_NANOSECOND_OR_UNKNOWN"


def validate_time_range(series):

    """
    Validate that time-only fields represent plausible clock times.

    We intentionally do not impose a regular-market-hours restriction.
    """

    parsed = parse_time(series)

    invalid_mask = (
        series.notna()
        & parsed.isna()
    )

    valid = parsed[
        parsed.notna()
    ]

    if valid.empty:

        return {
            "invalid_count": int(
                invalid_mask.sum()
            ),
            "min_time": None,
            "max_time": None,
            "outside_00_00_00_to_23_59_59": None,
        }

    day = pd.Timedelta(
        days=1
    )

    outside_day = (
        (valid < pd.Timedelta(0))
        |
        (valid >= day)
    )

    return {
        "invalid_count": int(
            invalid_mask.sum()
        ),
        "min_time": str(
            valid.min()
        ),
        "max_time": str(
            valid.max()
        ),
        "outside_00_00_00_to_23_59_59": int(
            outside_day.sum()
        ),
    }


# =============================================================================
# MAIN SCAN
# =============================================================================

def scan_dataset():

    if not TAQ_FILE.exists():

        raise FileNotFoundError(
            f"TAQ source file not found:\n{TAQ_FILE}"
        )

    print(
        f"Source file:\n{TAQ_FILE}"
    )

    print(
        f"\nChunk size: {CHUNK_SIZE:,}"
    )

    usecols = [
        DATE_COLUMN,
        SYMBOL_COLUMN,
    ] + TIME_ONLY_COLUMNS

    # -------------------------------------------------------------------------
    # Counters
    # -------------------------------------------------------------------------

    total_rows = 0

    missing_dates = 0

    malformed_dates = 0

    date_counts = {}

    symbol_counts = {}

    date_symbol_counts = {}

    time_stats = {
        column: {
            "rows": 0,
            "non_null": 0,
            "missing": 0,
            "invalid": 0,
            "min_seconds": None,
            "max_seconds": None,
            "precision_values": set(),
        }
        for column in TIME_ONLY_COLUMNS
    }

    # -------------------------------------------------------------------------
    # Read source in chunks
    # -------------------------------------------------------------------------

    for chunk_number, chunk in enumerate(
        pd.read_csv(
            TAQ_FILE,
            usecols=usecols,
            chunksize=CHUNK_SIZE,
            low_memory=False,
        ),
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

        raw_dates = chunk[
            DATE_COLUMN
        ]

        parsed_dates = parse_date(
            raw_dates
        )

        missing_mask = (
            raw_dates.isna()
        )

        malformed_mask = (
            raw_dates.notna()
            & parsed_dates.isna()
        )

        missing_dates += int(
            missing_mask.sum()
        )

        malformed_dates += int(
            malformed_mask.sum()
        )

        # ---------------------------------------------------------------------
        # Date counts
        # ---------------------------------------------------------------------

        valid_date_mask = (
            parsed_dates.notna()
        )

        if valid_date_mask.any():

            valid_dates = (
                parsed_dates[
                    valid_date_mask
                ]
                .dt.normalize()
            )

            counts = (
                valid_dates
                .value_counts()
            )

            for date_value, count in (
                counts.items()
            ):

                key = date_value.date()

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

        symbols = chunk[
            SYMBOL_COLUMN
        ]

        symbol_counts_chunk = (
            symbols
            .dropna()
            .astype(str)
            .value_counts()
        )

        for symbol, count in (
            symbol_counts_chunk.items()
        ):

            symbol_counts[symbol] = (
                symbol_counts.get(
                    symbol,
                    0,
                )
                + int(count)
            )

        # =====================================================================
        # DATE + SYMBOL
        # =====================================================================

        valid_pair_mask = (
            parsed_dates.notna()
            & symbols.notna()
        )

        if valid_pair_mask.any():

            pair_df = pd.DataFrame(
                {
                    "date": (
                        parsed_dates[
                            valid_pair_mask
                        ]
                        .dt.normalize()
                    ),
                    "symbol": (
                        symbols[
                            valid_pair_mask
                        ]
                        .astype(str)
                    ),
                }
            )

            pair_counts = (
                pair_df
                .value_counts()
            )

            for (
                date_value,
                symbol,
            ), count in pair_counts.items():

                key = (
                    date_value.date(),
                    symbol,
                )

                date_symbol_counts[key] = (
                    date_symbol_counts.get(
                        key,
                        0,
                    )
                    + int(count)
                )

        # =====================================================================
        # TIME-ONLY FIELDS
        # =====================================================================

        for column in TIME_ONLY_COLUMNS:

            series = chunk[
                column
            ]

            stats = time_stats[
                column
            ]

            stats["rows"] += len(
                series
            )

            stats["missing"] += int(
                series.isna().sum()
            )

            non_null = (
                series.dropna()
            )

            stats["non_null"] += len(
                non_null
            )

            if non_null.empty:
                continue

            # -------------------------------------------------------------
            # Precision
            # -------------------------------------------------------------

            precision = (
                classify_time_precision(
                    non_null
                )
            )

            stats[
                "precision_values"
            ].add(
                precision
            )

            # -------------------------------------------------------------
            # Parse time
            # -------------------------------------------------------------

            parsed_time = parse_time(
                non_null
            )

            invalid = (
                parsed_time.isna()
            )

            stats["invalid"] += int(
                invalid.sum()
            )

            valid_time = (
                parsed_time[
                    parsed_time.notna()
                ]
            )

            if valid_time.empty:
                continue

            min_seconds = (
                valid_time
                .dt.total_seconds()
                .min()
            )

            max_seconds = (
                valid_time
                .dt.total_seconds()
                .max()
            )

            if (
                stats["min_seconds"]
                is None
            ):

                stats[
                    "min_seconds"
                ] = min_seconds

            else:

                stats[
                    "min_seconds"
                ] = min(
                    stats[
                        "min_seconds"
                    ],
                    min_seconds,
                )

            if (
                stats["max_seconds"]
                is None
            ):

                stats[
                    "max_seconds"
                ] = max_seconds

            else:

                stats[
                    "max_seconds"
                ] = max(
                    stats[
                        "max_seconds"
                    ],
                    max_seconds,
                )

    # =========================================================================
    # DATE DATAFRAME
    # =========================================================================

    if date_counts:

        date_df = pd.DataFrame(
            {
                "date": list(
                    date_counts.keys()
                ),
                "record_count": list(
                    date_counts.values()
                ),
            }
        )

        date_df["date"] = pd.to_datetime(
            date_df["date"]
        )

        date_df = (
            date_df
            .sort_values("date")
            .reset_index(drop=True)
        )

    else:

        date_df = pd.DataFrame(
            columns=[
                "date",
                "record_count",
            ]
        )

    # =========================================================================
    # DATE DIAGNOSTICS
    # =========================================================================

    if not date_df.empty:

        date_df["year"] = (
            date_df["date"]
            .dt.year
        )

        date_df["month"] = (
            date_df["date"]
            .dt.month
        )

        date_df["year_month"] = (
            date_df["date"]
            .dt.to_period("M")
            .astype(str)
        )

        date_df["day_of_week"] = (
            date_df["date"]
            .dt.day_name()
        )

        date_df[
            "days_since_previous_observed_date"
        ] = (
            date_df["date"]
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

        median_count = (
            date_df[
                "record_count"
            ]
            .median()
        )

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

        else:

            date_df[
                "record_count_vs_median"
            ] = None

    # =========================================================================
    # DATE + SYMBOL DUPLICATES
    # =========================================================================

    duplicate_pairs = {
        key: count
        for key, count
        in date_symbol_counts.items()
        if count > 1
    }

    duplicate_extra_rows = sum(
        count - 1
        for count in duplicate_pairs.values()
    )

    duplicate_pair_count = len(
        duplicate_pairs
    )

    # =========================================================================
    # CALENDAR GAPS
    # =========================================================================

    if date_df.empty:

        calendar_gap_count = 0

        first_date = None

        last_date = None

    else:

        first_date = date_df[
            "date"
        ].min()

        last_date = date_df[
            "date"
        ].max()

        full_calendar = pd.date_range(
            first_date,
            last_date,
            freq="D",
        )

        observed_dates = (
            pd.DatetimeIndex(
                date_df["date"]
            )
        )

        calendar_gaps = (
            full_calendar
            .difference(
                observed_dates
            )
        )

        calendar_gap_count = len(
            calendar_gaps
        )

    # =========================================================================
    # TEMPORAL COVERAGE OUTPUT
    # =========================================================================

    temporal_coverage = pd.DataFrame(
        [
            {
                "dataset": "taq.csv",
                "source_path": str(
                    TAQ_FILE
                ),
                "total_rows": total_rows,
                "first_date": first_date,
                "last_date": last_date,
                "unique_dates": (
                    len(date_counts)
                ),
                "unique_symbols": (
                    len(symbol_counts)
                ),
                "missing_date_rows": (
                    missing_dates
                ),
                "malformed_date_rows": (
                    malformed_dates
                ),
                "date_symbol_duplicate_pairs": (
                    duplicate_pair_count
                ),
                "date_symbol_duplicate_extra_rows": (
                    duplicate_extra_rows
                ),
                "calendar_date_gaps": (
                    calendar_gap_count
                ),
                "observed_frequency": (
                    "DAILY_SECURITY_LEVEL"
                ),
                "date_format": (
                    "DD/MM/YYYY"
                ),
                "timestamp_semantics": (
                    "TIME_ONLY"
                ),
                "timestamp_precision": (
                    "MILLISECOND"
                ),
            }
        ]
    )

    # =========================================================================
    # TIMESTAMP DIAGNOSTICS OUTPUT
    # =========================================================================

    timestamp_records = []

    for column, stats in (
        time_stats.items()
    ):

        min_seconds = (
            stats["min_seconds"]
        )

        max_seconds = (
            stats["max_seconds"]
        )

        if min_seconds is not None:

            min_time = str(
                pd.to_timedelta(
                    min_seconds,
                    unit="s",
                )
            )

        else:

            min_time = None

        if max_seconds is not None:

            max_time = str(
                pd.to_timedelta(
                    max_seconds,
                    unit="s",
                )
            )

        else:

            max_time = None

        timestamp_records.append(
            {
                "column": column,
                "rows_observed": (
                    stats["rows"]
                ),
                "non_null_count": (
                    stats["non_null"]
                ),
                "missing_count": (
                    stats["missing"]
                ),
                "parse_failure_count": (
                    stats["invalid"]
                ),
                "parse_failure_rate": (
                    stats["invalid"]
                    / stats["non_null"]
                    if stats["non_null"] > 0
                    else None
                ),
                "min_time": min_time,
                "max_time": max_time,
                "precision_observed": (
                    ";".join(
                        sorted(
                            stats[
                                "precision_values"
                            ]
                        )
                    )
                ),
                "semantic_type": (
                    "TIME_ONLY_EVENT_OR_SNAPSHOT"
                ),
            }
        )

    timestamp_diagnostics = pd.DataFrame(
        timestamp_records
    )

    return (
        temporal_coverage,
        date_df,
        timestamp_diagnostics,
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_header(
        "PHASE 5 — STEP 4: CORRECTED TEMPORAL COVERAGE & TIMESTAMP VALIDATION"
    )

    print(
        "\nConfirmed source date format:"
    )

    print(
        "  DD/MM/YYYY"
    )

    print(
        "\nConfirmed time-only fields:"
    )

    for column in TIME_ONLY_COLUMNS:

        print(
            f"  - {column}"
        )

    print(
        "\nExplicitly excluded from timestamp processing:"
    )

    for column in NON_TIMESTAMP_TIME_NAMED_COLUMNS:

        print(
            f"  - {column}"
        )

    (
        temporal_coverage,
        date_diagnostics,
        timestamp_diagnostics,
    ) = scan_dataset()

    # -------------------------------------------------------------------------
    # Create output directory
    # -------------------------------------------------------------------------

    TAQ_PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -------------------------------------------------------------------------
    # Save outputs
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Console summary
    # -------------------------------------------------------------------------

    print_header(
        "CORRECTED TEMPORAL COVERAGE SUMMARY"
    )

    row = temporal_coverage.iloc[0]

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
        f"pairs:                  "
        f"{row['date_symbol_duplicate_pairs']:,}"
    )

    print(
        f"Date+symbol duplicate "
        f"extra rows:             "
        f"{row['date_symbol_duplicate_extra_rows']:,}"
    )

    print(
        f"Calendar gaps:           "
        f"{row['calendar_date_gaps']:,}"
    )

    print(
        f"Date format:             "
        f"{row['date_format']}"
    )

    print(
        f"Timestamp semantics:     "
        f"{row['timestamp_semantics']}"
    )

    print(
        f"Timestamp precision:     "
        f"{row['timestamp_precision']}"
    )

    print_header(
        "TIMESTAMP SUMMARY"
    )

    print(
        timestamp_diagnostics.to_string(
            index=False
        )
    )

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

    print_header(
        "STATUS"
    )

    if (
        row["malformed_date_rows"] == 0
        and timestamp_diagnostics[
            "parse_failure_count"
        ].sum() == 0
    ):

        print(
            "PASS — date and time fields are "
            "structurally parseable using the "
            "confirmed source formats."
        )

    else:

        print(
            "FAIL — temporal parsing issues remain. "
            "Investigate before proceeding."
        )


if __name__ == "__main__":
    main()