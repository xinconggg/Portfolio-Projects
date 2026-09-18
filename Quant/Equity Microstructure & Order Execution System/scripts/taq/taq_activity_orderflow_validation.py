from pathlib import Path
import pandas as pd
import numpy as np


# =============================================================================
# PHASE 5 — STEP 7
# TAQ TRADING ACTIVITY & ORDER-FLOW ECONOMIC VALIDATION
# =============================================================================
#
# PURPOSE
# -------
# Diagnose the economic consistency of:
#
#   1. Trading activity
#   2. Buy/sell classification
#   3. Trade volume
#   4. Trade dollar value
#   5. ISO / odd-lot / mixed-lot activity
#   6. Quote depth / order-flow fields
#
# IMPORTANT
# ---------
# This is a DIAGNOSTIC stage only.
#
# NO:
#   - observations are removed
#   - values are modified
#   - values are imputed
#   - canonical TAQ data is overwritten
#
# All detected violations are retained for semantic review.
#
# INPUT
# -----
# data/processed/taq/taq_cleaned.csv
#
# OUTPUT DIRECTORY
# ---------------
# data/processed/taq/activity_orderflow_validation/
#
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
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
    / "activity_orderflow_validation"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


SUMMARY_FILE = OUTPUT_DIR / "taq_activity_orderflow_validation_summary.csv"
ACTIVITY_FILE = OUTPUT_DIR / "taq_activity_orderflow_validation_by_field.csv"
SYMBOL_FILE = OUTPUT_DIR / "taq_activity_orderflow_validation_by_symbol.csv"
DATE_FILE = OUTPUT_DIR / "taq_activity_orderflow_validation_by_date.csv"
EXAMPLES_FILE = OUTPUT_DIR / "taq_activity_orderflow_validation_examples.csv"
TRADE_CONSISTENCY_FILE = (
    OUTPUT_DIR / "taq_activity_trade_consistency.csv"
)
DIRECTION_FILE = (
    OUTPUT_DIR / "taq_activity_direction_consistency.csv"
)
LOT_FILE = (
    OUTPUT_DIR / "taq_activity_lot_consistency.csv"
)
ORDERFLOW_FILE = (
    OUTPUT_DIR / "taq_orderflow_consistency.csv"
)


CHUNK_SIZE = 100_000


# =============================================================================
# FIELD DEFINITIONS
# =============================================================================

TRADE_COUNT_FIELDS = [
    "NumTrades_t",
    "NumTrades_m",
    "MFCount",
]

TRADE_VOLUME_FIELDS = [
    "SumVolume_t",
    "SumVolume_m",
]

TRADE_VALUE_FIELDS = [
    "SumValue_b",
    "SumValue_m",
]

BUY_SELL_COUNT_FIELDS = [
    "BuyNumTrades_LR1",
    "SellNumTrades_LR1",
]

BUY_SELL_VOLUME_FIELDS = [
    "BuyVol_LR1",
    "SellVol_LR1",
]

BUY_SELL_DOLLAR_FIELDS = [
    "BuyDollar_LR1",
    "SellDollar_LR1",
]

ISO_FIELDS = [
    "NumISOTrades_m",
    "SumISOVolume_m",
    "SumISOValue_m",
]

ODD_LOT_FIELDS = [
    "NumOddLotTrades_m",
    "SumOddLotVolume_m",
    "SumOddLotValue_m",
]

MIXED_LOT_FIELDS = [
    "NumMixedLotTrades_m",
    "SumMixedLotVolume_m",
    "SumMixedLotValue_m",
]

ORDERFLOW_FIELDS = [
    "TOfrDollar_TW_m",
    "TBidDollar_TW_m",
    "TOfrShares_TW_m",
    "TBidShares_TW_m",
    "BOfrDollar_TW_m",
    "BBidDollar_TW_m",
    "BOfrShares_TW_m",
    "BBidShares_TW_m",
]

