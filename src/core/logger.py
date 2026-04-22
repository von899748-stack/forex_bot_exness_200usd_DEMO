"""Logging configuration with loguru"""
import sys
from pathlib import Path
from loguru import logger
from typing import Optional

from ..config.base import Config


def setup_logger(config: Optional[Config] = None, log_level: str = "INFO"):
    """Configure loguru logger with rotation and formatting"""

    # Remove default handler
    logger.remove()

    # Console handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
    )

    # File handler with rotation
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    logger.add(
        logs_dir / "system.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level,
        rotation="1 day",
        retention="7 days",
        compression="zip",
        enqueue=True,
    )

    # Agent-specific logs
    logger.add(
        logs_dir / "agents" / "agent_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | Agent {extra[agent_id]} | {message}",
        level=log_level,
        rotation="1 day",
        retention="7 days",
        compression="zip",
        enqueue=True,
    )

    return logger


def get_agent_logger(agent_id: int):
    """Get a logger bound to a specific agent ID"""
    return logger.bind(agent_id=agent_id)
