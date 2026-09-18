from pathlib import Path
import pandas as pd
import numpy as np


# =============================================================================
# PROJECT PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data" / "processed" / "taq"

INPUT_FILE = DATA_DIR / "taq_cleaned.csv"

OUTPUT_DIR = DATA_DIR / "quote_semantic_investigation"

OUTPUT_SUMMARY = OUTPUT_DIR / "taq_quote_economic_validation_summary.csv"
OUTPUT_SET_SUMMARY = OUTPUT_DIR / "taq_quote_economic_validation_by_set.csv"
OUTPUT_SYMBOL = OUTPUT_DIR / "taq_quote_economic_validation_by_symbol.csv"
OUTPUT_DATE = OUTPUT_DIR / "taq_quote_economic_validation_by_date.csv"
OUTPUT_EXAMPLES = OUTPUT_DIR / "taq_quote_economic_validation_examples.csv"
OUTPUT_SPREAD = OUTPUT_DIR / "taq_quote_spread_diagnostics.csv"
OUTPUT_CROSS_FIELD = OUTPUT_DIR / "taq_quote_economic_crossfield.csv"


# =============================================================================
# CONFIGURATION
# =============================================================================

CHUNK_SIZE = 100_000

QUOTE_SETS = {
    "1pm": {
        "bid": "BB_1pm",
        "ask": "BO_1pm",
        "mid": "MID_1pm",
        "time": "QTime_1pm",
    },
    "c1": {
        "bid": "BB_c1",
        "ask": "BO_c1",
        "mid": "Mid_c1",
        "time": "QTime_c1",
    },
    "4pm": {
        "bid": "BB_4pm",
        "ask": "BO_4pm",
        "mid": "Mid_4pm",
        "time": "QTime_4pm",
    },
    "last": {
        "bid": "LBB",
        "ask": "LBO",
        "mid": "LMid",
        "time": "LQTime",
    },
}


# =============================================================================
# HELPERS
# =============================================================================

def safe_numeric(series):
    return pd.to_numeric(series, errors="coerce")


def summarize_numeric(series):
    """
    Return robust distribution diagnostics.
    """
    s = safe_numeric(series).dropna()

    if len(s) == 0:
        return {
            "count": 0,
            "min": np.nan,
            "p01": np.nan,
            "p05": np.nan,
            "median": np.nan,
            "p95": np.nan,
            "p99": np.nan,
            "max": np.nan,
            "mean": np.nan,
        }

    return {
        "count": len(s),
        "min": s.min(),
        "p01": s.quantile(0.01),
        "p05": s.quantile(0.05),
        "median": s.median(),
        "p95": s.quantile(0.95),
        "p99": s.quantile(0.99),
        "max": s.max(),
        "mean": s.mean(),
    }