ALL_ACTIVITY_FIELDS = (
    TRADE_COUNT_FIELDS
    + TRADE_VOLUME_FIELDS
    + TRADE_VALUE_FIELDS
    + BUY_SELL_COUNT_FIELDS
    + BUY_SELL_VOLUME_FIELDS
    + BUY_SELL_DOLLAR_FIELDS
    + ISO_FIELDS
    + ODD_LOT_FIELDS
    + MIXED_LOT_FIELDS
    + ORDERFLOW_FIELDS
)


# =============================================================================
# HELPERS
# =============================================================================

def safe_numeric(df, columns):
    """
    Convert selected fields to numeric without modifying the source dataframe.
    """
    existing = [c for c in columns if c in df.columns]

    for col in existing:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return existing


def add_count(container, key, value):
    container[key] = container.get(key, 0) + int(value)


# =============================================================================
# INITIALIZATION
# =============================================================================

print("=" * 80)
print("PHASE 5 — STEP 7: TAQ TRADING ACTIVITY & ORDER-FLOW ECONOMIC VALIDATION")
print("=" * 80)

print(f"Input file:\n  {INPUT_FILE}")

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Input file does not exist:\n{INPUT_FILE}"
    )


# =============================================================================
# DISCOVER SCHEMA
# =============================================================================

sample = pd.read_csv(
    INPUT_FILE,
    nrows=1000,
    low_memory=False
)

print(f"Columns found: {len(sample.columns)}")

existing_fields = [
    c for c in ALL_ACTIVITY_FIELDS
    if c in sample.columns
]

print("\nActivity/order-flow fields found:")
for col in existing_fields:
    print(f"  - {col}")


missing_expected = [
    c for c in ALL_ACTIVITY_FIELDS
    if c not in sample.columns
]

if missing_expected:
    print("\nExpected fields not found:")
    for col in missing_expected:
        print(f"  - {col}")


# =============================================================================
# STORAGE
# =============================================================================

field_stats = {}

symbol_stats = {}
date_stats = {}

examples = []

trade_consistency_records = []
direction_records = []
lot_records = []
orderflow_records = []

total_rows = 0


# =============================================================================
# FIELD INITIALIZATION
# =============================================================================

for col in existing_fields:
    field_stats[col] = {
        "column": col,
        "semantic_group": (
            "TRADE_COUNT"
            if col in TRADE_COUNT_FIELDS
            else "TRADE_VOLUME"
            if col in TRADE_VOLUME_FIELDS
            else "TRADE_VALUE"
            if col in TRADE_VALUE_FIELDS
            else "BUY_SELL_COUNT"
            if col in BUY_SELL_COUNT_FIELDS
            else "BUY_SELL_VOLUME"
            if col in BUY_SELL_VOLUME_FIELDS
            else "BUY_SELL_DOLLAR"
            if col in BUY_SELL_DOLLAR_FIELDS
            else "ISO_ACTIVITY"
            if col in ISO_FIELDS
            else "ODD_LOT_ACTIVITY"
            if col in ODD_LOT_FIELDS
            else "MIXED_LOT_ACTIVITY"
            if col in MIXED_LOT_FIELDS
            else "ORDER_FLOW"
        ),
        "rows_observed": 0,
        "non_null_count": 0,
        "missing_count": 0,
        "negative_count": 0,
        "zero_count": 0,
        "minimum": np.nan,
        "maximum": np.nan,
        "sum": 0.0,
    }


# =============================================================================
# CHUNK PROCESSING
# =============================================================================

reader = pd.read_csv(
    INPUT_FILE,
    chunksize=CHUNK_SIZE,
    low_memory=False
)

