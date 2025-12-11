
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
    """Convert HTML to text but preserve links and images in Markdown format."""
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
                src_match = re.match(r".*", first_src)
        if not src_match:
            src_match = re.search(r'src=["\']([^"\']+)["\']', attrs, re.IGNORECASE)

        alt_match = re.search(r'alt=["\']([^"\']*)["\']', attrs, re.IGNORECASE)
        src = src_match.group(1) if src_match else ""
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

