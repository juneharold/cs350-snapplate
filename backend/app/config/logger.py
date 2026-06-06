from __future__ import annotations

import sys

from loguru import logger

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        ),
    )
    _configured = True


def create_logger(name: str):
    _configure()
    return logger.bind(name=name)
