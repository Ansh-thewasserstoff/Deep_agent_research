from .analyst import ANALYST_CONFIG
from .researcherv2 import RESEARCHER_CONFIG_2

# Exported as a list for easy injection into create_deep_agent
SUBAGENT_REGISTRY = [
    ANALYST_CONFIG,
    RESEARCHER_CONFIG_2
]