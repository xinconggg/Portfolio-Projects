import numpy as np
import pandas as pd

def parameter_sweep(zscore: pd.Series,
                    entry_range: list,
                    exit_range: list,
                    max_hold_range: list,
                    prices: pd.DataFrame):
    """
    Perform a grid search/sensitivity analysis to test strategy robustness across multiple parameters.

    Inputs:
    - zscore: Spread z-score
    - entry_range: Entry threshold
    - exit_range: Exit threshold
    - max_hold_range: Maximum holding period
    - pricesL Asset price series for volatility targeting

    Outputs:
    - (pd.DataFrame): Consisting of columns: entry, exit, max_hold, final_pnl
                      Each row represents one parameter combination
    """
    from Multi_Asset_Stat_Arb_Backtesting_Engine.main.signals.signal_generator import generate_signals
    from Multi_Asset_Stat_Arb_Backtesting_Engine.main.portfolio.allocation import volatility_targeting

    # Drop NaNs in zscore and prices
    zscore = zscore.dropna()
    prices = prices.loc[zscore.index].dropna()

    results = []

    # Loop through all combinations of parameters
    for entry in entry_range:
        for exit in exit_range:
            for max_hold in max_hold_range:
                # Generate trading signals for this parameter set
                signals = generate_signals(zscore, entry_threshold=entry,
                                           exit_threshold=exit,
                                           max_hold=max_hold)
                
                # Convert signals to dollar positions with volatility targeting
                positions = volatility_targeting(signals, prices, target_vol=0.02)
                
                # PnL calculation
                daily_returns = positions.shift(1) * prices.pct_change()
                daily_returns = daily_returns.replace([np.inf, -np.inf], 0).fillna(0)

                final_pnl = np.nancumsum(daily_returns)[-1] # cumulative PnL for this parameter combo
                
                # Store results
                results.append({
                    'entry': entry,
                    'exit': exit,
                    'max_hold': max_hold,
                    'final_pnl': final_pnl
                })

    return pd.DataFrame(results)