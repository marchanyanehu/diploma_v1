# AI Prompts & System Instructions

This document describes the AI prompt engineering approach used in the Intelligent Web Data Aggregator. Each prompt is designed with specific goals, constraints, and rationale.

## Table of Contents

1. [Prompt Engineering Principles](#prompt-engineering-principles)
2. [Intent Extraction](#intent-extraction)
3. [Source Disambiguation](#source-disambiguation)
4. [RegEx Generation](#regex-generation)
5. [Edge Case Handling](#edge-case-handling)
6. [Model Selection Rationale](#model-selection-rationale)

---

## Prompt Engineering Principles

Our prompts follow these core principles:

| Principle | Implementation | Why |
|-----------|----------------|-----|
| **Strict JSON Output** | "Output ONLY valid JSON" | Ensures machine-parseable responses |
| **No Commentary** | "No markdown fences or explanations" | Prevents parsing errors |
| **Role Assignment** | "You are a..." | Focuses model behavior |
| **Default Values** | "use empty list/string if unknown" | Handles missing data gracefully |
| **Confidence Scoring** | `confidence: 0.0-1.0` | Enables quality filtering |
| **Few-Shot Examples** | Provide target examples in prompts | Improves accuracy |

---

## Intent Extraction

### Purpose

Transforms a user's natural language request into a structured representation that guides the web scraping process.

### Design Goals

1. **Extract the target** - What the user wants to find (e.g., "product prices", "job titles")
2. **Identify keywords** - Search terms to locate relevant page sections
3. **Detect constraints** - Filters like geography, date range, price limits
4. **Determine output shape** - How results should be structured

### System Prompt

```text
You are an intent extraction engine. Given a free-form user request about web data scraping or extraction, you MUST output ONLY strict JSON matching the required schema. Do not include any commentary, markdown fences, or explanations.

Rules:
1. Output ONLY valid JSON.
2. If a field is unknown or not present, use an empty list for arrays or an empty string for strings.
3. confidence is a float 0..1 (use 0.5 if uncertain).
4. keywords should be lowercased single or multi-word tokens (no duplicates).
5. constraints are specific filters (e.g., geography, price range, date window).
6. output_shape is a concise description of the desired result form.
7. target should be a short noun phrase (e.g., 'job links', 'product prices').
```

### Why This Design

| Element | Rationale |
|---------|-----------|
| "intent extraction engine" role | Narrows the model's focus to semantic analysis |
| "ONLY strict JSON" | Prevents chatty responses that break parsing |
| Lowercased keywords rule | Ensures consistent matching in HTML search |
| Confidence 0.5 default | Allows processing to continue with uncertainty flagged |
| "short noun phrase" for target | Creates concise, actionable targets for regex generation |

### Example Input/Output

**Input**: "Find all remote Python developer jobs paying over $100k"

**Output**:
```json
{
  "target": "job listings",
  "keywords": ["python", "developer", "remote"],
  "constraints": ["salary > $100k", "remote only"],
  "output_shape": "list of job titles with salaries",
  "confidence": 0.85
}
```

### Integration

Used by `services/ai_worker/tasks.py` during `process_request_full` to decide target, keywords, schema_fields, and attribute targets.

---

## Source Disambiguation

### Purpose

When multiple HTML sections contain potentially relevant content, this prompt helps the AI select the most likely source for the target data.

### Design Goals

1. **Reduce false positives** - Avoid extracting from navbars, footers, ads
2. **Focus on main content** - Identify the primary data list/table
3. **Provide reasoning** - Enable human review of decisions

### Prompt Template

```text
TARGET: {target}
KEYWORDS: {keywords}
We found these text fragments in the HTML. Which one seems to be part of the main list/data area we want to extract?
CANDIDATES:
Option 0: ...snippet...
Option 1: ...snippet...

Return JSON: {'best_option_index': int, 'reason': str}
```

### Why This Design

| Element | Rationale |
|---------|-----------|
| Numbered options | Enables clear selection via index |
| Context: "main list/data area" | Guides away from navigation/footer |
| "reason" field | Provides explainability for debugging |
| Snippet preview format | Shows enough context without overwhelming |

### Example

**Candidates**:
- Option 0: "Home | About | Contact | Careers"
- Option 1: "Software Engineer - $120k - New York | Data Scientist - $130k - Remote"
- Option 2: "© 2024 Company Inc. Privacy Policy"

**Response**:
```json
{
  "best_option_index": 1,
  "reason": "Option 1 contains job listings with titles, salaries, and locations matching the target 'job listings'. Options 0 and 2 are navigation and footer elements."
}
```

### Integration

Used by `shared/example_finder.py` when multiple candidates match keyword searches, called from `services/ai_worker/tasks.py` in `_select_best_candidate_via_llm()`.

---

## RegEx Generation

### Purpose

Generates regular expressions to extract structured data from HTML/JSON content based on user intent and example snippets.

### Location

**Module**: `shared/regex_generation.py`

**Key Functions**:
- `build_generation_messages()` - Creates initial prompt for regex generation
- `build_refinement_messages()` - Creates fix-it prompts when regex fails validation
- `validate_regex()` - Tests pattern against examples without LLM
- `iterative_regex_generation()` - Main loop: Generate → Validate → Refine (up to 3 iterations)

**Called From**: `services/ai_worker/tasks.py` in `_run_single_field_extraction()`

### Design Goals

1. **Match provided examples** - Regex MUST match all given examples
2. **Avoid overfitting** - Don't match irrelevant surrounding content
3. **Generalization** - Patterns should work across similar pages, not just the current one
4. **Efficiency** - Use non-greedy quantifiers, avoid catastrophic backtracking
5. **Consistency** - Always return same JSON schema

### Snippet Strategy

The system **never sends full HTML to the LLM**. Instead, it extracts focused snippets:

| Snippet Type | Size | Purpose |
|--------------|------|---------|
| Full content | Unlimited | Kept for regex application (pure Python, no LLM) |
| LLM text prompt | 32KB max | Clean text sent to LLM for example finding |
| Attribute prompt | 15KB max | HTML snippets for URL/attribute extraction |
| `extract_snippet_around_example()` | 600 chars default | Line-aware extraction preserving example intact |
| `micro_snippet` | 150 chars | Focused HTML context for precise regex generation |
| `best_snippet` | 4000 chars | Larger context as fallback |

This architecture means **page size doesn't matter** - a 10MB page works just as well as a 10KB page.

### System Prompt

```text
You are a specialized AI assistant that generates **generalized, production-grade regular expressions** from provided JSON or HTML snippets.

## Global Assumptions
* **DOTALL is enabled** (`.` matches newlines). Do **not** add inline `(?s)`.
* **Never wrap** the regex in language/framework scopes or delimiters (no `/.../`).
* **Always escape curly braces** as `\\{` and `\\}` inside the pattern.

## Generalization Rules (Must Follow)
Your regexes **must be reusable across pages/jobs with similar structure**.

**Avoid page-specific anchors**
* Do not use full URLs, numeric IDs, GUIDs, timestamps, build hashes.
* Do not bind to exact tag names if an attribute-level anchor exists.

**Prefer structural, tolerant anchors**
* Use stable `class`/`id` fragments; allow other attributes via `[^>]*?`.
* Allow optional whitespace with lazy spacing (`\\s*?` or `\\s*`).
* Use **lazy quantifiers** and **tempered patterns**.

**Capture only what you need**
* Use a **single capturing group** for the target value.
* Use `(?: ... )` for all non-target grouping.
```

### User Prompt Template

```text
TARGET: {target_desc}

EXAMPLES (the regex MUST match each):
- example 1
- example 2

SNIPPET (context only, do NOT overfit to unrelated text):
<<<SNIPPET_START>>>
{snippet}
<<<SNIPPET_END>>>

Produce JSON with keys: regex, flags, extraction_mode, explanation, confidence.

BASE RULES:
1. Output ONLY JSON (no backticks).
2. Use non-greedy quantifiers where possible.
3. Prefer explicit character classes.
4. extraction_mode: "findall" for multiple matches, "group" for single with captures.
5. flags: combination of i,m,s (usually empty or "s").
```

### Why This Design

| Element | Rationale |
|---------|-----------|
| "rigorous" role assignment | Emphasizes precision over creativity |
| "MUST match each" examples | Hard requirement prevents hallucinated patterns |
| "do NOT overfit" warning | Common failure mode addressed explicitly |
| Delimiter `<<<SNIPPET_START>>>` | Clearly separates code from instructions |
| Non-greedy quantifiers rule | Prevents `.*` from matching entire page |
| Confidence field | Enables automatic retry when confidence is low |
| Generalization rules | Ensures cached regexes work on future page visits |

### Validation Heuristics

Before accepting a generated regex, `validate_regex()` enforces:

| Check | Threshold | Reason |
|-------|-----------|--------|
| Pattern length | < 500 chars | Reject likely hallucinations |
| Catastrophic backtracking | No `(.+)+` or `(.*)*` | Prevent runaway regex |
| Match limit | ≤ 200 matches | Avoid memory blow-up |
| Example coverage | 100% of examples | Must match ALL provided examples |
| Duplicate ratio | < 80% duplicates | Reject overly broad patterns |
| Average match length | 2-2000 chars | Filter garbage matches |

### Output Schema

```json
{
  "regex": "(?:Software|Data)\\s+Engineer\\s+-\\s+\\$([\\d,]+)",
  "flags": ["i"],
  "extraction_mode": "findall",
  "explanation": "Matches job titles followed by salary amounts",
  "confidence": 0.92
}
```

### Edge Cases Handled

| Case | Handling |
|------|----------|
| HTML entities | Instruct to match `&nbsp;`, `&amp;` etc. |
| Unicode characters | Use `.` with `s` flag or `\S+` |
| Variable whitespace | `\s+` or `\s*` between tokens |
| Optional elements | Non-capturing groups with `?` |

### Integration

Used by `shared/regex_generation.py` in `generate_regex_for_target()`. Results are cached in `ParserCache` table for reuse on the same domain/keywords.

---

## Edge Case Handling

The prompt system addresses various edge cases through specific design decisions:

### 1. Empty or Minimal Input

**Problem**: User sends very short or vague prompts like "get data"

**Solution**:
- Input sanitization requires minimum 5 characters
- Intent extraction produces low confidence (≤ 0.3) for vague inputs
- System returns helpful error: "Please be more specific about what data you want to extract"

### 2. Multiple Data Types Requested

**Problem**: User wants "prices AND reviews AND images" in one request

**Solution**:
- Intent extraction identifies primary target (highest keyword density)
- Constraints field captures secondary requirements
- System focuses on one data type per extraction pass

### 3. No Matching Content on Page

**Problem**: Page doesn't contain requested data type

**Solution**:
- Example finder returns empty list
- System returns structured empty result with explanation
- Confidence score reflects extraction uncertainty

### 4. Malformed JSON from LLM

**Problem**: LLM occasionally outputs markdown fences or extra text

**Solution**:
```python
# Strip markdown code fences if present
if response.startswith("```"):
    response = response.split("```")[1]
    if response.startswith("json"):
        response = response[4:]
```

### 5. Prompt Injection Attempts

**Problem**: User tries "ignore previous instructions"

**Solution**:
- Pre-LLM sanitization removes injection patterns
- Clear role definition in system prompt
- Separation of user data from instructions via delimiters

---

## Model Selection Rationale

### Current Configuration

| Provider | Model | Use Case |
|----------|-------|----------|
| **Google Gemini** | gemini-2.0-flash | Primary (intent extraction, regex generation) |
| **OpenAI** | gpt-4o-mini | Fallback provider |

### Why Gemini Flash?

1. **Cost Efficiency**: Lower cost per token than GPT-4
2. **Speed**: Flash models optimized for low latency
3. **JSON Mode**: Reliable structured output
4. **Context Window**: 1M tokens handles large HTML snippets

### Why LiteLLM Abstraction?

```python
# Easy provider switching via environment variable
GEMINI_API_KEY=xxx  # Uses Gemini
OPENAI_API_KEY=xxx  # Falls back to OpenAI
```

Benefits:
- **No vendor lock-in**: Switch providers without code changes
- **Automatic retries**: Built-in retry logic with exponential backoff
- **Unified interface**: Same code for all providers

### Temperature Settings

| Task | Temperature | Why |
|------|-------------|-----|
| Intent Extraction | 0.1 | Deterministic, structured output |
| Regex Generation | 0.0 | Precise, reproducible patterns |
| Source Disambiguation | 0.2 | Some creativity in reasoning |

---

## Prompt Evolution Log

| Version | Date | Change | Reason |
|---------|------|--------|--------|
| 1.0 | Initial | Basic JSON output request | — |
| 1.1 | 2024-Q1 | Added "no code fences" rule | LLM wrapped JSON in ``` |
| 1.2 | 2024-Q2 | Added confidence scoring | Enable quality filtering |
| 1.3 | 2024-Q3 | Added delimiter markers | Separate code from instructions |
| 1.4 | 2024-Q4 | Added edge case handling | Improved robustness |

---

*See also: [Architecture](ARCHITECTURE.md) | [Limitations](SYSTEM_LIMITATIONS.md) | [Examples](EXAMPLE_DIALOGS.md)*