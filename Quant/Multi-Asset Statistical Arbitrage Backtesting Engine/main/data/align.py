import pandas as pd
from pathlib import Path

CLEAN_DATA_DIR = Path(r"C:\PATH\Multi-Asset Statistical Arbitrage Backtesting Engine\main\data\cleaned") # Change path accordingly

def align_assets(price_files=None):
    # If no price files exists, "yahoo_prices_cleaned.csv" will be read
    if price_files is None:
        price_files = ['yahoo_prices_cleaned.csv']
    
    # Read multiple price files
    dfs = [pd.read_csv(CLEAN_DATA_DIR/i, index_col=0, parse_dates=True) for i in price_files]
    
    # Outer join to ensure all dates are present
    df_aligned = pd.concat(dfs, axis=1, join="outer").ffill().bfill()
    
    # Save aligned dataframe
    df_aligned.to_csv(CLEAN_DATA_DIR / "aligned_prices.csv")
    return df_aligned