for chunk_number, df in enumerate(reader, start=1):

    print(
        f"Processing activity/order-flow chunk "
        f"{chunk_number}: {len(df):,} rows"
    )

    total_rows += len(df)

    # -------------------------------------------------------------------------
    # NORMALIZE DATE / SYMBOL FOR DIAGNOSTICS
    # -------------------------------------------------------------------------

    if "date_iso" in df.columns:
        diagnostic_date = df["date_iso"].astype(str)
    elif "date_normalized" in df.columns:
        diagnostic_date = df["date_normalized"].astype(str)
    elif "date" in df.columns:
        diagnostic_date = pd.to_datetime(
            df["date"],
            errors="coerce",
            dayfirst=True
        ).dt.strftime("%Y-%m-%d")
    else:
        diagnostic_date = pd.Series(
            ["UNKNOWN"] * len(df),
            index=df.index
        )

    if "symbol_normalized" in df.columns:
        diagnostic_symbol = df["symbol_normalized"].astype(str)
    elif "symbol" in df.columns:
        diagnostic_symbol = df["symbol"].astype(str)
    else:
        diagnostic_symbol = pd.Series(
            ["UNKNOWN"] * len(df),
            index=df.index
        )

    # -------------------------------------------------------------------------
    # NUMERIC CONVERSION
    # -------------------------------------------------------------------------

    fields = safe_numeric(
        df,
        existing_fields
    )

    # -------------------------------------------------------------------------
    # FIELD-LEVEL DIAGNOSTICS
    # -------------------------------------------------------------------------

    for col in fields:

        s = df[col]

        non_null = s.notna()
        negative = s < 0
        zero = s == 0

        stats = field_stats[col]

        stats["rows_observed"] += len(df)
        stats["non_null_count"] += int(non_null.sum())
        stats["missing_count"] += int(s.isna().sum())
        stats["negative_count"] += int(negative.sum())
        stats["zero_count"] += int(zero.sum())

        if non_null.any():

            local_min = s.min()
            local_max = s.max()

            if pd.isna(stats["minimum"]):
                stats["minimum"] = local_min
            else:
                stats["minimum"] = min(
                    stats["minimum"],
                    local_min
                )

            if pd.isna(stats["maximum"]):
                stats["maximum"] = local_max
            else:
                stats["maximum"] = max(
                    stats["maximum"],
                    local_max
                )

            stats["sum"] += float(
                s[non_null].sum()
            )

    # -------------------------------------------------------------------------
    # SYMBOL-LEVEL STATISTICS
    # -------------------------------------------------------------------------

    grouped_symbol = df.groupby(
        diagnostic_symbol,
        dropna=False
    )

    for symbol, group in grouped_symbol:

        if symbol not in symbol_stats:
            symbol_stats[symbol] = {
                "symbol": symbol,
                "rows": 0,
                "negative_activity_rows": 0,
                "trade_count_rows": 0,
                "direction_violation_rows": 0,
                "trade_consistency_violation_rows": 0,
                "lot_consistency_violation_rows": 0,
                "orderflow_violation_rows": 0,
            }

        stats = symbol_stats[symbol]

        stats["rows"] += len(group)

        # Negative activity
        activity_cols = [
            c for c in
            TRADE_COUNT_FIELDS
            + TRADE_VOLUME_FIELDS
            + TRADE_VALUE_FIELDS
            + BUY_SELL_COUNT_FIELDS
            + BUY_SELL_VOLUME_FIELDS
            + BUY_SELL_DOLLAR_FIELDS
            + ISO_FIELDS
            + ODD_LOT_FIELDS
            + MIXED_LOT_FIELDS
            if c in group.columns
        ]

        if activity_cols:
            neg_mask = group[activity_cols].lt(0).any(axis=1)
            stats["negative_activity_rows"] += int(
                neg_mask.sum()
            )

    # -------------------------------------------------------------------------
    # DATE-LEVEL INITIALIZATION
    # -------------------------------------------------------------------------

    grouped_date = df.groupby(
        diagnostic_date,
        dropna=False
    )

    for date_value, group in grouped_date:

        if date_value not in date_stats:
            date_stats[date_value] = {
                "date": date_value,
                "rows": 0,
                "negative_activity_rows": 0,
                "direction_violation_rows": 0,
                "trade_consistency_violation_rows": 0,
                "lot_consistency_violation_rows": 0,
                "orderflow_violation_rows": 0,
            }

        date_stats[date_value]["rows"] += len(group)

    # =============================================================================
    # TRADE COUNT / VOLUME / VALUE CONSISTENCY
    # =============================================================================

    if all(
        c in df.columns
        for c in [
            "NumTrades_t",
            "NumTrades_m"
        ]
    ):

        mask = (
            df["NumTrades_t"].notna()
            & df["NumTrades_m"].notna()
            & (df["NumTrades_t"] > df["NumTrades_m"])
        )

        violations = int(mask.sum())

        trade_consistency_records.append({
            "check": "NumTrades_t_GT_NumTrades_m",
            "violations": violations,
            "rate": violations / len(df) if len(df) else 0,
        })

        if violations:
            for idx in df.index[mask][:10]:
                examples.append({
                    "diagnostic_type": "TRADE_COUNT",
                    "row_index": idx,
                    "symbol": diagnostic_symbol.loc[idx],
                    "date": diagnostic_date.loc[idx],
                    "field_1": "NumTrades_t",
                    "value_1": df.loc[idx, "NumTrades_t"],
                    "field_2": "NumTrades_m",
                    "value_2": df.loc[idx, "NumTrades_m"],
                    "description": (
                        "NumTrades_t exceeds NumTrades_m"
                    ),
                })

    # -------------------------------------------------------------------------
    # BUY + SELL COUNT CONSISTENCY
    # -------------------------------------------------------------------------

    if all(
        c in df.columns
        for c in [
            "BuyNumTrades_LR1",
            "SellNumTrades_LR1",
            "NumTrades_m"
        ]
    ):

        total_directional = (
            df["BuyNumTrades_LR1"]
            + df["SellNumTrades_LR1"]
        )

        mask = (
            df["NumTrades_m"].notna()
            & total_directional.notna()
            & (total_directional > df["NumTrades_m"])
        )

        violations = int(mask.sum())

        direction_records.append({
            "check": "BUY_PLUS_SELL_TRADES_GT_TOTAL",
            "violations": violations,
            "rate": violations / len(df) if len(df) else 0,
        })

        if violations:
            for idx in df.index[mask][:10]:
                examples.append({
                    "diagnostic_type": "TRADE_DIRECTION",
                    "row_index": idx,
                    "symbol": diagnostic_symbol.loc[idx],
                    "date": diagnostic_date.loc[idx],
                    "field_1": "BuyNumTrades_LR1 + SellNumTrades_LR1",
                    "value_1": total_directional.loc[idx],
                    "field_2": "NumTrades_m",
                    "value_2": df.loc[idx, "NumTrades_m"],
                    "description": (
                        "Directional trade count exceeds total trade count"
                    ),
                })

    # -------------------------------------------------------------------------
    # BUY + SELL VOLUME CONSISTENCY
    # -------------------------------------------------------------------------

    if all(
        c in df.columns
        for c in [
            "BuyVol_LR1",
            "SellVol_LR1",
            "SumVolume_m"
        ]
    ):

        directional_volume = (
            df["BuyVol_LR1"]
            + df["SellVol_LR1"]
        )

        mask = (
            df["SumVolume_m"].notna()
            & directional_volume.notna()
            & (directional_volume > df["SumVolume_m"] * 1.000001)
        )

        violations = int(mask.sum())

        direction_records.append({
            "check": "BUY_PLUS_SELL_VOLUME_GT_TOTAL",
            "violations": violations,
            "rate": violations / len(df) if len(df) else 0,
        })

        if violations:
            for idx in df.index[mask][:10]:
                examples.append({
                    "diagnostic_type": "TRADE_DIRECTION",
                    "row_index": idx,
                    "symbol": diagnostic_symbol.loc[idx],
                    "date": diagnostic_date.loc[idx],
                    "field_1": "BuyVol_LR1 + SellVol_LR1",
                    "value_1": directional_volume.loc[idx],
                    "field_2": "SumVolume_m",
                    "value_2": df.loc[idx, "SumVolume_m"],
                    "description": (
                        "Directional volume exceeds total volume"
                    ),
                })

    # -------------------------------------------------------------------------
    # BUY + SELL DOLLAR CONSISTENCY
    # -------------------------------------------------------------------------

    if all(
        c in df.columns
        for c in [
            "BuyDollar_LR1",
            "SellDollar_LR1",
            "SumValue_m"
        ]
    ):

        directional_value = (
            df["BuyDollar_LR1"]
            + df["SellDollar_LR1"]
        )

        mask = (
            df["SumValue_m"].notna()
            & directional_value.notna()
            & (directional_value > df["SumValue_m"] * 1.000001)
        )

        violations = int(mask.sum())

        direction_records.append({
            "check": "BUY_PLUS_SELL_DOLLAR_GT_TOTAL",
            "violations": violations,
            "rate": violations / len(df) if len(df) else 0,
        })

        if violations:
            for idx in df.index[mask][:10]:
                examples.append({
                    "diagnostic_type": "TRADE_DIRECTION",
                    "row_index": idx,
                    "symbol": diagnostic_symbol.loc[idx],
                    "date": diagnostic_date.loc[idx],
                    "field_1": "BuyDollar_LR1 + SellDollar_LR1",
                    "value_1": directional_value.loc[idx],
                    "field_2": "SumValue_m",
                    "value_2": df.loc[idx, "SumValue_m"],
                    "description": (
                        "Directional dollar value exceeds total dollar value"
                    ),
                })

    # =============================================================================
    # LOT CONSISTENCY
    # =============================================================================

    if all(
        c in df.columns
        for c in [
            "NumOddLotTrades_m",
            "NumMixedLotTrades_m",
            "NumTrades_m"
        ]
    ):

        specialized_trade_count = (
            df["NumOddLotTrades_m"]
            + df["NumMixedLotTrades_m"]
        )

        mask = (
            df["NumTrades_m"].notna()
            & specialized_trade_count.notna()
            & (specialized_trade_count > df["NumTrades_m"])
        )

        violations = int(mask.sum())

        lot_records.append({
            "check": "ODD_PLUS_MIXED_TRADES_GT_TOTAL",
            "violations": violations,
            "rate": violations / len(df) if len(df) else 0,
        })

        if violations:
            for idx in df.index[mask][:10]:
                examples.append({
                    "diagnostic_type": "LOT_ACTIVITY",
                    "row_index": idx,
                    "symbol": diagnostic_symbol.loc[idx],
                    "date": diagnostic_date.loc[idx],
                    "field_1": (
                        "NumOddLotTrades_m + NumMixedLotTrades_m"
                    ),
                    "value_1": specialized_trade_count.loc[idx],
                    "field_2": "NumTrades_m",
                    "value_2": df.loc[idx, "NumTrades_m"],
                    "description": (
                        "Specialized lot trade counts exceed total trades"
                    ),
                })

    # -------------------------------------------------------------------------
    # ISO TRADE COUNT / VOLUME / VALUE CONSISTENCY
    # -------------------------------------------------------------------------

    if all(
        c in df.columns
        for c in [
            "NumISOTrades_m",
            "SumISOVolume_m",
            "SumISOValue_m"
        ]
    ):

        # ISO volume without ISO trades
        mask = (
            df["NumISOTrades_m"].notna()
            & df["SumISOVolume_m"].notna()
            & (df["NumISOTrades_m"] == 0)
            & (df["SumISOVolume_m"] > 0)
        )

        violations = int(mask.sum())

        lot_records.append({
            "check": "ISO_VOLUME_WITH_ZERO_ISO_TRADES",
            "violations": violations,
            "rate": violations / len(df) if len(df) else 0,
        })

        if violations:
            for idx in df.index[mask][:10]:
                examples.append({
                    "diagnostic_type": "ISO_ACTIVITY",
                    "row_index": idx,
                    "symbol": diagnostic_symbol.loc[idx],
                    "date": diagnostic_date.loc[idx],
                    "field_1": "NumISOTrades_m",
                    "value_1": df.loc[idx, "NumISOTrades_m"],
                    "field_2": "SumISOVolume_m",
                    "value_2": df.loc[idx, "SumISOVolume_m"],
                    "description": (
                        "ISO volume exists despite zero ISO trade count"
                    ),
                })

    # =============================================================================
    # ORDER-FLOW CONSISTENCY
    # =============================================================================

    if all(
        c in df.columns
        for c in [
            "TOfrShares_TW_m",
            "TOfrDollar_TW_m"
        ]
    ):

        mask = (
            df["TOfrShares_TW_m"].notna()
            & df["TOfrDollar_TW_m"].notna()
            & (df["TOfrShares_TW_m"] == 0)
            & (df["TOfrDollar_TW_m"] > 0)
        )

        violations = int(mask.sum())

        orderflow_records.append({
            "check": "OFFER_DOLLAR_WITH_ZERO_OFFER_SHARES",
            "violations": violations,
            "rate": violations / len(df) if len(df) else 0,
        })

        if violations:
            for idx in df.index[mask][:10]:
                examples.append({
                    "diagnostic_type": "ORDER_FLOW",
                    "row_index": idx,
                    "symbol": diagnostic_symbol.loc[idx],
                    "date": diagnostic_date.loc[idx],
                    "field_1": "TOfrShares_TW_m",
                    "value_1": df.loc[idx, "TOfrShares_TW_m"],
                    "field_2": "TOfrDollar_TW_m",
                    "value_2": df.loc[idx, "TOfrDollar_TW_m"],
                    "description": (
                        "Offer dollar value exists with zero offer shares"
                    ),
                })

    if all(
        c in df.columns
        for c in [
            "TBidShares_TW_m",
            "TBidDollar_TW_m"
        ]
    ):

        mask = (
            df["TBidShares_TW_m"].notna()
            & df["TBidDollar_TW_m"].notna()
            & (df["TBidShares_TW_m"] == 0)
            & (df["TBidDollar_TW_m"] > 0)
        )

        violations = int(mask.sum())

        orderflow_records.append({
            "check": "BID_DOLLAR_WITH_ZERO_BID_SHARES",
            "violations": violations,
            "rate": violations / len(df) if len(df) else 0,
        })

        if violations:
            for idx in df.index[mask][:10]:
                examples.append({
                    "diagnostic_type": "ORDER_FLOW",
                    "row_index": idx,
                    "symbol": diagnostic_symbol.loc[idx],
                    "date": diagnostic_date.loc[idx],
                    "field_1": "TBidShares_TW_m",
                    "value_1": df.loc[idx, "TBidShares_TW_m"],
                    "field_2": "TBidDollar_TW_m",
                    "value_2": df.loc[idx, "TBidDollar_TW_m"],
                    "description": (
                        "Bid dollar value exists with zero bid shares"
                    ),
                })

    # =============================================================================
    # NEGATIVE ACTIVITY
    # =============================================================================

    negative_activity_columns = [
        c for c in (
            TRADE_COUNT_FIELDS
            + TRADE_VOLUME_FIELDS
            + TRADE_VALUE_FIELDS
            + BUY_SELL_COUNT_FIELDS
            + BUY_SELL_VOLUME_FIELDS
            + BUY_SELL_DOLLAR_FIELDS
            + ISO_FIELDS
            + ODD_LOT_FIELDS
            + MIXED_LOT_FIELDS
            + ORDERFLOW_FIELDS
        )
        if c in df.columns
    ]

    if negative_activity_columns:

        negative_mask = (
            df[negative_activity_columns]
            .lt(0)
            .any(axis=1)
        )

        negative_count = int(negative_mask.sum())

        if negative_count:

            for idx in df.index[negative_mask][:20]:

                negative_fields = [
                    c
                    for c in negative_activity_columns
                    if pd.notna(df.loc[idx, c])
                    and df.loc[idx, c] < 0
                ]

                examples.append({
                    "diagnostic_type": "NEGATIVE_ACTIVITY",
                    "row_index": idx,
                    "symbol": diagnostic_symbol.loc[idx],
                    "date": diagnostic_date.loc[idx],
                    "field_1": ",".join(negative_fields),
                    "value_1": np.nan,
                    "field_2": "",
                    "value_2": np.nan,
                    "description": (
                        "Negative trading activity/order-flow value detected"
                    ),
                })


