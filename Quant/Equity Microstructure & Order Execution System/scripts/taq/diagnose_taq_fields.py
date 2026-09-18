from pathlib import Path

import numpy as np
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

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "taq"
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "taq_field_quality_diagnostics.csv"
)

VALUE_SUMMARY_FILE = (
    PROCESSED_DIR
    / "taq_field_value_summary.csv"
)


# =============================================================================
# CONFIGURATION
# =============================================================================

CHUNK_SIZE = 100_000

DATE_COLUMN = "date"

IDENTIFIER_COLUMNS = [
    "symbol",
]

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

NON_TIMESTAMP_TIME_NAMED_COLUMNS = [
    "NumTimeUnitsWithTrade1",
    "NumTimeUnitsWithTrade2",
]


# =============================================================================
# COLUMN SEMANTIC MAP
# =============================================================================
#
# These classifications are based on the observed schema and column names.
# They are diagnostic classifications, not yet final economic definitions.
#

COLUMN_ROLE_RULES = {
    "QUOTE_PRICE": [
        "BB_",
        "BO_",
        "MID_",
        "Mid_",
        "LBB",
        "LBO",
        "LMid",
        "CPrc",
        "CPrc2",
    ],

    "TRADE_OR_EVENT_PRICE": [
        "OPrice",
        "DPrice",
        "LPrice",
        "Price_1pm",
        "Price_4pm",
    ],

    "QUOTE_TIMESTAMP": [
        "QTime_",
        "LQTime",
    ],

    "TRADE_OR_EVENT_TIMESTAMP": [
        "OTime",
        "DTime",
        "LTTime",
        "TTime_",
        "CTime",
    ],

    "TRADING_ACTIVITY": [
        "NumTrades",
        "SumVolume",
        "SumValue",
        "MFCount",
    ],

    "TRADE_DIRECTION": [
        "BuyNumTrades",
        "SellNumTrades",
        "BuyVol",
        "SellVol",
        "BuyDollar",
        "SellDollar",
        "TSign",
    ],

    "EXECUTION_COST_METRIC": [
        "ESpread",
        "RSpread",
        "PriceImpact",
    ],

    "QUOTE_QUALITY_METRIC": [
        "QSpread",
        "ExtremeOfr",
        "ExtremeBid",
    ],

    "QUOTE_DEPTH_OR_ORDER_FLOW": [
        "TOfr",
        "TBid",
        "BOfr",
        "BBid",
    ],

    "MARKET_STATISTIC": [
        "Ret_",
        "IVol_",
        "VarianceRatio",
        "HIndex",
    ],

    "OBSERVATION_COUNT": [
        "NObsUsed",
        "NumTimeUnitsWithTrade",
    ],
}


# =============================================================================
# HELPERS
# =============================================================================

def print_header(title):

    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def classify_column(column):

    if column == DATE_COLUMN:

        return "DATE"

    if column in IDENTIFIER_COLUMNS:

        return "SECURITY_IDENTIFIER"

    if column in NON_TIMESTAMP_TIME_NAMED_COLUMNS:

        return "OBSERVATION_COUNT"

    if column in TIME_COLUMNS:

        if column.startswith("QTime") or column == "LQTime":

            return "QUOTE_TIMESTAMP"

        return "TRADE_OR_EVENT_TIMESTAMP"

    for role, patterns in COLUMN_ROLE_RULES.items():

        for pattern in patterns:

            if pattern in column:

                return role

    return "OTHER"


def safe_numeric(series):

    return pd.to_numeric(
        series,
        errors="coerce",
    )


