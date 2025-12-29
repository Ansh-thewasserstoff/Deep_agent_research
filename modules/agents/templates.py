"""
Shared prompt fragments and instructions for the agent team.
"""

CITATION_RULES = """
## CITATION & OFFLOADING PROTOCOL
1. **Source IDs**: Assign [src_1], [src_2], etc., to every URL found.
2. **Registry Management (Lazy Init)**: 
   - ATTEMPT to read `/sources/registry.json`.
   - **IF IT FAILS OR RETURNS ERROR**: Assume the registry is empty `{}`.
   - **UPDATE**: Add your new source `{ID: {url, title, summary}}` to the object.
   - **WRITE**: Save the valid JSON back to `/sources/registry.json`.
   - **CRITICAL**: Do NOT try to append text. Read -> Update Dict -> Write.
3. **Context Isolation**: NEVER return raw search text in chat. 
4. **File-First Reporting**: Always point the Lead Agent to a specific file in `/research/`.
## STRICT CITATION PROTOCOL (MANDATORY)
1. **Source IDs**: You will receive data with tags like `[src_1]`, `[src_2]`.
2. **Sentence-Level Attribution**: 
   - Every single sentence that contains a fact MUST end with its specific source ID.
   - **Bad**: "The sky is blue and grass is green. [src_1]"
   - **Good**: "The sky is blue [src_1]. However, grass is green [src_2]."
3. **Multi-Source**: If a fact is supported by multiple sources, cite them all: "AI is growing [src_1, src_4]."
4. **Unknowns**: If a fact has no source in your context, DO NOT write it.
5. **Preservation**: When summarizing or rewriting, you MUST copy the `[src_X]` tag to the new sentence.
"""

FILE_NAMING_PROTOCOL = """
## FILE NAMING
- Use descriptive filenames: `/research/search_<topic>.md` or `/research/summary_<topic>.md`.
- VFS Paths: Treat `/research/` and `/sources/` as virtual prefixes. You do not need to create these directories.
"""

REASONING_FOOTER = """
Think step-by-step. 
1. Check if required files exist before reading.
2. If a search result contradicts a previous finding, log it in '/research/conflicts.md'.
"""