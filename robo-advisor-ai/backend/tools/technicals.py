"""
RoboAdvisor AI — Technical Indicators
Computes RSI, MACD, Bollinger Bands, and moving averages from price data.
"""

import numpy as np
from typing import Optional


class TechnicalAnalysis:
    """Calculate technical indicators from price history."""
    
    def __init__(self, close_prices: list[float]):
        """
        Args:
            close_prices: List of daily closing prices (oldest first)
        """
        self.close = np.array(close_prices, dtype=float)
    
    def rsi(self, period: int = 14) -> Optional[float]:
        """
        Relative Strength Index (0-100).
        > 70 = overbought, < 30 = oversold.
        """
        if len(self.close) < period + 1:
            return None
        
        deltas = np.diff(self.close)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return round(100.0 - (100.0 / (1.0 + rs)), 2)
    
    def macd(
        self, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Optional[dict]:
        """
        MACD (Moving Average Convergence Divergence).
        Returns macd line, signal line, and histogram.
        """
        if len(self.close) < slow + signal:
            return None
        
        ema_fast = self._ema(self.close, fast)
        ema_slow = self._ema(self.close, slow)
        
        macd_line = ema_fast - ema_slow
        signal_line = self._ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return {
            "macd": round(float(macd_line[-1]), 4),
            "signal": round(float(signal_line[-1]), 4),
            "histogram": round(float(histogram[-1]), 4),
        }
    
    def sma(self, period: int) -> Optional[float]:
        """Simple Moving Average."""
        if len(self.close) < period:
            return None
        return round(float(np.mean(self.close[-period:])), 2)
    
    def bollinger_bands(self, period: int = 20, std_dev: float = 2.0) -> Optional[dict]:
        """
        Bollinger Bands.
        Returns upper, middle (SMA), and lower bands.
        """
        if len(self.close) < period:
            return None
        
        window = self.close[-period:]
        mid = float(np.mean(window))
        std = float(np.std(window))
        
        return {
            "upper": round(mid + std_dev * std, 2),
            "mid": round(mid, 2),
            "lower": round(mid - std_dev * std, 2),
        }
    
    def all_indicators(self) -> dict:
        """Compute all indicators at once. Returns a flat dict."""
        macd_data = self.macd()
        bb = self.bollinger_bands()
        
        return {
            "rsi_14": self.rsi(14),
            "macd": macd_data["macd"] if macd_data else None,
            "macd_signal": macd_data["signal"] if macd_data else None,
            "macd_histogram": macd_data["histogram"] if macd_data else None,
            "sma_50": self.sma(50),
            "sma_200": self.sma(200),
            "bollinger_upper": bb["upper"] if bb else None,
            "bollinger_mid": bb["mid"] if bb else None,
            "bollinger_lower": bb["lower"] if bb else None,
        }
    
    @staticmethod
    def _ema(data: np.ndarray, period: int) -> np.ndarray:
        """Exponential Moving Average."""
        multiplier = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = (data[i] * multiplier) + (ema[i - 1] * (1 - multiplier))
        return ema
