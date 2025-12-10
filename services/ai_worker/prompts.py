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

EXAMPLES (the regex MUST capture each of these exactly as shown):
{examples_block}

CONTENT SNIPPET (examples are marked with [[EXAMPLE→]]...[[←EXAMPLE]]):
<<<SNIPPET_START>>>
{marked_snippet}
<<<SNIPPET_END>>>

INSTRUCTIONS:
1. Find the [[EXAMPLE→]]...[[←EXAMPLE]] markers in the snippet.
2. Look at the HTML tags/classes IMMEDIATELY before each marker - that's your anchor.
3. Build a regex using THOSE specific tags/classes to capture text in that position.
4. Do NOT use other classes from elsewhere in the snippet.

{generation_rules}"""

REGEX_GENERATION_MULTILINE_USER_TEMPLATE = """TARGET: {target_desc}

EXPECTED TEXT CONTENT (this is the inner text, not exact HTML):
{examples_block}

HTML SNIPPET:
<<<SNIPPET_START>>>
{marked_snippet}
<<<SNIPPET_END>>>

CRITICAL INSTRUCTIONS:
1. ONLY match visible HTML elements (<h1>, <p>, <div>, <li>, etc.) - NOT JSON or script content.
2. IGNORE any embedded JSON like "title":"..." - these are data structures, not visible text.
3. Look for the EXACT example text within HTML tags in the snippet.
4. For titles: <h1[^>]*>([^<]+)</h1> or similar
5. For descriptions: find the container div/section with a stable class, then capture its contents.
6. The captured text MUST match the examples provided.

{generation_rules}"""

# ---------------------------------------------------------------------------
# HTML Field Regex Generation (Specific to tasks.py _generate_field_regex)
# ---------------------------------------------------------------------------

HTML_FIELD_REGEX_SYSTEM_PROMPT = (
    "You are a regex expert. Your task is to generate STRUCTURAL regex patterns for HTML data extraction. "
    "CRITICAL RULES:\n"
    "1. NEVER use literal text from the page (words, phrases, labels) in your regex.\n"
    "2. ONLY anchor on HTML class/id attributes that are specific to the data structure.\n"
    "3. Use single capturing group for the target value.\n"
    "4. Output ONLY valid JSON: {\"regex\": \"...\", \"flags\": \"s\"}\n"
    "5. Return empty regex if no reliable structural pattern exists."
)

HTML_FIELD_REGEX_USER_TEMPLATE = """Generate a regex to extract ALL "{field_name}" values from HTML.

EXAMPLE VALUES THAT MUST BE MATCHED (there are {example_count} total):
{examples_text}

HTML SNIPPETS WHERE THESE VALUES APPEAR:
{snippet_text}

## STRICT RULES - FOLLOW EXACTLY

### Global Assumptions
* DOTALL is enabled (`.` matches newlines). Do NOT add inline `(?s)`.
* Always escape curly braces as `\\{{` and `\\}}`.

### Output Format
Output ONLY: {{"regex": "YOUR_PATTERN", "flags": "s"}}
No explanations. No comments. No extra keys.

### CRITICAL: Avoid Literal Text Anchors
❌ NEVER include literal words/phrases from the page content in your regex.
❌ NEVER use text like "Būklė", "Price:", "Posted:", category names, or any natural language text.
❌ NEVER anchor on specific values that appear in the examples themselves.
❌ NEVER use Unicode characters from the page content.

### CRITICAL: Avoid Page-Specific Anchors  
❌ Do NOT use full URLs, numeric IDs, GUIDs, timestamps, hashes.
❌ Do NOT use overly generic class names like "title", "text", "content" alone - they match too many elements.
❌ Do NOT bind to complete class lists; use only the most specific/stable fragment.

### MUST: Use Structural Anchors Only
✅ Anchor ONLY on stable class/id attribute fragments that are specific to the data type.
✅ Look for class names that indicate the semantic meaning (e.g., "listing-title", "item-price", "post-date").
✅ Use `[^>]*?` to allow attribute variability.
✅ Use `[^<]+?` for text content, `[^"]+` for attribute values.

