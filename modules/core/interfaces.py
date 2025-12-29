from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator, Literal, Tuple
from ..models.models import Citation, ResearchPlan, ResearchResult

class LLMClientInterface(ABC):
    @abstractmethod
    async def chat_completion(self,
                              messages: List[Dict[str,str]],
                              temperature:float = 0.7,
                              stream: bool = False) -> Any:
        pass

    @abstractmethod
    async def stream_chat_completion(self,
                                     messages: List[Dict[str,str]],
                                     temperature:float = 0.7) -> AsyncIterator[Dict[str,str]]:
        pass


class SearchToolInterface(ABC):
    """Abstract interface for search tools"""

    @abstractmethod
    async def search(
            self,
            query: str,
            max_results: int = 10,
            search_depth: str = "advanced",
            exclude_domains: List[str] = []
    ) -> Dict[str, Any]:
        """Perform search and return results"""
        pass


class URLValidatorInterface(ABC):
    """Abstract interface for URL validators"""

    @abstractmethod
    async def validate_url(
            self,
            url: str,
            preview_chars: int = 500
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Validate URL and return (is_valid, error_message, preview_text)"""
        pass


class ResearchAgentInterface(ABC):
    """Abstract interface for research agents"""

    @abstractmethod
    async def research(
            self,
            query: str,
            mode: Literal["normal", "detailed"] = "normal",
            stream_callback: Optional[callable] = None
    ) -> ResearchResult:
        """Main research method"""
        pass

    @abstractmethod
    async def create_research_plan(
            self,
            query: str,
            mode: Literal["normal", "detailed"] = "normal"
    ) -> ResearchPlan:
        """Create a research plan for the query"""
        pass


class SubAgentInterface(ABC):
    """Abstract interface for research sub-agents"""

    @abstractmethod
    async def execute_task(
            self,
            task_description: str,
            context: str = ""
    ) -> Tuple[str, List[Citation]]:
        """Execute a specific research task"""
        pass



