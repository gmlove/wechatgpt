import logging
import sys

LOG_LEVEL = logging.DEBUG

logger = logging.getLogger("flask.app")


def set_logger(_logger):
    global logger
    logger = _logger


def get_logger():
    return logger


def _config_logger():
    logger = logging.getLogger("simple_logger")
    logger.setLevel(LOG_LEVEL)
    python_version = sys.version_info
    if python_version.major == 3 and python_version.minor == 6:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())  # type: ignore
    elif hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(LOG_LEVEL)

    formatter = logging.Formatter("[%(asctime)s][%(processName)s:%(threadName)s][%(levelname)s][%(module)s.%(funcName)s:%(lineno)d] %(message)s")
    handler.setFormatter(formatter)

    for existing_handler in logger.handlers:
        logger.removeHandler(existing_handler)
    logger.addHandler(handler)

    return logger


if "unittest" in sys.modules.keys():
    logger.info("enable test logger for testing..")
    logger = _config_logger()
