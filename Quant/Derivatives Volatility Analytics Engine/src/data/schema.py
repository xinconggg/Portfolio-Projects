from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class OptionChainSchema:
    """Canonical column names for the option-chain dataset."""

    QUOTE_UNIXTIME: str = "quote_unixtime"
    QUOTE_READTIME: str = "quote_readtime"
    QUOTE_DATE: str = "quote_date"
    QUOTE_TIME_HOURS: str = "quote_time_hours"

    UNDERLYING_LAST: str = "underlying_last"

    EXPIRE_DATE: str = "expire_date"
    EXPIRE_UNIX: str = "expire_unix"
    DTE: str = "dte"

    C_DELTA: str = "c_delta"
    C_GAMMA: str = "c_gamma"
    C_VEGA: str = "c_vega"
    C_THETA: str = "c_theta"
    C_RHO: str = "c_rho"
    C_IV: str = "c_iv"
    C_VOLUME: str = "c_volume"
    C_LAST: str = "c_last"
    C_SIZE: str = "c_size"
    C_BID: str = "c_bid"
    C_ASK: str = "c_ask"

    STRIKE: str = "strike"

    P_BID: str = "p_bid"
    P_ASK: str = "p_ask"
    P_SIZE: str = "p_size"
    P_LAST: str = "p_last"

    P_DELTA: str = "p_delta"
    P_GAMMA: str = "p_gamma"
    P_VEGA: str = "p_vega"
    P_THETA: str = "p_theta"
    P_RHO: str = "p_rho"
    P_IV: str = "p_iv"
    P_VOLUME: str = "p_volume"

    STRIKE_DISTANCE: str = "strike_distance"
    STRIKE_DISTANCE_PCT: str = "strike_distance_pct"


EXPECTED_RAW_COLUMNS = [
    "[QUOTE_UNIXTIME]",
    "[QUOTE_READTIME]",
    "[QUOTE_DATE]",
    "[QUOTE_TIME_HOURS]",
    "[UNDERLYING_LAST]",
    "[EXPIRE_DATE]",
    "[EXPIRE_UNIX]",
    "[DTE]",
    "[C_DELTA]",
    "[C_GAMMA]",
    "[C_VEGA]",
    "[C_THETA]",
    "[C_RHO]",
    "[C_IV]",
    "[C_VOLUME]",
    "[C_LAST]",
    "[C_SIZE]",
    "[C_BID]",
    "[C_ASK]",
    "[STRIKE]",
    "[P_BID]",
    "[P_ASK]",
    "[P_SIZE]",
    "[P_LAST]",
    "[P_DELTA]",
    "[P_GAMMA]",
    "[P_VEGA]",
    "[P_THETA]",
    "[P_RHO]",
    "[P_IV]",
    "[P_VOLUME]",
    "[STRIKE_DISTANCE]",
    "[STRIKE_DISTANCE_PCT]",
]


COLUMN_RENAME_MAP = {
    column: column.strip("[]").lower()
    for column in EXPECTED_RAW_COLUMNS
}