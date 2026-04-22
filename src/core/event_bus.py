"""Event bus for inter-component communication"""
import threading
from typing import Callable, Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from .redis_client import RedisClient


class EventType(str, Enum):
    """Event types for the system"""
    # Trading events
    TRADE_OPENED = "trade.opened"
    TRADE_CLOSED = "trade.closed"
    SIGNAL_GENERATED = "signal.generated"
    ORDER_PLACED = "order.placed"
    ORDER_FILLED = "order.filled"
    ORDER_REJECTED = "order.rejected"

    # Agent events
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_ERROR = "agent.error"

    # Risk events
    RISK_LIMIT_REACHED = "risk.limit_reached"
    DRAWDOWN_ALERT = "drawdown.alert"
    CONSECUTIVE_LOSSES = "consecutive_losses.alert"

    # System events
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    SYSTEM_ERROR = "system.error"

    # Learning events
    NOISE_TRADE_FILTERED = "noise.filtered"
    DRIFT_DETECTED = "drift.detected"
    MODEL_UPDATED = "model.updated"


@dataclass
class Event:
    """Event object"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = EventType.SYSTEM_START
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": self.data,
        }


class EventBus:
    """Event bus for pub/sub communication"""

    def __init__(self, redis_client: Optional[RedisClient] = None):
        self.redis_client = redis_client or RedisClient()
        self.enabled = self.redis_client.enabled
        self._local_subscribers: Dict[EventType, List[Callable]] = {}
        self._lock = threading.RLock()

    def publish(self, event: Event):
        """Publish event to Redis and local subscribers"""
        # Notify local subscribers
        with self._lock:
            callbacks = self._local_subscribers.get(event.type, []).copy()

        for callback in callbacks:
            try:
                callback(event)
            except Exception:
                pass

        # Publish to Redis if enabled
        if self.enabled:
            self.redis_client.publish(f"events:{event.type}", event.to_dict())

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """Subscribe to event type"""
        with self._lock:
            if event_type not in self._local_subscribers:
                self._local_subscribers[event_type] = []
            self._local_subscribers[event_type].append(callback)

        # Also subscribe to Redis if enabled
        if self.enabled:
            def redis_callback(data):
                try:
                    event = Event(
                        id=data.get("id", str(uuid.uuid4())),
                        type=EventType(data["type"]),
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        source=data.get("source", ""),
                        data=data.get("data", {}),
                    )
                    callback(event)
                except Exception:
                    pass

            self.redis_client.subscribe(f"events:{event_type}", redis_callback)

    def unsubscribe(self, event_type: EventType, callback: Callable):
        """Unsubscribe from event"""
        with self._lock:
            if event_type in self._local_subscribers:
                try:
                    self._local_subscribers[event_type].remove(callback)
                except ValueError:
                    pass
