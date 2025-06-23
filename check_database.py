#!/usr/bin/env python3
"""
Check WebAgent database status and tables
"""

import asyncio
import sqlite3

from app.db.init_db import check_database_health
from app.db.session import get_async_session


def check_sqlite_tables():
    """Check SQLite database tables"""
    print("🗄️ Checking SQLite database tables...")

    try:
        conn = sqlite3.connect("webagent.db")
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        print(f"📋 Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")

        # Check if users table exists and has correct structure
        cursor.execute("PRAGMA table_info(users);")
        user_columns = cursor.fetchall()

        if user_columns:
            print(f"\n👤 Users table structure ({len(user_columns)} columns):")
            for col in user_columns:
                print(f"  - {col[1]} ({col[2]})")
        else:
            print("\n❌ Users table not found!")

        conn.close()
        return len(tables) > 0

    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False


async def check_db_health():
    """Check database health via app"""
    print("\n🔧 Checking database health via app...")

    try:
        async for db in get_async_session():
            health = await check_database_health(db)
            print(f"✅ Database health: {health}")
            break
    except Exception as e:
        print(f"❌ Database health check failed: {e}")


if __name__ == "__main__":
    # Check SQLite directly
    tables_exist = check_sqlite_tables()

    if not tables_exist:
        print("\n💡 No tables found. Run migrations: alembic upgrade head")

    # Check via app
    asyncio.run(check_db_health())
