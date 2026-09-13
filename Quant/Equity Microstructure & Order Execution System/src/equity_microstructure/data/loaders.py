from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd


def load_csv_filtered(
    path: Path,
    date_column: str,
    symbol_column: str,
    symbols: Iterable[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    chunksize: int = 100_000,
) -> pd.DataFrame:
    """
    Load selected rows from a large CSV without reading
    the entire file into memory.

    Dates are interpreted as DD/MM/YYYY.
    """

    symbols_set = None

    if symbols is not None:
        symbols_set = {
            str(symbol).strip().upper()
            for symbol in symbols
        }

    start = (
        pd.Timestamp(start_date)
        if start_date is not None
        else None
    )

    end = (
        pd.Timestamp(end_date)
        if end_date is not None
        else None
    )

    pieces = []

    for chunk in pd.read_csv(
        path,
        chunksize=chunksize,
        low_memory=False,
    ):
        chunk[date_column] = pd.to_datetime(
            chunk[date_column],
            dayfirst=True,
            errors="coerce",
        )

        chunk[symbol_column] = (
            chunk[symbol_column]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        if symbols_set is not None:
            chunk = chunk[
                chunk[symbol_column].isin(symbols_set)
            ]

        if start is not None:
            chunk = chunk[
                chunk[date_column] >= start
            ]

        if end is not None:
            chunk = chunk[
                chunk[date_column] <= end
            ]

        if not chunk.empty:
            pieces.append(chunk)

    if not pieces:
        return pd.DataFrame()

    return pd.concat(
        pieces,
        ignore_index=True,
    )

def load_taq(
    path: Path,
    symbols: Iterable[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    chunksize: int = 100_000,
) -> pd.DataFrame:

    return load_csv_filtered(
        path=path,
        date_column="date",
        symbol_column="symbol",
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        chunksize=chunksize,
    )


def load_taqm(
    path: Path,
    symbols: Iterable[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    chunksize: int = 100_000,
) -> pd.DataFrame:

    return load_csv_filtered(
        path=path,
        date_column="DATE",
        symbol_column="symbol",
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        chunksize=chunksize,
    )