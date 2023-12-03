import logging as log


class ColoredFormatter(log.Formatter):
    colors = {
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',  # Red
        'INFO': '\033[37m',  # White
        'DEBUG': '\033[92m',  # Green
        'RESET': '\033[0m'  # Reset to default
    }

    def __init__(self, fmt, date_format):
        super().__init__(fmt, date_format)

    def format(self, record):
        log_message = super().format(record)
        return f"{self.colors.get(record.levelname, '')}{log_message}{self.colors.get('RESET', '')}"


class Logger:
    def __init__(self, debug: bool = False, log_file: str = 'error.log'):
        # Create logger
        logger = log.getLogger()
        logger.setLevel(log.INFO)

        # Create custom formatter
        formatter = ColoredFormatter('%(asctime)s [%(levelname)s]: %(message)s', '%y-%m-%d %H:%M:%S')

        # Stream handler (console) with colors
        stream_handler = log.StreamHandler()
        stream_handler.setLevel(log.INFO)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        if log_file:
            logger.info(f"Logging to file: {log_file}")
            file_handler = log.FileHandler(log_file)
            file_handler.setLevel(log.ERROR)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            if debug:
                file_handler.setLevel(log.DEBUG)

        if debug:
            logger.info("Debug mode enabled")
            logger.setLevel(log.DEBUG)
            stream_handler.setLevel(log.DEBUG)

