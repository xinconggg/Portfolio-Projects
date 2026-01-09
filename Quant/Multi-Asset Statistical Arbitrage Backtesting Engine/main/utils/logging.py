import logging
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

def get_logger(name:str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    
    file_handler = logging.FileHandler(LOG_DIR / f"{name}.log")
    file_handler.setFormatter(formatter)
    
    if not logger.handlers:
        logger.addHandler(file_handler)
    
    return logger