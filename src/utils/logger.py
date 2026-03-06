import sys
from loguru import logger


def setup_logging(config: dict):
    logger.remove()
    level = config.get("level", "INFO")
    log_dir = config.get("log_dir", "logs/")

    logger.add(sys.stderr, level=level, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}")
    logger.add(
        f"{log_dir}/trading_bot.log",
        level=level,
        rotation="10 MB",
        retention=5,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
