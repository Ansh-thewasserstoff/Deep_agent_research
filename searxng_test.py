import os
import asyncio
import json
from dotenv import load_dotenv

# Import your tools here.
from modules.tools.search3 import searxng_search_tool, get_source_details

# Load environment variables
load_dotenv()


async def main():
    print("--- 1. Testing SearXNG Search Tool ---")

    # 1. Run the search
    # Asking for 20 results to test a variety of sites
    search_output = await searxng_search_tool.ainvoke({
        "queries": ["current price of ddr5 ram"],
        "max_results_per_query": 20
    })

    print(f"\n[LLM View] Search Tool Output (Snippet): {search_output[:200]}...")

    # 2. Extract the Search ID
    try:
        search_id = search_output.split("[ID: ")[1].split("]")[0]
        print(f"\n-> Captured Search ID: {search_id}")
    except IndexError:
        print("\n[!] Could not parse Search ID. Check format above.")
        return

    print("\n--- 2. Batch Fetching All Sources (src_1 to src_20) ---")

    # 3. Generate IDs for all potential results
    all_source_ids = [f"src_{i}" for i in range(1, 21)]

    # 4. Fetch full content
    details_str = await get_source_details.ainvoke({
        "source_ids": all_source_ids,
        "search_id": search_id
    })

    # 5. Verify and Tabulate Results
    try:
        data = json.loads(details_str)
        sources = data.get("sources", {})

        print(f"\n{'ID':<8} | {'STATUS':<15} | {'LENGTH':<8} | URL")
        print("-" * 110)

        stats = {"success": 0, "forbidden": 0, "empty": 0, "error": 0}

        for src_id in all_source_ids:
            if src_id not in sources:
                continue

            src = sources[src_id]
            url = src.get('url', 'N/A')
            content = src.get('content', '')
            error = src.get('error', '')

            # --- Status Logic ---
            status = "UNKNOWN"
            debug_info = None

            lower_content = content.lower()

            # Case 1: Explicit Error or Forbidden Keywords
            if error or "403 forbidden" in lower_content or "access denied" in lower_content:
                status = "⛔ FORBIDDEN/ERR"
                stats["forbidden"] += 1
                debug_info = content.strip() if content else error

            # Case 2: Content is suspicious (Trafilatura error or very short)
            elif "error" in lower_content[:50]:
                status = "❌ EXTRACT ERR"
                stats["error"] += 1
                debug_info = content.strip()

            # Case 3: Content is too short (likely empty body or CAPTCHA)
            elif len(content) < 200:
                status = "⚠️  EMPTY/SHORT"
                stats["empty"] += 1
                debug_info = content.strip()

            # Case 4: Success
            else:
                status = "✅ 200 OK"
                stats["success"] += 1

            # --- Output ---
            # Truncate URL for display
            display_url = (url[:55] + '..') if len(url) > 55 else url
            print(f"{src_id:<8} | {status:<15} | {len(content):<8} | {display_url}")

            # Print the actual data if it failed/was short
            if debug_info:
                # repr() escapes newlines so you can see the raw string clearly
                preview = repr(debug_info[:150])
                print(f"           ↳ DATA: {preview}")

        print("-" * 110)
        print("SUMMARY:")
        print(f"Total Success:     {stats['success']}")
        print(f"Blocked/Forbidden: {stats['forbidden']}")
        print(f"Empty/Short:       {stats['empty']}")
        print(f"Extraction Error:  {stats['error']}")

    except json.JSONDecodeError:
        print("\n[!] Error: Output was not valid JSON.")
    except Exception as e:
        print(f"\n[!] Unexpected Error: {e}")


if __name__ == "__main__":
    if "SEARXNG_BASE_URL" not in os.environ:
        print("Error: Please set 'SEARXNG_BASE_URL' environment variable.")
    else:
        asyncio.run(main())