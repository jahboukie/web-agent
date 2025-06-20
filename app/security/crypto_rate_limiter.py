"""
Cryptographic Operations Rate Limiter

Rate limiting for cryptographic operations to prevent resource exhaustion attacks
and ensure fair usage of expensive cryptographic computations.
"""

import asyncio
import time
import hashlib
from typing import Dict, Optional, Tuple, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

import redis.asyncio as redis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CryptoOperationType(str, Enum):
    """Types of cryptographic operations."""
    KEY_DERIVATION = "key_derivation"
    ENCRYPTION = "encryption"
    DECRYPTION = "decryption"
    SIGNING = "signing"
    VERIFICATION = "verification"
    HASHING = "hashing"
    RANDOM_GENERATION = "random_generation"
    KEY_GENERATION = "key_generation"
    HSM_OPERATION = "hsm_operation"


@dataclass
class RateLimitConfig:
    """Rate limit configuration for crypto operations."""
    
    # Requests per time window
    requests_per_minute: int = 100
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    
    # Burst allowance
    burst_size: int = 20
    
    # Cost-based limiting (heavier operations cost more)
    operation_costs: Dict[CryptoOperationType, int] = field(default_factory=lambda: {
        CryptoOperationType.KEY_DERIVATION: 10,  # PBKDF2 is expensive
        CryptoOperationType.ENCRYPTION: 2,
        CryptoOperationType.DECRYPTION: 2,
        CryptoOperationType.SIGNING: 5,
        CryptoOperationType.VERIFICATION: 3,
        CryptoOperationType.HASHING: 1,
        CryptoOperationType.RANDOM_GENERATION: 1,
        CryptoOperationType.KEY_GENERATION: 15,  # RSA key generation is very expensive
        CryptoOperationType.HSM_OPERATION: 8,   # HSM operations have network overhead
    })
    
    # Per-user limits
    user_requests_per_minute: int = 50
    user_requests_per_hour: int = 500
    
    # Global cost limits
    global_cost_per_minute: int = 1000
    global_cost_per_hour: int = 10000


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    
    allowed: bool
    remaining_requests: int
    reset_time: datetime
    retry_after: Optional[int] = None
    reason: Optional[str] = None
    cost_consumed: int = 0


