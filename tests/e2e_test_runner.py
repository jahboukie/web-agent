"""
E2E Test Runner for WebAgent
Comprehensive test execution with reporting and monitoring integration
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import get_logger

logger = get_logger(__name__)


class E2ETestRunner:
    """Comprehensive E2E test runner with enterprise features."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        self.reports_dir = Path("tests/reports")
        self.reports_dir.mkdir(exist_ok=True)

    async def run_test_suite(self, test_categories: list[str] = None) -> dict[str, Any]:
        """
        Run comprehensive E2E test suite.

        Args:
            test_categories: Specific test categories to run, or None for all

        Returns:
            Test execution summary with metrics
        """
        self.start_time = datetime.utcnow()
        logger.info("Starting E2E test suite execution", categories=test_categories)

        # Define test categories and their priorities
        all_test_categories = {
            "core_functionality": {
                "priority": 1,
                "tests": [
                    "tests/e2e/test_agent_execution_flow.py",
                ],
                "timeout": 1800,  # 30 minutes
                "critical": True,
            },
            "subscription_billing": {
                "priority": 2,
                "tests": [
                    "tests/e2e/test_subscription_billing.py",
                ],
                "timeout": 900,  # 15 minutes
                "critical": True,
            },
            "enterprise_security": {
                "priority": 1,
                "tests": [
                    "tests/e2e/test_enterprise_security.py",
                ],
                "timeout": 1200,  # 20 minutes
                "critical": True,
            },
            "authentication_security": {
                "priority": 1,
                "tests": [
                    "tests/e2e/test_authentication_security.py",
                ],
                "timeout": 900,  # 15 minutes
                "critical": True,
            },
            "performance_load": {
                "priority": 3,
                "tests": [
                    "tests/e2e/test_performance_load.py",
                ],
                "timeout": 3600,  # 60 minutes
                "critical": False,
            },
        }

        # Filter test categories if specified
        if test_categories:
            test_categories_to_run = {
                k: v for k, v in all_test_categories.items() if k in test_categories
            }
        else:
            test_categories_to_run = all_test_categories

        # Sort by priority
        sorted_categories = sorted(
            test_categories_to_run.items(), key=lambda x: x[1]["priority"]
        )

        # Execute test categories
        for category_name, category_config in sorted_categories:
            logger.info(f"Executing test category: {category_name}")

            category_result = await self._run_test_category(
                category_name, category_config
            )

            self.test_results[category_name] = category_result

            # Stop execution if critical test fails
            if category_config["critical"] and not category_result["success"]:
                logger.error(
                    f"Critical test category '{category_name}' failed, stopping execution"
                )
                break

        self.end_time = datetime.utcnow()

        # Generate comprehensive report
        summary = await self._generate_test_summary()
        await self._save_test_report(summary)

        return summary

    async def _run_test_category(
        self, category_name: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Run a specific test category."""
        start_time = datetime.utcnow()

        # Prepare pytest command
        pytest_args = [
            "python",
            "-m",
            "pytest",
            "-v",
            "--tb=short",
            "--json-report",
            f"--json-report-file=tests/reports/{category_name}_report.json",
            "--html=tests/reports/{category_name}_report.html",
            "--self-contained-html",
            f"--timeout={config['timeout']}",
            "-m",
            "e2e",
        ]

        # Add test files
        pytest_args.extend(config["tests"])

        # Add markers for specific test types
        if category_name == "performance_load":
            pytest_args.extend(["-m", "slow"])

        try:
            # Execute pytest
            process = await asyncio.create_subprocess_exec(
                *pytest_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path(__file__).parent.parent,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=config["timeout"]
            )

            # Parse results
            return_code = process.returncode

            # Load JSON report if available
            json_report_path = Path(f"tests/reports/{category_name}_report.json")
            if json_report_path.exists():
                with open(json_report_path) as f:
                    json_report = json.load(f)
            else:
                json_report = {}

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            return {
                "success": return_code == 0,
                "return_code": return_code,
                "duration_seconds": duration,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "json_report": json_report,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            }

        except TimeoutError:
            logger.error(
                f"Test category '{category_name}' timed out after {config['timeout']}s"
            )
            return {
                "success": False,
                "return_code": -1,
                "duration_seconds": config["timeout"],
                "error": "Test execution timed out",
                "start_time": start_time.isoformat(),
                "end_time": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error executing test category '{category_name}': {e}")
            return {
                "success": False,
                "return_code": -1,
                "duration_seconds": (datetime.utcnow() - start_time).total_seconds(),
                "error": str(e),
                "start_time": start_time.isoformat(),
                "end_time": datetime.utcnow().isoformat(),
            }

    async def _generate_test_summary(self) -> dict[str, Any]:
        """Generate comprehensive test execution summary."""
        total_duration = (self.end_time - self.start_time).total_seconds()

        # Calculate overall metrics
        total_categories = len(self.test_results)
        successful_categories = sum(
            1 for r in self.test_results.values() if r["success"]
        )
        failed_categories = total_categories - successful_categories

        # Extract test metrics from JSON reports
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0

        for category_result in self.test_results.values():
            json_report = category_result.get("json_report", {})
            summary = json_report.get("summary", {})

            total_tests += summary.get("total", 0)
            passed_tests += summary.get("passed", 0)
            failed_tests += summary.get("failed", 0)
            skipped_tests += summary.get("skipped", 0)

        # Calculate success rates
        category_success_rate = (
            successful_categories / total_categories if total_categories > 0 else 0
        )
        test_success_rate = passed_tests / total_tests if total_tests > 0 else 0

        # Identify critical failures
        critical_failures = []
        for category_name, result in self.test_results.items():
            if not result["success"]:
                critical_failures.append(
                    {
                        "category": category_name,
                        "error": result.get("error", "Unknown error"),
                        "return_code": result.get("return_code", -1),
                    }
                )

        return {
            "execution_summary": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "total_duration_seconds": total_duration,
                "total_duration_formatted": str(timedelta(seconds=int(total_duration))),
            },
            "category_metrics": {
                "total_categories": total_categories,
                "successful_categories": successful_categories,
                "failed_categories": failed_categories,
                "category_success_rate": category_success_rate,
            },
            "test_metrics": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "skipped_tests": skipped_tests,
                "test_success_rate": test_success_rate,
            },
            "critical_metrics": {
                "false_positive_rate": 0.0,  # Would be calculated from known issues
                "critical_defect_escape_rate": len(critical_failures)
                / total_categories,
                "mean_time_to_failure_detection": total_duration
                / max(failed_categories, 1),
            },
            "category_results": self.test_results,
            "critical_failures": critical_failures,
            "overall_success": len(critical_failures) == 0
            and category_success_rate >= 0.95,
        }

    async def _save_test_report(self, summary: dict[str, Any]) -> None:
        """Save comprehensive test report."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Save JSON report
        json_report_path = self.reports_dir / f"e2e_test_report_{timestamp}.json"
        with open(json_report_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        # Generate HTML report
        html_report = self._generate_html_report(summary)
        html_report_path = self.reports_dir / f"e2e_test_report_{timestamp}.html"
        with open(html_report_path, "w") as f:
            f.write(html_report)

        logger.info(f"Test reports saved: {json_report_path}, {html_report_path}")

    def _generate_html_report(self, summary: dict[str, Any]) -> str:
        """Generate HTML test report."""
        # Simple HTML report template
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>WebAgent E2E Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .success {{ color: green; }}
                .failure {{ color: red; }}
                .metrics {{ display: flex; gap: 20px; margin: 20px 0; }}
                .metric-card {{ border: 1px solid #ddd; padding: 15px; border-radius: 5px; flex: 1; }}
                .category-result {{ margin: 10px 0; padding: 10px; border-left: 4px solid #ddd; }}
                .category-success {{ border-left-color: green; }}
                .category-failure {{ border-left-color: red; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>WebAgent E2E Test Report</h1>
                <p>Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
                <p class="{"success" if summary["overall_success"] else "failure"}">
                    Overall Status: {"PASS" if summary["overall_success"] else "FAIL"}
                </p>
            </div>

            <div class="metrics">
                <div class="metric-card">
                    <h3>Execution Time</h3>
                    <p>{summary["execution_summary"]["total_duration_formatted"]}</p>
                </div>
                <div class="metric-card">
                    <h3>Category Success Rate</h3>
                    <p>{summary["category_metrics"]["category_success_rate"]:.1%}</p>
                </div>
                <div class="metric-card">
                    <h3>Test Success Rate</h3>
                    <p>{summary["test_metrics"]["test_success_rate"]:.1%}</p>
                </div>
                <div class="metric-card">
                    <h3>Critical Failures</h3>
                    <p>{len(summary["critical_failures"])}</p>
                </div>
            </div>

            <h2>Category Results</h2>
        """

        for category_name, result in summary["category_results"].items():
            status_class = (
                "category-success" if result["success"] else "category-failure"
            )
            status_text = "PASS" if result["success"] else "FAIL"

            html += f"""
            <div class="category-result {status_class}">
                <h3>{category_name.replace("_", " ").title()} - {status_text}</h3>
                <p>Duration: {result["duration_seconds"]:.1f}s</p>
                {f"<p>Error: {result.get('error', 'N/A')}</p>" if not result["success"] else ""}
            </div>
            """

        html += """
            </body>
        </html>
        """

        return html


async def main():
    """Main entry point for E2E test runner."""
    parser = argparse.ArgumentParser(description="WebAgent E2E Test Runner")
    parser.add_argument(
        "--categories",
        nargs="*",
        help="Specific test categories to run",
        choices=[
            "core_functionality",
            "subscription_billing",
            "enterprise_security",
            "authentication_security",
            "performance_load",
        ],
    )
    parser.add_argument(
        "--config", default="tests/e2e_config.json", help="Test configuration file path"
    )

    args = parser.parse_args()

    # Load configuration
    config_path = Path(args.config)
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {
            "environment": "test",
            "parallel_execution": False,
            "generate_reports": True,
            "send_notifications": False,
        }

    # Initialize and run test suite
    runner = E2ETestRunner(config)

    try:
        summary = await runner.run_test_suite(args.categories)

        # Print summary
        print("\n" + "=" * 80)
        print("E2E TEST EXECUTION SUMMARY")
        print("=" * 80)
        print(f"Overall Status: {'PASS' if summary['overall_success'] else 'FAIL'}")
        print(
            f"Total Duration: {summary['execution_summary']['total_duration_formatted']}"
        )
        print(
            f"Categories: {summary['category_metrics']['successful_categories']}/{summary['category_metrics']['total_categories']} passed"
        )
        print(
            f"Tests: {summary['test_metrics']['passed_tests']}/{summary['test_metrics']['total_tests']} passed"
        )
        print(f"Success Rate: {summary['test_metrics']['test_success_rate']:.1%}")

        if summary["critical_failures"]:
            print("\nCRITICAL FAILURES:")
            for failure in summary["critical_failures"]:
                print(f"  - {failure['category']}: {failure['error']}")

        print("=" * 80)

        # Exit with appropriate code
        sys.exit(0 if summary["overall_success"] else 1)

    except Exception as e:
        logger.error(f"E2E test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
