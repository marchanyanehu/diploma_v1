
from __future__ import annotations

import os
import time
import random
import logging
import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from playwright.async_api import async_playwright, Page
from shared.celery_app import celery_app

logger = logging.getLogger(__name__)

async def _async_browse_and_capture(url: str) -> tuple[str, str, list[dict[str, Any]], int, datetime, datetime]:
    started = datetime.now(timezone.utc)
    network_events: list[dict[str, Any]] = []
    
    async with async_playwright() as p:
        # Launch options
        headless = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
        browser = await p.chromium.launch(headless=headless)
        
        # Context options (stealth)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US"
        )
        
        page = await context.new_page()
        
        # Network capturing
        async def handle_response(response):
            try:
                # Only capture XHR/Fetch/Document/Script to save space
                if response.request.resource_type in ["xhr", "fetch", "document", "script", "stylesheet"]:
                    body = ""
                    truncated = False
                    # Try to get text for json/text responses
                    if response.ok and response.request.resource_type in ["xhr", "fetch"]:
                        try:
                            text = await response.text()
                            if len(text) > 50000:
                                body = text[:50000]
                                truncated = True
                            else:
                                body = text
                        except Exception:
                            pass
                            
                    network_events.append({
                        "url": response.url,
                        "method": response.request.method,
                        "status": response.status,
                        "type": response.request.resource_type,
                        "body_preview": body,
                        "body_truncated": truncated,
                        "headers": response.headers
                    })
            except Exception as e:
                # Ignore errors during capture to not break flow
                pass

        page.on("response", handle_response)
        
        try:
            # Navigate
            timeout = int(os.getenv("PLAYWRIGHT_NAV_TIMEOUT_MS", "30000"))
            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            
            # Wait for some settlement (optional)
            settle = int(os.getenv("PLAYWRIGHT_SETTLE_DELAY_MS", "1000"))
            if settle > 0:
                await page.wait_for_timeout(settle)
            
            # Extract
            content = await page.content()
            # Get visible text (innerText of body)
            inner_text = await page.eval_on_selector("body", "el => el.innerText")
            
        except Exception as e:
            logger.error(f"Playwright navigation error: {e}")
            # Return partial data if possible
            content = await page.content() if 'page' in locals() else ""
            inner_text = ""
            raise e
        finally:
            await browser.close()
            
    completed = datetime.now(timezone.utc)
    duration = int((completed - started).total_seconds())
    return inner_text, content, network_events, duration, started, completed

@celery_app.task(name="scrape.fetch_page")
def fetch_page(task_id: str, url: str, intent: Dict[str, Any]):
    """Fetch page content using Playwright and trigger AI processing."""
    logger.info("headless.fetch_page.received", extra={"task_id": task_id, "url": url})
    
    try:
        # Execute async playwright in sync task
        inner_text, html_content, network, duration, started, completed = asyncio.run(_async_browse_and_capture(url))
        
        logger.info("headless.fetch_page.captured", extra={"task_id": task_id, "bytes": len(inner_text)})
        
        # Trigger next step: AI Processing
        celery_app.send_task(
            "scrape.process_content",
            args=[
                task_id, 
                url, 
                intent, 
                inner_text, 
                html_content, 
                network, 
                duration, 
                started.isoformat(), 
                completed.isoformat()
            ],
            queue="ai_queue"
        )
        logger.info("headless.fetch_page.delegated_to_ai", extra={"task_id": task_id})
        
        return {"status": "SUCCESS", "message": "Fetched and delegated"}
        
    except Exception as exc:
        logger.exception("headless.fetch_page.failed", extra={"task_id": task_id})
        from services.api.database import SessionLocal
        from services.api import db_utils
        db = SessionLocal()
        try:
            db_utils.update_task_status(db, task_id=task_id, status="FAILED", error_message=f"Fetch failed: {str(exc)}")
        finally:
            db.close()
        # We don't raise to avoid infinite retries unless configured
        return {"status": "FAILED", "error": str(exc)}
