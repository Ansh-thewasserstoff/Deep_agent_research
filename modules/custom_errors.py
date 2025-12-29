"""
Core exceptions for the Deep Research Agent system.
"""


class DeepResearchError(Exception):
    """Base exception for all Deep Research Agent errors"""
    pass


class LLMClientError(DeepResearchError):
    """Raised when LLM client encounters an error"""
    pass


class SearchToolError(DeepResearchError):
    """Raised when search tool encounters an error"""
    pass


class URLValidationError(DeepResearchError):
    """Raised when URL validation fails"""
    pass


class ResearchPlanError(DeepResearchError):
    """Raised when research plan creation fails"""
    pass


class ResearchExecutionError(DeepResearchError):
    """Raised when research execution fails"""
    pass


class ConfigurationError(DeepResearchError):
    """Raised when configuration is invalid"""
    pass

