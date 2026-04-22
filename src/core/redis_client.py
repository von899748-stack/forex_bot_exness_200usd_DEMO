"""Redis client for caching and pub/sub"""
import json
from typing import Optional, Any, Callable
import redis
from redis.connection import ConnectionPool
import threading

from ..config.base import BaseConfig


class RedisClient:
    """Redis client singleton for caching and event bus"""

    _instance: Optional["RedisClient"] = None
    _lock = threading.Lock()

    def __new__(cls, config: Optional[BaseConfig] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[BaseConfig] = None):
        if not hasattr(self, "_initialized"):
            self.config = config or BaseConfig()
            self.enabled = self.config.redis.enabled
            self._pool: Optional[ConnectionPool] = None
            self._client: Optional[redis.Redis] = None
            self._pubsub: Optional[redis.client.PubSub] = None
            self._subscribers: dict = {}
            self._initialized = True

            if self.enabled:
                self._connect()

    def _connect(self):
        """Establish Redis connection"""
        try:
            self._pool = redis.ConnectionPool.from_url(
                self.config.redis.url,
                decode_responses=True,
                max_connections=10
            )
            self._client = redis.Redis(connection_pool=self._pool)
            self._pubsub = self._client.pubsub()
            # Test connection
            self._client.ping()
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self.enabled = False

    def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self.enabled or not self._client:
            return None
        try:
            return self._client.get(key)
        except Exception:
            return None

    def set(self, key: str, value: str, ttl: int = 300):
        """Set cache value with TTL in seconds"""
        if not self.enabled or not self._client:
            return
        try:
            self._client.setex(key, ttl, value)
        except Exception:
            pass

    def delete(self, key: str):
        """Delete key from cache"""
        if not self.enabled or not self._client:
            return
        try:
            self._client.delete(key)
        except Exception:
            pass

    def publish(self, channel: str, message: Any):
        """Publish message to channel"""
        if not self.enabled or not self._client:
            return
        try:
            if not isinstance(message, str):
                message = json.dumps(message, default=str)
            self._client.publish(channel, message)
        except Exception:
            pass

    def subscribe(self, channel: str, callback: Callable):
        """Subscribe to channel with callback"""
        if not self.enabled or not self._pubsub:
            return

        def listener():
            for message in self._pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    try:
                        obj = json.loads(data)
                    except Exception:
                        obj = data
                    callback(obj)

        thread = threading.Thread(target=listener, daemon=True)
        thread.start()
        self._subscribers[channel] = thread

    def close(self):
        """Close Redis connections"""
        if self._pubsub:
            self._pubsub.close()
        if self._pool:
            self._pool.disconnect()
