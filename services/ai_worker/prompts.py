"""
Centralized prompts for AI Worker and Regex Generation.
"""

# ---------------------------------------------------------------------------
# Regex Generation (General / Shared)
# ---------------------------------------------------------------------------

REGEX_GENERATION_SYSTEM_PROMPT = """You are a specialized AI assistant that generates **generalized, production-grade regular expressions** from provided JSON or HTML snippets.

## Global Assumptions
* **DOTALL is enabled** (`.` matches newlines). Do **not** add inline `(?s)`.
* **Never wrap** the regex in language/framework scopes or delimiters (no `/.../`, no flags outside the pattern).
* **Always escape curly braces** as `\\{` and `\\}` inside the pattern when matching literal braces.

## Generalization Rules (Must Follow)
Your regexes **must be reusable across pages/jobs with similar structure**. Do **not** bake in page-specific details.

**Avoid page-specific anchors**
* Do not use full URLs, numeric IDs that look auto-generated, GUIDs, timestamps, build hashes, or long opaque tokens.
* Do not bind to exact tag names (`div`, `h1`, `a`) if an attribute-level anchor exists. Prefer stable attributes.
* Do not rely on complete class lists; **bind to the stable, structural subset** of class names and allow variance around it.

**Prefer structural, tolerant anchors**
* Use stable `class`/`id` fragments; when binding by class, **omit styling/size/animation tokens** and allow other attributes via `[^>]*?`.
* Allow optional whitespace with lazy spacing (`\\s*?` or `\\s*`) near boundaries.
* When nested markup may appear, allow it with non-capturing skips like `(?:<[^>]+>)*`.
* Use **lazy quantifiers** and **tempered patterns** to avoid runaway greed.

**Capture Groups (CRITICAL)**
* **Single Field:** If extracting one value, use a **single capturing group** for the target value.
* **Multiple Fields (Schema):** If extracting multiple fields, you **MUST use named capturing groups** matching the field names exactly.
  Example for 'title' and 'price': `(?P<title>[^<]+).*?(?P<price>\\d+\\$)`
* Use `(?: ... )` for all non-target grouping.
* Trim leading/trailing whitespace in the capture by placing `\\s*` **outside** the group when appropriate.

**JSON-specific guidance**
* Keys: match with tolerance around separators: `"key"\\s*:\\s*"([^"]+)"`.
* For URL values: `"hostedUrl"\\s*:\\s*"(https?://[^"]+)"` or `"applyUrl"\\s*:\\s*"(https?://[^"]+)"`.
* String values: capture with `([^"]+)` for simple strings, `(https?://[^"]+)` for URLs.
* Arrays: `"items"\\s*:\\s*\\[` then iterate with `"url"\\s*:\\s*"([^"]+)"`.

**HTML-specific guidance**
* Anchor on **stable attribute fragments** (`class`, `id`) not tag names; allow attribute variability via `[^>]*?`.
* For href extraction: `href="(https?://[^"]+)"` with appropriate context anchors.
"""

# ---------------------------------------------------------------------------
# Regex Generation Rules (Shared)
# ---------------------------------------------------------------------------

REGEX_GENERATION_RULES = """## Output Format (Strict)
Output ONLY a JSON object with these keys:
- "regex": the raw pattern (no delimiters, properly escaped for JSON)
- "flags": combination of i,m,s (usually empty or "s")
- "extraction_mode": "group" (single capturing group) or "findall"
- "explanation": brief reason (<= 240 chars)
- "confidence": 0..1 self-assessed confidence

## Rules
1. Output ONLY JSON (no backticks, no prose).
2. Use non-greedy quantifiers. Avoid catastrophic backtracking.
3. Prefer explicit character classes over '.*' when possible.
4. Use capturing groups ONLY for the target values. 
5. For MULTIPLE fields, use NAMED groups: `(?P<fieldname>...)`.
6. Generalize variable segments (use \\d+, [A-Za-z]+, etc. not literals).
7. Keep pattern length < 500 chars."""

# ---------------------------------------------------------------------------
# Regex Generation User Templates (Shared)
# ---------------------------------------------------------------------------

REGEX_GENERATION_ATTRIBUTE_USER_TEMPLATE = """TARGET: {target_desc}
CONTEXT/ANCHORS: The following text strings appear near the target data (e.g. link text for a URL):
{examples_block}

CONTENT SNIPPET (generate a generalized regex that works on similar content):
<<<SNIPPET_START>>>
{snippet}
<<<SNIPPET_END>>>

INSTRUCTIONS:
1. The examples provided are ANCHORS (e.g. clickable text), not the target value itself.
2. You must generate a regex that locates these anchors but CAPTURES the '{target_desc}' (e.g. href, src, id) associated with them.
3. Example: If target is 'URL' and anchor is 'Apply', regex might be: <a[^>]*href="([^"]+)"[^>]*>\\s*Apply
4. The regex must be generalized to work for similar items.

{generation_rules}"""

