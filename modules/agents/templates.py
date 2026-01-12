"""
Shared prompt fragments and instructions for the agent team.
"""

CITATION_RULES = """
## CITATION & ATTRIBUTION PROTOCOL
1. **Use Provided Tags**: The search tool provides data pre-tagged with `[src_X]` IDs. You must use these exact tags.
2. **Sentence-Level Citation**: 
   - Every single sentence that contains a fact MUST end with its specific source ID.
   - **Bad**: "The sky is blue and grass is green. [src_1]"
   - **Good**: "The sky is blue [src_1]. However, grass is green [src_2]."
3. **Tag Preservation**: When summarizing or rewriting, you MUST copy the `[src_X]` tag to the new sentence. Do not drop tags.
4. **No Registry Management**: Do NOT create or update a `/sources/registry.json` file. Focus only on writing the content with correct tags.
"""

FILE_NAMING_PROTOCOL = """
## FILE NAMING
- Use descriptive filenames: `/memories/research/findings_<topic>.md` or `/memories/research/summary_<topic>.md`.
- **Persistence**: ALWAYS save important findings to `/memories/` so the Analyst can see them.
"""

REASONING_FOOTER = """
Think step-by-step. 
1. Check if required files exist in `/memories/` before reading.
2. If a search result contradicts a previous finding, note the conflict.
"""