#!/usr/bin/env python3
"""
Simple endpoint testing script to verify API fixes.
Uses only standard library - no external dependencies.
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BACKEND_URL = "http://127.0.0.1:8000"
API_BASE = f"{BACKEND_URL}/api/v1"


def test_endpoint(method, url, data=None, expected_statuses=None):
    """Test an API endpoint."""
    if expected_statuses is None:
        expected_statuses = [200, 401, 422]

    try:
        if method == "GET":
            req = urllib.request.Request(url)
        elif method == "POST":
            json_data = json.dumps(data).encode("utf-8") if data else b""
            req = urllib.request.Request(url, data=json_data)
            req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.getcode()
            return status in expected_statuses, status, None

    except urllib.error.HTTPError as e:
        status = e.code
        return status in expected_statuses, status, str(e)
    except Exception as e:
        return False, 0, str(e)


def main():
    """Run endpoint tests."""
    print("🧪 Testing API Endpoints After Fixes")
    print("=" * 50)

    tests = [
        # GET endpoints
        ("GET", f"{BACKEND_URL}/docs", None, [200], "API Documentation"),
        (
            "GET",
            f"{API_BASE}/analytics/dashboard",
            None,
            [401, 422],
            "Analytics Dashboard",
        ),
        ("GET", f"{API_BASE}/tasks", None, [401, 422], "Tasks Endpoint"),
        ("GET", f"{API_BASE}/web-pages/active", None, [401, 422], "Web Pages Active"),
        # POST endpoints
        (
            "POST",
            f"{API_BASE}/auth/register",
            {
                "email": "test_validation@webagent.com",
                "password": "TestPass123!",
                "full_name": "Validation Test User",
            },
            [201, 400, 409, 422],
            "Auth Registration",
        ),
    ]

    results = []

    for method, url, data, expected_statuses, description in tests:
        print(f"Testing {description}...")

        success, status, error = test_endpoint(method, url, data, expected_statuses)

        if success:
            print(f"  ✅ PASS - HTTP {status}")
            results.append(("PASS", description, status))
        else:
            print(f"  ❌ FAIL - HTTP {status} - {error}")
            results.append(("FAIL", description, status))

    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")

    passed = len([r for r in results if r[0] == "PASS"])
    failed = len([r for r in results if r[0] == "FAIL"])
    total = len(results)

    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Ready for deployment!")
        return 0
    else:
        print(f"\n⚠️  {failed} tests still failing")
        return 1


if __name__ == "__main__":
    sys.exit(main())
