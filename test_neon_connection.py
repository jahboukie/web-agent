#!/usr/bin/env python3
"""
Test script to verify Neon database connection.
Run this after configuring your Neon database URL in .env
"""

import asyncio
import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_neon_connection():
    """Test Neon PostgreSQL connection."""
    try:
        import asyncpg

        database_url = os.getenv("DATABASE_URL")
        if not database_url or "your-username" in database_url:
            print("❌ DATABASE_URL not properly configured")
            print("Please update .env with your actual Neon connection string")
            return False

        # Test connection
        print("🔌 Testing Neon database connection...")
        print(f"Database URL: {database_url[:50]}...")

        conn = await asyncpg.connect(database_url)

        # Test query
        result = await conn.fetchval("SELECT version()")
        await conn.close()

        print("✅ Neon database connection successful!")
        print(f"PostgreSQL Version: {result[:50]}...")
        return True

    except ImportError:
        print("⚠️  asyncpg library not installed. Run: pip install asyncpg")
        return False
    except Exception as e:
        print(f"❌ Neon database connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check your Neon connection string is correct")
        print("2. Ensure your Neon database is active")
        print("3. Verify IP allowlist settings in Neon console")
        return False


async def test_sqlalchemy_connection():
    """Test SQLAlchemy async connection."""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine

        async_url = os.getenv("ASYNC_DATABASE_URL")
        if not async_url or "your-username" in async_url:
            print("❌ ASYNC_DATABASE_URL not properly configured")
            return False

        print("🔌 Testing SQLAlchemy async connection...")

        engine = create_async_engine(async_url)
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.fetchone()

        await engine.dispose()

        print("✅ SQLAlchemy async connection successful!")
        return True

    except ImportError as e:
        print(f"⚠️  Missing dependency: {e}")
        print("Run: pip install sqlalchemy asyncpg")
        return False
    except Exception as e:
        print(f"❌ SQLAlchemy connection failed: {e}")
        return False


async def main():
    """Main test function."""
    print("🐘 Testing Neon PostgreSQL Connection...")
    print("=" * 50)

    # Test basic connection
    basic_ok = await test_neon_connection()

    if basic_ok:
        # Test SQLAlchemy connection
        sqlalchemy_ok = await test_sqlalchemy_connection()
    else:
        sqlalchemy_ok = False

    print("=" * 50)
    if basic_ok and sqlalchemy_ok:
        print("🎉 Neon database fully configured and working!")
        print("Ready to run migrations: alembic upgrade head")
    elif basic_ok:
        print("⚠️  Basic connection works, SQLAlchemy needs setup")
    else:
        print("❌ Database connection failed")
        print("\nNext steps:")
        print("1. Get your Neon connection string from: https://console.neon.tech/")
        print("2. Update DATABASE_URL and ASYNC_DATABASE_URL in .env")
        print("3. Run this test again")


if __name__ == "__main__":
    # Add missing import
    from sqlalchemy import text

    asyncio.run(main())
