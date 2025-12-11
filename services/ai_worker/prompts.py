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

**Capture only what you need**
* Use a **single capturing group** for the target value. Use `(?: ... )` for all non-target grouping.
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
4. Single capturing group for the target value only.
5. Generalize variable segments (use \\d+, [A-Za-z]+, etc. not literals).
6. Keep pattern length < 500 chars."""

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
# HTML Field Regex Generation (Specific to tasks.py _generate_field_regex)
# ---------------------------------------------------------------------------

HTML_FIELD_REGEX_SYSTEM_PROMPT = (
    "You are a regex expert. Generate STRUCTURAL HTML regex patterns.\n"
    "RULES:\n"
    "1. NEVER use literal text from the page in your regex\n"
    "2. ONLY anchor on class/id attributes\n"
    "3. Single capturing group\n"
    "4. Output ONLY: {\"regex\": \"...\", \"flags\": \"s\"}\n"
    "5. Return empty regex if no reliable pattern exists"
)

HTML_FIELD_REGEX_USER_TEMPLATE = """Extract "{field_name}" values from HTML.

EXAMPLES ({example_count} total):
{examples_text}

HTML SNIPPETS:
{snippet_text}

RULES:
- DOTALL enabled (. matches newlines)
- Escape curly braces: \\{{, \\}}
- Output ONLY: {{"regex": "YOUR_PATTERN", "flags": "s"}}

AVOID:
❌ Literal text/words from page content
❌ Specific values from examples
❌ Full URLs, IDs, GUIDs, timestamps
❌ Generic class names like "title", "text" alone

USE:
✅ Stable class/id fragments specific to data type
✅ [^>]*? for attribute variability
✅ [^<]+? for text, [^"]+ for attributes

PATTERN TEMPLATES:
Text: class="specific-class[^"]*"[^>]*>\\s*([^<]+?)\\s*</
Attribute: class="specific-class[^"]*"[^>]*?href="([^"]+)"

If no reliable pattern: {{"regex": "", "flags": "s"}}

Your JSON:"""

# ---------------------------------------------------------------------------
# Attribute Extraction Regex (Specific to tasks.py _run_attribute_extraction)
# ---------------------------------------------------------------------------

ATTRIBUTE_EXTRACTION_USER_TEMPLATE = """Generate regex to extract '{attribute}' attribute for '{target}'.

RULES:
1. Match HTML STRUCTURE/PATTERN, NOT specific text content
2. Use tag names, CSS classes, parent elements - NOT job titles, names, etc.
3. Capture ONLY the '{attribute}' attribute value

✅ CORRECT: <a[^>]*class="job-link"[^>]*href="([^"]+)"[^>]*>
❌ WRONG: <a href="([^"]+)"[^>]*>.*?Senior Developer.*?</a>

Text labels (for context only, NOT for regex):
{text_examples}

HTML:
{combined_snippet}

Return: {{"regex": "structural_pattern", "flags": "is", "explanation": "brief explanation"}}"""

# ---------------------------------------------------------------------------
# Direct Attribute Extraction (Specific to tasks.py _extract_attribute_via_llm)
# ---------------------------------------------------------------------------

ATTRIBUTE_EXTRACTION_DIRECT_USER_TEMPLATE = """Extract '{attribute}' attribute values for elements related to '{target}'.

Text labels of target elements: {text_examples}

Find the '{attribute}' attribute values for these elements.

Return: {{"values": ["value1", "value2", ...]}}
If none found: {{"values": []}}

HTML:
{combined_snippets}"""

# ---------------------------------------------------------------------------
# Value Filtering (Specific to tasks.py _filter_values_via_llm)
# ---------------------------------------------------------------------------

FILTER_VALUES_USER_TEMPLATE = """Filter these values for '{target}':

Keep ONLY specific item values. Remove:
- Generic navigation/category links
- Static assets (images, CSS, JS)
- Social media/share links

CANDIDATES: {chunk}

Return: {{"valid_values": ["val1", "val2", ...]}}"""

# ---------------------------------------------------------------------------
# Candidate Selection (Specific to tasks.py _select_best_candidate_via_llm)
# ---------------------------------------------------------------------------

SELECT_BEST_CANDIDATE_USER_TEMPLATE = """Select the best content snippet for extracting '{target}' (keywords: {keywords}).

CANDIDATES:
{options}

Return: {{"best_option_index": int, "reason": "brief explanation"}}"""

# ---------------------------------------------------------------------------
# Text Matching (Specific to tasks.py _find_matching_text_via_llm)
# ---------------------------------------------------------------------------

FIND_MATCHING_TEXT_ATTRIBUTE_USER_TEMPLATE = """Find visible text labels for '{target}' elements.

Return 3-5 EXACT text labels as they appear (the clickable/visible text, NOT URLs).

Format: {{"examples": ["Label 1", "Label 2", ...]}}
If none found: {{"examples": []}}

CONTENT:
{snippet}"""

FIND_MATCHING_TEXT_CONTENT_USER_TEMPLATE = """Find examples of '{target}' in the content below.

Return 3-5 EXACT text values as they appear in the content.

Format: {{"examples": ["value1", "value2", ...]}}
If none found: {{"examples": []}}

CONTENT:
{snippet}"""

# ---------------------------------------------------------------------------
# Structured Examples (Specific to tasks.py _find_structured_examples_via_llm)
# ---------------------------------------------------------------------------

FIND_STRUCTURED_EXAMPLES_USER_TEMPLATE = """Extract structured records with these fields: {fields_str}

From the content below, find 3-5 COMPLETE records. Each record should be a JSON object.

Return JSON format:
{{"examples": [{{"field1": "value1", "field2": "value2"}}, ...]}}

Rules:
- Extract EXACT values as they appear in the content
- If a field is missing for a record, use empty string ""
- Focus on the main repeating items (products, listings, entries)
- Skip navigation, headers, footers

CONTENT:
{snippet}"""

# ---------------------------------------------------------------------------
# Schema Extraction (Specific to tasks.py _run_schema_extraction_with_cache)
# ---------------------------------------------------------------------------

SCHEMA_EXTRACTION_SYSTEM_PROMPT = """You are a precise data extraction assistant. Your task is to find and extract ALL matching records from web content. Output ONLY valid JSON."""

SCHEMA_EXTRACTION_USER_TEMPLATE = """Extract records with these fields: {fields_list}

PAGE CONTENT:
{content_snippet}

CRITICAL INSTRUCTIONS:
1. Find ALL records/items that contain the requested fields - THIS IS A PRODUCT LISTING PAGE
2. Look for REPEATING structures (product cards, list items, article tags, divs with product data)
3. Extract EVERY SINGLE product you can find - aim for 20-30+ items if they exist
4. Do NOT stop after finding just a few items - scroll through all the content
5. Extract EXACT text values as they appear (titles, prices, etc.)
6. If a field is empty/missing for an item, use ""
7. Skip navigation menus, headers, footers, sidebars - focus ONLY on product listings

Output format - JSON with "items" array containing ALL products:
{{"items": [
  {{"title": "Product 1", "price": "10€"}},
  {{"title": "Product 2", "price": "20€"}},
  ... (continue with ALL remaining products)
]}}

REMINDER: Extract ALL products, not just 5-10. If you see 25 products, return all 25.
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