class CryptoRateLimiter:
    """
    Rate limiter for cryptographic operations with multiple limiting strategies.
    
    Features:
    - Per-operation type limits
    - Per-user limits
    - Global system limits
    - Cost-based limiting
    - Burst allowance
    - Redis-based distributed limiting
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.redis_client: Optional[redis.Redis] = None
        self.local_cache: Dict[str, Any] = {}
        self.cache_ttl = 60  # 1 minute local cache
        
        # Key prefixes for Redis
        self.global_prefix = "webagent:crypto_limits:global:"
        self.user_prefix = "webagent:crypto_limits:user:"
        self.operation_prefix = "webagent:crypto_limits:operation:"
        self.stats_prefix = "webagent:crypto_limits:stats:"
        
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
            logger.info("Crypto rate limiter initialized with Redis")
            
        except Exception as e:
            logger.warning(f"Redis unavailable for rate limiting, using local cache: {str(e)}")
            self.redis_client = None
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
    
    def _get_rate_limit_key(self, prefix: str, identifier: str, window: str) -> str:
        """Generate rate limit key."""
        return f"{prefix}{identifier}:{window}"
    
    def _get_time_windows(self) -> Dict[str, int]:
        """Get current time windows."""
        now = datetime.utcnow()
        return {
            "minute": int(now.timestamp() // 60),
            "hour": int(now.timestamp() // 3600),
            "day": int(now.timestamp() // 86400)
        }
    
    async def _check_redis_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        cost: int = 1
    ) -> Tuple[bool, int, datetime]:
        """Check rate limit using Redis."""
        try:
            if not self.redis_client:
                return True, limit, datetime.utcnow()
            
            current_time = int(time.time())
            window_start = current_time - window_seconds
            
            # Use Redis sliding window
            pipe = self.redis_client.pipeline()
            
            # Remove expired entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {f"{current_time}:{cost}": current_time})
            
            # Set TTL
            pipe.expire(key, window_seconds)
            
            results = await pipe.execute()
            
            current_count = results[1] if len(results) > 1 else 0
            
            # Calculate cost-based usage
            if cost > 1:
                # Get all entries in window and sum costs
                entries = await self.redis_client.zrangebyscore(key, window_start, current_time)
                total_cost = sum(int(entry.split(':')[1]) for entry in entries if ':' in entry)
                current_count = total_cost
            
            allowed = current_count <= limit
            remaining = max(0, limit - current_count)
            reset_time = datetime.utcfromtimestamp(current_time + window_seconds)
            
            return allowed, remaining, reset_time
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {str(e)}")
            # Fallback to allow request if Redis fails
            return True, limit, datetime.utcnow()
    
    async def _check_local_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        cost: int = 1
    ) -> Tuple[bool, int, datetime]:
        """Check rate limit using local cache."""
        try:
            current_time = int(time.time())
            window_start = current_time - window_seconds
            
            # Clean expired entries
            if key in self.local_cache:
                self.local_cache[key] = [
                    (timestamp, req_cost) for timestamp, req_cost in self.local_cache[key]
                    if timestamp > window_start
                ]
            else:
                self.local_cache[key] = []
            
            # Calculate current usage
            current_cost = sum(req_cost for _, req_cost in self.local_cache[key])
            
            # Add current request
            self.local_cache[key].append((current_time, cost))
            
            allowed = current_cost + cost <= limit
            remaining = max(0, limit - current_cost - cost)
            reset_time = datetime.utcfromtimestamp(current_time + window_seconds)
            
            return allowed, remaining, reset_time
            
        except Exception as e:
            logger.error(f"Local rate limit check failed: {str(e)}")
            return True, limit, datetime.utcnow()
    
    async def check_rate_limit(
        self,
        operation_type: CryptoOperationType,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None
    ) -> RateLimitResult:
        """
        Check if operation is allowed under rate limits.
        
        Args:
            operation_type: Type of cryptographic operation
            user_id: User ID (if applicable)
            ip_address: Client IP address
            
        Returns:
            RateLimitResult: Rate limit decision
        """
        try:
            time_windows = self._get_time_windows()
            cost = self.config.operation_costs.get(operation_type, 1)
            
            # Check multiple rate limit layers
            checks = []
            
            # 1. Global operation limits
            global_minute_key = self._get_rate_limit_key(
                self.global_prefix, "operations", str(time_windows["minute"])
            )
            global_hour_key = self._get_rate_limit_key(
                self.global_prefix, "operations", str(time_windows["hour"])
            )
            
            checks.append(("global_minute", global_minute_key, self.config.requests_per_minute, 60, 1))
            checks.append(("global_hour", global_hour_key, self.config.requests_per_hour, 3600, 1))
            
            # 2. Global cost limits
            global_cost_minute_key = self._get_rate_limit_key(
                self.global_prefix, "cost", str(time_windows["minute"])
            )
            global_cost_hour_key = self._get_rate_limit_key(
                self.global_prefix, "cost", str(time_windows["hour"])
            )
            
            checks.append(("global_cost_minute", global_cost_minute_key, self.config.global_cost_per_minute, 60, cost))
            checks.append(("global_cost_hour", global_cost_hour_key, self.config.global_cost_per_hour, 3600, cost))
            
            # 3. Per-user limits
            if user_id:
                user_minute_key = self._get_rate_limit_key(
                    self.user_prefix, str(user_id), str(time_windows["minute"])
                )
                user_hour_key = self._get_rate_limit_key(
                    self.user_prefix, str(user_id), str(time_windows["hour"])
                )
                
                checks.append(("user_minute", user_minute_key, self.config.user_requests_per_minute, 60, 1))
                checks.append(("user_hour", user_hour_key, self.config.user_requests_per_hour, 3600, 1))
            
            # 4. Per-IP limits (if no user_id)
            elif ip_address:
                ip_minute_key = self._get_rate_limit_key(
                    "webagent:crypto_limits:ip:", hashlib.sha256(ip_address.encode()).hexdigest()[:16], 
                    str(time_windows["minute"])
                )
                
                checks.append(("ip_minute", ip_minute_key, self.config.user_requests_per_minute, 60, 1))
            
            # 5. Per-operation type limits
            op_minute_key = self._get_rate_limit_key(
                self.operation_prefix, operation_type.value, str(time_windows["minute"])
            )
            
            # Higher limits for less expensive operations
            op_limit = self.config.requests_per_minute // max(1, cost // 2)
            checks.append(("operation_minute", op_minute_key, op_limit, 60, 1))
            
            # Perform all rate limit checks
            for check_name, key, limit, window_seconds, check_cost in checks:
                if self.redis_client:
                    allowed, remaining, reset_time = await self._check_redis_limit(
                        key, limit, window_seconds, check_cost
                    )
                else:
                    allowed, remaining, reset_time = await self._check_local_limit(
                        key, limit, window_seconds, check_cost
                    )
                
                if not allowed:
                    retry_after = int((reset_time - datetime.utcnow()).total_seconds())
                    
                    logger.warning(
                        "Crypto operation rate limited",
                        check=check_name,
                        operation_type=operation_type.value,
                        user_id=user_id,
                        limit=limit,
                        cost=check_cost
                    )
                    
                    return RateLimitResult(
                        allowed=False,
                        remaining_requests=remaining,
                        reset_time=reset_time,
                        retry_after=retry_after,
                        reason=f"Rate limit exceeded: {check_name}",
                        cost_consumed=cost
                    )
            
            # All checks passed
            await self._update_stats(operation_type, user_id, cost)
            
            return RateLimitResult(
                allowed=True,
                remaining_requests=remaining,
                reset_time=reset_time,
                cost_consumed=cost
            )
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            # Fail open - allow the operation
            return RateLimitResult(
                allowed=True,
                remaining_requests=0,
                reset_time=datetime.utcnow(),
                reason="Rate limit check failed"
            )
    
    async def _update_stats(self, operation_type: CryptoOperationType, user_id: Optional[int], cost: int) -> None:
        """Update operation statistics."""
        try:
            if not self.redis_client:
                return
            
            current_time = datetime.utcnow()
            day_key = current_time.strftime("%Y-%m-%d")
            
            pipe = self.redis_client.pipeline()
            
            # Update global stats
            stats_key = f"{self.stats_prefix}daily:{day_key}"
            pipe.hincrby(stats_key, "total_operations", 1)
            pipe.hincrby(stats_key, f"operation:{operation_type.value}", 1)
            pipe.hincrby(stats_key, "total_cost", cost)
            pipe.expire(stats_key, 86400 * 7)  # Keep for 7 days
            
            # Update per-user stats
            if user_id:
                user_stats_key = f"{self.stats_prefix}user:{user_id}:{day_key}"
                pipe.hincrby(user_stats_key, "operations", 1)
                pipe.hincrby(user_stats_key, "cost", cost)
                pipe.expire(user_stats_key, 86400 * 7)
            
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Failed to update crypto stats: {str(e)}")
    
    async def get_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        try:
            if not self.redis_client:
                return {"error": "Redis not available"}
            
            stats = {}
            
            for i in range(days):
                date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
                day_stats = await self.redis_client.hgetall(f"{self.stats_prefix}daily:{date}")
                
                if day_stats:
                    stats[date] = day_stats
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get crypto stats: {str(e)}")
            return {"error": str(e)}


# Global crypto rate limiter
crypto_rate_limiter: Optional[CryptoRateLimiter] = None


async def initialize_crypto_rate_limiter(config: Optional[RateLimitConfig] = None) -> None:
    """Initialize the global crypto rate limiter."""
    global crypto_rate_limiter
    
    try:
        crypto_rate_limiter = CryptoRateLimiter(config)
        await crypto_rate_limiter.initialize()
        logger.info("Crypto rate limiter initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize crypto rate limiter: {str(e)}")


async def cleanup_crypto_rate_limiter() -> None:
    """Cleanup the global crypto rate limiter."""
    global crypto_rate_limiter
    
    if crypto_rate_limiter:
        await crypto_rate_limiter.close()
        crypto_rate_limiter = None


def rate_limit_crypto_operation(operation_type: CryptoOperationType):
    """
    Decorator to rate limit cryptographic operations.
    
    Args:
        operation_type: Type of cryptographic operation
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if crypto_rate_limiter is None:
                # Rate limiter not initialized, allow operation
                return await func(*args, **kwargs)
            
            # Extract user_id and ip_address from context if available
            user_id = kwargs.get('user_id')
            ip_address = kwargs.get('ip_address')
            
            # Check rate limit
            result = await crypto_rate_limiter.check_rate_limit(
                operation_type=operation_type,
                user_id=user_id,
                ip_address=ip_address
            )
            
            if not result.allowed:
                logger.warning(
                    "Crypto operation blocked by rate limiter",
                    operation_type=operation_type.value,
                    reason=result.reason,
                    retry_after=result.retry_after
                )
                
                # Raise an exception or return an error response
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "operation_type": operation_type.value,
                        "retry_after": result.retry_after,
                        "reason": result.reason
                    },
                    headers={"Retry-After": str(result.retry_after)} if result.retry_after else {}
                )
            
            # Execute the operation
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Log the error but don't count failed operations against rate limit
                logger.error(f"Crypto operation failed: {str(e)}")
                raise
                
        return wrapper
    return decorator


# Convenience decorators for common operations
def rate_limit_key_derivation(func: Callable) -> Callable:
    """Rate limit key derivation operations."""
    return rate_limit_crypto_operation(CryptoOperationType.KEY_DERIVATION)(func)


def rate_limit_encryption(func: Callable) -> Callable:
    """Rate limit encryption operations."""
    return rate_limit_crypto_operation(CryptoOperationType.ENCRYPTION)(func)


def rate_limit_decryption(func: Callable) -> Callable:
    """Rate limit decryption operations."""
    return rate_limit_crypto_operation(CryptoOperationType.DECRYPTION)(func)


def rate_limit_signing(func: Callable) -> Callable:
    """Rate limit signing operations."""
    return rate_limit_crypto_operation(CryptoOperationType.SIGNING)(func)


def rate_limit_key_generation(func: Callable) -> Callable:
    """Rate limit key generation operations."""
    return rate_limit_crypto_operation(CryptoOperationType.KEY_GENERATION)(func)


def rate_limit_hsm_operation(func: Callable) -> Callable:
    """Rate limit HSM operations."""
    return rate_limit_crypto_operation(CryptoOperationType.HSM_OPERATION)(func)