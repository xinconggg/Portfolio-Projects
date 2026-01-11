import pandas as pd

def split_subperiods(returns: pd.Series, n_splits: int=4):
    """
    Split a return series into multiple consecutive subperiods.

    Purpose:
    - Test stability of strategy over time
    - Check if performance is consistent or dominated by a single period
    - Identify regime shifts or structural breaks

    Inputs:
    - returns: Period returns (daily)
    - n_splits: Number of consecutive subperiods to create

    Outputs:
    - (pd.series): Each element within the series is the returns of one subperiod
    """
    length = len(returns)
    subperiod_length = length // n_splits
    subperiod_results = []

    for i in range(n_splits):
        # Slice consecutive subperiods
        sub = returns.iloc[i * subperiod_length : (i+1) * subperiod_length]
        subperiod_results.append(sub)
    return subperiod_results