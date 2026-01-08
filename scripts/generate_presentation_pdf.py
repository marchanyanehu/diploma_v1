import argparse
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_args() -> argparse.Namespace:
    root = _repo_root()
    default_html = root / "presentation" / "slides.html"
    default_pdf = root / "presentation" / "Marchan_Presentation.pdf"

    parser = argparse.ArgumentParser(description="Render the HTML slide deck to a PDF via Playwright.")
    parser.add_argument("--html", type=Path, default=default_html, help="Path to slides.html")
    parser.add_argument("--out", type=Path, default=default_pdf, help="Output PDF path")

    # Defaults: 16:9 slide size (matches 1280x720 at 96 DPI => 13.333in x 7.5in).
    # If --format is provided, width/height are ignored.
    parser.add_argument("--format", type=str, default="", help='PDF format, e.g. "A4". If set, overrides width/height.')
    parser.add_argument("--width", type=str, default="13.333in", help='Page width (e.g. "13.333in", "1280px")')
    parser.add_argument("--height", type=str, default="7.5in", help='Page height (e.g. "7.5in", "720px")')
    parser.add_argument("--landscape", action="store_true", help="Force landscape mode (mainly for --format)")

    parser.add_argument("--wait-until", type=str, default="networkidle", help="Playwright wait_until strategy")
    parser.add_argument("--print-background", action="store_true", help="Print CSS backgrounds")

    return parser.parse_args()


async def generate_presentation_pdf(
    html_path: Path,
    out_path: Path,
    *,
    pdf_format: str = "",
    width: str = "13.333in",
    height: str = "7.5in",
    landscape: bool = False,
    wait_until: str = "networkidle",
    print_background: bool = True,
) -> None:
    html_path = html_path.resolve()
    out_path = out_path.resolve()

    if not html_path.exists():
        raise FileNotFoundError(f"Presentation file not found: {html_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        url = html_path.as_uri()
        print(f"Rendering {url}...")

        await page.goto(url, wait_until=wait_until)
        await page.emulate_media(media="screen")
        # Ensure local images are fully loaded before printing to PDF.
        # Without this, some slides may render with blank screenshot areas.
        await page.evaluate(
            """() => Promise.all(Array.from(document.images || []).map(img => {
                if (img.complete) return true;
                return new Promise(resolve => {
                    img.addEventListener('load', () => resolve(true), { once: true });
                    img.addEventListener('error', () => resolve(true), { once: true });
                });
            }))"""
        )
        await page.wait_for_timeout(300)

        pdf_kwargs: dict = {
            "path": str(out_path),
            "print_background": print_background,
            "margin": {"top": "0cm", "bottom": "0cm", "left": "0cm", "right": "0cm"},
        }

        if pdf_format:
            pdf_kwargs["format"] = pdf_format
            pdf_kwargs["landscape"] = landscape
        else:
            pdf_kwargs["width"] = width
            pdf_kwargs["height"] = height

        await page.pdf(**pdf_kwargs)

        print(f"Presentation PDF successfully generated at: {out_path}")
        await browser.close()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(
        generate_presentation_pdf(
            args.html,
            args.out,
            pdf_format=args.format,
            width=args.width,
            height=args.height,
            landscape=args.landscape,
            wait_until=args.wait_until,
            print_background=args.print_background or True,
        )
    )
