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


def _attach_network_listener(page, network: List[Dict[str, Any]], *, max_responses: int, max_preview: int) -> None:
    """Attach a response listener to capture XHR/Fetch responses with small previews."""

    def on_response(resp, _network=network):  # type: ignore[no-redef]
        try:
            if len(_network) >= max_responses:
                return
            req = resp.request
            rtype = getattr(req, "resource_type", lambda: None)()
            if rtype not in ("xhr", "fetch"):
                return
            entry: Dict[str, Any] = {
                "url": resp.url,
                "method": req.method,
                "status": resp.status,
                "request_headers": dict(req.headers),
                "response_headers": dict(resp.headers()),
                "resource_type": rtype,
            }
            try:
                text = resp.text()
                if text and len(text) > max_preview:
                    entry["body_preview"] = text[:max_preview]
                    entry["body_truncated"] = True
                else:
                    entry["body_preview"] = text
                    entry["body_truncated"] = False
            except Exception:  # noqa: BLE001
                entry["body_preview"] = None
                entry["body_truncated"] = False
            _network.append(entry)
        except Exception as e:  # noqa: BLE001
            logger.debug("response capture error: %s", e)

    page.on("response", on_response)


def _navigate_and_capture(page, url: str, *, nav_timeout_ms: int, settle_delay_ms: int) -> str:
    """Navigate with two-phase wait and return document.body.innerText."""
    from playwright.sync_api import TimeoutError as PWTimeoutError  # type: ignore

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=nav_timeout_ms)
        time.sleep(random.uniform(0.2, 0.6))
        page.wait_for_load_state("networkidle", timeout=nav_timeout_ms)
    except PWTimeoutError:
        logger.warning("Timeout navigating to %s after %sms", url, nav_timeout_ms)
    except Exception as nav_exc:  # noqa: BLE001
        logger.exception("Navigation error for %s: %s", url, nav_exc)

    time.sleep(max(0, settle_delay_ms) / 1000.0)
    try:
        return page.evaluate("document.body.innerText || ''")
    except Exception as eval_exc:  # noqa: BLE001
        logger.warning("Failed to evaluate innerText on %s: %s", url, eval_exc)
        return ""


def _browse_and_capture(url: str) -> Tuple[str, List[Dict[str, Any]], int, datetime, datetime]:
    """Open the URL headlessly with Playwright, capture innerText and XHR/Fetch.

    Returns:
        inner_text, network_events, duration_seconds, started_at, completed_at
    """
    # Allow tests to bypass Playwright (no browser dependency in CI/unit tests)
    if os.getenv("PLAYWRIGHT_SKIP", "").lower() in {"1", "true", "yes"}:
        dummy_text = (
            "Senior Python Developer Remote Europe\n"
            "Job Title: Data Scientist\n"
            "Apply now for remote python jobs.\n"
        )
        return dummy_text, [], 0, datetime.now(timezone.utc), datetime.now(timezone.utc)

    from playwright.sync_api import sync_playwright  # type: ignore

    # Configurable knobs
    headless = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() != "false"
    nav_timeout_ms = int(os.getenv("PLAYWRIGHT_NAV_TIMEOUT_MS", "30000"))
    settle_delay_ms = int(os.getenv("PLAYWRIGHT_SETTLE_DELAY_MS", "500"))
    max_retries = int(os.getenv("PLAYWRIGHT_MAX_RETRIES", "2"))
    retry_backoff_ms = int(os.getenv("PLAYWRIGHT_RETRY_BACKOFF_MS", "1000"))
    locale = os.getenv("PLAYWRIGHT_LOCALE", "en-US")
    timezone_id = os.getenv("PLAYWRIGHT_TZ", "UTC")
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    MAX_RESPONSES = 50
    MAX_BODY_PREVIEW = 50 * 1024

    started_overall = datetime.now(timezone.utc)
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            with sync_playwright() as p:
                browser, context, page = _create_context(
                    p,
                    headless=headless,
                    user_agent=user_agent,
                    locale=locale,
                    timezone_id=timezone_id,
                )
                network: List[Dict[str, Any]] = []
                _attach_network_listener(page, network, max_responses=MAX_RESPONSES, max_preview=MAX_BODY_PREVIEW)
                inner_text = _navigate_and_capture(
                    page,
                    url,
                    nav_timeout_ms=nav_timeout_ms,
                    settle_delay_ms=settle_delay_ms,
                )
                context.close()
                browser.close()

            if inner_text or network:
                completed_overall = datetime.now(timezone.utc)
                duration_sec = int((completed_overall - started_overall).total_seconds())
                return inner_text, network, duration_sec, started_overall, completed_overall
            else:
                last_error = RuntimeError("Empty page and no network captured")
                raise last_error
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < max_retries:
                backoff = (attempt + 1) * retry_backoff_ms / 1000.0
                logger.info("Retrying %s in %.2fs due to: %s", url, backoff, exc)
                time.sleep(backoff)
            else:
                break

    completed_overall = datetime.now(timezone.utc)
    duration_sec = int((completed_overall - started_overall).total_seconds())
    raise RuntimeError(f"Failed after {max_retries + 1} attempts: {last_error}")


