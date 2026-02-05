"""
Technical Indicators Module
RSI calculation and divergence detection for Trading Alert Bot
"""
from typing import List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
import numpy as np

from utils.logger import setup_logger

logger = setup_logger(__name__, "indicators.log")


class DivergenceType(Enum):
    """Types of RSI divergence"""
    NONE = "none"
    BULLISH_REGULAR = "bullish_regular"      # Price lower low, RSI higher low → Reversal up
    BEARISH_REGULAR = "bearish_regular"      # Price higher high, RSI lower high → Reversal down
    BULLISH_HIDDEN = "bullish_hidden"        # Price higher low, RSI lower low → Continuation up
    BEARISH_HIDDEN = "bearish_hidden"        # Price lower high, RSI higher high → Continuation down


@dataclass
class DivergenceResult:
    """Result of divergence detection"""
    type: DivergenceType
    price_point1: Tuple[int, float]  # (index, price) of first point
    price_point2: Tuple[int, float]  # (index, price) of second point
    rsi_point1: Tuple[int, float]    # (index, rsi) of first point
    rsi_point2: Tuple[int, float]    # (index, rsi) of second point
    strength: float                   # How strong the divergence is (0-1)
    
    def __str__(self) -> str:
        type_names = {
            DivergenceType.BULLISH_REGULAR: "🟢 상승 다이버전스 (추세 반전)",
            DivergenceType.BEARISH_REGULAR: "🔴 하락 다이버전스 (추세 반전)",
            DivergenceType.BULLISH_HIDDEN: "🟢 히든 상승 다이버전스 (추세 지속)",
            DivergenceType.BEARISH_HIDDEN: "🔴 히든 하락 다이버전스 (추세 지속)",
            DivergenceType.NONE: "다이버전스 없음",
        }
        return type_names.get(self.type, str(self.type))


def calculate_rsi(closes: List[float], period: int = 14) -> List[float]:
    """
    Calculate RSI (Relative Strength Index)
    
    Args:
        closes: List of closing prices
        period: RSI period (default 14)
    
    Returns:
        List of RSI values (first `period` values will be NaN)
    """
    if len(closes) < period + 1:
        logger.warning(f"Not enough data for RSI calculation. Need {period + 1}, got {len(closes)}")
        return []
    
    closes_arr = np.array(closes, dtype=float)
    
    # Calculate price changes
    deltas = np.diff(closes_arr)
    
    # Separate gains and losses
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    # Calculate initial average gain/loss
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    rsi_values = [np.nan] * period
    
    # Calculate RSI for each subsequent period using Wilder's smoothing
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        rsi_values.append(rsi)
    
    return rsi_values


def find_peaks(data: List[float], order: int = 5) -> List[int]:
    """Find local maxima in data"""
    peaks = []
    for i in range(order, len(data) - order):
        if np.isnan(data[i]):
            continue
        is_peak = True
        for j in range(1, order + 1):
            if data[i] <= data[i - j] or data[i] <= data[i + j]:
                is_peak = False
                break
        if is_peak:
            peaks.append(i)
    return peaks


def find_troughs(data: List[float], order: int = 5) -> List[int]:
    """Find local minima in data"""
    troughs = []
    for i in range(order, len(data) - order):
        if np.isnan(data[i]):
            continue
        is_trough = True
        for j in range(1, order + 1):
            if data[i] >= data[i - j] or data[i] >= data[i + j]:
                is_trough = False
                break
        if is_trough:
            troughs.append(i)
    return troughs


