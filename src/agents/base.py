"""Base agent class - all agents inherit from this"""
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime, time
import uuid

from ...core.types import Trade, Signal, AgentStatus, Side, MarketData, OrderRequest, OrderResponse
from ...core.logger import get_agent_logger
from ...core.event_bus import EventBus, EventType
from ...core.exceptions import AgentError
from ...config.base import BaseConfig


class BaseAgent(ABC):
    """
    Abstract base class for all trading agents

    Each agent runs in a loop:
    1. Fetch market data
    2. Analyze (perception)
    3. Generate signal (strategy)
    4. Calculate risk
    5. Execute if signal strong enough
    6. Monitor and learn from results
    """

    def __init__(
        self,
        agent_id: int,
        config: BaseConfig,
        symbol: str,
        event_bus: Optional[EventBus] = None
    ):
        self.agent_id = agent_id
        self.config = config
        self.symbol = symbol
        self.event_bus = event_bus or EventBus()
        self.logger = get_agent_logger(agent_id)

        # State
        self.state = None  # Will be set in initialize
        self.current_trade: Optional[Trade] = None
        self.equity = config.risk.total_capital / config.risk.max_agents  # Per-agent capital
        self.peak_equity = self.equity
        self.drawdown = 0.0
        self.consecutive_losses = 0
        self.last_signal_time: Optional[datetime] = None

        # Sub-modules (initialized in subclass)
        self.perception = None
        self.strategy = None
        self.risk_manager = None
        self.executor = None
        self.learner = None
        self.memory = None

        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def initialize(self) -> bool:
        """Initialize agent components"""
        try:
            self._setup_perception()
            self._setup_strategy()
            self._setup_risk_manager()
            self._setup_executor()
            self._setup_memory()
            self._setup_learner()
            self.state = AgentState.READY
            self.logger.info(f"Agent {self.agent_id} initialized for {self.symbol}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize agent {self.agent_id}: {e}")
            self.state = AgentState.ERROR
            return False

    @abstractmethod
    def _setup_perception(self):
        """Set up perception modules"""
        pass

    @abstractmethod
    def _setup_strategy(self):
        """Set up strategy modules"""
        pass

    def _setup_risk_manager(self):
        """Set up risk management (can be overridden)"""
        from .risk.per_agent_risk import PerAgentRiskManager
        self.risk_manager = PerAgentRiskManager(self.config)
        self.logger.info("Risk manager initialized")

    def _setup_executor(self):
        """Set up order executor (can be overridden)"""
        from ..execution.broker.demo_broker import DemoBroker
        self.executor = DemoBroker(self.config)
        self.logger.info("Executor initialized")

    def _setup_memory(self):
        """Set up memory systems (can be overridden)"""
        from .memory.agent_memory import AgentMemory
        self.memory = AgentMemory(self.agent_id)
        self.logger.info("Memory initialized")

    def _setup_learner(self):
        """Set up learning modules (can be overridden)"""
        from .execution.learning.loss_minimizer import LossMinimizer
        self.learner = LossMinimizer(self.config)
        self.logger.info("Learner initialized")

    async def run(self):
        """Main agent loop"""
        if not await self.initialize():
            return

        self._running = True
        self.state = AgentState.TRADING
        self.logger.info(f"Agent {self.agent_id} started")

        while self._running:
            try:
                # Check trading hours
                if not self._is_trading_time():
                    await asyncio.sleep(60)
                    continue

                # Check loss limit
                if self.consecutive_losses >= self.config.risk.max_consecutive_losses:
                    self.state = AgentState.STOPPED
                    self.logger.warning(f"Agent stopped: max consecutive losses reached")
                    await self.event_bus.publish(Event(
                        type=EventType.CONSECUTIVE_LOSSES,
                        source=f"agent_{self.agent_id}",
                        data={"consecutive_losses": self.consecutive_losses}
                    ))
                    break

                # Fetch market data
                market_data = await self._fetch_market_data()
                if market_data is None:
                    await asyncio.sleep(5)
                    continue

                # Analyze market (perception)
                analysis = await self.perception.analyze(market_data)

                # Generate signal (strategy)
                signal = await self.strategy.generate_signal(analysis)

                # Calculate dynamic risk
                risk = self.risk_manager.calculate_risk(
                    equity=self.equity,
                    peak_equity=self.peak_equity,
                    consecutive_losses=self.consecutive_losses,
                    signal_confidence=signal.confidence if signal else 0.0
                )

                # Execute signal
                if signal and signal.confidence > 0.5:
                    await self._execute_signal(signal, risk)

                # Learn from recent trades
                await self._learn()

                # Wait before next iteration
                await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"Error in agent {self.agent_id} loop: {e}")
                self.state = AgentState.ERROR
                await asyncio.sleep(5)

        self.logger.info(f"Agent {self.agent_id} stopped")

    async def stop(self):
        """Stop the agent"""
        self._running = False
        if self._task:
            self._task.cancel()
        self.state = AgentState.STOPPED
        self.logger.info(f"Agent {self.agent_id} stop requested")

    @abstractmethod
    async def _fetch_market_data(self) -> Optional[MarketData]:
        """Fetch latest market data for the symbol"""
        pass

    async def _execute_signal(self, signal: Signal, risk: float):
        """Execute a trading signal with calculated risk"""
        try:
            # Calculate lot size
            lot_size = self.risk_manager.calculate_lot_size(
                capital=self.equity,
                risk_percent=risk,
                sl_pips=signal.stop_loss_pips,
                pip_value=self._get_pip_value()
            )

            # Create order
            side = Side.BUY if signal.is_bullish else Side.SELL
            order = OrderRequest(
                symbol=self.symbol,
                side=side,
                order_type=OrderRequest.OrderType.MARKET,
                quantity=lot_size,
                stop_loss=self._calculate_stop_loss_price(signal),
                take_profit=self._calculate_take_profit_price(signal),
                agent_id=self.agent_id,
                metadata={"signal_id": str(uuid.uuid4()), "confidence": signal.confidence}
            )

            # Send order
            response: OrderResponse = await self.executor.send_order(order)

            if response.status == "filled":
                trade = Trade(
                    agent_id=self.agent_id,
                    symbol=self.symbol,
                    side=order.side,
                    quantity=order.filled_quantity,
                    entry_price=response.avg_fill_price,
                    stop_loss=order.stop_loss,
                    take_profit=order.take_profit,
                    reason=f"signal_{signal.type}"
                )
                self.current_trade = trade
                self.memory.record_trade(trade)
                self.logger.info(f"Trade opened: {trade.side} {trade.quantity} lots at {trade.entry_price}")

                # Publish event
                await self.event_bus.publish(Event(
                    type=EventType.TRADE_OPENED,
                    source=f"agent_{self.agent_id}",
                    data=trade.__dict__
                ))

        except Exception as e:
            self.logger.error(f"Failed to execute signal: {e}")

    def _calculate_stop_loss_price(self, signal: Signal) -> float:
        """Convert pip-based SL to price (placeholder)"""
        return 0.0

    def _calculate_take_profit_price(self, signal: Signal) -> float:
        """Convert pip-based TP to price (placeholder)"""
        return 0.0

    def _get_pip_value(self) -> float:
        """Get pip value for the symbol"""
        values = {
            "EURUSD": 10.0,
            "GBPUSD": 10.0,
            "XAUUSD": 1.0,
        }
        return values.get(self.symbol, 10.0)

    def _is_trading_time(self) -> bool:
        """Check if within trading hours"""
        from ...core.utils import is_trading_time
        now = datetime.utcnow()
        return is_trading_time(
            now,
            start_hour=self.config.trading_hours.start_hour,
            end_hour=self.config.trading_hours.end_hour
        )

    async def _learn(self):
        """Learn from recent trade outcomes"""
        if self.learner and self.current_trade and self.current_trade.exit_time:
            await self.learner.process_trade(self.current_trade)
            self.current_trade = None

    def update_equity(self, new_equity: float):
        """Update equity and drawdown"""
        self.equity = new_equity
        self.peak_equity = max(self.peak_equity, new_equity)
        self.drawdown = (self.peak_equity - new_equity) / self.peak_equity if self.peak_equity > 0 else 0

    def record_loss(self):
        """Record a loss, increment consecutive losses"""
        self.consecutive_losses += 1
        self.update_equity(self.equity * 0.99)

    def record_win(self):
        """Record a win, reset consecutive losses"""
        self.consecutive_losses = 0
        self.update_equity(self.equity * 1.01)

    def get_status(self) -> AgentStatus:
        """Get current agent status"""
        return AgentStatus(
            agent_id=self.agent_id,
            state=self.state,
            current_trade=self.current_trade,
            equity=self.equity,
            peak_equity=self.peak_equity,
            drawdown=self.drawdown,
            consecutive_losses=self.consecutive_losses,
            last_signal_time=self.last_signal_time,
            metrics={}
        )
