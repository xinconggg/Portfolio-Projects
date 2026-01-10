import numpy as np
from statsmodels.tsa.stattools import adfuller

def half_life(spread: np.ndarray):
    """
    Generate the half-life of mean reversion for a time-series spread (time taken for spread between 2 stocks to shrink by half)

    Input:
    - spread: Time-series containing the spread between two assets

    Output:
    - hl (float): Estimated half-life
    """
    # Lagged spread (all but last value)
    spread_lag = spread[:-1]

    # Compute change in spread
    delta = np.diff(spread)

    # Regress delta on lagged spread to estimate speed of mean reversion
    beta = np.polyfit(spread_lag, delta, 1)[0]

    # Compute half-life = -ln(2) / beta
    hl = -np.log(2) / beta if beta !=0 else np.nan
    return hl

def hurst_exponent(ts: np.ndarray, lags: int=100):
    """
    Compute Hurst exponent (how likely the time-series is going to continue moving in the same direction: 
    - Hurst = 0.5: Random Walk
    - Hurst > 0.5: Likely to continue in same direction
    - Hurst < 0.5: Likely to continue in opposite direction i.e. Mean-Reverting)

    Input:
    - ts: Time-series
    - lags: Maximum lag to compute differences

    Output:
    - Hurst (float): Hurst Exponent
    """
    # Limit lag to half the time-series length to avoid small-sample bias
    lags = min(lags, len(ts)//2)

    # Compute standard deviation of differences for each lag
    tau = [np.std(np.subtract(ts[lag:], ts[:-lag])) for lag in range(2, lags)]

    # Compute Hurst Exponent
    hurst = np.polyfit(np.log(range(2, lags)), np.log(tau), 1)[0] * 2
    return hurst

def adf_test(ts: np.ndarray):
    """
    Perform Augmented Dickey-Fuller (ADF) test for stationarity

    Input:
    - ts: Time-series

    Output:
    - (dict): ADF statistic and p-value:
                - adf_stat: test statistic
                - p_value: probability of null hypothesis
    """
    result = adfuller(ts)
    return {"adf_stat": result[0], "p_value": result[1]}