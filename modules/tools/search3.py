import os
import asyncio
import json
import httpx
import trafilatura
from langchain_core.tools import tool
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

_SEARCH_CACHE = {}


@tool
async def searxng_search_tool(queries: List[str], max_results_per_query: int = 3) -> str:
    """
    Executes parallel searches using a self-hosted SearXNG instance.
    Returns metadata (Title, URL, Domain, Snippet).
    Does NOT fetch full page content. Use get_source_details for that.
    """
    base_url = os.getenv("SEARXNG_BASE_URL")
    if not base_url:
        return "Error: SEARXNG_BASE_URL not found in environment variables."

    # Remove trailing slash if present for cleaner URL construction
    base_url = base_url.rstrip("/")
    search_endpoint = f"{base_url}/search"

    async def fetch_single_query(client, query, start_src_id):
        params = {
            "q": query,
            "format": "json",
            "pageno": 1,
            # 'time_range': 'year', # Optional: restrict to recent results
            # 'language': 'en',     # Optional: restrict language
        }

        try:
            # SearXNG sometimes requires a User-Agent to avoid blocking
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; DeepAgent/1.0)"
            }

            response = await client.get(search_endpoint, params=params, headers=headers, timeout=10.0)

            # Handle non-200 responses (e.g., rate limits)
            if response.status_code != 200:
                return {"query": query, "results": [], "sources": {}, "error": f"Status {response.status_code}"}

            data = response.json()

            results = []
            src_counter = start_src_id
            sources_registry = {}

            # SearXNG returns results in a 'results' list
            raw_results = data.get("results", [])[:max_results_per_query]

            for result in raw_results:
                url_link = result.get("url", "")
                title = result.get("title", "Untitled")
                content_snippet = result.get("content", "")

                # Safe domain extraction
                try:
                    domain = url_link.split('/')[2]
                except IndexError:
                    domain = "unknown"

                src_id = f"src_{src_counter}"

                # Create a short preview for the LLM
                snippet_preview = content_snippet[:150].replace("\n", " ") + "..."

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
                    "snippet": snippet_preview,
                    "full_content": None,
                    "is_fetched": False
                }
                src_counter += 1

            return {"query": query, "results": results, "sources": sources_registry}
        except Exception as e:
            return {"query": query, "results": [], "sources": {}, "error": str(e)}

    # Execute searches concurrently
    async with httpx.AsyncClient() as client:
        src_counter = 1
        tasks = []
        for query in queries:
            tasks.append(fetch_single_query(client, query, src_counter))
            # Increment counter by max_results to keep IDs unique across queries
            src_counter += max_results_per_query
        results_list = await asyncio.gather(*tasks)

    # Aggregate results
    all_sources = {}
    total_results = 0
    for result_data in results_list:
        all_sources.update(result_data['sources'])
        total_results += len(result_data['results'])

    # Cache the results using a deterministic hash of the queries
    search_id = str(abs(hash(json.dumps(queries))))[:8]
    _SEARCH_CACHE[search_id] = {
        "queries": queries,
        "results": results_list,
        "registry": all_sources
    }

    # Build the output string
    summary_lines = [f"SEARCH_COMPLETE [ID: {search_id}]"]
    summary_lines.append(f"Queries: {len(queries)} | Results: {total_results}")

    for result_data in results_list:
        summary_lines.append(f"\n## {result_data['query']}")
        if result_data.get('error'):
            summary_lines.append(f"  Error: {result_data['error']}")

        for result in result_data['results']:
            summary_lines.append(f"  [{result['id']}] {result['title'][:60]} ({result['domain']})")

    summary_lines.append(f"\nUse get_source_details(['src_1', ...], search_id='{search_id}') to fetch content.")

    return "\n".join(summary_lines)


@tool
async def get_source_details(source_ids: List[str], search_id: Optional[str] = None) -> str:
    """
    Fetches the actual HTML of the requested source_ids and extracts clean text using Trafilatura.
    """
    # Locate cache
    if search_id and search_id in _SEARCH_CACHE:
        search_data = _SEARCH_CACHE[search_id]
    elif _SEARCH_CACHE:
        search_data = list(_SEARCH_CACHE.values())[-1]
    else:
        return "Error: No cached search data found"

    registry = search_data['registry']
    final_output = {}

    async def fetch_and_parse(src_id, source_info):
        # Return cached content if available
        if source_info.get("is_fetched") and source_info.get("full_content"):
            return src_id, source_info

        url = source_info['url']

        # Browser headers to prevent 403 Forbidden on some sites
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0, verify=False) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                html_content = response.text

                # Run Trafilatura in a thread to avoid blocking the async event loop
                text_content = await asyncio.to_thread(
                    trafilatura.extract,
                    html_content,
                    include_comments=False,
                    include_tables=True,
                    no_fallback=False
                )

                if not text_content:
                    text_content = "Error: Trafilatura could not extract main text (site might be JS-only)."

                source_info['full_content'] = text_content
                source_info['is_fetched'] = True

                return src_id, source_info

        except Exception as e:
            source_info['full_content'] = f"Error fetching URL: {str(e)}"
            return src_id, source_info

    # Create tasks for all requested IDs
    tasks = []
    for src_id in source_ids:
        if src_id in registry:
            tasks.append(fetch_and_parse(src_id, registry[src_id]))

    # Run fetches in parallel
    if tasks:
        results = await asyncio.gather(*tasks)
        for src_id, data in results:
            final_output[src_id] = {
                "title": data['title'],
                "url": data['url'],
                "domain": data['domain'],
                "content": data['full_content']
            }

    return json.dumps({"sources": final_output, "count": len(final_output)}, indent=2)


@tool
def list_available_domains(search_id: Optional[str] = None) -> str:
    """Lists all unique domains in the search results."""
    if _SEARCH_CACHE:
        data = _SEARCH_CACHE.get(search_id) if search_id else list(_SEARCH_CACHE.values())[-1]
        if data:
            registry = data['registry']
            domains = [s['domain'] for s in registry.values()]
            return json.dumps(list(set(domains)), indent=2)
    return "[]"


@tool
def filter_sources_by_domain(domains: List[str], search_id: Optional[str] = None) -> str:
    """Filter sources by preferred domains."""
    if _SEARCH_CACHE:
        data = _SEARCH_CACHE.get(search_id) if search_id else list(_SEARCH_CACHE.values())[-1]
    else:
        return "Error: No cached search data found"

    if not data:
        return "Error: Invalid search ID"

    registry = data['registry']
    matched_sources = {}

    for src_id, source_info in registry.items():
        if source_info['domain'] in domains:
            matched_sources[src_id] = {
                "title": source_info['title'],
                "url": source_info['url'],
                "snippet_preview": source_info['snippet']
            }

    return json.dumps({
        "matched_sources": matched_sources,
        "count": len(matched_sources)
    }, indent=2)