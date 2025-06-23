# Mock Data Removal Best Practices

## 🎯 Overview

This guide outlines standard best practices for removing mock data before staging and production deployment.

## 📋 Pre-Deployment Checklist

### 1. **Environment Configuration**

#### Development Environment
```bash
# .env.development
ENVIRONMENT=development
DATABASE_URL=postgresql://localhost:5432/webagent_dev
SEED_DEMO_DATA=true
CREATE_TEST_USERS=true
```

#### Staging Environment
```bash
# .env.staging
ENVIRONMENT=staging
DATABASE_URL=postgresql://staging-db:5432/webagent_staging
SEED_DEMO_DATA=false
CREATE_TEST_USERS=false
```

#### Production Environment
```bash
# .env.production
ENVIRONMENT=production
DATABASE_URL=postgresql://prod-db:5432/webagent_prod
SEED_DEMO_DATA=false
CREATE_TEST_USERS=false
```

### 2. **Mock Data Sources Identified**

#### ✅ **Safe - Test/Development Only**
- `tests/` - All test files (19 files)
- `demo_*.py` - Demo scripts
- `test_*.py` - Test scripts  
- `validate_*.py` - Validation scripts
- `check_*.py` - Debug scripts
- `scripts/test_*.py` - Test automation

#### ⚠️ **Review Required**
- `app/db/init_db.py` - Database initialization (✅ Already environment-aware)
- `tests/e2e_config.json` - Test configuration with demo emails
- Configuration files with default passwords

## 🔧 **Implementation Strategy**

### 1. **Database Initialization Enhancement**

Current implementation in `app/db/init_db.py` is already production-safe:

```python
async def init_db(db: AsyncSession) -> None:
    # Always create superuser
    await create_superuser(db)
    
    # Only create test data in development
    if settings.ENVIRONMENT == "development":
        await create_test_data(db)
```

### 2. **Configuration Management**

#### Environment Variables
```python
# app/core/config.py
class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    SEED_DEMO_DATA: bool = False
    CREATE_TEST_USERS: bool = False
    
    @property
    def should_seed_demo_data(self) -> bool:
        return self.ENVIRONMENT == "development" and self.SEED_DEMO_DATA
```

### 3. **Pre-Deployment Validation Script**

```python
# scripts/validate_production_readiness.py
import os
import sys
from app.core.config import settings

def validate_production_config():
    """Validate production configuration has no mock data."""
    errors = []
    
    # Check environment
    if settings.ENVIRONMENT not in ["staging", "production"]:
        errors.append(f"Invalid environment: {settings.ENVIRONMENT}")
    
    # Check demo data flags
    if settings.SEED_DEMO_DATA:
        errors.append("SEED_DEMO_DATA must be false in production")
    
    # Check for default passwords
    if "changeme" in settings.SECRET_KEY.lower():
        errors.append("Default SECRET_KEY detected")
    
    if "changeme" in os.getenv("POSTGRES_PASSWORD", "").lower():
        errors.append("Default POSTGRES_PASSWORD detected")
    
    # Check for demo email domains
    demo_domains = ["example.com", "test.com", "demo.com"]
    for domain in demo_domains:
        if domain in str(settings.CORS_ORIGINS):
            errors.append(f"Demo domain {domain} found in CORS_ORIGINS")
    
    return errors

if __name__ == "__main__":
    errors = validate_production_config()
    if errors:
        print("❌ Production readiness validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("✅ Production configuration validated")
```

## 🚀 **Deployment Pipeline Integration**

### 1. **CI/CD Pipeline Steps**

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  validate-production:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Validate Production Readiness
        run: python scripts/validate_production_readiness.py
        env:
          ENVIRONMENT: production
          SEED_DEMO_DATA: false
          SECRET_KEY: ${{ secrets.SECRET_KEY }}
          POSTGRES_PASSWORD: ${{ secrets.POSTGRES_PASSWORD }}
```

### 2. **Database Migration Strategy**

```bash
# Production deployment script
#!/bin/bash

# 1. Validate configuration
echo "Validating production configuration..."
python scripts/validate_production_readiness.py

# 2. Run migrations on fresh database
echo "Running database migrations..."
alembic upgrade head

# 3. Initialize with production data only
echo "Initializing production database..."
python -c "
from app.db.session import get_db
from app.db.init_db import create_superuser
import asyncio

async def init_prod_db():
    async for db in get_db():
        await create_superuser(db)
        break

asyncio.run(init_prod_db())
"

echo "✅ Production database ready"
```

## 🔍 **Validation Commands**

### 1. **Pre-Deployment Checks**
```bash
# Check for mock data patterns
grep -r "demo\|test\|mock" app/ --exclude-dir=tests
grep -r "@test\|@demo\|@example" app/ --exclude-dir=tests

# Validate environment
python -c "from app.core.config import settings; print(f'Environment: {settings.ENVIRONMENT}')"

# Check database is clean
python -c "
from app.db.session import get_db
from app.models.user import User
import asyncio
from sqlalchemy import select

async def check_users():
    async for db in get_db():
        result = await db.execute(select(User))
        users = result.scalars().all()
        print(f'Total users: {len(users)}')
        for user in users:
            print(f'- {user.email} (superuser: {user.is_superuser})')
        break

asyncio.run(check_users())
"
```

### 2. **Post-Deployment Verification**
```bash
# Verify only production admin exists
curl -X GET "https://api.yourapp.com/health"
curl -X GET "https://api.yourapp.com/users/me" -H "Authorization: Bearer $ADMIN_TOKEN"
```

## 🚨 **Common Pitfalls to Avoid**

### 1. **Hardcoded Test Data**
❌ **Bad**:
```python
# Hardcoded in production code
admin_user = User(email="admin@test.com", password="password123")
```

✅ **Good**:
```python
# Environment-based configuration
admin_email = settings.ADMIN_EMAIL or os.getenv("ADMIN_EMAIL")
admin_password = os.getenv("ADMIN_PASSWORD")
```

### 2. **Test Database URLs**
❌ **Bad**:
```python
DATABASE_URL = "postgresql://localhost:5432/webagent_test"
```

✅ **Good**:
```python
DATABASE_URL = os.getenv("DATABASE_URL")
```

### 3. **Demo Data in Seeds**
❌ **Bad**:
```python
# Always creates demo data
def seed_database():
    create_demo_users()
    create_sample_tasks()
```

✅ **Good**:
```python
# Environment-controlled seeding
def seed_database():
    if settings.ENVIRONMENT == "development":
        create_demo_users()
        create_sample_tasks()
```

## ✅ **WebAgent Current Status**

### **Already Production-Safe**
- ✅ Environment-based database initialization
- ✅ Test data segregated in `tests/` directory
- ✅ Demo scripts clearly labeled
- ✅ Configuration management with environment variables
- ✅ No hardcoded credentials in production code

### **Recommendations**
1. **Add validation script** to CI/CD pipeline
2. **Review default passwords** in docker-compose.yml
3. **Implement production deployment checklist**
4. **Add post-deployment verification steps**

## 🎯 **Summary**

WebAgent already follows best practices for mock data management:
- Test data is properly segregated
- Database initialization is environment-aware
- Configuration is externalized
- Demo scripts are clearly identified

The platform is **production-ready** with minimal additional validation steps needed.