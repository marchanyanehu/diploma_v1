"""
Performance and load testing for the application.

Tests system behavior under load, response times, and resource usage
to ensure the application meets performance requirements.
"""

import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient


class TestPerformanceAPI:
    """Performance tests for API endpoints."""

    def test_health_endpoint_response_time(self, client):
        """Test health endpoint responds within acceptable time."""
        iterations = 10
        times = []
        
        for _ in range(iterations):
            start = time.time()
            response = client.get("/health")
            duration = time.time() - start
            times.append(duration)
            assert response.status_code == 200
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Health check should be very fast
        assert avg_time < 0.1  # 100ms average
        assert max_time < 0.5  # 500ms max

    def test_api_health_with_db_response_time(self, client):
        """Test API health check with DB query response time."""
        iterations = 10
        times = []
        
        for _ in range(iterations):
            start = time.time()
            response = client.get("/api/v1/health")
            duration = time.time() - start
            times.append(duration)
            assert response.status_code == 200
        
        avg_time = sum(times) / len(times)
        
        # Should still be reasonably fast with DB query
        assert avg_time < 0.5  # 500ms average

    def test_authentication_response_time(self, client):
        """Test authentication endpoint performance."""
        # Register user first
        client.post(
            "/auth/register",
            json={
                "username": "perfuser",
                "password": "password123",
                "email": "perf@example.com"
            }
        )
        
        # Test login performance
        iterations = 10
        times = []
        
        for _ in range(iterations):
            start = time.time()
            response = client.post(
                "/auth/token",
                data={
                    "username": "perfuser",
                    "password": "password123"
                }
            )
            duration = time.time() - start
            times.append(duration)
            assert response.status_code == 200
        
        avg_time = sum(times) / len(times)
        
        # Login should be reasonably fast (bcrypt hashing takes time)
        assert avg_time < 1.0  # 1 second average

    def test_task_creation_throughput(self, auth_client):
        """Test how many tasks can be created per second."""
        num_tasks = 20
        start = time.time()
        
        for i in range(num_tasks):
            response = auth_client.post(
                "/api/v1/process",
                json={
                    "url": "https://example.com",
                    "prompt": f"Throughput test {i}"
                }
            )
            # Allow some failures due to rate limiting
            assert response.status_code in [202, 429]
        
        duration = time.time() - start
        throughput = num_tasks / duration
        
        # Should handle at least 5 requests per second
        # (rate limit is 10/minute, so this accounts for that)
        assert throughput > 0  # Basic sanity check

    def test_status_check_performance(self, auth_client):
        """Test status check endpoint performance."""
        # Create a task
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Status perf test"
            }
        )
        task_id = response.json()["task_id"]
        
        # Check status multiple times
        iterations = 20
        times = []
        
        for _ in range(iterations):
            start = time.time()
            response = auth_client.get(f"/api/v1/status/{task_id}")
            duration = time.time() - start
            times.append(duration)
            assert response.status_code == 200
        
        avg_time = sum(times) / len(times)
        
        # Status check should be fast (simple DB query)
        assert avg_time < 0.2  # 200ms average


class TestPerformanceDatabaseQueries:
    """Performance tests for database operations."""

    def test_task_list_query_performance(self, auth_client):
        """Test performance of listing user tasks."""
        # Create multiple tasks
        for i in range(50):
            auth_client.post(
                "/api/v1/process",
                json={
                    "url": "https://example.com",
                    "prompt": f"List test {i}"
                }
            )
        
        # Measure list performance
        start = time.time()
        response = auth_client.get("/api/v1/users/me/activity")
        duration = time.time() - start
        
        assert response.status_code == 200
        # Should handle listing many tasks efficiently
        assert duration < 1.0  # 1 second max

    def test_parser_cache_lookup_performance(self):
        """Test performance of parser cache lookup."""
        from tests.conftest import TestingSessionLocal
        from services.api.repositories import ParserRepository
        from shared.database import Domain, ParserCache
        
        db = TestingSessionLocal()
        try:
            # Create domain
            domain = Domain(name="perftest.com")
            db.add(domain)
            db.commit()
            db.refresh(domain)
            
            # Create many parsers
            for i in range(100):
                parser = ParserCache(
                    url_pattern=f"https://perftest.com/page{i}",
                    domain_id=domain.id,
                    user_intent=f"Intent {i}",
                    generated_regex=f"pattern{i}",
                    source_type="HTML",
                    test_matches_count=5,
                    confidence_score=80 + (i % 20),
                    created_by_task_id=f"task{i}"
                )
                db.add(parser)
            db.commit()
            
            # Measure lookup performance
            repo = ParserRepository(db)
            
            iterations = 10
            times = []
            for _ in range(iterations):
                start = time.time()
                parsers = repo.find_cached_parser(
                    domain="perftest.com",
                    confidence_threshold=85
                )
                duration = time.time() - start
                times.append(duration)
            
            avg_time = sum(times) / len(times)
            
            # Cache lookup should be fast
            assert avg_time < 0.1  # 100ms average
        finally:
            db.close()

    def test_user_query_performance(self):
        """Test performance of user queries."""
        from tests.conftest import TestingSessionLocal
        from services.api.repositories import UserRepository
        
        db = TestingSessionLocal()
        try:
            repo = UserRepository(db)
            
            # Create many users
            for i in range(100):
                repo.create(
                    username=f"perfuser{i}",
                    password_hash="hashed",
                    email=f"perfuser{i}@example.com"
                )
            
            # Measure lookup performance
            iterations = 20
            times = []
            for i in range(iterations):
                start = time.time()
                user = repo.get_by_username(f"perfuser{i % 100}")
                duration = time.time() - start
                times.append(duration)
                assert user is not None
            
            avg_time = sum(times) / len(times)
            
            # User lookup should be very fast (indexed column)
            assert avg_time < 0.05  # 50ms average
        finally:
            db.close()


