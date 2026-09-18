from pathlib import Path
import re

import pandas as pd


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TAQ_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "taq"

INVENTORY_FILE = TAQ_PROCESSED_DIR / "taq_file_inventory.csv"
SCHEMA_FILE = TAQ_PROCESSED_DIR / "taq_schema_inventory.csv"
SAMPLES_FILE = TAQ_PROCESSED_DIR / "taq_schema_samples.csv"

FILE_CLASSIFICATION_OUTPUT = (
    TAQ_PROCESSED_DIR / "taq_file_classification.csv"
)

COLUMN_CLASSIFICATION_OUTPUT = (
    TAQ_PROCESSED_DIR / "taq_column_classification.csv"
)


# =============================================================================
# HELPERS
# =============================================================================

def normalize(value):
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(value).strip().lower(),
    ).strip("_")


def classify_column(column):
    """
    Research-oriented classification of observed TAQ/TAQM columns.

    This classification is diagnostic. It does NOT assert the exact
    economic meaning of ambiguous source fields.
    """

    c = normalize(column)

    # -------------------------------------------------------------------------
    # Primary identifiers
    # -------------------------------------------------------------------------

    if c == "date":
        return "DATE"

    if c in {"symbol", "ticker"}:
        return "SECURITY_IDENTIFIER"

    # -------------------------------------------------------------------------
    # Quote timestamps
    # -------------------------------------------------------------------------

    if (
        c.startswith("qtime")
        or c.endswith("_qtime")
        or c == "lqtime"
    ):
        return "QUOTE_TIMESTAMP"

    # -------------------------------------------------------------------------
    # Quote prices
    # -------------------------------------------------------------------------

    if (
        c.startswith("bb_")
        or c.startswith("bo_")
        or c.startswith("mid_")
        or c in {"lbb", "lbo", "lmid"}
    ):
        return "QUOTE_PRICE"

    # -------------------------------------------------------------------------
    # Trade timestamps
    # -------------------------------------------------------------------------

    if (
        c.startswith("ttime")
        or c in {"lt_time", "lttime", "otime", "dtime", "ctime", "ctime2"}
    ):
        return "TRADE_OR_EVENT_TIMESTAMP"

    # -------------------------------------------------------------------------
    # Trade prices
    # -------------------------------------------------------------------------

    if (
        c.startswith("price_")
        or c in {
            "oprice",
            "dprice",
            "lprice",
            "cprc",
            "cprc2",
        }
    ):
        return "TRADE_OR_EVENT_PRICE"

    # -------------------------------------------------------------------------
    # Trading activity
    # -------------------------------------------------------------------------

    if (
        "numtrades" in c
        or "volume" in c
        or "sumvolume" in c
        or "sumvalue" in c
        or "vol_oc" in c
        or "value_oc" in c
    ):
        return "TRADING_ACTIVITY"

    # -------------------------------------------------------------------------
    # Trade direction / order flow
    # -------------------------------------------------------------------------

    if (
        c.startswith("buy")
        or c.startswith("sell")
        or "tsign" in c
    ):
        return "TRADE_DIRECTION"

    # -------------------------------------------------------------------------
    # Execution / spread / price impact
    # -------------------------------------------------------------------------

    if (
        c.startswith("espread")
        or c.startswith("rspread")
        or c.startswith("priceimpact")
    ):
        return "EXECUTION_COST_METRIC"

    # -------------------------------------------------------------------------
    # Quote spread / quote quality
    # -------------------------------------------------------------------------

    if (
        c.startswith("qspread")
        or c.startswith("numextreme")
    ):
        return "QUOTE_QUALITY_METRIC"

    # -------------------------------------------------------------------------
    # Bid / offer depth and dollar/share measures
    # -------------------------------------------------------------------------

    if (
        "bid" in c
        or "ofr" in c
        or "offer" in c
    ):
        return "QUOTE_DEPTH_OR_ORDER_FLOW"

    # -------------------------------------------------------------------------
    # Volatility / market statistics
    # -------------------------------------------------------------------------

    if (
        c.startswith("ret_")
        or c.startswith("ivol")
        or c.startswith("variance")
        or c.startswith("hindex")
    ):
        return "MARKET_STATISTIC"

    # -------------------------------------------------------------------------
    # Observation counts
    # -------------------------------------------------------------------------

    if (
        c.startswith("nobs")
        or c.startswith("numtimeunits")
        or c == "mfcount"
    ):
        return "OBSERVATION_COUNT"

    # -------------------------------------------------------------------------
    # Unknown
    # -------------------------------------------------------------------------

    return "OTHER"


