
import re
import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

def strip_html_to_text(html: str) -> str:
    """Strip HTML tags and normalize whitespace to get clean text."""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Decode common HTML entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def decompose_stored_regex(stored: str) -> tuple[str, str]:
    """Split a stored regex into (pattern, flags).

    Supports these encodings:
    - `(?is)<item>(.*?)</item>`  (inline flags at start)
    - `(?is:<item>(.*?)</item>)` (scoped flags group)

    If no flags prefix is detected, returns (stored, "").
    """
    if not stored:
        return "", ""

    # 1) Scoped group form: (?ims:...)
    m = re.match(r"^\(\?([ims]+):(.*)\)$", stored, flags=re.DOTALL)
    if m:
        return m.group(2), m.group(1)

    # 2) Inline flags at start: (?ims)rest...
    m = re.match(r"^\(\?([ims]+)\)(.*)$", stored, flags=re.DOTALL)
    if m:
        return m.group(2), m.group(1)

    return stored, ""

def apply_regex_matches(
    pattern: str,
    flags: str,
    source: str,
    *,
    fields: list[str] | None = None,
    max_matches: int = 5000,
) -> list[Dict[str, Any]]:
    re_flags = 0
    if 'i' in flags: re_flags |= re.IGNORECASE
    if 'm' in flags: re_flags |= re.MULTILINE
    if 's' in flags: re_flags |= re.DOTALL
    try:
        rx = re.compile(pattern, re_flags)
    except Exception:
        return []

    out: list[Dict[str, Any]] = []
    for i, m in enumerate(rx.finditer(source)):
        if i >= max_matches:
            break

        groupdict = m.groupdict() or {}
        extracted_fields: Dict[str, Any] = {}

        if groupdict:
            # Named groups are the canonical multi-field format.
            extracted_fields = {k: (v.strip() if isinstance(v, str) else v) for k, v in groupdict.items()}
        else:
            # Fallback for single-field patterns: use group(1) if present else whole match.
            val = m.group(1) if (m.lastindex and m.lastindex >= 1) else m.group(0)
            if isinstance(val, str):
                val = val.strip()
            if fields and len(fields) == 1:
                extracted_fields = {fields[0]: val}
            elif val is not None:
                extracted_fields = {"value": val}

        # Build a stable text representation
        if extracted_fields and fields:
            text_repr = " | ".join(f"{f}: {extracted_fields.get(f, '')}" for f in fields if extracted_fields.get(f) not in (None, ""))
        else:
            text_repr = ""
        if not text_repr:
            text_repr = " | ".join(f"{k}: {v}" for k, v in extracted_fields.items() if v not in (None, "")) or ""

        out.append(
            {
                "text": text_repr,
                "fields": extracted_fields,
                "source": "cache",
                "confidence": 0.95,
            }
        )
    return out

def log_event(task_id: str, event: str, **fields) -> None:
    payload = {"trace_id": task_id, "event": event, **fields}
    try:
        logger.info(json.dumps(payload, ensure_ascii=False))
    except Exception:
        logger.info("%s %s", event, fields)

def convert_html_to_markdown_like(html: str) -> str:
    """Convert HTML to text but preserve links and images in Markdown format. 
    Strips scripts and styles first to reduce noise.
    """
    if not html:
        return ""
        
    # Strip script and style tags
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.IGNORECASE | re.DOTALL)

    def replace_link(match):
        attrs = match.group(1)
        text = match.group(2)
        href_match = re.search(r'href=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
        if href_match:
            url = href_match.group(1)
            clean_text = re.sub(r'<[^>]+>', '', text).strip() or "link"
            return f" [{clean_text}]({url}) "
        return text

    def replace_image(match):
        attrs = match.group(1)
        # Prefer lazy-loading attributes first, then srcset, then src
        src_match = (
            re.search(r'data-src=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
            or re.search(r'data-original=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
            or None
        )
        if not src_match:
            srcset_match = re.search(r'srcset=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
            if srcset_match:
                # srcset format: "url1 1x, url2 2x" -> take first URL token
                first_src = srcset_match.group(1).split(",")[0].strip().split(" ")[0]
                # Store the URL directly, we'll handle it below
                src_direct = first_src
            else:
                src_direct = None
        else:
            src_direct = None
        if not src_match and not src_direct:
            src_match = re.search(r'src=["\']([^"\']+)["\']', attrs, re.IGNORECASE)

        alt_match = re.search(r'alt=["\']([^"\']*)["\']', attrs, re.IGNORECASE)
        src = src_direct if src_direct else (src_match.group(1) if src_match else "")
        alt = alt_match.group(1) if alt_match else "image"
        if not src:
            return ""
        return f" ![{alt}]({src}) "

    # Preserve anchors
    text = re.sub(r'<a([^>]+)>(.*?)</a>', replace_link, html, flags=re.IGNORECASE | re.DOTALL)
    # Preserve images
    text = re.sub(r'<img([^>]+)>', replace_image, text, flags=re.IGNORECASE | re.DOTALL)
    # Strip remaining tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Decode entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

