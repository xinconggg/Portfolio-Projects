import yfinance as yf
import pandas as pd
from pathlib import Path

RAW_DATA_DIR = Path(r"PATH\Multi_Asset_Stat_Arb_Backtesting_Engine\main\data\raw") # Change path accordingly
RAW_DATA_DIR.mkdir(exist_ok=True)

def fetch_yahoo(tickers, start="2017-01-01", end="2026-01-01"):
    """
    Download adjusted close prices and cache locally
    """
    df = yf.download(tickers, start=start, end=end, auto_adjust=True)["Close"]
    df.to_csv(RAW_DATA_DIR / "yahoo_prices.csv")
    return df