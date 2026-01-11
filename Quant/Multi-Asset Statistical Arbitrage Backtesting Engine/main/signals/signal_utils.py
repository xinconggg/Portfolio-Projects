import pandas as pd

def debounce_signals(signals: pd.Series, min_gap: int=1):
    """
    Debounce (limit how often a function is executed) trading signals to prevent rapid consecutive entries.
    This function enforces a minumum gap of 1 between changes in position (-1 to 0, 0 to 1, etc., but not -1 to 1 and 1 to -1), helping to reduce noise, overtrading and whipsaw behavior.
    
    Input:
    - signals: Raw position signals (-1, 0, 1)
    - min_gap: Minimum number of periods required between consecutive position changes

    Output:
    - debounced (pd.Series): Debounced position signals i.e. if original = (0,1,-1,1) then debounced = (0,1,0,1)
    """
    last_signal = 0 # Last accepted signal value
    counter = 0 
    debounced = signals.copy()

    for t in range(len(signals)):
        # Detect change in signal
        if signals.iloc[t] != last_signal:
            # If change happens too soon after the previous one, suppress it
            if counter < min_gap and last_signal != 0:
                debounced.iloc[t] = 0
            else:
                # Accept new signal
                last_signal = signals.iloc[t]
                counter = 0
        counter += 1
    return debounced