def detect_divergence(
    closes: List[float],
    rsi_values: List[float],
    lookback: int = 50,
    min_bars_between: int = 5,
    detect_hidden: bool = True
) -> Optional[DivergenceResult]:
    """
    Detect RSI divergence
    
    Args:
        closes: List of closing prices
        rsi_values: List of RSI values
        lookback: Number of bars to look back for divergence
        min_bars_between: Minimum bars between two points
        detect_hidden: Whether to detect hidden divergence
    
    Returns:
        DivergenceResult if divergence found, None otherwise
    """
    if len(closes) < lookback or len(rsi_values) < lookback:
        return None
    
    # Use only the lookback period
    recent_closes = closes[-lookback:]
    recent_rsi = rsi_values[-lookback:]
    
    # Find peaks and troughs
    price_peaks = find_peaks(recent_closes, order=3)
    price_troughs = find_troughs(recent_closes, order=3)
    rsi_peaks = find_peaks(recent_rsi, order=3)
    rsi_troughs = find_troughs(recent_rsi, order=3)
    
    # Check for bearish regular divergence (price higher high, RSI lower high)
    if len(price_peaks) >= 2 and len(rsi_peaks) >= 2:
        p1, p2 = price_peaks[-2], price_peaks[-1]
        
        if p2 - p1 >= min_bars_between:
            # Find corresponding RSI peaks
            r1 = min(rsi_peaks, key=lambda x: abs(x - p1), default=None)
            r2 = min(rsi_peaks, key=lambda x: abs(x - p2), default=None)
            
            if r1 is not None and r2 is not None and r1 != r2:
                # Price makes higher high, RSI makes lower high
                if recent_closes[p2] > recent_closes[p1] and recent_rsi[r2] < recent_rsi[r1]:
                    strength = (recent_rsi[r1] - recent_rsi[r2]) / recent_rsi[r1]
                    return DivergenceResult(
                        type=DivergenceType.BEARISH_REGULAR,
                        price_point1=(p1, recent_closes[p1]),
                        price_point2=(p2, recent_closes[p2]),
                        rsi_point1=(r1, recent_rsi[r1]),
                        rsi_point2=(r2, recent_rsi[r2]),
                        strength=min(abs(strength), 1.0)
                    )
    
    # Check for bullish regular divergence (price lower low, RSI higher low)
    if len(price_troughs) >= 2 and len(rsi_troughs) >= 2:
        p1, p2 = price_troughs[-2], price_troughs[-1]
        
        if p2 - p1 >= min_bars_between:
            r1 = min(rsi_troughs, key=lambda x: abs(x - p1), default=None)
            r2 = min(rsi_troughs, key=lambda x: abs(x - p2), default=None)
            
            if r1 is not None and r2 is not None and r1 != r2:
                # Price makes lower low, RSI makes higher low
                if recent_closes[p2] < recent_closes[p1] and recent_rsi[r2] > recent_rsi[r1]:
                    strength = (recent_rsi[r2] - recent_rsi[r1]) / (100 - recent_rsi[r1])
                    return DivergenceResult(
                        type=DivergenceType.BULLISH_REGULAR,
                        price_point1=(p1, recent_closes[p1]),
                        price_point2=(p2, recent_closes[p2]),
                        rsi_point1=(r1, recent_rsi[r1]),
                        rsi_point2=(r2, recent_rsi[r2]),
                        strength=min(abs(strength), 1.0)
                    )
    
    # Hidden divergence detection
    if detect_hidden:
        # Bullish hidden: Price higher low, RSI lower low (continuation)
        if len(price_troughs) >= 2 and len(rsi_troughs) >= 2:
            p1, p2 = price_troughs[-2], price_troughs[-1]
            
            if p2 - p1 >= min_bars_between:
                r1 = min(rsi_troughs, key=lambda x: abs(x - p1), default=None)
                r2 = min(rsi_troughs, key=lambda x: abs(x - p2), default=None)
                
                if r1 is not None and r2 is not None and r1 != r2:
                    if recent_closes[p2] > recent_closes[p1] and recent_rsi[r2] < recent_rsi[r1]:
                        strength = (recent_rsi[r1] - recent_rsi[r2]) / recent_rsi[r1]
                        return DivergenceResult(
                            type=DivergenceType.BULLISH_HIDDEN,
                            price_point1=(p1, recent_closes[p1]),
                            price_point2=(p2, recent_closes[p2]),
                            rsi_point1=(r1, recent_rsi[r1]),
                            rsi_point2=(r2, recent_rsi[r2]),
                            strength=min(abs(strength), 1.0)
                        )
        
        # Bearish hidden: Price lower high, RSI higher high (continuation)
        if len(price_peaks) >= 2 and len(rsi_peaks) >= 2:
            p1, p2 = price_peaks[-2], price_peaks[-1]
            
            if p2 - p1 >= min_bars_between:
                r1 = min(rsi_peaks, key=lambda x: abs(x - p1), default=None)
                r2 = min(rsi_peaks, key=lambda x: abs(x - p2), default=None)
                
                if r1 is not None and r2 is not None and r1 != r2:
                    if recent_closes[p2] < recent_closes[p1] and recent_rsi[r2] > recent_rsi[r1]:
                        strength = (recent_rsi[r2] - recent_rsi[r1]) / (100 - recent_rsi[r1])
                        return DivergenceResult(
                            type=DivergenceType.BEARISH_HIDDEN,
                            price_point1=(p1, recent_closes[p1]),
                            price_point2=(p2, recent_closes[p2]),
                            rsi_point1=(r1, recent_rsi[r1]),
                            rsi_point2=(r2, recent_rsi[r2]),
                            strength=min(abs(strength), 1.0)
                        )
    
    return None


def get_rsi_status(rsi: float) -> str:
    """Get human-readable RSI status"""
    if rsi >= 70:
        return "🔴 과매수 (Overbought)"
    elif rsi >= 60:
        return "🟠 매수 우세"
    elif rsi >= 40:
        return "⚪ 중립"
    elif rsi >= 30:
        return "🔵 매도 우세"
    else:
        return "🟢 과매도 (Oversold)"


if __name__ == "__main__":
    # Test RSI calculation
    test_prices = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 
                   46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41,
                   46.22, 45.64, 46.21, 46.25, 45.71, 46.45, 45.78]
    
    rsi = calculate_rsi(test_prices, period=14)
    print(f"RSI values: {[f'{r:.2f}' if not np.isnan(r) else 'NaN' for r in rsi]}")
    
    if rsi and not np.isnan(rsi[-1]):
        print(f"Current RSI: {rsi[-1]:.2f}")
        print(f"Status: {get_rsi_status(rsi[-1])}")
