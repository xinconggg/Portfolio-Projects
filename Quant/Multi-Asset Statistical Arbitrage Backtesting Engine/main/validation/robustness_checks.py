import pandas as pd
import numpy as np

def false_discovery_control(p_values: np.ndarray, alpha: float=0.05):
    """
    Control the False Discovery Rate (FDR) control using the Benjamini-Hochberg procedure.

    Purpose:
    - When testing multiple pairs or parameters, some may appear 'significant' purely by coincidence
    - FDR control ensures that on average, only a proportion of 'alpha' of the rejections are false positives
    
    Inputs:
    - pvalues: Array of p-values from multiple hypothesis tests
    - alpha: Desired FDR level

    Outputs:
    - reject_final (np.ndarray of bool): True=Reject Null Hypothesis, False=Fail to Reject
    """
    pvals = np.array(p_values)
    n = len(pvals)

    # Sort p-values in ascending order
    sorted_idx = np.argsort(pvals)
    sorted_p = pvals[sorted_idx]

    # Compute BH (Benjamini-Hochberg) threshold = i/n * alpha
    bh_threshold = np.arange(1, n+1) / n*alpha

    # Compare sorted p-values to thresholds
    rejected = sorted_p <= bh_threshold

    # Map rejection decisions back to original order
    reject_final = np.zeros_like(pvals, dtype=bool)
    reject_final[sorted_idx] = rejected

    return reject_final