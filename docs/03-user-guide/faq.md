# FAQ & Troubleshooting

## Frequently Asked Questions

### General

**Q: Who can use this service?**  
A: Any user with an account can use the API to extract data from websites. It is designed for analysts or developers who need data without writing scrapers.

**Q: How do I authenticate?**  
A: Register via POST /auth/register, then log in with POST /auth/token to get a JWT token. Include Authorization: Bearer &lt;token&gt; in all protected requests.

**Q: What kinds of websites can be scraped?**  
A: Both static and dynamic sites are supported (via Playwright). However, sites requiring login or behind heavy anti-bot measures may not work without additional configuration.

**Q: How fast are the results?**  
A: Initial tasks may take a few seconds (due to LLM calls). Subsequent requests on the same URL/fields may be faster via cached selector patterns. There are no hard SLAs for response time; this is an experimental system.

### Account & Access

**Q: How do I reset my password?**  
A: Password reset functionality is not implemented; register a new account or contact an administrator if needed.

**Q: Can I delete my account?**  
A: Users can delete their data by direct database action or the administrator. (Not available via public API.)

### Features

**Q: What if my prompt is not specific enough?**  
A: The AI may return incorrect or empty results. For best results, be clear about what fields you want (e.g. include field names, avoid vague requests).

**Q: How do I know the data sources (HTML path) used?**  
A: Each result includes a source field indicating how it was extracted (e.g. generated_selector or schema_extraction). Source paths (XPaths) are shown in result objects.

### Error Troubleshooting

| Problem | Possible Cause | Solution |
| --- | --- | --- |
| **401 Unauthorized** | Invalid or expired token | Request a new token via POST /auth/token |
| **422 Validation Error** | Invalid URL format or prompt too short | Ensure URL begins with http/https and prompt ≥ 5 chars |
| **400 Input rejected** | Prompt injection or banned content detected | Modify your prompt to remove suspicious phrases |
| **429 Too Many Requests** | Rate limit exceeded (too many API calls) | Wait and retry (limits: /process:10/min, /token:10/min, /register:5/min) |
| **Status remains PENDING** | Workers may be down or busy | Ensure Celery workers (headless and AI) are running |
| **Status = FAILED** | Extraction or page load error | Check error message in status response; try altering prompt or URL |
| **No results returned** | Page didn't contain requested info or dynamic load failed | Verify the prompt context; ensure the site doesn't require login. Try manual inspection. |

### Troubleshooting Steps

- Check the [System Limitations](../appendices/system-limitations.md) for known constraints (e.g. request size limits).
- Review [Example Dialogs](../appendices/example-dialogs.md) for sample successful prompts.
- Use the Swagger UI (/docs) to interactively test endpoints and view models.
- If problems persist, check service logs (if accessible) for errors in the backend.
