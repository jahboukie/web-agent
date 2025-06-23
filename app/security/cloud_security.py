"""
Cloud Security Posture Management (CSPM)

Comprehensive cloud security monitoring, misconfiguration prevention,
and secure API management for multi-cloud deployments.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import azure.identity
import boto3
from google.cloud import security_center

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.user import ThreatLevel

logger = get_logger(__name__)


class CloudProvider(str, Enum):
    """Supported cloud providers."""

    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    MULTI_CLOUD = "multi_cloud"


class SecurityControl(str, Enum):
    """Cloud security controls."""

    ENCRYPTION_AT_REST = "encryption_at_rest"
    ENCRYPTION_IN_TRANSIT = "encryption_in_transit"
    NETWORK_SECURITY = "network_security"
    ACCESS_CONTROL = "access_control"
    LOGGING_MONITORING = "logging_monitoring"
    BACKUP_RECOVERY = "backup_recovery"
    VULNERABILITY_MANAGEMENT = "vulnerability_management"
    CONFIGURATION_MANAGEMENT = "configuration_management"


class ComplianceFramework(str, Enum):
    """Compliance frameworks."""

    SOC2 = "soc2"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    FEDRAMP = "fedramp"
    ISO27001 = "iso27001"
    NIST = "nist"


@dataclass
class SecurityFinding:
    """Security finding from CSPM scan."""

    finding_id: str
    title: str
    description: str
    severity: ThreatLevel
    resource_type: str
    resource_id: str
    cloud_provider: CloudProvider
    region: str
    control: SecurityControl
    compliance_frameworks: list[ComplianceFramework]
    remediation_steps: list[str]
    risk_score: float
    first_detected: datetime
    last_updated: datetime
    status: str = "open"  # open, remediated, accepted_risk, false_positive
    auto_remediation_available: bool = False


@dataclass
class CloudConfiguration:
    """Cloud configuration baseline."""

    provider: CloudProvider
    account_id: str
    region: str
    service_name: str
    resource_type: str
    configuration: dict[str, Any]
    security_score: float
    compliance_status: dict[ComplianceFramework, bool]
    last_scanned: datetime
    drift_detected: bool = False


class CloudSecurityPostureManager:
    """
    Cloud Security Posture Management (CSPM) Engine

    Monitors cloud configurations, detects misconfigurations,
    and ensures compliance across multi-cloud environments.
    """

    def __init__(self):
        self.aws_client = None
        self.azure_client = None
        self.gcp_client = None
        self.security_baselines = self._load_security_baselines()
        self.compliance_rules = self._load_compliance_rules()

    async def initialize_cloud_clients(self) -> None:
        """Initialize cloud provider clients."""

        try:
            # AWS Client
            if settings.AWS_ACCESS_KEY_ID:
                self.aws_client = boto3.Session(
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_DEFAULT_REGION,
                )
                logger.info("AWS client initialized")

            # Azure Client
            if settings.AZURE_CLIENT_ID:
                self.azure_client = azure.identity.DefaultAzureCredential()
                logger.info("Azure client initialized")

            # GCP Client
            if settings.GCP_PROJECT_ID:
                self.gcp_client = security_center.SecurityCenterClient()
                logger.info("GCP client initialized")

        except Exception as e:
            logger.error("Failed to initialize cloud clients", error=str(e))
            raise

    def _load_security_baselines(self) -> dict[CloudProvider, dict[str, Any]]:
        """Load security configuration baselines."""

        return {
            CloudProvider.AWS: {
                "s3_bucket": {
                    "public_read_prohibited": True,
                    "public_write_prohibited": True,
                    "encryption_enabled": True,
                    "versioning_enabled": True,
                    "mfa_delete_enabled": True,
                    "access_logging_enabled": True,
                },
                "ec2_instance": {
                    "public_ip_prohibited": True,
                    "security_groups_restrictive": True,
                    "instance_metadata_v2_required": True,
                    "ebs_encryption_enabled": True,
                    "monitoring_enabled": True,
                },
                "rds_instance": {
                    "public_access_prohibited": True,
                    "encryption_enabled": True,
                    "backup_retention_min_days": 7,
                    "deletion_protection_enabled": True,
                    "multi_az_enabled": True,
                },
                "iam": {
                    "password_policy_enforced": True,
                    "mfa_required": True,
                    "root_access_keys_prohibited": True,
                    "unused_credentials_removed": True,
                    "privilege_escalation_prohibited": True,
                },
            },
            CloudProvider.AZURE: {
                "storage_account": {
                    "public_blob_access_prohibited": True,
                    "encryption_enabled": True,
                    "firewall_enabled": True,
                    "https_only": True,
                    "threat_protection_enabled": True,
                },
                "virtual_machine": {
                    "disk_encryption_enabled": True,
                    "endpoint_protection_installed": True,
                    "network_security_groups_configured": True,
                    "monitoring_agent_installed": True,
                },
                "sql_database": {
                    "transparent_data_encryption_enabled": True,
                    "auditing_enabled": True,
                    "threat_detection_enabled": True,
                    "firewall_configured": True,
                },
            },
            CloudProvider.GCP: {
                "storage_bucket": {
                    "uniform_bucket_level_access": True,
                    "public_access_prohibited": True,
                    "encryption_enabled": True,
                    "versioning_enabled": True,
                },
                "compute_instance": {
                    "os_login_enabled": True,
                    "serial_port_disabled": True,
                    "shielded_vm_enabled": True,
                    "ip_forwarding_disabled": True,
                },
                "cloud_sql": {
                    "ssl_required": True,
                    "authorized_networks_restricted": True,
                    "backup_enabled": True,
                    "point_in_time_recovery_enabled": True,
                },
            },
        }

    def _load_compliance_rules(self) -> dict[ComplianceFramework, dict[str, Any]]:
        """Load compliance framework rules."""

        return {
            ComplianceFramework.SOC2: {
                "cc6_1_logical_access": {
                    "controls": [SecurityControl.ACCESS_CONTROL],
                    "requirements": [
                        "Multi-factor authentication enabled",
                        "Privileged access restricted",
                        "Access reviews conducted",
                    ],
                },
                "cc6_7_data_transmission": {
                    "controls": [SecurityControl.ENCRYPTION_IN_TRANSIT],
                    "requirements": [
                        "Data encrypted in transit",
                        "Secure protocols used",
                        "Certificate management implemented",
                    ],
                },
            },
            ComplianceFramework.GDPR: {
                "art32_security_processing": {
                    "controls": [
                        SecurityControl.ENCRYPTION_AT_REST,
                        SecurityControl.ENCRYPTION_IN_TRANSIT,
                        SecurityControl.ACCESS_CONTROL,
                    ],
                    "requirements": [
                        "Pseudonymisation and encryption",
                        "Confidentiality and integrity assured",
                        "Availability and resilience maintained",
                    ],
                }
            },
            ComplianceFramework.HIPAA: {
                "164_312_access_control": {
                    "controls": [SecurityControl.ACCESS_CONTROL],
                    "requirements": [
                        "Unique user identification",
                        "Emergency access procedure",
                        "Automatic logoff",
                        "Encryption and decryption",
                    ],
                }
            },
        }

    async def scan_cloud_posture(
        self, provider: CloudProvider, account_id: str
    ) -> list[SecurityFinding]:
        """Comprehensive cloud security posture scan."""

        findings = []

        try:
            if provider == CloudProvider.AWS:
                findings.extend(await self._scan_aws_posture(account_id))
            elif provider == CloudProvider.AZURE:
                findings.extend(await self._scan_azure_posture(account_id))
            elif provider == CloudProvider.GCP:
                findings.extend(await self._scan_gcp_posture(account_id))
            elif provider == CloudProvider.MULTI_CLOUD:
                # Scan all providers
                findings.extend(await self._scan_aws_posture(account_id))
                findings.extend(await self._scan_azure_posture(account_id))
                findings.extend(await self._scan_gcp_posture(account_id))

            # Sort findings by risk score (highest first)
            findings.sort(key=lambda x: x.risk_score, reverse=True)

            logger.info(
                "Cloud posture scan completed",
                provider=provider.value,
                account_id=account_id,
                findings_count=len(findings),
                critical_findings=len(
                    [f for f in findings if f.severity == ThreatLevel.CRITICAL]
                ),
                high_findings=len(
                    [f for f in findings if f.severity == ThreatLevel.HIGH]
                ),
            )

            return findings

        except Exception as e:
            logger.error(
                "Cloud posture scan failed",
                provider=provider.value,
                account_id=account_id,
                error=str(e),
            )
            raise

    async def _scan_aws_posture(self, account_id: str) -> list[SecurityFinding]:
        """Scan AWS security posture."""

        findings = []

        if not self.aws_client:
            return findings

        try:
            # Scan S3 buckets
            s3_findings = await self._scan_aws_s3_buckets()
            findings.extend(s3_findings)

            # Scan EC2 instances
            ec2_findings = await self._scan_aws_ec2_instances()
            findings.extend(ec2_findings)

            # Scan RDS instances
            rds_findings = await self._scan_aws_rds_instances()
            findings.extend(rds_findings)

            # Scan IAM configuration
            iam_findings = await self._scan_aws_iam_configuration()
            findings.extend(iam_findings)

            # Scan VPC configuration
            vpc_findings = await self._scan_aws_vpc_configuration()
            findings.extend(vpc_findings)

        except Exception as e:
            logger.error("AWS posture scan failed", error=str(e))

        return findings

    async def _scan_aws_s3_buckets(self) -> list[SecurityFinding]:
        """Scan AWS S3 bucket configurations."""

        findings = []

        try:
            s3_client = self.aws_client.client("s3")

            # List all buckets
            response = s3_client.list_buckets()

            for bucket in response["Buckets"]:
                bucket_name = bucket["Name"]

                # Check public access
                try:
                    public_access = s3_client.get_public_access_block(
                        Bucket=bucket_name
                    )

                    pab = public_access["PublicAccessBlockConfiguration"]
                    if not all(
                        [
                            pab.get("BlockPublicAcls", False),
                            pab.get("IgnorePublicAcls", False),
                            pab.get("BlockPublicPolicy", False),
                            pab.get("RestrictPublicBuckets", False),
                        ]
                    ):
                        findings.append(
                            SecurityFinding(
                                finding_id=f"s3_public_access_{bucket_name}",
                                title="S3 Bucket Public Access Not Blocked",
                                description=f"S3 bucket {bucket_name} allows public access",
                                severity=ThreatLevel.HIGH,
                                resource_type="s3_bucket",
                                resource_id=bucket_name,
                                cloud_provider=CloudProvider.AWS,
                                region=s3_client.meta.region_name,
                                control=SecurityControl.ACCESS_CONTROL,
                                compliance_frameworks=[
                                    ComplianceFramework.SOC2,
                                    ComplianceFramework.GDPR,
                                ],
                                remediation_steps=[
                                    "Enable S3 bucket public access block",
                                    "Review bucket policies",
                                    "Implement least privilege access",
                                ],
                                risk_score=8.5,
                                first_detected=datetime.utcnow(),
                                last_updated=datetime.utcnow(),
                                auto_remediation_available=True,
                            )
                        )

                except Exception:
                    # Public access block not configured
                    findings.append(
                        SecurityFinding(
                            finding_id=f"s3_no_pab_{bucket_name}",
                            title="S3 Bucket Missing Public Access Block",
                            description=f"S3 bucket {bucket_name} has no public access block configuration",
                            severity=ThreatLevel.CRITICAL,
                            resource_type="s3_bucket",
                            resource_id=bucket_name,
                            cloud_provider=CloudProvider.AWS,
                            region=s3_client.meta.region_name,
                            control=SecurityControl.ACCESS_CONTROL,
                            compliance_frameworks=[
                                ComplianceFramework.SOC2,
                                ComplianceFramework.GDPR,
                            ],
                            remediation_steps=[
                                "Configure S3 bucket public access block",
                                "Enable all public access restrictions",
                            ],
                            risk_score=9.0,
                            first_detected=datetime.utcnow(),
                            last_updated=datetime.utcnow(),
                            auto_remediation_available=True,
                        )
                    )

                # Check encryption
                try:
                    encryption = s3_client.get_bucket_encryption(Bucket=bucket_name)
                except Exception:
                    # No encryption configured
                    findings.append(
                        SecurityFinding(
                            finding_id=f"s3_no_encryption_{bucket_name}",
                            title="S3 Bucket Encryption Not Enabled",
                            description=f"S3 bucket {bucket_name} does not have default encryption enabled",
                            severity=ThreatLevel.HIGH,
                            resource_type="s3_bucket",
                            resource_id=bucket_name,
                            cloud_provider=CloudProvider.AWS,
                            region=s3_client.meta.region_name,
                            control=SecurityControl.ENCRYPTION_AT_REST,
                            compliance_frameworks=[
                                ComplianceFramework.GDPR,
                                ComplianceFramework.HIPAA,
                            ],
                            remediation_steps=[
                                "Enable S3 bucket default encryption",
                                "Use AES-256 or AWS KMS encryption",
                            ],
                            risk_score=7.5,
                            first_detected=datetime.utcnow(),
                            last_updated=datetime.utcnow(),
                            auto_remediation_available=True,
                        )
                    )

        except Exception as e:
            logger.error("S3 bucket scan failed", error=str(e))

        return findings

    async def _scan_aws_ec2_instances(self) -> list[SecurityFinding]:
        """Scan AWS EC2 instance configurations."""

        findings = []

        try:
            ec2_client = self.aws_client.client("ec2")

            # Get all instances
            response = ec2_client.describe_instances()

            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    instance_id = instance["InstanceId"]

                    # Check for public IP
                    if instance.get("PublicIpAddress"):
                        findings.append(
                            SecurityFinding(
                                finding_id=f"ec2_public_ip_{instance_id}",
                                title="EC2 Instance Has Public IP",
                                description=f"EC2 instance {instance_id} has a public IP address",
                                severity=ThreatLevel.MEDIUM,
                                resource_type="ec2_instance",
                                resource_id=instance_id,
                                cloud_provider=CloudProvider.AWS,
                                region=instance["Placement"]["AvailabilityZone"][:-1],
                                control=SecurityControl.NETWORK_SECURITY,
                                compliance_frameworks=[ComplianceFramework.SOC2],
                                remediation_steps=[
                                    "Move instance to private subnet",
                                    "Use NAT gateway for outbound access",
                                    "Implement bastion host for access",
                                ],
                                risk_score=6.0,
                                first_detected=datetime.utcnow(),
                                last_updated=datetime.utcnow(),
                                auto_remediation_available=False,
                            )
                        )

                    # Check IMDSv2 requirement
                    metadata_options = instance.get("MetadataOptions", {})
                    if metadata_options.get("HttpTokens") != "required":
                        findings.append(
                            SecurityFinding(
                                finding_id=f"ec2_imdsv1_{instance_id}",
                                title="EC2 Instance Allows IMDSv1",
                                description=f"EC2 instance {instance_id} allows insecure IMDSv1",
                                severity=ThreatLevel.MEDIUM,
                                resource_type="ec2_instance",
                                resource_id=instance_id,
                                cloud_provider=CloudProvider.AWS,
                                region=instance["Placement"]["AvailabilityZone"][:-1],
                                control=SecurityControl.CONFIGURATION_MANAGEMENT,
                                compliance_frameworks=[ComplianceFramework.SOC2],
                                remediation_steps=[
                                    "Require IMDSv2 tokens",
                                    "Update instance metadata options",
                                ],
                                risk_score=5.5,
                                first_detected=datetime.utcnow(),
                                last_updated=datetime.utcnow(),
                                auto_remediation_available=True,
                            )
                        )

        except Exception as e:
            logger.error("EC2 instance scan failed", error=str(e))

        return findings

    async def _scan_aws_rds_instances(self) -> list[SecurityFinding]:
        """Scan AWS RDS instance configurations."""
        return []  # Implementation would scan RDS configurations

    async def _scan_aws_iam_configuration(self) -> list[SecurityFinding]:
        """Scan AWS IAM configurations."""
        return []  # Implementation would scan IAM policies and users

    async def _scan_aws_vpc_configuration(self) -> list[SecurityFinding]:
        """Scan AWS VPC configurations."""
        return []  # Implementation would scan VPC and security groups

    async def _scan_azure_posture(self, subscription_id: str) -> list[SecurityFinding]:
        """Scan Azure security posture."""
        return []  # Implementation would scan Azure resources

    async def _scan_gcp_posture(self, project_id: str) -> list[SecurityFinding]:
        """Scan GCP security posture."""
        return []  # Implementation would scan GCP resources

    async def remediate_finding(self, finding: SecurityFinding) -> bool:
        """Auto-remediate security finding if possible."""

        try:
            if not finding.auto_remediation_available:
                logger.warning(
                    "Auto-remediation not available", finding_id=finding.finding_id
                )
                return False

            if finding.cloud_provider == CloudProvider.AWS:
                return await self._remediate_aws_finding(finding)
            elif finding.cloud_provider == CloudProvider.AZURE:
                return await self._remediate_azure_finding(finding)
            elif finding.cloud_provider == CloudProvider.GCP:
                return await self._remediate_gcp_finding(finding)

            return False

        except Exception as e:
            logger.error(
                "Auto-remediation failed", finding_id=finding.finding_id, error=str(e)
            )
            return False

    async def _remediate_aws_finding(self, finding: SecurityFinding) -> bool:
        """Remediate AWS security finding."""

        try:
            if "s3_public_access" in finding.finding_id:
                # Enable S3 public access block
                s3_client = self.aws_client.client("s3")
                s3_client.put_public_access_block(
                    Bucket=finding.resource_id,
                    PublicAccessBlockConfiguration={
                        "BlockPublicAcls": True,
                        "IgnorePublicAcls": True,
                        "BlockPublicPolicy": True,
                        "RestrictPublicBuckets": True,
                    },
                )
                logger.info("Remediated S3 public access", bucket=finding.resource_id)
                return True

            elif "s3_no_encryption" in finding.finding_id:
                # Enable S3 bucket encryption
                s3_client = self.aws_client.client("s3")
                s3_client.put_bucket_encryption(
                    Bucket=finding.resource_id,
                    ServerSideEncryptionConfiguration={
                        "Rules": [
                            {
                                "ApplyServerSideEncryptionByDefault": {
                                    "SSEAlgorithm": "AES256"
                                }
                            }
                        ]
                    },
                )
                logger.info("Remediated S3 encryption", bucket=finding.resource_id)
                return True

            elif "ec2_imdsv1" in finding.finding_id:
                # Require IMDSv2 for EC2 instance
                ec2_client = self.aws_client.client("ec2")
                ec2_client.modify_instance_metadata_options(
                    InstanceId=finding.resource_id,
                    HttpTokens="required",
                    HttpPutResponseHopLimit=1,
                )
                logger.info(
                    "Remediated EC2 IMDSv2 requirement", instance_id=finding.resource_id
                )
                return True

        except Exception as e:
            logger.error(
                "AWS remediation failed", finding_id=finding.finding_id, error=str(e)
            )

        return False

    async def _remediate_azure_finding(self, finding: SecurityFinding) -> bool:
        """Remediate Azure security finding."""
        return False  # Implementation would remediate Azure findings

    async def _remediate_gcp_finding(self, finding: SecurityFinding) -> bool:
        """Remediate GCP security finding."""
        return False  # Implementation would remediate GCP findings

    async def generate_compliance_report(
        self, framework: ComplianceFramework
    ) -> dict[str, Any]:
        """Generate compliance report for specific framework."""

        report = {
            "framework": framework.value,
            "generated_at": datetime.utcnow().isoformat(),
            "overall_compliance_score": 0.0,
            "control_results": [],
            "findings_summary": {
                "total_findings": 0,
                "critical_findings": 0,
                "high_findings": 0,
                "medium_findings": 0,
                "low_findings": 0,
            },
            "recommendations": [],
        }

        # This would integrate with the findings database
        # and calculate compliance scores based on control implementation

        return report


# Global CSPM instance
cspm_manager = CloudSecurityPostureManager()
