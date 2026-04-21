from enum import StrEnum


class LoggerFormatEnum(StrEnum):
    BASE = "%(asctime)s - [%(levelname)s] - %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s"