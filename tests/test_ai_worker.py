
import pytest
from unittest.mock import MagicMock, patch
from services.ai_worker.tasks import process_content, _find_candidates_in_html
from datetime import datetime, timezone

@patch('services.ai_worker.tasks.SessionLocal')
@patch('services.ai_worker.tasks.LLMClient')
@patch('services.ai_worker.tasks.db_utils')
def test_process_content_optimized_flow(mock_db_utils, mock_llm_cls, mock_session_cls):
    # Mock setup
    mock_db = MagicMock()
    mock_session_cls.return_value = mock_db
    
    mock_llm = MagicMock()
    mock_llm_cls.from_env.return_value = mock_llm
    
    # Mock LLM responses
    # 1. Intent
    # 2. Disambiguation
    # 3. Regex Generation
    mock_llm.chat.side_effect = [
        '{"target": "prices", "keywords": ["price", "cost"]}', # Intent (not called in process_content directly anymore?)
        # Actually intent is passed in.
    ]
    mock_llm.generate_text.side_effect = [
        '{"best_option_index": 0, "reason": "good fit"}', # Disambiguate
    ]
    # Iterative regex gen uses chat or generate_text? Uses iterative_regex_generation which uses chat
    
    task_id = "task-123"
    url = "http://example.com"
    intent = {"target": "prices", "keywords": ["price", "cost"]}
    inner_text = "Product A price is $10"
    html_content = "<html><body><div class='item'>Product A price is $10</div></body></html>"
    network = []
    duration = 1
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # Mock find_cached_parser to return empty (force generation)
    mock_db_utils.find_cached_parser.return_value = []
    
    # Mock regex generation result
    with patch('services.ai_worker.tasks.regex_generation.iterative_regex_generation') as mock_gen:
        mock_gen.return_value = {
            "success": True,
            "final_pattern": r"price is (\$\d+)",
            "final_flags": "i"
        }
        
        process_content(
            task_id, url, intent, inner_text, html_content, network, duration, now_iso, now_iso
        )
        
        # Verification
        # Step 1: find examples (implicit in code)
        # Step 2: find candidates
        # Step 3: disambiguate
        # Step 4: generate regex
        
        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args[1]
        assert "snippet" in call_kwargs
        assert call_kwargs["snippet"] # Should not be empty
        
        mock_db_utils.persist_extraction_result.assert_called_once()
        mock_db_utils.record_new_parser.assert_called_once()

def test_find_candidates():
    html = "<div>abc</div><div>def</div><div>abc again</div>"
    examples = ["abc"]
    candidates = _find_candidates_in_html(html, examples)
    # Deduplication should merge these into one candidate since snippet window covers both
    assert len(candidates) == 1
    assert candidates[0]["offset"] == 5
