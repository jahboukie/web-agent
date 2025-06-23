#!/usr/bin/env python3
"""
Test script to validate dependency resolution
"""

import subprocess
import sys


def test_poetry_lock():
    """Test if Poetry can resolve dependencies without conflicts."""
    print("🔍 Testing Poetry dependency resolution...")

    try:
        # Run poetry lock --check to see if lock file is consistent
        result = subprocess.run(
            ["poetry", "lock", "--check"], capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            print("✅ Poetry lock file is consistent")
            return True
        else:
            print("⚠️ Poetry lock file needs updating")
            print(f"Output: {result.stdout}")
            print(f"Error: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("⏰ Poetry lock check timed out")
        return False
    except Exception as e:
        print(f"❌ Error checking Poetry lock: {e}")
        return False


def test_dependency_resolution():
    """Test if Poetry can resolve dependencies."""
    print("🔍 Testing dependency resolution (dry run)...")

    try:
        # Run poetry install --dry-run to test resolution without installing
        result = subprocess.run(
            ["poetry", "install", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            print("✅ Dependencies can be resolved successfully")
            return True
        else:
            print("❌ Dependency resolution failed")
            print(f"Error: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("⏰ Dependency resolution timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing dependency resolution: {e}")
        return False


def main():
    """Run dependency validation tests."""
    print("🚀 WebAgent Dependency Validation")
    print("=" * 50)

    # Check if Poetry is available
    try:
        result = subprocess.run(
            ["poetry", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            print("❌ Poetry is not available")
            return 1
        print(f"✅ Poetry found: {result.stdout.strip()}")
    except Exception as e:
        print(f"❌ Poetry not found: {e}")
        return 1

    print()

    # Test dependency resolution
    tests = [
        ("Dependency Resolution", test_dependency_resolution),
        ("Lock File Check", test_poetry_lock),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"Running: {test_name}")
        if test_func():
            passed += 1
        print()

    print("=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All dependency tests PASSED! Ready for CI/CD.")
        return 0
    else:
        print("⚠️ Some dependency tests FAILED.")
        print("\n💡 Quick fixes:")
        print("1. Run: poetry lock --no-update")
        print("2. Run: poetry install")
        print("3. Commit the updated poetry.lock file")
        return 1


if __name__ == "__main__":
    sys.exit(main())