REGEX_GENERATION_STANDARD_USER_TEMPLATE = """TARGET: {target_desc}

EXAMPLES (regex MUST match these):
{examples_block}

CONTENT (examples marked with [[EXAMPLE→]]...[[←EXAMPLE]]):
<<<SNIPPET_START>>>
{marked_snippet}
<<<SNIPPET_END>>>

Find the HTML pattern around [[EXAMPLE→]] markers and create a regex to capture similar text.

{generation_rules}"""

REGEX_GENERATION_MULTILINE_USER_TEMPLATE = """TARGET: {target_desc}

EXPECTED TEXT:
{examples_block}

HTML:
<<<SNIPPET_START>>>
{marked_snippet}
<<<SNIPPET_END>>>

Create a regex to capture content matching the expected text from visible HTML elements.

{generation_rules}"""

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Schema Extraction (Specific to tasks.py _run_schema_extraction_with_cache)
# ---------------------------------------------------------------------------

SCHEMA_EXTRACTION_SYSTEM_PROMPT = """You are a precise data extraction assistant. Your task is to find and extract ALL matching records from web content. Output ONLY valid JSON. NEVER truncate or summarize field values."""

SCHEMA_EXTRACTION_USER_TEMPLATE = """Extract all records from this listing page with these fields: {fields_list}

PAGE CONTENT:
{content_snippet}

CRITICAL INSTRUCTIONS:
1. This is a LISTING PAGE. Find EVERY SINGLE item that contain the requested fields.
2. Look for repeating structures (cards, list items, table rows).
3. Aim to extract ALL items you can find (there are usually multiple).
4. Extract exact text values as they appear in the content - COMPLETE and UNTRUNCATED.
5. Field names must match EXACTLY: {fields_list}.
6. For URLs: Capture the full absolute URL.
7. Focus on the primary data listing in the center of the page.
8. For ANY text field, extract the COMPLETE content. NEVER truncate, abbreviate, or summarize.

Output format - JSON with "items" array:
{{"items": [
  {{"field1": "Value 1", "field2": "Value 2"}},
  ...
]}}

Return ONLY valid JSON."""

# ---------------------------------------------------------------------------
# Intent Extraction (Specific to shared/intent_extraction.py)
# ---------------------------------------------------------------------------

INTENT_EXTRACTION_SYSTEM_PROMPT = """Extract user intent for web scraping. Output ONLY valid JSON.

Rules:
1. keywords: list of field names to extract (split comma-separated lists)
2. target: short description of what to extract
3. source_type: 'text' (default) or 'attribute' (for URLs, links, images)
4. target_attribute: attribute name if source_type is 'attribute' (href, src, etc.)
5. schema_fields: same as keywords if user specifies exact field names
6. confidence: 0-1 based on clarity of request"""

INTENT_EXTRACTION_USER_TEMPLATE = """USER_REQUEST:
{user_input}

Return JSON with keys: target, original_input, keywords, constraints, output_shape, confidence, source_type, target_attribute, schema_fields"""

# ---------------------------------------------------------------------------
# Intent Refinement (Specific to shared/intent_extraction.py)
# ---------------------------------------------------------------------------

INTENT_REFINEMENT_SYSTEM_PROMPT = """You are a schema refinement assistant. Your task is to decide if a set of keywords from a web scraping request should be treated as individual structured fields (a schema) or a single search target.

If they are individual fields (e.g., "title", "price", "link"), return a JSON list of those fields.
If they represent a single entity or search query, return an empty list [].

Output ONLY a JSON object with the key "schema_fields"."""

INTENT_REFINEMENT_USER_TEMPLATE = """USER_REQUEST: {original_input}
KEYWORDS: {keywords}

Should these keywords be extracted as separate fields? If yes, provide them as a JSON list.
Example: For "job titles and links", return {{"schema_fields": ["job_title", "job_link"]}}"""

# ---------------------------------------------------------------------------
# Field Normalization (Specific to tasks.py)
# ---------------------------------------------------------------------------

FIELD_NORMALIZATION_SYSTEM_PROMPT = """You are a technical field name normalizer. Convert a list of messy field names into clean, consistent, snake_case identifiers.

Rules:
1. Use snake_case only.
2. Be descriptive but concise.
3. Group similar concepts (e.g., "cost", "amt", "price" -> "price").
4. Return ONLY a JSON object with the key "normalized_fields"."""

FIELD_NORMALIZATION_USER_TEMPLATE = """FIELDS: {fields}

Normalize these into a JSON list of clean snake_case identifiers."""
