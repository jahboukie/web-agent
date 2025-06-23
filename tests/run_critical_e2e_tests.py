#!/usr/bin/env python3
"""
WebAgent Critical E2E Test Execution Script
Enterprise-grade test execution with comprehensive reporting

Usage:
    python tests/run_critical_e2e_tests.py --suite critical_path
    python tests/run_critical_e2e_tests.py --suite all --parallel --include-load
    python tests/run_critical_e2e_tests.py --suite security --generate-report
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.e2e_comprehensive_runner import WebAgentE2ERunner


class CriticalE2ETestExecutor:
    """Execute critical E2E tests with enterprise reporting."""

    def __init__(self):
        self.test_suites = {
            "critical_path": {
                "description": "[CRITICAL] Core functionality that must work",
                "tests": [
                    "tests/e2e/test_agent_execution_critical.py",
                    "tests/e2e/test_subscription_billing_critical.py::TestSubscriptionBillingCritical::test_free_tier_feature_gating_comprehensive",
                ],
                "timeout_minutes": 30,
                "required_success_rate": 100.0,
            },
            "security": {
                "description": "🔒 Security and compliance validation",
                "tests": ["tests/e2e/test_security_compliance_critical.py"],
                "timeout_minutes": 45,
                "required_success_rate": 100.0,
            },
            "performance": {
                "description": "⚡ Performance and scalability tests",
                "tests": ["tests/e2e/test_performance_load_critical.py"],
                "timeout_minutes": 60,
                "required_success_rate": 90.0,
            },
            "billing": {
                "description": "💰 Revenue-critical billing and subscription tests",
                "tests": ["tests/e2e/test_subscription_billing_critical.py"],
                "timeout_minutes": 30,
                "required_success_rate": 100.0,
            },
            "all": {
                "description": "[COMPLETE] Complete test suite",
                "tests": "all",
                "timeout_minutes": 120,
                "required_success_rate": 95.0,
            },
        }

    async def execute_test_suite(
        self,
        suite_name: str,
        parallel: bool = True,
        generate_report: bool = True,
        include_load: bool = False,
        verbose: bool = True,
    ) -> dict[str, Any]:
        """Execute specified test suite with comprehensive reporting."""

        if suite_name not in self.test_suites:
            raise ValueError(
                f"Unknown test suite: {suite_name}. Available: {list(self.test_suites.keys())}"
            )

        suite_config = self.test_suites[suite_name]

        print(f"\n>> Starting WebAgent E2E Test Suite: {suite_name}")
        print(f"-- {suite_config['description']}")
        print(f"** Timeout: {suite_config['timeout_minutes']} minutes")
        print(f"** Required Success Rate: {suite_config['required_success_rate']}%")
        print("=" * 80)

        start_time = datetime.now()

        try:
            if suite_name == "all":
                # Use comprehensive runner for full suite
                runner = WebAgentE2ERunner()
                results = await runner.run_comprehensive_tests(
                    categories=["critical_path", "security", "performance", "billing"],
                    parallel=parallel,
                    include_load=include_load,
                )

                return {
                    "suite_name": suite_name,
                    "success": results.success_rate
                    >= suite_config["required_success_rate"],
                    "metrics": results,
                    "duration": (datetime.now() - start_time).total_seconds(),
                }

            else:
                # Execute specific test suite
                results = await self._execute_pytest_suite(
                    suite_config, parallel, verbose, include_load
                )

                return {
                    "suite_name": suite_name,
                    "success": results["success_rate"]
                    >= suite_config["required_success_rate"],
                    "results": results,
                    "duration": (datetime.now() - start_time).total_seconds(),
                }

        except Exception as e:
            return {
                "suite_name": suite_name,
                "success": False,
                "error": str(e),
                "duration": (datetime.now() - start_time).total_seconds(),
            }

    async def _execute_pytest_suite(
        self, suite_config: dict, parallel: bool, verbose: bool, include_load: bool
    ) -> dict[str, Any]:
        """Execute pytest test suite with proper configuration."""

        # Create artifacts directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        artifacts_dir = Path(f"tests/artifacts/critical_e2e_{timestamp}")
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Build pytest command
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            *suite_config["tests"],
            "-v" if verbose else "",
            "--tb=short",
            f"--html={artifacts_dir}/report.html",
            f"--json-report={artifacts_dir}/report.json",
            "--json-report-summary",
            f"--junit-xml={artifacts_dir}/junit.xml",
            "--capture=no" if verbose else "--capture=sys",
        ]

        # Add parallel execution
        if parallel:
            cmd.extend(["-n", "auto"])

        # Add performance flags for load tests
        if include_load:
            cmd.extend(["-m", "performance or critical"])
        else:
            cmd.extend(["-m", "critical"])

        # Add timeout
        cmd.extend(["--timeout", str(suite_config["timeout_minutes"] * 60)])

        # Remove empty strings
        cmd = [arg for arg in cmd if arg]

        print(f">> Executing: {' '.join(cmd)}")

        # Execute tests
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path(__file__).parent.parent,
            )

            stdout, stderr = await process.communicate()

            # Parse results
            results = await self._parse_test_results(artifacts_dir, process.returncode)

            if stdout:
                print("-- Test Output:")
                print(stdout.decode())

            if stderr and process.returncode != 0:
                print("!! Test Errors:")
                print(stderr.decode())

            return results

        except Exception as e:
            return {
                "success_rate": 0.0,
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "error": str(e),
            }

    async def _parse_test_results(
        self, artifacts_dir: Path, return_code: int
    ) -> dict[str, Any]:
        """Parse test results from JSON report."""

        json_report_path = artifacts_dir / "report.json"

        if json_report_path.exists():
            try:
                with open(json_report_path) as f:
                    report_data = json.load(f)

                summary = report_data.get("summary", {})

                return {
                    "success_rate": (
                        summary.get("passed", 0) / max(summary.get("total", 1), 1)
                    )
                    * 100,
                    "total_tests": summary.get("total", 0),
                    "passed_tests": summary.get("passed", 0),
                    "failed_tests": summary.get("failed", 0),
                    "skipped_tests": summary.get("skipped", 0),
                    "error_tests": summary.get("error", 0),
                    "duration_seconds": summary.get("duration", 0),
                    "return_code": return_code,
                    "artifacts_dir": str(artifacts_dir),
                }

            except Exception as e:
                print(f"!! Failed to parse JSON report: {e}")

        # Fallback based on return code
        return {
            "success_rate": 100.0 if return_code == 0 else 0.0,
            "total_tests": 1,
            "passed_tests": 1 if return_code == 0 else 0,
            "failed_tests": 0 if return_code == 0 else 1,
            "return_code": return_code,
            "artifacts_dir": str(artifacts_dir),
        }

    def print_results_summary(self, results: dict[str, Any]):
        """Print comprehensive test results summary."""

        print("\n" + "=" * 80)
        print("== WebAgent E2E Test Results Summary ==")
        print("=" * 80)

        if results["success"]:
            print("[PASS] OVERALL STATUS: PASSED")
        else:
            print("[FAIL] OVERALL STATUS: FAILED")

        print(f"-- Suite: {results['suite_name']}")
        print(f"** Duration: {results['duration']:.1f} seconds")

        if "results" in results:
            test_results = results["results"]
            print(f"** Success Rate: {test_results['success_rate']:.1f}%")
            print(f"🧪 Total Tests: {test_results['total_tests']}")
            print(f"[PASS] Passed: {test_results['passed_tests']}")
            print(f"[FAIL] Failed: {test_results['failed_tests']}")
            print(f"[SKIP] Skipped: {test_results.get('skipped_tests', 0)}")

            if test_results.get("artifacts_dir"):
                print(f"📁 Artifacts: {test_results['artifacts_dir']}")

        elif "metrics" in results:
            metrics = results["metrics"]
            print(f"** Success Rate: {metrics.success_rate:.1f}%")
            print(f"🧪 Total Tests: {metrics.total_tests}")
            print(f"[PASS] Passed: {metrics.passed_tests}")
            print(f"[FAIL] Failed: {metrics.failed_tests}")

        if "error" in results:
            print(f"[ERROR] Error: {results['error']}")

        print("=" * 80)


async def main():
    """Main entry point for critical E2E test execution."""

    parser = argparse.ArgumentParser(
        description="WebAgent Critical E2E Test Execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Suites:
  critical_path  - Core functionality tests (Reader → Planner → Actor)
  security      - Security and compliance validation
  performance   - Performance and scalability tests
  billing       - Revenue-critical billing tests
  all          - Complete test suite

Examples:
  python tests/run_critical_e2e_tests.py --suite critical_path
  python tests/run_critical_e2e_tests.py --suite all --parallel --include-load
  python tests/run_critical_e2e_tests.py --suite security --verbose
        """,
    )

    parser.add_argument(
        "--suite",
        choices=["critical_path", "security", "performance", "billing", "all"],
        default="critical_path",
        help="Test suite to execute",
    )

    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")

    parser.add_argument(
        "--include-load", action="store_true", help="Include load/performance tests"
    )

    parser.add_argument(
        "--generate-report",
        action="store_true",
        default=True,
        help="Generate comprehensive test report",
    )

    parser.add_argument("--verbose", action="store_true", help="Verbose test output")

    args = parser.parse_args()

    # Initialize test executor
    executor = CriticalE2ETestExecutor()

    try:
        # Execute test suite
        results = await executor.execute_test_suite(
            suite_name=args.suite,
            parallel=args.parallel,
            generate_report=args.generate_report,
            include_load=args.include_load,
            verbose=args.verbose,
        )

        # Print results
        executor.print_results_summary(results)

        # Exit with appropriate code
        exit_code = 0 if results["success"] else 1
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n!! Test execution interrupted by user")
        sys.exit(130)

    except Exception as e:
        print(f"\n[ERROR] Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
