import json
import redis
import os
from typing import Callable


class RedisMessageBus:
    def __init__(self, host=None, port=None):
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = int(port or os.getenv("REDIS_PORT", 6379))
        self.client = redis.Redis(
            host=self.host, port=self.port, decode_responses=True
        )

    def publish(self, channel: str, message: dict):
        self.client.publish(channel, json.dumps(message))

    def subscribe(self, channel: str, callback: Callable[[dict], None]):
        pubsub = self.client.pubsub()
        pubsub.subscribe(channel)
        for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    callback(data)
                except json.JSONDecodeError:
                    continue