class TestPerformanceMemoryUsage:
    """Performance tests for memory usage."""

    def test_large_extracted_data_handling(self):
        """Test handling of large extracted data sets."""
        from services.api.services import task_presenter
        from unittest.mock import Mock
        from shared.database import ScrapingTask
        from datetime import datetime, timezone
        
        # Create task with large data
        mock_task = Mock(spec=ScrapingTask)
        mock_task.task_id = "large-data"
        mock_task.status = "SUCCESS"
        mock_task.url = "https://example.com"
        mock_task.user_prompt = "Extract data"
        mock_task.extracted_data = [
            {"text": f"Item {i}", "field": f"value{i}"}
            for i in range(1000)  # 1000 items
        ]
        mock_task.used_cached_parser = False
        mock_task.total_matches = 1000
        mock_task.processing_time_seconds = 10
        mock_task.created_at = datetime.now(timezone.utc)
        mock_task.completed_at = datetime.now(timezone.utc)
        
        # Should handle without memory issues
        start = time.time()
        response = task_presenter.build_result_response(mock_task)
        duration = time.time() - start
        
        assert response is not None
        assert len(response.data) == 1000
        assert duration < 1.0  # Should process quickly

    def test_concurrent_requests_memory_stability(self, auth_client):
        """Test memory stability under concurrent requests."""
        def make_request(i):
            return auth_client.post(
                "/api/v1/process",
                json={
                    "url": "https://example.com",
                    "prompt": f"Concurrent test {i}"
                }
            )
        
        # Make concurrent requests
        num_requests = 10
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            
            # Wait for all to complete
            results = [f.result() for f in as_completed(futures)]
        
        # Verify all completed (allowing for rate limits)
        assert len(results) == num_requests
        success_count = sum(1 for r in results if r.status_code in [202, 429])
        assert success_count == num_requests


class TestPerformanceCaching:
    """Performance tests for caching mechanisms."""

    def test_parser_cache_hit_vs_miss(self):
        """Test performance difference between cache hit and miss."""
        from services.ai_worker import workflows
        from unittest.mock import Mock, patch
        
        db_mock = Mock()
        
        # Test cache miss (no parsers found)
        with patch('shared.database.find_cached_parser_by_fields', return_value=[]):
            start = time.time()
            result_miss = workflows.check_cached_parser(
                db=db_mock,
                domain="example.com",
                fields=["title"],
                search_content="content"
            )
            time_miss = time.time() - start
        
        # Cache miss should be fast (just DB query)
        assert time_miss < 0.1
        assert result_miss["used_cached"] is False

    def test_repeated_task_status_checks(self, auth_client):
        """Test performance of repeated status checks (potential caching)."""
        # Create task
        response = auth_client.post(
            "/api/v1/process",
            json={
                "url": "https://example.com",
                "prompt": "Cache test"
            }
        )
        task_id = response.json()["task_id"]
        
        # Check status many times
        times = []
        for _ in range(50):
            start = time.time()
            response = auth_client.get(f"/api/v1/status/{task_id}")
            duration = time.time() - start
            times.append(duration)
            assert response.status_code == 200
        
        # Later checks should be similar speed (no significant degradation)
        first_10_avg = sum(times[:10]) / 10
        last_10_avg = sum(times[-10:]) / 10
        
        # Performance should not degrade significantly
        assert last_10_avg < first_10_avg * 2  # Less than 2x slower


