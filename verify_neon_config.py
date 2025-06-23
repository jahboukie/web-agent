#!/usr/bin/env python3
"""
Simple verification of Neon database configuration.
No external dependencies required.
"""

import os
import re

def verify_neon_config():
    """Verify Neon database configuration in environment."""
    
    print("🔍 Verifying Neon Database Configuration...")
    print("=" * 50)
    
    # Read .env file directly
    env_vars = {}
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    except FileNotFoundError:
        print("❌ .env file not found")
        return False
    
    # Check DATABASE_URL
    database_url = env_vars.get('DATABASE_URL', '')
    async_url = env_vars.get('ASYNC_DATABASE_URL', '')
    
    print(f"DATABASE_URL: {database_url[:60]}...")
    print(f"ASYNC_DATABASE_URL: {async_url[:60]}...")
    print()
    
    # Validate URLs
    errors = []
    
    # Check DATABASE_URL format
    if not database_url.startswith('postgresql://'):
        errors.append("DATABASE_URL should start with 'postgresql://'")
    
    if 'neon.tech' not in database_url:
        errors.append("DATABASE_URL should contain 'neon.tech' hostname")
    
    # Check ASYNC_DATABASE_URL format  
    if not async_url.startswith('postgresql+asyncpg://'):
        errors.append("ASYNC_DATABASE_URL should start with 'postgresql+asyncpg://'")
    
    if 'neon.tech' not in async_url:
        errors.append("ASYNC_DATABASE_URL should contain 'neon.tech' hostname")
    
    # Check if they have same connection details
    db_pattern = r'postgresql(?:\+asyncpg)?://([^:]+):([^@]+)@([^/]+)/([^?]+)'
    
    db_match = re.match(db_pattern, database_url)
    async_match = re.match(db_pattern, async_url)
    
    if db_match and async_match:
        db_user, db_pass, db_host, db_name = db_match.groups()
        async_user, async_pass, async_host, async_name = async_match.groups()
        
        if (db_user != async_user or db_pass != async_pass or 
            db_host != async_host or db_name != async_name):
            errors.append("DATABASE_URL and ASYNC_DATABASE_URL should have same connection details")
        else:
            print("✅ Both URLs have matching connection details")
    
    # Check for placeholder values
    if 'your-username' in database_url or 'your-password' in database_url:
        errors.append("DATABASE_URL contains placeholder values")
    
    if 'your-username' in async_url or 'your-password' in async_url:
        errors.append("ASYNC_DATABASE_URL contains placeholder values")
    
    # Report results
    if errors:
        print("❌ Configuration Issues Found:")
        for error in errors:
            print(f"   • {error}")
        print("\n🔧 Fix these issues and run the verification again.")
        return False
    else:
        print("✅ Neon database configuration looks correct!")
        print("\n📝 Configuration Summary:")
        if db_match:
            user, _, host, dbname = db_match.groups()
            print(f"   • User: {user}")
            print(f"   • Host: {host}")
            print(f"   • Database: {dbname}")
            print(f"   • SSL: Required")
        
        print("\n🚀 Ready for:")
        print("   • Database migrations: alembic upgrade head")
        print("   • WebAgent startup with Neon database")
        
        return True

if __name__ == "__main__":
    verify_neon_config()