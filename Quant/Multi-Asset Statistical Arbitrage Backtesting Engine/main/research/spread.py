import pandas as pd
import numpy as np

def compute_beta(S1: pd.Series, S2: pd.Series):
    """
    Compute the hedge ratio (beta) between the two time-series using Ordinary Least Squares (OLS).

    Input:
    - S1: The "dependent" time-series (Long Position)
    - S2: The "independent" time-series (Short Position)

    Output:
    - beta (float): Hedge Ratio
    """
    # Fit a linear model: y = beta*x + alpha
    beta = np.polyfit(S2, S1, 1)[0]
    return beta

def construct_spread(S1: pd.Series, S2: pd.Series):
    """
    Construct the spread between the two time-series then normalize it to a z-score.

    Input:
    - S1: Time-series of price of stock 1 
    - S2: Time-series of price of stock 2

    Output:
    - spread (pd.Series): Raw spread: S1 - beta*S2
    - zscore (pd.Series): Normalized spread
    """
    # Compute hedge ratio (beta)
    beta = compute_beta(S1, S2)

    # Compute raw spread
    spread = S1 - beta * S2

    # Normalize spread to z-score
    zscore = (spread - spread.mean()) / spread.std()

    return spread, zscore