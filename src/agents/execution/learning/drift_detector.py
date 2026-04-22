"""Drift detector - detects concept drift in market behavior"""
from typing import List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
from scipy import stats

from ...core.logger import get_agent_logger
from ...config.base import LearningConfig


@dataclass
class DriftReport:
    """Report of detected drift"""
    is_drift: bool
    p_value: float
    statistic: float
    timestamp: datetime
    affected_features: List[str]


class DriftDetector:
    """
    Detects concept drift using statistical tests.
    Compares recent data against baseline distribution.
    """

    def __init__(self, config: LearningConfig, window: int = 50):
        self.config = config
        self.window = window
        self.logger = get_agent_logger(0)
        self.baseline: Optional[np.ndarray] = None
        self.baseline_window = 200
        self.recent_buffer: List[np.ndarray] = []

    def set_baseline(self, data: np.ndarray):
        """Set baseline distribution"""
        self.baseline = data[-self.baseline_window:] if len(data) > self.baseline_window else data
        self.logger.info(f"Baseline set with {len(self.baseline)} samples")

    def add_observation(self, observation: np.ndarray):
        """Add new observation"""
        self.recent_buffer.append(observation)
        if len(self.recent_buffer) > self.window:
            self.recent_buffer = self.recent_buffer[-self.window:]

    def check_drift(self) -> DriftReport:
        """
        Check for drift between baseline and recent observations

        Returns:
            DriftReport
        """
        if self.baseline is None or len(self.recent_buffer) < 10:
            return DriftReport(False, 1.0, 0.0, datetime.utcnow(), [])

        recent = np.array(self.recent_buffer)
        if recent.ndim > 1:
            recent = recent.mean(axis=1)  # aggregate features

        baseline_mean = np.mean(self.baseline)
        recent_mean = np.mean(recent)

        # Kolmogorov-Smirnov test
        try:
            statistic, p_value = stats.ks_2samp(self.baseline, recent)
        except Exception:
            statistic, p_value = 0.0, 1.0

        is_drift = p_value < self.config.drift_p_value

        report = DriftReport(
            is_drift=is_drift,
            p_value=p_value,
            statistic=statistic,
            timestamp=datetime.utcnow(),
            affected_features=[]
        )

        if is_drift:
            self.logger.warning(f"Concept drift detected: p={p_value:.4f}, stat={statistic:.4f}")
            # Reset baseline to recent data
            self.set_baseline(recent)

        return report
