import pandas as pd

def rebalance_positions(positions: pd.Series, freq: int=5):
    """
    Rebalance trading positions at a fixed frequency.

    Inputs:
    - positions: Positions over time
    - freq: Rebalancing frequncy in day periods (i.e. freq=5: rebalance every 5 day)

    Outputs:
    - reb_positions (pd.Series): Rebalanced positions
    """
    # Copy original positions to avoid modifying input
    reb_positions = positions.copy()

    # Iterate through all time steps
    for i in range(len(positions)):
        # If not a rebalance day
        if i % freq != 0:
            # Carry forward previous position
            reb_positions.iloc[i] = reb_positions.iloc[i-1]
        # Else, if its a rebalance day, keep new position
    return reb_positions