from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize dataframe column names by stripping surrounding whitespace.

    The original semantic names are otherwise preserved.
    """
    df = df.copy()

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
    )

    return df


def normalize_symbol_column(
    df: pd.DataFrame,
    column: str = "symbol",
) -> pd.DataFrame:
    """
    Normalize a stock-symbol column.

    Values are converted to strings and surrounding whitespace is removed.
    Missing values remain missing.
    """
    df = df.copy()

    if column not in df.columns:
        return df

    df[column] = (
        df[column]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return df


def normalize_date_column(
    df: pd.DataFrame,
    column: str,
) -> pd.DataFrame:
    """
    Convert a DD/MM/YYYY date column to pandas datetime.

    Invalid dates are converted to NaT.
    """
    df = df.copy()

    if column not in df.columns:
        return df

    df[column] = pd.to_datetime(
        df[column],
        dayfirst=True,
        errors="coerce",
    )

    return df


def convert_numeric_columns(
    df: pd.DataFrame,
    columns: Iterable[str],
) -> pd.DataFrame:
    """
    Convert explicitly specified columns to numeric.

    Invalid values become NaN.
    """
    df = df.copy()

    for column in columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    return df


def normalize_taq(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply structural normalization to a TAQ dataframe.
    """
    df = normalize_column_names(df)

    df = normalize_date_column(
        df,
        "date",
    )

    df = normalize_symbol_column(
        df,
        "symbol",
    )

    return df


def normalize_taqm(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply structural normalization to a TAQM dataframe.
    """
    df = normalize_column_names(df)

    df = normalize_date_column(
        df,
        "DATE",
    )

    df = normalize_symbol_column(
        df,
        "symbol",
    )

    df = normalize_symbol_column(
        df,
        "SYM_ROOT",
    )

    df = normalize_symbol_column(
        df,
        "SYM_SUFFIX",
    )

    return df