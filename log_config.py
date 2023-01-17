import logging


def get_logger(name):
    """Переопределим логгер."""
    logger = logging.getLogger(name)
    stream_handler = logging.StreamHandler()
    logger.addHandler(stream_handler)
    stream_formatter = logging.Formatter(
        '[%(levelname)s] %(asctime)s - %(name)s.%(funcName)s: %(message)s')
    stream_handler.setFormatter(stream_formatter)
    logger.setLevel(logging.DEBUG)
    return logger
