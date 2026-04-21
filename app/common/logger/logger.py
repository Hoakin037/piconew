import logging
from colorama import Fore, Style

from app.common.consts.logger import LoggerFormatEnum

class ColoredFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: Fore.BLUE,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT
    }

    def format(self, record):
        if record.levelno in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelno]}{record.levelname}{Style.RESET_ALL}"
            record.msg = f"{self.COLORS[record.levelno]}{record.msg}{Style.RESET_ALL}"
        return super().format(record)

def setup_logging(logger_name,level=logging.INFO):
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_formatter = ColoredFormatter(LoggerFormatEnum.BASE.value)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger