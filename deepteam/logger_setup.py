
import logging
import sys

def setup_logger():
    """
    Set up a global logger for the application.
    """
    # Get the root logger
    logger = logging.getLogger("DeepTeamLogger")
    if logger.hasHandlers():
        # Logger is already configured
        return logger

    logger.setLevel(logging.DEBUG)  # Set the lowest level to capture all logs

    # Create a formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create a handler for console output, ensuring UTF-8 encoding
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)  # Console shows INFO level and above
    stream_handler.setFormatter(formatter)
    #logger.addHandler(stream_handler)

    # Create a handler for file output, ensuring UTF-8 encoding
    file_handler = logging.FileHandler("red_team_debug.log", mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # File captures everything (DEBUG and above)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# Get a logger instance for any module that needs it
logger = setup_logger()
