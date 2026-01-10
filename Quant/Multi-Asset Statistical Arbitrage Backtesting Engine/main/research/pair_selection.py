import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import coint

def rolling_correlation(prices: pd.DataFrame, window: int=60):
    """
    Compute rolling correlation matrix of time-series returns.

    Input: 
    - prices: DataFrame with each column as time series
    - window: Rolling window size

    Output:
    - rolling_corr (pd.DataFrame): Multi-index dataframe containing rolling correlations between all pairs
    """
    return prices.pct_change().rolling(window).corr()

def find_cointegrated_pairs(prices: pd.DataFrame, significance=0.05):
    """
    Returns a pair of cointegrated pairs based on Engle-Granger Test.

    Input:
    - prices: DataFrame with each column as time series
    - significance: p-value threshold to determine correlation

    Output:
    - pairs (list of tuples): List of tuples (stock 1, stock 2, p-value) for cointegrated pairs
    - pvalue_matrix (np.ndarray): Matrix of p-values for all pairwise cointegration tests
    """
    n = prices.shape[1] # number of time-series columns

    # Initialize a matrix to store the p-values of cointegration tests
    pvalue_matrix = np.ones((n, n))

    keys = prices.columns # Column names (Stock names)

    pairs = [] # List to store cointegrated pairs

    # Loop through each unique pairs of time-series
    for i in range(n):
        for j in range(i+1, n):
            S1 = prices[keys[i]] # time-series of stock 1
            S2 = prices[keys[j]] # time-series of stock 2

            # Perform Engle-Granger cointegration test
            _, pvalue, _ = coint(S1, S2) # coint() returns t-value, p-value, crit value but we only need p-value
 
            # Store p-value in matrix
            pvalue_matrix[i, j] = pvalue

            # If p-value is below significance level, consider them cointegrated
            if pvalue < significance:
                pairs.append((keys[i], keys[j], pvalue))

    # Return list of cointegrated pairs and matrix of p-values
    return pairs, pvalue_matrix