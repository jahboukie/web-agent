"""
E2E Tests: Chaos Engineering
Failure scenario testing including database failures, queue saturation, and multi-cloud failover
"""

import pytest
import asyncio
import time
import psutil
import docker
from typing import Dict, Any, List
from datetime import datetime, timedelta
import json
import subprocess
import threading
from contextlib import asynccontextmanager
from unittest.mock import patch, MagicMock

from app.core.config import settings
from app.db.session import get_async_session, check_database_connection
from app.services.task_service import TaskService
from app.services.web_parser import web_parser_service


class ChaosScenario:
    """Base class for chaos engineering scenarios."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.active = False
        self.start_time = None
        self.end_time = None
    
    async def start(self):
        """Start the chaos scenario."""
        self.active = True
        self.start_time = datetime.utcnow()
    
    async def stop(self):
        """Stop the chaos scenario."""
        self.active = False
        self.end_time = datetime.utcnow()
    
    @property
    def duration(self):
        """Get scenario duration."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0


class DatabaseFailureScenario(ChaosScenario):
    """Simulate database connection failures."""
    
    def __init__(self):
        super().__init__("database_failure", "Simulate database disconnection and recovery")
        self.docker_client = None
        self.postgres_container = None
    
    async def start(self):
        """Stop PostgreSQL container to simulate database failure."""
        await super().start()
        
        try:
            self.docker_client = docker.from_env()
            
            # Find PostgreSQL container
            containers = self.docker_client.containers.list()
            for container in containers:
                if "postgres" in container.name.lower() or "postgres" in str(container.image).lower():
                    self.postgres_container = container
                    break
            
            if self.postgres_container:
                self.postgres_container.stop()
                print(f"Stopped PostgreSQL container: {self.postgres_container.name}")
            else:
                print("PostgreSQL container not found")
                
        except Exception as e:
            print(f"Error stopping database: {e}")
    
    async def stop(self):
        """Restart PostgreSQL container to simulate recovery."""
        try:
            if self.postgres_container:
                self.postgres_container.start()
                
                # Wait for database to be ready
                max_wait = 60
                start_time = time.time()
                
                while time.time() - start_time < max_wait:
                    if await check_database_connection():
                        break
                    await asyncio.sleep(2)
                
                print(f"Restarted PostgreSQL container: {self.postgres_container.name}")
            
        except Exception as e:
            print(f"Error restarting database: {e}")
        
        await super().stop()


class HighCPULoadScenario(ChaosScenario):
    """Simulate high CPU load."""
    
    def __init__(self, intensity: int = 90):
        super().__init__("high_cpu_load", f"Simulate {intensity}% CPU load")
        self.intensity = intensity
        self.stress_processes = []
        self.stop_event = threading.Event()
    
    def _cpu_stress_worker(self):
        """Worker function to create CPU stress."""
        while not self.stop_event.is_set():
            # Busy loop to consume CPU
            for _ in range(1000000):
                if self.stop_event.is_set():
                    break
                _ = 2 ** 2
            
            # Small sleep to allow other processes
            time.sleep(0.001)
    
    async def start(self):
        """Start CPU stress processes."""
        await super().start()
        
        # Calculate number of processes based on CPU count and desired intensity
        cpu_count = psutil.cpu_count()
        num_processes = max(1, int(cpu_count * self.intensity / 100))
        
        self.stop_event.clear()
        
        for i in range(num_processes):
            process = threading.Thread(target=self._cpu_stress_worker)
            process.daemon = True
            process.start()
            self.stress_processes.append(process)
        
        print(f"Started {num_processes} CPU stress processes")
    
    async def stop(self):
        """Stop CPU stress processes."""
        self.stop_event.set()
        
        # Wait for processes to finish
        for process in self.stress_processes:
            process.join(timeout=5)
        
        self.stress_processes.clear()
        print("Stopped CPU stress processes")
        
        await super().stop()


