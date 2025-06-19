"""
Webpage Cache Service for intelligent caching of parsing results.

This service provides:
- Redis-based caching for webpage parsing results
- Content-aware cache keys for efficient lookups
- TTL management and cache invalidation
- Cache hit/miss metrics
- Intelligent cache warming
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import structlog
import redis.asyncio as redis
from urllib.parse import urlparse

from app.core.config import settings
from app.schemas.web_page import WebPageParseResponse

logger = structlog.get_logger(__name__)


class WebpageCacheService:
    """Service for caching webpage parsing results with intelligent key management."""
    
    def __init__(self):
        self.redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        self.default_ttl = getattr(settings, 'REDIS_CACHE_TTL', 3600)  # 1 hour
        self.max_cache_size = getattr(settings, 'MAX_CACHE_SIZE_MB', 100)
        
        # Cache key prefixes
        self.WEBPAGE_PREFIX = "webpage:"
        self.METADATA_PREFIX = "meta:"
        self.STATS_PREFIX = "stats:"
        
        # Redis connection
        self.redis_client: Optional[redis.Redis] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Redis connection."""
        if self._initialized:
            return
            
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            await self.redis_client.ping()
            
            self._initialized = True
            logger.info("Webpage cache service initialized", redis_url=self.redis_url)
            
        except Exception as e:
            logger.error("Failed to initialize webpage cache service", error=str(e))
            # Continue without caching if Redis is not available
            self.redis_client = None
    
    def _generate_cache_key(self, url: str, options: Dict[str, Any] = None) -> str:
        """Generate a content-aware cache key for the webpage."""
        
        # Parse URL to get consistent format
        parsed_url = urlparse(url)
        normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        
        # Include query parameters in hash if they affect content
        query_params = parsed_url.query
        if query_params:
            # Sort query parameters for consistent hashing
            sorted_params = "&".join(sorted(query_params.split("&")))
            normalized_url += f"?{sorted_params}"
        
        # Include relevant options in the key
        options_hash = ""
        if options:
            relevant_options = {
                'include_screenshot': options.get('include_screenshot', False),
                'wait_for_load': options.get('wait_for_load', 0),
                'wait_for_network_idle': options.get('wait_for_network_idle', False)
            }
            options_str = json.dumps(relevant_options, sort_keys=True)
            options_hash = hashlib.md5(options_str.encode()).hexdigest()[:8]
        
        # Create final cache key
        url_hash = hashlib.md5(normalized_url.encode()).hexdigest()
        cache_key = f"{self.WEBPAGE_PREFIX}{url_hash}"
        
        if options_hash:
            cache_key += f":{options_hash}"
        
        return cache_key
    
    async def get_cached_result(
        self, 
        url: str, 
        options: Dict[str, Any] = None
    ) -> Optional[WebPageParseResponse]:
        """Get cached parsing result if available."""
        
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._generate_cache_key(url, options)
            
            # Get cached data
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                # Update access statistics
                await self._update_cache_stats(cache_key, "hit")
                
                # Parse cached result
                result_dict = json.loads(cached_data)
                
                # Add cache metadata
                result_dict['cached'] = True
                result_dict['cache_key'] = cache_key
                result_dict['retrieved_at'] = datetime.utcnow().isoformat()
                
                logger.info("Cache hit", url=url, cache_key=cache_key)
                return WebPageParseResponse(**result_dict)
            else:
                # Update miss statistics
                await self._update_cache_stats(cache_key, "miss")
                logger.debug("Cache miss", url=url, cache_key=cache_key)
                return None
                
        except Exception as e:
            logger.error("Failed to get cached result", url=url, error=str(e))
            return None
    
    async def cache_result(
        self, 
        url: str, 
        result: WebPageParseResponse, 
        options: Dict[str, Any] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache parsing result with intelligent TTL."""
        
        if not self.redis_client:
            return False
        
        try:
            cache_key = self._generate_cache_key(url, options)
            ttl = ttl or self._calculate_intelligent_ttl(url, result)
            
            # Prepare data for caching
            cache_data = result.dict()
            cache_data['cached_at'] = datetime.utcnow().isoformat()
            cache_data['cache_ttl'] = ttl
            
            # Store in Redis
            await self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cache_data, default=str)
            )
            
            # Store metadata
            await self._store_cache_metadata(cache_key, url, result, ttl)
            
            # Update statistics
            await self._update_cache_stats(cache_key, "store")
            
            logger.info(
                "Result cached successfully",
                url=url,
                cache_key=cache_key,
                ttl=ttl,
                size_kb=len(json.dumps(cache_data)) / 1024
            )
            return True
            
        except Exception as e:
            logger.error("Failed to cache result", url=url, error=str(e))
            return False
    
    def _calculate_intelligent_ttl(self, url: str, result: WebPageParseResponse) -> int:
        """Calculate intelligent TTL based on content characteristics."""
        
        base_ttl = self.default_ttl
        
        # Adjust TTL based on domain
        domain = urlparse(url).netloc
        
        # Static content sites get longer TTL
        if any(indicator in domain for indicator in ['cdn', 'static', 'assets']):
            return base_ttl * 4  # 4 hours
        
        # News/dynamic sites get shorter TTL
        if any(indicator in domain for indicator in ['news', 'blog', 'feed']):
            return base_ttl // 2  # 30 minutes
        
        # E-commerce sites get medium TTL
        if any(indicator in domain for indicator in ['shop', 'store', 'cart']):
            return base_ttl  # 1 hour
        
        # Adjust based on content complexity
        element_count = len(result.interactive_elements)
        if element_count > 100:
            # Complex pages change less frequently
            return int(base_ttl * 1.5)
        elif element_count < 10:
            # Simple pages might be more dynamic
            return int(base_ttl * 0.8)
        
        return base_ttl
    
    async def _store_cache_metadata(
        self, 
        cache_key: str, 
        url: str, 
        result: WebPageParseResponse, 
        ttl: int
    ):
        """Store metadata about cached entries."""
        
        try:
            metadata_key = f"{self.METADATA_PREFIX}{cache_key}"
            metadata = {
                'url': url,
                'domain': urlparse(url).netloc,
                'cached_at': datetime.utcnow().isoformat(),
                'ttl': ttl,
                'expires_at': (datetime.utcnow() + timedelta(seconds=ttl)).isoformat(),
                'element_count': len(result.interactive_elements),
                'content_blocks': len(result.content_blocks),
                'has_screenshot': result.screenshot_path is not None,
                'content_hash': result.content_hash
            }
            
            await self.redis_client.setex(
                metadata_key,
                ttl + 300,  # Keep metadata slightly longer
                json.dumps(metadata)
            )
            
        except Exception as e:
            logger.error("Failed to store cache metadata", cache_key=cache_key, error=str(e))
    
    async def _update_cache_stats(self, cache_key: str, operation: str):
        """Update cache statistics."""
        
        try:
            stats_key = f"{self.STATS_PREFIX}daily:{datetime.utcnow().strftime('%Y-%m-%d')}"
            
            # Increment counters
            await self.redis_client.hincrby(stats_key, f"{operation}_count", 1)
            await self.redis_client.hincrby(stats_key, "total_operations", 1)
            
            # Set expiry for stats (keep for 7 days)
            await self.redis_client.expire(stats_key, 7 * 24 * 3600)
            
        except Exception as e:
            logger.error("Failed to update cache stats", error=str(e))
    
    async def invalidate_cache(self, url: str, options: Dict[str, Any] = None) -> bool:
        """Invalidate cached result for a specific URL."""
        
        if not self.redis_client:
            return False
        
        try:
            cache_key = self._generate_cache_key(url, options)
            
            # Delete cached data and metadata
            deleted_count = await self.redis_client.delete(
                cache_key,
                f"{self.METADATA_PREFIX}{cache_key}"
            )
            
            logger.info("Cache invalidated", url=url, cache_key=cache_key, deleted=deleted_count)
            return deleted_count > 0
            
        except Exception as e:
            logger.error("Failed to invalidate cache", url=url, error=str(e))
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        
        if not self.redis_client:
            return {"error": "Redis not available"}
        
        try:
            today = datetime.utcnow().strftime('%Y-%m-%d')
            stats_key = f"{self.STATS_PREFIX}daily:{today}"
            
            # Get daily stats
            daily_stats = await self.redis_client.hgetall(stats_key)
            
            # Get Redis info
            redis_info = await self.redis_client.info('memory')
            
            # Calculate hit rate
            hits = int(daily_stats.get('hit_count', 0))
            misses = int(daily_stats.get('miss_count', 0))
            total = hits + misses
            hit_rate = (hits / total * 100) if total > 0 else 0
            
            return {
                'date': today,
                'cache_hits': hits,
                'cache_misses': misses,
                'hit_rate_percentage': round(hit_rate, 2),
                'total_operations': int(daily_stats.get('total_operations', 0)),
                'redis_memory_used_mb': round(redis_info.get('used_memory', 0) / 1024 / 1024, 2),
                'redis_connected': True
            }
            
        except Exception as e:
            logger.error("Failed to get cache stats", error=str(e))
            return {"error": str(e)}


# Global cache service instance
webpage_cache_service = WebpageCacheService()
