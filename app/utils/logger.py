import logging
import sys
from app.config import get_settings

settings = get_settings()

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

logging.basicConfig(
    level=logging.getLevelName(settings.log_level),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)