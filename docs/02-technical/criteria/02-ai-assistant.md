# Criterion: AI Assistant / Chatbot (LLM Integration)

## Architecture Decision Record

### Status
**Status:** Accepted
**Date:** 2025-01-05

### Context
Traditional scrapers are brittle and require manual creation of RegEx or CSS selectors. We needed a way to allow non-technical users to describe what they want to extract in plain English and have the system autonomously figure out how to find that data on a page.

### Decision
We implemented an **AI Intelligence Pipeline** using Large Language Models (LLMs) like GPT-4, Gemini, and DeepSeek. The LLM is used as an "intelligent parser" that receives the page content and user prompt, identifies the relevant fields, and generates robust extraction patterns (specifically RegEx and CSS selectors).

### Alternatives Considered
- **Hand-coded templates:** Too rigid; would require a new template for every website.
- **Classic NLP (SpaCy/NLTK):** Not flexible enough to handle arbitrary web layouts without extensive training.

### Consequences
**Positive:**
- Zero-code data extraction for end-users.
- Resilience to minor HTML changes (LLM can re-generate selectors).
- Support for complex, multi-field extractions via schema generation.

**Negative:**
- Latency introduced by LLM API calls.
- Potential for non-deterministic results (mitigated via prompt engineering and validation).

## Implementation Details

### Key Implementation Decisions
- **Intent Extraction:** The LLM first identifies "what" is being asked (e.g., "price", "title") before looking at the page.
- **RegEx Generation:** LLM generates specific regular expressions based on structural markers in the semantic text.
- **Prompt Templates:** Highly optimized prompts with few-shot examples ensure consistent output format (JSON).

## Requirements Checklist

| # | Requirement | Status | Evidence/Notes |
|---|-------------|--------|----------------|
| 1 | LLM Interpretation | ✅ | Uses OpenAI/Gemini/DeepSeek APIs for prompt processing. |
| 2 | Natural Language Support | ✅ | Users submit prompts like "Get all product titles". |
| 3 | RegEx Generation | ✅ | LLM generates regex patterns for semantic text extraction. |
| 4 | Adaptive Parsing | ✅ | System can regenerate patterns if the page structure changes. |

## Known Limitations
- LLM accuracy depends on the quality of the prompt and the page structure.
- Cost per request depends on external API pricing.

