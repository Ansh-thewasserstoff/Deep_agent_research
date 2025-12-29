from .researcher import RESEARCHER_CONFIG
from .analyst import ANALYST_CONFIG

# Exported as a list for easy injection into create_deep_agent
SUBAGENT_REGISTRY = [
    RESEARCHER_CONFIG,
    ANALYST_CONFIG
]