def validate_columns(columns):
    required = {"date", "symbol"}

    for q in QUOTE_SETS.values():
        required.update(
            [
                q["bid"],
                q["ask"],
                q["mid"],
                q["time"],
            ]
        )

    missing = sorted(required - set(columns))

    if missing:
        raise ValueError(
            "Input file is missing required quote/economic validation columns:\n"
            + "\n".join(f"  - {c}" for c in missing)
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 80)
    print("PHASE 5 — TAQ QUOTE ECONOMIC VALIDATION")
    print("=" * 80)
    print(f"Input file:\n  {INPUT_FILE}")
    print(f"Output directory:\n  {OUTPUT_DIR}")

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Inspect schema
    # -------------------------------------------------------------------------

    header = pd.read_csv(INPUT_FILE, nrows=0)

    validate_columns(header.columns)

    print(f"Columns found: {len(header.columns)}")

    # -------------------------------------------------------------------------
    # Storage
    # -------------------------------------------------------------------------

    set_records = []
    symbol_records = []
    date_records = []
    example_records = []
    spread_records = []
    crossfield_records = []

    total_rows = 0

    # Global quote statistics
    global_stats = {
        qset: {
            "rows": 0,
            "non_null_bid_ask": 0,
            "bid_gt_ask": 0,
            "bid_eq_ask": 0,
            "bid_lt_ask": 0,
            "midpoint_consistent": 0,
            "midpoint_inconsistent": 0,
            "negative_spread": 0,
            "zero_spread": 0,
            "positive_spread": 0,
            "bid_negative": 0,
            "ask_negative": 0,
            "mid_negative": 0,
        }
        for qset in QUOTE_SETS
    }

    # -------------------------------------------------------------------------
    # Chunk processing
    # -------------------------------------------------------------------------

    for chunk_number, chunk in enumerate(
        pd.read_csv(
            INPUT_FILE,
            chunksize=CHUNK_SIZE,
            low_memory=False,
        ),
        start=1,
    ):

        print(
            f"Processing chunk {chunk_number}: "
            f"{len(chunk):,} rows"
        )

        total_rows += len(chunk)

        # Normalize identifiers for diagnostics only.
        chunk["symbol"] = chunk["symbol"].astype("string")

        # Parse date from canonical cleaned file.
        chunk["date"] = pd.to_datetime(
            chunk["date"],
            errors="coerce",
        )

        # ---------------------------------------------------------------------
        # Process each quote set
        # ---------------------------------------------------------------------

        for qset, config in QUOTE_SETS.items():

            bid_col = config["bid"]
            ask_col = config["ask"]
            mid_col = config["mid"]

            bid = safe_numeric(chunk[bid_col])
            ask = safe_numeric(chunk[ask_col])
            mid = safe_numeric(chunk[mid_col])

            valid = bid.notna() & ask.notna()

            spread = ask - bid

            midpoint_expected = (bid + ask) / 2.0

            midpoint_difference = mid - midpoint_expected

            midpoint_consistent = (
                valid
                & mid.notna()
                & np.isclose(
                    mid,
                    midpoint_expected,
                    rtol=1e-10,
                    atol=1e-8,
                    equal_nan=False,
                )
            )

            bid_gt_ask = valid & (bid > ask)
            bid_eq_ask = valid & (bid == ask)
            bid_lt_ask = valid & (bid < ask)

            negative_spread = valid & (spread < 0)
            zero_spread = valid & (spread == 0)
            positive_spread = valid & (spread > 0)

            bid_negative = bid.notna() & (bid < 0)
            ask_negative = ask.notna() & (ask < 0)
            mid_negative = mid.notna() & (mid < 0)

            stats = global_stats[qset]

            stats["rows"] += len(chunk)
            stats["non_null_bid_ask"] += int(valid.sum())
            stats["bid_gt_ask"] += int(bid_gt_ask.sum())
            stats["bid_eq_ask"] += int(bid_eq_ask.sum())
            stats["bid_lt_ask"] += int(bid_lt_ask.sum())
            stats["midpoint_consistent"] += int(
                midpoint_consistent.sum()
            )
            stats["midpoint_inconsistent"] += int(
                (
                    valid
                    & mid.notna()
                    & ~midpoint_consistent
                ).sum()
            )
            stats["negative_spread"] += int(
                negative_spread.sum()
            )
            stats["zero_spread"] += int(
                zero_spread.sum()
            )
            stats["positive_spread"] += int(
                positive_spread.sum()
            )
            stats["bid_negative"] += int(
                bid_negative.sum()
            )
            stats["ask_negative"] += int(
                ask_negative.sum()
            )
            stats["mid_negative"] += int(
                mid_negative.sum()
            )

            # -----------------------------------------------------------------
            # Distribution diagnostics for quoted spread
            # -----------------------------------------------------------------

            spread_valid = spread[valid].dropna()

            if len(spread_valid):

                spread_records.append(
                    {
                        "quote_set": qset,
                        "rows": len(spread_valid),
                        "negative_spread_count": int(
                            (spread_valid < 0).sum()
                        ),
                        "zero_spread_count": int(
                            (spread_valid == 0).sum()
                        ),
                        "positive_spread_count": int(
                            (spread_valid > 0).sum()
                        ),
                        "negative_spread_rate": float(
                            (spread_valid < 0).mean()
                        ),
                        "zero_spread_rate": float(
                            (spread_valid == 0).mean()
                        ),
                        "positive_spread_rate": float(
                            (spread_valid > 0).mean()
                        ),
                        "min_spread": float(
                            spread_valid.min()
                        ),
                        "p01_spread": float(
                            spread_valid.quantile(0.01)
                        ),
                        "p05_spread": float(
                            spread_valid.quantile(0.05)
                        ),
                        "median_spread": float(
                            spread_valid.median()
                        ),
                        "p95_spread": float(
                            spread_valid.quantile(0.95)
                        ),
                        "p99_spread": float(
                            spread_valid.quantile(0.99)
                        ),
                        "max_spread": float(
                            spread_valid.max()
                        ),
                        "mean_spread": float(
                            spread_valid.mean()
                        ),
                    }
                )

            # -----------------------------------------------------------------
            # Quote-set summary by chunk
            # -----------------------------------------------------------------

            set_records.append(
                {
                    "quote_set": qset,
                    "rows": len(chunk),
                    "non_null_bid_ask": int(valid.sum()),
                    "bid_gt_ask": int(bid_gt_ask.sum()),
                    "bid_eq_ask": int(bid_eq_ask.sum()),
                    "bid_lt_ask": int(bid_lt_ask.sum()),
                    "bid_gt_ask_rate": (
                        float(bid_gt_ask.sum() / valid.sum())
                        if valid.sum()
                        else np.nan
                    ),
                    "negative_spread": int(
                        negative_spread.sum()
                    ),
                    "zero_spread": int(
                        zero_spread.sum()
                    ),
                    "positive_spread": int(
                        positive_spread.sum()
                    ),
                    "midpoint_inconsistent": int(
                        (
                            valid
                            & mid.notna()
                            & ~midpoint_consistent
                        ).sum()
                    ),
                    "bid_negative": int(
                        bid_negative.sum()
                    ),
                    "ask_negative": int(
                        ask_negative.sum()
                    ),
                    "mid_negative": int(
                        mid_negative.sum()
                    ),
                }
            )

            # -----------------------------------------------------------------
            # Cross-field quote economics
            # -----------------------------------------------------------------

            crossfield_records.append(
                {
                    "quote_set": qset,
                    "bid_column": bid_col,
                    "ask_column": ask_col,
                    "mid_column": mid_col,
                    "time_column": config["time"],
                    "valid_bid_ask": int(valid.sum()),
                    "bid_gt_ask": int(bid_gt_ask.sum()),
                    "bid_gt_ask_rate": (
                        float(
                            bid_gt_ask.sum() /
                            valid.sum()
                        )
                        if valid.sum()
                        else np.nan
                    ),
                    "bid_eq_ask": int(bid_eq_ask.sum()),
                    "bid_lt_ask": int(bid_lt_ask.sum()),
                    "negative_spread": int(
                        negative_spread.sum()
                    ),
                    "zero_spread": int(
                        zero_spread.sum()
                    ),
                    "positive_spread": int(
                        positive_spread.sum()
                    ),
                    "midpoint_inconsistent": int(
                        (
                            valid
                            & mid.notna()
                            & ~midpoint_consistent
                        ).sum()
                    ),
                    "bid_negative": int(
                        bid_negative.sum()
                    ),
                    "ask_negative": int(
                        ask_negative.sum()
                    ),
                    "mid_negative": int(
                        mid_negative.sum()
                    ),
                }
            )

            # -----------------------------------------------------------------
            # Violation examples
            # -----------------------------------------------------------------

            violation_mask = bid_gt_ask

            if violation_mask.any():

                example = chunk.loc[
                    violation_mask,
                    [
                        "date",
                        "symbol",
                    ],
                ].copy()

                example["quote_set"] = qset
                example["bid"] = bid.loc[
                    violation_mask
                ].values
                example["ask"] = ask.loc[
                    violation_mask
                ].values
                example["mid"] = mid.loc[
                    violation_mask
                ].values
                example["spread"] = spread.loc[
                    violation_mask
                ].values
                example["expected_mid"] = midpoint_expected.loc[
                    violation_mask
                ].values
                example["midpoint_difference"] = (
                    midpoint_difference.loc[
                        violation_mask
                    ].values
                )

                example_records.append(
                    example.head(250)
                )

            # -----------------------------------------------------------------
            # Symbol-level diagnostics
            # -----------------------------------------------------------------

            tmp = pd.DataFrame(
                {
                    "symbol": chunk["symbol"],
                    "valid": valid,
                    "bid_gt_ask": bid_gt_ask,
                    "negative_spread": negative_spread,
                    "zero_spread": zero_spread,
                    "positive_spread": positive_spread,
                    "midpoint_inconsistent": (
                        valid
                        & mid.notna()
                        & ~midpoint_consistent
                    ),
                    "spread": spread,
                }
            )

            grouped = (
                tmp.groupby("symbol", dropna=False)
                .agg(
                    rows=("valid", "size"),
                    valid_bid_ask=("valid", "sum"),
                    bid_gt_ask=("bid_gt_ask", "sum"),
                    negative_spread=("negative_spread", "sum"),
                    zero_spread=("zero_spread", "sum"),
                    positive_spread=("positive_spread", "sum"),
                    midpoint_inconsistent=(
                        "midpoint_inconsistent",
                        "sum",
                    ),
                )
                .reset_index()
            )

            grouped["quote_set"] = qset

            grouped["bid_gt_ask_rate"] = (
                grouped["bid_gt_ask"]
                / grouped["valid_bid_ask"]
                .replace(0, np.nan)
            )

            symbol_records.append(grouped)

            # -----------------------------------------------------------------
            # Date-level diagnostics
            # -----------------------------------------------------------------

            tmp_date = pd.DataFrame(
                {
                    "date": chunk["date"],
                    "valid": valid,
                    "bid_gt_ask": bid_gt_ask,
                    "negative_spread": negative_spread,
                    "zero_spread": zero_spread,
                    "positive_spread": positive_spread,
                    "midpoint_inconsistent": (
                        valid
                        & mid.notna()
                        & ~midpoint_consistent
                    ),
                }
            )

            grouped_date = (
                tmp_date.groupby("date", dropna=False)
                .agg(
                    rows=("valid", "size"),
                    valid_bid_ask=("valid", "sum"),
                    bid_gt_ask=("bid_gt_ask", "sum"),
                    negative_spread=("negative_spread", "sum"),
                    zero_spread=("zero_spread", "sum"),
                    positive_spread=("positive_spread", "sum"),
                    midpoint_inconsistent=(
                        "midpoint_inconsistent",
                        "sum",
                    ),
                )
                .reset_index()
            )

            grouped_date["quote_set"] = qset

            grouped_date["bid_gt_ask_rate"] = (
                grouped_date["bid_gt_ask"]
                / grouped_date["valid_bid_ask"]
                .replace(0, np.nan)
            )

            date_records.append(grouped_date)

    # =========================================================================
    # AGGREGATE RESULTS
    # =========================================================================

    set_df = pd.DataFrame(set_records)

    symbol_df = (
        pd.concat(symbol_records, ignore_index=True)
        if symbol_records
        else pd.DataFrame()
    )

    date_df = (
        pd.concat(date_records, ignore_index=True)
        if date_records
        else pd.DataFrame()
    )

    spread_df = (
        pd.DataFrame(spread_records)
        if spread_records
        else pd.DataFrame()
    )

    crossfield_df = (
        pd.DataFrame(crossfield_records)
        if crossfield_records
        else pd.DataFrame()
    )

    # -------------------------------------------------------------------------
    # Aggregate symbol diagnostics across chunks
    # -------------------------------------------------------------------------

    if not symbol_df.empty:

        symbol_df = (
            symbol_df.groupby(
                ["quote_set", "symbol"],
                dropna=False,
            )
            .agg(
                rows=("rows", "sum"),
                valid_bid_ask=("valid_bid_ask", "sum"),
                bid_gt_ask=("bid_gt_ask", "sum"),
                negative_spread=("negative_spread", "sum"),
                zero_spread=("zero_spread", "sum"),
                positive_spread=("positive_spread", "sum"),
                midpoint_inconsistent=(
                    "midpoint_inconsistent",
                    "sum",
                ),
            )
            .reset_index()
        )

        symbol_df["bid_gt_ask_rate"] = (
            symbol_df["bid_gt_ask"]
            / symbol_df["valid_bid_ask"]
            .replace(0, np.nan)
        )

    # -------------------------------------------------------------------------
    # Aggregate date diagnostics across chunks
    # -------------------------------------------------------------------------

    if not date_df.empty:

        date_df = (
            date_df.groupby(
                ["quote_set", "date"],
                dropna=False,
            )
            .agg(
                rows=("rows", "sum"),
                valid_bid_ask=("valid_bid_ask", "sum"),
                bid_gt_ask=("bid_gt_ask", "sum"),
                negative_spread=("negative_spread", "sum"),
                zero_spread=("zero_spread", "sum"),
                positive_spread=("positive_spread", "sum"),
                midpoint_inconsistent=(
                    "midpoint_inconsistent",
                    "sum",
                ),
            )
            .reset_index()
        )

        date_df["bid_gt_ask_rate"] = (
            date_df["bid_gt_ask"]
            / date_df["valid_bid_ask"]
            .replace(0, np.nan)
        )

    # =========================================================================
    # GLOBAL SUMMARY
    # =========================================================================

    summary_records = []

    total_bid_gt_ask = 0
    total_valid_bid_ask = 0
    total_midpoint_inconsistent = 0
    total_negative_spread = 0
    total_zero_spread = 0
    total_positive_spread = 0

    for qset, stats in global_stats.items():

        total_bid_gt_ask += stats["bid_gt_ask"]
        total_valid_bid_ask += stats["non_null_bid_ask"]
        total_midpoint_inconsistent += (
            stats["midpoint_inconsistent"]
        )
        total_negative_spread += stats["negative_spread"]
        total_zero_spread += stats["zero_spread"]
        total_positive_spread += stats["positive_spread"]

        valid = stats["non_null_bid_ask"]

        summary_records.append(
            {
                "quote_set": qset,
                "rows": stats["rows"],
                "valid_bid_ask": valid,
                "bid_gt_ask": stats["bid_gt_ask"],
                "bid_gt_ask_rate": (
                    stats["bid_gt_ask"] / valid
                    if valid
                    else np.nan
                ),
                "bid_eq_ask": stats["bid_eq_ask"],
                "bid_lt_ask": stats["bid_lt_ask"],
                "negative_spread": stats["negative_spread"],
                "negative_spread_rate": (
                    stats["negative_spread"] / valid
                    if valid
                    else np.nan
                ),
                "zero_spread": stats["zero_spread"],
                "zero_spread_rate": (
                    stats["zero_spread"] / valid
                    if valid
                    else np.nan
                ),
                "positive_spread": stats["positive_spread"],
                "positive_spread_rate": (
                    stats["positive_spread"] / valid
                    if valid
                    else np.nan
                ),
                "midpoint_inconsistent": (
                    stats["midpoint_inconsistent"]
                ),
                "midpoint_inconsistent_rate": (
                    stats["midpoint_inconsistent"]
                    / valid
                    if valid
                    else np.nan
                ),
                "bid_negative": stats["bid_negative"],
                "ask_negative": stats["ask_negative"],
                "mid_negative": stats["mid_negative"],
            }
        )

    summary_df = pd.DataFrame(summary_records)

    # =========================================================================
    # GLOBAL CROSS-SET SUMMARY
    # =========================================================================

    overall_valid = total_valid_bid_ask

    overall_summary = pd.DataFrame(
        [
            {
                "metric": "total_rows",
                "value": total_rows,
            },
            {
                "metric": "total_valid_bid_ask_observations",
                "value": total_valid_bid_ask,
            },
            {
                "metric": "total_bid_greater_than_ask",
                "value": total_bid_gt_ask,
            },
            {
                "metric": "overall_bid_greater_than_ask_rate",
                "value": (
                    total_bid_gt_ask / overall_valid
                    if overall_valid
                    else np.nan
                ),
            },
            {
                "metric": "total_negative_spreads",
                "value": total_negative_spread,
            },
            {
                "metric": "negative_spread_rate",
                "value": (
                    total_negative_spread / overall_valid
                    if overall_valid
                    else np.nan
                ),
            },
            {
                "metric": "total_zero_spreads",
                "value": total_zero_spread,
            },
            {
                "metric": "zero_spread_rate",
                "value": (
                    total_zero_spread / overall_valid
                    if overall_valid
                    else np.nan
                ),
            },
            {
                "metric": "total_positive_spreads",
                "value": total_positive_spread,
            },
            {
                "metric": "positive_spread_rate",
                "value": (
                    total_positive_spread / overall_valid
                    if overall_valid
                    else np.nan
                ),
            },
            {
                "metric": "total_midpoint_inconsistent",
                "value": total_midpoint_inconsistent,
            },
            {
                "metric": "midpoint_inconsistent_rate",
                "value": (
                    total_midpoint_inconsistent
                    / overall_valid
                    if overall_valid
                    else np.nan
                ),
            },
            {
                "metric": "negative_quote_values",
                "value": sum(
                    x["bid_negative"]
                    + x["ask_negative"]
                    + x["mid_negative"]
                    for x in global_stats.values()
                ),
            },
        ]
    )

    # =========================================================================
    # SAVE OUTPUTS
    # =========================================================================

    summary_df.to_csv(
        OUTPUT_SET_SUMMARY,
        index=False,
    )

    overall_summary.to_csv(
        OUTPUT_SUMMARY,
        index=False,
    )

    if not symbol_df.empty:
        symbol_df.to_csv(
            OUTPUT_SYMBOL,
            index=False,
        )

    if not date_df.empty:
        date_df.to_csv(
            OUTPUT_DATE,
            index=False,
        )

    if example_records:

        examples_df = pd.concat(
            example_records,
            ignore_index=True,
        )

        examples_df.to_csv(
            OUTPUT_EXAMPLES,
            index=False,
        )

    else:

        pd.DataFrame(
            columns=[
                "date",
                "symbol",
                "quote_set",
                "bid",
                "ask",
                "mid",
                "spread",
                "expected_mid",
                "midpoint_difference",
            ]
        ).to_csv(
            OUTPUT_EXAMPLES,
            index=False,
        )

    if not spread_df.empty:

        # Each chunk generates one observation. Aggregate across chunks.
        spread_agg = (
            spread_df.groupby(
                "quote_set",
                dropna=False,
            )
            .agg(
                rows=("rows", "sum"),
                negative_spread_count=(
                    "negative_spread_count",
                    "sum",
                ),
                zero_spread_count=(
                    "zero_spread_count",
                    "sum",
                ),
                positive_spread_count=(
                    "positive_spread_count",
                    "sum",
                ),
                min_spread=("min_spread", "min"),
                max_spread=("max_spread", "max"),
            )
            .reset_index()
        )

        spread_agg["negative_spread_rate"] = (
            spread_agg["negative_spread_count"]
            / spread_agg["rows"]
        )

        spread_agg["zero_spread_rate"] = (
            spread_agg["zero_spread_count"]
            / spread_agg["rows"]
        )

        spread_agg["positive_spread_rate"] = (
            spread_agg["positive_spread_count"]
            / spread_agg["rows"]
        )

        spread_agg.to_csv(
            OUTPUT_SPREAD,
            index=False,
        )

    crossfield_df.to_csv(
        OUTPUT_CROSS_FIELD,
        index=False,
    )

    # =========================================================================
    # CONSOLE REPORT
    # =========================================================================

    print()
    print("=" * 80)
    print("QUOTE ECONOMIC VALIDATION SUMMARY")
    print("=" * 80)

    print(f"Input rows:                 {total_rows:,}")
    print(
        f"Valid bid/ask observations: {total_valid_bid_ask:,}"
    )
    print(
        f"Bid > ask observations:     {total_bid_gt_ask:,}"
    )

    if total_valid_bid_ask:
        print(
            "Overall bid > ask rate:     "
            f"{100 * total_bid_gt_ask / total_valid_bid_ask:.6f}%"
        )

    print()
    print("QUOTE-SET RESULTS")
    print("-" * 80)

    for row in summary_records:

        print(
            f"{row['quote_set']:>6} | "
            f"bid>ask={row['bid_gt_ask']:>7,} | "
            f"rate={100 * row['bid_gt_ask_rate']:.6f}% | "
            f"negative_spread={row['negative_spread']:>7,} | "
            f"midpoint_inconsistent="
            f"{row['midpoint_inconsistent']:>7,}"
        )

    print()
    print("=" * 80)
    print("ECONOMIC INTERPRETATION FLAGS")
    print("=" * 80)

    print(
        "1. Bid > ask observations are retained for semantic/economic review."
    )
    print(
        "2. Negative spreads are equivalent to bid > ask and are not "
        "automatically treated as data errors."
    )
    print(
        "3. Stored midpoint consistency is evaluated independently."
    )
    print(
        "4. Negative quote prices are flagged separately."
    )
    print(
        "5. Quote-set, symbol, and date concentrations are reported."
    )
    print(
        "6. No quote values are corrected."
    )
    print(
        "7. No observations are removed."
    )
    print(
        "8. No imputation is performed."
    )

    print()
    print("=" * 80)
    print("OUTPUTS")
    print("=" * 80)

    print(f"Summary:")
    print(f"  {OUTPUT_SUMMARY}")

    print(f"Quote-set summary:")
    print(f"  {OUTPUT_SET_SUMMARY}")

    print(f"Symbol summary:")
    print(f"  {OUTPUT_SYMBOL}")

    print(f"Date summary:")
    print(f"  {OUTPUT_DATE}")

    print(f"Violation examples:")
    print(f"  {OUTPUT_EXAMPLES}")

    print(f"Spread diagnostics:")
    print(f"  {OUTPUT_SPREAD}")

    print(f"Cross-field diagnostics:")
    print(f"  {OUTPUT_CROSS_FIELD}")

    print()
    print("=" * 80)
    print("STATUS")
    print("=" * 80)
    print(
        "PASS — quote economic validation completed."
    )
    print(
        "REVIEW — bid/ask ordering and negative-spread observations "
        "remain subject to source-semantic interpretation."
    )
    print()
    print("IMPORTANT:")
    print("No observations were removed.")
    print("No values were modified.")
    print("No quote values were corrected.")
    print("No imputation was performed.")
    print("No automatic economic validity rule was applied.")


if __name__ == "__main__":
    main()