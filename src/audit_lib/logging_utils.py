import logging
import os
from typing import Union


def setup_logging(level: Union[str, int, None] = None) -> None:
    """Configure basic logging with consistent format.

    Parameters
    ----------
    level: str | int | None
        Desired log level (e.g., "DEBUG", "INFO"). If ``None``, the
        ``LOG_LEVEL`` environment variable is consulted. Defaults to
        ``INFO`` if neither is provided.
    """
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

