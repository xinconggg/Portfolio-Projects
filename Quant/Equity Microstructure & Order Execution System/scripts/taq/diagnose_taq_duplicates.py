from pathlib import Path
import pandas as pd
import numpy as np


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "taq"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "taq"

SOURCE_FILE = RAW_DIR / "taq.csv"

DIAGNOSTIC_FILE = OUTPUT_DIR / "taq_duplicate_diagnostic.csv"
EXAMPLES_FILE = OUTPUT_DIR / "taq_duplicate_examples.csv"

CHUNK_SIZE = 100_000


# =============================================================================
# CONFIGURATION
# =============================================================================

DATE_COLUMN = "date"
SYMBOL_COLUMN = "symbol"

# Fields that represent event/snapshot timing.
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

# Fields representing quote state.
QUOTE_COLUMNS = [
    "BB_1pm",
    "BO_1pm",
    "MID_1pm",
    "BB_c1",
    "BO_c1",
    "Mid_c1",
    "BB_4pm",
    "BO_4pm",
    "Mid_4pm",
    "LBB",
    "LBO",
    "LMid",
    "CPrc",
    "CPrc2",
]

# Fields representing trade/event prices.
TRADE_PRICE_COLUMNS = [
    "OPrice",
    "DPrice",
    "LPrice",
    "Price_1pm",
    "Price_4pm",
]

# Fields representing activity / volume.
ACTIVITY_COLUMNS = [
    "Vol_oc",
    "Value_oc",
    "NumTrades_t",
    "NumTrades_m",
    "SumVolume_t",
    "SumVolume_m",
    "SumValue_b",
    "SumValue_m",
]

# Derived fields that should NOT normally define a raw-event duplicate key.
DERIVED_METRIC_COLUMNS = [
    "Ret_pre_t",
    "Ret_mkt_t",
    "Ret_post_t",
    "MFCount",
    "NumISOTrades_m",
    "SumISOVolume_m",
    "SumISOValue_m",
    "NumOddLotTrades_m",
    "SumOddLotVolume_m",
    "SumOddLotValue_m",
    "NumMixedLotTrades_m",
    "SumMixedLotVolume_m",
    "SumMixedLotValue_m",
    "BuyNumTrades_LR1",
    "SellNumTrades_LR1",
    "BuyVol_LR1",
    "SellVol_LR1",
    "BuyDollar_LR1",
    "SellDollar_LR1",
    "ESpreadDollar_Avg1",
    "ESpreadPct_Avg1",
    "RSpreadDollar_Avg1",
    "RSpreadPct_Avg1",
    "PriceImpactDollar_Avg1",
    "PriceImpactPct_Avg1",
    "ESpreadDollar_VW1",
    "ESpreadDollar_SW1",
    "ESpreadPct_VW1",
    "ESpreadPct_SW1",
    "RSpreadDollar_SW1",
    "RSpreadDollar_VW1",
    "RSpreadPct_SW1",
    "RSpreadPct_VW1",
    "PriceImpactDollar_VW1",
    "PriceImpactDollar_SW1",
    "PriceImpactPct_VW1",
    "PriceImpactPct_SW1",
    "IVol_t_m",
    "IVol_q_m",
    "NumExtremeOfr_m",
    "NumExtremeBid_m",
    "QSpreadDollar_EW_m",
    "QSpreadPct_EW_m",
    "QSpreadDollar_TW_m",
    "QSpreadPct_TW_m",
    "TOfrDollar_TW_m",
    "TBidDollar_TW_m",
    "TOfrShares_TW_m",
    "TBidShares_TW_m",
    "BOfrDollar_TW_m",
    "BBidDollar_TW_m",
    "BOfrShares_TW_m",
    "BBidShares_TW_m",
    "VarianceRatio1",
    "VarianceRatio2",
    "TSignSqrtDVol1",
    "TSignSqrtDVol2",
    "NObsUsed1",
    "NObsUsed2",
    "NumTimeUnitsWithTrade1",
    "NumTimeUnitsWithTrade2",
    "HIndex1",
]


# =============================================================================
# HELPERS
# =============================================================================

def normalize_columns(columns):
    return [str(c).strip() for c in columns]


def existing_columns(df, columns):
    return [c for c in columns if c in df.columns]


