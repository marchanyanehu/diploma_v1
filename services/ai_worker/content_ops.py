
import re
import logging
from typing import List, Dict, Any

from .utils import extract_snippet, extract_micro_snippet

logger = logging.getLogger(__name__)

def find_text_in_raw_content(raw_content: str, text_examples: List[str], max_candidates: int = 20) -> List[Dict[str, Any]]:
    """Step 3: Find text examples in raw content (no LLM, pure string search)."""
    candidates = []
    seen_snippets: set = set()
    
    for ex in text_examples:
        if not ex or len(ex) < 3:
            continue
        
        # Try multiple search strategies for multi-line text
        search_terms = [ex]  # Full text first
        
        # If example has newlines, also try first line and significant chunks
        if '\n' in ex:
            lines = [l.strip() for l in ex.split('\n') if l.strip() and len(l.strip()) > 5]
            if lines:
                search_terms.append(lines[0])  # First line
                # Also try first 2-3 significant words from first line
                words = lines[0].split()
                if len(words) >= 2:
                    search_terms.append(' '.join(words[:3]))
        
        for search_term in search_terms:
            if not search_term or len(search_term) < 3:
                continue
                
            start = 0
            while len(candidates) <= max_candidates:
                idx = raw_content.find(search_term, start)
                if idx == -1:
                    break
                
                snippet = extract_snippet(raw_content, idx, len(search_term))
                micro = extract_micro_snippet(raw_content, idx, len(search_term))
                logger.info(f"MICRO_SNIPPET for '{search_term[:30]}': {repr(micro)}")
                
                if snippet not in seen_snippets:
                    candidates.append({
                        "example_match": search_term, 
                        "snippet": snippet, 
                        "micro_snippet": micro,  # Store the micro-snippet too
                        "offset": idx
                    })
                    seen_snippets.add(snippet)
                
                start = idx + 1
                if len(candidates) > 10:
                    break
            
            # If we found candidates with this term, stop trying alternatives
            if candidates:
                break
        
        if len(candidates) > max_candidates:
            break
            
    return candidates