def summarize_numeric(series):

    numeric = safe_numeric(series)

    non_null_numeric = numeric.dropna()

    if non_null_numeric.empty:

        return {
            "numeric_count": 0,
            "numeric_min": None,
            "numeric_max": None,
            "numeric_mean": None,
            "numeric_median": None,
            "zero_count": 0,
            "negative_count": 0,
            "positive_count": 0,
            "inf_count": 0,
        }

    finite = (
        non_null_numeric
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
        .dropna()
    )

    return {
        "numeric_count": len(
            non_null_numeric
        ),
        "numeric_min": (
            finite.min()
            if not finite.empty
            else None
        ),
        "numeric_max": (
            finite.max()
            if not finite.empty
            else None
        ),
        "numeric_mean": (
            finite.mean()
            if not finite.empty
            else None
        ),
        "numeric_median": (
            finite.median()
            if not finite.empty
            else None
        ),
        "zero_count": int(
            (non_null_numeric == 0).sum()
        ),
        "negative_count": int(
            (non_null_numeric < 0).sum()
        ),
        "positive_count": int(
            (non_null_numeric > 0).sum()
        ),
        "inf_count": int(
            np.isinf(
                non_null_numeric
            ).sum()
        ),
    }


def update_minimum(
    current,
    candidate,
):

    if candidate is None:
        return current

    if current is None:
        return candidate

    return min(
        current,
        candidate,
    )


def update_maximum(
    current,
    candidate,
):

    if candidate is None:
        return current

    if current is None:
        return candidate

    return max(
        current,
        candidate,
    )


# =============================================================================
# MAIN DIAGNOSTIC
# =============================================================================

