import pandas as pd
import numpy as np

def sharpe_ratio(returns: pd.Series, risk_free_rate=0.0):
    """
    Compute annualized Sharpe Ratio.
    """
    return (returns.mean() - risk_free_rate) / returns.std() * np.sqrt(252)

def sortino_ratio(returns: pd.Series, risk_free_rate=0.0):
    """
    Compute annualized Sortino Ratio (similar to Sharpe Ratio but penalizes downside volatility).
    """
    # Downside Volatility
    downside_vol = returns[returns<0].std()
    return (returns.mean() - risk_free_rate) / downside_vol * np.sqrt(252)

def calmar_ratio(returns: pd.Series):
    """
    Compute annualized Calmar Ratio (measures return relative to max drawdown).
    """
    cumulative = (1+returns).cumprod()
    peak = cumulative.cummax()
    drawdown = (peak-cumulative) / peak
    max_dd = drawdown.max()
    return (cumulative.pct_change().mean()*252) / max_dd if max_dd>0 else np.nan

def max_drawdown(returns: pd.Series):
    """
    Compute max drawdown of a return series.
    """
    cumulative = (1+returns).cumprod()
    peak = cumulative.cummax()
    drawdown = (peak-cumulative) / peak
    return drawdown.max()

def hit_rate(returns: pd.Series):
    """
    Percentage of periods with positive returns.
    """
    return (returns>0).sum() / len(returns)

def turnover(positions: pd.Series):
    """
    Measure portfolio turnover as total absolute position changes.
    """
    return positions.diff().abs().sum()