@celery_app.task(name="scrape.process_request")
def process_request_task(task_id: str, url: str, prompt: str) -> Dict[str, Any]:
    """End-to-end pipeline for a scraping task with reuse + generation.

    Keeps sub-steps in small local helper functions to reduce complexity.
    """
    db = SessionLocal()
    try:
        # Mark as IN_PROGRESS
        db_utils.update_task_status(db, task_id=task_id, status="IN_PROGRESS")
        logger.info(f"Task {task_id} started for URL: {url}")
        llm = LLMClient.from_env()
        # ---- Helpers ---- #
        def do_intent() -> Dict[str, Any]:
            return extract_intent(prompt, llm=llm)

        def capture() -> Tuple[str, List[Dict[str, Any]], int, datetime, datetime]:
            return _browse_and_capture(url)

        def apply_regex(pattern: str, flags: str, source: str) -> List[str]:
            import re
            re_flags = 0
            if 'i' in flags: re_flags |= re.IGNORECASE
            if 'm' in flags: re_flags |= re.MULTILINE
            if 's' in flags: re_flags |= re.DOTALL
            try:
                rx = re.compile(pattern, re_flags)
            except Exception:
                return []
            out: List[str] = []
            for m in rx.finditer(source):
                if m.lastindex and m.lastindex >= 1:
                    out.append(m.group(1))
                else:
                    out.append(m.group(0))
            return out

        def try_reuse(domain: str, inner_text: str, keywords: List[str]):
            parsers = db_utils.find_cached_parser(db, domain, keywords=keywords)
            for p in parsers:
                stored = cast(str, p.generated_regex)
                import re as _re
                m = _re.match(r"\(\?([ims]+):(.*)\)$", stored)
                p_flags = m.group(1) if m else ""
                p_pattern = m.group(2) if m else stored
                matches = apply_regex(p_pattern, p_flags, inner_text)
                if matches:
                    return p, p_pattern, p_flags, matches
            return None, None, "", []  # type: ignore[return-value]

        def generate_pattern(inner_text: str, keywords: List[str], intent: Dict[str, Any], *, source_body: str | None = None):
            examples = find_target_examples(
                inner_text,
                keywords=keywords,
                target=intent.get("target"),
                max_examples=5,
            )
            example_texts = [e["text"] for e in examples]
            base_source = source_body or inner_text
            snippet_context: str = base_source[:1500]
            if example_texts:
                snip = extract_snippet_around_example(base_source, example_texts[0], max_chars=800, line_radius=2)
                snippet_context = cast(str, snip["snippet"])  # ensure str for typing
            gen = regex_generation.iterative_regex_generation(
                source=base_source,
                examples=example_texts or keywords[:3],
                target_desc=intent.get("target") or "target data",
                llm=llm,
                max_iterations=3,
                snippet=snippet_context,
            )
            if not gen.get("success"):
                return None, None, []
            pattern = cast(Optional[str], gen.get("final_pattern")) or ""
            flags = cast(Optional[str], gen.get("final_flags")) or ""
            matches = apply_regex(pattern, flags, inner_text)
            if pattern and matches:
                db_utils.record_new_parser(
                    db,
                    task_id=task_id,
                    url=url,
                    intent=intent,
                    pattern=pattern,
                    flags=flags,
                    matches_count=len(matches),
                    source_type="HTML",
                    sample_input=snippet_context,
                    sample_output=[{"text": m} for m in matches[:5]],
                )
            return pattern, flags, matches

        # ---- Pipeline ---- #
        intent = do_intent()
        keywords = intent.get("keywords", [])
        inner_text, network, duration_sec, started, completed = capture()
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
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        used_parser, pattern_applied, flags_applied, reuse_matches = try_reuse(domain, inner_text, keywords)

        # Source mapping step (Sprint 1): only if not reused successfully
        chosen_source_body: str | None = None
        chosen_source_url: str | None = None
        chosen_source_type: str | None = None
        if not reuse_matches:
            # Build candidate examples first (heuristic); if none, fallback to keywords subset
            heuristic_examples = [e["text"] for e in find_target_examples(inner_text, keywords=keywords, target=intent.get("target"), max_examples=5)]
            probe_examples = heuristic_examples or keywords[:3]
            network_candidates = _search_examples_in_network(probe_examples, network)
            picked = _disambiguate_source(network_candidates, intent, llm) if network_candidates else None
            if picked:
                chosen_source_url = picked.get("url")
                chosen_source_type = picked.get("source_type")
                # Attempt to locate full body from original network list
                for ev in network:
                    if ev.get("url") == chosen_source_url:
                        chosen_source_body = ev.get("body_preview") or ""
                        break
                # Persist chosen source metadata
                try:
                    db.query(db_utils.ScrapingTask).filter(db_utils.ScrapingTask.task_id == task_id)  # type: ignore[attr-defined]
                except Exception:
                    pass
                db_utils.update_task_sources(
                    db,
                    task_id,
                    page_content=None,
                    network_requests=None,
                    intent=None,
                )
                # Direct column update for source metadata
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
        matches: List[str]
        if reuse_matches:
            matches = reuse_matches
        else:
            pattern_applied, flags_applied, gen_matches = generate_pattern(inner_text, keywords, intent, source_body=chosen_source_body)
            matches = gen_matches

        extracted = [
            {"text": m, "source": "innerText", "confidence": 1.0 if used_cached else 0.9}
            for m in matches
        ]

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
        else:
            db_utils.update_task_status(db, task_id=task_id, status="FAILED", error_message="No matches extracted")

        logger.info(
            "Task %s finished; target=%s pattern=%s matches=%d reused=%s",
            task_id,
            intent.get("target"),
            pattern_applied,
            len(matches),
            used_cached,
        )

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
            },
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"Task {task_id} failed: {exc}")
        db_utils.update_task_status(db, task_id=task_id, status="FAILED", error_message=str(exc))
        raise
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
