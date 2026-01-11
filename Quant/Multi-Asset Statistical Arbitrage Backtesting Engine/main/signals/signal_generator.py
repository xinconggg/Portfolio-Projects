import pandas as pd
import numpy as np
from .signal_utils import debounce_signals

def generate_signals(zscore: pd.Series,
                     entry_threshold: float=2.0,
                     exit_threshold: float=0.5,
                     max_hold: int=None):
    """
    Generate long/short trading signals based on spread z-score.

    Trading Logic:
    - Long if z-score <= -entry_threshold
    - Short if z-score >= entry_threshold
    - Exit if |z-score| <= exit_threshold or max holding period is reached

    Input:
    - zscore: Normalized spread (z-score)
    - entry_threshold: Absolute z-score required to enter a position
    - exit_threshold: Absolute z-score required to exit a position
    - max_hold: Maximum holding period of a position

    Output:
    - signals (pd.Series): Position signals (-1:Short, 0:Flat, 1:Long)
    """
    # Initialize signal series
    signals = pd.Series(0, index=zscore.index)

    # Set entry conditions
    long_mask = zscore <= -entry_threshold # Oversold: expect mean reversion upward
    short_mask = zscore >= entry_threshold # Overbought: expect mean reversion downward

    # Set exit condition
    exit_mask = zscore.abs() <= exit_threshold # Mean reversion reached

    position = 0 # Current position
    hold_counter = 0 # Track how long position has been held

    # Iterate through time
    for t in range(len(zscore)):
        # Enter new position if flat
        if position==0:
            if long_mask.iloc[t]:
                position = 1
            elif short_mask.iloc[t]:
                position = -1
        
        elif position!=0:
            # Increase holding period count
            hold_counter += 1

            # Exit position if spread has reverted or max holding period is exceeded
            if exit_mask.iloc[t] or (max_hold is not None and hold_counter >= max_hold):
                # Reset position and hold_counter
                position = 0
                hold_counter = 0

        # Record position for this time
        signals.iloc[t] = position
    
    # Debounce signals
    return debounce_signals(signals)