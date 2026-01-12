
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

_SEARCH_CACHE = {}
import os
import asyncio
import json
import httpx
import csv
from typing import List, Optional, Set
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables

# --- 1. CONFIGURATION & REFINER ---

_VERIFIED_URLS_CACHE: Set[str] = set()


# Load Verified URLs from CSV
def load_verified_urls(csv_path: str = "verified_urls.csv"):
    """Loads a list of trusted URLs from a CSV file."""
    global _VERIFIED_URLS_CACHE
    if _VERIFIED_URLS_CACHE:
        return  # Already loaded

    verified_list = []
    # If file exists, read it. Otherwise, use your hardcoded list as fallback/default.
    if os.path.exists(csv_path):
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)  # Skip header if "URL" is the first row
                for row in reader:
                    if row:
                        url = row[0].strip()
                        if url.startswith("http"):
                            verified_list.append(url)
            print(f"Loaded {len(verified_list)} verified URLs from {csv_path}")
        except Exception as e:
            print(f"Error reading verified CSV: {e}")
    else:
        # Fallback list (The one you provided)
        print("Warning: verified_urls.csv not found. Using default list.")
        verified_list = [
            "https://judgments.ecourts.gov.in/",
            "https://ecourts.gov.in/",
            "https://njdg.ecourts.gov.in/",
            "https://ecommitteesci.gov.in/",
            "https://doj.gov.in/",
            "https://districts.ecourts.gov.in/",
            "http://www.delhihighcourt.nic.in/",
            "https://highcourt.kerala.gov.in/",
            "https://bombayhighcourt.nic.in/",
            "https://hcmadras.tn.gov.in/",
            "https://tshc.gov.in/",
            "https://orissahighcourt.nic.in/",
            "https://patnahighcourt.gov.in/",
            "https://aphc.gov.in/",
            "https://mphc.gov.in/"
        ]

    _VERIFIED_URLS_CACHE = set(verified_list)


# Initialize Refiner
if "GOOGLE_API_KEY" in os.environ:
    refiner_model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite-preview",
        temperature=0,
        google_api_key=os.environ["GOOGLE_API_KEY"]
    )
else:
    refiner_model = None

REFINER_PROMPT = """
You are a Data Cleaning Engine. Your ONLY job is to extract the core informational content from the provided web scraper text.
RULES:
1. Remove Noise: nav menus, footers, copyright, ads.
2. Preserve Facts: dates, numbers, prices, technical specs.
3. No Chatter.
INPUT TEXT:
{raw_text}
"""


async def refine_content(raw_text: str) -> str:
    if not refiner_model or len(raw_text) < 300:
        return raw_text
    try:
        chain = ChatPromptTemplate.from_template(REFINER_PROMPT) | refiner_model
        response = await chain.ainvoke({"raw_text": raw_text})
        return response.content
    except:
        return raw_text


# --- 2. TOOLS ---

@tool
async def parallel_search_tool(queries: List[str], max_results_per_query: int = 3) -> str:
    """Executes parallel web searches and prioritizes verified government/legal sources."""

    # 1. Ensure verified URLs are loaded
    load_verified_urls(csv_path=r"C:\Users\Ansh\wstf_project\deep_agent_research\srxng.csv")

    api_key = os.getenv("PARALLEL_API_KEY")
    if not api_key:
        return "Error: PARALLEL_API_KEY not found."

    url = "https://api.parallel.ai/v1beta/search"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "parallel-beta": "search-extract-2025-10-10"
    }

    async def fetch_single_objective(client, objective, start_src_id):
        payload = {"objective": objective, "max_results": max_results_per_query, "extract": True}
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            results = []
            src_counter = start_src_id
            sources_registry = {}

            for result in data.get("results", []):
                # Content Extraction Logic
                excerpts = result.get("excerpts", [])
                if isinstance(excerpts, list) and excerpts:
                    content = "\n\n".join(excerpts)
                else:
                    content = result.get("extract", result.get("snippet", ""))

                url_link = result.get("url", "")
                title = result.get("title", "Untitled")
                try:
                    domain = url_link.split('/')[2]
                except IndexError:
                    domain = "unknown"

                # --- VERIFICATION LOGIC ---
                is_verified = False
                # Check if the result URL starts with any URL in our trusted list
                # We normalize slightly by checking if trusted_url is IN result_url
                for trusted_url in _VERIFIED_URLS_CACHE:
                    # Remove 'www.' for looser matching if needed
                    clean_trusted = trusted_url.replace("www.", "").rstrip("/")
                    clean_link = url_link.replace("www.", "")

                    if clean_trusted in clean_link:
                        is_verified = True
                        break

                # Tag the title for the LLM
                display_title = f"[VERIFIED] {title}" if is_verified else title
                # --------------------------

                src_id = f"src_{src_counter}"
                snippet_preview = content[:100].replace("\n", " ") + "..."

                results.append({
                    "id": src_id,
                    "title": display_title,  # LLM sees this
                    "domain": domain,
                    "snippet": snippet_preview,
                    "is_verified": is_verified  # Hidden metadata
                })

                sources_registry[src_id] = {
                    "url": url_link,
                    "title": display_title,
                    "domain": domain,
                    "full_content": content,
                    "snippet": content[:200],
                    "is_refined": False,
                    "is_verified": is_verified
                }
                src_counter += 1

            return {"query": objective, "results": results, "sources": sources_registry}
        except Exception as e:
            return {"query": objective, "results": [], "sources": {}, "error": str(e)}

    # Run Parallel Requests
    async with httpx.AsyncClient() as client:
        src_counter = 1
        tasks = []
        for query in queries:
            tasks.append(fetch_single_objective(client, query, src_counter))
            src_counter += max_results_per_query
        results_list = await asyncio.gather(*tasks)

    # Aggregate
    all_sources = {}
    total_results = 0
    verified_count = 0

    for result_data in results_list:
        all_sources.update(result_data['sources'])
        total_results += len(result_data['results'])
        # Count verified
        verified_count += sum(1 for r in result_data['results'] if r['is_verified'])

    search_id = str(abs(hash(json.dumps(queries))))[:8]
    _SEARCH_CACHE[search_id] = {
        "queries": queries,
        "results": results_list,
        "registry": all_sources
    }

    # --- Build LLM Summary Output ---
    summary_lines = [f"SEARCH_COMPLETE [ID: {search_id}]"]
    summary_lines.append(f"Queries: {len(queries)} | Results: {total_results} | Sources: {len(all_sources)}")

    if verified_count > 0:
        summary_lines.append(f"*** FOUND {verified_count} VERIFIED OFFICIAL SOURCES ***")

    for result_data in results_list:
        summary_lines.append(f"\n## {result_data['query']}")
        for result in result_data['results']:
            # The [VERIFIED] tag is already in result['title']
            summary_lines.append(f"  [{result['id']}] {result['title'][:80]} ({result['domain']})")

    summary_lines.append(f"\nUse get_source_details(['src_1', ...], search_id='{search_id}') to read content.")

    return "\n".join(summary_lines)


