"""Lightweight readers for inspecting large research files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def read_sample(
    path: Path,
    nrows: int = 10,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Read a small sample from the beginning of a file."""

    suffix = path.name.lower()

    if suffix.endswith(".csv.gz"):
        return pd.read_csv(
            path,
            compression="gzip",
            nrows=nrows,
            usecols=columns,
        )

    if suffix.endswith(".csv"):
        return pd.read_csv(
            path,
            nrows=nrows,
            usecols=columns,
        )

    if suffix.endswith(".tsv"):
        return pd.read_csv(
            path,
            sep="\t",
            nrows=nrows,
            usecols=columns,
        )

    if suffix.endswith(".txt"):
        return pd.read_csv(
            path,
            nrows=nrows,
            usecols=columns,
        )

    if suffix.endswith(".parquet"):
        return pd.read_parquet(
            path,
            columns=columns,
        ).head(nrows)

    raise ValueError(
        f"Unsupported file format for sample reading: {path}"
    )