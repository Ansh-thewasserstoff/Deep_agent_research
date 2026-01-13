import redis.asyncio as redis
import os

REDIS_URL = os.getenv("REDIS_URL")

class RedisService:
    _instance = None

    def __init__(self):
        self.redis = redis.Redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def close(self):
        await self.redis.close()

    async def publish_event(self, session_id: str, event_type: str, payload):
        channel = f"session_{session_id}"
        message = f"{event_type}:{payload}"
        await self.redis.publish(channel, message)


    async def listen_to_session(self, session_id: str):
        """
        Generator that yields messages for SSE
        """
        pubsub = self.redis.pubsub()
        channel = f"session_{session_id}"
        await pubsub.subscribe(channel)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    if data == "[DONE]":
                        break
                    yield data
        finally:
            await pubsub.unsubscribe(channel)

    # --- MEMORY METHODS (CHAT HISTORY) ---
    async def get_chat_history(self, session_id: str):
        """
        Retrieves the last X messages for the Agent's context
        """
        key = f"history:{session_id}"
        # LPRANGE gets items from list. 0 to -1 means "everything"
        history = await self.redis.lrange(key, 0, -1)
        return history

    async def append_message(self, session_id: str, role: str, content: str):
        """
        Saves a message to the history list
        """
        key = f"history:{session_id}"
        msg_json = f"{role}:{content}"  # Simple format, or use JSON

        # Push to end of list (RPUSH)
        await self.redis.rpush(key, msg_json)

        # Optional: Trim list to keep only last 50 messages to save RAM
        await self.redis.ltrim(key, -50, -1)

        # Set expiry so abandoned chats clear out after 24 hours
        await self.redis.expire(key, 86400)

    # Global instance


redis_service = RedisService.get_instance()
