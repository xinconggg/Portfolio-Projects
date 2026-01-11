import pandas as pd
import numpy as np
from pathlib import Path

RAW_DATA_DIR = Path(r"PATH\Multi_Asset_Stat_Arb_Backtesting_Engine\main\data\raw") # Change path accordingly
CLEAN_DATA_DIR = Path(r"PATH\Multi_Asset_Stat_Arb_Backtesting_Engine\main\data\cleaned") # Change path accordingly
CLEAN_DATA_DIR.mkdir(exist_ok=True)

def clean_prices(file="yahoo_prices.csv"):
    # Read raw data
    df = pd.read_csv(RAW_DATA_DIR/file, index_col=0, parse_dates=True)
    
    # Forward fill missing prices
    df = df.ffill().bfill()
    
    # Clip extreme daily returns to prevent mispricing noise
    returns = df.pct_change().clip(-0.2, 0.2)
    
    # Reconstruct adjusted price
    df_cleaned = (1 + returns).cumprod()
    
    # Save cleaned dataframe
    df_cleaned.to_csv(CLEAN_DATA_DIR / "yahoo_prices_cleaned.csv")
    return df_cleaned

clean_prices()