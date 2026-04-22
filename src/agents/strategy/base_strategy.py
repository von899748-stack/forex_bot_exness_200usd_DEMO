"""Base strategy interface"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ...core.types import Signal, SignalType
from datetime import datetime


class BaseStrategy(ABC):
    """Abstract base for all strategies"""

    @abstractmethod
    async def generate_signal(self, analysis: Dict[str, Any]) -> Optional[Signal]:
        """Generate trading signal from analysis"""
        pass