# =============================================================================
# BUILD FIELD SUMMARY
# =============================================================================

activity_summary = pd.DataFrame(
    list(field_stats.values())
)

if not activity_summary.empty:

    activity_summary["missing_rate"] = (
        activity_summary["missing_count"]
        / activity_summary["rows_observed"]
    )

    activity_summary["negative_rate"] = (
        activity_summary["negative_count"]
        / activity_summary["non_null_count"].replace(0, np.nan)
    )

    activity_summary["zero_rate"] = (
        activity_summary["zero_count"]
        / activity_summary["non_null_count"].replace(0, np.nan)
    )


# =============================================================================
# BUILD SYMBOL SUMMARY
# =============================================================================

symbol_summary = pd.DataFrame(
    list(symbol_stats.values())
)

if not symbol_summary.empty:

    symbol_summary = symbol_summary.sort_values(
        ["negative_activity_rows", "rows"],
        ascending=[False, False]
    )


# =============================================================================
# BUILD DATE SUMMARY
# =============================================================================

date_summary = pd.DataFrame(
    list(date_stats.values())
)

if not date_summary.empty:

    date_summary = date_summary.sort_values(
        "date"
    )


# =============================================================================
# CONSISTENCY TABLES
# =============================================================================

trade_consistency_df = pd.DataFrame(
    trade_consistency_records
)

