import logging
import traceback
from logging.handlers import RotatingFileHandler

class CustomFormatter(logging.Formatter):
    def formatException(self, exc_info):
        result = super().formatException(exc_info)
        return f"{result}"

    def format(self, record):
        if record.exc_info:
            # Save the original exc_info and set it to None
            exc_info = record.exc_info
            record.exc_info = None
            # Format the log message without the traceback
            message = super().format(record)
            # Restore the original exc_info
            record.exc_info = exc_info
            # Add the traceback to the log message
            traceback_message = self.formatException(record.exc_info)
            return f"{'`' * 100}\n{message}\n{traceback_message}\n{'`' * 100}\n"
        else:
            message = super().format(record)
            return f"{'`' * 100}\n{message}\n{'`' * 100}\n"

# Set up the logging configuration
log_file = 'log.txt'
max_file_size = 1024 * 1024  # 1 MB
backup_count = 0  # Set to 0 for only one log file

# Create a rotating file handler
handler = RotatingFileHandler(log_file, maxBytes=max_file_size, backupCount=backup_count)
handler.setLevel(logging.ERROR)

# Set the log format
formatter = CustomFormatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Get the root logger and add the handler
logger = logging.getLogger('')
logger.addHandler(handler)