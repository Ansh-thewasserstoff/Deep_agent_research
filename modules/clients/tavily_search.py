"""
Search tool implementation for the Deep Research Agent system.
"""

import asyncio
from typing import List, Dict, Any, Optional
import aiohttp

from modules.core.interfaces import SearchToolInterface
from modules.custom_errors import SearchToolError
from modules.config.settings import SearchConfig
from modules.models.models import SearchTavilyUsage
from modules.utils.logging import BaseLogger


class TavilySearchTool(SearchToolInterface):
    """Tavily search API client implementation"""
    
    def __init__(self, config: SearchConfig):
        self.config = config
        self.logger = BaseLogger.get_logger()
        self.search_usage = SearchTavilyUsage()
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "advanced",
        exclude_domains: List[str] = None,
        include_domains: List[str] = None
    ) -> Dict[str, Any]:
        """Perform Tavily search with retry logic"""
        if exclude_domains is None:
            exclude_domains = self.config.exclude_domains
        if include_domains is None:
            include_domains = self.config.include_domains
        
        payload = {
            "api_key": self.config.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "exclude_domains": exclude_domains,
            "include_domains": include_domains,
            "include_answer": True,
            "include_raw_content": True
        }
        
        for attempt in range(self.config.max_retries):
            try:
                self.logger.debug(f"Search request attempt {attempt + 1} for query: '{query}'")
                
                timeout = aiohttp.ClientTimeout(total=self.config.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(self.config.base_url, json=payload) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise SearchToolError(f"Search API error {response.status}: {error_text}")
                        
                        result = await response.json()
                        
                        # Track search usage
                        self.search_usage.search_count += 1
                        self.logger.debug(f"Search successful, found {len(result.get('results', []))} results. Total searches: {self.search_usage.search_count}")
                        
                        return result
                        
            except SearchToolError:
                # Don't retry on API errors
                raise
            except Exception as e:
                self.logger.warning(f"Search attempt {attempt + 1} failed: {str(e)}")
                
                if attempt == self.config.max_retries - 1:
                    raise SearchToolError(f"Search failed after {self.config.max_retries} attempts: {str(e)}")
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
    
    def get_search_usage(self) -> SearchTavilyUsage:
        """Get the current search usage"""
        return self.search_usage
    
    def reset_search_usage(self) -> None:
        """Reset the search usage tracker"""
        self.search_usage = SearchTavilyUsage()

