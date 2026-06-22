import logging
import sys
from config import Config


def setup_logging():
    """Configure root logger with structured format and configurable level.

    Reads LOG_LEVEL and DEBUG from Config. Outputs to stdout.
    """
    log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

    if Config.DEBUG:
        logging.getLogger().setLevel(logging.DEBUG)
