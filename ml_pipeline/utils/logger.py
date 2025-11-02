# ml_pipeline/utils/logger.py
import logging
from datetime import datetime
from pathlib import Path

def get_logger(script_name: str):
    """
    Returns a logger configured to log both to console and file.
    Each script (rag_eval, bias_detection, sensitivity_analysis)
    will have its own daily log file.
    """
    base_dir = Path(__file__).resolve().parents[2]  # /FrontShiftAI
    log_dir = base_dir / "ml_pipeline" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # One log file per script per day
    timestamp = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"{script_name}_{timestamp}.log"

    logger = logging.getLogger(script_name)

    # Avoid duplicate handlers (in case of multiple imports)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
