"""Technical analysis perception module"""
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import ta  # technical analysis library

from ...core.types import MarketData
from ...core.logger import get_agent_logger


class TechnicalPerception:
    """Analyzes price action using technical indicators"""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.logger = get_agent_logger(0)
        self.data_buffer = pd.DataFrame()

    async def analyze(self, market_data: MarketData) -> Dict[str, Any]:
        """
        Analyze market data with technical indicators

        Returns:
            Dictionary with indicators and signals
        """
        try:
            # Add new data point to buffer
            new_row = {
                'timestamp': market_data.timestamp,
                'open': market_data.open,
                'high': market_data.high,
                'low': market_data.low,
                'close': market_data.close,
                'volume': market_data.volume,
                'spread': market_data.spread,
            }
            self.data_buffer = pd.concat([
                self.data_buffer,
                pd.DataFrame([new_row])
            ], ignore_index=True)

            # Keep buffer manageable (last 1000 bars)
            if len(self.data_buffer) > 1000:
                self.data_buffer = self.data_buffer.iloc[-1000:]

            # Calculate indicators if enough data
            analysis = {}
            if len(self.data_buffer) >= 50:
                analysis = self._calculate_indicators()

            return analysis

        except Exception as e:
            self.logger.error(f"Technical analysis error: {e}")
            return {}

    def _calculate_indicators(self) -> Dict[str, Any]:
        """Calculate technical indicators"""
        df = self.data_buffer.copy()
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']

        analysis = {}

        # Moving averages
        analysis['sma_20'] = ta.trend.sma_indicator(close, window=20).iloc[-1]
        analysis['sma_50'] = ta.trend.sma_indicator(close, window=50).iloc[-1]
        analysis['ema_12'] = ta.trend.ema_indicator(close, window=12).iloc[-1]
        analysis['ema_26'] = ta.trend.ema_indicator(close, window=26).iloc[-1]

        # MACD
        macd = ta.trend.MACD(close)
        analysis['macd'] = macd.macd().iloc[-1]
        analysis['macd_signal'] = macd.macd_signal().iloc[-1]
        analysis['macd_hist'] = macd.macd_diff().iloc[-1]

        # RSI
        analysis['rsi'] = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]

        # Bollinger Bands
        bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
        analysis['bb_upper'] = bb.bollinger_hband().iloc[-1]
        analysis['bb_lower'] = bb.bollinger_lband().iloc[-1]
        analysis['bb_middle'] = bb.bollinger_mband().iloc[-1]

        # Stochastic
        stoch = ta.momentum.StochasticOscillator(high, low, close, window=14)
        analysis['stoch_k'] = stoch.stoch().iloc[-1]
        analysis['stoch_d'] = stoch.stoch_signal().iloc[-1]

        # ATR (volatility)
        analysis['atr'] = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range().iloc[-1]

        # Volume indicators
        analysis['volume_sma'] = volume.rolling(20).mean().iloc[-1]
        analysis['volume_ratio'] = volume.iloc[-1] / analysis['volume_sma'] if analysis['volume_sma'] > 0 else 1.0

        # Price action
        analysis['close_change'] = close.iloc[-1] - close.iloc[-2] if len(close) >= 2 else 0
        analysis['high_low_range'] = high.iloc[-1] - low.iloc[-1]

        # Trend detection
        analysis['trend'] = self._detect_trend(close, analysis['sma_20'], analysis['sma_50'])

        return analysis

    def _detect_trend(self, close: pd.Series, sma20: float, sma50: float) -> str:
        """Detect market trend"""
        if len(close) < 50:
            return "sideways"

        # Simple trend detection
        current = close.iloc[-1]
        past = close.iloc[-20]

        if current > sma20 and sma20 > sma50 and current > past:
            return "uptrend"
        elif current < sma20 and sma20 < sma50 and current < past:
            return "downtrend"
        else:
            return "sideways"
