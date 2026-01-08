import os
import re
import asyncio
from playwright.async_api import async_playwright

DOCS_DIR = r"c:\Users\user\Documents\diploma\docs"

async def validate():
    print("Scanning for Mermaid diagrams...")
    mermaid_blocks = []
    
    # 1. Scan all md files
    for root, dirs, files in os.walk(DOCS_DIR):
        for file in files:
            if file.endswith(".md"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Find ```mermaid ... ``` blocks
                    matches = re.finditer(r"```mermaid\n(.*?)\n```", content, re.DOTALL)
                    for i, m in enumerate(matches):
                        mermaid_blocks.append({
                            "file": file,
                            "index": i,
                            "code": m.group(1).strip()
                        })
    
    print(f"Found {len(mermaid_blocks)} diagrams.")
    
    # 2. Create Validation HTML
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
        <script>mermaid.initialize({startOnLoad:true});</script>
    </head>
    <body>
    """
    
    for i, block in enumerate(mermaid_blocks):
        html_content += f"""
        <div class="test-case" id="diagram-{i}" data-file="{block['file']}">
            <h3>{block['file']} #{block['index']}</h3>
            <div class="mermaid">
{block['code']}
            </div>
            <hr/>
        </div>
        """
        
    html_content += "</body></html>"
    
    temp_html = os.path.join(DOCS_DIR, "validation.html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    # 3. Render and Check for Errors
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Capture console errors
        page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}") if msg.type == "error" else None)
        
        url = f"file:///{temp_html.replace(os.path.sep, '/')}"
        print(f"Validating at {url}...")
        
        await page.goto(url, wait_until="networkidle")
        
        # Wait a bit for rendering
        await page.wait_for_timeout(2000)
        
            # Check for syntax errors visually
        content = await page.content()
        if "Syntax error" in content:
            print("❌ VALIDATION FAILED: Syntax errors detected!")
            count = await page.locator('.mermaid').count()
            for i in range(count):
                div = page.locator('.mermaid').nth(i)
                text = await div.inner_text()
                if "Syntax error" in text:
                     # Get metadata from parent div
                     parent = page.locator(f'#diagram-{i}')
                     filename = await parent.get_attribute("data-file")
                     print(f"  -> Error in {filename} (Diagram #{i})")
                     # Print the first few lines of the code to be sure
                     code = mermaid_blocks[i]['code']
                     print(f"     Code snippet: {code[:50]}...")
        else:
            print("✅ ALL DIAGRAMS VALIDATED SUCCESSFULLY")
            
        await browser.close()
    
    if os.path.exists(temp_html):
        os.remove(temp_html)

if __name__ == "__main__":
    asyncio.run(validate())
