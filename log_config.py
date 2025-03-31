# log_config.py
import logging

def setup_logging(log_file: str = None, level: str = "DEBUG"):
    """
    Sets up logging to console and optionally to a file if `log_file` is provided.
    """
    # Resolve the numeric level (DEBUG, INFO, WARNING, etc.)
    numeric_level = getattr(logging, level.upper(), logging.DEBUG)

    # Create a list of handlers: always have console handler
    handlers = []

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    handlers.append(console_handler)

    # If a log_file is specified, also log to file
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        handlers.append(file_handler)

    # Set up the log format you prefer
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    
    # Configure logging with both handlers
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=handlers
    )