direction_df = pd.DataFrame(
    direction_records
)

lot_df = pd.DataFrame(
    lot_records
)

orderflow_df = pd.DataFrame(
    orderflow_records
)


# =============================================================================
# EXAMPLES
# =============================================================================

examples_df = pd.DataFrame(examples)

if not examples_df.empty:
    examples_df = examples_df.drop_duplicates()


# =============================================================================
# SUMMARY METRICS
# =============================================================================

negative_activity_total = 0
missing_activity_total = 0

if not activity_summary.empty:

    negative_activity_total = int(
        activity_summary["negative_count"].sum()
    )

    missing_activity_total = int(
        activity_summary["missing_count"].sum()
    )


trade_consistency_violations = (
    int(trade_consistency_df["violations"].sum())
    if not trade_consistency_df.empty
    else 0
)

direction_violations = (
    int(direction_df["violations"].sum())
    if not direction_df.empty
    else 0
)

lot_violations = (
    int(lot_df["violations"].sum())
    if not lot_df.empty
    else 0
)

orderflow_violations = (
    int(orderflow_df["violations"].sum())
    if not orderflow_df.empty
    else 0
)


# =============================================================================
# SUMMARY OUTPUT
# =============================================================================

summary_rows = [
    {
        "metric": "input_rows",
        "value": total_rows,
    },
    {
        "metric": "activity_orderflow_fields_evaluated",
        "value": len(existing_fields),
    },
    {
        "metric": "negative_activity_values",
        "value": negative_activity_total,
    },
    {
        "metric": "missing_activity_values",
        "value": missing_activity_total,
    },
    {
        "metric": "trade_consistency_violations",
        "value": trade_consistency_violations,
    },
    {
        "metric": "trade_direction_violations",
        "value": direction_violations,
    },
    {
        "metric": "lot_activity_violations",
        "value": lot_violations,
    },
    {
        "metric": "orderflow_violations",
        "value": orderflow_violations,
    },
]

