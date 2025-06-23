#!/usr/bin/env python3
"""
Fix execution_plans table schema by adding missing user_id column.
"""

import sqlite3
import sys


def fix_execution_plans_schema():
    """Add missing user_id column to execution_plans table."""
    try:
        # Connect to database
        conn = sqlite3.connect("webagent.db")
        cursor = conn.cursor()

        print("🔧 Fixing execution_plans table schema...")

        # Check if user_id column already exists
        cursor.execute("PRAGMA table_info(execution_plans)")
        columns = cursor.fetchall()

        has_user_id = any(col[1] == "user_id" for col in columns)

        if has_user_id:
            print("✅ user_id column already exists")
            conn.close()
            return True

        print("➕ Adding user_id column...")

        # Add user_id column
        cursor.execute(
            """
            ALTER TABLE execution_plans
            ADD COLUMN user_id INTEGER
        """
        )

        # Add foreign key constraint (SQLite doesn't support adding FK constraints to existing tables)
        # We'll add an index instead for performance
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_execution_plans_user_id
            ON execution_plans(user_id)
        """
        )

        # Add task_id column if it doesn't exist
        cursor.execute("PRAGMA table_info(execution_plans)")
        columns = cursor.fetchall()
        has_task_id = any(col[1] == "task_id" for col in columns)

        if not has_task_id:
            print("➕ Adding task_id column...")
            cursor.execute(
                """
                ALTER TABLE execution_plans
                ADD COLUMN task_id INTEGER
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_execution_plans_task_id
                ON execution_plans(task_id)
            """
            )

        # Commit changes
        conn.commit()

        print("✅ execution_plans table schema fixed successfully")

        # Verify the fix
        cursor.execute("PRAGMA table_info(execution_plans)")
        columns = cursor.fetchall()

        print("\nUpdated schema:")
        for column in columns:
            cid, name, type_, notnull, default_value, pk = column
            if name in ["user_id", "task_id"]:
                print(f"  ✅ {name} ({type_})")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error fixing database schema: {e}")
        return False


if __name__ == "__main__":
    print("🚀 WebAgent Database Schema Fix")
    print("=" * 50)

    success = fix_execution_plans_schema()

    if success:
        print("\n🎉 Database schema fix completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Database schema fix failed!")
        sys.exit(1)