@tool
async def get_source_details(source_ids: List[str], search_id: Optional[str] = None) -> str:
    """Retrieves full content for specific source IDs with auto-refinement."""
    if search_id and search_id in _SEARCH_CACHE:
        search_data = _SEARCH_CACHE[search_id]
    elif _SEARCH_CACHE:
        search_data = list(_SEARCH_CACHE.values())[-1]
    else:
        return json.dumps({"error": "No cached search data found"})

    registry = search_data['registry']
    results = {}
    tasks = []

    ids_to_process = [sid for sid in source_ids if sid in registry]

    async def process_source(src_id):
        src = registry[src_id]
        raw_text = src.get('full_content', '')

        if src.get('is_refined', False):
            final_text = raw_text
        else:
            final_text = await refine_content(raw_text)
            registry[src_id]['full_content'] = final_text
            registry[src_id]['is_refined'] = True

        return src_id, {
            "title": src['title'],
            "url": src['url'],
            "domain": src['domain'],
            "is_verified": src.get('is_verified', False),  # Pass this flag to LLM again
            "content": final_text
        }

    if not ids_to_process:
        return json.dumps({"sources": {}, "count": 0})

    for src_id in ids_to_process:
        tasks.append(process_source(src_id))

    processed_items = await asyncio.gather(*tasks)

    for src_id, data in processed_items:
        results[src_id] = data

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

# ... (Include list_available_domains and filter_sources_by_domain from previous code) ...
# --- MAIN VERIFICATION SCRIPT ---

async def main():
    print("--- 1. Testing Parallel Search Tool ---")
    search_output = await parallel_search_tool.ainvoke({
        "queries": ["latest ruling on dogs in india"],
        "max_results_per_query": 2
    })

    print("\n[LLM View] Search Tool Output:")
    print(search_output)

    try:
        search_id = search_output.split("[ID: ")[1].split("]")[0]
        print(f"\n-> Captured Search ID: {search_id}")
    except IndexError:
        print("\n[!] Could not parse Search ID. Check format above.")
        return

    print("\n--- 2. Testing Get Source Details (Fetching src_1) ---")
    details = get_source_details.invoke({"source_ids": ["src_1"], "search_id": search_id})

    print(f"[LLM View] Source Details JSON (Snippet):")
    # Only printing the first 500 chars so we don't flood the console, but checking len
    print(details[:500] + "...")

    data = json.loads(details)
    if "sources" in data and "src_1" in data["sources"]:
        src = data["sources"]["src_1"]
        content_len = len(src.get('full_content', ''))

        print(f"\n[✓] Verification Success:")
        print(f"    - Title: {src.get('title')}")
        print(f"    - URL: {src.get('url')}")
        print(f"    - Content Length: {content_len} chars")

        if content_len > 0:
            print("    - Status: FIXED (Content is populated)")
        else:
            print("    - Status: FAILED (Content is still empty)")
    else:
        print("\n[!] Verification Failed: src_1 data missing or malformed.")


if __name__ == "__main__":
    if "PARALLEL_API_KEY" not in os.environ:
        print("Please set 'PARALLEL_API_KEY' environment variable.")
    else:
        asyncio.run(main())