summary_df = pd.DataFrame(summary_rows)


# =============================================================================
# WRITE OUTPUTS
# =============================================================================

summary_df.to_csv(
    SUMMARY_FILE,
    index=False
)

activity_summary.to_csv(
    ACTIVITY_FILE,
    index=False
)

symbol_summary.to_csv(
    SYMBOL_FILE,
    index=False
)

date_summary.to_csv(
    DATE_FILE,
    index=False
)

examples_df.to_csv(
    EXAMPLES_FILE,
    index=False
)

trade_consistency_df.to_csv(
    TRADE_CONSISTENCY_FILE,
    index=False
)

direction_df.to_csv(
    DIRECTION_FILE,
    index=False
)

lot_df.to_csv(
    LOT_FILE,
    index=False
)

orderflow_df.to_csv(
    ORDERFLOW_FILE,
    index=False
)


# =============================================================================
# CONSOLE REPORT
# =============================================================================

print()
print("=" * 80)
print("TRADING ACTIVITY & ORDER-FLOW ECONOMIC VALIDATION SUMMARY")
print("=" * 80)

print(f"Input rows:                         {total_rows:,}")
print(
    f"Activity/order-flow fields:        "
    f"{len(existing_fields)}"
)
print(
    f"Negative activity values:          "
    f"{negative_activity_total:,}"
)
print(
    f"Missing activity values:            "
    f"{missing_activity_total:,}"
)

