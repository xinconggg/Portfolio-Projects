import pandas as pd
import numpy as np

def dollar_neutral_allocation(signals: pd.Series, capital: float=100000):
    """
    Allocate capital in a dollar-neutral (equal amount in long and short positions) way between long and short positions.

    Input:
    - signals: Position signals (-1:Short, 0:Hold, 1:Long)
    - capital: Total portfolio capital

    Output:
    - positions (pd.Series): Dollar allocation per position (+:Long, -:Short)
    """
    # Identify current longs and shorts
    longs = signals[signals==1].index
    shorts = signals[signals==-1].index

    # Avoid division by zero if no positions under long or short
    n_longs = len(longs) if len(longs)>0 else 1
    n_shorts = len(shorts) if len(shorts)>0 else 1

    # Initialize positions
    positions = pd.Series(0.0, index=signals.index)

    # Allocate equally within each side
    positions[signals==1] = capital / 2 / n_longs
    positions[signals==-1] = -(capital / 2 / n_shorts)
    
    return positions

def volatility_targeting(signals: pd.Series, prices: pd.Series, target_vol: float=0.02):
    """
    Adjust position sizes to target a desired daily portfolio volatility.

    Steps:
    1) Compute daily returns of the underlying prices
    2) Compute realized daily volatility
    3) Scale positions to achieve target_vol

    Inputs:
    - signals: Position signals (-1:Short, 0:Hold, 1:Long)
    - prices: Price series of the asset
    - target_vol: Desired daily volatility of the portfolio

    Output:
    - scaled_positions (pd.Series): Dollar allocation adjusted for volatility
    """
    # Daily returns
    returns = prices.pct_change().dropna()

    # Daily volatility
    vol = returns.std()

    # Dollar-neutral allocation
    allocation = dollar_neutral_allocation(signals)

    # Scale to hit target volatility and avoid division by 0
    scaling = target_vol / vol if vol>0 else 1

    # Derive scaled positions
    scaled_positions = allocation * scaling
    return scaled_positions