def classify_data_layer(column_class):
    """
    Broad distinction between raw-event-like fields and derived summary fields.
    """

    if column_class in {
        "DATE",
        "SECURITY_IDENTIFIER",
        "QUOTE_TIMESTAMP",
        "QUOTE_PRICE",
        "TRADE_OR_EVENT_TIMESTAMP",
        "TRADE_OR_EVENT_PRICE",
    }:
        return "EVENT_OR_SNAPSHOT_FIELD"

    if column_class in {
        "TRADING_ACTIVITY",
        "TRADE_DIRECTION",
        "QUOTE_DEPTH_OR_ORDER_FLOW",
        "QUOTE_QUALITY_METRIC",
        "EXECUTION_COST_METRIC",
        "MARKET_STATISTIC",
        "OBSERVATION_COUNT",
    }:
        return "DERIVED_OR_AGGREGATED_FIELD"

    return "UNCLASSIFIED"


def infer_file_function(columns):
    """
    Determine the likely function of the file from the observed schema.

    This deliberately avoids calling the file 'raw TAQ' merely because
    the source directory contains TAQ data.
    """

    normalized = {
        normalize(column)
        for column in columns
    }

    quote_snapshot_signals = {
        "qtime_1pm",
        "bb_1pm",
        "bo_1pm",
        "mid_1pm",
        "qtime_4pm",
        "bb_4pm",
        "bo_4pm",
        "mid_4pm",
    }

    trade_summary_signals = {
        "numtrades_t",
        "sumvolume_t",
        "numtrades_m",
        "sumvolume_m",
    }

    execution_signals = {
        "espreaddollar_avg1",
        "rspreaddollar_avg1",
        "priceimpactdollar_avg1",
    }

    matched_quote = len(
        normalized & quote_snapshot_signals
    )

    matched_trade = len(
        normalized & trade_summary_signals
    )

    matched_execution = len(
        normalized & execution_signals
    )

    if (
        matched_quote >= 2
        and matched_trade >= 1
        and matched_execution >= 1
    ):
        return (
            "DAILY_TAQ_DERIVED_MICROSTRUCTURE_SUMMARY"
        )

    if matched_quote >= 2:
        return "QUOTE_SNAPSHOT_OR_QUOTE_SUMMARY"

    if matched_trade >= 1:
        return "TRADE_SUMMARY"

    return "TAQ_UNCLASSIFIED"


def inspect_value_examples(samples, column):
    """
    Return a compact representation of observed sample values.
    """

    if column not in samples.columns:
        return None

    values = (
        samples[column]
        .dropna()
        .astype(str)
        .drop_duplicates()
        .head(10)
        .tolist()
    )

    return " | ".join(values)


# =============================================================================
# LOAD INPUTS
# =============================================================================

def load_inputs():

    for path in [
        INVENTORY_FILE,
        SCHEMA_FILE,
        SAMPLES_FILE,
    ]:

        if not path.exists():

            raise FileNotFoundError(
                f"Required artifact not found:\n{path}"
            )

    inventory = pd.read_csv(
        INVENTORY_FILE
    )

    schema = pd.read_csv(
        SCHEMA_FILE
    )

    samples = pd.read_csv(
        SAMPLES_FILE,
        low_memory=False,
    )

    return inventory, schema, samples


# =============================================================================
# COLUMN CLASSIFICATION
# =============================================================================

def build_column_classification(schema, samples):

    records = []

    for _, row in schema.iterrows():

        column = row["column"]

        if pd.isna(column):
            continue

        classification = classify_column(
            column
        )

        data_layer = classify_data_layer(
            classification
        )

        records.append(
            {
                "file": row["file"],
                "relative_path": row["relative_path"],
                "column_position": row[
                    "column_position"
                ],
                "column": column,
                "dtype": row["dtype"],
                "non_null_count": row[
                    "non_null_count"
                ],
                "missing_count": row[
                    "missing_count"
                ],
                "missing_rate": row[
                    "missing_rate"
                ],
                "unique_count": row[
                    "unique_count"
                ],
                "sample_min": row[
                    "sample_min"
                ],
                "sample_max": row[
                    "sample_max"
                ],
                "possible_date_or_timestamp": row[
                    "possible_date_or_timestamp"
                ],
                "timestamp_precision": row[
                    "timestamp_precision"
                ],
                "column_class": classification,
                "data_layer": data_layer,
                "sample_values": inspect_value_examples(
                    samples,
                    column,
                ),
            }
        )

    return pd.DataFrame(records)


# =============================================================================
# FILE CLASSIFICATION
# =============================================================================

