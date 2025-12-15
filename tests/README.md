# Test Suite Documentation

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=services --cov=shared --cov-report=html --cov-report=term

# Run specific test category
pytest tests/test_api_integration.py -v

# Run only fast tests (exclude slow performance tests)
pytest -m "not slow"
```

## Test Files Overview

### Core API Tests
- **test_api_basic.py**: Basic API endpoint tests (health, root, OpenAPI)
- **test_api_contract.py**: API contract validation tests
- **test_api_process.py**: Process endpoint functionality
- **test_api_integration.py**: End-to-end integration workflows
- **test_auth.py**: Authentication and authorization tests

### Repository & Service Layer Tests
- **test_repositories.py**: Unit tests for data access layer
  - UserRepository: User CRUD operations
  - TaskRepository: Task management
  - ScheduleRepository: Scheduled job operations
  - ParserRepository: Parser cache queries

- **test_services.py**: Unit tests for business logic layer
  - TaskService: Task orchestration
  - AuthService: Authentication logic
  - task_presenter: Response formatting

### Infrastructure Tests
- **test_error_handlers.py**: Error handling and middleware
  - 404/500 error handlers
  - CORS middleware
  - Correlation ID propagation
  - Rate limiting
  - Input validation

- **test_correlation.py**: Correlation ID utilities
  - ID generation and binding
  - Header extraction
  - Context management

### AI Workflow Tests
- **test_workflows_comprehensive.py**: AI processing workflows
  - Cache hit/miss scenarios
  - Schema extraction
  - Field extraction
  - Regex generation and caching

- **test_intent_extraction.py**: Intent analysis
- **test_llm_client.py**: LLM client interactions
- **test_regex_generation.py**: Regex pattern generation
- **test_input_sanitization.py**: Input validation and sanitization

### Advanced Testing
- **test_edge_cases.py**: Boundary conditions and edge cases
  - Unicode handling
  - Special characters
  - Null/empty values
  - Concurrent operations
  - Error recovery

- **test_performance.py**: Performance and load testing
  - Response time benchmarks
  - Throughput testing
  - Database query performance
  - Memory usage
  - Scalability tests

- **test_contracts_snapshots.py**: Contract and snapshot testing
  - API contract validation
  - Response structure verification
  - Backwards compatibility
  - Schema stability

### Utility Tests
- **test_scheduler.py**: Scheduled job execution
- **test_schema_caching.py**: Schema-based caching
- **test_utils_links.py**: Utility functions
- **test_worker_persistence.py**: Worker task persistence

## Test Configuration

### conftest.py

Shared fixtures and configuration:

- **client**: Basic FastAPI test client
- **auth_client**: Authenticated test client with valid JWT token
- **TestingSessionLocal**: In-memory SQLite database session
- **suppress_litellm_logging_errors**: Cleanup fixture

### Database Setup

Tests use SQLite in-memory database:
- Fresh database for each test session
- Auto-created tables from SQLAlchemy models
- Automatic cleanup after tests

## Running Specific Test Types

### Unit Tests Only

```bash
# Repository tests
pytest tests/test_repositories.py -v

# Service tests
pytest tests/test_services.py -v

# Workflow tests
pytest tests/test_workflows_comprehensive.py -v
```

### Integration Tests

```bash
pytest tests/test_api_integration.py -v
pytest tests/test_auth.py -v
```

### Performance Tests

```bash
# Warning: These may take several minutes
pytest tests/test_performance.py -v

# Run with slow marker
pytest -m slow -v
```

### Contract Tests

```bash
pytest tests/test_contracts_snapshots.py -v
```

## Coverage Reports

### Generate HTML Report

```bash
pytest --cov=services --cov=shared --cov-report=html
```

View report: `htmlcov/index.html`

### Terminal Report

```bash
pytest --cov=services --cov=shared --cov-report=term-missing
```

Shows line-by-line coverage with missing lines highlighted.

### Coverage by Module

```bash
# API coverage only
pytest --cov=services.api --cov-report=term

# AI worker coverage only
pytest --cov=services.ai_worker --cov-report=term

# Shared utilities coverage
pytest --cov=shared --cov-report=term
```

## Test Markers

### Available Markers

- **slow**: Tests that take significant time (performance/load tests)

### Usage

```bash
# Run only slow tests
pytest -m slow

# Exclude slow tests
pytest -m "not slow"
```

## Debugging Tests

### Verbose Output

```bash
# Show test names and results
pytest -v

# Show print statements
pytest -s

# Show local variables on failure
pytest -l
```

### Run Single Test

```bash
# Run specific test function
pytest tests/test_api_basic.py::test_root_endpoint -v

