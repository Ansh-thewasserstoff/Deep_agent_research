"""
URL validator implementation for the Deep Research Agent system.
"""

import asyncio
from typing import Tuple, Optional
import aiohttp

from ..core.interfaces import URLValidatorInterface
from ..config.settings import URLValidatorConfig
from ..utils.logging import BaseLogger

class URLValidator(URLValidatorInterface):
    """URL validator implementation"""
    def __init__(self, config: URLValidatorConfig):
        self.config = config
        self.logger = BaseLogger.get_logger()

    async def validate_url(
            self,
            url: str,
            preview_chars: int = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validate URL and return (is_valid, error_message, preview_text)"""
        if preview_chars is None:
            preview_chars = self.config.preview_chars

        for attempt in range(self.config.max_retries):
            try:
                self.logger.debug(f"Attempt {attempt + 1} to validate URL: {url}")

                headers = {
                    "User-Agent": self.config.user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
                }

                timeout = aiohttp.ClientTimeout(total=self.config.timeout)
                async with aiohttp.ClientSession(
                    timeout=timeout,
                    headers=headers
                ) as session:
                    async with session.get(
                        url,
                        allow_redirects=True,
                        ssl=False
                    ) as response:
                        if response.status == 404:
                            self.logger.debug(f"URL {url} not found")
                            return False, "404 URL not found", None
                        if response.status >= 400:
                            self.logger.debug(f"URL returned {response.status}: {url}")
                            return False, f"HTTP {response.status}", None

                        try:
                            text = await response.text()
                            preview_text = text[:preview_chars] if text else ""

                            if preview_text and "404" in preview_text.lower() and "not found" in preview_text.lower():
                                self.logger.debug(f"URL {url} not found")
                                return False, "404 URL not found", None
                            self.logger.debug(f"URL {url} is valid")
                            return True, None, preview_text
                        except Exception as e:
                            self.logger.debug(f"URL accessible but content unreadable: {url} - {str(e)}")
                            return True, None, None
            except asyncio.TimeoutError:
                self.logger.debug(f"URL validation timeout attempt {attempt + 1}: {url}")
                if attempt == self.config.max_retries - 1:
                    return False, "Timeout", None
            except Exception as e:
                self.logger.debug(f"URL validation error attempt {attempt + 1}: {url} - {str(e)}")
                if attempt == self.config.max_retries - 1:
                    return False, str(e), None
        return False, "Validation failed after retries", None

