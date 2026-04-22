"""Base configuration for all modes"""
import os
from dataclasses import dataclass, field
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = os.getenv("TIMESCALEDB_HOST", "localhost")
    port: int = int(os.getenv("TIMESCALEDB_PORT", "5432"))
    database: str = os.getenv("TIMESCALEDB_DB", "forex_bot")
    user: str = os.getenv("TIMESCALEDB_USER", "postgres")
    password: str = os.getenv("TIMESCALEDB_PASSWORD", "postgres")
    pool_size: int = 10
    max_overflow: int = 20


@dataclass
class RedisConfig:
    """Redis configuration"""
    url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    enabled: bool = os.getenv("USE_REDIS", "False").lower() == "true"


@dataclass
class MT5Config:
    """MetaTrader 5 configuration"""
    login: int = int(os.getenv("MT5_LOGIN", "0"))
    password: str = os.getenv("MT5_PASSWORD", "")
    server: str = os.getenv("MT5_SERVER", "Exness-Demo")
    path: str = os.getenv("MT5_PATH", "")


@dataclass
class TelegramConfig:
    """Telegram bot configuration"""
    bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    enabled: bool = bool(os.getenv("TELEGRAM_BOT_TOKEN"))


@dataclass
class RiskConfig:
    """Risk management configuration"""
    total_capital: float = float(os.getenv("TOTAL_CAPITAL", "200"))
    max_agents: int = int(os.getenv("MAX_AGENTS", "5"))
    risk_base: float = float(os.getenv("RISK_BASE", "0.01"))
    dynamic_risk: bool = os.getenv("DYNAMIC_RISK", "True").lower() == "true"
    max_risk: float = float(os.getenv("MAX_RISK", "0.02"))
    min_risk: float = float(os.getenv("MIN_RISK", "0.005"))
    drawdown_limit: float = 0.10  # 10% drawdown triggers risk reduction
    max_consecutive_losses: int = int(os.getenv("MAX_CONSECUTIVE_LOSSES", "3"))
    loss_impact: float = 0.002  # Each loss reduces risk by 0.2%


@dataclass
class TradingHoursConfig:
    """Trading hours configuration"""
    start_hour: int = int(os.getenv("TRADING_START", "7"))
    end_hour: int = int(os.getenv("TRADING_END", "22"))
    timezone: str = "UTC"
    include_weekends: bool = False


@dataclass
class SymbolConfig:
    """Symbol configuration"""
    symbols: List[str] = field(default_factory=lambda: ["EURUSD", "GBPUSD", "XAUUSD"])
    default_pip_value: float = 10.0  # For EURUSD, 1 pip = $10 per standard lot
    default_min_lot: float = 0.01
    default_max_lot: float = 100.0
    default_lot_step: float = 0.01


@dataclass
class FilterConfig:
    """Data filter configuration"""
    enable_outlier_removal: bool = True
    outlier_threshold: float = 3.0  # Z-score threshold
    enable_smoothing: bool = True
    smoothing_window: int = 5
    enable_volume_filter: bool = True
    min_volume_threshold: float = 0.1  # Minimum volume as fraction of average


@dataclass
class LearningConfig:
    """Machine learning configuration"""
    enable_noise_filter: bool = os.getenv("ENABLE_NOISE_FILTER", "True").lower() == "true"
    noise_spread_threshold: float = 2.0  # Spread multiplier over normal
    noise_slippage_threshold: float = 5.0  # Slippage in pips
    enable_drift_detection: bool = True
    drift_detection_window: int = 50  # Trades to analyze for drift
    drift_p_value: float = 0.05  # Statistical significance
    enable_self_correction: bool = True
    correction_learning_rate: float = 0.1
    min_trades_for_learning: int = 20


@dataclass
class DashboardConfig:
    """Dashboard configuration"""
    enabled: bool = True
    port: int = int(os.getenv("DASHBOARD_PORT", "8501"))
    host: str = "0.0.0.0"
    update_interval: float = 1.0  # seconds


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = os.getenv("LOG_LEVEL", "INFO")
    rotation: str = os.getenv("LOG_ROTATION", "1 day")
    retention: str = os.getenv("LOG_RETENTION", "7 days")
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class BaseConfig:
    """Base configuration shared by all modes"""
    # Sub-configs
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    mt5: MT5Config = field(default_factory=MT5Config)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    trading_hours: TradingHoursConfig = field(default_factory=TradingHoursConfig)
    symbols: SymbolConfig = field(default_factory=SymbolConfig)
    filters: FilterConfig = field(default_factory=FilterConfig)
    learning: LearningConfig = field(default_factory=LearningConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # Mode-specific
    mode: str = "base"  # 'live', 'demo', 'paper', 'backtest'
    broker_mode: str = os.getenv("BROKER_MODE", "demo")

    # Backtest specific (overridden in backtest config)
    backtest_start: Optional[str] = None
    backtest_end: Optional[str] = None

    @classmethod
    def from_env(cls) -> "BaseConfig":
        """Create config from environment variables"""
        return cls()
