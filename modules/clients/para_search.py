import asyncio
from typing import List, Dict, Any, Optional
import aiohttp

from modules.core.interfaces import SearchToolInterface
from modules.custom_errors import SearchToolError
from modules.config.settings import SearchConfig
from modules.models.models import SearchParallelUsage
from modules.utils.logging import BaseLogger


class ParallelSearchTool(SearchToolInterface):
    """Parallel AI search API client implementation"""

    def __init__(self, config: SearchConfig):
        self.config = config
        self.logger = BaseLogger.get_logger()
        self.search_usage = SearchParallelUsage()
        # Parallel requires this specific beta header
        self.base_url = "https://api.parallel.ai/v1beta/search"
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "parallel-beta": "search-extract-2025-10-10"
        }

    async def search(
            self,
            query: str,
            max_results: int = 10,
            mode: str = "one-shot",  # 'one-shot' (comprehensive) or 'agentic' (concise)
            exclude_domains: List[str] = None,
            include_domains: List[str] = None
    ) -> Dict[str, Any]:
        """Perform Parallel AI search with natural language objective"""

        # Mapping parameters to Parallel's schema
        payload = {
            "objective": query,  # Using the query as the primary objective
            "search_queries": [query],
            "max_results": max_results,
            "mode": mode,
            "excerpts": {
                "max_chars_per_result": 2000  # Optimal for citation-rich RAG context
            }
        }

        # Handle domain filtering if provided
        if exclude_domains or include_domains:
            payload["source_policy"] = {
                "exclude_domains": exclude_domains or [],
                "include_domains": include_domains or []
            }

        for attempt in range(self.config.max_retries):
            try:
                self.logger.debug(f"Parallel Search attempt {attempt + 1} for: '{query}'")

                timeout = aiohttp.ClientTimeout(total=self.config.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(self.base_url, headers=self.headers, json=payload) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise SearchToolError(f"Parallel API error {response.status}: {error_text}")

                        raw_result = await response.json()

                        # Normalize response to match your system's expected 'results' format
                        normalized_result = self._normalize_response(raw_result)

                        # Track usage
                        self.search_usage.search_count += 1
                        self.logger.debug(f"Parallel successful. Results: {len(normalized_result['results'])}")

                        return normalized_result

            except Exception as e:
                self.logger.warning(f"Parallel attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.config.max_retries - 1:
                    raise SearchToolError(f"Parallel failed after {self.config.max_retries} attempts")
                await asyncio.sleep(2 ** attempt)

    def _normalize_response(self, data: Dict) -> Dict:
        """Translates Parallel's structure to your internal format"""
        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title"),
                "url": item.get("url"),
                "content": " ".join(item.get("excerpts", [])),  # Combine excerpts for the LLM
                "raw_content": item.get("excerpts")
            })
        return {
            "results": results,
            "search_id": data.get("search_id")
        }

    def get_search_usage(self) -> SearchParallelUsage:
        return self.search_usage

    def reset_search_usage(self) -> None:
        self.search_usage = SearchParallelUsage()