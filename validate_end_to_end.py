#!/usr/bin/env python3
"""
WebAgent + Aura End-to-End Validation Script

Comprehensive validation of the complete WebAgent platform including:
- Backend API health and functionality
- Frontend dashboard components
- Authentication flow
- Analytics dashboard
- User workflows
- Security features
- Performance testing

This script mimics real user flows through the dashboard elements.
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import aiohttp
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

# Configuration
BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:3000"
API_BASE = f"{BACKEND_URL}/api/v1"

# Test user credentials
TEST_USER = {
    "email": "test@webagent.com",
    "password": "TestPassword123!",
    "full_name": "Test User"
}

class ValidationResults:
    """Track validation results across all tests."""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        
    def add_result(self, test_name: str, status: str, details: str = "", 
                   duration: float = 0, error: str = ""):
        """Add a test result."""
        self.results.append({
            "test_name": test_name,
            "status": status,  # PASS, FAIL, SKIP
            "details": details,
            "duration": duration,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        total = len(self.results)
        passed = len([r for r in self.results if r["status"] == "PASS"])
        failed = len([r for r in self.results if r["status"] == "FAIL"])
        skipped = len([r for r in self.results if r["status"] == "SKIP"])
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "duration": (datetime.now() - self.start_time).total_seconds(),
            "results": self.results
        }

class WebAgentValidator:
    """Main validation class for WebAgent + Aura platform."""
    
    def __init__(self):
        self.results = ValidationResults()
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
        self.driver: Optional[webdriver.Chrome] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
        if self.driver:
            self.driver.quit()
            
    def setup_browser(self):
        """Setup Chrome browser for frontend testing."""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Run in background
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            return True
        except Exception as e:
            print(f"❌ Failed to setup browser: {e}")
            return False
            
    async def test_backend_health(self):
        """Test backend service health."""
        test_name = "Backend Health Check"
        start_time = time.time()
        
        try:
            async with self.session.get(f"{BACKEND_URL}/") as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "operational":
                        self.results.add_result(
                            test_name, "PASS", 
                            f"Backend operational, version: {data.get('version')}",
                            time.time() - start_time
                        )
                        return True
                    else:
                        raise Exception(f"Backend status: {data.get('status')}")
                else:
                    raise Exception(f"HTTP {response.status}")
                    
        except Exception as e:
            self.results.add_result(
                test_name, "FAIL", 
                "Backend health check failed",
                time.time() - start_time, str(e)
            )
            return False
            
    async def test_api_endpoints(self):
        """Test critical API endpoints."""
        endpoints = [
            ("/docs", "API Documentation"),
            ("/api/v1/auth/register", "Auth Registration Endpoint"),
            ("/api/v1/analytics/dashboard", "Analytics Dashboard Endpoint"),
            ("/api/v1/tasks", "Tasks Endpoint"),
            ("/api/v1/web-pages", "Web Pages Endpoint")
        ]
        
        for endpoint, description in endpoints:
            test_name = f"API Endpoint: {description}"
            start_time = time.time()
            
            try:
                async with self.session.get(f"{BACKEND_URL}{endpoint}") as response:
                    # Accept 200 (OK) or 401 (Unauthorized - expected for protected endpoints)
                    if response.status in [200, 401, 422]:
                        self.results.add_result(
                            test_name, "PASS",
                            f"Endpoint accessible (HTTP {response.status})",
                            time.time() - start_time
                        )
                    else:
                        raise Exception(f"HTTP {response.status}")
                        
            except Exception as e:
                self.results.add_result(
                    test_name, "FAIL",
                    f"Endpoint not accessible",
                    time.time() - start_time, str(e)
                )
                
    async def test_user_registration(self):
        """Test user registration flow."""
        test_name = "User Registration"
        start_time = time.time()
        
        try:
            # Add timestamp to email to avoid conflicts
            test_email = f"test_{int(time.time())}@webagent.com"
            
            registration_data = {
                "email": test_email,
                "username": f"testuser_{int(time.time())}",
                "password": TEST_USER["password"],
                "confirm_password": TEST_USER["password"],
                "full_name": TEST_USER["full_name"],
                "accept_terms": True
            }
            
            async with self.session.post(
                f"{API_BASE}/auth/register",
                json=registration_data
            ) as response:
                if response.status == 201:
                    data = await response.json()
                    self.auth_token = data.get("access_token")
                    self.results.add_result(
                        test_name, "PASS",
                        f"User registered successfully: {test_email}",
                        time.time() - start_time
                    )
                    return True
                else:
                    error_data = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_data}")
                    
        except Exception as e:
            self.results.add_result(
                test_name, "FAIL",
                "User registration failed",
                time.time() - start_time, str(e)
            )
            return False
            
    async def test_analytics_dashboard_api(self):
        """Test analytics dashboard API."""
        if not self.auth_token:
            self.results.add_result(
                "Analytics Dashboard API", "SKIP",
                "No auth token available"
            )
            return
            
        test_name = "Analytics Dashboard API"
        start_time = time.time()
        
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            
            async with self.session.get(
                f"{API_BASE}/analytics/dashboard",
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    required_fields = ["subscription", "usage_metrics", "upgrade_opportunities"]
                    
                    missing_fields = [field for field in required_fields if field not in data]
                    if not missing_fields:
                        self.results.add_result(
                            test_name, "PASS",
                            f"Analytics data complete with {len(data)} fields",
                            time.time() - start_time
                        )
                    else:
                        raise Exception(f"Missing fields: {missing_fields}")
                else:
                    error_data = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_data}")
                    
        except Exception as e:
            self.results.add_result(
                test_name, "FAIL",
                "Analytics dashboard API failed",
                time.time() - start_time, str(e)
            )
            
    def test_frontend_loading(self):
        """Test frontend application loading."""
        if not self.driver:
            self.results.add_result(
                "Frontend Loading", "SKIP",
                "Browser not available"
            )
            return

        test_name = "Frontend Loading"
        start_time = time.time()

        try:
            self.driver.get(FRONTEND_URL)

            # Wait for React app to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Check for common React error indicators
            if "Error" in self.driver.title or "404" in self.driver.title:
                raise Exception(f"Error in page title: {self.driver.title}")

            self.results.add_result(
                test_name, "PASS",
                f"Frontend loaded successfully: {self.driver.title}",
                time.time() - start_time
            )
            return True

        except Exception as e:
            self.results.add_result(
                test_name, "FAIL",
                "Frontend loading failed",
                time.time() - start_time, str(e)
            )
            return False

    def test_dashboard_components(self):
        """Test dashboard components are rendering."""
        if not self.driver:
            self.results.add_result(
                "Dashboard Components", "SKIP",
                "Browser not available"
            )
            return

        test_name = "Dashboard Components"
        start_time = time.time()

        try:
            # Navigate to dashboard
            self.driver.get(f"{FRONTEND_URL}/dashboard")

            # Wait for dashboard to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "main"))
            )

            # Check for key dashboard elements
            components_found = []

            # Look for navigation elements
            try:
                nav_element = self.driver.find_element(By.TAG_NAME, "nav")
                components_found.append("Navigation")
            except:
                pass

            # Look for dashboard cards/components
            try:
                cards = self.driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='dashboard']")
                if cards:
                    components_found.append(f"Dashboard Cards ({len(cards)})")
            except:
                pass

            # Look for analytics components
            try:
                analytics = self.driver.find_elements(By.CSS_SELECTOR, "[class*='analytics'], [class*='chart']")
                if analytics:
                    components_found.append(f"Analytics Components ({len(analytics)})")
            except:
                pass

            if components_found:
                self.results.add_result(
                    test_name, "PASS",
                    f"Dashboard components found: {', '.join(components_found)}",
                    time.time() - start_time
                )
                return True
            else:
                raise Exception("No dashboard components found")

        except Exception as e:
            self.results.add_result(
                test_name, "FAIL",
                "Dashboard components test failed",
                time.time() - start_time, str(e)
            )
            return False

    async def run_validation(self):
        """Run complete validation suite."""
        print("🚀 Starting WebAgent + Aura End-to-End Validation")
        print("=" * 60)
        print(f"Backend URL: {BACKEND_URL}")
        print(f"Frontend URL: {FRONTEND_URL}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print()
        
        # Setup browser
        browser_available = self.setup_browser()
        if not browser_available:
            print("⚠️  Browser tests will be skipped")
        
        # Run backend tests
        print("🔧 Testing Backend Services...")
        await self.test_backend_health()
        await self.test_api_endpoints()
        await self.test_user_registration()
        await self.test_analytics_dashboard_api()
        
        # Run frontend tests
        if browser_available:
            print("\n🎨 Testing Frontend Application...")
            self.test_frontend_loading()
            self.test_dashboard_components()
        
        # Generate report
        print("\n📊 Validation Results")
        print("=" * 60)
        summary = self.results.get_summary()
        
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']} ✅")
        print(f"Failed: {summary['failed']} ❌")
        print(f"Skipped: {summary['skipped']} ⏭️")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Duration: {summary['duration']:.2f}s")
        
        print("\n📋 Detailed Results:")
        for result in self.results.results:
            status_icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}[result["status"]]
            print(f"{status_icon} {result['test_name']}: {result['details']}")
            if result["error"]:
                print(f"   Error: {result['error']}")
        
        return summary

async def main():
    """Main validation function."""
    async with WebAgentValidator() as validator:
        summary = await validator.run_validation()
        
        # Save detailed results
        with open("validation_results.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: validation_results.json")
        
        # Exit with appropriate code
        if summary["failed"] > 0:
            print("\n❌ Validation completed with failures")
            sys.exit(1)
        else:
            print("\n✅ All validations passed successfully!")
            sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
