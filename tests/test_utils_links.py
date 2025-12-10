
import pytest
from services.ai_worker.utils import convert_html_to_markdown_like

def test_convert_html_to_markdown_like():
    html = """
    <html>
        <body>
            <h1>Job List</h1>
            <div class="job">
                <a href="/job/123">Software Engineer</a>
                <span>$100k</span>
            </div>
            <div class="job">
                <a href="https://example.com/job/456">Product Manager</a>
            </div>
            <p>Contact us at <a href="mailto:hr@example.com">hr@example.com</a></p>
        </body>
    </html>
    """
    
    text = convert_html_to_markdown_like(html)
    
    assert "[Software Engineer](/job/123)" in text
    assert "[Product Manager](https://example.com/job/456)" in text
    assert "[hr@example.com](mailto:hr@example.com)" in text
    assert "$100k" in text
    assert "Job List" in text
    assert "<html>" not in text
    assert "href=" not in text

def test_convert_html_to_markdown_like_nested():
    html = '<a href="/link"><b>Bold Link</b></a>'
    text = convert_html_to_markdown_like(html)
    assert "[Bold Link](/link)" in text

def test_convert_html_to_markdown_like_empty_text():
    html = '<a href="/link"></a>'
    text = convert_html_to_markdown_like(html)
    assert "[link](/link)" in text
