from __future__ import annotations

from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CRSP_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "crsp"
    / "CRSP_Daily Stock File.csv"
)


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

USECOLS = [
    "PERMNO",
    "PERMCO",
    "Ticker",
    "YYYYMMDD",
    "DlyCalDt",
    "DlyDelFlg",
    "DlyPrc",
    "DlyRet",
    "DlyRetx",
    "DlyRetI",
    "DlyFacPrc",
    "DlyVol",
    "DlyClose",
    "DlyLow",
    "DlyHigh",
    "DlyBid",
    "DlyAsk",
    "DlyOpen",
    "DlyNumTrd",
    "ShrStartDt",
    "ShrEndDt",
    "ShrOut",
    "DisExDt",
    "DisDivAmt",
    "DisFacPr",
    "DisFacShr",
]

CHUNK_SIZE = 100_000


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:
    if not CRSP_PATH.exists():
        raise FileNotFoundError(
            f"CRSP file not found: {CRSP_PATH}"
        )

    duplicate_chunks: list[pd.DataFrame] = []

    # -------------------------------------------------------------
    # Read only the columns relevant to duplicate investigation.
    # -------------------------------------------------------------

    for chunk in pd.read_csv(
        CRSP_PATH,
        usecols=USECOLS,
        chunksize=CHUNK_SIZE,
    ):
        chunk["date"] = pd.to_datetime(
            chunk["DlyCalDt"],
            dayfirst=True,
            errors="coerce",
        )

        duplicate_mask = chunk.duplicated(
            subset=["PERMNO", "date"],
            keep=False,
        )

        duplicates = chunk.loc[
            duplicate_mask
        ].copy()

        if not duplicates.empty:
            duplicate_chunks.append(
                duplicates
            )

    if not duplicate_chunks:
        print("No duplicate PERMNO/date observations found.")
        return

    duplicates = pd.concat(
        duplicate_chunks,
        ignore_index=True,
    )

    duplicates = duplicates.sort_values(
        ["PERMNO", "date"]
    )

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------

    print("=" * 100)
    print("CRSP DUPLICATE PERMNO/DATE ANALYSIS")
    print("=" * 100)

    print(f"\nDuplicate rows: {len(duplicates):,}")

    duplicate_groups = (
        duplicates
        .groupby(["PERMNO", "date"])
        .size()
        .reset_index(name="rows")
    )

    print(
        f"Duplicate PERMNO/date groups: "
        f"{len(duplicate_groups):,}"
    )

    print("\nDuplicate group sizes:")
    print(
        duplicate_groups["rows"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    # -------------------------------------------------------------
    # Print the actual duplicate observations.
    # -------------------------------------------------------------

    print("\n" + "-" * 100)
    print("DUPLICATE OBSERVATIONS")
    print("-" * 100)

    display_columns = [
        "PERMNO",
        "PERMCO",
        "Ticker",
        "date",
        "YYYYMMDD",
        "DlyDelFlg",
        "DlyPrc",
        "DlyRet",
        "DlyRetx",
        "DlyRetI",
        "DlyFacPrc",
        "DlyVol",
        "DlyClose",
        "DlyLow",
        "DlyHigh",
        "DlyBid",
        "DlyAsk",
        "DlyOpen",
        "DlyNumTrd",
        "ShrStartDt",
        "ShrEndDt",
        "ShrOut",
        "DisExDt",
        "DisDivAmt",
        "DisFacPr",
        "DisFacShr",
    ]

    print(
        duplicates[display_columns].to_string(
            index=False
        )
    )

    # -------------------------------------------------------------
    # Determine whether duplicate rows are exact duplicates
    # after excluding the derived date column.
    # -------------------------------------------------------------

    comparison_columns = [
        column
        for column in duplicates.columns
        if column != "date"
    ]

    exact_duplicate_groups = (
        duplicates
        .groupby(comparison_columns, dropna=False)
        .size()
        .reset_index(name="count")
    )

    exact_duplicate_rows = int(
        exact_duplicate_groups["count"]
        .where(
            exact_duplicate_groups["count"] > 1,
            0,
        )
        .sum()
    )

    print("\n" + "-" * 100)
    print("EXACT DUPLICATE ANALYSIS")
    print("-" * 100)

    print(
        f"Rows belonging to exact duplicate groups: "
        f"{exact_duplicate_rows:,}"
    )

    print(
        f"Rows requiring further investigation: "
        f"{len(duplicates) - exact_duplicate_rows:,}"
    )

    # -------------------------------------------------------------
    # Show differences within each duplicate key.
    # -------------------------------------------------------------

    print("\n" + "-" * 100)
    print("FIELD-LEVEL DIFFERENCES WITHIN DUPLICATE KEYS")
    print("-" * 100)

    for (permno, date), group in duplicates.groupby(
        ["PERMNO", "date"],
        sort=True,
    ):
        varying_columns = []

        for column in comparison_columns:
            if group[column].nunique(
                dropna=False
            ) > 1:
                varying_columns.append(column)

        print(
            f"\nPERMNO={permno}, "
            f"DATE={date.date()}, "
            f"ROWS={len(group)}"
        )

        if varying_columns:
            print(
                "Fields that differ:"
            )
            print(
                "  "
                + ", ".join(varying_columns)
            )
        else:
            print(
                "All fields are identical."
            )

    print("\n" + "=" * 100)
    print("END OF DUPLICATE ANALYSIS")
    print("=" * 100)


if __name__ == "__main__":
    main()