print()
print("CONSISTENCY RESULTS")
print("-" * 80)

print(
    f"Trade consistency violations:      "
    f"{trade_consistency_violations:,}"
)

print(
    f"Trade-direction violations:        "
    f"{direction_violations:,}"
)

print(
    f"Lot-activity violations:           "
    f"{lot_violations:,}"
)

print(
    f"Order-flow violations:             "
    f"{orderflow_violations:,}"
)


# =============================================================================
# INTERPRETATION
# =============================================================================

print()
print("=" * 80)
print("INTERPRETATION")
print("=" * 80)

print(
    "Negative trading activity/order-flow values were investigated "
    "without automatic exclusion."
)

print(
    "Buy/sell, trade-count, volume, dollar-value, lot, ISO, and "
    "order-flow relationships were diagnosed without imposing "
    "automatic correction rules."
)

print()
print("No observations were removed.")
print("No values were modified.")
print("No imputation was performed.")
print("No activity/order-flow fields were corrected.")


# =============================================================================
# STATUS
# =============================================================================

print()
print("=" * 80)
print("STATUS")
print("=" * 80)

print(
    "PASS — trading activity and order-flow economic validation completed."
)

print(
    "REVIEW — activity/order-flow inconsistencies require semantic "
    "interpretation before any exclusion or correction."
)


# =============================================================================
# OUTPUTS
# =============================================================================

print()
print("=" * 80)
print("OUTPUTS")
print("=" * 80)

print(f"Summary:")
print(f"  {SUMMARY_FILE}")

print(f"Activity summary:")
print(f"  {ACTIVITY_FILE}")

print(f"Symbol summary:")
print(f"  {SYMBOL_FILE}")

print(f"Date summary:")
print(f"  {DATE_FILE}")

print(f"Violation examples:")
print(f"  {EXAMPLES_FILE}")

print(f"Trade consistency:")
print(f"  {TRADE_CONSISTENCY_FILE}")

print(f"Direction consistency:")
print(f"  {DIRECTION_FILE}")

print(f"Lot consistency:")
print(f"  {LOT_FILE}")

print(f"Order-flow consistency:")
print(f"  {ORDERFLOW_FILE}")

print()
print("=" * 80)
print("IMPORTANT")
print("=" * 80)

print(
    "This stage is diagnostic only. "
    "No canonical TAQ data was changed."
)