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
]

CHUNK_SIZE = 100_000


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def normalize_date(series: pd.Series) -> pd.Series:
    """
    Parse CRSP DlyCalDt using the observed day/month/year convention.
    """
    return pd.to_datetime(
        series,
        dayfirst=True,
        errors="coerce",
    )


# ---------------------------------------------------------------------
# Main validation
# ---------------------------------------------------------------------

def main() -> None:
    if not CRSP_PATH.exists():
        raise FileNotFoundError(
            f"CRSP file not found: {CRSP_PATH}"
        )

    total_rows = 0

    missing_permno = 0
    invalid_permno = 0

    unique_permnos: set[int] = set()

    # Track PERMCO relationships.
    permno_permco_pairs: set[tuple[int, int]] = set()

    # Track PERMNO -> observed tickers.
    permno_tickers: dict[int, set[str]] = {}

    # Track PERMNO/date keys.
    duplicate_key_count = 0
    seen_keys: set[tuple[int, pd.Timestamp]] = set()

    # Track malformed dates for the identifier key.
    invalid_dates = 0

    # -----------------------------------------------------------------
    # Read the file in chunks.
    # -----------------------------------------------------------------

    for chunk in pd.read_csv(
        CRSP_PATH,
        usecols=USECOLS,
        chunksize=CHUNK_SIZE,
    ):
        total_rows += len(chunk)

        # -------------------------------------------------------------
        # PERMNO validation
        # -------------------------------------------------------------

        missing_mask = chunk["PERMNO"].isna()
        missing_permno += int(missing_mask.sum())

        valid_permno = chunk.loc[
            ~missing_mask,
            "PERMNO",
        ]

        # PERMNO should be a positive integer identifier.
        invalid_mask = valid_permno <= 0
        invalid_permno += int(invalid_mask.sum())

        unique_permnos.update(
            valid_permno.astype("int64").tolist()
        )

        # -------------------------------------------------------------
        # Date parsing
        # -------------------------------------------------------------

        chunk["date"] = normalize_date(
            chunk["DlyCalDt"]
        )

        invalid_dates += int(
            chunk["date"].isna().sum()
        )

        # -------------------------------------------------------------
        # PERMNO / PERMCO relationship
        # -------------------------------------------------------------

        relationship = chunk.loc[
            chunk["PERMNO"].notna()
            & chunk["PERMCO"].notna(),
            ["PERMNO", "PERMCO"],
        ]

        for permno, permco in relationship.itertuples(
            index=False,
            name=None,
        ):
            permno_permco_pairs.add(
                (int(permno), int(permco))
            )

        # -------------------------------------------------------------
        # PERMNO / Ticker relationship
        # -------------------------------------------------------------

        ticker_data = chunk.loc[
            chunk["PERMNO"].notna(),
            ["PERMNO", "Ticker"],
        ]

        for permno, ticker in ticker_data.itertuples(
            index=False,
            name=None,
        ):
            permno = int(permno)

            ticker = (
                str(ticker).strip()
                if pd.notna(ticker)
                else "<MISSING>"
            )

            permno_tickers.setdefault(
                permno,
                set(),
            ).add(ticker)

        # -------------------------------------------------------------
        # PERMNO + date uniqueness
        # -------------------------------------------------------------

        key_data = chunk.loc[
            chunk["PERMNO"].notna()
            & chunk["date"].notna(),
            ["PERMNO", "date"],
        ]

        for permno, date in key_data.itertuples(
            index=False,
            name=None,
        ):
            key = (int(permno), date)

            if key in seen_keys:
                duplicate_key_count += 1
            else:
                seen_keys.add(key)

    # -----------------------------------------------------------------
    # Results
    # -----------------------------------------------------------------

    print("=" * 80)
    print("CRSP SECURITY IDENTIFIER VALIDATION")
    print("=" * 80)

    print(f"\nFile: {CRSP_PATH}")
    print(f"Rows scanned: {total_rows:,}")

    print("\n" + "-" * 80)
    print("PERMNO")
    print("-" * 80)

    print(f"Missing PERMNO: {missing_permno:,}")
    print(f"Invalid PERMNO (<= 0): {invalid_permno:,}")
    print(f"Unique valid PERMNOs: {len(unique_permnos):,}")

    print("\n" + "-" * 80)
    print("DATE")
    print("-" * 80)

    print(f"Invalid DlyCalDt values: {invalid_dates:,}")

    print("\n" + "-" * 80)
    print("PERMNO + DATE KEY")
    print("-" * 80)

    print(
        f"Unique PERMNO/date keys: {len(seen_keys):,}"
    )

    print(
        f"Duplicate PERMNO/date observations: "
        f"{duplicate_key_count:,}"
    )

    if total_rows > 0:
        duplicate_pct = (
            duplicate_key_count / total_rows * 100
        )
    else:
        duplicate_pct = 0.0

    print(
        f"Duplicate percentage of rows: "
        f"{duplicate_pct:.6f}%"
    )

    print("\n" + "-" * 80)
    print("PERMNO / PERMCO RELATIONSHIP")
    print("-" * 80)

    print(
        f"Observed PERMNO/PERMCO pairs: "
        f"{len(permno_permco_pairs):,}"
    )

    # Find PERMNOs associated with multiple PERMCOs.
    permno_to_permcos: dict[int, set[int]] = {}

    for permno, permco in permno_permco_pairs:
        permno_to_permcos.setdefault(
            permno,
            set(),
        ).add(permco)

    multi_permco = {
        permno: permcos
        for permno, permcos
        in permno_to_permcos.items()
        if len(permcos) > 1
    }

    print(
        f"PERMNOs associated with >1 PERMCO: "
        f"{len(multi_permco):,}"
    )

    print("\n" + "-" * 80)
    print("PERMNO / TICKER RELATIONSHIP")
    print("-" * 80)

    ticker_change_counts = {
        permno: tickers
        for permno, tickers in permno_tickers.items()
        if len(tickers) > 1
    }

    print(
        f"PERMNOs observed with >1 ticker value: "
        f"{len(ticker_change_counts):,}"
    )

    if ticker_change_counts:
        print("\nExamples of PERMNOs with multiple tickers:")

        for permno, tickers in list(
            sorted(ticker_change_counts.items())
        )[:20]:
            print(
                f"  PERMNO {permno}: "
                f"{sorted(tickers)}"
            )

    print("\n" + "=" * 80)
    print("END OF VALIDATION")
    print("=" * 80)


if __name__ == "__main__":
    main()