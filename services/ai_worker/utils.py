
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
    m = re.match(r"\(\?([ims]+):(.*)\)$", stored)
    if m:
        return m.group(2), m.group(1)
    return stored, ""

def apply_regex_matches(pattern: str, flags: str, source: str) -> list[str]:
    re_flags = 0
    if 'i' in flags: re_flags |= re.IGNORECASE
    if 'm' in flags: re_flags |= re.MULTILINE
    if 's' in flags: re_flags |= re.DOTALL
    try:
        rx = re.compile(pattern, re_flags)
    except Exception:
        return []
    out: list[str] = []
    for m in rx.finditer(source):
        if m.lastindex and m.lastindex >= 1:
            out.append(m.group(1))
        else:
            out.append(m.group(0))
    return out

def log_event(task_id: str, event: str, **fields) -> None:
    payload = {"trace_id": task_id, "event": event, **fields}
    try:
        logger.info(json.dumps(payload, ensure_ascii=False))
    except Exception:
        logger.info("%s %s", event, fields)

def convert_html_to_markdown_like(html: str) -> str:
    """Convert HTML to text but preserve links in Markdown format [text](url)."""
    # 1. Extract links: <a ... href="url" ...>text</a> -> [text](url)
    
    def replace_link(match):
        attrs = match.group(1)
        text = match.group(2)
        
        # Find href in attributes
        href_match = re.search(r'href=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
        if href_match:
            url = href_match.group(1)
            # Clean text (remove internal tags)
            clean_text = re.sub(r'<[^>]+>', '', text).strip()
            if not clean_text:
                clean_text = "link"
            return f" [{clean_text}]({url}) "
        return text

    # Match <a attributes>content</a>
    # Non-greedy match for content
    text = re.sub(r'<a([^>]+)>(.*?)</a>', replace_link, html, flags=re.IGNORECASE | re.DOTALL)
    
    # 2. Strip remaining HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    
    # 3. Decode entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    
    # 4. Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

