import sys
import logging

class CustomFormatter(logging.Formatter):
    grey = "\x1b[37;20m"
    yellow = "\x1b[33;20m"
    green = "\x1b[32;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    blue = "\x1b[34;20m"
    magenta = "\x1b[35;20m"
    cyan = "\x1b[36;20m"
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    format_info = ["%(asctime)s - ", "%(name)s", " - %(levelname)s - ", "%(message)s (%(filename)s:%(lineno)d)"]

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format_info[0] + cyan + format_info[1] +
                      green + format_info[2] + grey + format_info[3] + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def logger(name, level=logging.DEBUG):
    app_logger = logging.getLogger(name)
    app_logger.setLevel(level)
    # create console handler with a higher log level
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(CustomFormatter())
    app_logger.addHandler(handler)
    return app_logger
