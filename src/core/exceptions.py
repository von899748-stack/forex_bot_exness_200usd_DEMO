"""Custom exceptions for the trading bot"""


class TradingBotError(Exception):
    """Base exception for all trading bot errors"""
    pass


class ConfigurationError(TradingBotError):
    """Configuration related errors"""
    pass


class ConnectionError(TradingBotError):
    """Connection errors (MT5, DB, Redis)"""
    pass


class TradingError(TradingBotError):
    """Trading operation errors"""
    pass


class InsufficientFundsError(TradingError):
    """Insufficient funds for trade"""
    pass


class MarketClosedError(TradingError):
    """Market is closed"""
    pass


class SymbolNotFoundError(TradingError):
    """Symbol not found"""
    pass


class OrderRejectedError(TradingError):
    """Order rejected by broker"""
    pass


class InvalidRiskError(TradingError):
    """Invalid risk parameters"""
    pass


class MaxLossReachedError(TradingError):
    """Maximum consecutive losses reached - bot stopped"""
    pass


class DataSourceError(TradingBotError):
    """Data source errors"""
    pass


class AgentError(TradingBotError):
    """Agent-specific errors"""
    pass


class StrategyError(AgentError):
    """Strategy errors"""
    pass


class RiskError(AgentError):
    """Risk management errors"""
    pass


class LearningError(AgentError):
    """Learning module errors"""
    pass


class NotificationError(TradingBotError):
    """Notification errors (Telegram, etc)"""
    pass


class ValidationError(TradingBotError):
    """Data validation errors"""
    pass
