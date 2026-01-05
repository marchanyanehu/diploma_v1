
import pytest
from unittest.mock import MagicMock, patch
import json
from services.ai_worker.workflows import run_schema_extraction, check_cached_parser

@patch('services.ai_worker.workflows.db_utils')
@patch('services.ai_worker.workflows.LLMClient')
def test_field_based_cache_hit(mock_llm_cls, mock_db_utils):
    """Test that field-based caching finds and reuses cached regex."""
    # Setup
    db = MagicMock()
    domain = "example.com"
    fields = ["title", "price"]
    search_content = "## Product 1\n• Title: Item A\n• Price: $10\n\n## Product 2\n• Title: Item B\n• Price: $20"
    
    # Mock cached parser
    mock_parser = MagicMock()
    mock_parser.id = 1
    mock_parser.generated_regex = r"(?s)Title:\s*([^\n]+)\n.*?Price:\s*([^\n]+)"
    mock_parser.source_type = "SEMANTIC"    
    mock_db_utils.find_cached_parser_by_fields.return_value = [mock_parser]
    
    # Mock successful regex matches
    with patch('services.ai_worker.workflows.apply_regex_matches') as mock_apply:
        mock_apply.return_value = [
            {"fields": {"title": "Item A", "price": "$10"}, "text": "Item A | $10"},
            {"fields": {"title": "Item B", "price": "$20"}, "text": "Item B | $20"}
        ]
        
        # Run
        result = check_cached_parser(db, domain, fields, search_content)
        
        # Verify
        assert result["used_cached"] is True
        assert len(result["matches"]) == 2
        assert result["used_parser"] == mock_parser
        
        # Verify cache lookup was called with correct params
        mock_db_utils.find_cached_parser_by_fields.assert_called_once_with(
            db, domain, fields, "SEMANTIC", url_pattern=None
        )
        mock_db_utils.update_parser_usage.assert_called_once()

@patch('services.ai_worker.workflows.db_utils')
@patch('services.ai_worker.workflows.LLMClient')
def test_schema_caching_mismatch(mock_llm_cls, mock_db_utils):
    # Setup: Regexes match different counts
    task_id = "task-schema-2"


@patch('services.ai_worker.workflows.db_utils')
def test_field_based_cache_miss(mock_db_utils):
    """Test that cache miss is handled correctly."""
    # Setup
    db = MagicMock()
    domain = "example.com"
    fields = ["title", "price"]
    search_content = "## Product 1\n• Title: Item A\n• Price: $10"
    
    # No cached parsers found
    mock_db_utils.find_cached_parser_by_fields.return_value = []
    
    # Run
    result = check_cached_parser(db, domain, fields, search_content)
    
    # Verify
    assert result["used_cached"] is False
    assert result["matches"] == []
    assert result["used_parser"] is None


@patch('services.ai_worker.workflows.db_utils')
def test_field_based_cache_invalidation(mock_db_utils):
    """Test that invalid cached parser gets invalidated."""
    # Setup
    db = MagicMock()
    domain = "example.com"
    fields = ["title", "price"]
    search_content = "## Product 1\n• Title: Item A\n• Price: $10"
    
    # Mock cached parser that produces invalid matches
    mock_parser = MagicMock()
    mock_parser.id = 1
    mock_parser.generated_regex = r"(?s)INVALID_PATTERN"
    mock_parser.source_type = "SEMANTIC"    
    mock_db_utils.find_cached_parser_by_fields.return_value = [mock_parser]
    
    # Mock failed regex matches (no matches or missing fields)
    with patch('services.ai_worker.workflows.apply_regex_matches') as mock_apply:
        mock_apply.return_value = []  # No matches
        
        # Run
        result = check_cached_parser(db, domain, fields, search_content)
        
        # Verify cache miss and invalidation
        assert result["used_cached"] is False
        assert result["matches"] == []
        mock_db_utils.invalidate_parser.assert_called_once_with(db, mock_parser.id)
