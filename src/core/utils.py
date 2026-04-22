"""Utility functions for trading calculations and validations"""
from datetime import datetime, time
from typing import Tuple
import numpy as np


def is_trading_time(
    current_time: datetime,
    start_hour: int = 7,
    end_hour: int = 22,
    days_of_week: list = None
) -> bool:
    """
    Check if current time is within trading hours

    Args:
        current_time: Current datetime
        start_hour: Trading start hour (UTC)
        end_hour: Trading end hour (UTC)
        days_of_week: List of allowed weekdays (0=Monday). None = all days

    Returns:
        True if within trading hours
    """
    if days_of_week is None:
        days_of_week = list(range(7))  # All days

    # Check day of week
    if current_time.weekday() not in days_of_week:
        return False

    # Check time
    current_hour = current_time.hour
    return start_hour <= current_hour < end_hour


def calculate_dynamic_risk(
    current_equity: float,
    peak_equity: float,
    drawdown_limit: float,
    base_risk: float,
    min_risk: float,
    max_risk: float,
    consecutive_losses: int = 0,
    loss_impact: float = 0.002  # Each loss reduces risk by 0.2%
) -> float:
    """
    Calculate dynamic risk based on equity curve and recent performance

    Formula:
    1. Drawdown scaling: if drawdown > 0, scale risk down linearly
    2. Loss streak scaling: each consecutive loss reduces risk
    3. Clamp between min_risk and max_risk

    Args:
        current_equity: Current account equity
        peak_equity: Highest recorded equity
        drawdown_limit: Max drawdown before risk reduction (e.g., 0.1 for 10%)
        base_risk: Base risk per trade (e.g., 0.01 for 1%)
        min_risk: Minimum allowed risk
        max_risk: Maximum allowed risk
        consecutive_losses: Number of consecutive losing trades
        loss_impact: Risk reduction per consecutive loss

    Returns:
        Adjusted risk multiplier
    """
    # Start with base risk
    risk = base_risk

    # Drawdown adjustment
    if peak_equity > 0:
        current_drawdown = (peak_equity - current_equity) / peak_equity
        if current_drawdown > 0:
            # Scale risk down as drawdown increases
            drawdown_factor = max(0, 1 - (current_drawdown / drawdown_limit))
            risk *= drawdown_factor

    # Consecutive losses adjustment
    if consecutive_losses > 0:
        loss_factor = max(0, 1 - (consecutive_losses * loss_impact))
        risk *= loss_factor

    # Clamp to min/max
    risk = max(min_risk, min(max_risk, risk))

    return risk


def calculate_lot_size(
    capital: float,
    risk_percent: float,
    sl_pips: float,
    pip_value_per_lot: float,
    min_lot: float = 0.01,
    max_lot: float = 100.0,
    lot_step: float = 0.01
) -> float:
    """
    Calculate position size in lots

    Formula:
    risk_amount = capital * risk_percent
    lot_size = risk_amount / (sl_pips * pip_value)

    Args:
        capital: Account capital
        risk_percent: Risk per trade as decimal (e.g., 0.01 = 1%)
        sl_pips: Stop loss in pips
        pip_value_per_lot: Value of 1 pip per standard lot
        min_lot: Minimum lot size
        max_lot: Maximum lot size
        lot_step: Lot size increment

    Returns:
        Position size in lots
    """
    if sl_pips <= 0 or pip_value_per_lot <= 0:
        return min_lot

    risk_amount = capital * risk_percent
    lot_size = risk_amount / (sl_pips * pip_value_per_lot)

    # Round to lot step
    lot_size = round(lot_size / lot_step) * lot_step

    # Clamp to min/max
    lot_size = max(min_lot, min(max_lot, lot_size))

    return lot_size


def calculate_pip_value(
    symbol: str,
    lot_size: float = 1.0,
    exchange_rate: float = 1.0
) -> float:
    """
    Calculate pip value for a given symbol and lot size

    For forex pairs:
    - XXX/YYY: pip = 0.0001, value = lot_size * 100000 * 0.0001 * exchange_rate
    - XXX/JPY: pip = 0.01, value = lot_size * 100000 * 0.01 / exchange_rate
    """
    if symbol.endswith("JPY"):
        pip_value = lot_size * 1000 * 0.01  # JPY pairs
        if exchange_rate > 0:
            pip_value /= exchange_rate
    else:
        pip_value = lot_size * 100000 * 0.0001  # Most other pairs
        if "USD" in symbol[:3]:
            pip_value *= exchange_rate

    return pip_value


