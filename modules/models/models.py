from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
from urllib.parse import quote
import uuid

@dataclass
class Citation:
    """Represents a source citation with validation status"""
    url: str
    title: str
    content: str
    snippet: str
    is_valid: bool =True
    validation_error: Optional[str] = None
    used_in_response: bool = False

    def get_citation_url(self, text_fragment: Optional[str]=None) -> str:
        """Generate URL with text fragment for highlighting"""
        if not text_fragment:
            if hasattr(self, "_highlight_text"):
                text_fragment = self._highlight_text
            else:
                text_fragment = self.snippet[:100] if self.snippet else ""
        if text_fragment:
            text_fragment = text_fragment.strip()
            text_fragment = ' '.join(text_fragment.split())

            encoded_fragment = quote(text_fragment)
            return f"{self.url}#:~:text={encoded_fragment}"
        else:
            return self.url


@dataclass
class ResearchPlan:
    """Represents a research plan with steps"""
    query: str
    steps: List[str]
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "steps": self.steps,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ResearchResult:
    """Final research result with citations"""
    answer: str
    citation: List[Citation]
    plan: ResearchPlan
    mode: Literal["normal", "detailed"]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_unique_citations(self) -> List[Citation]:
        """Get unique citations from the result"""
        seen_urls = set()
        unique_citations = []
        for citation in self.citation:
            if citation.url not in seen_urls:
                seen_urls.add(citation.url)
                unique_citations.append(citation)
        return unique_citations

@dataclass
class StreamEvent:
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return{
            "type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""

    def calculate_cost(self) -> float:
        """Calculate the cost of the token usage"""
        # pricing per million tokens
        if self.model == "gpt-4.1-mini":
            input_cost = (self.input_tokens / 1_000_000) * 0.40
            output_cost = (self.output_tokens / 1_000_000) * 1.60
        elif self.model == "gpt-4.1-nano":
            input_cost = (self.input_tokens / 1_000_000) * 0.10
            output_cost = (self.output_tokens / 1_000_000) * 0.40
        else:
            # Default to gpt-4.1-mini pricing
            input_cost = (self.input_tokens / 1_000_000) * 0.40
            output_cost = (self.output_tokens / 1_000_000) * 1.60

        return input_cost + output_cost

    def to_dict(self)->Dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "model": self.model,
            "cost": self.calculate_cost()
        }

@dataclass
class SearchTavilyUsage:
    """Search usage tracking for Tavily calls"""
    search_count: int = 0
    def calculate_cost(self) -> float:
        """Calculate the cost of the search usage"""
        return self.search_count * 0.008

    def to_dict(self) -> Dict[str, Any]:
        return{
            "search_count": self.search_count,
            "cost": self.calculate_cost()
        }


@dataclass
class SearchParallelUsage:
    search_count: int = 0

    def calculate_cost(self) -> float:
        """Calculate the cost of the search usage"""
        return self.search_count * 0.008

    def to_dict(self) -> Dict[str, Any]:
        return {
            "search_count": self.search_count,
            "cost": self.calculate_cost()
        }

@dataclass
class TokenInfo:
    """Complete token and cost information for a query"""
    main_llm_usage: TokenUsage = field(default_factory=TokenUsage)
    search_tavily_usage: SearchTavilyUsage = field(default_factory=SearchTavilyUsage)
    context_summarization_usage: TokenUsage = field(default_factory=TokenUsage)

    def get_total_cost(self) -> float:
        """Get the total cost of the token usage"""
        return self.main_llm_usage.calculate_cost() + self.search_tavily_usage.calculate_cost() + self.context_summarization_usage.calculate_cost()

    def to_dict(self)->Dict[str, Any]:
        return{
            "main_llm_usage": self.main_llm_usage.to_dict(),
            "search_tavily_usage": self.search_tavily_usage.to_dict(),
            "context_summarization_usage": self.context_summarization_usage.to_dict(),
            "total_cost": self.get_total_cost()
        }

@dataclass
class ChatSession:
    """Chat session with message history"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_message(self, role:str, content:str)-> None:
        """Add a message to the session"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now()
    def get_context_messages(self, max_messages:int=5)-> List[Dict[str, Any]]:
        """Get the last n messages for context"""
        if len(self.messages) <= max_messages:
            return [{"role": msg["role"], "content": msg["content"]} for msg in self.messages]

        # Return last max_messages, but we'll need to summarize older ones
        return [{"role": msg["role"], "content": msg["content"]} for msg in self.messages[-max_messages:]]

    def needs_summarization(self, max_messages: int = 5)-> bool:
        """Check if the session needs summarization"""
        return len(self.messages) > max_messages

    def to_dict(self) -> Dict[str, Any]:
        return{
            "session_id": self.session_id,
            "messages": self.messages,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

@dataclass
class QueryRecord:
    """Complete record of a research query and response"""
    query_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    user_query: str = ""
    answer: str = ""
    citations: List[Dict[str,Any]] = field(default_factory=list)
    metadata: Dict[str,Any] = field(default_factory=dict)
    token_info: TokenInfo = field(default_factory=TokenInfo)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "session_id": self.session_id,
            "user_query": self.user_query,
            "answer": self.answer,
            "citations": self.citations,
            "metadata": self.metadata,
            "token_info": self.token_info.to_dict(),
            "created_at": self.created_at.isoformat()
        }





