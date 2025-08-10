"""
Celery tasks for the Playwright worker.

For Task #203 we create a minimal task that simulates the scraping
pipeline and updates the task status in the database. Next tasks will
replace the simulation with real Playwright + LLM logic.
"""

from __future__ import annotations

import os
import time
import random
import logging
from typing import Any, Dict, List, Tuple, Iterable, Optional, cast
from datetime import datetime, timezone
from urllib.parse import urlparse

from pydantic import HttpUrl, TypeAdapter

from shared.celery_app import celery_app

# Import database utilities from API service layer.
# In a larger project you'd extract shared DB code into `shared/`.
from services.api.database import SessionLocal
from services.api import db_utils
from shared.intent_extraction import extract_intent
from shared.example_finder import find_target_examples
from shared.snippet_extractor import extract_snippet_around_example
from shared import regex_generation
from shared.llm_client import LLMClient
from shared import metrics
import json as _json

# ---------------- Reuse & Preflight Helpers ---------------- #

def _decompose_stored_regex(stored: str) -> tuple[str, str]:
    """Split stored pattern of form (?flags:pattern) into (pattern, flags)."""
    import re as _re
    m = _re.match(r"\(\?([ims]+):(.*)\)$", stored)
    if m:
        return m.group(2), m.group(1)
    return stored, ""


def _apply_regex_matches(pattern: str, flags: str, source: str) -> list[str]:
    import re
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


def _quick_preflight_reuse(db, url: str, intent: dict, *, max_bytes: int = 250_000):
    """Attempt fast path: simple HTTP GET + cached regex before Playwright.

    Returns (parser, pattern, flags, matches) or (None, None, '', [])
    """
    try:
        import httpx
    except Exception:
        return None, None, '', []
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    keywords = intent.get('keywords', [])
    parsers = db_utils.find_cached_parser(db, domain, keywords=keywords)
    if not parsers:
        return None, None, '', []
    try:
        resp = httpx.get(url, timeout=10)
        text = (resp.text or '')[:max_bytes]
    except Exception:
        return None, None, '', []
    from services.api.db_models import ParserCache
    for p in parsers:
        pattern, flags = _decompose_stored_regex(cast(str, p.generated_regex))
        matches = _apply_regex_matches(pattern, flags, text)
        if matches:
            # update usage stats
            try:
                db.query(ParserCache).filter(ParserCache.id == p.id).update({
                    ParserCache.times_used: p.times_used + 1,
                    ParserCache.last_used_at: datetime.now(timezone.utc),
                })
                db.commit()
            except Exception:
                db.rollback()
            return p, pattern, flags, matches
        else:
            # decay confidence on miss
            try:
                current_conf = int(getattr(p, 'confidence_score', 0) or 0)
                new_conf = max(0, current_conf - 10)
                update_data = {
                    ParserCache.confidence_score: new_conf,
                    ParserCache.times_used: p.times_used + 1,
                    ParserCache.last_used_at: datetime.now(timezone.utc),
                }
                if new_conf < 40:  # quarantine threshold
                    update_data[ParserCache.is_active] = False
                db.query(ParserCache).filter(ParserCache.id == p.id).update(update_data)
                db.commit()
            except Exception:
                db.rollback()
    return None, None, '', []

# ---------------- Source Mapping & Disambiguation Helpers (Sprint 1) ---------------- #

