"""RabbitMQ client for pub/sub"""
import json
import threading
from typing import Optional, Any, Callable
import pika
from pika.connection import BlockingConnection
from pika.channel import Channel
from ..config.base import BaseConfig


class RabbitMQClient:
    """Message queue client using RabbitMQ for pub/sub"""

    _instance: Optional["RabbitMQClient"] = None
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
            self.enabled = self.config.rabbitmq.enabled
            self._publish_connection: Optional[BlockingConnection] = None
            self._publish_channel: Optional[Channel] = None
            self._subscribers: dict = {}
            self._initialized = True

            if self.enabled:
                self._connect()

    def _connect(self):
        """Establish RabbitMQ connection and declare exchange"""
        try:
            parameters = pika.URLParameters(self.config.rabbitmq.url)
            self._publish_connection = pika.BlockingConnection(parameters)
            self._publish_channel = self._publish_connection.channel()
            # Declare a durable topic exchange for events
            self._publish_channel.exchange_declare(
                exchange="events",
                exchange_type="topic",
                durable=True
            )
        except Exception as e:
            print(f"RabbitMQ connection failed: {e}")
            self.enabled = False

    def get(self, key: str) -> Optional[str]:
        """Caching not supported with RabbitMQ - no-op"""
        return None

    def set(self, key: str, value: str, ttl: int = 300):
        """Caching not supported with RabbitMQ - no-op"""
        pass

    def delete(self, key: str):
        """Caching not supported with RabbitMQ - no-op"""
        pass

    def publish(self, channel: str, message: Any):
        """Publish message to exchange"""
        if not self.enabled or not self._publish_channel:
            return
        try:
            if not isinstance(message, str):
                message = json.dumps(message, default=str)
            self._publish_channel.basic_publish(
                exchange="events",
                routing_key=channel,
                body=message,
                properties=pika.BasicProperties(delivery_mode=2)
            )
        except Exception:
            pass

    def subscribe(self, channel: str, callback: Callable):
        """Subscribe to channel with callback"""
        if not self.enabled:
            return

        def consumer_thread():
            try:
                parameters = pika.URLParameters(self.config.rabbitmq.url)
                connection = pika.BlockingConnection(parameters)
                channel_obj = connection.channel()
                channel_obj.exchange_declare(exchange="events", exchange_type="topic", durable=True)
                # Declare an exclusive, auto-delete queue
                queue = channel_obj.queue_declare(queue='', exclusive=True, auto_delete=True).method.queue
                channel_obj.queue_bind(exchange="events", queue=queue, routing_key=channel)
                def on_message(ch, method, properties, body):
                    try:
                        data = json.loads(body)
                    except Exception:
                        data = body
                    callback(data)
                channel_obj.basic_consume(queue=queue, on_message_callback=on_message, auto_ack=True)
                channel_obj.start_consuming()
            except Exception:
                pass

        thread = threading.Thread(target=consumer_thread, daemon=True)
        thread.start()
        self._subscribers[channel] = thread

    def close(self):
        """Close RabbitMQ connections"""
        if self._publish_connection and self._publish_connection.is_open:
            self._publish_connection.close()
