#!/usr/bin/env python3
"""
Quick Validation Script for WebAgent
Runs essential checks before commit without the full pre-commit suite
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"🔍 {description}...")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=Path(__file__).parent
        )

        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False


def main():
    """Run quick validation checks."""
    print("🚀 WebAgent Quick Validation")
    print("=" * 50)

    checks = [
        # Basic Python syntax check
        ("python -m py_compile app/main.py", "Python syntax check"),
        # Import check
        ("python -c \"import app.main; print('App imports OK')\"", "Import validation"),
        # Black formatting check
        ("python -m black app/ tests/ --check --quiet", "Code formatting (Black)"),
        # Basic file checks
        (
            "python -c \"import os; assert os.path.exists('app/main.py'), 'Main app file missing'\"",
            "File structure check",
        ),
        # Database models import
        (
            "python -c \"from app.models.user import User; print('Models import OK')\"",
            "Database models check",
        ),
        # API endpoints import
        (
            "python -c \"from app.api.v1.router import api_router; print('API router OK')\"",
            "API endpoints check",
        ),
    ]

    passed = 0
    total = len(checks)

    for cmd, description in checks:
        if run_command(cmd, description):
            passed += 1
        print()

    print("=" * 50)
    print(f"📊 Results: {passed}/{total} checks passed")

    if passed == total:
        print("🎉 All essential checks PASSED! Ready for commit.")
        return 0
    else:
        print("⚠️  Some checks FAILED. Please fix issues before committing.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
