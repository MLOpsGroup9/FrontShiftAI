import logging
import os

# Create logs directory if not exists
os.makedirs("logs", exist_ok=True)

def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # File handler
    file_handler = logging.FileHandler("logs/pipeline.log")
    file_handler.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Avoid duplicate handlers
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