class NetworkLatencyScenario(ChaosScenario):
    """Simulate network latency."""
    
    def __init__(self, delay_ms: int = 2000):
        super().__init__("network_latency", f"Add {delay_ms}ms network latency")
        self.delay_ms = delay_ms
        self.original_session = None
    
    async def start(self):
        """Add network latency to HTTP requests."""
        await super().start()
        
        # Mock aiohttp to add artificial delay
        import aiohttp
        
        self.original_request = aiohttp.ClientSession._request
        
        async def delayed_request(self, method, url, **kwargs):
            # Add artificial delay
            await asyncio.sleep(self.delay_ms / 1000.0)
            return await self.original_request(method, url, **kwargs)
        
        aiohttp.ClientSession._request = delayed_request
        print(f"Added {self.delay_ms}ms network latency")
    
    async def stop(self):
        """Remove network latency."""
        import aiohttp
        
        if self.original_request:
            aiohttp.ClientSession._request = self.original_request
        
        print("Removed network latency")
        await super().stop()


class MemoryPressureScenario(ChaosScenario):
    """Simulate memory pressure."""
    
    def __init__(self, intensity: int = 85):
        super().__init__("memory_pressure", f"Consume {intensity}% of available memory")
        self.intensity = intensity
        self.memory_hogs = []
        self.stop_event = threading.Event()
    
    async def start(self):
        """Start consuming memory."""
        await super().start()
        
        # Get available memory
        memory_info = psutil.virtual_memory()
        target_memory = int(memory_info.total * self.intensity / 100)
        chunk_size = 100 * 1024 * 1024  # 100MB chunks
        
        def memory_consumer():
            chunks = []
            consumed = 0
            
            while not self.stop_event.is_set() and consumed < target_memory:
                try:
                    chunk = bytearray(chunk_size)
                    chunks.append(chunk)
                    consumed += chunk_size
                    time.sleep(0.1)  # Small delay
                except MemoryError:
                    break
            
            # Keep memory allocated until stop signal
            while not self.stop_event.is_set():
                time.sleep(1)
        
        self.stop_event.clear()
        thread = threading.Thread(target=memory_consumer)
        thread.daemon = True
        thread.start()
        self.memory_hogs.append(thread)
        
        print(f"Started memory pressure scenario targeting {target_memory // (1024*1024)}MB")
    
    async def stop(self):
        """Release consumed memory."""
        self.stop_event.set()
        
        for thread in self.memory_hogs:
            thread.join(timeout=10)
        
        self.memory_hogs.clear()
        print("Released memory pressure")
        
        await super().stop()


