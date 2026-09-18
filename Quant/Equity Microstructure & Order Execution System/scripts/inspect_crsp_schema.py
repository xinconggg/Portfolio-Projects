from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CRSP_DAILY_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "crsp"
    / "CRSP_Daily Stock File.csv"
)


def main() -> None:
    if not CRSP_DAILY_PATH.exists():
        raise FileNotFoundError(
            f"CRSP daily file not found: {CRSP_DAILY_PATH}"
        )

    # Read only a small sample.
    df = pd.read_csv(
        CRSP_DAILY_PATH,
        nrows=1000,
    )

    print("=" * 100)
    print("CRSP DAILY STOCK FILE — SCHEMA INSPECTION")
    print("=" * 100)

    print(f"\nFile: {CRSP_DAILY_PATH}")
    print(f"Sample rows loaded: {len(df):,}")
    print(f"Columns: {len(df.columns)}")

    print("\n" + "-" * 100)
    print("COLUMNS")
    print("-" * 100)

    for i, column in enumerate(df.columns):
        print(f"{i:>2}: {column}")

    print("\n" + "-" * 100)
    print("PANDAS DTYPES")
    print("-" * 100)

    print(df.dtypes.to_string())

    print("\n" + "-" * 100)
    print("NON-MISSING COUNTS")
    print("-" * 100)

    non_missing = df.notna().sum()

    for column in df.columns:
        print(
            f"{column:<20} "
            f"{non_missing[column]:>6,} / {len(df):,}"
        )

    print("\n" + "-" * 100)
    print("UNIQUE COUNTS IN SAMPLE")
    print("-" * 100)

    for column in df.columns:
        print(
            f"{column:<20} "
            f"{df[column].nunique(dropna=True):>8,}"
        )

    print("\n" + "-" * 100)
    print("FIRST 5 ROWS")
    print("-" * 100)

    print(
        df.head(5).to_string(
            index=False,
        )
    )


if __name__ == "__main__":
    main()