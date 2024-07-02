from typing import Optional


def get_logger(name: Optional[str] = None):
    import loguru
    return loguru.logger