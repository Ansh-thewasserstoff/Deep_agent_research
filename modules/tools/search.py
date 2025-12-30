import os
import httpx
import asyncio
import json
from langchain_core.tools import tool
from typing import List


@tool
async def parallel_search_tool(queries: List[str], max_results_per_query: int = 3) -> str:
    """
    Executes multiple search queries in parallel using the Parallel.ai API.

    Args:
        queries: A list of search strings (e.g., ["iPhone 16 battery", "Samsung S24 battery"])
        max_results_per_query: Results to fetch per query (default 3 to save tokens)

    Returns:
        A consolidated string of all results with unique [src_n] tags.
    """
    api_key = os.getenv("PARALLEL_API_KEY")
    url = "https://api.parallel.ai/v1beta/search"

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "parallel-beta": "search-extract-2025-10-10"
    }

    # Internal function to handle a single request
    async def fetch_single_objective(client, objective, start_src_id):
        payload = {
            "objective": objective,
            "max_results": max_results_per_query,
            "excerpts": {"max_chars_per_result": 600}  # Tightened further for bulk queries
        }
        try:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                return []

            data = response.json()
            results = data.get("results", [])

            formatted_results = []
            for i, res in enumerate(results):
                # Calculate unique ID: start_id + current_index
                # e.g., if start_src_id is 10, this becomes [src_10], [src_11]...
                current_id = start_src_id + i

                # Combine title and snippets concisely
                content = ' '.join(res.get('excerpts', []))
                entry = (
                    f"[{current_id}] {content[:500]}... "  # Hard cut off to ensure safety
                    f"(Source: {res.get('title', 'Web')} - {res.get('url')})"
                )
                formatted_results.append(entry)

            return formatted_results

        except Exception as e:
            return [f"Error searching '{objective}': {str(e)}"]

    # --- The Parallel Execution Logic ---
    async with httpx.AsyncClient(timeout=30.0) as client:
        # We need to manage source IDs so they don't overlap across queries
        # Query 1 gets IDs 1-3, Query 2 gets IDs 4-6, etc.
        tasks = []
        current_src_id = 1

        for q in queries:
            tasks.append(fetch_single_objective(client, q, current_src_id))
            current_src_id += max_results_per_query

        # Fire all requests at once
        results_lists = await asyncio.gather(*tasks)

    # Flatten and Formatting
    final_output = []

    # Add a header for each query so the LLM knows which fact belongs to which question
    for i, q in enumerate(queries):
        query_results = results_lists[i]
        final_output.append(f"## Results for: '{q}'")
        if query_results:
            final_output.extend(query_results)
        else:
            final_output.append("(No results found)")
        final_output.append("")  # Empty line for spacing

    return "\n".join(final_output)