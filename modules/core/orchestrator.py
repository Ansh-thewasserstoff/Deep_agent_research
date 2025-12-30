import os
from typing import Dict, Any
from deepagents import create_deep_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver # <--- Add this import
from ..tools.search import parallel_search_tool
from ..tools.url_validator import url_validator_tool
from ..agents import SUBAGENT_REGISTRY

# 1. Google Gemini 3.0 Tier Configuration
# Gemini 3 introduces 'thinking_level' (minimal, low, medium, high)
TIER_SETTINGS = {
    "free": {
        "model": "gemini-3-flash-preview",
        "thinking_level": "low",
        "max_tasks": 5,
        "recursion_limit": 20,
        "description": "Fast, lightweight reasoning with Flash speed."
    },
    "pro": {
        "model": "gemini-3-flash-preview",
        "thinking_level": "medium",
        "max_tasks": 15,
        "recursion_limit": 60,
        "description": "Pro-grade reasoning at Flash-level latency."
    },
    "ultra": {
        "model": "gemini-3-pro-preview",
        "thinking_level": "high",
        "max_tasks": 35,
        "recursion_limit": 120,
        "description": "Deep Thinking mode: Maximum reasoning depth for complex agents."
    }
}

# 2. Lead Orchestrator System Prompt
# 1. Define the Roster (Hardcoded or Dynamic)
# This tells the Orchestrator EXACTLY who is available and when to call them.
TEAM_ROSTER = """
### AVAILABLE SUB-AGENTS (TEAM ROSTER)
You have access to the following specialists via the `task` tool or direct tool calls:

1. **researcher**:
   - **Role**: Web Search & Fact Gathering.
   - **When to use**: ANY time you need external information, specs, prices, or news.
   - **Input**: A specific research topic (e.g., "iPhone 16 battery specs").
   - **Output**: Saves findings to `/research/` files.

Note it is better to call one researcher with multiple queries if the queries are related and not complex
2. **analyst**:
   - **Role**: Reading & Synthesis.
   - **When to use**: AFTER research is complete, to write the final report.
   - **Input**: Instruction to read specific files.
   - **Output**: A final synthesized answer.
"""

# 2. Update the System Prompt
ORCHESTRATOR_SYSTEM_PROMPT = """
You are the **Lead Orchestrator (Gemini 3)**.

### PROTOCOL: HUMAN-IN-THE-LOOP PLANNING
**PHASE 1: PLANNING (Mandatory First Step)**
When you receive a new request, do NOT use any tools immediately.
1. Analyze the request.
2. Draft a clear, numbered **To-Do List** of research steps.
3. Present this plan to the user and ask: *"Does this plan look correct?"*
4. **STOP** and wait for the user's input.
CRITICAL: You do not have permission to use tools yet. Output the plan as text.

**PHASE 2: EXECUTION**
ONLY when the user says "Yes", "Proceed", or "Approved":
1. Start executing the plan.
2. **DELEGATE**: Use the `researcher` for data gathering.
3. **SYNTHESIZE**: Use the `analyst` for the final report.
4. **DO NOT** doing the research yourself. You are the Manager, not the Worker.
5. **FINAL HANDOFF**: 
   - When the Analyst provides the final report, pass it to the user **VERBATIM**.
   - Do NOT rewrite it. Do NOT remove the `[src_X]` tags.
   - Ensure the "References" section is included at the bottom.
...
{roster}

{tier_info}
"""


def create_research_system(tier: str = "pro"):
    settings = TIER_SETTINGS.get(tier.lower(), TIER_SETTINGS["free"])

    model = ChatGoogleGenerativeAI(
        model=settings["model"],
        thinking_level=settings["thinking_level"],
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )

    # Inject the Roster into the prompt
    full_prompt = ORCHESTRATOR_SYSTEM_PROMPT.format(
        roster=TEAM_ROSTER,
        tier_info=f"Tier: {tier.upper()}. Max sub-tasks: {settings['max_tasks']}"
    )

    # Initialize Memory
    memory = MemorySaver()

    agent = create_deep_agent(
        model=model,
        system_prompt=full_prompt,
        tools=[],  # Orchestrator has NO search tools, only delegation tools
        subagents=SUBAGENT_REGISTRY,
        checkpointer=memory
    )

    agent.recursion_limit = settings["recursion_limit"]
    return agent