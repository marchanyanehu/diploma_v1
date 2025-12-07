# System Limitations

This document describes the known limitations and constraints of the Intelligent Web Data Aggregator system. Understanding these limitations helps users set appropriate expectations and choose the right approach for their data extraction needs.

## 🚫 What the System CANNOT Do

### Data Extraction Limitations

1. **No Real-Time Data Streaming**
   - The system processes requests asynchronously with polling-based status checks
   - Not suitable for real-time data feeds or live streaming requirements
   - Typical response times: 5-30 seconds depending on page complexity

2. **No Authentication to Target Websites**
   - Cannot log into websites requiring credentials (login forms, OAuth)
   - Only publicly accessible pages can be scraped
   - Pages behind paywalls or authentication walls are not accessible

3. **Limited JavaScript Rendering**
   - Uses Playwright for JavaScript rendering, but heavily dynamic SPAs may not fully render
   - Infinite scroll pages only capture initially loaded content
   - Web apps requiring user interaction (clicks, scrolls) for data loading may be incomplete

4. **No CAPTCHA Solving**
   - Cannot bypass CAPTCHA, reCAPTCHA, or similar bot protection
   - Websites with aggressive bot detection may block requests
   - No support for solving image-based or puzzle challenges

5. **No File Downloads**
   - Cannot download and process binary files (PDFs, images, videos)
   - Limited to text-based data extraction from HTML pages
   - Network request capture is text-only (JSON/XML responses)

### Content Processing Limitations

6. **No Image/Media Analysis**
   - Cannot extract text from images (no OCR capability)
   - Cannot analyze or describe image content
   - Image URLs can be extracted, but not processed

7. **Limited Language Support for Intent Extraction**
   - Optimized for English and Russian prompts
   - Other languages may have reduced accuracy in intent extraction
   - Regex patterns are language-agnostic once generated

8. **No Semantic Understanding of Page Structure**
   - Relies on pattern matching and LLM analysis, not true semantic understanding
   - Complex nested data structures may not be correctly identified
   - Unusual page layouts may confuse the extraction pipeline

### Technical Constraints

9. **Rate Limits Apply**
   - API endpoints are rate-limited (10 requests/minute for scraping)
   - LLM API rate limits from providers (Gemini/OpenAI) apply
   - High-volume scraping not recommended

10. **Maximum Content Size**
    - Pages larger than ~1MB may be truncated
    - Very long pages may exceed LLM context limits
    - Network response previews limited to 50KB per request

11. **Session Isolation**
    - Each scraping task is independent
    - No persistent browser sessions between requests
    - Cookies and local storage are not preserved

12. **No Webhook/Push Notifications**
    - Results must be polled via status endpoint
    - No callback URLs or push notification support
    - Scheduled jobs create tasks but don't notify on completion

### Data Quality Limitations

13. **Extraction Accuracy**
    - Regex-based extraction may miss edge cases
    - Generated patterns may be too broad or too narrow
    - Cached parsers may become stale if website structure changes

14. **No Data Transformation**
    - Extracts raw data as-is from pages
    - No built-in data cleaning, normalization, or transformation
    - No data type conversion (dates, numbers remain as strings)

15. **No Cross-Page Aggregation**
    - Each request processes a single URL
    - No automatic pagination or following links
    - Multi-page scraping requires multiple API calls

## ⚠️ Known Edge Cases

### Websites That May Cause Issues

- **Heavy JavaScript frameworks**: React/Vue SPAs with client-side routing
- **Lazy-loaded content**: Images and content loaded on scroll
- **Single-page applications**: Content loaded via AJAX after initial render
- **Anti-scraping protection**: CloudFlare, Akamai, Imperva protected sites
- **Dynamic pricing**: Prices that change based on cookies/location

### Input That May Cause Problems

- **Very short prompts**: Less than 5 characters may lack context
- **Ambiguous requests**: "Get everything" without specifying what
- **Multiple unrelated targets**: "Get prices AND news AND images"
- **Non-existent data**: Requesting data types not present on page

## 📊 Performance Expectations

| Metric | Typical Range | Maximum |
|--------|---------------|---------|
| Response time (simple page) | 3-10 seconds | 30 seconds |
| Response time (complex page) | 10-30 seconds | 60 seconds |
| Concurrent users | 10-50 | 100 (with Redis scaling) |
| Prompt length | 5-1000 chars | 1000 characters |
| Cached parser reuse | 80%+ for same domain | - |

## 🔒 Security Limitations

- **No end-to-end encryption** for scraped content in transit through workers
- **API keys stored in memory** during runtime (not persisted)
- **Logs may contain URLs** (but not full page content by default)
- **Rate limiting is IP-based**, not foolproof against distributed attacks

## 💡 Recommendations

For use cases that fall outside these limitations:

1. **For authenticated sites**: Consider browser automation tools with session management
2. **For real-time data**: Use WebSocket-based scraping solutions
3. **For high volume**: Deploy dedicated scraping infrastructure
4. **For media extraction**: Integrate OCR/image analysis services separately
5. **For complex navigation**: Use purpose-built web crawlers with link following

---

*Last updated: December 2025*
