import pandas as pd
from datetime import datetime
import os

log_path = "data/processed/pipeline_log.csv"

def log_pipeline_step(step_name, records_processed, status="SUCCESS"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = pd.DataFrame([{
        "timestamp": timestamp,
        "step": step_name,
        "records_processed": records_processed,
        "status": status
    }])
    if os.path.exists(log_path):
        log_entry.to_csv(log_path, mode="a", header=False, index=False)
    else:
        log_entry.to_csv(log_path, index=False)