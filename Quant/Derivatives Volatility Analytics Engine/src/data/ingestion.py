from __future__ import annotations
from pathlib import Path
import pandas as pd
from .schema import COLUMN_RENAME_MAP, EXPECTED_RAW_COLUMNS


NUMERIC_COLUMNS = [
    "quote_unixtime",
    "quote_time_hours",
    "underlying_last",
    "expire_unix",
    "dte",
    "c_delta",
    "c_gamma",
    "c_vega",
    "c_theta",
    "c_rho",
    "c_volume",
    "c_last",
    "c_bid",
    "c_ask",
    "strike",
    "p_bid",
    "p_ask",
    "p_last",
    "p_delta",
    "p_gamma",
    "p_vega",
    "p_theta",
    "p_rho",
    "p_volume",
    "strike_distance",
    "strike_distance_pct",
]

OPTION_NUMERIC_COLUMNS = [
    "c_iv",
    "c_volume",
    "c_last",
    "c_bid",
    "c_ask",
    "p_iv",
    "p_volume",
    "p_last",
    "p_bid",
    "p_ask",
]


def load_raw_option_chain(path: str | Path) -> pd.DataFrame:
    """
    Load a raw SPY option-chain file.
    The raw dataset uses comma-separated values and may contain blank strings in several fields.

    Parameters:
    - path: Path to the raw TXT/CSV file.

    Returns:    
    - pd.DataFrame: Raw dataframe with canonical column names and normalized primitive data types.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Raw data file not found: {path}")

    df = pd.read_csv(
        path, sep=",", skipinitialspace=True, na_values=[""], keep_default_na=True,
    )

    missing_columns = set(EXPECTED_RAW_COLUMNS) - set(df.columns)

    if missing_columns:
        raise ValueError(f"Missing expected columns: {sorted(missing_columns)}")

    df = df.rename(columns=COLUMN_RENAME_MAP)


    # ------------------------------------------------------------------
    # Datetime normalization
    # ------------------------------------------------------------------
    df["quote_readtime"] = pd.to_datetime(
        df["quote_readtime"], errors="coerce",
    )

    df["quote_date"] = pd.to_datetime(
        df["quote_date"], errors="coerce",
    )

    df["expire_date"] = pd.to_datetime(
        df["expire_date"], errors="coerce",
    )


    # ------------------------------------------------------------------
    # Numeric normalization
    # ------------------------------------------------------------------
    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column], errors="coerce",
            )

    # IV requires special handling because the raw file may contain blank strings and malformed values.
    for column in ["c_iv", "p_iv"]:
        df[column] = pd.to_numeric(
            df[column], errors="coerce",
        )


    # ------------------------------------------------------------------
    # Preserve volume missingness
    # ------------------------------------------------------------------
    # IMPORTANT:
    # Missing volume is NOT converted to zero.
    # NaN means the vendor did not provide a volume observation.
    # 0 means an explicit zero was reported.


    # ------------------------------------------------------------------
    # Sort chronologically
    # ------------------------------------------------------------------
    df = df.sort_values(
        ["quote_date", "expire_date", "strike"]).reset_index(drop=True)
    return df