# Run test class
pytest tests/test_repositories.py::TestUserRepository -v
```

### Debug Mode

```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger at start
pytest --trace
```

## Common Scenarios

### Testing New Feature

1. Write unit tests first
2. Implement feature
3. Add integration tests
4. Verify coverage meets threshold

```bash
# Run tests for specific module
pytest tests/test_repositories.py -v

# Check coverage
pytest --cov=services.api.repositories --cov-report=term-missing
```

### Before Committing

```bash
# Run full test suite with coverage
pytest --cov=services --cov=shared --cov-report=term --cov-fail-under=70

# Run linter
flake8 services/ shared/

# Run type checker (if using mypy)
mypy services/ shared/
```

### CI/CD Pipeline

```bash
# Run tests as in CI
pytest --cov=services --cov=shared --cov-report=xml --cov-fail-under=70 -v
```

## Test Data

### Sample Users

Tests create temporary users:
- Username: `testuser`, `integrationuser`, etc.
- Password: `testpass`, `password123`, etc.
- Email: `test@example.com`, etc.

All test data is cleaned up after test session.

### Sample Tasks

Tests create tasks with:
- URL: `https://example.com`
- Prompts: Various test prompts
- Unique task IDs (UUIDs)

## Troubleshooting

### Tests Fail with "Database Locked"

SQLite in-memory DB is single-threaded. Ensure tests aren't using threading:

```bash
# Run tests sequentially
pytest --workers 1
```

### Import Errors

Add project root to PYTHONPATH:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

Or on Windows:

```cmd
set PYTHONPATH=%PYTHONPATH%;%CD%
pytest
```

### Fixture Not Found

Check that `conftest.py` is in the tests directory and fixtures are defined there.

### Rate Limit Errors

Some tests may hit rate limits. The test environment uses in-memory rate limiting, but you may need to run tests with delays:

```bash
pytest --timeout=10  # Add timeout
```

### Database Migration Issues

If database schema changes:

```bash
# Remove old test database
rm test_debug.db

# Re-run tests
pytest
```

## Writing New Tests

### Unit Test Template

```python
def test_my_function():
    """Test my_function does X."""
    # Arrange
    input_data = "test"
    
    # Act
    result = my_function(input_data)
    
    # Assert
    assert result == expected_value
```

### Integration Test Template

```python
def test_my_api_endpoint(auth_client):
    """Test API endpoint X."""
    # Arrange
    payload = {"key": "value"}
    
    # Act
    response = auth_client.post("/api/v1/endpoint", json=payload)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "expected_field" in data
```

### Using Mocks

```python
from unittest.mock import Mock, patch

def test_with_mock():
    """Test function with mocked dependency."""
    # Create mock
    mock_service = Mock()
    mock_service.method.return_value = "mocked result"
    
    # Use mock
    result = function_using_service(mock_service)
    
    # Verify
    assert result == "mocked result"
    mock_service.method.assert_called_once()
```

## Code Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| Overall | 70% | 75%+ |
| API Layer | 90% | 92% |
| Service Layer | 85% | 87% |
| Repository Layer | 80% | 85% |
| Workflows | 75% | 78% |
| Utilities | 80% | 82% |

## Test Statistics

- **Total Tests**: 200+ comprehensive tests
- **Average Execution Time**: ~30 seconds (full suite)
- **Fast Tests**: <100ms each
- **Integration Tests**: 100-500ms each
- **Performance Tests**: 1-10s each

## Continuous Improvement

### Adding Tests Checklist

- [ ] Test covers new functionality
- [ ] Test follows FIRST principles
- [ ] Test has descriptive name
- [ ] Test uses proper fixtures
- [ ] Test includes arrange-act-assert
- [ ] Test is independent
- [ ] Coverage increases or maintains
- [ ] Test passes in CI

### Refactoring Tests

- Keep tests DRY (Don't Repeat Yourself)
- Extract common setup to fixtures
- Use parameterized tests for similar cases
- Maintain test independence
- Update tests when refactoring code

## Resources

- [Detailed Testing Strategy](../docs/TESTING_STRATEGY.md)
- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Test Requirements](../reference_docs/auto_tests/requirements_tests.md)

## Support

For questions or issues with tests:
1. Check this README
2. Review test examples
3. Check CI logs for failures
4. Review error messages carefully
5. Consult testing strategy document

---

**Last Updated**: December 2024  
**Maintainer**: Yan Marchan  
**Test Framework**: pytest 7.x  
**Coverage Tool**: pytest-cov / coverage.py