def build_file_classification(
    inventory,
    schema,
    column_classification,
):

    records = []

    for _, file_row in inventory.iterrows():

        filename = file_row["filename"]

        file_schema = schema[
            schema["file"] == filename
        ]

        columns = (
            file_schema["column"]
            .dropna()
            .tolist()
        )

        function = infer_file_function(
            columns
        )

        file_columns = column_classification[
            column_classification["file"] == filename
        ]

        counts = (
            file_columns[
                "column_class"
            ]
            .value_counts()
            .to_dict()
        )

        records.append(
            {
                "file": filename,
                "relative_path": file_row[
                    "relative_path"
                ],
                "file_type": file_row[
                    "file_type"
                ],
                "compression": file_row[
                    "compression"
                ],
                "size_bytes": file_row[
                    "size_bytes"
                ],
                "readable": file_row[
                    "readable"
                ],
                "column_count": len(
                    columns
                ),
                "security_identifier_columns": counts.get(
                    "SECURITY_IDENTIFIER",
                    0,
                ),
                "date_columns": counts.get(
                    "DATE",
                    0,
                ),
                "quote_timestamp_columns": counts.get(
                    "QUOTE_TIMESTAMP",
                    0,
                ),
                "trade_event_timestamp_columns": counts.get(
                    "TRADE_OR_EVENT_TIMESTAMP",
                    0,
                ),
                "quote_price_columns": counts.get(
                    "QUOTE_PRICE",
                    0,
                ),
                "trade_event_price_columns": counts.get(
                    "TRADE_OR_EVENT_PRICE",
                    0,
                ),
                "trading_activity_columns": counts.get(
                    "TRADING_ACTIVITY",
                    0,
                ),
                "execution_metric_columns": counts.get(
                    "EXECUTION_COST_METRIC",
                    0,
                ),
                "market_statistic_columns": counts.get(
                    "MARKET_STATISTIC",
                    0,
                ),
                "inferred_function": function,
                "classification_basis": (
                    "Observed schema and column semantics; "
                    "not filename alone."
                ),
            }
        )

    return pd.DataFrame(records)


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 80)
    print(
        "PHASE 5 — STEP 3: TAQ/TAQM FILE CLASSIFICATION"
    )
    print("=" * 80)

    inventory, schema, samples = load_inputs()

    print(
        f"Inventory files: {len(inventory)}"
    )

    print(
        f"Schema rows: {len(schema)}"
    )

    print(
        f"Sample rows: {len(samples)}"
    )

    # -------------------------------------------------------------------------
    # Column classification
    # -------------------------------------------------------------------------

    print()
    print("-" * 80)
    print("CLASSIFYING COLUMNS")
    print("-" * 80)

    column_classification = (
        build_column_classification(
            schema,
            samples,
        )
    )

    # -------------------------------------------------------------------------
    # File classification
    # -------------------------------------------------------------------------

    print()
    print("-" * 80)
    print("CLASSIFYING FILES")
    print("-" * 80)

    file_classification = (
        build_file_classification(
            inventory,
            schema,
            column_classification,
        )
    )

    # -------------------------------------------------------------------------
    # Save outputs
    # -------------------------------------------------------------------------

    TAQ_PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    column_classification.to_csv(
        COLUMN_CLASSIFICATION_OUTPUT,
        index=False,
    )

    file_classification.to_csv(
        FILE_CLASSIFICATION_OUTPUT,
        index=False,
    )

    # -------------------------------------------------------------------------
    # Console report
    # -------------------------------------------------------------------------

    print()
    print("=" * 80)
    print("FILE CLASSIFICATION")
    print("=" * 80)

    for _, row in file_classification.iterrows():

        print(
            f"\nFile: {row['file']}"
        )

        print(
            f"  Columns:              "
            f"{row['column_count']}"
        )

        print(
            f"  Security identifiers: "
            f"{row['security_identifier_columns']}"
        )

        print(
            f"  Date columns:         "
            f"{row['date_columns']}"
        )

        print(
            f"  Quote timestamps:     "
            f"{row['quote_timestamp_columns']}"
        )

        print(
            f"  Trade/event timestamps:"
            f" {row['trade_event_timestamp_columns']}"
        )

        print(
            f"  Quote prices:         "
            f"{row['quote_price_columns']}"
        )

        print(
            f"  Trade/event prices:   "
            f"{row['trade_event_price_columns']}"
        )

        print(
            f"  Trading activity:     "
            f"{row['trading_activity_columns']}"
        )

        print(
            f"  Execution metrics:    "
            f"{row['execution_metric_columns']}"
        )

        print(
            f"  Market statistics:    "
            f"{row['market_statistic_columns']}"
        )

        print(
            f"  INFERRED FUNCTION:    "
            f"{row['inferred_function']}"
        )

    print()
    print("=" * 80)
    print("COLUMN CLASS COUNTS")
    print("=" * 80)

    counts = (
        column_classification[
            "column_class"
        ]
        .value_counts()
    )

    for classification, count in counts.items():

        print(
            f"{classification:<35} {count}"
        )

    print()
    print("=" * 80)
    print("OUTPUTS")
    print("=" * 80)

    print(
        f"File classification:\n"
        f"{FILE_CLASSIFICATION_OUTPUT}"
    )

    print(
        f"\nColumn classification:\n"
        f"{COLUMN_CLASSIFICATION_OUTPUT}"
    )


if __name__ == "__main__":
    main()