"""Utilities for reading research data samples."""

from pathlib import Path

import pandas as pd


def read_sample(
    path: Path,
    nrows: int = 5,
) -> pd.DataFrame:
    """Read a small sample from a supported data file."""

    if not path.exists():
        raise FileNotFoundError(
            f"Data file not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Data path is not a file: {path}"
        )

    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(
            path,
            nrows=nrows,
        )

    raise ValueError(
        f"Unsupported sample file format: {suffix}"
    )