from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = [
    "PERMNO",
    "PERMCO",
    "Ticker",
    "SecurityType",
    "SecuritySubType",
    "ShareType",
    "PrimaryExch",
    "SICCD",
    "NAICS",
    "DlyCalDt",
    "DlyPrc",
    "DlyVol",
    "DlyCap",
]


def load_clean_crsp(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CRSP clean file not found: {path}")

    df = pd.read_csv(path, low_memory=False)

    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(
            "CRSP clean file is missing required columns: "
            + ", ".join(missing)
        )

    df["DlyCalDt"] = pd.to_datetime(df["DlyCalDt"], errors="coerce")

    return df


def build_security_profile(df: pd.DataFrame) -> pd.DataFrame:
    dimensions = [
        "SecurityType",
        "SecuritySubType",
        "ShareType",
        "PrimaryExch",
    ]

    frames = []

    for column in dimensions:
        counts = (
            df[column]
            .astype("string")
            .fillna("<MISSING>")
            .value_counts(dropna=False)
            .rename_axis(column)
            .reset_index(name="observations")
        )

        counts["unique_PERMNOs"] = counts[column].map(
            df.assign(
                _category=df[column].astype("string").fillna("<MISSING>")
            )
            .groupby("_category")["PERMNO"]
            .nunique()
        )

        counts["dimension"] = column
        counts = counts.rename(columns={column: "category"})

        frames.append(
            counts[
                [
                    "dimension",
                    "category",
                    "observations",
                    "unique_PERMNOs",
                ]
            ]
        )

    return pd.concat(frames, ignore_index=True)


def build_combined_security_profile(df: pd.DataFrame) -> pd.DataFrame:
    dimensions = [
        "SecurityType",
        "SecuritySubType",
        "ShareType",
        "PrimaryExch",
    ]

    profile = (
        df.groupby(dimensions, dropna=False)
        .agg(
            observations=("PERMNO", "size"),
            unique_PERMNOs=("PERMNO", "nunique"),
        )
        .reset_index()
    )

    return profile.sort_values(
        dimensions,
        kind="mergesort",
    )


def build_dataset_profile(df: pd.DataFrame) -> pd.DataFrame:
    per_permno = (
        df.groupby("PERMNO", dropna=False)
        .agg(
            PERMCO=("PERMCO", "first"),
            observations=("PERMNO", "size"),
            first_date=("DlyCalDt", "min"),
            last_date=("DlyCalDt", "max"),
            nonmissing_price=("DlyPrc", "count"),
            nonmissing_volume=("DlyVol", "count"),
            avg_daily_volume=("DlyVol", "mean"),
            median_daily_volume=("DlyVol", "median"),
            avg_market_cap=("DlyCap", "mean"),
            median_market_cap=("DlyCap", "median"),
        )
        .reset_index()
    )

    return per_permno.sort_values("PERMNO", kind="mergesort")


def build_year_profile(df: pd.DataFrame) -> pd.DataFrame:
    work = df.loc[df["DlyCalDt"].notna()].copy()
    work["year"] = work["DlyCalDt"].dt.year

    return (
        work.groupby("year")
        .agg(
            observations=("PERMNO", "size"),
            unique_PERMNOs=("PERMNO", "nunique"),
        )
        .reset_index()
        .sort_values("year")
    )


def print_overview(df: pd.DataFrame) -> None:
    print("\n=== CRSP CLEAN DATASET PROFILE ===")
    print(f"Rows:              {len(df):,}")
    print(f"Columns:           {len(df.columns):,}")
    print(f"Unique PERMNOs:    {df['PERMNO'].nunique():,}")
    print(f"Unique PERMCOs:    {df['PERMCO'].nunique():,}")
    print(f"Unique tickers:    {df['Ticker'].nunique(dropna=True):,}")
    print(f"Minimum date:      {df['DlyCalDt'].min()}")
    print(f"Maximum date:      {df['DlyCalDt'].max()}")

    print("\n=== SECURITY TYPES ===")
    print(
        df["SecurityType"]
        .value_counts(dropna=False)
        .rename("observations")
        .to_string()
    )

    print("\n=== SECURITY SUBTYPES ===")
    print(
        df["SecuritySubType"]
        .value_counts(dropna=False)
        .rename("observations")
        .to_string()
    )

    print("\n=== SHARE TYPES ===")
    print(
        df["ShareType"]
        .value_counts(dropna=False)
        .rename("observations")
        .to_string()
    )

    print("\n=== PRIMARY EXCHANGES ===")
    print(
        df["PrimaryExch"]
        .value_counts(dropna=False)
        .rename("observations")
        .to_string()
    )

def build_permno_classification_profile(df: pd.DataFrame) -> pd.DataFrame:
    dimensions = [
        "SecurityType",
        "SecuritySubType",
        "ShareType",
        "PrimaryExch",
    ]

    rows = []

    for permno, group in df.groupby("PERMNO", dropna=False):
        row = {
            "PERMNO": permno,
            "observations": len(group),
        }

        for column in dimensions:
            values = (
                group[column]
                .astype("string")
                .fillna("<MISSING>")
                .drop_duplicates()
                .sort_values()
                .tolist()
            )

            row[f"{column}_nunique"] = len(values)
            row[f"{column}_values"] = "|".join(values)

        rows.append(row)

    return (
        pd.DataFrame(rows)
        .sort_values("PERMNO", kind="mergesort")
        .reset_index(drop=True)
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Profile Phase 2 clean CRSP data for Phase 3 Tier 1 construction."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/crsp/crsp_daily_clean.csv"),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/crsp"),
    )

    args = parser.parse_args()

    df = load_clean_crsp(args.input)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    security_profile = build_security_profile(df)
    security_profile.to_csv(
        args.output_dir / "crsp_security_type_profile.csv",
        index=False,
    )

    combined_profile = build_combined_security_profile(df)
    combined_profile.to_csv(
        args.output_dir / "crsp_security_type_combinations.csv",
        index=False,
    )   

    dataset_profile = build_dataset_profile(df)
    dataset_profile.to_csv(
        args.output_dir / "crsp_tier1_profile.csv",
        index=False,
    )

    year_profile = build_year_profile(df)
    year_profile.to_csv(
        args.output_dir / "crsp_tier1_year_profile.csv",
        index=False,
    )

    permno_classification = build_permno_classification_profile(df)

    permno_classification.to_csv(
        args.output_dir / "crsp_permno_classification_profile.csv",
        index=False,
    )
    print_overview(df)

    print("\n=== OUTPUTS ===")
    print(args.output_dir / "crsp_tier1_profile.csv")
    print(args.output_dir / "crsp_security_type_profile.csv")
    print(args.output_dir / "crsp_security_type_combinations.csv")
    print(args.output_dir / "crsp_tier1_year_profile.csv")

    print("\n=== PERMNO CLASSIFICATION PROFILE ===")
    print(
        permno_classification[
            [
                "PERMNO",
                "SecurityType_nunique",
                "SecuritySubType_nunique",
                "ShareType_nunique",
                "PrimaryExch_nunique",
            ]
        ].to_string(index=False)
    )
    
    classification = pd.read_csv(
    "data/processed/crsp/crsp_permno_classification_profile.csv"
)

    print("\n=== CLASSIFICATION VALUES per PERMNO ===")
    print(
        classification[
            [
                "PERMNO",
                "SecurityType_values",
                "SecuritySubType_values",
                "ShareType_values",
                "PrimaryExch_values",
            ]
        ].to_string(index=False)
    )

    print("\n=== INSPECT THE FIVE EXCHANGE-CHANGING SECURITIES ===")
    print(
        classification[
            classification["PrimaryExch_nunique"] > 1
        ][
            [
                "PERMNO",
                "SecurityType_values",
                "SecuritySubType_values",
                "ShareType_values",
                "PrimaryExch_values",
            ]
        ].to_string(index=False)
    )
    
    print("\n=== INSPECT THE `AD` SHARE TYPE ===")
    ad_permnos = (
    df.loc[df["ShareType"].eq("AD"), "PERMNO"]
    .drop_duplicates()
    .sort_values()
    )

    print("PERMNOs with ShareType = AD:")
    print(ad_permnos.to_list())

    print(f"\nCount: {len(ad_permnos)}")
    
    print(
        df.loc[df["ShareType"].eq("AD")]
        .groupby(
            [
                "PERMNO",
                "PERMCO",
                "SecurityType",
                "SecuritySubType",
                "PrimaryExch",
            ],
            dropna=False,
        )
        .agg(
            observations=("PERMNO", "size"),
            first_date=("DlyCalDt", "min"),
            last_date=("DlyCalDt", "max"),
        )
        .reset_index()
        .sort_values("PERMNO")
        .to_string(index=False)
    )
    
if __name__ == "__main__":
    main()