### Pattern Templates
Text in element: `class="specific-class[^"]*"[^>]*>\\s*([^<]+?)\\s*</`
Attribute value: `class="specific-class[^"]*"[^>]*?href="([^"]+)"`

### Failure Behavior
If you cannot find a reliable structural anchor, output: {{"regex": "", "flags": "s"}}
It is BETTER to return empty than to create a brittle regex.

Your JSON response:"""

# ---------------------------------------------------------------------------
# Attribute Extraction Regex (Specific to tasks.py _run_attribute_extraction)
# ---------------------------------------------------------------------------

ATTRIBUTE_EXTRACTION_USER_TEMPLATE = """Analyze this HTML and generate a regex to extract '{attribute}' attribute values for '{target}'.

CRITICAL REQUIREMENTS:
1. The regex must match the HTML STRUCTURE/PATTERN, NOT the specific text content
2. DO NOT include any specific text like job titles, names, or dynamic content in the regex
3. Match based on: tag names, CSS classes, parent elements, attribute patterns
4. The regex should work even when the page content changes (new jobs, products, etc.)
5. Capture ONLY the '{attribute}' attribute value

Example of WRONG regex: <a href="([^"]+)"[^>]*>.*?Senior Developer.*?</a>
Example of CORRECT regex: <a[^>]*class="job-link"[^>]*href="([^"]+)"[^>]*>

The visible text in target elements includes (for context only, DO NOT embed in regex):
{text_examples}

HTML SAMPLE:
{combined_snippet}

Analyze the HTML structure around these elements and create a STRUCTURAL pattern.
Return ONLY a JSON object:
{{"regex": "structural_pattern", "flags": "is", "explanation": "what structural pattern you identified"}}"""

# ---------------------------------------------------------------------------
# Direct Attribute Extraction (Specific to tasks.py _extract_attribute_via_llm)
# ---------------------------------------------------------------------------

ATTRIBUTE_EXTRACTION_DIRECT_USER_TEMPLATE = """I need to extract '{attribute}' attributes related to '{target}'.
The text examples associated with these elements are: {text_examples}
Find the values of the '{attribute}' attribute for elements matching these text descriptions.
Return ONLY a JSON object: {{"values": ["value1", "value2"]}}
If none found, return {{"values": []}}.

HTML SNIPPETS:
{combined_snippets}"""

# ---------------------------------------------------------------------------
# Value Filtering (Specific to tasks.py _filter_values_via_llm)
# ---------------------------------------------------------------------------

FILTER_VALUES_USER_TEMPLATE = """I am extracting '{target}' from a webpage.
I found the following candidate URLs/values.

FILTER RULES:
- Keep ONLY values that are specific '{target}' (e.g. individual job posting URLs)
- REMOVE generic navigation links (e.g. '/careers/', '/jobs/', '/about/')
- REMOVE image URLs, javascript links, CSS files
- REMOVE social media share links
- For job URLs: keep URLs with specific job IDs/slugs, remove generic listing pages

CANDIDATES: {chunk}

Return ONLY a JSON object: {{"valid_values": ["val1", "val2"]}}
Return only the values that are specific '{target}', not navigation links."""

# ---------------------------------------------------------------------------
# Candidate Selection (Specific to tasks.py _select_best_candidate_via_llm)
# ---------------------------------------------------------------------------

SELECT_BEST_CANDIDATE_USER_TEMPLATE = """TARGET: {target}
KEYWORDS: {keywords}
We found these content snippets containing the target data. Which one is the best source for regex extraction?
CANDIDATES:
{options}

Return JSON: {{'best_option_index': int, 'reason': str}}"""

# ---------------------------------------------------------------------------
# Text Matching (Specific to tasks.py _find_matching_text_via_llm)
# ---------------------------------------------------------------------------

FIND_MATCHING_TEXT_ATTRIBUTE_USER_TEMPLATE = """I need to find '{target}' from this page, which are likely in HTML attributes.
Identify 3-5 distinct visible TEXT labels that represent or anchor these items.
For links, this is the clickable text. For images, this might be the caption or alt text.
Return the EXACT text labels as they appear in the content.
Do NOT return URLs/attributes - return the visible text.
Return ONLY a JSON object: {{"examples": ["Label 1", "Label 2"]}}
If none found, return {{"examples": []}}.

