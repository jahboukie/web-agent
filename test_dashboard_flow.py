#!/usr/bin/env python3
"""
WebAgent Dashboard User Flow Test

This script tests the complete user flow through the dashboard components:
1. User registration/login
2. Dashboard navigation
3. Analytics viewing
4. Component interaction
5. Real user workflow simulation

Focus on testing the newly built dashboard elements and user experience.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any

import aiohttp

# Configuration
BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:3000"
API_BASE = f"{BACKEND_URL}/api/v1"


class DashboardFlowTester:
    """Test dashboard user flows and component interactions."""

    def __init__(self):
        self.session: aiohttp.ClientSession = None
        self.auth_token: str = None
        self.user_data: dict[str, Any] = None
        self.test_results: list = []

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def log_result(
        self, test_name: str, success: bool, details: str = "", error: str = ""
    ):
        """Log test result."""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }
        self.test_results.append(result)

        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {details}")
        if error:
            print(f"   Error: {error}")

    async def test_user_registration_flow(self):
        """Test complete user registration and authentication."""
        print("\n🔐 Testing User Registration & Authentication Flow")

        # Generate unique test user
        timestamp = int(time.time())
        self.test_username = f"dashtest_{timestamp}"
        test_user = {
            "email": f"dashboard_test_{timestamp}@webagent.com",
            "username": self.test_username,
            "password": "DashTest123!",
            "confirm_password": "DashTest123!",
            "full_name": "Dashboard Test User",
            "accept_terms": True,
        }

        try:
            async with self.session.post(
                f"{API_BASE}/auth/register", json=test_user
            ) as response:
                if response.status == 201:
                    data = await response.json()
                    self.user_data = data
                    self.log_result(
                        "User Registration",
                        True,
                        f"User registered: {test_user['email']}",
                    )
                    return True
                else:
                    error_text = await response.text()
                    self.log_result(
                        "User Registration",
                        False,
                        f"Registration failed with status {response.status}",
                        error_text,
                    )
                    return False

        except Exception as e:
            self.log_result(
                "User Registration", False, "Registration request failed", str(e)
            )
            return False

    async def test_user_login_flow(self):
        """Test user login and token acquisition."""
        print("\n🔑 Testing User Login Flow")

        if not hasattr(self, "test_username"):
            self.log_result("User Login", False, "No username available for login")
            return False

        login_data = {"username": self.test_username, "password": "DashTest123!"}

        try:
            # Use form data for OAuth2 login
            async with self.session.post(
                f"{API_BASE}/auth/login",
                data=login_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data.get("access_token")
                    self.log_result(
                        "User Login", True, "Login successful, token acquired"
                    )
                    return True
                else:
                    error_text = await response.text()
                    self.log_result(
                        "User Login",
                        False,
                        f"Login failed with status {response.status}",
                        error_text,
                    )
                    return False

        except Exception as e:
            self.log_result("User Login", False, "Login request failed", str(e))
            return False

    async def test_analytics_dashboard_access(self):
        """Test analytics dashboard API access."""
        print("\n📊 Testing Analytics Dashboard Access")

        if not self.auth_token:
            self.log_result("Analytics Dashboard", False, "No auth token available")
            return False

        headers = {"Authorization": f"Bearer {self.auth_token}"}

        try:
            async with self.session.get(
                f"{API_BASE}/analytics/dashboard", headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    # Check for key dashboard components
                    components = []
                    if "subscription" in data:
                        components.append("Subscription Info")
                    if "usage_metrics" in data:
                        components.append("Usage Metrics")
                    if "upgrade_opportunities" in data:
                        components.append("Upgrade Opportunities")
                    if "success_metrics" in data:
                        components.append("Success Metrics")
                    if "roi_calculation" in data:
                        components.append("ROI Calculator")

                    self.log_result(
                        "Analytics Dashboard",
                        True,
                        f"Dashboard data loaded with components: {', '.join(components)}",
                    )
                    return data
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Analytics Dashboard",
                        False,
                        f"Dashboard access failed with status {response.status}",
                        error_text,
                    )
                    return None

        except Exception as e:
            self.log_result(
                "Analytics Dashboard", False, "Dashboard request failed", str(e)
            )
            return None

    async def test_usage_metrics_api(self):
        """Test usage metrics API endpoint."""
        print("\n📈 Testing Usage Metrics API")

        if not self.auth_token:
            self.log_result("Usage Metrics", False, "No auth token available")
            return False

        headers = {"Authorization": f"Bearer {self.auth_token}"}

        try:
            async with self.session.get(
                f"{API_BASE}/analytics/usage", headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    # Check for usage metrics structure
                    metrics = []
                    if "parses_used" in data:
                        metrics.append(f"Parses: {data['parses_used']}")
                    if "plans_used" in data:
                        metrics.append(f"Plans: {data['plans_used']}")
                    if "executions_used" in data:
                        metrics.append(f"Executions: {data['executions_used']}")

                    self.log_result(
                        "Usage Metrics",
                        True,
                        f"Usage data: {', '.join(metrics) if metrics else 'Empty metrics'}",
                    )
                    return True
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Usage Metrics",
                        False,
                        f"Metrics access failed with status {response.status}",
                        error_text,
                    )
                    return False

        except Exception as e:
            self.log_result("Usage Metrics", False, "Metrics request failed", str(e))
            return False

    async def test_upgrade_opportunities_api(self):
        """Test upgrade opportunities API endpoint."""
        print("\n🚀 Testing Upgrade Opportunities API")

        if not self.auth_token:
            self.log_result("Upgrade Opportunities", False, "No auth token available")
            return False

        headers = {"Authorization": f"Bearer {self.auth_token}"}

        try:
            async with self.session.get(
                f"{API_BASE}/analytics/upgrade-opportunities", headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    if isinstance(data, list):
                        self.log_result(
                            "Upgrade Opportunities",
                            True,
                            f"Found {len(data)} upgrade opportunities",
                        )
                    else:
                        self.log_result(
                            "Upgrade Opportunities",
                            True,
                            "Upgrade opportunities data loaded",
                        )
                    return True
                else:
                    error_text = await response.text()
                    self.log_result(
                        "Upgrade Opportunities",
                        False,
                        f"Upgrade opportunities failed with status {response.status}",
                        error_text,
                    )
                    return False

        except Exception as e:
            self.log_result(
                "Upgrade Opportunities",
                False,
                "Upgrade opportunities request failed",
                str(e),
            )
            return False

    async def test_complete_dashboard_workflow(self):
        """Test complete dashboard workflow simulation."""
        print("\n🎯 Testing Complete Dashboard Workflow")

        workflow_success = True

        # Step 1: Registration
        if not await self.test_user_registration_flow():
            workflow_success = False

        # Step 2: Login (if registration succeeded)
        if workflow_success and not await self.test_user_login_flow():
            workflow_success = False

        # Step 3: Dashboard access
        if workflow_success:
            dashboard_data = await self.test_analytics_dashboard_access()
            if not dashboard_data:
                workflow_success = False

        # Step 4: Usage metrics
        if workflow_success and not await self.test_usage_metrics_api():
            workflow_success = False

        # Step 5: Upgrade opportunities
        if workflow_success and not await self.test_upgrade_opportunities_api():
            workflow_success = False

        self.log_result(
            "Complete Dashboard Workflow",
            workflow_success,
            (
                "Full user workflow completed successfully"
                if workflow_success
                else "Workflow had failures"
            ),
        )

        return workflow_success

    async def run_all_tests(self):
        """Run all dashboard flow tests."""
        print("🚀 Starting WebAgent Dashboard Flow Testing")
        print("=" * 60)
        print(f"Backend: {BACKEND_URL}")
        print(f"Frontend: {FRONTEND_URL}")
        print(f"Timestamp: {datetime.now().isoformat()}")

        # Run complete workflow test
        await self.test_complete_dashboard_workflow()

        # Generate summary
        print("\n📊 Test Results Summary")
        print("=" * 60)

        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests

        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(
            f"Success Rate: {(passed_tests / total_tests * 100):.1f}%"
            if total_tests > 0
            else "0%"
        )

        # Save detailed results
        with open("dashboard_flow_results.json", "w") as f:
            json.dump(
                {
                    "summary": {
                        "total": total_tests,
                        "passed": passed_tests,
                        "failed": failed_tests,
                        "success_rate": (
                            (passed_tests / total_tests * 100) if total_tests > 0 else 0
                        ),
                    },
                    "results": self.test_results,
                    "timestamp": datetime.now().isoformat(),
                },
                f,
                indent=2,
            )

        print("\n💾 Detailed results saved to: dashboard_flow_results.json")

        return passed_tests == total_tests


async def main():
    """Main test function."""
    async with DashboardFlowTester() as tester:
        success = await tester.run_all_tests()

        if success:
            print("\n✅ All dashboard flow tests passed!")
            return 0
        else:
            print("\n❌ Some dashboard flow tests failed!")
            return 1


if __name__ == "__main__":
    import sys

    result = asyncio.run(main())
    sys.exit(result)
