
import pytest
from unittest.mock import MagicMock, patch
import json
from services.ai_worker.workflows import run_schema_extraction_with_cache, check_cached_parser

@patch('services.ai_worker.workflows.db_utils')
@patch('services.ai_worker.workflows.LLMClient')
def test_schema_caching_hit(mock_llm_cls, mock_db_utils):
    # Setup
    task_id = "task-schema-1"
    url = "http://example.com"
    schema_fields = ["title", "price"]
    inner_text = "Item 1 $10 Item 2 $20"
    html_content = "<ul><li><span class='t'>Item 1</span><span class='p'>$10</span></li><li><span class='t'>Item 2</span><span class='p'>$20</span></li></ul>"
    domain = "example.com"
    
    # Mock DB parser
    mock_parser = MagicMock()
    mock_parser.id = "parser-1"
    mock_parser.source_type = "SCHEMA"
    
    # Construct a valid SCHEMA regex
    schema_json = json.dumps({
        "schema_fields": ["title", "price"],
        "field_regexes": {
            "title": {"regex": "class='t'>([^<]+)</span>", "flags": "s"},
            "price": {"regex": "class='p'>([^<]+)</span>", "flags": "s"}
        }
    })
    mock_parser.generated_regex = f"(?s:SCHEMA:{schema_json})"
    
    mock_db_utils.find_cached_parser.return_value = [mock_parser]
    
    # Run
    extracted, used_cache = run_schema_extraction_with_cache(
        task_id, url, schema_fields, inner_text, html_content, mock_llm_cls, MagicMock(), domain
    )
    
    # Verify
    assert used_cache is True
    assert len(extracted) == 2
    assert extracted[0]["fields"]["title"] == "Item 1"
    assert extracted[0]["fields"]["price"] == "$10"
    assert extracted[1]["fields"]["title"] == "Item 2"
    assert extracted[1]["fields"]["price"] == "$20"
    
    # Ensure LLM was NOT called
    mock_llm_cls.chat.assert_not_called()

@patch('services.ai_worker.workflows.db_utils')
@patch('services.ai_worker.workflows.LLMClient')
def test_schema_caching_mismatch(mock_llm_cls, mock_db_utils):
    # Setup: Regexes match different counts
    task_id = "task-schema-2"
    url = "http://example.com"
    schema_fields = ["title", "price"]
    inner_text = "Item 1 $10 Item 2" # Missing price for item 2
    html_content = "<ul><li><span class='t'>Item 1</span><span class='p'>$10</span></li><li><span class='t'>Item 2</span></li></ul>"
    domain = "example.com"
    
    mock_parser = MagicMock()
    mock_parser.id = "parser-1"
    mock_parser.source_type = "SCHEMA"
    
    schema_json = json.dumps({
        "schema_fields": ["title", "price"],
        "field_regexes": {
            "title": {"regex": "class='t'>([^<]+)</span>", "flags": "s"},
            "price": {"regex": "class='p'>([^<]+)</span>", "flags": "s"}
        }
    })
    mock_parser.generated_regex = f"(?s:SCHEMA:{schema_json})"
    
    mock_db_utils.find_cached_parser.return_value = [mock_parser]
    
    # Mock LLM to return something so function finishes
    mock_llm = MagicMock()
    mock_llm.chat.return_value = '{"items": [{"title": "Item 1", "price": "$10"}]}'
    
    # Run
    extracted, used_cache = run_schema_extraction_with_cache(
        task_id, url, schema_fields, inner_text, html_content, mock_llm, MagicMock(), domain
    )
    
    # Verify
    assert used_cache is False # Should fall back to LLM because counts mismatch (2 titles, 1 price)
    assert len(extracted) == 1 # From LLM

@patch('services.ai_worker.workflows.db_utils')
def test_check_cached_parser_ignores_schema(mock_db_utils):
    # Setup
    domain = "example.com"
    keywords = ["price"]
    search_content = "Price: $10"
    
    mock_parser = MagicMock()
    mock_parser.id = "parser-schema"
    mock_parser.source_type = "SCHEMA"
    # SCHEMA regex that is valid regex syntax but won't match content
    mock_parser.generated_regex = "(?s:SCHEMA:{...})"
    
    mock_db_utils.find_cached_parser.return_value = [mock_parser]
    
    # Run
    result = check_cached_parser(MagicMock(), domain, keywords, search_content)
    
    # Verify
    assert result["matches"] == []
    assert result["used_parser"] is None