CONTENT:
{snippet}"""

FIND_MATCHING_TEXT_CONTENT_USER_TEMPLATE = """I need to extract '{target}' from the text content below.
Identify 3-5 distinct, concrete examples of text that represent '{target}'.
Return the EXACT substrings as they appear in the content.
These should be specific items, NOT generic phrases.
Return ONLY a JSON object: {{"examples": ["example1", "example2"]}}
If none found, return {{"examples": []}}.

CONTENT:
{snippet}"""

# ---------------------------------------------------------------------------
# Structured Examples (Specific to tasks.py _find_structured_examples_via_llm)
# ---------------------------------------------------------------------------

FIND_STRUCTURED_EXAMPLES_USER_TEMPLATE = """I need to extract structured records containing these fields: {fields_str}

Find 2-3 COMPLETE example records from the text below.
Each record MUST be a JSON object with ALL the fields mentioned above as keys.

Return ONLY a JSON object in this EXACT format:
{{"examples": [{{"field1": "value1", "field2": "value2"}}, {{"field1": "value3", "field2": "value4"}}]}}

CRITICAL: Each example MUST be a JSON object with the field names as keys, NOT plain text.
If a field value is not found, use empty string for that field.

CONTENT:
{snippet}"""

# ---------------------------------------------------------------------------
# Schema Extraction (Specific to tasks.py _run_schema_extraction_with_cache)
# ---------------------------------------------------------------------------

SCHEMA_EXTRACTION_SYSTEM_PROMPT = """You are a data extraction assistant. Extract ALL structured data from web page content. If there are multiple items, return them ALL as a JSON array. Output ONLY valid JSON."""

SCHEMA_EXTRACTION_USER_TEMPLATE = """Extract the following fields from the page content:
FIELDS TO EXTRACT: {fields_list}

PAGE CONTENT:
{content_snippet}

INSTRUCTIONS:
1. Find ALL items/records that match the requested fields.
2. If there are MULTIPLE items (like a list of products, jobs, etc.), return a JSON array with ALL of them.
3. For each item, extract the EXACT values from the page content.
4. If a field is not found for an item, use empty string.
5. Return ONLY valid JSON - either an array of objects OR a single object.

Example for MULTIPLE items:
{{"items": [{{"name": "Product 1", "price": "$10"}}, {{"name": "Product 2", "price": "$20"}}]}}

Example for SINGLE item:
{{"job_title": "Software Engineer", "city": "New York"}}

Return ONLY the JSON, no other text."""

# ---------------------------------------------------------------------------
# Intent Extraction (Specific to shared/intent_extraction.py)
# ---------------------------------------------------------------------------

INTENT_EXTRACTION_SYSTEM_PROMPT = """You are an intent extraction engine. Given a free-form user request about web data scraping or extraction, you MUST output ONLY strict JSON matching the required schema. Do not include any commentary, markdown fences, or explanations.

Rules:
1. Output ONLY valid JSON.
2. If a field is unknown or not present, use an empty list for arrays or an empty string for strings.
3. confidence is a float 0..1 (use 0.5 if uncertain).
4. keywords should be individual field names/phrases to extract. If user lists fields like 'job_title, country, city', split them into ['job_title', 'country', 'city'].
5. constraints are specific filters (e.g., geography, price range, date window).
6. output_shape is a concise description of the desired result form.
7. target should be a short noun phrase (e.g., 'job details', 'product info').
8. source_type should be 'text' or 'attribute'. Use 'attribute' if the user wants URLs, links, images, IDs.
9. target_attribute should be the attribute name (e.g., 'href', 'src', 'data-id') if source_type is 'attribute', otherwise null.
10. schema_fields: If user provides specific field names (like 'job_title, country, city'), extract them as a list. These are the exact field names for the output JSON."""

INTENT_EXTRACTION_USER_TEMPLATE = """USER_REQUEST:
{user_input}

Return JSON with keys: target, original_input, keywords, constraints, output_shape, confidence, source_type, target_attribute, schema_fields"""
