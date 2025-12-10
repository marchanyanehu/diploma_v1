
import pytest
from unittest.mock import MagicMock, patch
from services.ai_worker.tasks import process_content
from services.ai_worker.content_ops import find_text_in_raw_content
from datetime import datetime, timezone

@patch('services.ai_worker.tasks.SessionLocal')
@patch('services.ai_worker.tasks.LLMClient')
@patch('services.ai_worker.tasks.db_utils')
@patch('services.ai_worker.workflows.db_utils') # workflows also uses db_utils
def test_process_content_optimized_flow(mock_workflows_db_utils, mock_db_utils, mock_llm_cls, mock_session_cls):
    # Mock setup
    mock_db = MagicMock()
    mock_session_cls.return_value = mock_db
    
    mock_llm = MagicMock()
    mock_llm_cls.from_env.return_value = mock_llm
    
    # Mock LLM responses
    mock_llm.chat.side_effect = [
        '{"target": "prices", "keywords": ["price", "cost"]}', 
    ]
    mock_llm.generate_text.side_effect = [
        '{"best_option_index": 0, "reason": "good fit"}', # Disambiguate
    ]
    
    task_id = "task-123"
    url = "http://example.com"
    intent = {"target": "prices", "keywords": ["price"]}
    inner_text = "Product A price is $10"
    html_content = "<html><body><div class='item'>Product A price is $10</div></body></html>"
    network = []
    duration = 1
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # Mock find_cached_parser to return empty (force generation)
    # Note: check_cached_parser is in workflows, so we need to mock db_utils there too or mock check_cached_parser
    mock_workflows_db_utils.find_cached_parser.return_value = []
    
    # Mock regex generation result
    # We need to patch where it is used: services.ai_worker.workflows.regex_generation
    with patch('services.ai_worker.workflows.regex_generation.iterative_regex_generation') as mock_gen:
        mock_gen.return_value = {
            "success": True,
            "final_pattern": r"price is (\$\d+)",
            "final_flags": "i"
        }
        
        process_content(
            task_id, url, intent, inner_text, html_content, network, duration, now_iso, now_iso
        )
        
        # Verification
        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args[1]
        assert "snippet" in call_kwargs
        assert call_kwargs["snippet"] 
        
        mock_db_utils.persist_extraction_result.assert_called_once()
        # record_new_parser is called in workflows, so it uses workflows.db_utils
        mock_workflows_db_utils.record_new_parser.assert_called_once()

def test_find_candidates():
    html = "<div>abc</div><div>def</div><div>abc again</div>"
    examples = ["abc"]
    candidates = find_text_in_raw_content(html, examples)
    assert len(candidates) == 1
