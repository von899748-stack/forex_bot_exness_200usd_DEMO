"""Smoothing filter using moving average or median"""
import numpy as np
import pandas as pd
from typing import List, Optional


class SmoothFilter:
    """Apply smoothing to time series data"""

    def __init__(self, window: int = 5, method: str = "sma"):
        """
        Args:
            window: Window size for smoothing
            method: 'sma' (simple MA), 'ema' (exponential MA), 'median'
        """
        self.window = window
        self.method = method

    def filter(self, data: List[float]) -> List[float]:
        """Return smoothed data"""
        if len(data) < self.window:
            return data

        series = pd.Series(data)

        if self.method == "sma":
            smoothed = series.rolling(window=self.window, center=True, min_periods=1).mean()
        elif self.method == "ema":
            smoothed = series.ewm(span=self.window, adjust=False).mean()
        elif self.method == "median":
            smoothed = series.rolling(window=self.window, center=True, min_periods=1).median()
        else:
            smoothed = series

        return smoothed.tolist()

    def filter_dataframe(
        self,
        df: pd.DataFrame,
        columns: List[str],
        new_suffix: str = "_smooth"
    ) -> pd.DataFrame:
        """Add smoothed columns to DataFrame"""
        result = df.copy()
        for col in columns:
            if col in result.columns:
                result[f"{col}{new_suffix}"] = self.filter(result[col].tolist())
        return result
