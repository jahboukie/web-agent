#!/usr/bin/env python3
"""
Clear Redis cache to fix schema mismatch issues.
"""

import asyncio
import redis.asyncio as redis

async def clear_cache():
    """Clear all Redis cache data."""
    try:
        # Connect to Redis
        redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )

        # Get all keys first to see what's cached
        all_keys = await redis_client.keys('*')
        print(f"📊 Found {len(all_keys)} keys in Redis cache")

        # Show some sample keys
        if all_keys:
            print("🔍 Sample keys:")
            for key in all_keys[:10]:  # Show first 10 keys
                print(f"  - {key}")
            if len(all_keys) > 10:
                print(f"  ... and {len(all_keys) - 10} more")

        # Clear all data
        await redis_client.flushall()
        print("✅ Redis cache cleared successfully!")

        # Verify it's empty
        remaining_keys = await redis_client.keys('*')
        print(f"🔍 Remaining keys after clear: {len(remaining_keys)}")

        # Close connection
        await redis_client.aclose()

    except Exception as e:
        print(f"❌ Failed to clear cache: {e}")

if __name__ == "__main__":
    asyncio.run(clear_cache())
