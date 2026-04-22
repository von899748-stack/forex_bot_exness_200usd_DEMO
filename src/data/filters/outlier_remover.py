"""Outlier removal using Z-score or IQR"""
import numpy as np
from typing import List, Tuple
import pandas as pd


class OutlierRemover:
    """Remove outliers from price/volume data"""

    def __init__(self, threshold: float = 3.0, method: str = "zscore"):
        """
        Args:
            threshold: Z-score threshold or IQR multiplier
            method: 'zscore' or 'iqr'
        """
        self.threshold = threshold
        self.method = method

    def filter(self, data: List[float]) -> List[float]:
        """Return filtered data with outliers replaced by NaN"""
        if len(data) < 3:
            return data

        data_arr = np.array(data)
        mask = self._detect_outliers(data_arr)

        # Replace outliers with NaN (interpolate later)
        filtered = data_arr.copy()
        filtered[mask] = np.nan

        return filtered.tolist()

    def _detect_outliers(self, data: np.ndarray) -> np.ndarray:
        """Boolean mask of outliers"""
        if self.method == "zscore":
            mean = np.nanmean(data)
            std = np.nanstd(data)
            if std == 0:
                return np.zeros_like(data, dtype=bool)
            z_scores = np.abs((data - mean) / std)
            return z_scores > self.threshold
        else:  # IQR method
            q1 = np.nanpercentile(data, 25)
            q3 = np.nanpercentile(data, 75)
            iqr = q3 - q1
            lower = q1 - self.threshold * iqr
            upper = q3 + self.threshold * iqr
            return (data < lower) | (data > upper)

    def filter_dataframe(
        self,
        df: pd.DataFrame,
        columns: List[str]
    ) -> pd.DataFrame:
        """Filter outliers from specified DataFrame columns"""
        result = df.copy()
        for col in columns:
            if col in result.columns:
                filtered = self.filter(result[col].tolist())
                result[col] = filtered
        return result
