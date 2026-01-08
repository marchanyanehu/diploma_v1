import os
import markdown
import asyncio
from playwright.async_api import async_playwright
import re

# Order of traversal
DOCS_DIR = r"c:\Users\user\Documents\diploma\docs"
OUTPUT_PDF = r"c:\Users\user\Documents\diploma\documentation\Marchan_Documentation.pdf"

# Define the order of files explicitly to match the logical flow
ORDERed_FILES = [
    "index.md", # Title Page
    
    # 01-project-overview
    "01-project-overview/index.md",
    "01-project-overview/problem-and-goals.md",
    "01-project-overview/stakeholders.md",
    "01-project-overview/scope.md",
    "01-project-overview/features.md",
    
    # 02-technical
    "02-technical/index.md",
    "02-technical/tech-stack.md",
    "02-technical/deployment.md",
    # Criteria - grab all in alphanumeric order
    # will handle dynamically below
    
    # 03-user-guide
    "03-user-guide/index.md",
    "03-user-guide/features.md",
    "03-user-guide/faq.md",
    
    # 04-retrospective
    "04-retrospective/index.md",
    
    # Appendices
    "appendices/api-reference.md",
    "appendices/db-schema.md",
    "appendices/glossary.md"
]

def get_criteria_files():
    base = os.path.join(DOCS_DIR, "02-technical", "criteria")
    files = sorted([f for f in os.listdir(base) if f.endswith(".md")])
    return [f"02-technical/criteria/{f}" for f in files]

def read_file(rel_path):
    full_path = os.path.join(DOCS_DIR, rel_path)
    if not os.path.exists(full_path):
        print(f"Warning: File not found: {full_path}")
        return ""
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()

def fix_image_paths(html_content, base_path):
    # We need to ensure images like <img src="../assets/..." /> point to absolute file paths for Playwright
    # Or markdown links ![alt](../assets/...) which become <img src="../assets/..." />
    
    # Simple regex to replace ../assets with absolute path to assets
    assets_abs_path = os.path.join(DOCS_DIR, "assets").replace("\\", "/")
    
    # Replace ../assets with file:///.../assets
    # Also handle assets/ if referenced directly
    
    def replacer(match):
        # match group 1 is the prefix (src="), group 2 is the path
        prefix = match.group(1)
        path = match.group(2)
        
        # Resolve path relative to DOCS_DIR if it starts with .. or .
        # Use a simplified approach: just target the assets folder
        if "assets/" in path:
            # find where assets/ starts
            idx = path.find("assets/")
            clean_path = path[idx:] # assets/images/foo.png
            abs_uri = f"file:///{os.path.join(DOCS_DIR, clean_path).replace(os.path.sep, '/')}"
            return f'{prefix}{abs_uri}'
        return match.group(0)

    # Regex for src="..." or href="..."
    return re.sub(r'(src="|href=")([^"]+)', replacer, html_content)

async def generate_pdf():
    # 1. Collect Content
    full_md_content = ""
    
    # Main list
    for rel_path in ORDERed_FILES:
        full_md_content += "\n\n<div style='page-break-before: always;'></div>\n\n" # Force page break between files
        full_md_content += read_file(rel_path)
        
    # Inject criteria files after tech-stack or where appropriate?
    # Actually, let's just insert them after 02-technical/index.md for logical flow, 
    # or follow the user structure. The template says "criteria/ - ADR for each evaluation criterion".
    # Let's verify if I missed them in the manual list.
    # I didn't include them in the manual list above properly in the middle.
    # Let's re-construct the list dynamically a bit.
    
    final_file_list = []
    for f in ORDERed_FILES:
        final_file_list.append(f)
        if f == "02-technical/tech-stack.md":
            # Add criteria here
            final_file_list.extend(get_criteria_files())
            
    # Re-read with correct list
    full_md_content = ""
    for i, rel_path in enumerate(final_file_list):
        content = read_file(rel_path)
        if i > 0:
             full_md_content += "\n\n<div style='page-break-before: always;'></div>\n\n"
        full_md_content += content

    # 2. Convert to HTML
    html_body = markdown.markdown(full_md_content, extensions=['tables', 'fenced_code', 'toc'])
    
    # 2.1 Transform Mermaid code blocks to divs for rendering
    # Simple regex to replace <pre><code class="language-mermaid">...</code></pre> with <div class="mermaid">...</div>
    # We must be careful not to break other code blocks by naively replacing </code></pre> globally.
    
    html_body = re.sub(
        r'<pre><code class="language-mermaid">(.*?)</code></pre>', 
        r'<div class="mermaid">\1</div>', 
        html_body, 
        flags=re.DOTALL
    )

    # 3. Add CSS and Boilerplate
    html_doc = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
        <script>mermaid.initialize({{startOnLoad:true}});</script>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #24292e;
                max-width: 900px;
                margin: 0 auto;
                padding: 40px;
            }}
            h1, h2, h3 {{ border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }}
            h1 {{ font-size: 2.5em; }}
            h2 {{ font-size: 2em; margin-top: 2em; }}
            code {{ background-color: #f6f8fa; padding: 0.2em 0.4em; border-radius: 3px; }}
            pre {{ background-color: #f6f8fa; padding: 16px; overflow: auto; border-radius: 3px; }}
            pre code {{ background-color: transparent; padding: 0; }}
            /* Ensure mermaid divs don't look like code blocks if styling leaks */
            .mermaid {{ background-color: white; padding: 10px; display: flex; justify-content: center; }}
            table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
            th, td {{ border: 1px solid #dfe2e5; padding: 6px 13px; }}
            th {{ background-color: #f6f8fa; font-weight: 600; }}
            img {{ max-width: 100%; }}
            blockquote {{ border-left: 0.25em solid #dfe2e5; color: #6a737d; padding: 0 1em; }}
        </style>
    </head>
    <body>
        <div class="markdown-body">
            {html_body}
        </div>
    </body>
    </html>
    """
    
    # 4. Fix Images
    html_doc = fix_image_paths(html_doc, DOCS_DIR)
    
    # Save temp html for debugging
    temp_html = os.path.join(DOCS_DIR, "temp_full_docs.html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_doc)
        
    # 5. Generate PDF
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        url = f"file:///{temp_html.replace(os.path.sep, '/')}"
        print(f"Rendering {url}...")
        
        await page.goto(url, wait_until="networkidle")
        
        # Give Mermaid time to render (networkidle might not catch JS execution)
        # Wait for at least one svg inside .mermaid if any exist
        try:
             # Check if there are any mermaid blocks
             count = await page.locator('.mermaid').count()
             if count > 0:
                 print(f"Found {count} mermaid diagrams. Waiting for render...")
                 await page.wait_for_selector('.mermaid svg', timeout=5000)
                 # Add a small buffer for layout stability
                 await page.wait_for_timeout(2000)
        except Exception as e:
            print(f"Warning waiting for mermaid: {e}")

        # Create output dir if needed
        out_dir = os.path.dirname(OUTPUT_PDF)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
            
        await page.pdf(path=OUTPUT_PDF, format="A4", margin={"top": "2cm", "bottom": "2cm", "left": "2cm", "right": "2cm"})
        
        print(f"PDF successfully generated at: {OUTPUT_PDF}")
        await browser.close()
        
    # Cleanup
    if os.path.exists(temp_html):
        os.remove(temp_html)

if __name__ == "__main__":
    asyncio.run(generate_pdf())
