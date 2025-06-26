"""
Zero Trust Security Framework

Comprehensive Zero Trust implementation with continuous verification,
trust score calculation, device assessment, and behavioral analysis.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from app.core.logging import get_logger
from app.schemas.user import AccessContext, DeviceInfo

logger = get_logger(__name__)


class TrustLevel(str, Enum):
    """Trust levels for Zero Trust assessment."""

    VERY_LOW = "very_low"  # 0-20%
    LOW = "low"  # 21-40%
    MEDIUM = "medium"  # 41-60%
    HIGH = "high"  # 61-80%
    VERY_HIGH = "very_high"  # 81-100%


class ZeroTrustPolicy(str, Enum):
    """Zero Trust access policies."""

    CRITICAL_SYSTEMS = "critical_systems"  # 99% trust required
    SENSITIVE_DATA = "sensitive_data"  # 80% trust required
    STANDARD_ACCESS = "standard_access"  # 60% trust required
    PUBLIC_ACCESS = "public_access"  # 30% trust required


class DeviceTrustStatus(str, Enum):
    """Device trust status levels."""

    MANAGED = "managed"  # Corporate managed device
    REGISTERED = "registered"  # User registered device
    UNREGISTERED = "unregistered"  # Unknown device
    COMPROMISED = "compromised"  # Known compromised device


class BehavioralRiskFactor(str, Enum):
    """Behavioral risk factors."""

    UNUSUAL_LOCATION = "unusual_location"
    UNUSUAL_TIME = "unusual_time"
    UNUSUAL_DEVICE = "unusual_device"
    RAPID_REQUESTS = "rapid_requests"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DATA_EXFILTRATION = "data_exfiltration"
    FAILED_AUTHENTICATIONS = "failed_authentications"
    SUSPICIOUS_USER_AGENT = "suspicious_user_agent"


@dataclass
class TrustFactors:
    """Trust calculation factors."""

    # Authentication Factors (0-1)
    authentication_strength: float = 0.0
    mfa_enabled: bool = False
    sso_authenticated: bool = False
    password_age_days: int = 0

    # Device Factors (0-1)
    device_trust_score: float = 0.0
    device_managed: bool = False
    device_encrypted: bool = False
    device_compliance: bool = False
    device_last_scan: datetime | None = None

    # Location Factors (0-1)
    location_trust_score: float = 0.0
    known_location: bool = False
    geolocation_risk: float = 0.0
    vpn_detected: bool = False

    # Behavioral Factors (0-1)
    behavioral_trust_score: float = 0.0
    access_pattern_normal: bool = True
    time_pattern_normal: bool = True
    velocity_normal: bool = True

    # Network Factors (0-1)
    network_trust_score: float = 0.0
    ip_reputation: float = 1.0
    threat_intelligence_score: float = 1.0

    # Session Factors (0-1)
    session_age_minutes: int = 0
    concurrent_sessions: int = 1
    privilege_level: float = 0.0


@dataclass
class TrustAssessment:
    """Complete trust assessment result."""

    user_id: int
    assessment_id: str
    timestamp: datetime

    # Overall Trust Score (0-1)
    trust_score: float
    trust_level: TrustLevel

    # Factor Scores
    trust_factors: TrustFactors

    # Risk Assessment
    risk_factors: list[BehavioralRiskFactor] = field(default_factory=list)
    risk_score: float = 0.0
    confidence_score: float = 0.0

    # Recommendations
    required_actions: list[str] = field(default_factory=list)
    session_restrictions: dict[str, Any] = field(default_factory=dict)
    next_verification_in: int = 3600  # seconds

    # Context
    access_context: AccessContext | None = None
    policy_applied: ZeroTrustPolicy | None = None


@dataclass
class DeviceFingerprint:
    """Device fingerprinting data."""

    device_id: str
    user_agent: str
    screen_resolution: str | None = None
    timezone: str | None = None
    language: str | None = None
    platform: str | None = None
    browser: str | None = None
    browser_version: str | None = None
    plugins: list[str] = field(default_factory=list)
    fonts: list[str] = field(default_factory=list)
    canvas_fingerprint: str | None = None
    webgl_fingerprint: str | None = None
    audio_fingerprint: str | None = None

    # Calculated fingerprint hash
    fingerprint_hash: str | None = None

    def calculate_fingerprint(self) -> str:
        """Calculate unique device fingerprint hash."""

        fingerprint_data = {
            "user_agent": self.user_agent,
            "screen_resolution": self.screen_resolution,
            "timezone": self.timezone,
            "language": self.language,
            "platform": self.platform,
            "browser": self.browser,
            "browser_version": self.browser_version,
            "plugins": sorted(self.plugins),
            "fonts": sorted(self.fonts),
            "canvas_fingerprint": self.canvas_fingerprint,
            "webgl_fingerprint": self.webgl_fingerprint,
            "audio_fingerprint": self.audio_fingerprint,
        }

        fingerprint_json = json.dumps(fingerprint_data, sort_keys=True)
        self.fingerprint_hash = hashlib.sha256(fingerprint_json.encode()).hexdigest()
        return self.fingerprint_hash


class ZeroTrustEngine:
    """
    Zero Trust Security Framework Engine

    Implements comprehensive Zero Trust security with continuous verification,
    trust score calculation, device assessment, and behavioral analysis.
    """

    def __init__(self) -> None:
        self.trust_cache: dict[str, Any] = {}
        self.device_registry: dict[str, Any] = {}
        self.behavioral_model: IsolationForest | None = None
        self.threat_intelligence_cache: dict[str, Any] = {}
        self.location_history: dict[int, list[dict[str, Any]]] = {}
        self.access_patterns: dict[str, Any] = {}
        self.scaler: StandardScaler | None = None

        # Initialize ML models for behavioral analysis
        self._initialize_behavioral_models()

    def _initialize_behavioral_models(self) -> None:
        """Initialize machine learning models for behavioral analysis."""

        try:
            # Isolation Forest for anomaly detection
            self.behavioral_model = IsolationForest(
                contamination=0.1,  # 10% expected anomalies
                random_state=42,
                n_estimators=100,
            )

            # Scaler for feature normalization
            self.scaler = StandardScaler()

            logger.info("Behavioral analysis models initialized")

        except Exception as e:
            logger.error(f"Failed to initialize behavioral models: {str(e)}")
            self.behavioral_model = None

    async def calculate_trust_score(
        self,
        user_id: int,
        access_context: AccessContext,
        device_fingerprint: DeviceFingerprint | None = None,
    ) -> TrustAssessment:
        """
        Calculate comprehensive trust score for user access request.

        This is the core Zero Trust function that evaluates all trust factors
        and returns a complete assessment with recommendations.
        """

        try:
            assessment_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()

            # Initialize trust factors
            trust_factors = TrustFactors()

            # Calculate individual trust components
            auth_score = await self._calculate_authentication_trust(
                user_id, access_context
            )
            device_score = await self._calculate_device_trust(
                user_id, access_context, device_fingerprint
            )
            location_score = await self._calculate_location_trust(
                user_id, access_context
            )
            behavioral_score = await self._calculate_behavioral_trust(
                user_id, access_context
            )
            network_score = await self._calculate_network_trust(access_context)
            session_score = await self._calculate_session_trust(user_id, access_context)

            # Update trust factors
            trust_factors.authentication_strength = auth_score
            trust_factors.device_trust_score = device_score
            trust_factors.location_trust_score = location_score
            trust_factors.behavioral_trust_score = behavioral_score
            trust_factors.network_trust_score = network_score

            # Calculate weighted overall trust score
            trust_score = await self._calculate_weighted_trust_score(trust_factors)
            trust_level = self._determine_trust_level(trust_score)

            # Identify risk factors
            risk_factors = await self._identify_risk_factors(
                user_id, access_context, trust_factors
            )
            risk_score = (
                len(risk_factors) / len(BehavioralRiskFactor) if risk_factors else 0.0
            )

            # Calculate confidence score based on data quality
            confidence_score = await self._calculate_confidence_score(
                access_context, trust_factors
            )

            # Generate recommendations
            required_actions = await self._generate_required_actions(
                trust_score, risk_factors
            )
            session_restrictions = await self._generate_session_restrictions(
                trust_score, risk_factors
            )
            next_verification = await self._calculate_next_verification_interval(
                trust_score
            )

            # Create assessment
            assessment = TrustAssessment(
                user_id=user_id,
                assessment_id=assessment_id,
                timestamp=timestamp,
                trust_score=trust_score,
                trust_level=trust_level,
                trust_factors=trust_factors,
                risk_factors=risk_factors,
                risk_score=risk_score,
                confidence_score=confidence_score,
                required_actions=required_actions,
                session_restrictions=session_restrictions,
                next_verification_in=next_verification,
                access_context=access_context,
            )

            # Cache assessment
            cache_key = f"trust_assessment_{user_id}_{assessment_id}"
            self.trust_cache[cache_key] = assessment

            logger.info(
                "Trust assessment completed",
                user_id=user_id,
                trust_score=trust_score,
                trust_level=trust_level.value,
                risk_factors_count=len(risk_factors),
                confidence_score=confidence_score,
            )

            return assessment

        except Exception as e:
            logger.error(f"Trust score calculation failed: {str(e)}")

            # Return minimal trust assessment on error
            return TrustAssessment(
                user_id=user_id,
                assessment_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                trust_score=0.0,
                trust_level=TrustLevel.VERY_LOW,
                trust_factors=TrustFactors(),
                required_actions=["require_mfa", "verify_device", "contact_admin"],
                next_verification_in=300,  # 5 minutes
            )

    async def _calculate_authentication_trust(
        self, user_id: int, context: AccessContext
    ) -> float:
        """Calculate authentication trust score (0-1)."""

        try:
            score = 0.0

            # Base authentication (password) = 0.3
            score += 0.3

            # MFA enabled = +0.4
            if getattr(context, "mfa_verified", False):
                score += 0.4

            # SSO authentication = +0.2
            if getattr(context, "sso_authenticated", False):
                score += 0.2

            # Recent authentication = +0.1
            auth_timestamp = getattr(context, "auth_timestamp", None)
            if auth_timestamp:
                auth_age = (datetime.utcnow() - auth_timestamp).total_seconds()
                if auth_age < 3600:  # Within 1 hour
                    score += 0.1

            return min(score, 1.0)

        except Exception as e:
            logger.error(f"Authentication trust calculation failed: {str(e)}")
            return 0.3  # Base password authentication

    async def _calculate_device_trust(
        self,
        user_id: int,
        context: AccessContext,
        device_fingerprint: DeviceFingerprint | None = None,
    ) -> float:
        """Calculate device trust score (0-1)."""

        try:
            score = 0.0
            device_info = context.device_info

            # Check device registration status
            device_status = await self._get_device_status(user_id, device_info)

            if device_status == DeviceTrustStatus.MANAGED:
                score += 0.5  # Corporate managed device
            elif device_status == DeviceTrustStatus.REGISTERED:
                score += 0.3  # User registered device
            elif device_status == DeviceTrustStatus.COMPROMISED:
                return 0.0  # Known compromised device
            else:
                score += 0.1  # Unknown device

            # Device compliance checks
            if getattr(device_info, "is_encrypted", False):
                score += 0.2

            if getattr(device_info, "antivirus_enabled", False):
                score += 0.1

            if getattr(device_info, "os_updated", False):
                score += 0.1

            # Device fingerprint consistency
            if device_fingerprint:
                consistency_score = await self._check_device_fingerprint_consistency(
                    user_id, device_fingerprint
                )
                score += consistency_score * 0.1

            return min(score, 1.0)

        except Exception as e:
            logger.error(f"Device trust calculation failed: {str(e)}")
            return 0.1

    async def _calculate_location_trust(
        self, user_id: int, context: AccessContext
    ) -> float:
        """Calculate location trust score (0-1)."""

        try:
            score = 0.5  # Neutral starting point

            if not context.geolocation:
                return 0.3  # Unknown location, reduced trust

            # Check if location is known/trusted
            known_locations = await self._get_user_known_locations(user_id)
            current_location = context.geolocation

            location_known = False
            for known_loc in known_locations:
                if (
                    self._calculate_location_distance(current_location, known_loc) < 50
                ):  # 50km radius
                    location_known = True
                    break

            if location_known:
                score += 0.3
            else:
                # Check for impossible travel (velocity analysis)
                last_location = await self._get_last_user_location(user_id)
                if last_location and context.timestamp:  # type: ignore
                    travel_analysis = await self._analyze_travel_velocity(
                        last_location,
                        current_location,
                        context.timestamp,  # type: ignore
                    )
                    if travel_analysis["impossible_travel"]:
                        score -= 0.4
                    elif travel_analysis["suspicious_travel"]:
                        score -= 0.2

            # Country/region risk assessment
            country_risk = await self._get_country_risk_score(
                current_location.get("country")
            )
            score -= country_risk * 0.2

            # VPN/Proxy detection
            if await self._detect_vpn_proxy(getattr(context, "source_ip", "")):
                score -= 0.1  # Slight reduction for VPN usage

            # Update location history
            if context.timestamp:  # type: ignore
                await self._update_location_history(
                    user_id,
                    current_location,
                    context.timestamp,  # type: ignore
                )

            return max(min(score, 1.0), 0.0)

        except Exception as e:
            logger.error(f"Location trust calculation failed: {str(e)}")
            return 0.3

    async def _calculate_behavioral_trust(
        self, user_id: int, context: AccessContext
    ) -> float:
        """Calculate behavioral trust score using ML analysis (0-1)."""

        try:
            # Get user's historical access patterns
            access_history = await self._get_user_access_history(user_id, days=30)

            if not access_history or len(access_history) < 10:
                return 0.5  # Insufficient data for behavioral analysis

            # Extract behavioral features
            current_features_list = await self._extract_behavioral_features(context)
            historical_features = [
                await self._extract_behavioral_features(
                    AccessContext(**access)  # type: ignore
                )
                for access in access_history
            ]

            if not self.behavioral_model or not historical_features:
                return 0.5  # Fallback to neutral score

            # Prepare data for ML model
            try:
                historical_array = np.array(historical_features)
                current_array = np.array([current_features_list])

                # Fit model on historical data
                self.behavioral_model.fit(historical_array)

                # Calculate anomaly score
                anomaly_score = self.behavioral_model.decision_function(current_array)[
                    0
                ]

                # Convert anomaly score to trust score (higher anomaly = lower trust)
                # Anomaly scores typically range from -0.5 to 0.5
                trust_score = max(0.0, min(1.0, 0.5 - anomaly_score))

                return trust_score

            except Exception as ml_error:
                logger.warning(f"ML behavioral analysis failed: {str(ml_error)}")
                return await self._fallback_behavioral_analysis(
                    user_id, context, access_history
                )

        except Exception as e:
            logger.error(f"Behavioral trust calculation failed: {str(e)}")
            return 0.5

    async def _calculate_network_trust(self, context: AccessContext) -> float:
        """Calculate network trust score (0-1)."""

        try:
            score = 0.7  # Neutral starting point
            source_ip = getattr(context, "source_ip", "")
            if not source_ip:
                return 0.3  # Unknown IP, reduced trust

            # IP reputation check
            ip_reputation = await self._get_ip_reputation(source_ip)
            score += (ip_reputation - 0.5) * 0.4  # Scale reputation to trust impact

            # Threat intelligence check
            threat_intel = await self._check_threat_intelligence(source_ip)
            if threat_intel.get("malicious", False):
                score -= 0.5
            elif threat_intel.get("suspicious", False):
                score -= 0.2

            # Network type assessment
            network_type = await self._identify_network_type(source_ip)
            if network_type == "corporate":
                score += 0.2
            elif network_type == "residential":
                score += 0.1
            elif network_type == "mobile":
                score += 0.05
            elif network_type in ["tor", "proxy", "hosting"]:
                score -= 0.3

            # Rate limiting / abuse detection
            request_rate = await self._check_request_rate(source_ip)
            if request_rate > 100:  # requests per minute
                score -= 0.2
            elif request_rate > 50:
                score -= 0.1

            return max(min(score, 1.0), 0.0)

        except Exception as e:
            logger.error(f"Network trust calculation failed: {str(e)}")
            return 0.5

    async def _calculate_session_trust(
        self, user_id: int, context: AccessContext
    ) -> float:
        """Calculate session-based trust factors (0-1)."""

        try:
            score = 0.8  # High starting point for session factors
            session_start_time = getattr(context, "session_start_time", None)
            # Session age
            if session_start_time:
                session_age = (datetime.utcnow() - session_start_time).total_seconds()
                if session_age > 28800:  # 8 hours
                    score -= 0.3
                elif session_age > 14400:  # 4 hours
                    score -= 0.1

            # Concurrent sessions
            concurrent_sessions = await self._count_concurrent_sessions(user_id)
            if concurrent_sessions > 5:
                score -= 0.2
            elif concurrent_sessions > 3:
                score -= 0.1

            # Privilege level
            privilege_level = await self._get_user_privilege_level(user_id)
            if privilege_level > 0.8:  # High privilege user
                score -= 0.1  # Higher scrutiny for privileged users

            return max(min(score, 1.0), 0.0)

        except Exception as e:
            logger.error(f"Session trust calculation failed: {str(e)}")
            return 0.7

    async def _calculate_weighted_trust_score(
        self, trust_factors: TrustFactors
    ) -> float:
        """Calculate weighted overall trust score from individual factors."""

        try:
            # Define weights for different trust factors
            weights = {
                "authentication": 0.25,  # 25% - Strong authentication is critical
                "device": 0.20,  # 20% - Device trust is important
                "location": 0.15,  # 15% - Location patterns matter
                "behavioral": 0.20,  # 20% - Behavioral analysis is key
                "network": 0.15,  # 15% - Network reputation matters
                "session": 0.05,  # 5% - Session factors are supplementary
            }

            # Calculate weighted score
            weighted_score = (
                trust_factors.authentication_strength * weights["authentication"]
                + trust_factors.device_trust_score * weights["device"]
                + trust_factors.location_trust_score * weights["location"]
                + trust_factors.behavioral_trust_score * weights["behavioral"]
                + trust_factors.network_trust_score * weights["network"]
                + (trust_factors.session_age_minutes / 480.0)
                * weights["session"]  # Normalize session age
            )

            return max(min(weighted_score, 1.0), 0.0)

        except Exception as e:
            logger.error(f"Weighted trust score calculation failed: {str(e)}")
            return 0.0

    def _determine_trust_level(self, trust_score: float) -> TrustLevel:
        """Determine trust level from numerical score."""

        if trust_score >= 0.81:
            return TrustLevel.VERY_HIGH
        elif trust_score >= 0.61:
            return TrustLevel.HIGH
        elif trust_score >= 0.41:
            return TrustLevel.MEDIUM
        elif trust_score >= 0.21:
            return TrustLevel.LOW
        else:
            return TrustLevel.VERY_LOW

    async def _identify_risk_factors(
        self, user_id: int, context: AccessContext, trust_factors: TrustFactors
    ) -> list[BehavioralRiskFactor]:
        """Identify specific risk factors based on context and trust factors."""

        risk_factors: list[BehavioralRiskFactor] = []

        try:
            # Location-based risks
            if trust_factors.location_trust_score < 0.3:
                risk_factors.append(BehavioralRiskFactor.UNUSUAL_LOCATION)

            # Time-based risks
            current_hour = (
                context.timestamp.hour if context.timestamp else datetime.utcnow().hour  # type: ignore
            )
            if current_hour < 6 or current_hour > 22:  # Outside business hours
                user_patterns = await self._get_user_time_patterns(user_id)
                if not user_patterns.get("night_access_normal", False):
                    risk_factors.append(BehavioralRiskFactor.UNUSUAL_TIME)

            # Device-based risks
            if trust_factors.device_trust_score < 0.3:
                risk_factors.append(BehavioralRiskFactor.UNUSUAL_DEVICE)

            # Behavioral risks
            if trust_factors.behavioral_trust_score < 0.3:
                # Check for rapid requests
                source_ip = getattr(context, "source_ip", "")
                request_rate = await self._check_request_rate(source_ip)
                if request_rate > 100:
                    risk_factors.append(BehavioralRiskFactor.RAPID_REQUESTS)

            # Authentication risks
            failed_attempts = await self._get_recent_failed_attempts(user_id)
            if failed_attempts > 3:
                risk_factors.append(BehavioralRiskFactor.FAILED_AUTHENTICATIONS)

            # User agent risks
            if context.user_agent:
                if await self._is_suspicious_user_agent(context.user_agent):
                    risk_factors.append(BehavioralRiskFactor.SUSPICIOUS_USER_AGENT)

            return risk_factors

        except Exception as e:
            logger.error(f"Risk factor identification failed: {str(e)}")
            return []

    async def _calculate_confidence_score(
        self, context: AccessContext, trust_factors: TrustFactors
    ) -> float:
        """Calculate confidence score based on data quality and completeness."""

        try:
            confidence = 0.0
            total_factors = 6  # Number of trust factor categories

            # Check data completeness
            if trust_factors.authentication_strength > 0:
                confidence += 1 / total_factors

            if trust_factors.device_trust_score > 0:
                confidence += 1 / total_factors

            if trust_factors.location_trust_score > 0:
                confidence += 1 / total_factors

            if trust_factors.behavioral_trust_score > 0:
                confidence += 1 / total_factors

            if trust_factors.network_trust_score > 0:
                confidence += 1 / total_factors

            if context.timestamp:  # type: ignore
                confidence += 1 / total_factors

            # Adjust for data quality
            if context.geolocation and len(context.geolocation) > 2:
                confidence += 0.1

            if context.device_info:
                confidence += 0.1

            return min(confidence, 1.0)

        except Exception as e:
            logger.error(f"Confidence score calculation failed: {str(e)}")
            return 0.5

    async def _generate_required_actions(
        self, trust_score: float, risk_factors: list[BehavioralRiskFactor]
    ) -> list[str]:
        """Generate required actions based on trust score and risk factors."""

        actions = []

        try:
            # Trust score based actions
            if trust_score < 0.3:
                actions.extend(["require_mfa", "verify_device", "contact_admin"])
            elif trust_score < 0.5:
                actions.extend(["require_mfa", "verify_device"])
            elif trust_score < 0.7:
                actions.append("require_mfa")

            # Risk factor based actions
            if BehavioralRiskFactor.UNUSUAL_LOCATION in risk_factors:
                actions.append("verify_location")

            if BehavioralRiskFactor.UNUSUAL_DEVICE in risk_factors:
                actions.append("register_device")

            if BehavioralRiskFactor.RAPID_REQUESTS in risk_factors:
                actions.append("rate_limit")

            if BehavioralRiskFactor.FAILED_AUTHENTICATIONS in risk_factors:
                actions.append("account_review")

            return list(set(actions))  # Remove duplicates

        except Exception as e:
            logger.error(f"Required actions generation failed: {str(e)}")
            return ["require_mfa"]

    async def _generate_session_restrictions(
        self, trust_score: float, risk_factors: list[BehavioralRiskFactor]
    ) -> dict[str, Any]:
        """Generate session restrictions based on trust assessment."""

        restrictions: dict[str, Any] = {}

        try:
            # Time-based restrictions
            if trust_score < 0.5:
                restrictions["max_session_duration"] = 1800  # 30 minutes
            elif trust_score < 0.7:
                restrictions["max_session_duration"] = 3600  # 1 hour
            else:
                restrictions["max_session_duration"] = 28800  # 8 hours

            # Access restrictions
            if trust_score < 0.3:
                restrictions["allowed_resources"] = ["public"]
                restrictions["require_approval"] = True
            elif trust_score < 0.6:
                restrictions["allowed_resources"] = ["public", "standard"]

            # Rate limiting
            if BehavioralRiskFactor.RAPID_REQUESTS in risk_factors:
                restrictions["rate_limit"] = 10  # requests per minute

            # IP restrictions
            if BehavioralRiskFactor.UNUSUAL_LOCATION in risk_factors:
                restrictions["ip_locked"] = True

            return restrictions

        except Exception as e:
            logger.error(f"Session restrictions generation failed: {str(e)}")
            return {"max_session_duration": 1800}

    async def _calculate_next_verification_interval(self, trust_score: float) -> int:
        """Calculate next verification interval in seconds."""

        try:
            # Higher trust = longer intervals
            if trust_score >= 0.9:
                return 7200  # 2 hours
            elif trust_score >= 0.8:
                return 3600  # 1 hour
            elif trust_score >= 0.6:
                return 1800  # 30 minutes
            elif trust_score >= 0.4:
                return 900  # 15 minutes
            else:
                return 300  # 5 minutes

        except Exception as e:
            logger.error(f"Next verification calculation failed: {str(e)}")
            return 1800  # Default 30 minutes

    # Helper methods for trust calculations

    async def _get_device_status(
        self, user_id: int, device_info: DeviceInfo
    ) -> DeviceTrustStatus:
        """Get device trust status from registry."""

        try:
            device_key = f"{user_id}_{device_info.device_type}_{device_info.device_id}"

            if device_key in self.device_registry:
                return self.device_registry[device_key]["status"]

            # Check if device is in compromised list
            if await self._is_device_compromised(device_info):
                return DeviceTrustStatus.COMPROMISED

            # Default to unregistered
            return DeviceTrustStatus.UNREGISTERED

        except Exception as e:
            logger.error(f"Device status check failed: {str(e)}")
            return DeviceTrustStatus.UNREGISTERED

    async def _check_device_fingerprint_consistency(
        self, user_id: int, fingerprint: DeviceFingerprint
    ) -> float:
        """Check device fingerprint consistency (0-1)."""

        try:
            # Get stored fingerprints for user
            stored_fingerprints = await self._get_user_device_fingerprints(user_id)

            if not stored_fingerprints:
                return 0.0  # No baseline for comparison

            current_hash = fingerprint.calculate_fingerprint()

            # Check for exact matches
            for stored_fp in stored_fingerprints:
                if stored_fp["fingerprint_hash"] == current_hash:
                    return 1.0  # Perfect match

            # Calculate similarity scores
            max_similarity = 0.0
            for stored_fp in stored_fingerprints:
                similarity = await self._calculate_fingerprint_similarity(
                    fingerprint, stored_fp
                )
                max_similarity = max(max_similarity, similarity)

            return max_similarity

        except Exception as e:
            logger.error(f"Fingerprint consistency check failed: {str(e)}")
            return 0.0

    async def _get_user_known_locations(self, user_id: int) -> list[dict[str, Any]]:
        """Get user's known/trusted locations."""

        try:
            if user_id not in self.location_history:
                return []

            # Return locations where user has accessed from multiple times
            location_counts: dict[str, int] = {}
            for access in self.location_history[user_id]:
                location_key = (
                    f"{access.get('country')}_{access.get('city', 'unknown')}"
                )
                location_counts[location_key] = location_counts.get(location_key, 0) + 1

            # Consider locations with 3+ accesses as "known"
            known_locations = []
            for access in self.location_history[user_id]:
                location_key = (
                    f"{access.get('country')}_{access.get('city', 'unknown')}"
                )
                if location_counts.get(location_key, 0) >= 3:
                    known_locations.append(access)

            return known_locations

        except Exception as e:
            logger.error(f"Known locations retrieval failed: {str(e)}")
            return []

    def _calculate_location_distance(
        self, loc1: dict[str, Any], loc2: dict[str, Any]
    ) -> float:
        """Calculate distance between two locations in kilometers."""

        try:
            from math import asin, cos, radians, sin, sqrt

            lat1, lon1 = loc1.get("latitude", 0.0), loc1.get("longitude", 0.0)
            lat2, lon2 = loc2.get("latitude", 0.0), loc2.get("longitude", 0.0)

            # Haversine formula
            lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(
                radians, [lat1, lon1, lat2, lon2]
            )
            dlat = lat2_rad - lat1_rad
            dlon = lon2_rad - lon1_rad
            a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
            c = 2 * asin(sqrt(a))
            r = 6371  # Radius of earth in kilometers

            return c * r

        except Exception as e:
            logger.error(f"Location distance calculation failed: {str(e)}")
            return float("inf")  # Return large distance on error

    # Placeholder methods for external integrations
    # These would be implemented with actual data sources in production

    async def _get_last_user_location(self, user_id: int) -> dict[str, Any] | None:
        """Get user's last known location."""
        if user_id in self.location_history and self.location_history[user_id]:
            return self.location_history[user_id][-1]
        return None

    async def _analyze_travel_velocity(
        self,
        last_location: dict[str, Any],
        current_location: dict[str, Any],
        current_time: datetime,
    ) -> dict[str, Any]:
        """Analyze travel velocity for impossible travel detection."""

        try:
            distance = self._calculate_location_distance(
                last_location, current_location
            )
            last_timestamp = last_location.get("timestamp")
            if not isinstance(last_timestamp, datetime):
                return {"impossible_travel": False, "suspicious_travel": False}

            time_diff_seconds = (current_time - last_timestamp).total_seconds()
            time_diff_hours = time_diff_seconds / 3600.0

            if time_diff_hours <= 0:
                return {"impossible_travel": False, "suspicious_travel": False}

            velocity = distance / time_diff_hours  # km/h

            # Impossible travel: >1000 km/h (faster than commercial aircraft)
            # Suspicious travel: >500 km/h (very fast travel)
            return {
                "impossible_travel": velocity > 1000,
                "suspicious_travel": velocity > 500,
                "velocity_kmh": velocity,
            }

        except Exception as e:
            logger.error(f"Travel velocity analysis failed: {str(e)}")
            return {"impossible_travel": False, "suspicious_travel": False}

    async def _get_country_risk_score(self, country: str | None) -> float:
        """Get risk score for country (0-1, higher = more risky)."""

        # This would integrate with threat intelligence feeds
        high_risk_countries = ["CN", "RU", "KP", "IR"]  # Example
        medium_risk_countries = ["PK", "BD", "NG"]  # Example

        if not country:
            return 0.3  # Unknown country, medium risk

        if country in high_risk_countries:
            return 0.8
        elif country in medium_risk_countries:
            return 0.5
        else:
            return 0.1  # Low risk for most countries

    async def _detect_vpn_proxy(self, ip_address: str) -> bool:
        """Detect if IP is from VPN/proxy service."""

        # This would integrate with VPN detection services
        # For now, return False (no VPN detected)
        return False

    async def _update_location_history(
        self, user_id: int, location: dict[str, Any], timestamp: datetime
    ) -> None:
        """Update user's location history."""

        if user_id not in self.location_history:
            self.location_history[user_id] = []

        location_entry = {**location, "timestamp": timestamp}
        self.location_history[user_id].append(location_entry)

        # Keep only last 100 locations
        if len(self.location_history[user_id]) > 100:
            self.location_history[user_id] = self.location_history[user_id][-100:]

    async def _get_user_access_history(
        self, user_id: int, days: int = 30
    ) -> list[dict[str, Any]]:
        """Get user's access history for behavioral analysis."""

        # This would query the database for user's access history
        # For now, return empty list
        return []

    async def _extract_behavioral_features(self, context: AccessContext) -> list[float]:
        """Extract behavioral features for ML analysis."""

        try:
            features: list[float] = []
            timestamp = getattr(context, "timestamp", datetime.utcnow())
            # Time-based features
            hour = timestamp.hour
            day_of_week = timestamp.weekday()
            features.extend([hour / 24.0, day_of_week / 7.0])

            # Location features (if available)
            if context.geolocation:
                lat = (
                    context.geolocation.get("latitude", 0.0) / 90.0
                )  # Normalize to -1 to 1
                lon = (
                    context.geolocation.get("longitude", 0.0) / 180.0
                )  # Normalize to -1 to 1
                features.extend([lat, lon])
            else:
                features.extend([0.0, 0.0])

            # Device features
            if context.device_info:
                device_type_score = {"desktop": 0.8, "mobile": 0.6, "tablet": 0.4}.get(
                    context.device_info.device_type, 0.5
                )
                features.append(device_type_score)
            else:
                features.append(0.5)

            # Network features
            features.append(getattr(context, "risk_score", 0.5))

            return features

        except Exception as e:
            logger.error(f"Feature extraction failed: {str(e)}")
            return [0.5] * 6  # Return neutral features

    async def _fallback_behavioral_analysis(
        self, user_id: int, context: AccessContext, access_history: list[dict[str, Any]]
    ) -> float:
        """Fallback behavioral analysis when ML model fails."""

        try:
            score = 0.5  # Neutral starting point
            timestamp = getattr(context, "timestamp", datetime.utcnow())
            # Simple time pattern analysis
            current_hour = timestamp.hour
            historical_hours = [
                access.get("hour", 12)
                for access in access_history
                if isinstance(access.get("hour"), int)
            ]

            if historical_hours:
                # Check if current hour is within normal range
                hour_variance = (
                    np.var(historical_hours) if len(historical_hours) > 1 else 0.0
                )
                hour_mean = np.mean(historical_hours)

                if abs(current_hour - hour_mean) > 2 * np.sqrt(hour_variance + 1):
                    score -= 0.2  # Unusual time

            return max(min(score, 1.0), 0.0)

        except Exception as e:
            logger.error(f"Fallback behavioral analysis failed: {str(e)}")
            return 0.5

    # Additional placeholder methods for completeness

    async def _get_ip_reputation(self, ip_address: str) -> float:
        """Get IP reputation score (0-1, higher = better reputation)."""
        return 0.8  # Default good reputation

    async def _check_threat_intelligence(self, ip_address: str) -> dict[str, Any]:
        """Check IP against threat intelligence feeds."""
        return {"malicious": False, "suspicious": False}

    async def _identify_network_type(self, ip_address: str) -> str:
        """Identify network type (corporate, residential, mobile, etc.)."""
        return "residential"  # Default

    async def _check_request_rate(self, ip_address: str) -> int:
        """Check request rate for IP address."""
        return 10  # Default low rate

    async def _count_concurrent_sessions(self, user_id: int) -> int:
        """Count concurrent sessions for user."""
        return 1  # Default single session

    async def _get_user_privilege_level(self, user_id: int) -> float:
        """Get user privilege level (0-1)."""
        return 0.3  # Default standard user

    async def _get_user_time_patterns(self, user_id: int) -> dict[str, Any]:
        """Get user's typical access time patterns."""
        return {"night_access_normal": False}

    async def _get_recent_failed_attempts(self, user_id: int) -> int:
        """Get recent failed authentication attempts."""
        return 0  # Default no failures

    async def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is suspicious."""
        suspicious_patterns = ["bot", "crawler", "scanner", "curl", "wget"]
        return any(pattern in user_agent.lower() for pattern in suspicious_patterns)

    async def _is_device_compromised(self, device_info: DeviceInfo) -> bool:
        """Check if device is known to be compromised."""
        return False  # Default not compromised

    async def _get_user_device_fingerprints(self, user_id: int) -> list[dict[str, Any]]:
        """Get stored device fingerprints for user."""
        return []  # Default no stored fingerprints

    async def _calculate_fingerprint_similarity(
        self, fp1: DeviceFingerprint, fp2: dict[str, Any]
    ) -> float:
        """Calculate similarity between device fingerprints."""
        return 0.0  # Default no similarity


# Global Zero Trust engine instance
zero_trust_engine = ZeroTrustEngine()
