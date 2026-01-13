from langchain_core.callbacks.base import AsyncCallbackHandler
from typing import Dict, Any, List
# Import the service we just made
from ..services.redis import redis_service

class RedisStreamingCallback(AsyncCallbackHandler):
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_state = "THINKING"
        self.VISIBLE_TOOLS = ["InternetSearch"]

    async def _emit(self, type: str, content: str = ""):
        await redis_service.publish_event(self.session_id, type, content)

    async def on_llm_start(self, serialized, prompts, **kwargs):
        if self.current_state != "THINKING":
            self.current_state = "THINKING"
            await self._emit("STATE", "THINKING")

    async def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs):
        tool_name = serialized.get("name")
        if tool_name in self.VISIBLE_TOOLS:
            self.current_state = "USING_TOOL"
            await self._emit("STATE", f"TOOL:{tool_name}")
            await self._emit("LOG", f"Searching: {input_str}")
        else:
            # Masking internal tools
            self.current_state = "THINKING"
            await self._emit("STATE", "THINKING")
            await self._emit("LOG", "analyzing...")

    async def on_llm_new_token(self, token: str, **kwargs):
        # Heuristic to switch to OUTPUT mode
        if "Final Answer" in token and self.current_state != "OUTPUT":
            self.current_state = "OUTPUT"
            await self._emit("STATE", "OUTPUT")

        if self.current_state == "OUTPUT":
            await self._emit("TOKEN", token)
        else:
            await self._emit("LOG", token)