from __future__ import annotations

import pandas as pd


def validate_required_columns(
    df: pd.DataFrame,
    required_columns: list[str],
) -> list[str]:
    """
    Return required columns that are missing.
    """
    return [
        column
        for column in required_columns
        if column not in df.columns
    ]


def validate_date_column(
    df: pd.DataFrame,
    column: str,
) -> dict:
    """
    Validate a normalized datetime column.
    """
    if column not in df.columns:
        return {
            "exists": False,
            "missing": None,
            "min": None,
            "max": None,
        }

    series = df[column]

    return {
        "exists": True,
        "missing": int(series.isna().sum()),
        "min": series.min(),
        "max": series.max(),
    }


def validate_symbol_column(
    df: pd.DataFrame,
    column: str = "symbol",
) -> dict:
    """
    Basic symbol-column diagnostics.
    """
    if column not in df.columns:
        return {
            "exists": False,
            "missing": None,
            "unique": None,
        }

    series = df[column]

    return {
        "exists": True,
        "missing": int(series.isna().sum()),
        "unique": int(series.nunique(dropna=True)),
    }


def validate_dataframe(
    df: pd.DataFrame,
    required_columns: list[str],
    date_column: str,
    symbol_column: str = "symbol",
) -> dict:
    """
    Run basic structural validation on a dataframe.
    """
    missing_columns = validate_required_columns(
        df,
        required_columns,
    )

    return {
        "rows": len(df),
        "columns": len(df.columns),
        "missing_required_columns": missing_columns,
        "date": validate_date_column(
            df,
            date_column,
        ),
        "symbol": validate_symbol_column(
            df,
            symbol_column,
        ),
    }