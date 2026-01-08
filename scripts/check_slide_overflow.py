import argparse
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_args() -> argparse.Namespace:
    root = _repo_root()
    parser = argparse.ArgumentParser(
        description="Detect slides in slides.html whose content overflows the fixed 720px slide height."
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=root / "presentation" / "slides.html",
        help="Path to slides.html",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=2,
        help="Overflow threshold in pixels (scrollHeight - clientHeight > threshold).",
    )
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    html_path = args.html.resolve()

    if not html_path.exists():
        raise FileNotFoundError(f"Presentation file not found: {html_path}")

    url = html_path.as_uri()

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        await page.goto(url, wait_until="load")
        await page.emulate_media(media="screen")

        # Wait for local images to settle so layout/scrollHeight is stable
        await page.evaluate(
            """() => Promise.all(Array.from(document.images || []).map(img => {
                if (img.complete) return true;
                return new Promise(resolve => {
                    img.addEventListener('load', () => resolve(true), { once: true });
                    img.addEventListener('error', () => resolve(true), { once: true });
                });
            }))"""
        )
        await page.wait_for_timeout(200)

        results = await page.evaluate(
            """(threshold) => {
                const slides = Array.from(document.querySelectorAll('div.slide'));
                return slides.map((s, idx) => {
                    const h2 = s.querySelector('h2');
                    const h1 = s.querySelector('h1');
                    const title = (h2?.innerText || h1?.innerText || '').trim();
                    const overflowPx = s.scrollHeight - s.clientHeight;
                    return {
                        index: idx + 1,
                        title,
                        clientHeight: s.clientHeight,
                        scrollHeight: s.scrollHeight,
                        overflowPx,
                        overflow: overflowPx > threshold,
                    };
                });
            }""",
            args.threshold,
        )

        overflowed = [r for r in results if r["overflow"]]
        if not overflowed:
            print("No overflows detected.")
        else:
            for r in overflowed:
                print(
                    f"OVERFLOW slide {r['index']:02d}: {r['title']} "
                    f"(overflow {r['overflowPx']}px; scroll={r['scrollHeight']}, client={r['clientHeight']})"
                )

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())


