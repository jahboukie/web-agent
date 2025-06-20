"""
Cloud Security Posture Management (CSPM)

Comprehensive cloud security monitoring, misconfiguration prevention,
and secure API management for multi-cloud deployments.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import boto3
import azure.identity
from google.cloud import security_center

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.user import ThreatLevel, ComplianceLevel

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
    compliance_frameworks: List[ComplianceFramework]
    remediation_steps: List[str]
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
    configuration: Dict[str, Any]
    security_score: float
    compliance_status: Dict[ComplianceFramework, bool]
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
                    region_name=settings.AWS_DEFAULT_REGION
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
    
    def _load_security_baselines(self) -> Dict[CloudProvider, Dict[str, Any]]:
        """Load security configuration baselines."""
        
        return {
            CloudProvider.AWS: {
                "s3_bucket": {
                    "public_read_prohibited": True,
                    "public_write_prohibited": True,
                    "encryption_enabled": True,
                    "versioning_enabled": True,
                    "mfa_delete_enabled": True,
                    "access_logging_enabled": True
                },
                "ec2_instance": {
                    "public_ip_prohibited": True,
                    "security_groups_restrictive": True,
                    "instance_metadata_v2_required": True,
                    "ebs_encryption_enabled": True,
                    "monitoring_enabled": True
                },
                "rds_instance": {
                    "public_access_prohibited": True,
                    "encryption_enabled": True,
                    "backup_retention_min_days": 7,
                    "deletion_protection_enabled": True,
                    "multi_az_enabled": True
                },
                "iam": {
                    "password_policy_enforced": True,
                    "mfa_required": True,\n                    \"root_access_keys_prohibited\": True,\n                    \"unused_credentials_removed\": True,\n                    \"privilege_escalation_prohibited\": True\n                }\n            },\n            CloudProvider.AZURE: {\n                \"storage_account\": {\n                    \"public_blob_access_prohibited\": True,\n                    \"encryption_enabled\": True,\n                    \"firewall_enabled\": True,\n                    \"https_only\": True,\n                    \"threat_protection_enabled\": True\n                },\n                \"virtual_machine\": {\n                    \"disk_encryption_enabled\": True,\n                    \"endpoint_protection_installed\": True,\n                    \"network_security_groups_configured\": True,\n                    \"monitoring_agent_installed\": True\n                },\n                \"sql_database\": {\n                    \"transparent_data_encryption_enabled\": True,\n                    \"auditing_enabled\": True,\n                    \"threat_detection_enabled\": True,\n                    \"firewall_configured\": True\n                }\n            },\n            CloudProvider.GCP: {\n                \"storage_bucket\": {\n                    \"uniform_bucket_level_access\": True,\n                    \"public_access_prohibited\": True,\n                    \"encryption_enabled\": True,\n                    \"versioning_enabled\": True\n                },\n                \"compute_instance\": {\n                    \"os_login_enabled\": True,\n                    \"serial_port_disabled\": True,\n                    \"shielded_vm_enabled\": True,\n                    \"ip_forwarding_disabled\": True\n                },\n                \"cloud_sql\": {\n                    \"ssl_required\": True,\n                    \"authorized_networks_restricted\": True,\n                    \"backup_enabled\": True,\n                    \"point_in_time_recovery_enabled\": True\n                }\n            }\n        }\n    \n    def _load_compliance_rules(self) -> Dict[ComplianceFramework, Dict[str, Any]]:\n        \"\"\"Load compliance framework rules.\"\"\"\n        \n        return {\n            ComplianceFramework.SOC2: {\n                \"cc6_1_logical_access\": {\n                    \"controls\": [SecurityControl.ACCESS_CONTROL],\n                    \"requirements\": [\n                        \"Multi-factor authentication enabled\",\n                        \"Privileged access restricted\",\n                        \"Access reviews conducted\"\n                    ]\n                },\n                \"cc6_7_data_transmission\": {\n                    \"controls\": [SecurityControl.ENCRYPTION_IN_TRANSIT],\n                    \"requirements\": [\n                        \"Data encrypted in transit\",\n                        \"Secure protocols used\",\n                        \"Certificate management implemented\"\n                    ]\n                }\n            },\n            ComplianceFramework.GDPR: {\n                \"art32_security_processing\": {\n                    \"controls\": [\n                        SecurityControl.ENCRYPTION_AT_REST,\n                        SecurityControl.ENCRYPTION_IN_TRANSIT,\n                        SecurityControl.ACCESS_CONTROL\n                    ],\n                    \"requirements\": [\n                        \"Pseudonymisation and encryption\",\n                        \"Confidentiality and integrity assured\",\n                        \"Availability and resilience maintained\"\n                    ]\n                }\n            },\n            ComplianceFramework.HIPAA: {\n                \"164_312_access_control\": {\n                    \"controls\": [SecurityControl.ACCESS_CONTROL],\n                    \"requirements\": [\n                        \"Unique user identification\",\n                        \"Emergency access procedure\",\n                        \"Automatic logoff\",\n                        \"Encryption and decryption\"\n                    ]\n                }\n            }\n        }\n    \n    async def scan_cloud_posture(self, provider: CloudProvider, account_id: str) -> List[SecurityFinding]:\n        \"\"\"Comprehensive cloud security posture scan.\"\"\"\n        \n        findings = []\n        \n        try:\n            if provider == CloudProvider.AWS:\n                findings.extend(await self._scan_aws_posture(account_id))\n            elif provider == CloudProvider.AZURE:\n                findings.extend(await self._scan_azure_posture(account_id))\n            elif provider == CloudProvider.GCP:\n                findings.extend(await self._scan_gcp_posture(account_id))\n            elif provider == CloudProvider.MULTI_CLOUD:\n                # Scan all providers\n                findings.extend(await self._scan_aws_posture(account_id))\n                findings.extend(await self._scan_azure_posture(account_id))\n                findings.extend(await self._scan_gcp_posture(account_id))\n            \n            # Sort findings by risk score (highest first)\n            findings.sort(key=lambda x: x.risk_score, reverse=True)\n            \n            logger.info(\n                \"Cloud posture scan completed\",\n                provider=provider.value,\n                account_id=account_id,\n                findings_count=len(findings),\n                critical_findings=len([f for f in findings if f.severity == ThreatLevel.CRITICAL]),\n                high_findings=len([f for f in findings if f.severity == ThreatLevel.HIGH])\n            )\n            \n            return findings\n            \n        except Exception as e:\n            logger.error(\n                \"Cloud posture scan failed\",\n                provider=provider.value,\n                account_id=account_id,\n                error=str(e)\n            )\n            raise\n    \n    async def _scan_aws_posture(self, account_id: str) -> List[SecurityFinding]:\n        \"\"\"Scan AWS security posture.\"\"\"\n        \n        findings = []\n        \n        if not self.aws_client:\n            return findings\n        \n        try:\n            # Scan S3 buckets\n            s3_findings = await self._scan_aws_s3_buckets()\n            findings.extend(s3_findings)\n            \n            # Scan EC2 instances\n            ec2_findings = await self._scan_aws_ec2_instances()\n            findings.extend(ec2_findings)\n            \n            # Scan RDS instances\n            rds_findings = await self._scan_aws_rds_instances()\n            findings.extend(rds_findings)\n            \n            # Scan IAM configuration\n            iam_findings = await self._scan_aws_iam_configuration()\n            findings.extend(iam_findings)\n            \n            # Scan VPC configuration\n            vpc_findings = await self._scan_aws_vpc_configuration()\n            findings.extend(vpc_findings)\n            \n        except Exception as e:\n            logger.error(\"AWS posture scan failed\", error=str(e))\n        \n        return findings\n    \n    async def _scan_aws_s3_buckets(self) -> List[SecurityFinding]:\n        \"\"\"Scan AWS S3 bucket configurations.\"\"\"\n        \n        findings = []\n        \n        try:\n            s3_client = self.aws_client.client('s3')\n            \n            # List all buckets\n            response = s3_client.list_buckets()\n            \n            for bucket in response['Buckets']:\n                bucket_name = bucket['Name']\n                \n                # Check public access\n                try:\n                    public_access = s3_client.get_public_access_block(\n                        Bucket=bucket_name\n                    )\n                    \n                    pab = public_access['PublicAccessBlockConfiguration']\n                    if not all([\n                        pab.get('BlockPublicAcls', False),\n                        pab.get('IgnorePublicAcls', False),\n                        pab.get('BlockPublicPolicy', False),\n                        pab.get('RestrictPublicBuckets', False)\n                    ]):\n                        findings.append(SecurityFinding(\n                            finding_id=f\"s3_public_access_{bucket_name}\",\n                            title=\"S3 Bucket Public Access Not Blocked\",\n                            description=f\"S3 bucket {bucket_name} allows public access\",\n                            severity=ThreatLevel.HIGH,\n                            resource_type=\"s3_bucket\",\n                            resource_id=bucket_name,\n                            cloud_provider=CloudProvider.AWS,\n                            region=s3_client.meta.region_name,\n                            control=SecurityControl.ACCESS_CONTROL,\n                            compliance_frameworks=[ComplianceFramework.SOC2, ComplianceFramework.GDPR],\n                            remediation_steps=[\n                                \"Enable S3 bucket public access block\",\n                                \"Review bucket policies\",\n                                \"Implement least privilege access\"\n                            ],\n                            risk_score=8.5,\n                            first_detected=datetime.utcnow(),\n                            last_updated=datetime.utcnow(),\n                            auto_remediation_available=True\n                        ))\n                        \n                except Exception:\n                    # Public access block not configured\n                    findings.append(SecurityFinding(\n                        finding_id=f\"s3_no_pab_{bucket_name}\",\n                        title=\"S3 Bucket Missing Public Access Block\",\n                        description=f\"S3 bucket {bucket_name} has no public access block configuration\",\n                        severity=ThreatLevel.CRITICAL,\n                        resource_type=\"s3_bucket\",\n                        resource_id=bucket_name,\n                        cloud_provider=CloudProvider.AWS,\n                        region=s3_client.meta.region_name,\n                        control=SecurityControl.ACCESS_CONTROL,\n                        compliance_frameworks=[ComplianceFramework.SOC2, ComplianceFramework.GDPR],\n                        remediation_steps=[\n                            \"Configure S3 bucket public access block\",\n                            \"Enable all public access restrictions\"\n                        ],\n                        risk_score=9.0,\n                        first_detected=datetime.utcnow(),\n                        last_updated=datetime.utcnow(),\n                        auto_remediation_available=True\n                    ))\n                \n                # Check encryption\n                try:\n                    encryption = s3_client.get_bucket_encryption(Bucket=bucket_name)\n                except Exception:\n                    # No encryption configured\n                    findings.append(SecurityFinding(\n                        finding_id=f\"s3_no_encryption_{bucket_name}\",\n                        title=\"S3 Bucket Encryption Not Enabled\",\n                        description=f\"S3 bucket {bucket_name} does not have default encryption enabled\",\n                        severity=ThreatLevel.HIGH,\n                        resource_type=\"s3_bucket\",\n                        resource_id=bucket_name,\n                        cloud_provider=CloudProvider.AWS,\n                        region=s3_client.meta.region_name,\n                        control=SecurityControl.ENCRYPTION_AT_REST,\n                        compliance_frameworks=[ComplianceFramework.GDPR, ComplianceFramework.HIPAA],\n                        remediation_steps=[\n                            \"Enable S3 bucket default encryption\",\n                            \"Use AES-256 or AWS KMS encryption\"\n                        ],\n                        risk_score=7.5,\n                        first_detected=datetime.utcnow(),\n                        last_updated=datetime.utcnow(),\n                        auto_remediation_available=True\n                    ))\n                    \n        except Exception as e:\n            logger.error(\"S3 bucket scan failed\", error=str(e))\n        \n        return findings\n    \n    async def _scan_aws_ec2_instances(self) -> List[SecurityFinding]:\n        \"\"\"Scan AWS EC2 instance configurations.\"\"\"\n        \n        findings = []\n        \n        try:\n            ec2_client = self.aws_client.client('ec2')\n            \n            # Get all instances\n            response = ec2_client.describe_instances()\n            \n            for reservation in response['Reservations']:\n                for instance in reservation['Instances']:\n                    instance_id = instance['InstanceId']\n                    \n                    # Check for public IP\n                    if instance.get('PublicIpAddress'):\n                        findings.append(SecurityFinding(\n                            finding_id=f\"ec2_public_ip_{instance_id}\",\n                            title=\"EC2 Instance Has Public IP\",\n                            description=f\"EC2 instance {instance_id} has a public IP address\",\n                            severity=ThreatLevel.MEDIUM,\n                            resource_type=\"ec2_instance\",\n                            resource_id=instance_id,\n                            cloud_provider=CloudProvider.AWS,\n                            region=instance['Placement']['AvailabilityZone'][:-1],\n                            control=SecurityControl.NETWORK_SECURITY,\n                            compliance_frameworks=[ComplianceFramework.SOC2],\n                            remediation_steps=[\n                                \"Move instance to private subnet\",\n                                \"Use NAT gateway for outbound access\",\n                                \"Implement bastion host for access\"\n                            ],\n                            risk_score=6.0,\n                            first_detected=datetime.utcnow(),\n                            last_updated=datetime.utcnow(),\n                            auto_remediation_available=False\n                        ))\n                    \n                    # Check IMDSv2 requirement\n                    metadata_options = instance.get('MetadataOptions', {})\n                    if metadata_options.get('HttpTokens') != 'required':\n                        findings.append(SecurityFinding(\n                            finding_id=f\"ec2_imdsv1_{instance_id}\",\n                            title=\"EC2 Instance Allows IMDSv1\",\n                            description=f\"EC2 instance {instance_id} allows insecure IMDSv1\",\n                            severity=ThreatLevel.MEDIUM,\n                            resource_type=\"ec2_instance\",\n                            resource_id=instance_id,\n                            cloud_provider=CloudProvider.AWS,\n                            region=instance['Placement']['AvailabilityZone'][:-1],\n                            control=SecurityControl.CONFIGURATION_MANAGEMENT,\n                            compliance_frameworks=[ComplianceFramework.SOC2],\n                            remediation_steps=[\n                                \"Require IMDSv2 tokens\",\n                                \"Update instance metadata options\"\n                            ],\n                            risk_score=5.5,\n                            first_detected=datetime.utcnow(),\n                            last_updated=datetime.utcnow(),\n                            auto_remediation_available=True\n                        ))\n                        \n        except Exception as e:\n            logger.error(\"EC2 instance scan failed\", error=str(e))\n        \n        return findings\n    \n    async def _scan_aws_rds_instances(self) -> List[SecurityFinding]:\n        \"\"\"Scan AWS RDS instance configurations.\"\"\"\n        return []  # Implementation would scan RDS configurations\n    \n    async def _scan_aws_iam_configuration(self) -> List[SecurityFinding]:\n        \"\"\"Scan AWS IAM configurations.\"\"\"\n        return []  # Implementation would scan IAM policies and users\n    \n    async def _scan_aws_vpc_configuration(self) -> List[SecurityFinding]:\n        \"\"\"Scan AWS VPC configurations.\"\"\"\n        return []  # Implementation would scan VPC and security groups\n    \n    async def _scan_azure_posture(self, subscription_id: str) -> List[SecurityFinding]:\n        \"\"\"Scan Azure security posture.\"\"\"\n        return []  # Implementation would scan Azure resources\n    \n    async def _scan_gcp_posture(self, project_id: str) -> List[SecurityFinding]:\n        \"\"\"Scan GCP security posture.\"\"\"\n        return []  # Implementation would scan GCP resources\n    \n    async def remediate_finding(self, finding: SecurityFinding) -> bool:\n        \"\"\"Auto-remediate security finding if possible.\"\"\"\n        \n        try:\n            if not finding.auto_remediation_available:\n                logger.warning(\n                    \"Auto-remediation not available\",\n                    finding_id=finding.finding_id\n                )\n                return False\n            \n            if finding.cloud_provider == CloudProvider.AWS:\n                return await self._remediate_aws_finding(finding)\n            elif finding.cloud_provider == CloudProvider.AZURE:\n                return await self._remediate_azure_finding(finding)\n            elif finding.cloud_provider == CloudProvider.GCP:\n                return await self._remediate_gcp_finding(finding)\n            \n            return False\n            \n        except Exception as e:\n            logger.error(\n                \"Auto-remediation failed\",\n                finding_id=finding.finding_id,\n                error=str(e)\n            )\n            return False\n    \n    async def _remediate_aws_finding(self, finding: SecurityFinding) -> bool:\n        \"\"\"Remediate AWS security finding.\"\"\"\n        \n        try:\n            if \"s3_public_access\" in finding.finding_id:\n                # Enable S3 public access block\n                s3_client = self.aws_client.client('s3')\n                s3_client.put_public_access_block(\n                    Bucket=finding.resource_id,\n                    PublicAccessBlockConfiguration={\n                        'BlockPublicAcls': True,\n                        'IgnorePublicAcls': True,\n                        'BlockPublicPolicy': True,\n                        'RestrictPublicBuckets': True\n                    }\n                )\n                logger.info(\n                    \"Remediated S3 public access\",\n                    bucket=finding.resource_id\n                )\n                return True\n            \n            elif \"s3_no_encryption\" in finding.finding_id:\n                # Enable S3 bucket encryption\n                s3_client = self.aws_client.client('s3')\n                s3_client.put_bucket_encryption(\n                    Bucket=finding.resource_id,\n                    ServerSideEncryptionConfiguration={\n                        'Rules': [\n                            {\n                                'ApplyServerSideEncryptionByDefault': {\n                                    'SSEAlgorithm': 'AES256'\n                                }\n                            }\n                        ]\n                    }\n                )\n                logger.info(\n                    \"Remediated S3 encryption\",\n                    bucket=finding.resource_id\n                )\n                return True\n            \n            elif \"ec2_imdsv1\" in finding.finding_id:\n                # Require IMDSv2 for EC2 instance\n                ec2_client = self.aws_client.client('ec2')\n                ec2_client.modify_instance_metadata_options(\n                    InstanceId=finding.resource_id,\n                    HttpTokens='required',\n                    HttpPutResponseHopLimit=1\n                )\n                logger.info(\n                    \"Remediated EC2 IMDSv2 requirement\",\n                    instance_id=finding.resource_id\n                )\n                return True\n            \n        except Exception as e:\n            logger.error(\n                \"AWS remediation failed\",\n                finding_id=finding.finding_id,\n                error=str(e)\n            )\n        \n        return False\n    \n    async def _remediate_azure_finding(self, finding: SecurityFinding) -> bool:\n        \"\"\"Remediate Azure security finding.\"\"\"\n        return False  # Implementation would remediate Azure findings\n    \n    async def _remediate_gcp_finding(self, finding: SecurityFinding) -> bool:\n        \"\"\"Remediate GCP security finding.\"\"\"\n        return False  # Implementation would remediate GCP findings\n    \n    async def generate_compliance_report(self, framework: ComplianceFramework) -> Dict[str, Any]:\n        \"\"\"Generate compliance report for specific framework.\"\"\"\n        \n        report = {\n            \"framework\": framework.value,\n            \"generated_at\": datetime.utcnow().isoformat(),\n            \"overall_compliance_score\": 0.0,\n            \"control_results\": [],\n            \"findings_summary\": {\n                \"total_findings\": 0,\n                \"critical_findings\": 0,\n                \"high_findings\": 0,\n                \"medium_findings\": 0,\n                \"low_findings\": 0\n            },\n            \"recommendations\": []\n        }\n        \n        # This would integrate with the findings database\n        # and calculate compliance scores based on control implementation\n        \n        return report\n\n\n# Global CSPM instance\ncspm_manager = CloudSecurityPostureManager()"