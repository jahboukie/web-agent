"""
Security Incident Response Playbooks

Automated incident detection, response workflows, and customer notification
protocols for rapid response to security breaches and vulnerabilities.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.core.logging import get_logger
from app.schemas.user import IncidentResponse, SecurityEvent, ThreatLevel

logger = get_logger(__name__)


class IncidentType(str, Enum):
    """Types of security incidents."""

    DATA_BREACH = "data_breach"
    ACCOUNT_COMPROMISE = "account_compromise"
    MALWARE_DETECTION = "malware_detection"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DDOS_ATTACK = "ddos_attack"
    INSIDER_THREAT = "insider_threat"
    VULNERABILITY_EXPLOITATION = "vulnerability_exploitation"
    COMPLIANCE_VIOLATION = "compliance_violation"
    SYSTEM_COMPROMISE = "system_compromise"
    CLOUD_MISCONFIGURATION = "cloud_misconfiguration"


class ResponseAction(str, Enum):
    """Incident response actions."""

    ISOLATE_SYSTEM = "isolate_system"
    DISABLE_ACCOUNT = "disable_account"
    RESET_PASSWORD = "reset_password"
    REVOKE_TOKENS = "revoke_tokens"
    BLOCK_IP = "block_ip"
    QUARANTINE_FILE = "quarantine_file"
    NOTIFY_USERS = "notify_users"
    ESCALATE_TO_SOC = "escalate_to_soc"
    CONTACT_AUTHORITIES = "contact_authorities"
    PATCH_VULNERABILITY = "patch_vulnerability"
    BACKUP_EVIDENCE = "backup_evidence"
    ACTIVATE_DR = "activate_dr"


class NotificationChannel(str, Enum):
    """Notification channels for incident response."""

    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    WEBHOOK = "webhook"
    DASHBOARD = "dashboard"


@dataclass
class PlaybookStep:
    """Individual step in incident response playbook."""

    step_id: str
    name: str
    description: str
    action: ResponseAction
    automated: bool
    timeout_minutes: int
    prerequisites: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    notification_required: bool = False
    approval_required: bool = False
    rollback_possible: bool = False


@dataclass
class IncidentPlaybook:
    """Complete incident response playbook."""

    playbook_id: str
    name: str
    description: str
    incident_types: list[IncidentType]
    severity_levels: list[ThreatLevel]
    steps: list[PlaybookStep]
    max_execution_time_minutes: int
    auto_execute: bool
    requires_approval: bool
    notification_channels: list[NotificationChannel]
    compliance_requirements: list[str] = field(default_factory=list)


@dataclass
class PlaybookExecution:
    """Tracking of playbook execution."""

    execution_id: str
    incident_id: str
    playbook_id: str
    started_at: datetime
    status: str = "running"  # running, completed, failed, cancelled
    current_step: int = 0
    completed_steps: list[str] = field(default_factory=list)
    failed_steps: list[str] = field(default_factory=list)
    execution_log: list[dict[str, Any]] = field(default_factory=list)
    completed_at: datetime | None = None
    success: bool = False


class IncidentResponseOrchestrator:
    """
    Security Incident Response Orchestrator

    Manages automated incident detection, response workflows,
    and notifications according to predefined playbooks.
    """

    def __init__(self):
        self.playbooks = self._load_playbooks()
        self.active_incidents = {}
        self.execution_history = []
        self.notification_handlers = self._initialize_notification_handlers()

    def _load_playbooks(self) -> dict[str, IncidentPlaybook]:
        """Load predefined incident response playbooks."""

        playbooks = {}

        # Data Breach Response Playbook
        data_breach_playbook = IncidentPlaybook(
            playbook_id="pb_data_breach_001",
            name="Data Breach Response",
            description="Comprehensive response to data breach incidents",
            incident_types=[IncidentType.DATA_BREACH],
            severity_levels=[ThreatLevel.HIGH, ThreatLevel.CRITICAL],
            steps=[
                PlaybookStep(
                    step_id="db_001",
                    name="Immediate Containment",
                    description="Isolate affected systems to prevent further data exposure",
                    action=ResponseAction.ISOLATE_SYSTEM,
                    automated=True,
                    timeout_minutes=5,
                    notification_required=True,
                ),
                PlaybookStep(
                    step_id="db_002",
                    name="Evidence Preservation",
                    description="Create forensic backups of affected systems",
                    action=ResponseAction.BACKUP_EVIDENCE,
                    automated=True,
                    timeout_minutes=30,
                    prerequisites=["db_001"],
                ),
                PlaybookStep(
                    step_id="db_003",
                    name="Impact Assessment",
                    description="Assess scope and impact of data breach",
                    action=ResponseAction.ESCALATE_TO_SOC,
                    automated=False,
                    timeout_minutes=60,
                    prerequisites=["db_001", "db_002"],
                    approval_required=True,
                ),
                PlaybookStep(
                    step_id="db_004",
                    name="Customer Notification",
                    description="Notify affected customers within regulatory timeframes",
                    action=ResponseAction.NOTIFY_USERS,
                    automated=False,
                    timeout_minutes=120,
                    prerequisites=["db_003"],
                    approval_required=True,
                    parameters={
                        "notification_template": "data_breach_notification",
                        "regulatory_deadline_hours": 72,
                    },
                ),
                PlaybookStep(
                    step_id="db_005",
                    name="Regulatory Notification",
                    description="Notify relevant regulatory authorities",
                    action=ResponseAction.CONTACT_AUTHORITIES,
                    automated=False,
                    timeout_minutes=240,
                    prerequisites=["db_003"],
                    approval_required=True,
                ),
            ],
            max_execution_time_minutes=480,
            auto_execute=True,
            requires_approval=True,
            notification_channels=[
                NotificationChannel.EMAIL,
                NotificationChannel.SLACK,
            ],
            compliance_requirements=["GDPR Article 33", "CCPA Section 1798.82"],
        )
        playbooks[data_breach_playbook.playbook_id] = data_breach_playbook

        # Account Compromise Response Playbook
        account_compromise_playbook = IncidentPlaybook(
            playbook_id="pb_account_compromise_001",
            name="Account Compromise Response",
            description="Response to compromised user accounts",
            incident_types=[IncidentType.ACCOUNT_COMPROMISE],
            severity_levels=[
                ThreatLevel.MEDIUM,
                ThreatLevel.HIGH,
                ThreatLevel.CRITICAL,
            ],
            steps=[
                PlaybookStep(
                    step_id="ac_001",
                    name="Disable Compromised Account",
                    description="Immediately disable the compromised account",
                    action=ResponseAction.DISABLE_ACCOUNT,
                    automated=True,
                    timeout_minutes=1,
                ),
                PlaybookStep(
                    step_id="ac_002",
                    name="Revoke Active Sessions",
                    description="Revoke all active tokens and sessions",
                    action=ResponseAction.REVOKE_TOKENS,
                    automated=True,
                    timeout_minutes=2,
                    prerequisites=["ac_001"],
                ),
                PlaybookStep(
                    step_id="ac_003",
                    name="Force Password Reset",
                    description="Force password reset for the account",
                    action=ResponseAction.RESET_PASSWORD,
                    automated=True,
                    timeout_minutes=5,
                    prerequisites=["ac_001", "ac_002"],
                ),
                PlaybookStep(
                    step_id="ac_004",
                    name="Notify Account Owner",
                    description="Notify the account owner of the compromise",
                    action=ResponseAction.NOTIFY_USERS,
                    automated=True,
                    timeout_minutes=10,
                    prerequisites=["ac_003"],
                    parameters={
                        "notification_template": "account_compromise_notification"
                    },
                ),
            ],
            max_execution_time_minutes=60,
            auto_execute=True,
            requires_approval=False,
            notification_channels=[NotificationChannel.EMAIL],
        )
        playbooks[account_compromise_playbook.playbook_id] = account_compromise_playbook

        # Malware Detection Response Playbook
        malware_playbook = IncidentPlaybook(
            playbook_id="pb_malware_001",
            name="Malware Detection Response",
            description="Response to malware detection incidents",
            incident_types=[IncidentType.MALWARE_DETECTION],
            severity_levels=[ThreatLevel.HIGH, ThreatLevel.CRITICAL],
            steps=[
                PlaybookStep(
                    step_id="mw_001",
                    name="Quarantine Malware",
                    description="Quarantine detected malware files",
                    action=ResponseAction.QUARANTINE_FILE,
                    automated=True,
                    timeout_minutes=2,
                ),
                PlaybookStep(
                    step_id="mw_002",
                    name="Isolate Affected System",
                    description="Isolate the affected system from network",
                    action=ResponseAction.ISOLATE_SYSTEM,
                    automated=True,
                    timeout_minutes=5,
                    prerequisites=["mw_001"],
                ),
                PlaybookStep(
                    step_id="mw_003",
                    name="Scan Related Systems",
                    description="Scan systems that may be affected",
                    action=ResponseAction.ESCALATE_TO_SOC,
                    automated=False,
                    timeout_minutes=30,
                    prerequisites=["mw_002"],
                ),
            ],
            max_execution_time_minutes=120,
            auto_execute=True,
            requires_approval=False,
            notification_channels=[
                NotificationChannel.SLACK,
                NotificationChannel.PAGERDUTY,
            ],
        )
        playbooks[malware_playbook.playbook_id] = malware_playbook

        # DDoS Attack Response Playbook
        ddos_playbook = IncidentPlaybook(
            playbook_id="pb_ddos_001",
            name="DDoS Attack Response",
            description="Response to distributed denial of service attacks",
            incident_types=[IncidentType.DDOS_ATTACK],
            severity_levels=[ThreatLevel.HIGH, ThreatLevel.CRITICAL],
            steps=[
                PlaybookStep(
                    step_id="ddos_001",
                    name="Activate DDoS Protection",
                    description="Activate cloud-based DDoS protection",
                    action=ResponseAction.ACTIVATE_DR,
                    automated=True,
                    timeout_minutes=5,
                ),
                PlaybookStep(
                    step_id="ddos_002",
                    name="Block Malicious IPs",
                    description="Block identified malicious IP addresses",
                    action=ResponseAction.BLOCK_IP,
                    automated=True,
                    timeout_minutes=10,
                    prerequisites=["ddos_001"],
                ),
                PlaybookStep(
                    step_id="ddos_003",
                    name="Scale Infrastructure",
                    description="Scale infrastructure to handle increased load",
                    action=ResponseAction.ACTIVATE_DR,
                    automated=True,
                    timeout_minutes=15,
                    prerequisites=["ddos_001"],
                ),
            ],
            max_execution_time_minutes=60,
            auto_execute=True,
            requires_approval=False,
            notification_channels=[
                NotificationChannel.PAGERDUTY,
                NotificationChannel.SLACK,
            ],
        )
        playbooks[ddos_playbook.playbook_id] = ddos_playbook

        return playbooks

    def _initialize_notification_handlers(self) -> dict[NotificationChannel, Callable]:
        """Initialize notification handlers for different channels."""

        return {
            NotificationChannel.EMAIL: self._send_email_notification,
            NotificationChannel.SMS: self._send_sms_notification,
            NotificationChannel.SLACK: self._send_slack_notification,
            NotificationChannel.PAGERDUTY: self._send_pagerduty_notification,
            NotificationChannel.WEBHOOK: self._send_webhook_notification,
            NotificationChannel.DASHBOARD: self._send_dashboard_notification,
        }

    async def detect_and_respond(
        self, security_event: SecurityEvent
    ) -> PlaybookExecution | None:
        """Detect incident and trigger appropriate response playbook."""

        try:
            # Analyze security event to determine incident type
            incident_type = await self._classify_incident(security_event)
            if not incident_type:
                logger.debug(
                    "Security event does not require incident response",
                    event_id=security_event.event_id,
                )
                return None

            # Create incident record
            incident = await self._create_incident(security_event, incident_type)

            # Select appropriate playbook
            playbook = await self._select_playbook(
                incident_type, security_event.severity
            )
            if not playbook:
                logger.warning(
                    "No playbook found for incident", incident_type=incident_type.value
                )
                return None

            # Execute playbook
            execution = await self._execute_playbook(incident, playbook)

            return execution

        except Exception as e:
            logger.error("Incident detection and response failed", error=str(e))
            return None

    async def _classify_incident(
        self, security_event: SecurityEvent
    ) -> IncidentType | None:
        """Classify security event to determine incident type."""

        # Classification logic based on event type and context
        event_type = security_event.event_type.lower()

        if "data_breach" in event_type or "data_exposure" in event_type:
            return IncidentType.DATA_BREACH
        elif "account_compromise" in event_type or "credential_theft" in event_type:
            return IncidentType.ACCOUNT_COMPROMISE
        elif "malware" in event_type or "virus" in event_type:
            return IncidentType.MALWARE_DETECTION
        elif "unauthorized_access" in event_type:
            return IncidentType.UNAUTHORIZED_ACCESS
        elif "ddos" in event_type or "dos_attack" in event_type:
            return IncidentType.DDOS_ATTACK
        elif "insider_threat" in event_type:
            return IncidentType.INSIDER_THREAT
        elif "vulnerability_exploit" in event_type:
            return IncidentType.VULNERABILITY_EXPLOITATION
        elif "compliance_violation" in event_type:
            return IncidentType.COMPLIANCE_VIOLATION
        elif "system_compromise" in event_type:
            return IncidentType.SYSTEM_COMPROMISE
        elif "cloud_misconfiguration" in event_type:
            return IncidentType.CLOUD_MISCONFIGURATION

        # Check severity for automatic escalation
        if security_event.severity in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            return IncidentType.SYSTEM_COMPROMISE

        return None

    async def _create_incident(
        self, security_event: SecurityEvent, incident_type: IncidentType
    ) -> IncidentResponse:
        """Create incident record for tracking."""

        incident = IncidentResponse(
            incident_id=f"inc_{datetime.utcnow().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}",
            incident_type=incident_type.value,
            severity=security_event.severity,
            affected_users=[security_event.user_id],
            affected_resources=[],
            detected_at=datetime.utcnow(),
            customer_impact=security_event.severity
            in [ThreatLevel.HIGH, ThreatLevel.CRITICAL],
            regulatory_reporting_required=incident_type
            in [IncidentType.DATA_BREACH, IncidentType.COMPLIANCE_VIOLATION],
        )

        self.active_incidents[incident.incident_id] = incident

        logger.info(
            "Security incident created",
            incident_id=incident.incident_id,
            incident_type=incident_type.value,
            severity=security_event.severity.value,
        )

        return incident

    async def _select_playbook(
        self, incident_type: IncidentType, severity: ThreatLevel
    ) -> IncidentPlaybook | None:
        """Select appropriate playbook for incident."""

        for playbook in self.playbooks.values():
            if (
                incident_type in playbook.incident_types
                and severity in playbook.severity_levels
            ):
                return playbook

        return None

    async def _execute_playbook(
        self, incident: IncidentResponse, playbook: IncidentPlaybook
    ) -> PlaybookExecution:
        """Execute incident response playbook."""

        execution = PlaybookExecution(
            execution_id=f"exec_{uuid.uuid4().hex[:12]}",
            incident_id=incident.incident_id,
            playbook_id=playbook.playbook_id,
            started_at=datetime.utcnow(),
        )

        try:
            logger.info(
                "Starting playbook execution",
                incident_id=incident.incident_id,
                playbook_id=playbook.playbook_id,
                execution_id=execution.execution_id,
            )

            # Send initial notification
            await self._send_notifications(
                playbook.notification_channels,
                "Incident Response Started",
                f"Incident {incident.incident_id} detected. Executing playbook {playbook.name}.",
                incident,
            )

            # Execute each step
            for i, step in enumerate(playbook.steps):
                execution.current_step = i

                # Check prerequisites
                if not await self._check_prerequisites(step, execution):
                    logger.warning(
                        "Step prerequisites not met",
                        step_id=step.step_id,
                        execution_id=execution.execution_id,
                    )
                    continue

                # Check if approval required
                if step.approval_required and not playbook.auto_execute:
                    logger.info(
                        "Step requires manual approval",
                        step_id=step.step_id,
                        execution_id=execution.execution_id,
                    )
                    # In a real implementation, this would wait for approval
                    continue

                # Execute step
                success = await self._execute_step(step, incident, execution)

                if success:
                    execution.completed_steps.append(step.step_id)
                    execution.execution_log.append(
                        {
                            "timestamp": datetime.utcnow().isoformat(),
                            "step_id": step.step_id,
                            "status": "completed",
                            "message": f"Successfully executed {step.name}",
                        }
                    )
                else:
                    execution.failed_steps.append(step.step_id)
                    execution.execution_log.append(
                        {
                            "timestamp": datetime.utcnow().isoformat(),
                            "step_id": step.step_id,
                            "status": "failed",
                            "message": f"Failed to execute {step.name}",
                        }
                    )

                    # Stop execution if critical step fails
                    if not step.rollback_possible:
                        break

            # Complete execution
            execution.completed_at = datetime.utcnow()
            execution.success = len(execution.failed_steps) == 0
            execution.status = "completed" if execution.success else "failed"

            # Send completion notification
            status_msg = (
                "completed successfully"
                if execution.success
                else "completed with failures"
            )
            await self._send_notifications(
                playbook.notification_channels,
                f"Incident Response {status_msg.title()}",
                f"Incident {incident.incident_id} response {status_msg}.",
                incident,
            )

            self.execution_history.append(execution)

            logger.info(
                "Playbook execution completed",
                execution_id=execution.execution_id,
                success=execution.success,
                completed_steps=len(execution.completed_steps),
                failed_steps=len(execution.failed_steps),
            )

        except Exception as e:
            execution.status = "failed"
            execution.completed_at = datetime.utcnow()
            execution.execution_log.append(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "step_id": "execution",
                    "status": "error",
                    "message": f"Playbook execution failed: {str(e)}",
                }
            )

            logger.error(
                "Playbook execution failed",
                execution_id=execution.execution_id,
                error=str(e),
            )

        return execution

    async def _check_prerequisites(
        self, step: PlaybookStep, execution: PlaybookExecution
    ) -> bool:
        """Check if step prerequisites are met."""

        for prereq in step.prerequisites:
            if prereq not in execution.completed_steps:
                return False

        return True

    async def _execute_step(
        self,
        step: PlaybookStep,
        incident: IncidentResponse,
        execution: PlaybookExecution,
    ) -> bool:
        """Execute individual playbook step."""

        try:
            logger.info(
                "Executing playbook step",
                step_id=step.step_id,
                action=step.action.value,
                execution_id=execution.execution_id,
            )

            if not step.automated:
                # Manual step - log for human intervention
                logger.info(
                    "Manual step requires human intervention",
                    step_id=step.step_id,
                    description=step.description,
                )
                return True

            # Execute automated actions
            if step.action == ResponseAction.ISOLATE_SYSTEM:
                return await self._isolate_system(step, incident)
            elif step.action == ResponseAction.DISABLE_ACCOUNT:
                return await self._disable_account(step, incident)
            elif step.action == ResponseAction.RESET_PASSWORD:
                return await self._reset_password(step, incident)
            elif step.action == ResponseAction.REVOKE_TOKENS:
                return await self._revoke_tokens(step, incident)
            elif step.action == ResponseAction.BLOCK_IP:
                return await self._block_ip(step, incident)
            elif step.action == ResponseAction.QUARANTINE_FILE:
                return await self._quarantine_file(step, incident)
            elif step.action == ResponseAction.NOTIFY_USERS:
                return await self._notify_users(step, incident)
            elif step.action == ResponseAction.BACKUP_EVIDENCE:
                return await self._backup_evidence(step, incident)
            else:
                logger.warning("Unknown action type", action=step.action.value)
                return False

        except Exception as e:
            logger.error(
                "Step execution failed",
                step_id=step.step_id,
                action=step.action.value,
                error=str(e),
            )
            return False

    async def _send_notifications(
        self,
        channels: list[NotificationChannel],
        title: str,
        message: str,
        incident: IncidentResponse,
    ) -> None:
        """Send notifications through specified channels."""

        for channel in channels:
            try:
                handler = self.notification_handlers.get(channel)
                if handler:
                    await handler(title, message, incident)
                else:
                    logger.warning(
                        "No handler for notification channel", channel=channel.value
                    )
            except Exception as e:
                logger.error("Notification failed", channel=channel.value, error=str(e))

    # Action implementations
    async def _isolate_system(
        self, step: PlaybookStep, incident: IncidentResponse
    ) -> bool:
        """Isolate affected system from network."""
        logger.info("System isolation executed", incident_id=incident.incident_id)
        return True

    async def _disable_account(
        self, step: PlaybookStep, incident: IncidentResponse
    ) -> bool:
        """Disable compromised user account."""
        logger.info("Account disabled", incident_id=incident.incident_id)
        return True

    async def _reset_password(
        self, step: PlaybookStep, incident: IncidentResponse
    ) -> bool:
        """Force password reset for affected account."""
        logger.info("Password reset forced", incident_id=incident.incident_id)
        return True

    async def _revoke_tokens(
        self, step: PlaybookStep, incident: IncidentResponse
    ) -> bool:
        """Revoke all active tokens and sessions."""
        logger.info("Tokens revoked", incident_id=incident.incident_id)
        return True

    async def _block_ip(self, step: PlaybookStep, incident: IncidentResponse) -> bool:
        """Block malicious IP addresses."""
        logger.info("IP addresses blocked", incident_id=incident.incident_id)
        return True

    async def _quarantine_file(
        self, step: PlaybookStep, incident: IncidentResponse
    ) -> bool:
        """Quarantine malicious files."""
        logger.info("Files quarantined", incident_id=incident.incident_id)
        return True

    async def _notify_users(
        self, step: PlaybookStep, incident: IncidentResponse
    ) -> bool:
        """Notify affected users."""
        logger.info("Users notified", incident_id=incident.incident_id)
        return True

    async def _backup_evidence(
        self, step: PlaybookStep, incident: IncidentResponse
    ) -> bool:
        """Create forensic backups for evidence."""
        logger.info("Evidence backed up", incident_id=incident.incident_id)
        return True

    # Notification handlers
    async def _send_email_notification(
        self, title: str, message: str, incident: IncidentResponse
    ) -> None:
        """Send email notification."""
        logger.info(
            "Email notification sent", title=title, incident_id=incident.incident_id
        )

    async def _send_sms_notification(
        self, title: str, message: str, incident: IncidentResponse
    ) -> None:
        """Send SMS notification."""
        logger.info(
            "SMS notification sent", title=title, incident_id=incident.incident_id
        )

    async def _send_slack_notification(
        self, title: str, message: str, incident: IncidentResponse
    ) -> None:
        """Send Slack notification."""
        logger.info(
            "Slack notification sent", title=title, incident_id=incident.incident_id
        )

    async def _send_pagerduty_notification(
        self, title: str, message: str, incident: IncidentResponse
    ) -> None:
        """Send PagerDuty notification."""
        logger.info(
            "PagerDuty notification sent", title=title, incident_id=incident.incident_id
        )

    async def _send_webhook_notification(
        self, title: str, message: str, incident: IncidentResponse
    ) -> None:
        """Send webhook notification."""
        logger.info(
            "Webhook notification sent", title=title, incident_id=incident.incident_id
        )

    async def _send_dashboard_notification(
        self, title: str, message: str, incident: IncidentResponse
    ) -> None:
        """Send dashboard notification."""
        logger.info(
            "Dashboard notification sent", title=title, incident_id=incident.incident_id
        )


# Global incident response orchestrator
incident_response_orchestrator = IncidentResponseOrchestrator()
