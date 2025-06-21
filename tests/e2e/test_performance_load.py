"""
E2E Tests: Performance & Load Testing
Tests for concurrent agents, HSM latency, and auto-scaling validation
"""

import pytest
import asyncio
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import aiohttp
import json

from app.core.config import settings
from app.services.web_parser import web_parser_service
from app.services.planning_service import planning_service
from app.services.action_executor import action_executor
from app.security.hsm_integration import hsm_client


class TestConcurrentAgentLoad:
    """Test system performance under concurrent agent load."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_500_concurrent_agents_peak_load(self, test_db, test_users_db, test_websites):
        """
        Simulate 500+ concurrent agents under peak load.
        
        Validates system stability and performance under high concurrency.
        """
        # Test configuration
        concurrent_agents = 500
        test_duration_seconds = 300  # 5 minutes
        target_websites = [
            test_websites["simple_form"],
            test_websites["spa_application"],
            test_websites["authentication_required"],
            test_websites["complex_navigation"]
        ]
        
        # Performance metrics tracking
        metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "error_types": {},
            "throughput_per_second": [],
            "memory_usage": [],
            "cpu_usage": []
        }
        
        # Create user pool for testing
        test_users = [test_users_db["user"], test_users_db["manager"]] * (concurrent_agents // 2)
        
        async def simulate_agent_workflow(user, website, agent_id):
            """Simulate complete agent workflow for one user."""
            start_time = time.time()
            
            try:
                # Step 1: Parse webpage
                parse_result = await web_parser_service.parse_webpage_async(
                    test_db,
                    task_id=None,
                    url=website["url"],
                    options={
                        "extract_forms": True,
                        "extract_links": True,
                        "semantic_analysis": True,
                        "wait_for_load": 3
                    }
                )
                
                if not parse_result or not parse_result.success:
                    raise Exception("Parsing failed")
                
                # Step 2: Generate execution plan
                planning_result = await planning_service.generate_plan_async(
                    test_db,
                    task_id=parse_result.task_id,
                    user_goal=f"Complete workflow for agent {agent_id}",
                    planning_options={
                        "planning_timeout_seconds": 60,
                        "max_agent_iterations": 8,
                        "planning_temperature": 0.1
                    },
                    user_id=user.id
                )
                
                if not planning_result:
                    raise Exception("Planning failed")
                
                # Step 3: Execute plan (simulate execution without actual browser)
                execution_id = await action_executor.execute_plan_async(
                    test_db,
                    plan_id=planning_result.id,
                    user_id=user.id,
                    execution_options={
                        "take_screenshots": False,  # Disable for performance
                        "execution_timeout_seconds": 60,
                        "simulate_execution": True  # Mock execution for load testing
                    }
                )
                
                if not execution_id:
                    raise Exception("Execution failed")
                
                # Record success
                end_time = time.time()
                response_time = end_time - start_time
                
                return {
                    "success": True,
                    "response_time": response_time,
                    "agent_id": agent_id,
                    "steps_completed": 3
                }
                
            except Exception as e:
                end_time = time.time()
                response_time = end_time - start_time
                
                return {
                    "success": False,
                    "response_time": response_time,
                    "agent_id": agent_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
        
        # Execute concurrent agent workflows
        start_time = datetime.utcnow()
        tasks = []
        
        for i in range(concurrent_agents):
            user = test_users[i % len(test_users)]
            website = target_websites[i % len(target_websites)]
            
            task = simulate_agent_workflow(user, website, i)
            tasks.append(task)
        
        # Run all tasks concurrently with progress tracking
        results = []
        completed = 0
        
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            completed += 1
            
            # Track progress every 50 completions
            if completed % 50 == 0:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                throughput = completed / elapsed
                print(f"Progress: {completed}/{concurrent_agents} ({throughput:.2f} req/sec)")
        
        # Analyze results
        total_time = (datetime.utcnow() - start_time).total_seconds()
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        # Performance assertions
        success_rate = len(successful_results) / len(results)
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} below 95% threshold"
        
        # Response time analysis
        response_times = [r["response_time"] for r in successful_results]
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        
        assert avg_response_time < 30, f"Average response time {avg_response_time:.2f}s exceeds 30s"
        assert p95_response_time < 60, f"95th percentile response time {p95_response_time:.2f}s exceeds 60s"
        
        # Throughput analysis
        overall_throughput = len(results) / total_time
        assert overall_throughput >= 10, f"Throughput {overall_throughput:.2f} req/sec below 10 req/sec"
        
        # Error analysis
        if failed_results:
            error_types = {}
            for result in failed_results:
                error_type = result.get("error_type", "Unknown")
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            print(f"Error breakdown: {error_types}")
            
            # No single error type should account for more than 2% of requests
            for error_type, count in error_types.items():
                error_rate = count / len(results)
                assert error_rate < 0.02, f"Error type '{error_type}' rate {error_rate:.2%} exceeds 2%"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_hsm_latency_at_high_throughput(self, test_db, test_users_db):
        """
        Measure HSM latency at 100+ req/sec.
        
        Validates HSM performance under high cryptographic load.
        """
        # Test configuration
        target_rps = 100  # requests per second
        test_duration = 60  # seconds
        total_requests = target_rps * test_duration
        
        # HSM operation types to test
        hsm_operations = [
            "generate_key_pair",
            "encrypt_data",
            "decrypt_data",
            "sign_data",
            "verify_signature"
        ]
        
        # Performance tracking
        operation_metrics = {op: {"times": [], "errors": 0} for op in hsm_operations}
        
        async def perform_hsm_operation(operation_type, data_size=1024):
            """Perform a single HSM operation and measure latency."""
            start_time = time.time()
            
            try:
                if operation_type == "generate_key_pair":
                    result = await hsm_client.generate_key_pair(
                        key_type="RSA",
                        key_size=2048
                    )
                elif operation_type == "encrypt_data":
                    test_data = "x" * data_size
                    result = await hsm_client.encrypt(
                        data=test_data,
                        key_id="test_key_123"
                    )
                elif operation_type == "decrypt_data":
                    encrypted_data = "encrypted_test_data_blob"
                    result = await hsm_client.decrypt(
                        encrypted_data=encrypted_data,
                        key_id="test_key_123"
                    )
                elif operation_type == "sign_data":
                    test_data = "data_to_sign"
                    result = await hsm_client.sign(
                        data=test_data,
                        key_id="signing_key_123"
                    )
                elif operation_type == "verify_signature":
                    test_data = "data_to_verify"
                    signature = "test_signature_blob"
                    result = await hsm_client.verify_signature(
                        data=test_data,
                        signature=signature,
                        key_id="signing_key_123"
                    )
                
                end_time = time.time()
                latency = (end_time - start_time) * 1000  # Convert to milliseconds
                
                return {
                    "success": True,
                    "latency_ms": latency,
                    "operation": operation_type
                }
                
            except Exception as e:
                end_time = time.time()
                latency = (end_time - start_time) * 1000
                
                return {
                    "success": False,
                    "latency_ms": latency,
                    "operation": operation_type,
                    "error": str(e)
                }
        
        # Execute HSM operations at target throughput
        start_time = datetime.utcnow()
        all_tasks = []
        
        for i in range(total_requests):
            operation_type = hsm_operations[i % len(hsm_operations)]
            task = perform_hsm_operation(operation_type)
            all_tasks.append(task)
            
            # Control request rate
            if i > 0 and i % target_rps == 0:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                expected_time = i / target_rps
                
                if elapsed < expected_time:
                    await asyncio.sleep(expected_time - elapsed)
        
        # Execute all operations
        results = await asyncio.gather(*all_tasks, return_exceptions=True)
        
        # Analyze HSM performance
        for result in results:
            if isinstance(result, Exception):
                continue
                
            operation = result["operation"]
            
            if result["success"]:
                operation_metrics[operation]["times"].append(result["latency_ms"])
            else:
                operation_metrics[operation]["errors"] += 1
        
        # Performance assertions for each operation type
        for operation, metrics in operation_metrics.items():
            if not metrics["times"]:
                continue
                
            avg_latency = statistics.mean(metrics["times"])
            p95_latency = statistics.quantiles(metrics["times"], n=20)[18] if len(metrics["times"]) > 20 else max(metrics["times"])
            error_rate = metrics["errors"] / (len(metrics["times"]) + metrics["errors"])
            
            # HSM latency thresholds (adjust based on HSM specifications)
            max_avg_latency = {
                "generate_key_pair": 500,  # 500ms for key generation
                "encrypt_data": 50,        # 50ms for encryption
                "decrypt_data": 50,        # 50ms for decryption
                "sign_data": 100,          # 100ms for signing
                "verify_signature": 100    # 100ms for verification
            }
            
            assert avg_latency < max_avg_latency[operation], \
                f"{operation} average latency {avg_latency:.2f}ms exceeds {max_avg_latency[operation]}ms"
            
            assert p95_latency < max_avg_latency[operation] * 2, \
                f"{operation} 95th percentile latency {p95_latency:.2f}ms exceeds threshold"
            
            assert error_rate < 0.01, \
                f"{operation} error rate {error_rate:.2%} exceeds 1%"
        
        # Overall throughput validation
        total_time = (datetime.utcnow() - start_time).total_seconds()
        actual_rps = len([r for r in results if not isinstance(r, Exception)]) / total_time
        
        assert actual_rps >= target_rps * 0.95, \
            f"Actual RPS {actual_rps:.2f} below target {target_rps} (95% threshold)"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_auto_scaling_thresholds(self, test_db, test_users_db, test_client, auth_headers):
        """
        Test auto-scaling thresholds during traffic spikes.
        
        Validates that system scales appropriately under load.
        """
        # Simulate gradual traffic increase
        traffic_phases = [
            {"rps": 10, "duration": 30},   # Baseline
            {"rps": 50, "duration": 60},   # Moderate load
            {"rps": 100, "duration": 90},  # High load
            {"rps": 200, "duration": 60},  # Peak load
            {"rps": 50, "duration": 30}    # Scale down
        ]
        
        scaling_events = []
        performance_metrics = []
        
        async def make_api_request(endpoint="/api/v1/tasks/", method="GET"):
            """Make a single API request and measure response time."""
            start_time = time.time()
            
            try:
                if method == "GET":
                    response = test_client.get(endpoint, headers=auth_headers["user"])
                elif method == "POST":
                    response = test_client.post(
                        endpoint,
                        json={
                            "title": f"Load test task {time.time()}",
                            "description": "Load testing task",
                            "goal": "Test system under load"
                        },
                        headers=auth_headers["user"]
                    )
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # ms
                
                return {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "response_time_ms": response_time,
                    "timestamp": datetime.utcnow()
                }
                
            except Exception as e:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                return {
                    "success": False,
                    "status_code": 500,
                    "response_time_ms": response_time,
                    "error": str(e),
                    "timestamp": datetime.utcnow()
                }
        
        # Execute traffic phases
        for phase_idx, phase in enumerate(traffic_phases):
            print(f"Phase {phase_idx + 1}: {phase['rps']} RPS for {phase['duration']}s")
            
            phase_start = datetime.utcnow()
            phase_results = []
            
            # Generate requests at target RPS
            request_interval = 1.0 / phase["rps"]
            
            while (datetime.utcnow() - phase_start).total_seconds() < phase["duration"]:
                # Alternate between GET and POST requests
                method = "POST" if len(phase_results) % 4 == 0 else "GET"
                
                result = await make_api_request(method=method)
                phase_results.append(result)
                
                # Control request rate
                await asyncio.sleep(request_interval)
            
            # Analyze phase performance
            successful_requests = [r for r in phase_results if r["success"]]
            failed_requests = [r for r in phase_results if not r["success"]]
            
            if successful_requests:
                avg_response_time = statistics.mean([r["response_time_ms"] for r in successful_requests])
                p95_response_time = statistics.quantiles(
                    [r["response_time_ms"] for r in successful_requests], n=20
                )[18] if len(successful_requests) > 20 else max([r["response_time_ms"] for r in successful_requests])
            else:
                avg_response_time = float('inf')
                p95_response_time = float('inf')
            
            success_rate = len(successful_requests) / len(phase_results) if phase_results else 0
            actual_rps = len(phase_results) / phase["duration"]
            
            phase_metrics = {
                "phase": phase_idx + 1,
                "target_rps": phase["rps"],
                "actual_rps": actual_rps,
                "success_rate": success_rate,
                "avg_response_time_ms": avg_response_time,
                "p95_response_time_ms": p95_response_time,
                "total_requests": len(phase_results),
                "failed_requests": len(failed_requests)
            }
            
            performance_metrics.append(phase_metrics)
            
            # Check for scaling indicators
            if avg_response_time > 1000:  # Response time > 1s indicates need to scale
                scaling_events.append({
                    "phase": phase_idx + 1,
                    "event": "scale_up_needed",
                    "trigger": "high_response_time",
                    "value": avg_response_time
                })
            
            if success_rate < 0.95:  # Success rate < 95% indicates overload
                scaling_events.append({
                    "phase": phase_idx + 1,
                    "event": "scale_up_needed",
                    "trigger": "low_success_rate",
                    "value": success_rate
                })
        
        # Validate auto-scaling behavior
        # During high load phases (3-4), system should maintain performance
        high_load_phases = [p for p in performance_metrics if p["phase"] in [3, 4]]
        
        for phase in high_load_phases:
            # Even under high load, success rate should remain acceptable
            assert phase["success_rate"] >= 0.90, \
                f"Phase {phase['phase']} success rate {phase['success_rate']:.2%} below 90%"
            
            # Response times may increase but should remain reasonable
            assert phase["avg_response_time_ms"] < 5000, \
                f"Phase {phase['phase']} avg response time {phase['avg_response_time_ms']:.0f}ms exceeds 5s"
        
        # Scale-down phase should show improved performance
        scale_down_phase = performance_metrics[-1]  # Last phase
        baseline_phase = performance_metrics[0]     # First phase
        
        # Performance should return to baseline levels
        assert scale_down_phase["avg_response_time_ms"] <= baseline_phase["avg_response_time_ms"] * 1.5, \
            "Performance did not return to baseline after scale-down"
        
        print(f"Scaling events detected: {len(scaling_events)}")
        print(f"Performance summary: {json.dumps(performance_metrics, indent=2)}")
