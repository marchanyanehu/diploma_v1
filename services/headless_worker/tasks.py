
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

USER_AGENTS = [
    # Rotate a few modern Chrome UA strings to avoid static fingerprints
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.142 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.207 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.122 Safari/537.36",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1680, "height": 1050},
    {"width": 1366, "height": 768},
]

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = window.chrome || { runtime: {} };
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4] });
const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
if (originalQuery) {
  window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications'
      ? Promise.resolve({ state: Notification.permission })
      : originalQuery(parameters)
  );
}
"""

async def _extract_semantic_content(page: Page) -> str:
    """
    Extract semantic content including visible text, buttons, links, images (alt text),
    and other interactive elements to provide richer context than plain innerText.
    """
    script = """
    () => {
        const elements = [];
        
        // Helper to check if element is visible
        function isVisible(el) {
            if (!el) return false;
            const style = window.getComputedStyle(el);
            return style.display !== 'none' && 
                   style.visibility !== 'hidden' && 
                   style.opacity !== '0' &&
                   el.offsetWidth > 0 && 
                   el.offsetHeight > 0;
        }
        
        // Extract text content with context markers
        function extractText(el, prefix = '') {
            if (!isVisible(el)) return null;
            
            const tag = el.tagName.toLowerCase();
            let text = '';
            
            // Links
            if (tag === 'a') {
                const href = el.getAttribute('href') || '';
                const linkText = el.innerText.trim();
                if (linkText) {
                    text = `[LINK: ${linkText}]`;
                    if (href && !href.startsWith('#') && !href.startsWith('javascript:')) {
                        text += ` (${href})`;
                    }
                }
            }
            // Buttons
            else if (tag === 'button' || el.getAttribute('role') === 'button') {
                const btnText = el.innerText.trim() || el.getAttribute('aria-label') || '';
                if (btnText) text = `[BUTTON: ${btnText}]`;
            }
            // Images
            else if (tag === 'img') {
                const alt = el.getAttribute('alt') || '';
                const title = el.getAttribute('title') || '';
                if (alt) text = `[IMAGE: ${alt}]`;
                else if (title) text = `[IMAGE: ${title}]`;
            }
            // Input fields
            else if (tag === 'input') {
                const type = el.getAttribute('type') || 'text';
                const placeholder = el.getAttribute('placeholder') || '';
                const label = el.getAttribute('aria-label') || '';
                const value = el.value || '';
                
                if (type === 'submit' || type === 'button') {
                    text = `[BUTTON: ${value || label || 'Submit'}]`;
                } else if (placeholder) {
                    text = `[INPUT: ${placeholder}]`;
                } else if (label) {
                    text = `[INPUT: ${label}]`;
                }
            }
            // Select dropdowns
            else if (tag === 'select') {
                const label = el.getAttribute('aria-label') || 
                             el.previousElementSibling?.innerText?.trim() || '';
                const options = Array.from(el.options)
                    .filter(opt => opt.text.trim())
                    .map(opt => opt.text.trim())
                    .slice(0, 5); // First 5 options
                if (label || options.length) {
                    text = `[SELECT: ${label}`;
                    if (options.length) text += ` - Options: ${options.join(', ')}`;
                    text += ']';
                }
            }
            // Headings (preserve structure)
            else if (['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(tag)) {
                const headingText = el.innerText.trim();
                if (headingText) text = `\\n## ${headingText}\\n`;
            }
            // Lists
            else if (tag === 'li') {
                const listText = el.innerText.trim();
                if (listText) text = `• ${listText}`;
            }
            // Table cells (preserve data structure)
            else if (tag === 'td' || tag === 'th') {
                const cellText = el.innerText.trim();
                if (cellText) text = cellText + ' | ';
            }
            // Labels
            else if (tag === 'label') {
                const labelText = el.innerText.trim();
                if (labelText) text = `[LABEL: ${labelText}]`;
            }
            // ARIA labels and roles
            else {
                const ariaLabel = el.getAttribute('aria-label');
                const role = el.getAttribute('role');
                if (ariaLabel && ['menuitem', 'tab', 'option'].includes(role)) {
                    text = `[${role.toUpperCase()}: ${ariaLabel}]`;
                }
            }
            
            return text;
        }
        
        // Walk the DOM and extract semantic content
        function walk(node) {
            if (!node || node.nodeType !== 1) return;
            
            // Skip scripts, styles, and hidden elements
            const tag = node.tagName.toLowerCase();
            if (['script', 'style', 'noscript', 'iframe'].includes(tag)) return;
            if (!isVisible(node)) return;
            
            // Extract semantic content for this node
            const text = extractText(node);
            if (text) elements.push(text);
            
            // For nodes without special handling, just get innerText if it's a leaf
            if (!text && node.children.length === 0) {
                const innerText = node.innerText?.trim();
                if (innerText && innerText.length > 0 && innerText.length < 200) {
                    elements.push(innerText);
                }
            }
            
            // Recurse into children only if we didn't extract special content
            if (!text || ['div', 'section', 'article', 'nav', 'main', 'header', 'footer'].includes(tag)) {
                for (const child of node.children) {
                    walk(child);
                }
            }
        }
        
        walk(document.body);
        return elements.filter(e => e && e.trim()).join('\\n');
    }
    """
    
    try:
        semantic_content = await page.evaluate(script)
        return semantic_content or ""
    except Exception as e:
        logger.warning(f"Failed to extract semantic content: {e}")
        # Fallback to innerText
        try:
            return await page.eval_on_selector("body", "el => el.innerText")
        except Exception:
            return ""

async def _async_browse_and_capture(url: str) -> tuple[str, str, str, list[dict[str, Any]], int, datetime, datetime]:
    started = datetime.now(timezone.utc)
    network_events: list[dict[str, Any]] = []
    
    async with async_playwright() as p:
        # Launch options
        headless = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
        proxy_url = os.getenv("PLAYWRIGHT_PROXY")
        proxy_username = os.getenv("PLAYWRIGHT_PROXY_USERNAME")
        proxy_password = os.getenv("PLAYWRIGHT_PROXY_PASSWORD")
        proxy = None
        if proxy_url:
            proxy = {"server": proxy_url}
            if proxy_username and proxy_password:
                proxy["username"] = proxy_username
                proxy["password"] = proxy_password

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ]
        browser = await p.chromium.launch(
            headless=headless,
            args=launch_args,
            ignore_default_args=["--enable-automation"],
            proxy=proxy,
        )
        
        # Context options (stealth)
        ua = random.choice(USER_AGENTS)
        viewport = random.choice(VIEWPORTS)
        tz = os.getenv("PLAYWRIGHT_TIMEZONE", "America/Los_Angeles")
        lang = os.getenv("PLAYWRIGHT_LANG", "en-US,en;q=0.9")
        sec_ch_ua = os.getenv(
            "PLAYWRIGHT_SEC_CH_UA",
            '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        )
        context = await browser.new_context(
            user_agent=ua,
            viewport=viewport,
            locale="en-US",
            timezone_id=tz,
            device_scale_factor=1,
            extra_http_headers={
                "Accept-Language": lang,
                "sec-ch-ua": sec_ch_ua,
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            },
        )
        await context.add_init_script(STEALTH_INIT_SCRIPT)
        
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
            except Exception:
                # Ignore errors during capture to not break flow
                pass

        page.on("response", handle_response)
        
        try:
            # Navigate - use networkidle for better JS content loading
            timeout = int(os.getenv("PLAYWRIGHT_NAV_TIMEOUT_MS", "30000"))
            wait_until = os.getenv("PLAYWRIGHT_WAIT_UNTIL", "networkidle")
            await page.goto(url, timeout=timeout, wait_until=wait_until)
            await page.wait_for_timeout(random.randint(800, 1800))
            
            # Try to dismiss common cookie consent banners
            try:
                cookie_selectors = [
                    'button:has-text("Accept")',
                    'button:has-text("Accept All")',
                    'button:has-text("I Accept")',
                    'button:has-text("Got it")',
                    '[id*="cookie"] button',
                    '[class*="cookie"] button:has-text("Accept")',
                ]
                for selector in cookie_selectors:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=500):
                        await btn.click()
                        await page.wait_for_timeout(500)
                        break
            except Exception:
                pass  # Cookie banner dismissal is optional
            
            # Wait for some settlement (optional)
            settle = int(os.getenv("PLAYWRIGHT_SETTLE_DELAY_MS", "2000"))
            if settle > 0:
                await page.wait_for_timeout(settle)
            
            # Extract
            content = await page.content()
            # Get visible text (innerText of body)
            inner_text = await page.eval_on_selector("body", "el => el.innerText")
            
            # Extract semantic content (text + interactive elements)
            semantic_text = await _extract_semantic_content(page)
            
        except Exception as e:
            logger.error(f"Playwright navigation error: {e}")
            # Return partial data if possible
            content = await page.content() if 'page' in locals() else ""
            inner_text = ""
            semantic_text = ""
            raise e
        finally:
            await browser.close()
            
    completed = datetime.now(timezone.utc)
    duration = int((completed - started).total_seconds())
    return inner_text, semantic_text, content, network_events, duration, started, completed

@celery_app.task(name="scrape.fetch_page")
def fetch_page(task_id: str, url: str, intent: Dict[str, Any]):
    """Fetch page content using Playwright and trigger AI processing."""
    logger.info("headless.fetch_page.received", extra={"task_id": task_id, "url": url})
    
    try:
        # Execute async playwright in sync task
        inner_text, semantic_text, html_content, network, duration, started, completed = asyncio.run(_async_browse_and_capture(url))
        
        logger.info("headless.fetch_page.captured", extra={"task_id": task_id, "text_bytes": len(inner_text), "semantic_bytes": len(semantic_text)})
        
        # Trigger next step: AI Processing
        celery_app.send_task(
            "scrape.process_content",
            args=[
                task_id, 
                url, 
                intent, 
                semantic_text,  # Use semantic text instead of plain inner_text
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
