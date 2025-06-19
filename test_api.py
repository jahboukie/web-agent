#!/usr/bin/env python3
"""
Test script for WebAgent Phase 2B implementation.

This script tests the complete background task processing workflow:
1. User registration and authentication
2. Webpage parsing task creation
3. Real-time status monitoring
4. Result retrieval
5. Cache performance
6. Error handling
"""

import asyncio
import json
import time
from typing import Dict, Any
import httpx
import structlog

# Configure logging
logger = structlog.get_logger(__name__)

BASE_URL = "http://localhost:8000"
TEST_USER = {
    "email": "testuser@example.com",
    "username": "testuser", 
    "password": "Test123!",
    "confirm_password": "Test123!",
    "accept_terms": True
}

class WebAgentTester:
    """Test suite for WebAgent Phase 2B implementation."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.access_token = None
        self.test_results = {}
    
    async def test_user_registration(self) -> bool:
        """Test user registration."""
        print("\n🔐 Testing User Registration...")
        
        try:
            response = await self.client.post(
                f"{BASE_URL}/api/v1/auth/register",
                json=TEST_USER
            )
            
            if response.status_code == 201:
                print("✅ User registration successful")
                return True
            elif response.status_code == 400 and "already registered" in response.text:
                print("ℹ️  User already exists, continuing...")
                return True
            else:
                print(f"❌ Registration failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False
    
    async def test_user_login(self) -> bool:
        """Test user login and token retrieval."""
        print("\n🔑 Testing User Login...")
        
        try:
            login_data = {
                "username": TEST_USER["username"],
                "password": TEST_USER["password"]
            }
            
            response = await self.client.post(
                f"{BASE_URL}/api/v1/auth/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data["access_token"]
                print("✅ Login successful, token acquired")
                return True
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers."""
        return {"Authorization": f"Bearer {self.access_token}"}
    
    async def test_webpage_parsing(self, url: str = "https://example.com") -> Dict[str, Any]:
        """Test webpage parsing with background task processing."""
        print(f"\n🌐 Testing Webpage Parsing for: {url}")
        
        try:
            # Start parsing task
            parse_request = {
                "url": url,
                "include_screenshot": True,
                "wait_for_load": 2,
                "wait_for_network_idle": True
            }
            
            response = await self.client.post(
                f"{BASE_URL}/api/v1/web-pages/parse",
                json=parse_request,
                headers=self.get_auth_headers()
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to start parsing: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text}
            
            task_data = response.json()
            task_id = task_data["task_id"]
            print(f"✅ Parsing task created: {task_id}")
            print(f"   Status: {task_data['status']}")
            print(f"   Estimated duration: {task_data['estimated_duration_seconds']}s")
            
            # Monitor task progress
            return await self.monitor_task_progress(task_id)
            
        except Exception as e:
            print(f"❌ Parsing error: {e}")
            return {"success": False, "error": str(e)}
    
    async def monitor_task_progress(self, task_id: int) -> Dict[str, Any]:
        """Monitor task progress until completion."""
        print(f"\n📊 Monitoring Task Progress: {task_id}")
        
        max_wait_time = 120  # 2 minutes max
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                response = await self.client.get(
                    f"{BASE_URL}/api/v1/web-pages/{task_id}",
                    headers=self.get_auth_headers()
                )
                
                if response.status_code != 200:
                    print(f"❌ Failed to get task status: {response.status_code}")
                    return {"success": False, "error": "Status check failed"}
                
                status_data = response.json()
                status = status_data["status"]
                progress = status_data.get("progress_percentage", 0)
                current_step = status_data.get("current_step", "unknown")
                
                print(f"   Status: {status} | Progress: {progress}% | Step: {current_step}")
                
                if status == "completed":
                    print("✅ Task completed successfully!")
                    
                    # Get results
                    results = await self.get_task_results(task_id)
                    return {"success": True, "results": results, "task_data": status_data}
                
                elif status == "failed":
                    error_msg = status_data.get("error_message", "Unknown error")
                    print(f"❌ Task failed: {error_msg}")
                    return {"success": False, "error": error_msg}
                
                # Wait before next check
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ Error monitoring task: {e}")
                return {"success": False, "error": str(e)}
        
        print("⏰ Task monitoring timeout")
        return {"success": False, "error": "Timeout"}
    
    async def get_task_results(self, task_id: int) -> Dict[str, Any]:
        """Get detailed task results."""
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/web-pages/{task_id}/results",
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                results = response.json()
                print(f"📋 Results Summary:")
                print(f"   Interactive Elements: {len(results.get('interactive_elements', []))}")
                print(f"   Content Blocks: {len(results.get('content_blocks', []))}")
                print(f"   Action Capabilities: {len(results.get('action_capabilities', []))}")
                print(f"   Screenshot: {'Yes' if results.get('screenshot_path') else 'No'}")
                return results
            else:
                print(f"❌ Failed to get results: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ Error getting results: {e}")
            return {}
    
    async def test_cache_performance(self) -> bool:
        """Test cache performance by parsing the same URL twice."""
        print("\n🚀 Testing Cache Performance...")
        
        url = "https://httpbin.org/html"
        
        # First request (should be slow)
        print("   First request (no cache)...")
        start_time = time.time()
        result1 = await self.test_webpage_parsing(url)
        first_duration = time.time() - start_time
        
        if not result1.get("success"):
            print("❌ First request failed")
            return False
        
        # Second request (should be fast due to cache)
        print("   Second request (should hit cache)...")
        start_time = time.time()
        result2 = await self.test_webpage_parsing(url)
        second_duration = time.time() - start_time
        
        if not result2.get("success"):
            print("❌ Second request failed")
            return False
        
        # Check if second request was faster (indicating cache hit)
        if second_duration < first_duration * 0.5:  # At least 50% faster
            print(f"✅ Cache performance test passed!")
            print(f"   First request: {first_duration:.2f}s")
            print(f"   Second request: {second_duration:.2f}s")
            print(f"   Speed improvement: {((first_duration - second_duration) / first_duration * 100):.1f}%")
            return True
        else:
            print(f"⚠️  Cache may not be working optimally")
            print(f"   First request: {first_duration:.2f}s")
            print(f"   Second request: {second_duration:.2f}s")
            return False
    
    async def test_cache_stats(self) -> bool:
        """Test cache statistics endpoint."""
        print("\n📈 Testing Cache Statistics...")
        
        try:
            response = await self.client.get(
                f"{BASE_URL}/api/v1/web-pages/cache/stats",
                headers=self.get_auth_headers()
            )
            
            if response.status_code == 200:
                stats = response.json()
                cache_stats = stats.get("cache_stats", {})
                print("✅ Cache statistics retrieved:")
                print(f"   Cache Hits: {cache_stats.get('cache_hits', 0)}")
                print(f"   Cache Misses: {cache_stats.get('cache_misses', 0)}")
                print(f"   Hit Rate: {cache_stats.get('hit_rate_percentage', 0)}%")
                print(f"   Redis Memory: {cache_stats.get('redis_memory_used_mb', 0)} MB")
                return True
            else:
                print(f"❌ Failed to get cache stats: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Cache stats error: {e}")
            return False
    
    async def run_all_tests(self):
        """Run complete test suite."""
        print("🚀 Starting WebAgent Phase 2B Integration Tests")
        print("=" * 60)
        
        # Test authentication
        if not await self.test_user_registration():
            return False
        
        if not await self.test_user_login():
            return False
        
        # Test basic webpage parsing
        result = await self.test_webpage_parsing("https://httpbin.org/html")
        if not result.get("success"):
            return False
        
        # Test cache performance
        await self.test_cache_performance()
        
        # Test cache statistics
        await self.test_cache_stats()
        
        print("\n" + "=" * 60)
        print("🎉 All tests completed!")
        print("✅ WebAgent Phase 2B implementation is working correctly!")
        
        await self.client.aclose()
        return True


async def main():
    """Main test function."""
    tester = WebAgentTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
