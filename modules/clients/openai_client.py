"""
LLM client implementation for the Deep Research Agent system.
"""

import asyncio
from typing import List, Dict, Any, AsyncIterator, Optional
from openai import AsyncOpenAI

from ..core.interfaces import LLMClientInterface
from..custom_errors import LLMClientError
from ..config.settings import LLMConfig
from ..models.models import TokenUsage
from ..utils.logging import BaseLogger


class LLMClient(LLMClientInterface):
    """OpenAI LLM client implementation"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout
        )
        self.logger = BaseLogger.get_logger()
        self.last_token_usage: Optional[TokenUsage] = None

    async def chat_completion(
            self,
            messages: List[Dict[str, str]],
            temperature: float = 0.7,
            stream: bool = False
    ) -> Any:
        """Generate chat completion with retry logic"""
        for attempt in range(self.config.max_retries):
            try:
                self.logger.debug(f"LLM request attempt {attempt + 1}")

                response = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=temperature,
                    stream=stream
                )

                # Track token usage
                if hasattr(response, 'usage') and response.usage:
                    self.last_token_usage = TokenUsage(
                        input_tokens=response.usage.prompt_tokens,
                        output_tokens=response.usage.completion_tokens,
                        model=self.config.model
                    )
                    self.logger.debug(
                        f"Token usage: {self.last_token_usage.input_tokens} input, {self.last_token_usage.output_tokens} output")

                self.logger.debug("LLM request successful")
                return response

            except Exception as e:
                self.logger.warning(f"LLM request attempt {attempt + 1} failed: {str(e)}")

                if attempt == self.config.max_retries - 1:
                    raise LLMClientError(f"LLM request failed after {self.config.max_retries} attempts: {str(e)}")

                # Exponential backoff
                await asyncio.sleep(2 ** attempt)

    async def stream_chat_completion(
            self,
            messages: List[Dict[str, str]],
            temperature: float = 0.7
    ) -> AsyncIterator[str]:
        """Stream chat completion tokens with retry logic"""
        for attempt in range(self.config.max_retries):
            try:
                self.logger.debug(f"LLM stream request attempt {attempt + 1}")

                stream = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=temperature,
                    stream=True,
                    stream_options={"include_usage": True}
                )

                input_tokens = 0
                output_tokens = 0

                async for chunk in stream:
                    # Handle content chunks
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

                    # Handle usage information (comes at the end)
                    if hasattr(chunk, 'usage') and chunk.usage:
                        input_tokens = chunk.usage.prompt_tokens
                        output_tokens = chunk.usage.completion_tokens

                # Track token usage after streaming completes
                if input_tokens > 0 or output_tokens > 0:
                    self.last_token_usage = TokenUsage(
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        model=self.config.model
                    )
                    self.logger.debug(f"Stream token usage: {input_tokens} input, {output_tokens} output")

                self.logger.debug("LLM stream request successful")
                return

            except Exception as e:
                self.logger.warning(f"LLM stream attempt {attempt + 1} failed: {str(e)}")

                if attempt == self.config.max_retries - 1:
                    raise LLMClientError(f"LLM stream failed after {self.config.max_retries} attempts: {str(e)}")

                # Exponential backoff
                await asyncio.sleep(2 ** attempt)

    def get_last_token_usage(self) -> Optional[TokenUsage]:
        """Get the token usage from the last API call"""
        return self.last_token_usage

    def reset_token_usage(self) -> None:
        """Reset the token usage tracker"""
        self.last_token_usage = None


