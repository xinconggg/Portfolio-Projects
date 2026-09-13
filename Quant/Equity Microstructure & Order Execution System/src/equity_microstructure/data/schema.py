from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def inspect_schema(
    path: Path,
    *,
    sample_rows: int = 1000,
) -> dict:
    """
    Generate a lightweight schema description.

    The complete dataset is never loaded.
    """

    path = Path(path)

    df = pd.read_csv(
        path,
        nrows=sample_rows,
    )

    columns = []

    for column in df.columns:
        series = df[column]

        columns.append(
            {
                "name": column,
                "dtype": str(series.dtype),
                "non_null_sample": int(series.notna().sum()),
                "null_sample": int(series.isna().sum()),
                "example_values": (
                    series.dropna()
                    .head(5)
                    .tolist()
                ),
            }
        )

    return {
        "file": str(path),
        "sample_rows": len(df),
        "n_columns": len(df.columns),
        "columns": columns,
    }


def save_schema(
    schema: dict,
    output_path: Path,
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            schema,
            f,
            indent=2,
            default=str,
        )