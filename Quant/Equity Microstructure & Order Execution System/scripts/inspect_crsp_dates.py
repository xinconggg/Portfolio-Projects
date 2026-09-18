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

DATE_COLUMNS = [
    "YYYYMMDD",
    "DlyCalDt",
]

CHUNK_SIZE = 250_000


def main() -> None:
    if not CRSP_DAILY_PATH.exists():
        raise FileNotFoundError(
            f"CRSP daily file not found: {CRSP_DAILY_PATH}"
        )

    total_rows = 0

    missing_yyyymmdd = 0
    invalid_yyyymmdd = 0

    missing_dlycaldt = 0
    invalid_dlycaldt = 0

    date_disagreements = 0

    earliest_date = None
    latest_date = None

    unique_permnos: set[int] = set()

    observed_date_counts: dict[pd.Timestamp, int] = {}

    for chunk in pd.read_csv(
        CRSP_DAILY_PATH,
        usecols=["PERMNO", *DATE_COLUMNS],
        chunksize=CHUNK_SIZE,
    ):
        total_rows += len(chunk)

        unique_permnos.update(
            chunk["PERMNO"]
            .dropna()
            .astype(int)
            .tolist()
        )

        # ---------------------------------------------------------
        # YYYYMMDD validation
        # ---------------------------------------------------------

        yyyymmdd = chunk["YYYYMMDD"]

        missing_yyyymmdd += int(
            yyyymmdd.isna().sum()
        )

        yyyymmdd_str = yyyymmdd.astype("string")

        parsed_yyyymmdd = pd.to_datetime(
            yyyymmdd_str,
            format="%Y%m%d",
            errors="coerce",
        )

        invalid_yyyymmdd += int(
            (
                yyyymmdd.notna()
                & parsed_yyyymmdd.isna()
            ).sum()
        )

        # ---------------------------------------------------------
        # DlyCalDt validation
        # ---------------------------------------------------------

        dlycaldt = chunk["DlyCalDt"]

        missing_dlycaldt += int(
            dlycaldt.isna().sum()
        )

        parsed_dlycaldt = pd.to_datetime(
            dlycaldt,
            dayfirst=True,
            errors="coerce",
        )

        invalid_dlycaldt += int(
            (
                dlycaldt.notna()
                & parsed_dlycaldt.isna()
            ).sum()
        )

        # ---------------------------------------------------------
        # Compare the two representations
        # ---------------------------------------------------------

        valid_both = (
            parsed_yyyymmdd.notna()
            & parsed_dlycaldt.notna()
        )

        date_disagreements += int(
            (
                valid_both
                & (
                    parsed_yyyymmdd
                    != parsed_dlycaldt
                )
            ).sum()
        )

        # ---------------------------------------------------------
        # Track date range
        # ---------------------------------------------------------

        valid_dates = parsed_dlycaldt.dropna()

        if not valid_dates.empty:
            chunk_min = valid_dates.min()
            chunk_max = valid_dates.max()

            if (
                earliest_date is None
                or chunk_min < earliest_date
            ):
                earliest_date = chunk_min

            if (
                latest_date is None
                or chunk_max > latest_date
            ):
                latest_date = chunk_max

            counts = valid_dates.value_counts()

            for date, count in counts.items():
                observed_date_counts[date] = (
                    observed_date_counts.get(date, 0)
                    + int(count)
                )

    print("=" * 100)
    print("CRSP DAILY STOCK FILE — DATE SEMANTICS")
    print("=" * 100)

    print(f"\nFile: {CRSP_DAILY_PATH}")
    print(f"Rows scanned: {total_rows:,}")
    print(f"Unique PERMNOs: {len(unique_permnos):,}")

    print("\n" + "-" * 100)
    print("YYYYMMDD")
    print("-" * 100)

    print(f"Missing: {missing_yyyymmdd:,}")
    print(f"Invalid: {invalid_yyyymmdd:,}")

    print("\n" + "-" * 100)
    print("DlyCalDt")
    print("-" * 100)

    print(f"Missing: {missing_dlycaldt:,}")
    print(f"Invalid: {invalid_dlycaldt:,}")

    print("\n" + "-" * 100)
    print("DATE AGREEMENT")
    print("-" * 100)

    print(
        f"Disagreements between YYYYMMDD and DlyCalDt: "
        f"{date_disagreements:,}"
    )

    print("\n" + "-" * 100)
    print("DATE RANGE")
    print("-" * 100)

    print(f"Earliest date: {earliest_date}")
    print(f"Latest date:   {latest_date}")

    print("\n" + "-" * 100)
    print("DATE FREQUENCY")
    print("-" * 100)

    unique_dates = len(observed_date_counts)

    print(f"Unique calendar dates: {unique_dates:,}")

    if earliest_date is not None and latest_date is not None:
        expected_calendar_days = (
            latest_date - earliest_date
        ).days + 1

        print(
            "Calendar span: "
            f"{expected_calendar_days:,} days"
        )

    if observed_date_counts:
        print(
            "\nFirst 10 observed dates and row counts:"
        )

        for date, count in sorted(
            observed_date_counts.items()
        )[:10]:
            print(
                f"{date.date()} : {count:,}"
            )

        print(
            "\nLast 10 observed dates and row counts:"
        )

        for date, count in sorted(
            observed_date_counts.items()
        )[-10:]:
            print(
                f"{date.date()} : {count:,}"
            )


if __name__ == "__main__":
    main()