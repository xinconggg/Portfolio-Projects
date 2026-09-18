from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_CRSP = PROJECT_ROOT / "data" / "raw" / "crsp"

DAILY_FILE = (
    RAW_CRSP / "CRSP_Daily Stock File.csv"
)


def parse_date(
    series: pd.Series,
) -> pd.Series:
    return pd.to_datetime(
        series,
        dayfirst=True,
        errors="coerce",
    )


def numeric(
    series: pd.Series,
) -> pd.Series:
    return pd.to_numeric(
        series,
        errors="coerce",
    )


def report_count(
    label: str,
    value: int,
) -> None:
    print(
        f"{label:<45} {value:>12,}"
    )


def main() -> None:

    print("=" * 90)
    print("CRSP FULL-FILE DAILY STOCK VALIDATION")
    print("=" * 90)

    df = pd.read_csv(
        DAILY_FILE,
    )

    print()
    print(f"Rows loaded: {len(df):,}")
    print(f"Columns: {len(df.columns):,}")

    # -------------------------------------------------------------------------
    # DATE
    # -------------------------------------------------------------------------

    print()
    print("-" * 90)
    print("DATE VALIDATION")
    print("-" * 90)

    date = parse_date(
        df["DlyCalDt"]
    )

    yyyymmdd = pd.to_datetime(
        df["YYYYMMDD"].astype(str),
        format="%Y%m%d",
        errors="coerce",
    )

    report_count(
        "Invalid DlyCalDt",
        int(date.isna().sum()),
    )

    report_count(
        "Invalid YYYYMMDD",
        int(yyyymmdd.isna().sum()),
    )

    disagreement = (
        date.notna()
        & yyyymmdd.notna()
        & (date != yyyymmdd)
    )

    report_count(
        "YYYYMMDD/DlyCalDt disagreements",
        int(disagreement.sum()),
    )

    print(
        f"Earliest date: {date.min()}"
    )

    print(
        f"Latest date:   {date.max()}"
    )

    # -------------------------------------------------------------------------
    # PERMNO
    # -------------------------------------------------------------------------

    print()
    print("-" * 90)
    print("PERMNO VALIDATION")
    print("-" * 90)

    permno = numeric(
        df["PERMNO"]
    )

    report_count(
        "Missing PERMNO",
        int(permno.isna().sum()),
    )

    report_count(
        "Invalid PERMNO <= 0",
        int((permno <= 0).sum()),
    )

    print(
        f"Unique PERMNOs: "
        f"{permno.nunique():,}"
    )

    # -------------------------------------------------------------------------
    # PERMCO
    # -------------------------------------------------------------------------

    print()
    print("-" * 90)
    print("PERMNO / PERMCO")
    print("-" * 90)

    permco = numeric(
        df["PERMCO"]
    )

    relationship = (
        df.assign(
            _PERMNO=permno,
            _PERMCO=permco,
        )
        .groupby("_PERMNO")["_PERMCO"]
        .nunique()
    )

    multiple_permco = relationship[
        relationship > 1
    ]

    report_count(
        "PERMNOs with >1 PERMCO",
        len(multiple_permco),
    )

    # -------------------------------------------------------------------------
    # DUPLICATES
    # -------------------------------------------------------------------------

    print()
    print("-" * 90)
    print("PERMNO / DATE UNIQUENESS")
    print("-" * 90)

    temp = df.assign(
        _date=date,
        _PERMNO=permno,
    )

    valid_key = (
        temp["_PERMNO"].notna()
        & temp["_date"].notna()
    )

    key_duplicates = temp.loc[
        valid_key
    ].duplicated(
        subset=["_PERMNO", "_date"],
        keep=False,
    )

    duplicate_groups = (
        temp.loc[
            valid_key & key_duplicates,
            ["_PERMNO", "_date"],
        ]
        .drop_duplicates()
    )

    report_count(
        "Rows in duplicate groups",
        int(key_duplicates.sum()),
    )

    report_count(
        "Duplicate PERMNO/date groups",
        len(duplicate_groups),
    )

    # -------------------------------------------------------------------------
    # PRICE VALIDATION
    # -------------------------------------------------------------------------

    print()
    print("-" * 90)
    print("PRICE VALIDATION")
    print("-" * 90)

    price_columns = [
        "DlyPrc",
        "DlyOpen",
        "DlyHigh",
        "DlyLow",
        "DlyClose",
    ]

    for column in price_columns:

        values = numeric(
            df[column]
        )

        report_count(
            f"{column} missing",
            int(values.isna().sum()),
        )

        report_count(
            f"{column} <= 0",
            int((values <= 0).sum()),
        )

    high = numeric(
        df["DlyHigh"]
    )

    low = numeric(
        df["DlyLow"]
    )

    open_ = numeric(
        df["DlyOpen"]
    )

    close = numeric(
        df["DlyClose"]
    )

    invalid_low_high = (
        low.notna()
        & high.notna()
        & (low > high)
    )

    invalid_open_range = (
        open_.notna()
        & low.notna()
        & high.notna()
        & (
            (open_ < low)
            | (open_ > high)
        )
    )

    invalid_close_range = (
        close.notna()
        & low.notna()
        & high.notna()
        & (
            (close < low)
            | (close > high)
        )
    )

    report_count(
        "Low > High",
        int(invalid_low_high.sum()),
    )

    report_count(
        "Open outside Low/High",
        int(invalid_open_range.sum()),
    )

    report_count(
        "Close outside Low/High",
        int(invalid_close_range.sum()),
    )

    # -------------------------------------------------------------------------
    # BID / ASK
    # -------------------------------------------------------------------------

    print()
    print("-" * 90)
    print("BID / ASK VALIDATION")
    print("-" * 90)

    bid = numeric(
        df["DlyBid"]
    )

    ask = numeric(
        df["DlyAsk"]
    )

    report_count(
        "Missing bid",
        int(bid.isna().sum()),
    )

    report_count(
        "Missing ask",
        int(ask.isna().sum()),
    )

    report_count(
        "Bid <= 0",
        int((bid <= 0).sum()),
    )

    report_count(
        "Ask <= 0",
        int((ask <= 0).sum()),
    )

    crossed = (
        bid.notna()
        & ask.notna()
        & (bid > ask)
    )

    report_count(
        "Bid > Ask",
        int(crossed.sum()),
    )

    # -------------------------------------------------------------------------
    # VOLUME / TRADES
    # -------------------------------------------------------------------------

    print()
    print("-" * 90)
    print("TRADING ACTIVITY")
    print("-" * 90)

    volume = numeric(
        df["DlyVol"]
    )

    trades = numeric(
        df["DlyNumTrd"]
    )

    report_count(
        "Missing DlyVol",
        int(volume.isna().sum()),
    )

    report_count(
        "Negative DlyVol",
        int((volume < 0).sum()),
    )

    report_count(
        "Missing DlyNumTrd",
        int(trades.isna().sum()),
    )

    report_count(
        "Negative DlyNumTrd",
        int((trades < 0).sum()),
    )

    # -------------------------------------------------------------------------
    # RETURNS
    # -------------------------------------------------------------------------

    print()
    print("-" * 90)
    print("RETURNS")
    print("-" * 90)

    for column in [
        "DlyRet",
        "DlyRetx",
        "DlyRetI",
    ]:

        values = numeric(
            df[column]
        )

        report_count(
            f"{column} missing",
            int(values.isna().sum()),
        )

    # -------------------------------------------------------------------------
    # CORPORATE ACTION FIELDS
    # -------------------------------------------------------------------------

    print()
    print("-" * 90)
    print("CORPORATE ACTION FIELDS")
    print("-" * 90)

    for column in [
        "DisExDt",
        "DisDivAmt",
        "DisFacPr",
        "DisFacShr",
    ]:

        report_count(
            f"{column} missing",
            int(df[column].isna().sum()),
        )

    print()
    print("=" * 90)
    print("VALIDATION COMPLETE")
    print("=" * 90)


if __name__ == "__main__":
    main()