def count_duplicate_groups(df, subset):
    """
    Return:
        duplicate_rows = number of rows belonging to duplicate groups
        duplicate_extra_rows = rows beyond first observation in each group
        duplicate_groups = number of duplicated groups
    """
    subset = existing_columns(df, subset)

    if not subset:
        return 0, 0, 0

    mask = df.duplicated(subset=subset, keep=False)

    if not mask.any():
        return 0, 0, 0

    dup_df = df.loc[mask, subset]

    group_sizes = dup_df.groupby(
        subset,
        dropna=False,
        sort=False
    ).size()

    duplicate_groups = int((group_sizes > 1).sum())
    duplicate_rows = int(group_sizes[group_sizes > 1].sum())
    duplicate_extra_rows = int((group_sizes[group_sizes > 1] - 1).sum())

    return duplicate_rows, duplicate_extra_rows, duplicate_groups


def build_candidate_keys(columns):
    """
    Construct progressively broader duplicate keys.
    """

    keys = {}

    # -------------------------------------------------------------------------
    # Level 1: date + symbol
    # -------------------------------------------------------------------------
    keys["date_symbol"] = [
        DATE_COLUMN,
        SYMBOL_COLUMN,
    ]

    # -------------------------------------------------------------------------
    # Level 2: date + symbol + primary event time
    # -------------------------------------------------------------------------
    primary_time_candidates = [
        "OTime",
        "DTime",
        "LQTime",
        "LTTime",
        "TTime_1pm",
        "TTime_4pm",
    ]

    for time_col in primary_time_candidates:
        if time_col in columns:
            keys[f"date_symbol_{time_col.lower()}"] = [
                DATE_COLUMN,
                SYMBOL_COLUMN,
                time_col,
            ]

    # -------------------------------------------------------------------------
    # Level 3: date + symbol + event time + event price
    # -------------------------------------------------------------------------
    event_pairs = [
        ("OTime", "OPrice"),
        ("DTime", "DPrice"),
        ("LTTime", "LPrice"),
        ("TTime_1pm", "Price_1pm"),
        ("TTime_4pm", "Price_4pm"),
    ]

    for time_col, price_col in event_pairs:
        if time_col in columns and price_col in columns:
            keys[f"date_symbol_{time_col.lower()}_{price_col.lower()}"] = [
                DATE_COLUMN,
                SYMBOL_COLUMN,
                time_col,
                price_col,
            ]

    # -------------------------------------------------------------------------
    # Level 4: quote snapshot keys
    # -------------------------------------------------------------------------
    quote_snapshot_keys = [
        (
            "QTime_1pm",
            "BB_1pm",
            "BO_1pm",
        ),
        (
            "QTime_c1",
            "BB_c1",
            "BO_c1",
        ),
        (
            "QTime_4pm",
            "BB_4pm",
            "BO_4pm",
        ),
        (
            "LQTime",
            "LBB",
            "LBO",
        ),
    ]

    for time_col, bid_col, ask_col in quote_snapshot_keys:
        if (
            time_col in columns
            and bid_col in columns
            and ask_col in columns
        ):
            keys[
                f"date_symbol_{time_col.lower()}_bid_ask"
            ] = [
                DATE_COLUMN,
                SYMBOL_COLUMN,
                time_col,
                bid_col,
                ask_col,
            ]

    # -------------------------------------------------------------------------
    # Level 5: full row
    # -------------------------------------------------------------------------
    keys["full_row"] = list(columns)

    return keys


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 80)
    print("PHASE 5 — STEP 8: TAQ DUPLICATE ANALYSIS")
    print("=" * 80)

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"TAQ source file not found:\n{SOURCE_FILE}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Read header
    # -------------------------------------------------------------------------
    header = pd.read_csv(
        SOURCE_FILE,
        nrows=0
    )

    columns = normalize_columns(header.columns)

    print(f"Source file: {SOURCE_FILE}")
    print(f"Columns: {len(columns):,}")
    print(f"Chunk size: {CHUNK_SIZE:,}")

    if DATE_COLUMN not in columns:
        raise ValueError(
            f"Required date column '{DATE_COLUMN}' not found."
        )

    if SYMBOL_COLUMN not in columns:
        raise ValueError(
            f"Required symbol column '{SYMBOL_COLUMN}' not found."
        )

    # -------------------------------------------------------------------------
    # Candidate duplicate keys
    # -------------------------------------------------------------------------
    candidate_keys = build_candidate_keys(columns)

    print("\nCandidate duplicate keys:")

    for key_name, key_columns in candidate_keys.items():
        print(
            f"  {key_name}: "
            f"{', '.join(key_columns)}"
        )

    # -------------------------------------------------------------------------
    # We need global duplicate detection.
    #
    # Because the file is only ~122k rows based on prior diagnostics,
    # loading the complete file is reasonable.
    #
    # The implementation nevertheless keeps the logic explicit and can
    # easily be adapted to a larger source.
    # -------------------------------------------------------------------------
    print("\nLoading source data for duplicate analysis...")

    df = pd.read_csv(
        SOURCE_FILE,
        low_memory=False
    )

    df.columns = normalize_columns(df.columns)

    total_rows = len(df)

    print(f"Rows loaded: {total_rows:,}")

    # -------------------------------------------------------------------------
    # Normalize date representation only for diagnostic comparison.
    #
    # IMPORTANT:
    # Do not modify the raw source.
    # -------------------------------------------------------------------------
    if DATE_COLUMN in df.columns:

        raw_date = df[DATE_COLUMN].astype("string")

        parsed_date = pd.to_datetime(
            raw_date,
            format="%d/%m/%Y",
            errors="coerce"
        )

        df["_diagnostic_date"] = parsed_date.dt.strftime(
            "%Y-%m-%d"
        )

    # -------------------------------------------------------------------------
    # Exact full-row duplicate count
    # -------------------------------------------------------------------------
    full_duplicate_mask = df.duplicated(
        keep=False
    )

    full_duplicate_rows = int(
        full_duplicate_mask.sum()
    )

    full_duplicate_extra_rows = int(
        df.duplicated(
            keep="first"
        ).sum()
    )

    full_duplicate_groups = 0

    if full_duplicate_rows > 0:

        full_group_sizes = (
            df.loc[full_duplicate_mask]
            .groupby(
                columns,
                dropna=False,
                sort=False
            )
            .size()
        )

        full_duplicate_groups = int(
            (full_group_sizes > 1).sum()
        )

    # -------------------------------------------------------------------------
    # Candidate-key diagnostics
    # -------------------------------------------------------------------------
    diagnostic_rows = []

    for key_name, key_columns in candidate_keys.items():

        existing = existing_columns(
            df,
            key_columns
        )

        if not existing:
            continue

        duplicate_rows = 0
        duplicate_extra_rows = 0
        duplicate_groups = 0

        mask = df.duplicated(
            subset=existing,
            keep=False
        )

        if mask.any():

            grouped = (
                df.loc[mask, existing]
                .groupby(
                    existing,
                    dropna=False,
                    sort=False
                )
                .size()
            )

            grouped = grouped[grouped > 1]

            duplicate_groups = int(
                len(grouped)
            )

            duplicate_rows = int(
                grouped.sum()
            )

            duplicate_extra_rows = int(
                (grouped - 1).sum()
            )

        diagnostic_rows.append(
            {
                "diagnostic": "DUPLICATE_KEY",
                "key_name": key_name,
                "key_columns": "|".join(existing),
                "key_column_count": len(existing),
                "total_rows": total_rows,
                "duplicate_groups": duplicate_groups,
                "duplicate_rows": duplicate_rows,
                "duplicate_extra_rows": duplicate_extra_rows,
                "duplicate_row_rate": (
                    duplicate_rows / total_rows
                    if total_rows > 0
                    else np.nan
                ),
                "duplicate_extra_row_rate": (
                    duplicate_extra_rows / total_rows
                    if total_rows > 0
                    else np.nan
                ),
            }
        )

    # -------------------------------------------------------------------------
    # Add global structural diagnostics
    # -------------------------------------------------------------------------
    date_symbol_duplicates = (
        df.duplicated(
            subset=[DATE_COLUMN, SYMBOL_COLUMN],
            keep=False
        )
    )

    date_symbol_duplicate_rows = int(
        date_symbol_duplicates.sum()
    )

    date_symbol_duplicate_extra_rows = int(
        df.duplicated(
            subset=[DATE_COLUMN, SYMBOL_COLUMN],
            keep="first"
        ).sum()
    )

    # -------------------------------------------------------------------------
    # Missing key diagnostics
    # -------------------------------------------------------------------------
    key_missing_rows = {}

    for key_name, key_columns in candidate_keys.items():

        existing = existing_columns(
            df,
            key_columns
        )

        if not existing:
            continue

        missing_mask = df[existing].isna().any(axis=1)

        key_missing_rows[key_name] = int(
            missing_mask.sum()
        )

    # -------------------------------------------------------------------------
    # Build summary rows
    # -------------------------------------------------------------------------
    diagnostic_rows.append(
        {
            "diagnostic": "GLOBAL",
            "key_name": "FULL_ROW",
            "key_columns": "|".join(columns),
            "key_column_count": len(columns),
            "total_rows": total_rows,
            "duplicate_groups": full_duplicate_groups,
            "duplicate_rows": full_duplicate_rows,
            "duplicate_extra_rows": full_duplicate_extra_rows,
            "duplicate_row_rate": (
                full_duplicate_rows / total_rows
                if total_rows > 0
                else np.nan
            ),
            "duplicate_extra_row_rate": (
                full_duplicate_extra_rows / total_rows
                if total_rows > 0
                else np.nan
            ),
        }
    )

    diagnostic_rows.append(
        {
            "diagnostic": "GLOBAL",
            "key_name": "DATE_SYMBOL",
            "key_columns": f"{DATE_COLUMN}|{SYMBOL_COLUMN}",
            "key_column_count": 2,
            "total_rows": total_rows,
            "duplicate_groups": int(
                df.loc[date_symbol_duplicates]
                .groupby(
                    [DATE_COLUMN, SYMBOL_COLUMN],
                    dropna=False
                )
                .ngroups
            ) if date_symbol_duplicate_rows > 0 else 0,
            "duplicate_rows": date_symbol_duplicate_rows,
            "duplicate_extra_rows": date_symbol_duplicate_extra_rows,
            "duplicate_row_rate": (
                date_symbol_duplicate_rows / total_rows
                if total_rows > 0
                else np.nan
            ),
            "duplicate_extra_row_rate": (
                date_symbol_duplicate_extra_rows / total_rows
                if total_rows > 0
                else np.nan
            ),
        }
    )

    diagnostic_df = pd.DataFrame(
        diagnostic_rows
    )

    # -------------------------------------------------------------------------
    # Missing key summary
    # -------------------------------------------------------------------------
    missing_rows = []

    for key_name, count in key_missing_rows.items():

        key_columns = candidate_keys[key_name]

        missing_rows.append(
            {
                "diagnostic": "KEY_MISSINGNESS",
                "key_name": key_name,
                "key_columns": "|".join(
                    existing_columns(
                        df,
                        key_columns
                    )
                ),
                "key_column_count": len(
                    existing_columns(
                        df,
                        key_columns
                    )
                ),
                "total_rows": total_rows,
                "duplicate_groups": np.nan,
                "duplicate_rows": np.nan,
                "duplicate_extra_rows": np.nan,
                "duplicate_row_rate": np.nan,
                "duplicate_extra_row_rate": np.nan,
                "key_missing_rows": count,
                "key_missing_rate": (
                    count / total_rows
                    if total_rows > 0
                    else np.nan
                ),
            }
        )

    if missing_rows:

        missing_df = pd.DataFrame(
            missing_rows
        )

        diagnostic_df = pd.concat(
            [
                diagnostic_df,
                missing_df
            ],
            ignore_index=True
        )

    # -------------------------------------------------------------------------
    # Save diagnostics
    # -------------------------------------------------------------------------
    diagnostic_df.to_csv(
        DIAGNOSTIC_FILE,
        index=False
    )

    # =============================================================================
    # DUPLICATE EXAMPLES
    # =============================================================================

    example_frames = []

    # -------------------------------------------------------------------------
    # Exact duplicate examples
    # -------------------------------------------------------------------------
    if full_duplicate_rows > 0:

        full_dup_examples = (
            df.loc[
                full_duplicate_mask
            ]
            .copy()
            .head(100)
        )

        full_dup_examples.insert(
            0,
            "diagnostic_key",
            "FULL_ROW"
        )

        full_dup_examples.insert(
            1,
            "duplicate_group_marker",
            full_dup_examples.groupby(
                columns,
                dropna=False
            ).ngroup()
        )

        example_frames.append(
            full_dup_examples
        )

    # -------------------------------------------------------------------------
    # Date-symbol duplicate examples
    # -------------------------------------------------------------------------
    if date_symbol_duplicate_rows > 0:

        ds_examples = (
            df.loc[
                date_symbol_duplicates
            ]
            .copy()
            .head(100)
        )

        ds_examples.insert(
            0,
            "diagnostic_key",
            "DATE_SYMBOL"
        )

        ds_examples.insert(
            1,
            "duplicate_group_marker",
            ds_examples.groupby(
                [DATE_COLUMN, SYMBOL_COLUMN],
                dropna=False
            ).ngroup()
        )

        example_frames.append(
            ds_examples
        )

    # -------------------------------------------------------------------------
    # Candidate event-key examples
    # -------------------------------------------------------------------------
    for key_name, key_columns in candidate_keys.items():

        if key_name in {
            "date_symbol",
            "full_row"
        }:
            continue

        existing = existing_columns(
            df,
            key_columns
        )

        if not existing:
            continue

        mask = df.duplicated(
            subset=existing,
            keep=False
        )

        if not mask.any():
            continue

        examples = (
            df.loc[mask]
            .copy()
            .head(50)
        )

        examples.insert(
            0,
            "diagnostic_key",
            key_name
        )

        examples.insert(
            1,
            "duplicate_group_marker",
            examples.groupby(
                existing,
                dropna=False
            ).ngroup()
        )

        example_frames.append(
            examples
        )

    # -------------------------------------------------------------------------
    # Save examples
    # -------------------------------------------------------------------------
    if example_frames:

        examples_df = pd.concat(
            example_frames,
            ignore_index=True
        )

        examples_df.to_csv(
            EXAMPLES_FILE,
            index=False
        )

    else:

        # Preserve schema even when no duplicates exist.
        pd.DataFrame(
            columns=[
                "diagnostic_key",
                "duplicate_group_marker"
            ] + columns
        ).to_csv(
            EXAMPLES_FILE,
            index=False
        )

    # =============================================================================
    # CONSOLE REPORT
    # =============================================================================

    print("\n" + "=" * 80)
    print("DUPLICATE DIAGNOSTIC SUMMARY")
    print("=" * 80)

    print(
        f"Total rows:                         {total_rows:,}"
    )

    print(
        f"Exact duplicate rows:               "
        f"{full_duplicate_rows:,}"
    )

    print(
        f"Exact duplicate extra rows:         "
        f"{full_duplicate_extra_rows:,}"
    )

    print(
        f"Date+symbol duplicate rows:         "
        f"{date_symbol_duplicate_rows:,}"
    )

    print(
        f"Date+symbol duplicate extra rows:   "
        f"{date_symbol_duplicate_extra_rows:,}"
    )

    print("\nCandidate-key results:")

    display_columns = [
        "key_name",
        "duplicate_groups",
        "duplicate_rows",
        "duplicate_extra_rows",
        "duplicate_row_rate",
    ]

    print(
        diagnostic_df.loc[
            diagnostic_df["diagnostic"].isin(
                ["DUPLICATE_KEY", "GLOBAL"]
            ),
            display_columns
        ].to_string(
            index=False
        )
    )

    print("\n" + "=" * 80)
    print("OUTPUTS")
    print("=" * 80)

    print(
        f"Duplicate diagnostic:\n{DIAGNOSTIC_FILE}"
    )

    print(
        f"Duplicate examples:\n{EXAMPLES_FILE}"
    )

    print("\n" + "=" * 80)
    print("STATUS")
    print("=" * 80)

    print(
        "PASS — duplicate diagnostics generated."
    )

    print(
        "IMPORTANT:"
    )

    print(
        "No observations were removed."
    )

    print(
        "No duplicate-cleaning rule was applied."
    )

    print(
        "Duplicate candidates must be interpreted "
        "before any exclusion rule is defined."
    )


if __name__ == "__main__":
    main()