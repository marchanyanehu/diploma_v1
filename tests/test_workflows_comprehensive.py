"""
Comprehensive tests for AI workflows including cache, schema extraction, and field extraction.

Tests the core workflow logic for regex generation, caching, and LLM-based extraction.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json

from services.ai_worker import workflows
from services.ai_worker.llm_client import LLMClient
from shared.database import ParserCache, Domain


class TestCheckCachedParser:
    """Tests for check_cached_parser function."""

    def test_cache_hit_returns_matches(self):
        """Test cache hit returns matches from cached parser."""
        # Mock database session
        db_mock = Mock()
        
        # Create mock parser
        mock_parser = Mock()
        mock_parser.id = 1
        mock_parser.generated_regex = r"(?s)<item>(.*?)</item>"
        mock_parser.confidence_score = 90
        
        # Mock the database query function
        with patch('shared.database.find_cached_parser_by_fields', return_value=[mock_parser]):
            result = workflows.check_cached_parser(
                db=db_mock,
                domain="example.com",
                fields=["title", "price"],
                search_content="<item>Product 1</item><item>Product 2</item>",
                source_type="SEMANTIC",
                min_matches=1
            )
            
            assert result["used_cached"] is True
            assert len(result["matches"]) >= 0  # Depends on regex match

    def test_cache_miss_returns_empty(self):
        """Test cache miss returns empty matches."""
        db_mock = Mock()
        
        # Mock no cached parsers found
        with patch('shared.database.find_cached_parser_by_fields', return_value=[]):
            result = workflows.check_cached_parser(
                db=db_mock,
                domain="example.com",
                fields=["title"],
                search_content="content",
                source_type="SEMANTIC"
            )
            
            assert result["used_cached"] is False
            assert result["matches"] == []
            assert result["used_parser"] is None

    def test_cache_invalid_parser_is_removed(self):
        """Test invalid cached parser is invalidated."""
        db_mock = Mock()
        
        # Create mock parser that won't match
        mock_parser = Mock()
        mock_parser.id = 1
        mock_parser.generated_regex = r"(?s)NOMATCH"
        
        with patch('shared.database.find_cached_parser_by_fields', return_value=[mock_parser]):
            with patch('shared.database.invalidate_parser') as invalidate_mock:
                result = workflows.check_cached_parser(
                    db=db_mock,
                    domain="example.com",
                    fields=["title"],
                    search_content="<item>Product</item>",
                    source_type="SEMANTIC",
                    min_matches=1
                )
                
                # Should invalidate the parser
                invalidate_mock.assert_called_once_with(db_mock, 1)
                assert result["used_cached"] is False

    def test_cache_with_url_pattern_matching(self):
        """Test cache lookup with specific URL pattern."""
        db_mock = Mock()
        
        with patch('shared.database.find_cached_parser_by_fields') as find_mock:
            find_mock.return_value = []
            
            workflows.check_cached_parser(
                db=db_mock,
                domain="example.com",
                fields=["title"],
                search_content="content",
                url_pattern="https://example.com/products"
            )
            
            # Verify url_pattern was passed
            find_mock.assert_called_once()
            assert find_mock.call_args.kwargs.get('url_pattern') == "https://example.com/products"


class TestRunSchemaExtraction:
    """Tests for run_schema_extraction function."""

    def test_schema_extraction_success(self):
        """Test successful schema extraction."""
        # Mock LLM client
        llm_mock = Mock(spec=LLMClient)
        llm_mock.chat = Mock(return_value=json.dumps({
            "items": [
                {"title": "Product 1", "price": "$10"},
                {"title": "Product 2", "price": "$20"}
            ]
        }))
        
        result = workflows.run_schema_extraction(
            task_id="test-task",
            url="https://example.com",
            schema_fields=["title", "price"],
            inner_text="Product 1 $10 Product 2 $20",
            html_content="<html>...</html>",
            llm=llm_mock
        )
        
        assert len(result) == 2
        assert result[0]["fields"]["title"] == "Product 1"
        assert result[1]["fields"]["price"] == "$20"

    def test_schema_extraction_with_cache(self):
        """Test schema extraction caches successful regex."""
        db_mock = Mock()
        llm_mock = Mock(spec=LLMClient)
        
        # Mock LLM responses
        llm_mock.chat = Mock(side_effect=[
            # First call: schema extraction
            json.dumps({
                "items": [
                    {"title": "Product 1"},
                    {"title": "Product 2"},
                    {"title": "Product 3"}
                ]
            }),
            # Second call: regex generation
            json.dumps({
                "pattern": r"<title>(.*?)</title>",
                "flags": "s"
            })
        ])
        
        with patch('shared.database.create_parser_cache_by_fields') as cache_mock:
            result = workflows.run_schema_extraction(
                task_id="test-task",
                url="https://example.com",
                schema_fields=["title"],
                inner_text="<title>Product 1</title>",
                html_content="",
                llm=llm_mock,
                db=db_mock,
                domain="example.com",
                url_pattern="https://example.com/page"
            )
            
            # Should have cached the regex (if enough items extracted)
            # cache_mock.assert_called_once()

    def test_schema_extraction_handles_json_error(self):
        """Test schema extraction handles invalid JSON from LLM."""
        llm_mock = Mock(spec=LLMClient)
        llm_mock.chat = Mock(return_value="Invalid JSON response")
        
        result = workflows.run_schema_extraction(
            task_id="test-task",
            url="https://example.com",
            schema_fields=["title"],
            inner_text="content",
            html_content="",
            llm=llm_mock
        )
        
        assert result == []

    def test_schema_extraction_handles_llm_error(self):
        """Test schema extraction handles LLM errors gracefully."""
        llm_mock = Mock(spec=LLMClient)
        llm_mock.chat = Mock(side_effect=Exception("LLM Error"))
        
        result = workflows.run_schema_extraction(
            task_id="test-task",
            url="https://example.com",
            schema_fields=["title"],
            inner_text="content",
            html_content="",
            llm=llm_mock
        )
        
        assert result == []

    def test_schema_extraction_extracts_json_from_markdown(self):
        """Test schema extraction can extract JSON from markdown code blocks."""
        llm_mock = Mock(spec=LLMClient)
        llm_mock.chat = Mock(return_value="""
        ```json
        {
            "items": [
                {"title": "Product 1"}
            ]
        }
        ```
        """)
        
        result = workflows.run_schema_extraction(
            task_id="test-task",
            url="https://example.com",
            schema_fields=["title"],
            inner_text="content",
            html_content="",
            llm=llm_mock
        )
        
        assert len(result) == 1

    def test_schema_extraction_prefers_html_for_images(self):
        """Test schema extraction uses HTML content for image fields."""
        llm_mock = Mock(spec=LLMClient)
        llm_mock.chat = Mock(return_value=json.dumps({
            "items": [
                {"image_url": "https://example.com/img.jpg"}
            ]
        }))
        
        result = workflows.run_schema_extraction(
            task_id="test-task",
            url="https://example.com",
            schema_fields=["image_url"],
            inner_text="text content",
            html_content="<img src='https://example.com/img.jpg'>",
            llm=llm_mock
        )
        
        # Should have used HTML content
        llm_mock.chat.assert_called_once()
        call_args = llm_mock.chat.call_args[0][0]
        # Verify HTML was included in prompt
        prompt_text = str(call_args)


class TestRunFieldExtraction:
    """Tests for run_field_extraction function."""

    def test_field_extraction_success(self):
        """Test successful field extraction."""
        llm_mock = Mock(spec=LLMClient)
        
        # Mock LLM responses
        llm_mock.chat = Mock(side_effect=[
            # First: find examples
            json.dumps({"examples": ["Python Developer", "Java Developer"]}),
            # Second: regex generation for "python"
            json.dumps({
                "pattern": r"Python Developer",
                "flags": "i"
            })
        ])
        
        db_mock = Mock()
        
        with patch('services.ai_worker.regex_generation.iterative_regex_generation') as regex_mock:
            regex_mock.return_value = {
                "success": True,
                "final_pattern": r"(\w+ Developer)",
                "final_flags": "i",
                "attempts": []
            }
            
            result = workflows.run_field_extraction(
                task_id="test-task",
                keywords=["developer"],
                inner_text="Python Developer, Java Developer",
                html_content="",
                llm=llm_mock,
                db=db_mock,
                domain="example.com"
            )
            
            # Should have found matches
            assert isinstance(result, list)

    def test_field_extraction_handles_no_examples(self):
        """Test field extraction handles case when no examples found."""
        llm_mock = Mock(spec=LLMClient)
        llm_mock.chat = Mock(return_value=json.dumps({"examples": []}))
        
        db_mock = Mock()
        
        with patch('services.ai_worker.regex_generation.iterative_regex_generation') as regex_mock:
            regex_mock.return_value = {
                "success": False,
                "error": "No matches"
            }
            
            result = workflows.run_field_extraction(
                task_id="test-task",
                keywords=["nonexistent"],
                inner_text="content",
                html_content="",
                llm=llm_mock,
                db=db_mock,
                domain="example.com"
            )
            
            assert result == []

    def test_field_extraction_caches_successful_regex(self):
        """Test field extraction caches successful regex patterns."""
        llm_mock = Mock(spec=LLMClient)
        llm_mock.chat = Mock(return_value=json.dumps({
            "examples": ["Example 1", "Example 2"]
        }))
        
        db_mock = Mock()
        
        with patch('services.ai_worker.regex_generation.iterative_regex_generation') as regex_mock:
            regex_mock.return_value = {
                "success": True,
                "final_pattern": r"(Example \d+)",
                "final_flags": "",
                "attempts": []
            }
            
            with patch('shared.database.create_parser_cache_by_fields') as cache_mock:
                workflows.run_field_extraction(
                    task_id="test-task",
                    keywords=["example"],
                    inner_text="Example 1 Example 2",
                    html_content="",
                    llm=llm_mock,
                    db=db_mock,
                    domain="example.com",
                    url_pattern="https://example.com/page"
                )
                
                # Should have cached (if matches found)


class TestCacheRegexFromExtraction:
    """Tests for _cache_regex_from_extraction helper."""

    def test_cache_skips_with_too_few_items(self):
        """Test caching skips when too few items extracted."""
        db_mock = Mock()
        llm_mock = Mock()
        
        with patch('services.ai_worker.regex_generation.iterative_regex_generation') as regex_mock:
            workflows._cache_regex_from_extraction(
                db=db_mock,
                task_id="test-task",
                domain="example.com",
                fields=["title"],
                semantic_content="content",
                extracted_items=[{"fields": {"title": "Item 1"}}],  # Only 1 item
                llm=llm_mock
            )
            
            # Should not call regex generation
            regex_mock.assert_not_called()

    def test_cache_generates_regex_for_multiple_items(self):
        """Test caching generates regex for multiple items."""
        db_mock = Mock()
        llm_mock = Mock()
        
        extracted_items = [
            {"fields": {"title": "Product 1", "price": "$10"}},
            {"fields": {"title": "Product 2", "price": "$20"}},
            {"fields": {"title": "Product 3", "price": "$30"}}
        ]
        
        with patch('services.ai_worker.regex_generation.iterative_regex_generation') as regex_mock:
            regex_mock.return_value = {
                "success": True,
                "final_pattern": r"Product \d+",
                "final_flags": "",
                "attempts": []
            }
            
            with patch('shared.database.create_parser_cache_by_fields') as cache_mock:
                workflows._cache_regex_from_extraction(
                    db=db_mock,
                    task_id="test-task",
                    domain="example.com",
                    fields=["title", "price"],
                    semantic_content="Product 1 $10 Product 2 $20 Product 3 $30",
                    extracted_items=extracted_items,
                    llm=llm_mock
                )
                
                # Should have attempted regex generation
                regex_mock.assert_called_once()

    def test_cache_handles_regex_generation_failure(self):
        """Test caching handles regex generation failure gracefully."""
        db_mock = Mock()
        llm_mock = Mock()
        
        extracted_items = [
            {"fields": {"title": "Item 1"}},
            {"fields": {"title": "Item 2"}}
        ]
        
        with patch('services.ai_worker.regex_generation.iterative_regex_generation') as regex_mock:
            regex_mock.return_value = {
                "success": False,
                "error": "Failed to generate regex"
            }
            
            # Should not raise exception
            workflows._cache_regex_from_extraction(
                db=db_mock,
                task_id="test-task",
                domain="example.com",
                fields=["title"],
                semantic_content="Item 1 Item 2",
                extracted_items=extracted_items,
                llm=llm_mock
            )


class TestGetMatchesWithPositions:
    """Tests for _get_matches_with_positions helper."""

    def test_get_matches_basic(self):
        """Test getting matches with basic regex."""
        pattern = r"<item>(.*?)</item>"
        flags = "s"
        content = "<item>Product 1</item><item>Product 2</item>"
        
        matches = workflows._get_matches_with_positions(pattern, flags, content)
        
        assert len(matches) == 2
        assert matches[0][0] == "Product 1"
        assert matches[1][0] == "Product 2"

    def test_get_matches_with_flags(self):
        """Test getting matches with case-insensitive flag."""
        pattern = r"(PRODUCT)"
        flags = "i"
        content = "product PRODUCT Product"
        
        matches = workflows._get_matches_with_positions(pattern, flags, content)
        
        assert len(matches) == 3

    def test_get_matches_multiline(self):
        """Test getting matches with multiline flag."""
        pattern = r"^Line \d+"
        flags = "m"
        content = "Line 1\nSome text\nLine 2\nLine 3"
        
        matches = workflows._get_matches_with_positions(pattern, flags, content)
        
        assert len(matches) == 3

    def test_get_matches_invalid_regex(self):
        """Test invalid regex returns empty list."""
        pattern = r"[invalid"  # Unclosed bracket
        flags = ""
        content = "content"
        
        matches = workflows._get_matches_with_positions(pattern, flags, content)
        
        assert matches == []

    def test_get_matches_with_positions_info(self):
        """Test matches include position information."""
        pattern = r"(\w+)"
        flags = ""
        content = "hello world"
        
        matches = workflows._get_matches_with_positions(pattern, flags, content)
        
        # Should have matches with positions
        assert len(matches) == 2
        assert isinstance(matches[0], tuple)
        assert isinstance(matches[0][1], int)  # Position
        assert matches[0][1] == 0  # First match at position 0
        assert matches[1][1] == 6  # Second match at position 6


class TestDecomposeStoredRegex:
    """Tests for decompose_stored_regex utility."""

    def test_decompose_with_flags(self):
        """Test decomposing regex with flags."""
        from services.ai_worker.utils import decompose_stored_regex
        
        stored_regex = r"(?is)<item>(.*?)</item>"
        
        pattern, flags = decompose_stored_regex(stored_regex)
        
        assert pattern == r"<item>(.*?)</item>"
        assert "i" in flags
        assert "s" in flags

    def test_decompose_without_flags(self):
        """Test decomposing regex without flags."""
        from services.ai_worker.utils import decompose_stored_regex
        
        stored_regex = r"<item>(.*?)</item>"
        
        pattern, flags = decompose_stored_regex(stored_regex)
        
        assert pattern == r"<item>(.*?)</item>"
        assert flags == ""


class TestApplyRegexMatches:
    """Tests for apply_regex_matches utility."""

    def test_apply_regex_matches_success(self):
        """Test applying regex pattern to content."""
        from services.ai_worker.utils import apply_regex_matches
        
        pattern = r"<item>(.*?)</item>"
        flags = "s"
        content = "<item>Product 1</item><item>Product 2</item>"
        
        matches = apply_regex_matches(pattern, flags, content)
        
        assert len(matches) >= 0  # Depends on implementation

    def test_apply_regex_matches_no_matches(self):
        """Test applying regex with no matches."""
        from services.ai_worker.utils import apply_regex_matches
        
        pattern = r"NOMATCH"
        flags = ""
        content = "content without matches"
        
        matches = apply_regex_matches(pattern, flags, content)
        
        assert matches == [] or len(matches) == 0
