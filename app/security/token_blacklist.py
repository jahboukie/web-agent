"""
Enterprise Token Blacklist with Redis Backend

Scalable token blacklist implementation with Redis persistence,
automatic expiration, and high-performance operations.
"""

import asyncio
import json
import hashlib
from typing import Optional, Set, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field

import redis.asyncio as redis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BlacklistedToken:
    """Blacklisted token information."""
    
    token_hash: str
    user_id: Optional[int]
    reason: str
    blacklisted_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class RedisTokenBlacklist:
    """
    Redis-based token blacklist with automatic expiration and audit logging.
    
    Features:
    - High-performance Redis backend
    - Automatic token expiration
    - Audit logging for compliance
    - Hash-based token storage for security
    - Batch operations for efficiency
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.key_prefix = "webagent:blacklist:"
        self.audit_prefix = "webagent:audit:blacklist:"
        self.stats_key = "webagent:blacklist:stats"
        
    async def initialize(self) -> None:
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            
            logger.info("Redis token blacklist initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis token blacklist: {str(e)}")
            # Fallback to in-memory implementation
            self.redis_client = None
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
    
    def _hash_token(self, token: str) -> str:
        """Create secure hash of token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def _get_token_key(self, token_hash: str) -> str:
        """Get Redis key for token."""
        return f"{self.key_prefix}token:{token_hash}"
    
    def _get_user_key(self, user_id: int) -> str:
        """Get Redis key for user tokens."""
        return f"{self.key_prefix}user:{user_id}"
    
    def _get_audit_key(self, token_hash: str) -> str:
        """Get Redis key for audit log."""
        return f"{self.audit_prefix}{token_hash}"
    
    async def blacklist_token(
        self,
        token: str,
        reason: str,
        user_id: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Add token to blacklist.
        
        Args:
            token: JWT token to blacklist
            reason: Reason for blacklisting
            user_id: User ID associated with token
            ttl_seconds: TTL for blacklist entry (defaults to token expiration)
            ip_address: IP address of the request
            user_agent: User agent of the request
            
        Returns:
            bool: True if successfully blacklisted
        """
        try:
            if not self.redis_client:
                logger.error("Redis client not initialized")
                return False
            
            token_hash = self._hash_token(token)
            token_key = self._get_token_key(token_hash)
            
            # Create blacklist entry
            blacklist_entry = BlacklistedToken(
                token_hash=token_hash,
                user_id=user_id,
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds) if ttl_seconds else None
            )
            
            # Store in Redis with TTL
            entry_data = {
                "token_hash": blacklist_entry.token_hash,
                "user_id": blacklist_entry.user_id,
                "reason": blacklist_entry.reason,
                "blacklisted_at": blacklist_entry.blacklisted_at.isoformat(),
                "expires_at": blacklist_entry.expires_at.isoformat() if blacklist_entry.expires_at else None,
                "ip_address": blacklist_entry.ip_address,
                "user_agent": blacklist_entry.user_agent
            }
            
            # Use pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Set token blacklist entry
            pipe.hset(token_key, mapping=entry_data)
            
            if ttl_seconds:
                pipe.expire(token_key, ttl_seconds)
            
            # Add to user's blacklisted tokens if user_id provided
            if user_id:
                user_key = self._get_user_key(user_id)
                pipe.sadd(user_key, token_hash)
                if ttl_seconds:
                    pipe.expire(user_key, ttl_seconds)
            
            # Store audit log
            audit_key = self._get_audit_key(token_hash)
            audit_data = {
                "action": "blacklist",
                "token_hash": token_hash,
                "user_id": user_id,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
                "ip_address": ip_address,
                "user_agent": user_agent
            }
            pipe.hset(audit_key, mapping=audit_data)
            if ttl_seconds:
                pipe.expire(audit_key, ttl_seconds + 86400)  # Keep audit log 1 day longer
            
            # Update stats
            pipe.hincrby(self.stats_key, "total_blacklisted", 1)
            pipe.hincrby(self.stats_key, f"reason:{reason}", 1)
            
            # Execute pipeline
            await pipe.execute()
            
            logger.info(
                "Token blacklisted successfully",
                token_hash=token_hash[:12],
                user_id=user_id,
                reason=reason
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to blacklist token: {str(e)}")
            return False
    
    async def is_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted.
        
        Args:
            token: JWT token to check
            
        Returns:
            bool: True if token is blacklisted
        """
        try:
            if not self.redis_client:
                return False
            
            token_hash = self._hash_token(token)
            token_key = self._get_token_key(token_hash)
            
            exists = await self.redis_client.exists(token_key)
            
            if exists:
                # Log the blacklist hit for monitoring
                await self.redis_client.hincrby(self.stats_key, "blacklist_hits", 1)
                
                logger.debug(
                    "Blacklisted token access attempt",
                    token_hash=token_hash[:12]
                )
            
            return bool(exists)
            
        except Exception as e:
            logger.error(f"Failed to check token blacklist: {str(e)}")
            # Err on the side of caution - assume blacklisted if check fails
            return True
    
    async def remove_token(self, token: str, reason: str = "manual_removal") -> bool:
        """
        Remove token from blacklist.
        
        Args:
            token: JWT token to remove
            reason: Reason for removal
            
        Returns:
            bool: True if successfully removed
        """
        try:
            if not self.redis_client:
                return False
            
            token_hash = self._hash_token(token)
            token_key = self._get_token_key(token_hash)
            
            # Get token info before deletion for audit
            token_info = await self.redis_client.hgetall(token_key)
            
            if not token_info:
                return False
            
            user_id = token_info.get("user_id")
            
            # Use pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Remove token
            pipe.delete(token_key)
            
            # Remove from user's blacklisted tokens
            if user_id:
                user_key = self._get_user_key(user_id)
                pipe.srem(user_key, token_hash)
            
            # Add removal audit log
            audit_key = self._get_audit_key(token_hash)
            removal_audit = {
                "action": "remove",
                "token_hash": token_hash,
                "user_id": user_id,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
                "original_reason": token_info.get("reason", "unknown")
            }
            pipe.hset(f"{audit_key}:removal", mapping=removal_audit)
            pipe.expire(f"{audit_key}:removal", 86400)  # Keep removal log for 1 day
            
            # Update stats
            pipe.hincrby(self.stats_key, "total_removed", 1)
            
            # Execute pipeline
            await pipe.execute()
            
            logger.info(
                "Token removed from blacklist",
                token_hash=token_hash[:12],
                reason=reason
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove token from blacklist: {str(e)}")
            return False
    
    async def blacklist_user_tokens(self, user_id: int, reason: str) -> int:
        """
        Blacklist all tokens for a user.
        
        Args:
            user_id: User ID
            reason: Reason for blacklisting
            
        Returns:
            int: Number of tokens blacklisted
        """
        try:
            if not self.redis_client:
                return 0
            
            user_key = self._get_user_key(user_id)
            token_hashes = await self.redis_client.smembers(user_key)
            
            if not token_hashes:
                return 0
            
            # Use pipeline for batch operations
            pipe = self.redis_client.pipeline()
            
            count = 0
            for token_hash in token_hashes:
                token_key = self._get_token_key(token_hash)
                
                # Check if token still exists
                if await self.redis_client.exists(token_key):
                    # Update reason
                    pipe.hset(token_key, "reason", f"{reason} (user_revocation)")
                    count += 1
            
            # Update stats
            pipe.hincrby(self.stats_key, f"user_revocations", 1)
            pipe.hincrby(self.stats_key, f"tokens_revoked", count)
            
            await pipe.execute()
            
            logger.info(
                "User tokens blacklisted",
                user_id=user_id,
                token_count=count,
                reason=reason
            )
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to blacklist user tokens: {str(e)}")
            return 0
    
    async def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired blacklist entries.
        
        Returns:
            int: Number of entries cleaned up
        """
        try:
            if not self.redis_client:
                return 0
            
            # Redis TTL handles automatic expiration, but we can clean up
            # any entries that should have expired but didn't due to edge cases
            
            cursor = 0
            cleaned = 0
            
            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor=cursor,
                    match=f"{self.key_prefix}token:*",
                    count=100
                )
                
                for key in keys:
                    token_info = await self.redis_client.hgetall(key)
                    if token_info and token_info.get("expires_at"):
                        expires_at = datetime.fromisoformat(token_info["expires_at"])
                        if expires_at < datetime.utcnow():
                            await self.redis_client.delete(key)
                            cleaned += 1
                
                if cursor == 0:
                    break
            
            if cleaned > 0:
                await self.redis_client.hincrby(self.stats_key, "expired_cleaned", cleaned)
                logger.info(f"Cleaned up {cleaned} expired blacklist entries")
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired tokens: {str(e)}")
            return 0
    
    async def get_blacklist_stats(self) -> dict:
        """Get blacklist statistics."""
        try:
            if not self.redis_client:
                return {}
            
            stats = await self.redis_client.hgetall(self.stats_key)
            
            # Add real-time counts
            token_count = 0
            cursor = 0
            
            while True:
                cursor, keys = await self.redis_client.scan(
                    cursor=cursor,
                    match=f"{self.key_prefix}token:*",
                    count=100
                )
                token_count += len(keys)
                
                if cursor == 0:
                    break
            
            stats["active_blacklisted_tokens"] = str(token_count)
            stats["last_updated"] = datetime.utcnow().isoformat()
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get blacklist stats: {str(e)}")
            return {}
    
    async def get_user_blacklisted_tokens(self, user_id: int) -> List[dict]:
        """Get blacklisted tokens for a user."""
        try:
            if not self.redis_client:
                return []
            
            user_key = self._get_user_key(user_id)
            token_hashes = await self.redis_client.smembers(user_key)
            
            tokens = []
            for token_hash in token_hashes:
                token_key = self._get_token_key(token_hash)
                token_info = await self.redis_client.hgetall(token_key)
                if token_info:
                    tokens.append(token_info)
            
            return tokens
            
        except Exception as e:
            logger.error(f"Failed to get user blacklisted tokens: {str(e)}")
            return []


# Fallback in-memory implementation
class InMemoryTokenBlacklist:
    """Fallback in-memory token blacklist."""
    
    def __init__(self):
        self._blacklisted_tokens: Set[str] = set()
        self._audit_log: List[dict] = []
    
    async def initialize(self) -> None:
        """Initialize (no-op for in-memory)."""
        pass
    
    async def close(self) -> None:
        """Close (no-op for in-memory)."""
        pass
    
    def _hash_token(self, token: str) -> str:
        """Create secure hash of token."""
        return hashlib.sha256(token.encode()).hexdigest()
    
    async def blacklist_token(self, token: str, reason: str, **kwargs) -> bool:
        """Add token to blacklist."""
        try:
            token_hash = self._hash_token(token)
            self._blacklisted_tokens.add(token_hash)
            
            # Add to audit log
            self._audit_log.append({
                "action": "blacklist",
                "token_hash": token_hash[:12],
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.warning("Using in-memory token blacklist (not recommended for production)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to blacklist token: {str(e)}")
            return False
    
    async def is_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted."""
        try:
            token_hash = self._hash_token(token)
            return token_hash in self._blacklisted_tokens
        except Exception:
            return True  # Err on the side of caution
    
    async def remove_token(self, token: str, reason: str = "manual_removal") -> bool:
        """Remove token from blacklist."""
        try:
            token_hash = self._hash_token(token)
            if token_hash in self._blacklisted_tokens:
                self._blacklisted_tokens.remove(token_hash)
                return True
            return False
        except Exception:
            return False
    
    async def cleanup_expired_tokens(self) -> int:
        """Cleanup expired tokens (no-op for in-memory)."""
        return 0
    
    async def get_blacklist_stats(self) -> dict:
        """Get blacklist statistics."""
        return {
            "active_blacklisted_tokens": str(len(self._blacklisted_tokens)),
            "implementation": "in_memory",
            "warning": "Not recommended for production"
        }


# Global enterprise token blacklist
enterprise_token_blacklist: Optional[RedisTokenBlacklist] = None


async def initialize_token_blacklist() -> None:
    """Initialize the global token blacklist."""
    global enterprise_token_blacklist
    
    try:
        # Try Redis implementation first
        redis_blacklist = RedisTokenBlacklist()
        await redis_blacklist.initialize()
        
        if redis_blacklist.redis_client:
            enterprise_token_blacklist = redis_blacklist
            logger.info("Redis token blacklist initialized")
        else:
            # Fallback to in-memory
            enterprise_token_blacklist = InMemoryTokenBlacklist()
            await enterprise_token_blacklist.initialize()
            logger.warning("Using fallback in-memory token blacklist")
            
    except Exception as e:
        logger.error(f"Failed to initialize token blacklist: {str(e)}")
        # Last resort fallback
        enterprise_token_blacklist = InMemoryTokenBlacklist()
        await enterprise_token_blacklist.initialize()


async def cleanup_token_blacklist() -> None:
    """Cleanup the global token blacklist."""
    global enterprise_token_blacklist
    
    if enterprise_token_blacklist:
        await enterprise_token_blacklist.close()
        enterprise_token_blacklist = None