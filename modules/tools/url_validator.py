import httpx
from langchain_core.tools import tool


@tool
async def url_validator_tool(url: str) -> str:
    """
    Validates a URL's status and returns a text preview.
    Use this to verify sources before finalizing a citation.
    """
    headers = {
        "User-Agent": "DeepResearchAgent/1.0",
        "Accept": "text/html,application/xhtml+xml"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)

            if response.status_code >= 400:
                return f"VALIDATION_FAILED: HTTP {response.status_code}"

            # Simple check for 'soft' 404s in content
            text_preview = response.text[:1000].lower()
            if "404" in text_preview and "not found" in text_preview:
                return "VALIDATION_FAILED: Content suggests 404 Not Found."

            return f"VALIDATION_SUCCESS: Status 200. Preview: {text_preview[:300]}..."

    except Exception as e:
        return f"VALIDATION_ERROR: {str(e)}"