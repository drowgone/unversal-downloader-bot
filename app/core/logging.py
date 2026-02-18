import sys
import logging
from loguru import logger
from app.core.config import settings

def setup_logging():
    # Remove default handler
    logger.remove()
    
    # Add structured JSON logging to stdout
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="INFO",
        serialize=False  # Set to True for JSON in production
    )
    
    # Add error log file
    logger.add(
        "logs/error.log",
        level="ERROR",
        rotation="10 MB",
        retention="1 week",
        compression="zip"
    )

    # Intercept standard logging
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

setup_logging()
