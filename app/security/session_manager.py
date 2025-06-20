"""
Enterprise Session Management with Security Controls

Advanced session management with fixation protection, concurrent session limits,
and comprehensive security monitoring.
"""

import asyncio
import json
import hashlib
import secrets
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

import redis.asyncio as redis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SessionState(str, Enum):
    """Session states."""
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    SUSPICIOUS = "suspicious"
    LOCKED = "locked"


@dataclass
class SessionInfo:
    """Session information."""
    
    session_id: str
    user_id: int
    state: SessionState
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    
    # Security attributes
    ip_address: str
    user_agent: str
    device_fingerprint: Optional[str] = None
    geolocation: Dict[str, str] = field(default_factory=dict)
    
    # Session security
    csrf_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    session_key: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    
    # Tracking
    login_method: str = "password"  # "password", "sso", "2fa", "api_key"
    risk_score: float = 0.0
    activity_count: int = 0
    failed_attempts: int = 0
    
    # Metadata
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class SessionActivity:
    """Session activity record."""
    
    activity_id: str
    session_id: str
    user_id: int
    timestamp: datetime
    activity_type: str  # "login", "logout", "api_call", "page_view", "action"
    ip_address: str
    user_agent: str
    endpoint: Optional[str] = None
    success: bool = True
    risk_score: float = 0.0
    metadata: Dict[str, str] = field(default_factory=dict)


