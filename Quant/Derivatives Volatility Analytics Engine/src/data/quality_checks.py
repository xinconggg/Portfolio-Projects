from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd


@dataclass
class QualitySummary:
    """Container for high-level dataset quality statistics."""
    rows: int
    columns: int
    duplicate_rows: int
    duplicate_contract_keys: int
    crossed_call_quotes: int
    crossed_put_quotes: int
    negative_call_prices: int
    negative_put_prices: int
    zero_call_bids: int
    zero_put_bids: int
    zero_call_asks: int
    zero_put_asks: int
    dte_zero: int
    dte_negative: int


def check_basic_structure(df: pd.DataFrame) -> QualitySummary:
    """
    Run basic structural and quote-integrity checks.

    Parameters:
    - df: Normalized options DataFrame.

    Returns:
    - QualitySummary: Summary of key data-quality diagnostics.
    """
    required_columns = {
        "quote_unixtime",
        "quote_date",
        "expire_date",
        "dte",
        "strike",
        "c_bid",
        "c_ask",
        "c_last",
        "p_bid",
        "p_ask",
        "p_last",
    }
    missing_columns = required_columns.difference(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    duplicate_rows = int(df.duplicated().sum())

    contract_key = df[
        ["quote_unixtime", "expire_date", "strike"]
    ].duplicated()

    duplicate_contract_keys = int(contract_key.sum())

    crossed_call_quotes = int(
        ((df["c_bid"] > df["c_ask"]) &
         df["c_bid"].notna() &
         df["c_ask"].notna()).sum()
    )

    crossed_put_quotes = int(
        ((df["p_bid"] > df["p_ask"]) &
         df["p_bid"].notna() &
         df["p_ask"].notna()).sum()
    )

    negative_call_prices = int(
        (
            (
                (df["c_bid"] < 0)
                | (df["c_ask"] < 0)
                | (df["c_last"] < 0)
            )
        ).sum()
    )

    negative_put_prices = int(
        (
            (
                (df["p_bid"] < 0)
                | (df["p_ask"] < 0)
                | (df["p_last"] < 0)
            )
        ).sum()
    )

    zero_call_bids = int((df["c_bid"] == 0).sum())
    zero_put_bids = int((df["p_bid"] == 0).sum())

    zero_call_asks = int((df["c_ask"] == 0).sum())
    zero_put_asks = int((df["p_ask"] == 0).sum())

    dte_zero = int((df["dte"] == 0).sum())
    dte_negative = int((df["dte"] < 0).sum())

    return QualitySummary(
        rows=len(df),
        columns=len(df.columns),
        duplicate_rows=duplicate_rows,
        duplicate_contract_keys=duplicate_contract_keys,
        crossed_call_quotes=crossed_call_quotes,
        crossed_put_quotes=crossed_put_quotes,
        negative_call_prices=negative_call_prices,
        negative_put_prices=negative_put_prices,
        zero_call_bids=zero_call_bids,
        zero_put_bids=zero_put_bids,
        zero_call_asks=zero_call_asks,
        zero_put_asks=zero_put_asks,
        dte_zero=dte_zero,
        dte_negative=dte_negative,
    )


def calculate_quote_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add basic bid/ask-derived quote metrics.
    The original DataFrame is not modified.

    Returns:
    - pd.DataFrame: Copy of the input DataFrame with quote metrics added.
    """
    result = df.copy()

    result["c_mid"] = (result["c_bid"] + result["c_ask"]) / 2.0
    result["p_mid"] = (result["p_bid"] + result["p_ask"]) / 2.0

    result["c_spread"] = result["c_ask"] - result["c_bid"]
    result["p_spread"] = result["p_ask"] - result["p_bid"]

    result["c_relative_spread"] = (
        result["c_spread"] / result["c_mid"].replace(0, np.nan)
    )

    result["p_relative_spread"] = (
        result["p_spread"] / result["p_mid"].replace(0, np.nan)
    )
    return result


def summarize_missingness(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return missing-value statistics for every column.
    """
    summary = pd.DataFrame(
        {
            "missing_count": df.isna().sum(),
            "missing_pct": df.isna().mean() * 100,
        }
    )

    return summary.sort_values(
        "missing_count",
        ascending=False,
    )