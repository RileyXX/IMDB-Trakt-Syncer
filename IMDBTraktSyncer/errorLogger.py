import os
import logging

class CustomFormatter(logging.Formatter):
    def formatException(self, exc_info):
        result = super().formatException(exc_info)
        return f"{result}"

    def format(self, record):
        if record.exc_info:
            exc_info = record.exc_info
            record.exc_info = None
            message = super().format(record)
            record.exc_info = exc_info
            traceback_message = self.formatException(record.exc_info)
            return f"{'`' * 100}\n{message}\n{traceback_message}\n{'`' * 100}\n"
        else:
            message = super().format(record)
            return f"{'`' * 100}\n{message}\n{'`' * 100}\n"

class PrependFileHandler(logging.Handler):
    def __init__(self, filename):
        super().__init__()
        self.filename = filename

    def emit(self, record):
        try:
            log_entry = self.format(record) + "\n"
            if os.path.exists(self.filename):
                with open(self.filename, "r+", encoding="utf-8") as file:
                    old_content = file.read()
                    file.seek(0)
                    file.write(log_entry + old_content)
            else:
                with open(self.filename, "w", encoding="utf-8") as file:
                    file.write(log_entry)
        except Exception:
            print("Error writing log.")

# Get the directory of the script
script_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(script_dir, "log.txt")

# Create a custom file handler for prepending logs
handler = PrependFileHandler(log_file)
handler.setLevel(logging.ERROR)

# Set the log format
formatter = CustomFormatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

# Get the root logger and add the handler
logger = logging.getLogger("")
logger.setLevel(logging.ERROR)
logger.addHandler(handler)