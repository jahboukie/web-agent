"""
Automated Dependency Vulnerability Scanner

Automated scanning of Python dependencies for known security vulnerabilities
using multiple security databases and advisory sources.
"""

import asyncio
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import aiohttp
import pkg_resources

from app.core.logging import get_logger

logger = get_logger(__name__)


class VulnerabilitySeverity(str, Enum):
    """Vulnerability severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class Vulnerability:
    """Security vulnerability information."""

    id: str
    package_name: str
    installed_version: str
    affected_versions: list[str]
    fixed_versions: list[str]
    severity: VulnerabilitySeverity
    title: str
    description: str
    references: list[str] = field(default_factory=list)
    cvss_score: float | None = None
    cwe_ids: list[str] = field(default_factory=list)
    published_date: datetime | None = None
    source: str = "unknown"


@dataclass
class PackageInfo:
    """Package information."""

    name: str
    version: str
    location: str
    dependencies: list[str] = field(default_factory=list)
    is_editable: bool = False
    license: str | None = None


@dataclass
class ScanResult:
    """Vulnerability scan result."""

    scan_id: str
    timestamp: datetime
    packages_scanned: int
    vulnerabilities_found: int
    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    scan_duration: float = 0.0
    errors: list[str] = field(default_factory=list)

    def get_by_severity(self, severity: VulnerabilitySeverity) -> list[Vulnerability]:
        """Get vulnerabilities by severity level."""
        return [v for v in self.vulnerabilities if v.severity == severity]

    def get_critical_count(self) -> int:
        """Get count of critical vulnerabilities."""
        return len(self.get_by_severity(VulnerabilitySeverity.CRITICAL))

    def get_high_count(self) -> int:
        """Get count of high vulnerabilities."""
        return len(self.get_by_severity(VulnerabilitySeverity.HIGH))


class PyUpSecurityDB:
    """PyUp.io Security Database scanner."""

    def __init__(self):
        self.api_url = "https://pyup.io/api/v1/vulnerabilities/"
        self.timeout = 30

    async def scan_packages(self, packages: list[PackageInfo]) -> list[Vulnerability]:
        """Scan packages against PyUp security database."""
        vulnerabilities = []

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                for package in packages:
                    try:
                        url = f"{self.api_url}{package.name}/"
                        async with session.get(url) as response:
                            if response.status == 200:
                                data = await response.json()

                                for vuln_data in data:
                                    # Check if installed version is affected
                                    if self._is_version_affected(
                                        package.version,
                                        vuln_data.get("affected_versions", []),
                                    ):
                                        vulnerability = Vulnerability(
                                            id=vuln_data.get("id", "unknown"),
                                            package_name=package.name,
                                            installed_version=package.version,
                                            affected_versions=vuln_data.get(
                                                "affected_versions", []
                                            ),
                                            fixed_versions=vuln_data.get(
                                                "fixed_versions", []
                                            ),
                                            severity=self._map_severity(
                                                vuln_data.get("severity", "unknown")
                                            ),
                                            title=vuln_data.get(
                                                "title", "Unknown vulnerability"
                                            ),
                                            description=vuln_data.get(
                                                "description", ""
                                            ),
                                            references=vuln_data.get("references", []),
                                            cvss_score=vuln_data.get("cvss_score"),
                                            published_date=self._parse_date(
                                                vuln_data.get("published_date")
                                            ),
                                            source="pyup.io",
                                        )
                                        vulnerabilities.append(vulnerability)

                    except Exception as e:
                        logger.warning(
                            f"Failed to check {package.name} against PyUp: {str(e)}"
                        )
                        continue

        except Exception as e:
            logger.error(f"PyUp scanner failed: {str(e)}")

        return vulnerabilities

    def _is_version_affected(
        self, installed_version: str, affected_versions: list[str]
    ) -> bool:
        """Check if installed version is in affected versions."""
        try:
            # This is a simplified version comparison
            # In production, use packaging.version for proper version comparison
            return installed_version in affected_versions
        except Exception:
            return False

    def _map_severity(self, severity: str) -> VulnerabilitySeverity:
        """Map severity string to enum."""
        severity_map = {
            "critical": VulnerabilitySeverity.CRITICAL,
            "high": VulnerabilitySeverity.HIGH,
            "medium": VulnerabilitySeverity.MEDIUM,
            "low": VulnerabilitySeverity.LOW,
        }
        return severity_map.get(severity.lower(), VulnerabilitySeverity.UNKNOWN)

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """Parse date string to datetime."""
        if not date_str:
            return None

        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None


class SafetyScanner:
    """Safety CLI scanner wrapper."""

    def __init__(self):
        self.timeout = 60

    async def scan_packages(self, packages: list[PackageInfo]) -> list[Vulnerability]:
        """Scan packages using Safety CLI."""
        vulnerabilities = []

        try:
            # Run safety check
            result = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "safety",
                "check",
                "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                result.communicate(), timeout=self.timeout
            )

            if result.returncode == 0:
                # No vulnerabilities found
                return []

            # Parse JSON output
            if stdout:
                safety_data = json.loads(stdout.decode())

                for vuln_data in safety_data:
                    vulnerability = Vulnerability(
                        id=vuln_data.get("id", "unknown"),
                        package_name=vuln_data.get("package", "unknown"),
                        installed_version=vuln_data.get("installed_version", "unknown"),
                        affected_versions=vuln_data.get("affected_versions", []),
                        fixed_versions=[],  # Safety doesn't provide this
                        severity=self._map_severity(
                            vuln_data.get("severity", "unknown")
                        ),
                        title=vuln_data.get("advisory", "Security vulnerability"),
                        description=vuln_data.get("advisory", ""),
                        references=[],
                        source="safety",
                    )
                    vulnerabilities.append(vulnerability)

        except TimeoutError:
            logger.error("Safety scanner timed out")
        except FileNotFoundError:
            logger.warning("Safety CLI not installed, skipping safety scan")
        except Exception as e:
            logger.error(f"Safety scanner failed: {str(e)}")

        return vulnerabilities

    def _map_severity(self, severity: str) -> VulnerabilitySeverity:
        """Map severity to enum."""
        # Safety doesn't provide severity, so we default to medium
        return VulnerabilitySeverity.MEDIUM


class OSVScanner:
    """OSV (Open Source Vulnerabilities) scanner."""

    def __init__(self):
        self.api_url = "https://api.osv.dev/v1/query"
        self.timeout = 30

    async def scan_packages(self, packages: list[PackageInfo]) -> list[Vulnerability]:
        """Scan packages against OSV database."""
        vulnerabilities = []

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                for package in packages:
                    try:
                        query_data = {
                            "package": {"name": package.name, "ecosystem": "PyPI"},
                            "version": package.version,
                        }

                        async with session.post(
                            self.api_url, json=query_data
                        ) as response:
                            if response.status == 200:
                                data = await response.json()

                                for vuln_data in data.get("vulns", []):
                                    vulnerability = Vulnerability(
                                        id=vuln_data.get("id", "unknown"),
                                        package_name=package.name,
                                        installed_version=package.version,
                                        affected_versions=self._extract_affected_versions(
                                            vuln_data
                                        ),
                                        fixed_versions=self._extract_fixed_versions(
                                            vuln_data
                                        ),
                                        severity=self._extract_severity(vuln_data),
                                        title=vuln_data.get(
                                            "summary", "Security vulnerability"
                                        ),
                                        description=vuln_data.get("details", ""),
                                        references=self._extract_references(vuln_data),
                                        published_date=self._parse_date(
                                            vuln_data.get("published")
                                        ),
                                        source="osv.dev",
                                    )
                                    vulnerabilities.append(vulnerability)

                    except Exception as e:
                        logger.warning(
                            f"Failed to check {package.name} against OSV: {str(e)}"
                        )
                        continue

        except Exception as e:
            logger.error(f"OSV scanner failed: {str(e)}")

        return vulnerabilities

    def _extract_affected_versions(self, vuln_data: dict[str, Any]) -> list[str]:
        """Extract affected versions from OSV data."""
        affected_versions = []

        for affected in vuln_data.get("affected", []):
            if affected.get("package", {}).get("ecosystem") == "PyPI":
                for version_range in affected.get("ranges", []):
                    # This is simplified - OSV uses complex version ranges
                    affected_versions.extend(version_range.get("events", []))

        return affected_versions

    def _extract_fixed_versions(self, vuln_data: dict[str, Any]) -> list[str]:
        """Extract fixed versions from OSV data."""
        # OSV provides fix information in database_specific fields
        return []

    def _extract_severity(self, vuln_data: dict[str, Any]) -> VulnerabilitySeverity:
        """Extract severity from OSV data."""
        severity_data = vuln_data.get("severity", [])

        for severity in severity_data:
            if severity.get("type") == "CVSS_V3":
                score = severity.get("score", 0)
                if score >= 9.0:
                    return VulnerabilitySeverity.CRITICAL
                elif score >= 7.0:
                    return VulnerabilitySeverity.HIGH
                elif score >= 4.0:
                    return VulnerabilitySeverity.MEDIUM
                else:
                    return VulnerabilitySeverity.LOW

        return VulnerabilitySeverity.UNKNOWN

    def _extract_references(self, vuln_data: dict[str, Any]) -> list[str]:
        """Extract references from OSV data."""
        references = []

        for ref in vuln_data.get("references", []):
            if ref.get("url"):
                references.append(ref["url"])

        return references

    def _parse_date(self, date_str: str | None) -> datetime | None:
        """Parse date string to datetime."""
        if not date_str:
            return None

        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None


class DependencyScanner:
    """
    Comprehensive dependency vulnerability scanner.

    Combines multiple security databases for thorough vulnerability detection.
    """

    def __init__(self):
        self.scanners = [PyUpSecurityDB(), SafetyScanner(), OSVScanner()]
        self.scan_history: list[ScanResult] = []
        self.max_history = 100

    def get_installed_packages(self) -> list[PackageInfo]:
        """Get list of installed Python packages."""
        packages = []

        try:
            for dist in pkg_resources.working_set:
                package = PackageInfo(
                    name=dist.project_name,
                    version=dist.version,
                    location=dist.location,
                    dependencies=[str(req) for req in dist.requires()],
                    is_editable=dist.precedence == pkg_resources.DEVELOP_DIST,
                )
                packages.append(package)

        except Exception as e:
            logger.error(f"Failed to get installed packages: {str(e)}")

        return packages

    async def scan_dependencies(self) -> ScanResult:
        """Perform comprehensive dependency vulnerability scan."""
        start_time = datetime.utcnow()
        scan_id = hashlib.sha256(f"{start_time.isoformat()}".encode()).hexdigest()[:16]

        logger.info("Starting dependency vulnerability scan", scan_id=scan_id)

        try:
            # Get installed packages
            packages = self.get_installed_packages()

            if not packages:
                logger.warning("No packages found for scanning")
                return ScanResult(
                    scan_id=scan_id,
                    timestamp=start_time,
                    packages_scanned=0,
                    vulnerabilities_found=0,
                    errors=["No packages found"],
                )

            # Run all scanners concurrently
            all_vulnerabilities = []
            errors = []

            scanner_tasks = []
            for scanner in self.scanners:
                task = asyncio.create_task(scanner.scan_packages(packages))
                scanner_tasks.append(task)

            # Wait for all scanners to complete
            scanner_results = await asyncio.gather(
                *scanner_tasks, return_exceptions=True
            )

            for i, result in enumerate(scanner_results):
                if isinstance(result, Exception):
                    error_msg = f"Scanner {i} failed: {str(result)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                else:
                    all_vulnerabilities.extend(result)

            # Deduplicate vulnerabilities
            unique_vulnerabilities = self._deduplicate_vulnerabilities(
                all_vulnerabilities
            )

            # Calculate scan duration
            scan_duration = (datetime.utcnow() - start_time).total_seconds()

            # Create scan result
            scan_result = ScanResult(
                scan_id=scan_id,
                timestamp=start_time,
                packages_scanned=len(packages),
                vulnerabilities_found=len(unique_vulnerabilities),
                vulnerabilities=unique_vulnerabilities,
                scan_duration=scan_duration,
                errors=errors,
            )

            # Store in history
            self.scan_history.append(scan_result)
            if len(self.scan_history) > self.max_history:
                self.scan_history.pop(0)

            # Log results
            logger.info(
                "Dependency scan completed",
                scan_id=scan_id,
                packages_scanned=scan_result.packages_scanned,
                vulnerabilities_found=scan_result.vulnerabilities_found,
                critical_count=scan_result.get_critical_count(),
                high_count=scan_result.get_high_count(),
                duration=scan_duration,
            )

            return scan_result

        except Exception as e:
            logger.error(f"Dependency scan failed: {str(e)}")
            return ScanResult(
                scan_id=scan_id,
                timestamp=start_time,
                packages_scanned=0,
                vulnerabilities_found=0,
                errors=[str(e)],
            )

    def _deduplicate_vulnerabilities(
        self, vulnerabilities: list[Vulnerability]
    ) -> list[Vulnerability]:
        """Remove duplicate vulnerabilities from different sources."""
        seen = set()
        unique_vulnerabilities = []

        for vuln in vulnerabilities:
            # Create a unique key based on package and vulnerability ID
            key = f"{vuln.package_name}:{vuln.id}"

            if key not in seen:
                seen.add(key)
                unique_vulnerabilities.append(vuln)
            else:
                # If we've seen this vulnerability, prefer the one with more information
                existing_vuln = next(
                    v
                    for v in unique_vulnerabilities
                    if f"{v.package_name}:{v.id}" == key
                )
                if len(vuln.description) > len(existing_vuln.description):
                    # Replace with more detailed version
                    idx = unique_vulnerabilities.index(existing_vuln)
                    unique_vulnerabilities[idx] = vuln

        return unique_vulnerabilities

    def get_scan_history(self, limit: int = 10) -> list[ScanResult]:
        """Get recent scan history."""
        return self.scan_history[-limit:]

    def get_latest_scan(self) -> ScanResult | None:
        """Get the latest scan result."""
        return self.scan_history[-1] if self.scan_history else None

    async def generate_security_report(self) -> dict[str, Any]:
        """Generate comprehensive security report."""
        latest_scan = self.get_latest_scan()

        if not latest_scan:
            return {"error": "No scan results available"}

        # Categorize vulnerabilities
        critical_vulns = latest_scan.get_by_severity(VulnerabilitySeverity.CRITICAL)
        high_vulns = latest_scan.get_by_severity(VulnerabilitySeverity.HIGH)
        medium_vulns = latest_scan.get_by_severity(VulnerabilitySeverity.MEDIUM)
        low_vulns = latest_scan.get_by_severity(VulnerabilitySeverity.LOW)

        # Package risk analysis
        package_risks = {}
        for vuln in latest_scan.vulnerabilities:
            if vuln.package_name not in package_risks:
                package_risks[vuln.package_name] = {
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                }
            package_risks[vuln.package_name][vuln.severity.value] += 1

        # Sort packages by risk (critical > high > medium > low)
        sorted_packages = sorted(
            package_risks.items(),
            key=lambda x: (x[1]["critical"], x[1]["high"], x[1]["medium"], x[1]["low"]),
            reverse=True,
        )

        report = {
            "scan_summary": {
                "scan_id": latest_scan.scan_id,
                "timestamp": latest_scan.timestamp.isoformat(),
                "packages_scanned": latest_scan.packages_scanned,
                "total_vulnerabilities": latest_scan.vulnerabilities_found,
                "scan_duration": latest_scan.scan_duration,
            },
            "severity_breakdown": {
                "critical": len(critical_vulns),
                "high": len(high_vulns),
                "medium": len(medium_vulns),
                "low": len(low_vulns),
            },
            "high_risk_packages": sorted_packages[:10],
            "critical_vulnerabilities": [
                {
                    "id": v.id,
                    "package": v.package_name,
                    "version": v.installed_version,
                    "title": v.title,
                    "description": (
                        v.description[:200] + "..."
                        if len(v.description) > 200
                        else v.description
                    ),
                    "source": v.source,
                }
                for v in critical_vulns
            ],
            "recommendations": self._generate_recommendations(latest_scan),
            "scan_errors": latest_scan.errors,
        }

        return report

    def _generate_recommendations(self, scan_result: ScanResult) -> list[str]:
        """Generate security recommendations based on scan results."""
        recommendations = []

        critical_count = scan_result.get_critical_count()
        high_count = scan_result.get_high_count()

        if critical_count > 0:
            recommendations.append(
                f"URGENT: {critical_count} critical vulnerabilities found. "
                "Update affected packages immediately."
            )

        if high_count > 0:
            recommendations.append(
                f"HIGH PRIORITY: {high_count} high-severity vulnerabilities found. "
                "Schedule updates for affected packages."
            )

        if scan_result.vulnerabilities_found > 0:
            recommendations.append(
                "Review all vulnerabilities and create remediation plan."
            )
            recommendations.append(
                "Consider using automated dependency updates (e.g., Dependabot)."
            )
            recommendations.append(
                "Implement CI/CD security scanning to catch vulnerabilities early."
            )
        else:
            recommendations.append(
                "No vulnerabilities found. Continue regular scanning."
            )

        recommendations.append("Run dependency scans regularly (weekly recommended).")

        return recommendations


# Global dependency scanner
dependency_scanner: DependencyScanner | None = None


async def initialize_dependency_scanner() -> None:
    """Initialize the global dependency scanner."""
    global dependency_scanner

    try:
        dependency_scanner = DependencyScanner()
        logger.info("Dependency scanner initialized")

    except Exception as e:
        logger.error(f"Failed to initialize dependency scanner: {str(e)}")


async def scan_dependencies_scheduled() -> None:
    """Scheduled dependency scan."""
    if dependency_scanner:
        try:
            result = await dependency_scanner.scan_dependencies()

            # Alert on critical/high vulnerabilities
            if result.get_critical_count() > 0 or result.get_high_count() > 0:
                logger.error(
                    "High-priority vulnerabilities detected",
                    critical=result.get_critical_count(),
                    high=result.get_high_count(),
                    scan_id=result.scan_id,
                )

                # In production, send alerts to security team
                # await security_alerts.send_vulnerability_alert(result)

        except Exception as e:
            logger.error(f"Scheduled dependency scan failed: {str(e)}")


def get_dependency_scanner() -> DependencyScanner | None:
    """Get the global dependency scanner."""
    return dependency_scanner