class EnterpriseSessionManager:
    """
    Enterprise session manager with advanced security features.
    
    Features:
    - Session fixation protection
    - Concurrent session limits
    - Geographic anomaly detection
    - Device fingerprinting
    - Session hijacking prevention
    - Automatic session rotation
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.session_prefix = "webagent:session:"
        self.user_sessions_prefix = "webagent:user_sessions:"
        self.activity_prefix = "webagent:activity:"
        self.stats_prefix = "webagent:session_stats:"
        
        # Configuration
        self.max_concurrent_sessions = getattr(settings, 'MAX_CONCURRENT_SESSIONS', 5)
        self.session_timeout = getattr(settings, 'MAX_SESSION_DURATION_HOURS', 24) * 3600
        self.activity_timeout = 1800  # 30 minutes of inactivity
        self.rotation_interval = 3600  # 1 hour
        
    async def initialize(self) -> None:
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=30
            )
            
            await self.redis_client.ping()
            logger.info("Enterprise session manager initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize session manager: {str(e)}")
            self.redis_client = None
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
    
    def _generate_session_id(self) -> str:
        """Generate secure session ID."""
        timestamp = str(int(datetime.utcnow().timestamp()))
        random_part = secrets.token_urlsafe(32)
        return hashlib.sha256(f"{timestamp}:{random_part}".encode()).hexdigest()
    
    def _get_session_key(self, session_id: str) -> str:
        """Get Redis key for session."""
        return f"{self.session_prefix}{session_id}"
    
    def _get_user_sessions_key(self, user_id: int) -> str:
        """Get Redis key for user sessions."""
        return f"{self.user_sessions_prefix}{user_id}"
    
    def _get_activity_key(self, session_id: str) -> str:
        """Get Redis key for session activity."""
        return f"{self.activity_prefix}{session_id}"
    
    def _calculate_device_fingerprint(self, user_agent: str, additional_headers: Dict[str, str] = None) -> str:
        """Calculate device fingerprint."""
        fingerprint_data = user_agent
        
        if additional_headers:
            # Add relevant headers for fingerprinting
            relevant_headers = ['accept-language', 'accept-encoding', 'accept', 'dnt']
            for header in relevant_headers:
                if header in additional_headers:
                    fingerprint_data += f":{additional_headers[header]}"
        
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    
    async def create_session(
        self,
        user_id: int,
        ip_address: str,
        user_agent: str,
        login_method: str = "password",
        geolocation: Dict[str, str] = None,
        additional_headers: Dict[str, str] = None,
        force_new: bool = False
    ) -> Optional[SessionInfo]:
        """
        Create new session with fixation protection.
        
        Args:
            user_id: User ID
            ip_address: Client IP address
            user_agent: Client user agent
            login_method: Authentication method used
            geolocation: Client geolocation data
            additional_headers: Additional headers for fingerprinting
            force_new: Force creation even if limit exceeded
            
        Returns:
            SessionInfo: New session info or None if failed
        """
        try:
            if not self.redis_client:
                logger.error("Session manager not initialized")
                return None
            
            # Check concurrent session limit
            if not force_new:
                active_sessions = await self.get_user_active_sessions(user_id)
                if len(active_sessions) >= self.max_concurrent_sessions:
                    # Terminate oldest session
                    oldest_session = min(active_sessions, key=lambda s: s.last_activity)
                    await self.terminate_session(oldest_session.session_id, "concurrent_limit_exceeded")
            
            # Generate new session ID (prevents fixation)
            session_id = self._generate_session_id()
            
            # Create session info
            now = datetime.utcnow()
            session_info = SessionInfo(
                session_id=session_id,
                user_id=user_id,
                state=SessionState.ACTIVE,
                created_at=now,
                last_activity=now,
                expires_at=now + timedelta(seconds=self.session_timeout),
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=self._calculate_device_fingerprint(user_agent, additional_headers),
                geolocation=geolocation or {},
                login_method=login_method
            )
            
            # Calculate initial risk score
            session_info.risk_score = await self._calculate_session_risk(session_info)
            
            # Store session in Redis
            session_key = self._get_session_key(session_id)
            session_data = {
                "session_id": session_info.session_id,
                "user_id": session_info.user_id,
                "state": session_info.state.value,
                "created_at": session_info.created_at.isoformat(),
                "last_activity": session_info.last_activity.isoformat(),
                "expires_at": session_info.expires_at.isoformat(),
                "ip_address": session_info.ip_address,
                "user_agent": session_info.user_agent,
                "device_fingerprint": session_info.device_fingerprint,
                "geolocation": json.dumps(session_info.geolocation),
                "csrf_token": session_info.csrf_token,
                "session_key": session_info.session_key,
                "login_method": session_info.login_method,
                "risk_score": session_info.risk_score,
                "activity_count": session_info.activity_count,
                "failed_attempts": session_info.failed_attempts,
                "metadata": json.dumps(session_info.metadata)
            }
            
            # Use pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Store session
            pipe.hset(session_key, mapping=session_data)
            pipe.expire(session_key, self.session_timeout)
            
            # Add to user's active sessions
            user_sessions_key = self._get_user_sessions_key(user_id)
            pipe.sadd(user_sessions_key, session_id)
            pipe.expire(user_sessions_key, self.session_timeout)
            
            # Log session creation activity
            activity = SessionActivity(
                activity_id=secrets.token_urlsafe(16),
                session_id=session_id,
                user_id=user_id,
                timestamp=now,
                activity_type="login",
                ip_address=ip_address,
                user_agent=user_agent,
                success=True,
                risk_score=session_info.risk_score,
                metadata={"login_method": login_method}
            )
            
            activity_key = self._get_activity_key(session_id)
            activity_data = {
                "activity_id": activity.activity_id,
                "timestamp": activity.timestamp.isoformat(),
                "activity_type": activity.activity_type,
                "ip_address": activity.ip_address,
                "user_agent": activity.user_agent,
                "endpoint": activity.endpoint or "",
                "success": str(activity.success),
                "risk_score": activity.risk_score,
                "metadata": json.dumps(activity.metadata)
            }
            
            pipe.lpush(activity_key, json.dumps(activity_data))
            pipe.ltrim(activity_key, 0, 100)  # Keep last 100 activities
            pipe.expire(activity_key, self.session_timeout)
            
            # Update statistics
            stats_key = f"{self.stats_prefix}daily:{now.strftime('%Y-%m-%d')}"
            pipe.hincrby(stats_key, "sessions_created", 1)
            pipe.hincrby(stats_key, f"login_method:{login_method}", 1)
            pipe.expire(stats_key, 86400 * 7)  # Keep stats for 7 days
            
            await pipe.execute()
            
            logger.info(
                "Session created",
                session_id=session_id[:12],
                user_id=user_id,
                ip_address=ip_address,
                risk_score=session_info.risk_score
            )
            
            return session_info
            
        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            return None
    
    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information."""
        try:
            if not self.redis_client:
                return None
            
            session_key = self._get_session_key(session_id)
            session_data = await self.redis_client.hgetall(session_key)
            
            if not session_data:
                return None
            
            # Parse session data
            session_info = SessionInfo(
                session_id=session_data["session_id"],
                user_id=int(session_data["user_id"]),
                state=SessionState(session_data["state"]),
                created_at=datetime.fromisoformat(session_data["created_at"]),
                last_activity=datetime.fromisoformat(session_data["last_activity"]),
                expires_at=datetime.fromisoformat(session_data["expires_at"]),
                ip_address=session_data["ip_address"],
                user_agent=session_data["user_agent"],
                device_fingerprint=session_data.get("device_fingerprint"),
                geolocation=json.loads(session_data.get("geolocation", "{}")),
                csrf_token=session_data["csrf_token"],
                session_key=session_data["session_key"],
                login_method=session_data.get("login_method", "password"),
                risk_score=float(session_data.get("risk_score", 0.0)),
                activity_count=int(session_data.get("activity_count", 0)),
                failed_attempts=int(session_data.get("failed_attempts", 0)),
                metadata=json.loads(session_data.get("metadata", "{}"))
            )
            
            # Check if session is expired
            if session_info.expires_at < datetime.utcnow():
                await self.terminate_session(session_id, "expired")
                return None
            
            return session_info
            
        except Exception as e:
            logger.error(f"Failed to get session: {str(e)}")
            return None
    
    async def update_session_activity(
        self,
        session_id: str,
        activity_type: str,
        ip_address: str,
        user_agent: str,
        endpoint: Optional[str] = None,
        success: bool = True,
        metadata: Dict[str, str] = None
    ) -> bool:
        """Update session activity and security checks."""
        try:
            if not self.redis_client:
                return False
            
            session_info = await self.get_session(session_id)
            if not session_info or session_info.state != SessionState.ACTIVE:
                return False
            
            now = datetime.utcnow()
            
            # Security checks
            security_alerts = []
            
            # Check IP address change
            if ip_address != session_info.ip_address:
                security_alerts.append("ip_change")
                logger.warning(
                    "Session IP address changed",
                    session_id=session_id[:12],
                    old_ip=session_info.ip_address,
                    new_ip=ip_address
                )
            
            # Check user agent change
            if user_agent != session_info.user_agent:
                security_alerts.append("user_agent_change")
                logger.warning(
                    "Session user agent changed",
                    session_id=session_id[:12],
                    old_ua=session_info.user_agent[:50],
                    new_ua=user_agent[:50]
                )
            
            # Check for session hijacking indicators
            if len(security_alerts) >= 2:
                session_info.state = SessionState.SUSPICIOUS
                session_info.risk_score = min(session_info.risk_score + 0.3, 1.0)
                logger.warning(
                    "Session marked as suspicious",
                    session_id=session_id[:12],
                    alerts=security_alerts
                )
            
            # Update session
            session_info.last_activity = now
            session_info.activity_count += 1
            
            if not success:
                session_info.failed_attempts += 1
                session_info.risk_score = min(session_info.risk_score + 0.1, 1.0)
            
            # Check if session should be rotated
            if (now - session_info.created_at).seconds > self.rotation_interval:
                await self._rotate_session(session_info)
            
            # Update in Redis
            session_key = self._get_session_key(session_id)
            updates = {
                "last_activity": session_info.last_activity.isoformat(),
                "activity_count": session_info.activity_count,
                "failed_attempts": session_info.failed_attempts,
                "risk_score": session_info.risk_score,
                "state": session_info.state.value
            }
            
            pipe = self.redis_client.pipeline()
            pipe.hset(session_key, mapping=updates)
            
            # Log activity
            activity = SessionActivity(
                activity_id=secrets.token_urlsafe(16),
                session_id=session_id,
                user_id=session_info.user_id,
                timestamp=now,
                activity_type=activity_type,
                ip_address=ip_address,
                user_agent=user_agent,
                endpoint=endpoint,
                success=success,
                risk_score=session_info.risk_score,
                metadata=metadata or {}
            )
            
            activity_key = self._get_activity_key(session_id)
            activity_data = {
                "activity_id": activity.activity_id,
                "timestamp": activity.timestamp.isoformat(),
                "activity_type": activity.activity_type,
                "ip_address": activity.ip_address,
                "user_agent": activity.user_agent,
                "endpoint": activity.endpoint or "",
                "success": str(activity.success),
                "risk_score": activity.risk_score,
                "metadata": json.dumps(activity.metadata)
            }
            
            pipe.lpush(activity_key, json.dumps(activity_data))
            pipe.ltrim(activity_key, 0, 100)
            
            await pipe.execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session activity: {str(e)}")
            return False
    
    async def terminate_session(self, session_id: str, reason: str) -> bool:
        """Terminate session."""
        try:
            if not self.redis_client:
                return False
            
            session_info = await self.get_session(session_id)
            if not session_info:
                return False
            
            # Update session state
            session_key = self._get_session_key(session_id)
            pipe = self.redis_client.pipeline()
            
            pipe.hset(session_key, "state", SessionState.TERMINATED.value)
            pipe.hset(session_key, "terminated_at", datetime.utcnow().isoformat())
            pipe.hset(session_key, "termination_reason", reason)
            
            # Remove from user's active sessions
            user_sessions_key = self._get_user_sessions_key(session_info.user_id)
            pipe.srem(user_sessions_key, session_id)
            
            # Log termination activity
            activity_data = {
                "activity_id": secrets.token_urlsafe(16),
                "timestamp": datetime.utcnow().isoformat(),
                "activity_type": "logout",
                "ip_address": session_info.ip_address,
                "user_agent": session_info.user_agent,
                "success": "True",
                "risk_score": session_info.risk_score,
                "metadata": json.dumps({"reason": reason})
            }
            
            activity_key = self._get_activity_key(session_id)
            pipe.lpush(activity_key, json.dumps(activity_data))
            
            await pipe.execute()
            
            logger.info(
                "Session terminated",
                session_id=session_id[:12],
                user_id=session_info.user_id,
                reason=reason
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to terminate session: {str(e)}")
            return False
    
    async def get_user_active_sessions(self, user_id: int) -> List[SessionInfo]:
        """Get all active sessions for a user."""
        try:
            if not self.redis_client:
                return []
            
            user_sessions_key = self._get_user_sessions_key(user_id)
            session_ids = await self.redis_client.smembers(user_sessions_key)
            
            sessions = []
            for session_id in session_ids:
                session_info = await self.get_session(session_id)
                if session_info and session_info.state == SessionState.ACTIVE:
                    sessions.append(session_info)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get user active sessions: {str(e)}")
            return []
    
    async def terminate_user_sessions(self, user_id: int, except_session: Optional[str] = None, reason: str = "user_request") -> int:
        """Terminate all sessions for a user."""
        try:
            active_sessions = await self.get_user_active_sessions(user_id)
            
            terminated = 0
            for session in active_sessions:
                if except_session and session.session_id == except_session:
                    continue
                
                if await self.terminate_session(session.session_id, reason):
                    terminated += 1
            
            logger.info(
                "User sessions terminated",
                user_id=user_id,
                terminated_count=terminated,
                reason=reason
            )
            
            return terminated
            
        except Exception as e:
            logger.error(f"Failed to terminate user sessions: {str(e)}")
            return 0
    
    async def _calculate_session_risk(self, session_info: SessionInfo) -> float:
        """Calculate session risk score."""
        risk_score = 0.0
        
        try:
            # Time-based risk (higher risk for unusual hours)
            hour = session_info.created_at.hour
            if hour < 6 or hour > 22:  # Outside business hours
                risk_score += 0.1
            
            # Geographic risk (simplified)
            country = session_info.geolocation.get("country", "").upper()
            high_risk_countries = ["CN", "RU", "IR", "KP"]  # Example list
            if country in high_risk_countries:
                risk_score += 0.3
            
            # User agent risk (basic checks)
            user_agent = session_info.user_agent.lower()
            if "bot" in user_agent or "crawler" in user_agent:
                risk_score += 0.5
            
            # Login method risk
            if session_info.login_method == "api_key":
                risk_score += 0.1
            elif session_info.login_method == "password":
                risk_score += 0.2
            # SSO and 2FA are considered lower risk
            
            return min(risk_score, 1.0)
            
        except Exception as e:
            logger.error(f"Failed to calculate session risk: {str(e)}")
            return 0.5  # Default medium risk
    
    async def _rotate_session(self, session_info: SessionInfo) -> bool:
        """Rotate session keys for security."""
        try:
            # Generate new session key and CSRF token
            new_session_key = secrets.token_urlsafe(32)
            new_csrf_token = secrets.token_urlsafe(32)
            
            session_key = self._get_session_key(session_info.session_id)
            
            await self.redis_client.hset(session_key, mapping={
                "session_key": new_session_key,
                "csrf_token": new_csrf_token,
                "last_rotation": datetime.utcnow().isoformat()
            })
            
            logger.debug(
                "Session keys rotated",
                session_id=session_info.session_id[:12]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate session: {str(e)}")
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Cleanup expired sessions."""
        try:
            if not self.redis_client:
                return 0
            
            cursor = 0
            cleaned = 0
            
            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor=cursor,
                    match=f"{self.session_prefix}*",
                    count=100
                )
                
                for key in keys:
                    session_data = await self.redis_client.hgetall(key)
                    if session_data and session_data.get("expires_at"):
                        expires_at = datetime.fromisoformat(session_data["expires_at"])
                        if expires_at < datetime.utcnow():
                            session_id = session_data.get("session_id", "")
                            if session_id:
                                await self.terminate_session(session_id, "expired")
                                cleaned += 1
                
                if cursor == 0:
                    break
            
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} expired sessions")
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {str(e)}")
            return 0


# Global enterprise session manager
enterprise_session_manager: Optional[EnterpriseSessionManager] = None


async def initialize_session_manager() -> None:
    """Initialize the global session manager."""
    global enterprise_session_manager
    
    try:
        enterprise_session_manager = EnterpriseSessionManager()
        await enterprise_session_manager.initialize()
        logger.info("Enterprise session manager initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize session manager: {str(e)}")


async def cleanup_session_manager() -> None:
    """Cleanup the global session manager."""
    global enterprise_session_manager
    
    if enterprise_session_manager:
        await enterprise_session_manager.close()
        enterprise_session_manager = None