"""Loss controller - monitors consecutive losses and shuts down bot if needed"""
from typing import Optional
from ...core.logger import get_agent_logger
from ...core.exceptions import MaxLossReachedError
from ...core.event_bus import EventBus, EventType
from ...config.base import BaseConfig


class LossController:
    """
    Monitors consecutive losses across agents and triggers global stop.
    Per spec: loss bộ đếm lỗ liên tiếp; tự động tắt bot sau 3 lệnh thua.
    """

    def __init__(self, config: BaseConfig, event_bus: Optional[EventBus] = None):
        self.config = config
        self.logger = get_agent_logger(0)
        self.event_bus = event_bus
        self.max_consecutive_losses = config.risk.max_consecutive_losses
        self._active = True
        self._consecutive_losses = 0
        self._total_trades = 0
        self._total_losses = 0

    def record_trade_result(self, is_loss: bool):
        """Record a trade result and update counters"""
        self._total_trades += 1
        if is_loss:
            self._consecutive_losses += 1
            self._total_losses += 1
        else:
            self._consecutive_losses = 0

        self.logger.debug(f"Loss count: {self._consecutive_losses}/{self.max_consecutive_losses}")

        if self._consecutive_losses >= self.max_consecutive_losses:
            self.trigger_global_stop()

    async def on_trade_closed(self, event):
        """Event handler for trade close"""
        is_loss = event.data.get("pnl", 0) < 0
        self.record_trade_result(is_loss)

        # Also check if we need to pause
        await self._check_and_pause()

    def trigger_global_stop(self):
        """Trigger immediate stop of all trading"""
        self.logger.critical(f"MAX_CONSECUTIVE_LOSSES ({self.max_consecutive_losses}) reached. Stopping bot.")
        self._active = False
        if self.event_bus:
            import asyncio
            asyncio.create_task(self.event_bus.publish(
                EventType.SYSTEM_STOP,
                "loss_controller",
                {"reason": "max_consecutive_losses", "count": self._consecutive_losses}
            ))
        raise MaxLossReachedError(f"Bot stopped after {self.max_consecutive_losses} consecutive losses")

    def reset(self):
        """Reset loss counter (after manual intervention or recovery)"""
        self.logger.info("Resetting loss controller")
        self._consecutive_losses = 0
        self._active = True

    @property
    def consecutive_losses(self) -> int:
        return self._consecutive_losses

    @property
    def is_active(self) -> bool:
        return self._active

    async def _check_and_pause(self):
        """Check if we should pause after losses"""
        if self._consecutive_losses >= self.max_consecutive_losses - 1:
            # One more loss and we stop - send warning
            if self.event_bus:
                await self.event_bus.publish(
                    EventType.CONSECUTIVE_LOSSES,
                    "loss_controller",
                    {
                        "consecutive_losses": self._consecutive_losses,
                        "warning": True,
                        "next_threshold": self.max_consecutive_losses
                    }
                )
