"""
Gemini LLM client implementation for the Deep Research Agent system.
"""

import asyncio
from typing import List, Dict, Any, AsyncIterator, Optional
from google import genai
from google.genai import types

from ..core.interfaces import LLMClientInterface
from ..custom_errors import LLMClientError
from ..config.settings import LLMConfig
from ..models.models import TokenUsage
from ..utils.logging import BaseLogger


class GeminiClient(LLMClientInterface):
    """Google Gemini LLM client implementation"""

    def __init__(self, config: LLMConfig):
        self.config = config
        # Initializing the new Google GenAI Client
        self.client = genai.Client(
            api_key=config.api_key,
            # base_url is handled via http_options if using a proxy/Vertex
        )
        self.logger = BaseLogger.get_logger()
        self.last_token_usage: Optional[TokenUsage] = None

    def _prepare_payload(self, messages: List[Dict[str, str]], temperature: float):
        """Translates OpenAI message format to Gemini's system_instruction and contents"""
        system_instruction = None
        contents = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                system_instruction = content
            elif role == "user":
                contents.append(types.Content(role="user", parts=[types.Part(text=content)]))
            elif role == "assistant":
                contents.append(types.Content(role="model", parts=[types.Part(text=content)]))

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
        )
        return contents, config

    async def chat_completion(
            self,
            messages: List[Dict[str, str]],
            temperature: float = 0.7,
            stream: bool = False
    ) -> Any:
        """Generate chat completion with retry logic using Gemini's aio (async) bus"""
        contents, config = self._prepare_payload(messages, temperature)

        for attempt in range(self.config.max_retries):
            try:
                self.logger.debug(f"Gemini request attempt {attempt + 1}")

                # Gemini 2.5/3.0 Async call
                response = await self.client.aio.models.generate_content(
                    model=self.config.model,
                    contents=contents,
                    config=config
                )

                # Track token usage from usage_metadata
                if response.usage_metadata:
                    self.last_token_usage = TokenUsage(
                        input_tokens=response.usage_metadata.prompt_token_count,
                        output_tokens=response.usage_metadata.candidates_token_count,
                        model=self.config.model
                    )
                    self.logger.debug(
                        f"Gemini Token usage: {self.last_token_usage.input_tokens} in, {self.last_token_usage.output_tokens} out")

                return response

            except Exception as e:
                self.logger.warning(f"Gemini attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.config.max_retries - 1:
                    raise LLMClientError(f"Gemini failed after {self.config.max_retries} attempts: {str(e)}")
                await asyncio.sleep(2 ** attempt)

    async def stream_chat_completion(
            self,
            messages: List[Dict[str, str]],
            temperature: float = 0.7
    ) -> AsyncIterator[str]:
        """Stream chat completion tokens with retry logic"""
        contents, config = self._prepare_payload(messages, temperature)

        for attempt in range(self.config.max_retries):
            try:
                self.logger.debug(f"Gemini stream attempt {attempt + 1}")

                # Async streaming generator
                stream = await self.client.aio.models.generate_content_stream(
                    model=self.config.model,
                    contents=contents,
                    config=config
                )

                async for chunk in stream:
                    if chunk.text:
                        yield chunk.text

                    # Track usage from the final chunk
                    if chunk.usage_metadata:
                        self.last_token_usage = TokenUsage(
                            input_tokens=chunk.usage_metadata.prompt_token_count,
                            output_tokens=chunk.usage_metadata.candidates_token_count,
                            model=self.config.model
                        )

                return

            except Exception as e:
                self.logger.warning(f"Gemini stream attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.config.max_retries - 1:
                    raise LLMClientError(f"Gemini stream failed: {str(e)}")
                await asyncio.sleep(2 ** attempt)

    def get_last_token_usage(self) -> Optional[TokenUsage]:
        return self.last_token_usage

    def reset_token_usage(self) -> None:
        self.last_token_usage = None