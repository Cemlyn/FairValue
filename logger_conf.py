import logging
import json
from logging import StreamHandler, FileHandler


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger_name": record.name,
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def get_logger(
    logger_name: str, log_file: str = "sec_pipeline.jsonl", level=logging.INFO
):

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    if not logger.hasHandlers():
        formatter = JsonFormatter()
        stream_handler = StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        file_handler = FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
