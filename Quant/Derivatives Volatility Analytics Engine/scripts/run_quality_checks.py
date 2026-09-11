from pathlib import Path
import sys
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.quality_checks import (
    calculate_quote_metrics,
    check_basic_structure,
    summarize_missingness,
)

DATA_PATH = (
    PROJECT_ROOT
    / "src"
    / "data"
    / "raw"
    / "SPY"
    / "2010"
    / "spy_eod_201001.txt"
)


def main() -> None:
    df = pd.read_csv(DATA_PATH)

    df.columns = (
        df.columns
        .str.strip()
        .str.replace("[", "", regex=False)
        .str.replace("]", "", regex=False)
        .str.lower()
    )

    datetime_columns = [
        "quote_readtime",
        "quote_date",
        "expire_date",
    ]

    for column in datetime_columns:
        df[column] = pd.to_datetime(df[column], errors="coerce")

    numeric_columns = [
        "quote_unixtime",
        "quote_time_hours",
        "underlying_last",
        "expire_unix",
        "dte",
        "c_delta",
        "c_gamma",
        "c_vega",
        "c_theta",
        "c_rho",
        "c_iv",
        "c_volume",
        "c_last",
        "c_bid",
        "c_ask",
        "strike",
        "p_bid",
        "p_ask",
        "p_last",
        "p_delta",
        "p_gamma",
        "p_vega",
        "p_theta",
        "p_rho",
        "p_iv",
        "p_volume",
        "strike_distance",
        "strike_distance_pct",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    summary = check_basic_structure(df)

    print("=" * 70)
    print("BASIC DATA QUALITY SUMMARY")
    print("=" * 70)

    print(f"Rows:                    {summary.rows:,}")
    print(f"Columns:                 {summary.columns}")
    print(f"Duplicate rows:          {summary.duplicate_rows:,}")
    print(
        "Duplicate contract keys: "
        f"{summary.duplicate_contract_keys:,}"
    )

    print()
    print("QUOTE INTEGRITY")
    print("-" * 70)

    print(
        f"Crossed call quotes:     "
        f"{summary.crossed_call_quotes:,}"
    )

    print(
        f"Crossed put quotes:      "
        f"{summary.crossed_put_quotes:,}"
    )

    print(
        f"Negative call prices:    "
        f"{summary.negative_call_prices:,}"
    )

    print(
        f"Negative put prices:     "
        f"{summary.negative_put_prices:,}"
    )

    print()
    print("ZERO BID / ASK")
    print("-" * 70)

    print(
        f"Zero call bids:           "
        f"{summary.zero_call_bids:,}"
    )

    print(
        f"Zero call asks:           "
        f"{summary.zero_call_asks:,}"
    )

    print(
        f"Zero put bids:            "
        f"{summary.zero_put_bids:,}"
    )

    print(
        f"Zero put asks:            "
        f"{summary.zero_put_asks:,}"
    )

    print()
    print("DTE")
    print("-" * 70)

    print(f"DTE = 0: {summary.dte_zero:,}")
    print(f"DTE < 0: {summary.dte_negative:,}")

    df = calculate_quote_metrics(df)

    print()
    print("=" * 70)
    print("QUOTE METRICS")
    print("=" * 70)

    print(
        df[
            [
                "strike",
                "dte",
                "c_bid",
                "c_ask",
                "c_mid",
                "c_spread",
                "c_relative_spread",
                "p_bid",
                "p_ask",
                "p_mid",
                "p_spread",
                "p_relative_spread",
            ]
        ].head(10)
    )

    print()
    print("=" * 70)
    print("MISSINGNESS")
    print("=" * 70)
    print(summarize_missingness(df))

if __name__ == "__main__":
    main()