"""Telegram notification client"""
import asyncio
from typing import Optional, Dict, Any
import aiohttp

from ...core.logger import get_agent_logger
from ...config.base import TelegramConfig


class TelegramNotifier:
    """Sends notifications via Telegram bot"""

    def __init__(self, config: TelegramConfig):
        self.config = config
        self.logger = get_agent_logger(0)
        self.enabled = config.enabled
        self.bot_token = config.bot_token
        self.chat_id = config.chat_id
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def send_message(self, text: str, parse_mode: str = "HTML"):
        """Send a text message"""
        if not self.enabled or not self.bot_token or not self.chat_id:
            return

        await self._ensure_session()
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        try:
            async with self.session.post(url, json=payload) as resp:
                if resp.status != 200:
                    self.logger.error(f"Telegram send failed: {resp.status}")
        except Exception as e:
            self.logger.error(f"Telegram error: {e}")

    async def send_trade_notification(self, trade, pnl: Optional[float] = None):
        """Send trade open/close notification"""
        if not pnl:
            text = (
                f"📈 Trade Opened\n"
                f"Symbol: {trade.symbol}\n"
                f"Side: {trade.side}\n"
                f"Quantity: {trade.quantity}\n"
                f"Entry: {trade.entry_price}\n"
                f"SL: {trade.stop_loss}\n"
                f"TP: {trade.take_profit}"
            )
        else:
            emoji = "✅" if pnl > 0 else "❌"
            text = (
                f"{emoji} Trade Closed\n"
                f"Symbol: {trade.symbol}\n"
                f"Side: {trade.side}\n"
                f"Exit: {trade.exit_price}\n"
                f"P&L: ${pnl:.2f} ({trade.pnl_pct:.2f}%)\n"
                f"Reason: {trade.reason}"
            )
        await self.send_message(text)

    async def send_alert(self, title: str, message: str):
        """Send an alert message"""
        text = f"🚨 <b>{title}</b>\n{message}"
        await self.send_message(text)

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
