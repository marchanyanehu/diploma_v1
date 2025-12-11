# Semantic Content-Based Regex Caching Architecture

## Overview

This document describes the field-based regex caching system that enables fast, reusable extraction patterns across similar web pages without requiring LLM calls.

## Key Features

### 1. **Field-Based Indexing**
- Cache indexed by: `domain + fields` (not full user prompt)
- Same regex reused for different prompts if they extract the same fields
- Example: "extract title and price" and "get all product names and costs" use same cache

### 2. **Semantic Content Targeting**
- Regex generated from **semantic content** (not HTML or JSON)
- Uses structural markers: `##` headings, `•` lists, `|` tables
- Cleaner patterns, more robust to HTML structure changes
- 2KB semantic text vs 200KB HTML = faster matching

### 3. **Automatic Invalidation**
- Cache entries validated on each use
- If regex fails: automatically invalidated + removed
- Next request triggers regeneration pipeline
- Self-healing cache system

### 4. **Cross-Request Reusability**
- Different prompts → same cache if fields match
- Example:
  - Request 1: "extract all titles and prices" → generates regex → caches
  - Request 2: "show me product names and costs" → cache hit! (same fields)
  - 100x speedup on cached requests

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Request Processing Flow                       │
└─────────────────────────────────────────────────────────────────┘

1. User Request
   ↓
2. Extract Domain + Fields
   ↓
3. Check Cache (domain + sorted fields)
   ↓
   ├─ Cache HIT → Apply regex to semantic content → Done (fast!)
   │
   └─ Cache MISS → LLM Extraction
                    ↓
                   Generate Regex from Semantic Content
                    ↓
                   Cache Regex (indexed by domain + fields)
                    ↓
                   Return Results

┌─────────────────────────────────────────────────────────────────┐
│                     Cache Validation Flow                        │
└─────────────────────────────────────────────────────────────────┘

On Cache Hit:
1. Apply regex to semantic content
2. Check match count >= min_matches
3. Check all requested fields present in matches
   ↓
   ├─ Valid → Use cached results
   │
   └─ Invalid → Invalidate cache entry
                Delete from database
                Trigger regeneration pipeline
```

## Database Schema

### ParserCache Table (Enhanced)

```sql
-- Field-based caching
keyword_set: JSON  -- Stores field names for indexing ['title', 'price']
source_type: VARCHAR  -- 'SEMANTIC' (new), 'HTML', 'JSON'

-- Validation
confidence_score: INT  -- 0-100, decreased on failure
is_active: BOOLEAN  -- Set to false when invalidated
times_used: INT  -- Usage tracking
last_used_at: TIMESTAMP  -- Last successful use
```

## Key Functions

### 1. Cache Lookup (`check_cached_parser`)
```python
def check_cached_parser(
    db, domain: str, fields: List[str], 
    search_content: str, source_type: str = "SEMANTIC"
) -> Dict[str, Any]:
    """
    - Queries by domain + fields (normalized, sorted)
    - Validates matches (count + field presence)
    - Auto-invalidates on failure
    """
```

### 2. Cache Creation (`create_parser_cache_by_fields`)
```python
def create_parser_cache_by_fields(
    db, domain: str, fields: List[str],
    generated_regex: str, ...
) -> ParserCache:
    """
    - Indexes by field names (not full prompt)
    - Stores as keyword_set for matching
    - Enables cross-request reuse
    """
```

### 3. Regex Generation (`_cache_regex_from_extraction`)
```python
def _cache_regex_from_extraction(
    db, task_id: str, domain: str, fields: List[str],
    semantic_content: str, extracted_items: List[Dict], llm
) -> None:
    """
    - Takes successful LLM extraction
    - Generates regex from semantic content
    - Caches for future requests
    """
```

### 4. Auto-Invalidation (`invalidate_parser`)
```python
def invalidate_parser(db: Session, parser_id: int) -> None:
    """
    - Marks parser as inactive
    - Sets confidence to 0
    - Prevents future use
    """
```

## Example Workflow

### First Request (Cache Miss)
```
User: "extract all product titles and prices from puko.lt"
↓
1. Domain: puko.lt, Fields: [title, price]
2. Check cache: NOT FOUND
3. LLM extraction from semantic content:
   ## Халат Бамбоо весна
   75.00€
   
   ## Халат Бамбоо Копи
   54.00€
4. Generate regex:
   ## (?P<title>[^\n]+)\s+(?P<price>\d+\.\d+€)
5. Cache regex (domain=puko.lt, fields=[price, title])
6. Return 25 items
```

### Second Request (Cache Hit)
```
User: "show me all item names and costs from puko.lt"
↓
1. Domain: puko.lt, Fields: [name, cost]
   (normalized to [cost, name] → matches [price, title])
2. Check cache: FOUND! (parser_id=123)
3. Apply cached regex to semantic content
4. Return 25 items (0.5ms vs 5000ms)
5. Update parser usage stats
```

### Cache Invalidation (Automatic)
```
User: "extract titles and prices from puko.lt" (page changed)
↓
1. Domain: puko.lt, Fields: [title, price]
2. Check cache: FOUND (parser_id=123)
3. Apply regex → Only 2 matches (expected 25+)
4. INVALID! Invalidate parser_id=123
5. Fall back to LLM extraction
6. Generate NEW regex
7. Cache as parser_id=456
8. Return results
```

## Performance Benefits

| Scenario | Without Cache | With Cache | Speedup |
|----------|---------------|------------|---------|
| First request | 5-10s (LLM) | 5-10s (LLM) | 1x |
| Same domain + fields | 5-10s | 0.5ms | **10,000x** |
| Different prompt, same fields | 5-10s | 0.5ms | **10,000x** |
| Page structure changed | 5-10s | 5-10s + cache update | 1x |

## Advantages Over Other Approaches

### vs. Keyword-Based Caching
❌ Different prompts = cache miss  
✅ Field-based = cache hit across prompts

### vs. HTML Regex Caching
❌ Fragile to HTML changes  
✅ Semantic content more stable

### vs. JSON Response Caching
❌ Still need LLM to generate JSON  
✅ Skip LLM entirely with cached regex

### vs. Manual Regex Writing
❌ Human effort per site  
✅ Auto-generated, auto-cached

## Configuration

### Environment Variables
```bash
# Minimum matches for cache validation
CACHE_MIN_MATCHES=1

# Confidence threshold for cache lookup
CACHE_CONFIDENCE_THRESHOLD=70

# Max parsers to check per domain
CACHE_LOOKUP_LIMIT=3
```

## Monitoring

### Log Events
- `cache_hit` - Successful cache usage
- `cache_invalid` - Invalidation triggered
- `regex_cached` - New regex stored
- `regex_generation_failed` - Generation failed

### Metrics to Track
- Cache hit rate (hits / total requests)
- Average extraction time (cached vs uncached)
- Parser invalidation rate
- Regex generation success rate

## Future Improvements

1. **Multi-pattern caching** - Store multiple regex variants per field set
2. **Partial field matching** - Use cache even if subset of fields requested
3. **Cross-domain patterns** - Detect similar structures across domains
4. **Pattern versioning** - Keep old patterns for rollback
5. **A/B testing** - Compare LLM vs cached extraction quality