def diagnose_fields():

    if not TAQ_FILE.exists():

        raise FileNotFoundError(
            f"TAQ source file not found:\n{TAQ_FILE}"
        )

    print_header(
        "PHASE 5 — STEP 5: TAQ FIELD SEMANTIC & DATA-QUALITY DIAGNOSTICS"
    )

    print(
        f"Source file:\n{TAQ_FILE}"
    )

    print(
        f"\nChunk size: {CHUNK_SIZE:,}"
    )

    # -------------------------------------------------------------------------
    # Read header first
    # -------------------------------------------------------------------------

    header = pd.read_csv(
        TAQ_FILE,
        nrows=0,
    )

    columns = list(
        header.columns
    )

    print(
        f"\nColumns found: {len(columns):,}"
    )

    # -------------------------------------------------------------------------
    # Initialize statistics
    # -------------------------------------------------------------------------

    stats = {}

    for column in columns:

        role = classify_column(
            column
        )

        stats[column] = {
            "column": column,
            "semantic_role": role,
            "rows_observed": 0,
            "non_null_count": 0,
            "missing_count": 0,
            "missing_rate": 0.0,
            "numeric_count": 0,
            "numeric_min": None,
            "numeric_max": None,
            "numeric_mean": None,
            "numeric_median": None,
            "zero_count": 0,
            "negative_count": 0,
            "positive_count": 0,
            "inf_count": 0,
        }

    # -------------------------------------------------------------------------
    # Process source in chunks
    # -------------------------------------------------------------------------

    for chunk_number, chunk in enumerate(
        pd.read_csv(
            TAQ_FILE,
            chunksize=CHUNK_SIZE,
            low_memory=False,
        ),
        start=1,
    ):

        print(
            f"Processing chunk {chunk_number:,} "
            f"({len(chunk):,} rows)"
        )

        for column in columns:

            series = chunk[
                column
            ]

            field_stats = stats[
                column
            ]

            row_count = len(
                series
            )

            non_null = int(
                series.notna().sum()
            )

            missing = (
                row_count
                - non_null
            )

            field_stats[
                "rows_observed"
            ] += row_count

            field_stats[
                "non_null_count"
            ] += non_null

            field_stats[
                "missing_count"
            ] += missing

            # -----------------------------------------------------------------
            # Numeric diagnostics
            # -----------------------------------------------------------------

            numeric = safe_numeric(
                series
            )

            numeric_non_null = (
                numeric.dropna()
            )

            if not numeric_non_null.empty:

                field_stats[
                    "numeric_count"
                ] += len(
                    numeric_non_null
                )

                field_stats[
                    "zero_count"
                ] += int(
                    (
                        numeric_non_null
                        == 0
                    ).sum()
                )

                field_stats[
                    "negative_count"
                ] += int(
                    (
                        numeric_non_null
                        < 0
                    ).sum()
                )

                field_stats[
                    "positive_count"
                ] += int(
                    (
                        numeric_non_null
                        > 0
                    ).sum()
                )

                field_stats[
                    "inf_count"
                ] += int(
                    np.isinf(
                        numeric_non_null
                    ).sum()
                )

                finite = (
                    numeric_non_null
                    .replace(
                        [np.inf, -np.inf],
                        np.nan,
                    )
                    .dropna()
                )

                if not finite.empty:

                    field_stats[
                        "numeric_min"
                    ] = update_minimum(
                        field_stats[
                            "numeric_min"
                        ],
                        finite.min(),
                    )

                    field_stats[
                        "numeric_max"
                    ] = update_maximum(
                        field_stats[
                            "numeric_max"
                        ],
                        finite.max(),
                    )

    # =========================================================================
    # FINALIZE STATISTICS
    # =========================================================================

    records = []

    for column in columns:

        field_stats = stats[
            column
        ]

        rows = field_stats[
            "rows_observed"
        ]

        missing = field_stats[
            "missing_count"
        ]

        field_stats[
            "missing_rate"
        ] = (
            missing / rows
            if rows > 0
            else np.nan
        )

        records.append(
            field_stats
        )

    diagnostic_df = pd.DataFrame(
        records
    )

    # =========================================================================
    # ADD QUALITY FLAGS
    # =========================================================================

    diagnostic_df[
        "has_missing"
    ] = (
        diagnostic_df[
            "missing_count"
        ]
        > 0
    )

    diagnostic_df[
        "has_negative_values"
    ] = (
        diagnostic_df[
            "negative_count"
        ]
        > 0
    )

    diagnostic_df[
        "has_zero_values"
    ] = (
        diagnostic_df[
            "zero_count"
        ]
        > 0
    )

    diagnostic_df[
        "has_infinite_values"
    ] = (
        diagnostic_df[
            "inf_count"
        ]
        > 0
    )

    # -------------------------------------------------------------------------
    # Economic diagnostic flags
    # -------------------------------------------------------------------------

    diagnostic_df[
        "requires_manual_semantic_review"
    ] = (
        diagnostic_df[
            "semantic_role"
        ]
        == "OTHER"
    )

    diagnostic_df[
        "potential_price_field"
    ] = diagnostic_df[
        "semantic_role"
    ].isin(
        [
            "QUOTE_PRICE",
            "TRADE_OR_EVENT_PRICE",
        ]
    )

    diagnostic_df[
        "potential_time_field"
    ] = diagnostic_df[
        "semantic_role"
    ].isin(
        [
            "QUOTE_TIMESTAMP",
            "TRADE_OR_EVENT_TIMESTAMP",
        ]
    )

    # =========================================================================
    # SAVE MAIN DIAGNOSTIC
    # =========================================================================

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    diagnostic_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    # =========================================================================
    # VALUE-LEVEL SUMMARY
    # =========================================================================
    #
    # For each field capture a compact summary of observed values.
    #
    # This is particularly useful for:
    #
    #   condition-like fields
    #   count fields
    #   price fields
    #   percentage fields
    #   return fields
    #

    value_records = []

    # Re-read only the required fields for value summaries.
    #
    # The dataset is only 122k rows, so this remains manageable.
    #

    full_df = pd.read_csv(
        TAQ_FILE,
        low_memory=False,
    )

    for column in columns:

        series = full_df[
            column
        ]

        record = {
            "column": column,
            "semantic_role": classify_column(
                column
            ),
            "dtype": str(
                series.dtype
            ),
            "unique_count": int(
                series.nunique(
                    dropna=True
                )
            ),
        }

        # -------------------------------------------------------------
        # Numeric summary
        # -------------------------------------------------------------

        numeric = safe_numeric(
            series
        )

        numeric = (
            numeric
            .replace(
                [np.inf, -np.inf],
                np.nan,
            )
            .dropna()
        )

        if not numeric.empty:

            record[
                "min"
            ] = numeric.min()

            record[
                "max"
            ] = numeric.max()

            record[
                "median"
            ] = numeric.median()

            record[
                "mean"
            ] = numeric.mean()

            record[
                "zero_count"
            ] = int(
                (numeric == 0).sum()
            )

            record[
                "negative_count"
            ] = int(
                (numeric < 0).sum()
            )

        else:

            record[
                "min"
            ] = None

            record[
                "max"
            ] = None

            record[
                "median"
            ] = None

            record[
                "mean"
            ] = None

            record[
                "zero_count"
            ] = None

            record[
                "negative_count"
            ] = None

        # -------------------------------------------------------------
        # Top categorical values
        # -------------------------------------------------------------

        if (
            series.dtype == "object"
            or
            str(
                series.dtype
            ).startswith("string")
        ):

            top_values = (
                series
                .dropna()
                .astype(str)
                .value_counts()
                .head(10)
            )

            record[
                "top_values"
            ] = "; ".join(
                [
                    f"{value} ({count})"
                    for value, count
                    in top_values.items()
                ]
            )

        else:

            record[
                "top_values"
            ] = None

        value_records.append(
            record
        )

    value_summary_df = pd.DataFrame(
        value_records
    )

    value_summary_df.to_csv(
        VALUE_SUMMARY_FILE,
        index=False,
    )

    return (
        diagnostic_df,
        value_summary_df,
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    (
        diagnostic_df,
        value_summary_df,
    ) = diagnose_fields()

    # =========================================================================
    # CONSOLE REPORT
    # =========================================================================

    print_header(
        "FIELD ROLE COUNTS"
    )

    role_counts = (
        diagnostic_df[
            "semantic_role"
        ]
        .value_counts()
    )

    print(
        role_counts.to_string()
    )

    print_header(
        "FIELDS WITH MISSING VALUES"
    )

    missing_fields = (
        diagnostic_df[
            diagnostic_df[
                "has_missing"
            ]
        ][
            [
                "column",
                "semantic_role",
                "missing_count",
                "missing_rate",
            ]
        ]
        .sort_values(
            "missing_rate",
            ascending=False,
        )
    )

    if missing_fields.empty:

        print(
            "No missing values detected."
        )

    else:

        print(
            missing_fields.to_string(
                index=False
            )
        )

    print_header(
        "FIELDS WITH NEGATIVE VALUES"
    )

    negative_fields = (
        diagnostic_df[
            diagnostic_df[
                "has_negative_values"
            ]
        ][
            [
                "column",
                "semantic_role",
                "negative_count",
                "numeric_min",
            ]
        ]
        .sort_values(
            "negative_count",
            ascending=False,
        )
    )

    if negative_fields.empty:

        print(
            "No negative numeric values detected."
        )

    else:

        print(
            negative_fields.to_string(
                index=False
            )
        )

    print_header(
        "PRICE FIELD DIAGNOSTICS"
    )

    price_fields = (
        diagnostic_df[
            diagnostic_df[
                "potential_price_field"
            ]
        ][
            [
                "column",
                "semantic_role",
                "missing_count",
                "missing_rate",
                "numeric_min",
                "numeric_max",
                "zero_count",
                "negative_count",
            ]
        ]
    )

    print(
        price_fields.to_string(
            index=False
        )
    )

    print_header(
        "FIELDS REQUIRING MANUAL SEMANTIC REVIEW"
    )

    review_fields = (
        diagnostic_df[
            diagnostic_df[
                "requires_manual_semantic_review"
            ]
        ][
            [
                "column",
                "semantic_role",
                "missing_count",
                "missing_rate",
                "numeric_min",
                "numeric_max",
            ]
        ]
    )

    if review_fields.empty:

        print(
            "No unclassified fields remain."
        )

    else:

        print(
            review_fields.to_string(
                index=False
            )
        )

    print_header(
        "OUTPUTS"
    )

    print(
        f"Field quality diagnostics:\n"
        f"{OUTPUT_FILE}"
    )

    print(
        f"\nField value summary:\n"
        f"{VALUE_SUMMARY_FILE}"
    )

    print_header(
        "STATUS"
    )

    print(
        "PASS — field-level diagnostics generated."
    )

    print(
        "\nIMPORTANT:"
    )

    print(
        "No observations were removed."
    )

    print(
        "No cleaning rules were applied."
    )

    print(
        "The outputs are diagnostic only."
    )


if __name__ == "__main__":
    main()