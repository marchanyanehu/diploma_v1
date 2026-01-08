import argparse
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_args() -> argparse.Namespace:
    root = _repo_root()
    default_html = root / "presentation" / "slides.html"
    default_out = root / "presentation" / "_slide.png"

    parser = argparse.ArgumentParser(description="Render a single slide from slides.html to a PNG via Playwright.")
    parser.add_argument("--html", type=Path, default=default_html, help="Path to slides.html")
    parser.add_argument("--out", type=Path, default=default_out, help="Output PNG path")
    parser.add_argument("--index", type=int, required=True, help="1-based slide index to render (e.g., 19)")
    parser.add_argument("--wait-ms", type=int, default=300, help="Extra wait time before screenshot (ms)")

    return parser.parse_args()


async def render_slide_png(html_path: Path, out_path: Path, *, index: int, wait_ms: int = 300) -> None:
    html_path = html_path.resolve()
    out_path = out_path.resolve()

    if index < 1:
        raise ValueError("--index must be >= 1")
    if not html_path.exists():
        raise FileNotFoundError(f"Presentation file not found: {html_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        url = html_path.as_uri()
        await page.goto(url, wait_until="load")
        await page.emulate_media(media="screen")

        # Wait for all images (local file:// assets too)
        await page.evaluate(
            """() => Promise.all(Array.from(document.images || []).map(img => {
                if (img.complete) return true;
                return new Promise(resolve => {
                    img.addEventListener('load', () => resolve(true), { once: true });
                    img.addEventListener('error', () => resolve(true), { once: true });
                });
            }))"""
        )
        if wait_ms > 0:
            await page.wait_for_timeout(wait_ms)

        slides = page.locator("div.slide")
        count = await slides.count()
        if index > count:
            raise ValueError(f"Requested slide index {index}, but only {count} slides exist")

        await slides.nth(index - 1).screenshot(path=str(out_path))
        await browser.close()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(render_slide_png(args.html, args.out, index=args.index, wait_ms=args.wait_ms))


