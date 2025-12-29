import os
import httpx
from langchain_core.tools import tool


@tool
async def parallel_search_tool(objective: str, max_results: int = 5) -> str:
    """
    Performs a deep web search.
    Returns: A raw text string of results with [src_n] tags.
    """
    api_key = os.getenv("PARALLEL_API_KEY")
    url = "https://api.parallel.ai/v1beta/search"

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "parallel-beta": "search-extract-2025-10-10"
    }

    # We tighten the excerpts to 800 chars to prevent the initial token bloat
    payload = {
        "objective": objective,
        "max_results": max_results,
        "excerpts": {"max_chars_per_result": 800}
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            return f"Error: Search failed (Status {response.status_code})"

        data = response.json()
        results = data.get("results", [])

        # Format the data into a string for the agent to process
        output = []
        for i, res in enumerate(results, 1):
            output.append(
                f"SOURCE: [src_{i}]\nURL: {res['url']}\nTITLE: {res['title']}\nCONTENT: {' '.join(res['excerpts'])}")

        return "\n---\n".join(output)