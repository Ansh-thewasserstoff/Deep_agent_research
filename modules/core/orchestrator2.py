import os
import datetime
from deepagents import create_deep_agent
from langchain_google_genai import ChatGoogleGenerativeAI
# Backend & Memory Imports
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver

# Tool Imports (Agent does the work itself now)
from ..tools.search4 import parallel_search_tool,get_source_details,filter_sources_by_domain,list_available_domains

# 1. Configuration for the Solo Agent (Free Tier Optimized)
SOLO_SETTINGS = {

        "model": "gemini-3-flash-preview",
        "thinking_level": "low",
        "max_tasks": 5,
        "recursion_limit": 20,
        "description": "Fast, lightweight reasoning with Flash speed.",
"max_search_calls":1
}

today = datetime.datetime.now().strftime("%B %d, %Y")

# 2. The "All-in-One" System Prompt
SOLO_SYSTEM_PROMPT = f"""
You are the **Solo Research Agent**.

### MISSION
You are a fast, efficient researcher for free-tier users. 
You must Plan, Search, and Report in a single continuous workflow.

### CRITICAL RESOURCE CONSTRAINTS (COST CONTROL)
1. **Search Budget**: You are allowed **MAXIMUM {SOLO_SETTINGS['max_search_calls']}** call to `parallel_search_tool`.
   - You MUST batch ALL your questions into that single call.
   - Example: `parallel_search_tool(["iPhone 16 battery", "iPhone 16 camera", "iPhone 16 price"])`
   - Only choose required no of sources to get details, for each query based on your need ideally no more that 2 for each query. Also prefer verified sources where ever possible
2. Don't use todo list or write files unless necessary .
### HYBRID MEMORY PROTOCOL
- **Ephemeral Workspace (/)**: Use for temporary scratchpads. Vanishes after run.


### EXECUTION PROTOCOL
1. **Analyze**: Understand the user's request.
2. **Search**: Call `parallel_search_tool` ONCE with a list of targeted queries.
3. **Synthesize**: 
   - Synthesize the findings.
4. **Final Answer**:
   - Write the final response clearly to the user.
   - **Citation**: Use the `[src_X]` tags provided in the search results.
   - **Reference List**: Do NOT generate a bibliography. Just keep the tags inline.
"""

# 3. Shared Memory Store (The Vault)
global_store = InMemoryStore()


def make_hybrid_backend(runtime):
    """
    Creates the dual-layer filesystem:
    1. / (Root) -> StateBackend (Ephemeral, dies with thread)
    2. /memories/ -> StoreBackend (Persistent, survives threads)
    """
    return CompositeBackend(
        default=StateBackend(runtime),
        routes={
            "/memories/": StoreBackend(runtime)
        }
    )


def create_solo_agent():
    """
    Creates a standalone agent that performs all research steps itself.
    Optimized for low cost and low latency.
    """

    # Initialize Model
    model = ChatGoogleGenerativeAI(
        model=SOLO_SETTINGS["model"],
        thinking_level="low",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )

    # Gather Tools (No Sub-agents, just functions)
    # Note: We include 'write_file' so it can save the final report to /memories/
    active_tools = [parallel_search_tool,get_source_details,filter_sources_by_domain,list_available_domains]

    # Initialize Memory Saver
    checkpointer = MemorySaver()

    # Create the Deep Agent
    agent = create_deep_agent(
        model=model,
        system_prompt=SOLO_SYSTEM_PROMPT,
        tools=active_tools,  # Direct tools
        subagents=[],  # No sub-agents
        checkpointer=checkpointer,
        # Hybrid Backend for Context Management
        store=global_store,
        backend=make_hybrid_backend
    )

    agent.recursion_limit = SOLO_SETTINGS["recursion_limit"]

    return agent