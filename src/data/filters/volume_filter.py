"""Volume-based filtering"""
import numpy as np
from typing import List
import pandas as pd


class VolumeFilter:
    """Filter data based on volume thresholds"""

    def __init__(
        self,
        min_volume_threshold: float = 0.1,
        window: int = 20
    ):
        """
        Args:
            min_volume_threshold: Minimum volume as fraction of average (e.g., 0.1 = 10%)
            window: Window for calculating average volume
        """
        self.min_volume_threshold = min_volume_threshold
        self.window = window

    def is_volume_sufficient(self, current_volume: float, volume_history: List[float]) -> bool:
        """
        Check if current volume meets minimum threshold

        Args:
            current_volume: Current bar volume
            volume_history: Historical volumes

        Returns:
            True if volume is sufficient
        """
        if len(volume_history) < self.window:
            return True  # Not enough history, accept

        avg_volume = np.mean(volume_history[-self.window:])
        if avg_volume == 0:
            return True

        volume_ratio = current_volume / avg_volume
        return volume_ratio >= self.min_volume_threshold

    def filter_by_volume(
        self,
        volumes: List[float],
        data: List[float],
        fill_value: float = None
    ) -> List[float]:
        """
        Filter data points with insufficient volume

        Args:
            volumes: List of volumes
            data: Data to filter (e.g., prices)
            fill_value: Value to use for filtered points (None = keep original)

        Returns:
            Filtered data with low-volume points replaced
        """
        if len(volumes) != len(data):
            raise ValueError("volumes and data must have same length")

        result = list(data)
        for i in range(len(volumes)):
            if not self.is_volume_sufficient(volumes[i], volumes[:i] if i > 0 else []):
                if fill_value is not None:
                    result[i] = fill_value
                else:
                    result[i] = float('nan')

        return result

    def filter_dataframe(
        self,
        df: pd.DataFrame,
        volume_column: str = "volume",
        target_columns: List[str] = None
    ) -> pd.DataFrame:
        """
        Filter DataFrame rows based on volume

        Returns:
            DataFrame with low-volume rows set to NaN in target columns
        """
        result = df.copy()
        if target_columns is None:
            target_columns = [c for c in df.columns if c != volume_column]

        volumes = df[volume_column].tolist()

        for col in target_columns:
            if col in result.columns:
                result[col] = self.filter_by_volume(volumes, result[col].tolist())

        return result