class TestDatabaseFailures:
    """Test database failure scenarios and recovery."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_database_disconnect_recovery(self, test_db, test_users_db, test_client, auth_headers):
        """
        Test database disconnect and recovery scenario.
        
        Validates that the system gracefully handles database failures and recovers.
        """
        user = test_users_db["user"]
        
        # Create initial task to verify database is working
        response = test_client.post(
            "/api/v1/tasks/",
            json={
                "title": "Pre-chaos task",
                "description": "Task created before database failure",
                "goal": "Test database connectivity"
            },
            headers=auth_headers["user"]
        )
        assert response.status_code == 201
        pre_chaos_task_id = response.json()["id"]
        
        # Initialize chaos scenario
        db_failure = DatabaseFailureScenario()
        
        try:
            # Start database failure
            await db_failure.start()
            
            # Wait for failure to take effect
            await asyncio.sleep(5)
            
            # Attempt operations during database failure
            failure_responses = []
            
            for i in range(5):
                response = test_client.post(
                    "/api/v1/tasks/",
                    json={
                        "title": f"Chaos task {i}",
                        "description": "Task created during database failure",
                        "goal": "Test resilience"
                    },
                    headers=auth_headers["user"]
                )
                
                failure_responses.append({
                    "attempt": i + 1,
                    "status_code": response.status_code,
                    "response": response.json() if response.status_code != 500 else None
                })
                
                await asyncio.sleep(1)
            
            # Verify that requests fail gracefully during database outage
            server_errors = [r for r in failure_responses if r["status_code"] >= 500]
            assert len(server_errors) > 0, "Should have server errors during database failure"
            
            # Verify error responses are informative
            for error_response in server_errors:
                if error_response["response"]:
                    assert "error" in error_response["response"]
                    # Should not expose internal database details
                    error_msg = error_response["response"]["error"]["message"].lower()
                    assert "connection" in error_msg or "unavailable" in error_msg
            
            # Stop database failure (recovery)
            await db_failure.stop()
            
            # Wait for recovery
            await asyncio.sleep(10)
            
            # Verify recovery - should be able to create tasks again
            recovery_response = test_client.post(
                "/api/v1/tasks/",
                json={
                    "title": "Post-recovery task",
                    "description": "Task created after database recovery",
                    "goal": "Test recovery"
                },
                headers=auth_headers["user"]
            )
            
            assert recovery_response.status_code == 201, "Should be able to create tasks after recovery"
            
            # Verify pre-chaos data is still intact
            pre_chaos_response = test_client.get(
                f"/api/v1/tasks/{pre_chaos_task_id}",
                headers=auth_headers["user"]
            )
            assert pre_chaos_response.status_code == 200
            assert pre_chaos_response.json()["title"] == "Pre-chaos task"
            
        finally:
            # Ensure cleanup
            await db_failure.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_database_transaction_rollback(self, test_db, test_users_db):
        """
        Test transaction rollback during database failures.
        
        Validates that partial transactions are properly rolled back.
        """
        user = test_users_db["user"]
        
        # Simulate transaction failure during task creation
        from app.schemas.task import TaskCreate
        
        # Create a scenario where transaction might fail mid-way
        with patch('app.db.session.AsyncSession.commit') as mock_commit:
            # Make commit fail after some operations
            mock_commit.side_effect = Exception("Simulated database failure during commit")
            
            task_data = TaskCreate(
                title="Transaction test task",
                description="Testing transaction rollback",
                goal="Test database consistency"
            )
            
            # Attempt to create task - should fail and rollback
            with pytest.raises(Exception):
                await TaskService.create_task(test_db, user.id, task_data)
        
        # Verify no partial data was committed
        user_tasks = await TaskService.get_user_tasks(test_db, user.id)
        task_titles = [task.title for task in user_tasks]
        assert "Transaction test task" not in task_titles, \
            "Failed transaction should not leave partial data"


class TestResourceExhaustion:
    """Test resource exhaustion scenarios."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_high_cpu_load_resilience(self, test_db, test_users_db, test_client, auth_headers):
        """
        Test system resilience under high CPU load.
        
        Validates that the system remains responsive under CPU stress.
        """
        cpu_stress = HighCPULoadScenario(intensity=90)
        
        try:
            # Measure baseline performance
            baseline_times = []
            for i in range(5):
                start_time = time.time()
                response = test_client.get("/api/v1/tasks/", headers=auth_headers["user"])
                end_time = time.time()
                
                assert response.status_code == 200
                baseline_times.append(end_time - start_time)
                await asyncio.sleep(0.5)
            
            baseline_avg = sum(baseline_times) / len(baseline_times)
            
            # Start CPU stress
            await cpu_stress.start()
            
            # Wait for stress to take effect
            await asyncio.sleep(5)
            
            # Measure performance under stress
            stress_times = []
            stress_responses = []
            
            for i in range(10):
                start_time = time.time()
                response = test_client.get("/api/v1/tasks/", headers=auth_headers["user"])
                end_time = time.time()
                
                stress_times.append(end_time - start_time)
                stress_responses.append(response.status_code)
                await asyncio.sleep(0.5)
            
            stress_avg = sum(stress_times) / len(stress_times)
            success_rate = sum(1 for code in stress_responses if code == 200) / len(stress_responses)
            
            # System should remain functional under stress
            assert success_rate >= 0.8, f"Success rate {success_rate:.2%} too low under CPU stress"
            
            # Response times may increase but should remain reasonable
            assert stress_avg < baseline_avg * 5, \
                f"Response time degradation too severe: {stress_avg:.2f}s vs baseline {baseline_avg:.2f}s"
            
        finally:
            await cpu_stress.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_memory_pressure_handling(self, test_db, test_users_db, test_client, auth_headers):
        """
        Test system behavior under memory pressure.
        
        Validates graceful degradation under memory constraints.
        """
        memory_pressure = MemoryPressureScenario(intensity=85)
        
        try:
            # Start memory pressure
            await memory_pressure.start()
            
            # Wait for memory pressure to build
            await asyncio.sleep(10)
            
            # Test system behavior under memory pressure
            responses = []
            
            for i in range(20):
                try:
                    response = test_client.post(
                        "/api/v1/tasks/",
                        json={
                            "title": f"Memory pressure task {i}",
                            "description": "Task created under memory pressure",
                            "goal": "Test memory resilience"
                        },
                        headers=auth_headers["user"]
                    )
                    
                    responses.append({
                        "attempt": i + 1,
                        "status_code": response.status_code,
                        "success": response.status_code < 400
                    })
                    
                except Exception as e:
                    responses.append({
                        "attempt": i + 1,
                        "status_code": 500,
                        "success": False,
                        "error": str(e)
                    })
                
                await asyncio.sleep(0.5)
            
            # Analyze results
            successful_requests = [r for r in responses if r["success"]]
            success_rate = len(successful_requests) / len(responses)
            
            # System should handle some requests even under memory pressure
            assert success_rate >= 0.5, \
                f"Success rate {success_rate:.2%} too low under memory pressure"
            
            # Check for graceful error handling
            failed_requests = [r for r in responses if not r["success"]]
            for failed_request in failed_requests:
                # Should not be memory allocation errors exposed to user
                if "error" in failed_request:
                    assert "memory" not in failed_request["error"].lower()
                    assert "allocation" not in failed_request["error"].lower()
            
        finally:
            await memory_pressure.stop()


