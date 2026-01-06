import os
import asyncio
import json
import httpx
from langchain_core.tools import tool
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

_SEARCH_CACHE = {}


@tool
async def parallel_search_tool(queries: List[str], max_results_per_query: int = 3) -> str:
    """Executes parallel web searches and returns high-level summaries."""
    api_key = os.getenv("PARALLEL_API_KEY")
    if not api_key:
        return "Error: PARALLEL_API_KEY not found in environment variables."

    url = "https://api.parallel.ai/v1beta/search"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "parallel-beta": "search-extract-2025-10-10"
    }

    async def fetch_single_objective(client, objective, start_src_id):
        # We request "extract": True, but the API might return "excerpts"
        payload = {"objective": objective, "max_results": max_results_per_query, "extract": True}
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            # Debug print to confirm data arrival (optional)
            # print(f"DEBUG: Received {len(data.get('results', []))} results for '{objective}'")

            results = []
            src_counter = start_src_id
            sources_registry = {}

            for result in data.get("results", []):
                # --- FIX STARTS HERE ---
                # 1. Check for 'excerpts' (list) first, join them into a string
                excerpts = result.get("excerpts", [])
                if isinstance(excerpts, list) and excerpts:
                    content = "\n\n".join(excerpts)
                # 2. Fallback to 'extract' or 'snippet' if 'excerpts' is missing
                else:
                    content = result.get("extract", result.get("snippet", ""))
                # --- FIX ENDS HERE ---

                url_link = result.get("url", "")
                title = result.get("title", "Untitled")

                # Safe domain extraction
                try:
                    domain = url_link.split('/')[2]
                except IndexError:
                    domain = "unknown"

                src_id = f"src_{src_counter}"

                # Create a short preview for the LLM
                snippet_preview = content[:100].replace("\n", " ") + "..." if len(content) > 100 else content

                results.append({
                    "id": src_id,
                    "title": title,
                    "domain": domain,
                    "snippet": snippet_preview
                })

                sources_registry[src_id] = {
                    "url": url_link,
                    "title": title,
                    "domain": domain,
                    "full_content": content,  # This will now be populated
                    "snippet": content[:200]
                }
                src_counter += 1

            return {"query": objective, "results": results, "sources": sources_registry}
        except Exception as e:
            return {"query": objective, "results": [], "sources": {}, "error": str(e)}

    async with httpx.AsyncClient() as client:
        src_counter = 1
        tasks = []
        for query in queries:
            tasks.append(fetch_single_objective(client, query, src_counter))
            src_counter += max_results_per_query
        results_list = await asyncio.gather(*tasks)

    all_sources = {}
    total_results = 0
    for result_data in results_list:
        all_sources.update(result_data['sources'])
        total_results += len(result_data['results'])

    # Create a deterministic ID based on the query hash
    search_id = str(abs(hash(json.dumps(queries))))[:8]
    _SEARCH_CACHE[search_id] = {
        "queries": queries,
        "results": results_list,
        "registry": all_sources
    }

    summary_lines = [f"SEARCH_COMPLETE [ID: {search_id}]"]
    summary_lines.append(f"Queries: {len(queries)} | Results: {total_results} | Sources: {len(all_sources)}")

    for result_data in results_list:
        summary_lines.append(f"\n## {result_data['query']}")
        for result in result_data['results']:
            summary_lines.append(f"  [{result['id']}] {result['title'][:60]} ({result['domain']})")

    # Adding a helpful hint for the LLM
    summary_lines.append(f"\nUse get_source_details(['src_1', ...], search_id='{search_id}') to read content.")

    return "\n".join(summary_lines)


@tool
def get_source_details(source_ids: List[str], search_id: Optional[str] = None) -> str:
    """Retrieves full content for specific source IDs."""
    # Logic to find the correct cache entry
    if search_id and search_id in _SEARCH_CACHE:
        search_data = _SEARCH_CACHE[search_id]
    elif _SEARCH_CACHE:
        search_data = list(_SEARCH_CACHE.values())[-1]
    else:
        return "Error: No cached search data found"

    registry = search_data['registry']
    results = {}

    for src_id in source_ids:
        if src_id in registry:
            results[src_id] = registry[src_id]

    return json.dumps({"sources": results, "count": len(results)}, indent=2)


@tool
def list_available_domains(search_id: Optional[str] = None) -> str:
    """Lists all unique domains in the search results."""
    if _SEARCH_CACHE:
        search_data = list(_SEARCH_CACHE.values())[-1]
        registry = search_data['registry']
        domains = [s['domain'] for s in registry.values()]
        return json.dumps(list(set(domains)), indent=2)
    return "[]"


@tool
def filter_sources_by_domain(domains: List[str], search_id: Optional[str] = None) -> str:
    """
    Filter sources by preferred domains (e.g., ['techcrunch.com', 'theverge.com']).
    Future-proof for favored sources feature.

    Args:
        domains: List of domains to filter by
        search_id: Optional search ID

    Returns:
        List of source IDs matching the domains
    """
    # Find the search data
    if search_id and search_id in _SEARCH_CACHE:
        search_data = _SEARCH_CACHE[search_id]
    elif _SEARCH_CACHE:
        search_data = list(_SEARCH_CACHE.values())[-1]
    else:
        return "Error: No cached search data found"

    registry = search_data['registry']

    # Filter by domain
    matched_sources = {}
    for src_id, source_info in registry.items():
        if source_info['domain'] in domains:
            matched_sources[src_id] = {
                "title": source_info['title'],
                "url": source_info['url'],
                "snippet": source_info['snippet']
            }

    output = {
        "matched_sources": matched_sources,
        "count": len(matched_sources),
        "domains_searched": domains
    }

    return json.dumps(output, indent=2)