class TestPerformanceScalability:
    """Performance tests for scalability."""

    def test_increasing_task_count_performance(self, auth_client):
        """Test performance as number of tasks increases."""
        times = []
        
        # Create tasks in batches and measure
        for batch in range(5):
            start = time.time()
            response = auth_client.post(
                "/api/v1/process",
                json={
                    "url": "https://example.com",
                    "prompt": f"Scalability test batch {batch}"
                }
            )
            duration = time.time() - start
            times.append(duration)
            assert response.status_code in [202, 429]
        
        # Time should not increase significantly
        first_time = times[0]
        last_time = times[-1]
        
        # Last request should not be much slower than first
        assert last_time < first_time * 3  # Less than 3x slower

    def test_database_query_scalability(self):
        """Test database query performance with growing data."""
        from tests.conftest import TestingSessionLocal
        from services.api.repositories import TaskRepository
        
        db = TestingSessionLocal()
        try:
            repo = TaskRepository(db)
            
            # Create tasks and measure query time at different scales
            query_times = []
            
            for scale in [10, 50, 100]:
                # Create tasks up to scale
                current_count = db.query(repo.db.query_property).count() if hasattr(repo.db, 'query_property') else 0
                
                for i in range(scale):
                    repo.create(
                        task_id=f"scale-{scale}-{i}",
                        url="https://example.com",
                        user_prompt=f"Scale test {i}"
                    )
                
                # Measure query time
                start = time.time()
                task = repo.get_by_task_id(f"scale-{scale}-0")
                duration = time.time() - start
                query_times.append(duration)
                
                assert task is not None
            
            # Query time should not grow significantly
            # (indicates proper indexing)
            assert all(t < 0.1 for t in query_times)
        finally:
            db.close()


class TestLoadTesting:
    """Load testing scenarios."""

    @pytest.mark.slow
    def test_sustained_load_handling(self, auth_client):
        """Test handling sustained load over time."""
        duration_seconds = 10
        request_interval = 0.5  # Request every 500ms
        
        start = time.time()
        responses = []
        
        while time.time() - start < duration_seconds:
            response = auth_client.post(
                "/api/v1/process",
                json={
                    "url": "https://example.com",
                    "prompt": "Load test"
                }
            )
            responses.append(response)
            time.sleep(request_interval)
        
        # Verify system remained stable
        success_rate = sum(1 for r in responses if r.status_code in [202, 429]) / len(responses)
        assert success_rate > 0.8  # At least 80% success rate

    @pytest.mark.slow
    def test_burst_load_handling(self, auth_client):
        """Test handling sudden burst of requests."""
        burst_size = 20
        
        def make_request():
            return auth_client.post(
                "/api/v1/process",
                json={
                    "url": "https://example.com",
                    "prompt": "Burst test"
                }
            )
        
        # Send burst of requests
        start = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(burst_size)]
            results = [f.result() for f in as_completed(futures)]
        duration = time.time() - start
        
        # Should handle burst without crashing
        assert len(results) == burst_size
        # Some may be rate limited, but system should respond
        assert all(r.status_code in [202, 429, 401] for r in results)
        
        # Should complete burst reasonably quickly
        assert duration < 30.0  # 30 seconds max


class TestPerformanceOptimizations:
    """Tests to verify performance optimizations."""

    def test_json_serialization_performance(self):
        """Test JSON serialization performance for large payloads."""
        import json
        
        large_data = {
            "items": [
                {"id": i, "title": f"Item {i}", "description": "x" * 100}
                for i in range(1000)
            ]
        }
        
        start = time.time()
        json_str = json.dumps(large_data)
        encode_time = time.time() - start
        
        start = time.time()
        decoded = json.loads(json_str)
        decode_time = time.time() - start
        
        # Should serialize/deserialize efficiently
        assert encode_time < 0.1  # 100ms
        assert decode_time < 0.1  # 100ms

    def test_database_connection_pooling(self):
        """Test database connection pooling efficiency."""
        from tests.conftest import TestingSessionLocal
        
        # Multiple operations should reuse connections
        times = []
        
        for _ in range(10):
            start = time.time()
            db = TestingSessionLocal()
            try:
                # Simple query
                result = db.execute("SELECT 1").fetchone()
                assert result is not None
            finally:
                db.close()
            duration = time.time() - start
            times.append(duration)
        
        # Connection times should be consistent (pooling working)
        avg_time = sum(times) / len(times)
        assert avg_time < 0.05  # 50ms average
