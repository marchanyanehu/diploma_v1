# Test Suite Quick Reference

## 🚀 Most Common Commands

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=services --cov=shared --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_repositories.py -v

# Run specific test
pytest tests/test_repositories.py::TestUserRepository::test_create_user_success -v

# Run tests matching pattern
pytest -k "test_auth" -v
```

## 📊 Coverage Commands

```bash
# Generate HTML coverage report
pytest --cov=services --cov=shared --cov-report=html

# View terminal report with missing lines
pytest --cov=services --cov=shared --cov-report=term-missing

# Fail if coverage below 70%
pytest --cov=services --cov=shared --cov-fail-under=70

# Coverage for specific module
pytest --cov=services.api --cov-report=term
```

## 🎯 Test Categories

```bash
# Unit tests (repositories, services)
pytest tests/test_repositories.py tests/test_services.py -v

# Integration tests
pytest tests/test_api_integration.py -v

# Contract tests
pytest tests/test_contracts_snapshots.py -v

# Edge cases
pytest tests/test_edge_cases.py -v

# Performance tests (slow)
pytest tests/test_performance.py -v

# Workflows
pytest tests/test_workflows_comprehensive.py -v
```

## 🐛 Debugging

```bash
# Show print statements
pytest -s

# Show local variables on failure
pytest -l

# Drop into debugger on failure
pytest --pdb

# Verbose output
pytest -v

# Very verbose (show test names)
pytest -vv
```

## ⚡ Performance

```bash
# Exclude slow tests
pytest -m "not slow"

# Run only slow tests
pytest -m slow

# Run tests in parallel (requires pytest-xdist)
pytest -n auto
```

## 🎨 Output Formats

```bash
# Concise output
pytest --tb=short

# Detailed traceback
pytest --tb=long

# No traceback (only test names)
pytest --tb=no

# Show slowest tests
pytest --durations=10
```

## 📝 Test File Quick Access

| Category | File | Command |
|----------|------|---------|
| Repositories | test_repositories.py | `pytest tests/test_repositories.py -v` |
| Services | test_services.py | `pytest tests/test_services.py -v` |
| API Integration | test_api_integration.py | `pytest tests/test_api_integration.py -v` |
| Error Handlers | test_error_handlers.py | `pytest tests/test_error_handlers.py -v` |
| Correlation | test_correlation.py | `pytest tests/test_correlation.py -v` |
| Workflows | test_workflows_comprehensive.py | `pytest tests/test_workflows_comprehensive.py -v` |
| Edge Cases | test_edge_cases.py | `pytest tests/test_edge_cases.py -v` |
| Performance | test_performance.py | `pytest tests/test_performance.py -v` |
| Contracts | test_contracts_snapshots.py | `pytest tests/test_contracts_snapshots.py -v` |

## 🔧 Troubleshooting

```bash
# Clean test artifacts
rm -rf .pytest_cache __pycache__ htmlcov .coverage

# Remove test database
rm test_debug.db

# Set PYTHONPATH (if import errors)
export PYTHONPATH="${PYTHONPATH}:$(pwd)"  # Linux/Mac
set PYTHONPATH=%PYTHONPATH%;%CD%  # Windows

# Check pytest version
pytest --version

# List all available fixtures
pytest --fixtures
```

## 📦 Requirements

```bash
# Install test dependencies
pip install -r requirements.txt

# Install with dev dependencies
pip install -r requirements.txt pytest pytest-cov pytest-asyncio
```

## 🎯 CI/CD Commands

```bash
# Run as in CI pipeline
pytest --cov=services --cov=shared --cov-report=xml --cov-fail-under=70 -v

# Generate JUnit XML report (for CI)
pytest --junitxml=test-results.xml

# Run with timeout
pytest --timeout=300
```

## 📈 Coverage Targets

| Component | Target | Command |
|-----------|--------|---------|
| Overall | 70%+ | `pytest --cov=services --cov=shared --cov-fail-under=70` |
| API Layer | 90%+ | `pytest --cov=services.api --cov-fail-under=90` |
| Services | 85%+ | `pytest --cov=services.api.services --cov-fail-under=85` |
| Repositories | 80%+ | `pytest --cov=services.api.repositories --cov-fail-under=80` |

## 🎨 Test Selection

```bash
# Run tests by keyword
pytest -k "repository" -v
pytest -k "integration" -v
pytest -k "auth" -v

# Run tests by marker
pytest -m slow -v
pytest -m "not slow" -v

# Run specific test class
pytest tests/test_repositories.py::TestUserRepository -v

# Run multiple files
pytest tests/test_repositories.py tests/test_services.py -v
```

## 📊 Reports

```bash
# HTML coverage report
pytest --cov=services --cov=shared --cov-report=html
# View: htmlcov/index.html

# XML coverage report (for CI)
pytest --cov=services --cov=shared --cov-report=xml

# Terminal report
pytest --cov=services --cov=shared --cov-report=term

# JSON report
pytest --cov=services --cov=shared --cov-report=json
```

## 🎓 Before Submitting

```bash
# Full test suite with coverage
pytest --cov=services --cov=shared --cov-report=html --cov-report=term -v

# Check coverage meets requirement
pytest --cov=services --cov=shared --cov-fail-under=70

# Generate final report
pytest --cov=services --cov=shared --cov-report=html --cov-report=xml --cov-fail-under=70 -v
```

## 💡 Pro Tips

1. **Run often**: `pytest` after every change
2. **Watch mode**: Use `pytest-watch` for auto-running tests
3. **Focus**: Use `-k` to run subset of tests during development
4. **Coverage**: Check coverage for new code immediately
5. **Verbose**: Use `-v` to see which tests are running
6. **Debug**: Use `--pdb` to debug failing tests interactively

## 🔗 Links

- [Full Testing Strategy](../docs/TESTING_STRATEGY.md)
- [Test Suite README](README.md)
- [pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)

---

**Quick Reference Version**: 1.0  
**Last Updated**: December 2024  
**Framework**: pytest 7.x