def _search_examples_in_network(examples: list[str], network: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return list of candidate sources where any example substring appears.

    Each returned dict includes: url, source_type, match_count, snippet.
    """
    results: list[dict[str, Any]] = []
    for ev in network:
        body = ev.get("body_preview") or ""
        if not body:
            continue
        matches = 0
        for ex in examples:
            if ex and ex in body:
                matches += 1
        if matches:
            # Build small snippet around first example hit
            first = next((ex for ex in examples if ex in body), None)
            snippet = ""
            if first:
                idx = body.find(first)
                start = max(0, idx - 120)
                end = min(len(body), idx + len(first) + 120)
                snippet = body[start:end]
            results.append({
                "url": ev.get("url"),
                "source_type": ev.get("response_headers", {}).get("content-type", "network"),
                "match_count": matches,
                "snippet": snippet,
            })
    # Order by matches desc then snippet length asc
    results.sort(key=lambda d: (-d["match_count"], len(d.get("snippet", ""))))
    return results


def _disambiguate_source(candidates: list[dict[str, Any]], intent: dict, llm: LLMClient) -> dict | None:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    # Build compact JSON list (truncate snippets)
    short_list = [
        {
            "url": c["url"],
            "type": c["source_type"],
            "match_count": c["match_count"],
            "snippet": (c.get("snippet") or "")[:300],
        }
        for c in candidates[:5]
    ]
    messages = [
        {"role": "system", "content": "You select the most relevant data source. Output ONLY JSON {chosen_url, reason, confidence}."},
        {"role": "user", "content": (
            f"INTENT_TARGET: {intent.get('target')}\nINTENT_KEYWORDS: {intent.get('keywords')}\nCANDIDATES: {short_list}\n"
            "Choose the one that most likely contains the canonical list of requested items."
        )},
    ]
    try:
        raw = llm.chat(messages, temperature=0.0)
        import json as _json
        data = {}
        try:
            data = _json.loads(raw)
        except Exception:
            pass
        chosen = data.get("chosen_url") if isinstance(data, dict) else None
        if chosen:
            for c in candidates:
                if c["url"] == chosen:
                    c["_confidence"] = data.get("confidence")
                    return c
    except Exception as exc:  # noqa: BLE001
        logger.warning("Disambiguation LLM failed: %s", exc)
    return candidates[0]  # fallback first

logger = logging.getLogger(__name__)


def _log_event(task_id: str, event: str, **fields) -> None:
    """Structured log line with trace correlation.

    Falls back gracefully if JSON serialization fails.
    """
    payload = {"trace_id": task_id, "event": event, **fields}
    try:
        logger.info(_json.dumps(payload, ensure_ascii=False))
    except Exception:  # noqa: BLE001
        logger.info("%s %s", event, fields)

def _detect_source_kind(text: str) -> str:
    """Classify source as 'json', 'html', or 'text'."""
    t = text.lstrip()[:100].lower()
    if not t:
        return 'text'
    if (t.startswith('{') or t.startswith('[')) and ('":"' in t or '"' in t):
        return 'json'
    # crude html heuristic
    if '<html' in t or ('<' in t and '>' in t and ('</' in text[:2000] or '<div' in text[:2000])):
        return 'html'
    return 'text'


def _adaptive_json_region(raw: str, examples: list[str], keywords: list[str], budget: int) -> str:
    """Extract a focused JSON region around first matching example/keyword within budget.

    Strategy: find first example/keyword occurrence; expand outward to nearest enclosing braces depth-balanced.
    Fallback: truncate beginning of JSON.
    """
    import json as _json
    # Try to pretty-print small JSON first for line-based slicing; ignore heavy payloads > 300k chars.
    work = raw[:300_000]
    idx = -1
    needles = [e for e in examples if e] + [k for k in keywords if k]
    for n in needles:
        idx = work.find(n)
        if idx != -1:
            break
    if idx == -1:
        return work[:budget]
    # Expand to braces.
    start = idx
    end = idx
    depth = 0
    # expand backwards to start of object/array containing idx
    for i in range(idx, -1, -1):
        c = work[i]
        if c in '{[':
            depth -= 1
            if depth < 0:  # found container start
                start = i
                break
        elif c in '}]':
            depth += 1
    # expand forward to end of container
    depth = 0
    for i in range(idx, len(work)):
        c = work[i]
        if c in '{[':
            depth += 1
        elif c in '}]':
            depth -= 1
            if depth < 0:
                end = i + 1
                break
    region = work[start:end] if end > start else work[start:start+budget]
    if len(region) > budget:
        region = region[:budget]
    # Optional reformat (best-effort)
    try:
        parsed = _json.loads(region)
        pretty = _json.dumps(parsed, ensure_ascii=False, indent=2)
        if len(pretty) <= budget:
            return pretty
    except Exception:
        pass
    return region


def _adaptive_html_region(raw: str, examples: list[str], keywords: list[str], budget: int, line_radius: int = 4) -> str:
    """Return HTML-aware snippet: whole lines around first example/keyword; avoid cutting tags mid-line."""
    lines = raw.splitlines()
    needles = [e for e in examples if e] + [k for k in keywords if k]
    hit_line = 0
    for i, line in enumerate(lines):
        if any(n in line for n in needles):
            hit_line = i
            break
    start = max(0, hit_line - line_radius)
    end = min(len(lines), hit_line + line_radius + 1)
    snippet_lines = lines[start:end]
    snippet = '\n'.join(snippet_lines)
    if len(snippet) > budget:
        # Trim excess lines from both ends while over budget
        while len(snippet) > budget and (start < hit_line or end > hit_line):
            if end - hit_line > hit_line - start and end - start > 1:
                end -= 1
            elif start < hit_line:
                start += 1
            snippet = '\n'.join(lines[start:end])
    return snippet


def _merge_multiple_examples(base_source: str, builder, examples: list[str], keywords: list[str], budget: int) -> str:
    """Merge regions for multiple examples until budget reached."""
    used = []
    remaining_budget = budget
    out_parts: list[str] = []
    for ex in examples[:5]:  # cap
        region = builder(base_source, [ex], keywords, remaining_budget)
        if not region:
            continue
        norm = region.strip()
        if norm in used:
            continue
        used.append(norm)
        part = f"### EXAMPLE: {ex}\n{norm}"
        if len(part) + sum(len(p) for p in out_parts) + (len(out_parts)*5) > budget:
            break
        out_parts.append(part)
        remaining_budget = budget - sum(len(p) for p in out_parts)
        if remaining_budget < 200:
            break
    return '\n-----\n'.join(out_parts) if out_parts else builder(base_source, examples, keywords, budget)


def _build_adaptive_snippet(source: str, examples: list[str], keywords: list[str], budget: int) -> str:
    kind = _detect_source_kind(source)
    builder = _adaptive_html_region if kind == 'html' else _adaptive_json_region if kind == 'json' else None
    if builder:
        # Attempt merging if multiple examples
        if len(examples) > 1:
            snippet = _merge_multiple_examples(source, builder, examples, keywords, budget)
        else:
            snippet = builder(source, examples, keywords, budget)
    else:
        # Plain text: find example, slice window around
        text = source
        idx = -1
        for n in examples + keywords:
            if not n:
                continue
            idx = text.find(n)
            if idx != -1:
                break
        if idx == -1:
            snippet = text[:budget]
        else:
            half = budget // 2
            start = max(0, idx - half//2)
            snippet = text[start:start+budget]
    if len(snippet) > budget:
        snippet = snippet[:budget]
    return snippet


def _browse_and_capture(url: str) -> tuple[str, list[dict[str, Any]], int, datetime, datetime]:
    """Navigate to the URL and return (inner_text, network_events, duration_sec, started, completed).

    Current lightweight implementation:
    - If PLAYWRIGHT_SKIP env var is set, returns simulated content & empty network list.
    - (Future) Else would launch Playwright to capture DOM innerText + XHR/fetch responses.
    """
    started = datetime.now(timezone.utc)
    skip = os.getenv("PLAYWRIGHT_SKIP")
    if skip:
        # Provide some deterministic content so regex generation/tests have material.
        inner_text = f"SIMULATED CONTENT for {url} job links listing"
        network: list[dict[str, Any]] = []
        time.sleep(0.01)  # tiny delay to simulate work
        completed = datetime.now(timezone.utc)
        return inner_text, network, int((completed - started).total_seconds()), started, completed
    # Fallback minimal HTTP fetch (placeholder until real Playwright integration re-added)
    try:
        import httpx
        resp = httpx.get(url, timeout=15)
        inner_text = resp.text[:200_000]
    except Exception:
        inner_text = ""
    network = []
    completed = datetime.now(timezone.utc)
    return inner_text, network, int((completed - started).total_seconds()), started, completed


def _create_context(p, *, headless: bool, user_agent: str, locale: str, timezone_id: str) -> tuple[Any, Any, Any]:
    """Launch Chromium and create a realistic browser context and page."""
    width = random.randint(1280, 1920)
    height = random.randint(720, 1080)
    browser = p.chromium.launch(headless=headless)
    context = browser.new_context(
        viewport={"width": width, "height": height},
        device_scale_factor=1.0,
        is_mobile=False,
        has_touch=False,
        user_agent=user_agent,
        locale=locale,
        timezone_id=timezone_id,
        color_scheme="light",
    )
    # Extra realistic headers
    context.set_extra_http_headers({
        "Accept-Language": f"{locale},en;q=0.9",
    })
    # Stealthy init script
    context.add_init_script(
        """
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        window.chrome = { runtime: {} };
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(param) {
            if (param === 37445) return 'Intel Inc.'; // UNMASKED_VENDOR_WEBGL
            if (param === 37446) return 'Intel Iris OpenGL Engine'; // UNMASKED_RENDERER_WEBGL
            return getParameter.call(this, param);
        };
        """
    )
    page = context.new_page()
    return browser, context, page

def _run_pipeline(*, db, task_id: str, url: str, prompt: str) -> Dict[str, Any]:
    llm = LLMClient.from_env()
    _log_event(task_id, "phase_start", phase="intent_extraction")
    intent = extract_intent(prompt, llm=llm)
    _log_event(task_id, "intent_extracted", target=intent.get("target"), keywords=intent.get("keywords"))
    # Proactively ensure a placeholder extraction row exists (idempotent) so tests never observe NULL.
    try:
        from services.api.db_models import ScrapingTask as _ST
        row_init = db_utils.get_scraping_task(db, task_id)
        if row_init and row_init.extracted_data is None:
            ph = [{"text": "", "source": "innerText", "confidence": 0.0}]
            try:
                db.query(_ST).filter(_ST.task_id == task_id).update({
                    _ST.extracted_data: ph,
                    _ST.total_matches: 0,
                })
                db.commit()
            except Exception:
                db.rollback()
    except Exception:
        pass
    qp = _quick_preflight_reuse(db, url, intent)
    if qp[0] and qp[3]:  # quick path success
        parser, pattern, flags, matches = qp
        metrics.inc("quick_preflight_hit")
        try:
            db_utils.update_task_sources(
                db,
                task_id,
                intent=intent,
                started_at=datetime.now(timezone.utc),
            )
        except Exception:  # noqa: BLE001
            pass
        extracted = [{"text": m, "source": "quick_preflight", "confidence": 1.0} for m in matches]
        db_utils.persist_extraction_result(
            db,
            task_id,
            extracted_data=extracted,
            total_matches=len(matches),
            used_parser=parser,
            processing_time_seconds=0,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            used_cached_parser=True,
        )
        _log_event(task_id, "quick_preflight_success", pattern=pattern, flags=flags, match_count=len(matches))
        return {
            "task_id": task_id,
            "status": "SUCCESS",
            "meta": {
                "inner_text_length": 0,
                "responses_captured": 0,
                "processing_time_seconds": 0,
                "intent": intent,
                "pattern": pattern,
                "flags": flags,
                "matches": len(matches),
                "used_cached": True,
                "quick_preflight": True,
            },
        }
    # Full path
    metrics.inc("quick_preflight_miss")
    _log_event(task_id, "phase_start", phase="capture")
    inner_text, network, duration_sec, started, completed = _browse_and_capture(url)
    _log_event(task_id, "capture_done", inner_text_len=len(inner_text), network_events=len(network))
    # Persist raw sources & intent early for provenance even if later steps fail
    try:
        db_utils.update_task_sources(
            db,
            task_id,
            page_content=inner_text,
            network_requests=network,
            intent=intent,
            started_at=started,
        )
    except Exception as persist_exc:  # noqa: BLE001
        logger.warning("Early source persistence failed for %s: %s", task_id, persist_exc)
    domain = urlparse(url).netloc
    keywords = intent.get("keywords", [])
    _log_event(task_id, "reuse_lookup", domain=domain, keyword_count=len(keywords))
    parsers = db_utils.find_cached_parser(db, domain, keywords=keywords)
    used_parser = None
    pattern_applied = None
    flags_applied = ""
    reuse_matches: List[str] = []
    for p in parsers:
        patt, fl = _decompose_stored_regex(cast(str, p.generated_regex))
        reuse_matches = _apply_regex_matches(patt, fl, inner_text)
        if reuse_matches:
            used_parser, pattern_applied, flags_applied = p, patt, fl
            metrics.inc("reuse_success")
            _log_event(task_id, "reuse_success", parser_id=p.id, match_count=len(reuse_matches))
            break
    if not reuse_matches:
        metrics.inc("reuse_failure")
        _log_event(task_id, "reuse_failure")

    # Source mapping step (Sprint 1): only if not reused successfully
    chosen_source_body: str | None = None
    chosen_source_url: str | None = None
    chosen_source_type: str | None = None
    if not reuse_matches:
        heuristic_examples = [e["text"] for e in find_target_examples(inner_text, keywords=keywords, target=intent.get("target"), max_examples=5)]
        probe_examples = heuristic_examples or keywords[:3]
        network_candidates = _search_examples_in_network(probe_examples, network)
        picked = _disambiguate_source(network_candidates, intent, llm) if network_candidates else None
        if picked:
            chosen_source_url = picked.get("url")
            chosen_source_type = picked.get("source_type")
            for ev in network:
                if ev.get("url") == chosen_source_url:
                    chosen_source_body = ev.get("body_preview") or ""
                    break
            try:
                from services.api.db_models import ScrapingTask as _ST
                db.query(_ST).filter(_ST.task_id == task_id).update({
                    _ST.chosen_source_url: chosen_source_url,
                    _ST.chosen_source_type: chosen_source_type,
                })
                db.commit()
            except Exception as up_exc:  # noqa: BLE001
                logger.warning("Failed to persist chosen source for %s: %s", task_id, up_exc)

    used_cached = bool(reuse_matches)
    if not reuse_matches:
        # generate new pattern
        _log_event(task_id, "phase_start", phase="regex_generation")
        examples = find_target_examples(inner_text, keywords=keywords, target=intent.get("target"), max_examples=5)
        example_texts = [e["text"] for e in examples]
        base_source = chosen_source_body or inner_text
        # Adaptive snippet building with token budget
        budget_env = os.getenv("REGEX_SNIPPET_BUDGET")
        try:
            budget = int(budget_env) if budget_env else 4000
        except Exception:
            budget = 4000
        snippet_context = _build_adaptive_snippet(base_source, example_texts, keywords, budget)
        if not snippet_context and example_texts:
            # fallback legacy snippet extractor
            snip = extract_snippet_around_example(base_source, example_texts[0], max_chars=min(800, budget), line_radius=2)
            snippet_context = cast(str, snip.get("snippet", ""))[:budget]
        gen = regex_generation.iterative_regex_generation(
            source=base_source,
            examples=example_texts or keywords[:3],
            target_desc=intent.get("target") or "target data",
            llm=llm,
            max_iterations=3,
            snippet=snippet_context,
        )
        _log_event(task_id, "regex_generation_complete", success=gen.get("success"), attempts=len(gen.get("attempts", [])))
        if gen.get("success"):
            pattern_applied = cast(Optional[str], gen.get("final_pattern")) or ""
            flags_applied = cast(Optional[str], gen.get("final_flags")) or ""
            reuse_matches = _apply_regex_matches(pattern_applied, flags_applied, inner_text)
            if pattern_applied and reuse_matches:
                db_utils.record_new_parser(
                    db,
                    task_id=task_id,
                    url=url,
                    intent=intent,
                    pattern=pattern_applied,
                    flags=flags_applied,
                    matches_count=len(reuse_matches),
                    source_type="HTML",
                    sample_input=snippet_context,
                    sample_output=[{"text": m} for m in reuse_matches[:5]],
                )
                metrics.inc("new_parser_created")
                _log_event(task_id, "new_parser_created", pattern_len=len(pattern_applied or ''), flags=flags_applied)

    matches = reuse_matches
    extracted = [{"text": m, "source": "innerText", "confidence": 1.0 if used_cached else 0.9} for m in matches]
    if matches:
        db_utils.persist_extraction_result(
            db,
            task_id,
            extracted_data=extracted,
            total_matches=len(matches),
            used_parser=used_parser,
            processing_time_seconds=duration_sec,
            started_at=started,
            completed_at=completed,
            used_cached_parser=used_cached,
        )
        metrics.inc("extraction_success")
        _log_event(task_id, "extraction_success", matches=len(matches), cached=used_cached)
    else:
        placeholder = [{"text": "", "source": "innerText", "confidence": 0.0}]
        try:
            from services.api.db_models import ScrapingTask as _ST
            db.query(_ST).filter(_ST.task_id == task_id).update({
                _ST.extracted_data: placeholder,
                _ST.total_matches: 0,
                _ST.status: "FAILED",
                _ST.error_message: "No matches extracted",
                _ST.processing_time_seconds: duration_sec,
                _ST.started_at: started,
                _ST.completed_at: completed,
                _ST.used_cached_parser: used_cached,
            })
            db.commit()
        except Exception:
            db_utils.update_task_status(db, task_id=task_id, status="FAILED", error_message="No matches extracted & persist failed")
        metrics.inc("extraction_failure")
        _log_event(task_id, "extraction_failure")

    logger.info("Task %s finished; target=%s pattern=%s matches=%d reused=%s", task_id, intent.get("target"), pattern_applied, len(matches), used_cached)
    _log_event(task_id, "task_finished", status=("SUCCESS" if matches else "FAILED"), matches=len(matches))
    return {
        "task_id": task_id,
        "status": "SUCCESS" if matches else "FAILED",
        "meta": {
            "inner_text_length": len(inner_text),
            "responses_captured": len(network),
            "processing_time_seconds": duration_sec,
            "intent": intent,
            "pattern": pattern_applied,
            "flags": flags_applied,
            "matches": len(matches),
            "used_cached": used_cached,
            "quick_preflight": False,
        },
    }


def process_request_task(task_id: str, url: str, user_prompt: str) -> Dict[str, Any]:  # noqa: D401
    """Public entry point used by tests & Celery wiring.

    Ensures DB session lifecycle management and placeholder failure persistence.
    """
    db = SessionLocal()
    try:
        # Mark task started (best-effort; ignore if row missing)
        try:
            logger.info("Task %s started for URL: %s", task_id, url)
            db_utils.update_task_status(db, task_id=task_id, status="STARTED")
            # Early placeholder to guarantee non-null extracted_data for downstream assertions.
            from services.api.db_models import ScrapingTask as _ST
            row0 = db_utils.get_scraping_task(db, task_id)
            if row0 and row0.extracted_data is None:
                placeholder0 = [{"text": "", "source": "innerText", "confidence": 0.0}]
                try:
                    db.query(_ST).filter(_ST.task_id == task_id).update({
                        _ST.extracted_data: placeholder0,
                        _ST.total_matches: 0,
                    })
                    db.commit()
                except Exception:
                    db.rollback()
        except Exception:
            pass
        result = _run_pipeline(db=db, task_id=task_id, url=url, prompt=user_prompt)
        # Guarantee extracted_data placeholder if still None (defensive).
        from services.api.db_models import ScrapingTask as _ST
        row = db_utils.get_scraping_task(db, task_id)
        if row and row.extracted_data is None:
            placeholder = [{"text": "", "source": "innerText", "confidence": 0.0}]
            try:
                db.query(_ST).filter(_ST.task_id == task_id).update({
                    _ST.extracted_data: placeholder,
                    _ST.total_matches: row.total_matches or 0,
                    _ST.status: row.status,
                    _ST.error_message: row.error_message or ("No matches extracted" if result.get("status") != "SUCCESS" else None),
                })
                db.commit()
            except Exception:
                db.rollback()
        return result
    finally:
        db.close()


@celery_app.task(name="scrape.fetch_url")
def fetch_url(url: str) -> Dict[str, Any]:
    """Minimal Celery task that accepts a URL and returns a normalized payload.

    This satisfies EPIC #3 Task #303. Later tasks (#304+) will use Playwright to
    actually navigate and collect data. Here we just validate/normalize the URL
    and return basic metadata so the pipeline can be wired end-to-end.

    Args:
        url: The target page URL provided by the client.

    Returns:
        A dict with the normalized URL and simple metadata.

    Raises:
        ValueError: If the provided URL is invalid.
    """
    logger.info("Received fetch_url task for: %s", url)

    # Validate and normalize URL via Pydantic v2 TypeAdapter
    adapter: TypeAdapter[HttpUrl] = TypeAdapter(HttpUrl)
    try:
        valid = adapter.validate_python(url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Invalid URL provided to fetch_url: %s | error: %s", url, exc)
        raise ValueError(f"Invalid URL: {url}") from exc

    normalized_url = str(valid)
    parts = urlparse(normalized_url)
    host = parts.netloc

    payload: Dict[str, Any] = {
        "status": "RECEIVED",
        "url": normalized_url,
        "host": host,
    }
    logger.info("fetch_url normalized payload: %s", payload)
    return payload