class TestNetworkFailures:
    """Test network failure scenarios."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_network_latency_tolerance(self, test_db, test_users_db, test_client, auth_headers):
        """
        Test system tolerance to network latency.
        
        Validates that the system handles high latency gracefully.
        """
        latency_scenario = NetworkLatencyScenario(delay_ms=2000)
        
        try:
            # Test baseline external requests
            baseline_start = time.time()
            response = test_client.post(
                "/api/v1/web-pages/parse",
                json={
                    "url": "https://httpbin.org/forms/post",
                    "force_refresh": False
                },
                headers=auth_headers["user"]
            )
            baseline_time = time.time() - baseline_start
            
            # Should succeed without artificial latency
            assert response.status_code == 200
            
            # Start network latency
            await latency_scenario.start()
            
            # Test with artificial latency
            latency_start = time.time()
            response = test_client.post(
                "/api/v1/web-pages/parse",
                json={
                    "url": "https://httpbin.org/forms/post",
                    "force_refresh": True  # Force new request
                },
                headers=auth_headers["user"]
            )
            latency_time = time.time() - latency_start
            
            # Should still succeed but take longer
            assert response.status_code == 200
            assert latency_time > baseline_time + 1.5  # Should be noticeably slower
            
            # Test timeout handling
            timeout_responses = []
            
            for i in range(3):
                try:
                    start_time = time.time()
                    response = test_client.post(
                        "/api/v1/web-pages/parse",
                        json={
                            "url": f"https://httpbin.org/delay/1?test={i}",
                            "force_refresh": True
                        },
                        headers=auth_headers["user"],
                        timeout=5  # Short timeout
                    )
                    end_time = time.time()
                    
                    timeout_responses.append({
                        "attempt": i + 1,
                        "status_code": response.status_code,
                        "duration": end_time - start_time,
                        "success": response.status_code < 400
                    })
                    
                except Exception as e:
                    timeout_responses.append({
                        "attempt": i + 1,
                        "status_code": 408,  # Timeout
                        "success": False,
                        "error": str(e)
                    })
            
            # Should handle timeouts gracefully
            timeout_count = sum(1 for r in timeout_responses if not r["success"])
            assert timeout_count > 0, "Should experience timeouts with high latency"
            
        finally:
            await latency_scenario.stop()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_external_service_failure_resilience(self, test_db, test_users_db, test_client, auth_headers):
        """
        Test resilience to external service failures.
        
        Validates graceful handling when external services are unavailable.
        """
        # Test with unreachable external service
        unreachable_urls = [
            "http://192.0.2.1/nonexistent",  # RFC 5737 test address
            "https://this-domain-should-not-exist-12345.com",
            "http://localhost:99999/invalid-port"
        ]
        
        for url in unreachable_urls:
            response = test_client.post(
                "/api/v1/web-pages/parse",
                json={
                    "url": url,
                    "force_refresh": True
                },
                headers=auth_headers["user"]
            )
            
            # Should handle gracefully, not crash
            assert response.status_code in [200, 400, 422, 500]
            
            if response.status_code == 200:
                # If task created, it should indicate failure
                task_data = response.json()
                # Check task status or error indication
                # Implementation depends on how parsing failures are handled
            
            elif response.status_code >= 400:
                # Should provide meaningful error message
                error_data = response.json()
                assert "error" in error_data
                # Should not expose internal details
                error_msg = error_data["error"]["message"].lower()
                assert "connection" in error_msg or "unreachable" in error_msg or "invalid" in error_msg
