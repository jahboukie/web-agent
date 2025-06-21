#!/usr/bin/env python3
"""
Check database schema to see if execution_plans table has user_id column.
"""

import sqlite3
import sys

def check_execution_plans_schema():
    """Check if execution_plans table has user_id column."""
    try:
        # Connect to database
        conn = sqlite3.connect('webagent.db')
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute("PRAGMA table_info(execution_plans)")
        columns = cursor.fetchall()
        
        print("execution_plans table schema:")
        print("=" * 50)
        
        has_user_id = False
        for column in columns:
            cid, name, type_, notnull, default_value, pk = column
            print(f"{cid}: {name} ({type_}) {'NOT NULL' if notnull else 'NULL'} {'PK' if pk else ''}")
            if name == 'user_id':
                has_user_id = True
        
        print("=" * 50)
        print(f"Has user_id column: {has_user_id}")
        
        if not has_user_id:
            print("\n❌ user_id column is missing from execution_plans table")
            print("Need to run migration or add column manually")
        else:
            print("\n✅ user_id column exists in execution_plans table")
        
        # Check if table exists at all
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='execution_plans'")
        table_exists = cursor.fetchone() is not None
        
        print(f"Table exists: {table_exists}")
        
        conn.close()
        return has_user_id
        
    except Exception as e:
        print(f"Error checking database schema: {e}")
        return False

def check_alembic_version():
    """Check current alembic version."""
    try:
        conn = sqlite3.connect('webagent.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT version_num FROM alembic_version")
        version = cursor.fetchone()
        
        if version:
            print(f"Current Alembic version: {version[0]}")
        else:
            print("No Alembic version found")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking Alembic version: {e}")

if __name__ == "__main__":
    print("🔍 Checking WebAgent Database Schema")
    print()
    
    check_alembic_version()
    print()
    
    has_user_id = check_execution_plans_schema()
    
    if not has_user_id:
        sys.exit(1)
    else:
        sys.exit(0)