def pips_to_price(
    current_price: float,
    pips: float,
    direction: str,
    symbol: str
) -> float:
    """
    Convert pips to price level

    Args:
        current_price: Current market price
        pips: Distance in pips
        direction: 'long' or 'short'
        symbol: Trading symbol

    Returns:
        Price level pips away
    """
    if symbol.endswith("JPY"):
        pip_size = 0.01
    else:
        pip_size = 0.0001

    if direction.lower() == 'long':
        return current_price - pips * pip_size  # SL below for long
    else:
        return current_price + pips * pip_size  # SL above for short


def price_to_pips(
    entry_price: float,
    target_price: float,
    symbol: str
) -> float:
    """
    Convert price difference to pips

    Args:
        entry_price: Entry price
        target_price: Target price (stop loss or take profit)
        symbol: Trading symbol

    Returns:
        Distance in pips
    """
    if symbol.endswith("JPY"):
        pip_size = 0.01
    else:
        pip_size = 0.0001

    diff = abs(target_price - entry_price)
    return diff / pip_size


def calculate_position_size_by_risk(
    account_balance: float,
    risk_percent: float,
    entry_price: float,
    stop_loss_price: float,
    symbol: str,
    min_lot: float = 0.01,
    max_lot: float = 100.0
) -> float:
    """
    Calculate position size based on monetary risk

    Args:
        account_balance: Total account balance
        risk_percent: Percentage of account to risk (e.g., 0.01 = 1%)
        entry_price: Entry price
        stop_loss_price: Stop loss price
        symbol: Trading symbol
        min_lot: Minimum lot size
        max_lot: Maximum lot size

    Returns:
        Lot size
    """
    risk_amount = account_balance * risk_percent
    pips_risk = price_to_pips(entry_price, stop_loss_price, symbol)
    pip_value = calculate_pip_value(symbol)

    if pips_risk == 0 or pip_value == 0:
        return min_lot

    lot_size = risk_amount / (pips_risk * pip_value)
    lot_size = max(min_lot, min(max_lot, lot_size))

    # Round to standard lot step
    lot_size = round(lot_size * 100) / 100

    return lot_size


def calculate_expected_value(
    win_rate: float,
    avg_win: float,
    avg_loss: float
) -> float:
    """
    Calculate expected value per trade

    EV = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
    """
    return (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss))


def calculate_kelly_criterion(
    win_rate: float,
    avg_win: float,
    avg_loss: float
) -> float:
    """
    Kelly Criterion for optimal bet sizing

    f* = p - (q / (win_loss_ratio))
    where p = win_rate, q = 1 - win_rate, win_loss_ratio = avg_win / avg_loss
    """
    if avg_loss == 0:
        return 0.0

    win_loss_ratio = avg_win / abs(avg_loss)
    p = win_rate
    q = 1 - win_rate

    kelly = p - (q / win_loss_ratio)
    return max(0.0, min(0.1, kelly))  # Cap at 10% for safety


def detect_outlier_zscore(data: list, threshold: float = 3.0) -> list:
    """
    Detect outliers using Z-score

    Returns:
        List of booleans indicating if each point is an outlier
    """
    if len(data) < 3:
        return [False] * len(data)

    mean = np.mean(data)
    std = np.std(data)

    if std == 0:
        return [False] * len(data)

    return [abs((x - mean) / std) > threshold for x in data]


def calculate_drawdown(equity_curve: list) -> Tuple[float, float]:
    """
    Calculate maximum drawdown and current drawdown

    Returns:
        (max_drawdown, current_drawdown) as percentages
    """
    if len(equity_curve) < 2:
        return 0.0, 0.0

    # Calculate running max
    peak = equity_curve[0]
    max_dd = 0.0
    current_dd = 0.0

    for equity in equity_curve:
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0
        current_dd = dd
        max_dd = max(max_dd, dd)

    return max_dd, current_dd


def calculate_sharpe_ratio(returns: list, risk_free_rate: float = 0.02) -> float:
    """
    Calculate Sharpe ratio (annualized)

    Assumes returns are daily
    """
    if len(returns) < 2:
        return 0.0

    mean_return = np.mean(returns)
    std_return = np.std(returns)

    if std_return == 0:
        return 0.0

    daily_sharpe = (mean_return - risk_free_rate / 252) / std_return
    return daily_sharpe * np.sqrt(252)  # Annualize


def round_to_lot_step(lot: float, step: float = 0.01) -> float:
    """Round lot size to valid increment"""
    return round(lot / step) * step
