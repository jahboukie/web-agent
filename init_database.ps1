# Initialize WebAgent Database
Write-Host "🗄️ Initializing WebAgent Database" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# Set environment variables
$env:PYTHONPATH = "."
$env:DEBUG = "true"

Write-Host "📋 Running database migrations..." -ForegroundColor Yellow

try {
    # Run Alembic migrations
    alembic upgrade head
    Write-Host "✅ Database migrations completed successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Database migration failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "💡 Make sure alembic is installed: pip install alembic" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n🔧 Checking database health..." -ForegroundColor Yellow

try {
    # Test database connection
    python -c "
import asyncio
from app.db.session import get_async_session
from app.db.init_db import check_database_health

async def test_db():
    async for db in get_async_session():
        health = await check_database_health(db)
        print(f'Database health: {health}')
        break

asyncio.run(test_db())
"
    Write-Host "✅ Database is healthy and ready" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Database health check failed: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "💡 Database may still work, but there might be configuration issues" -ForegroundColor Yellow
}

Write-Host "`n📊 Database Initialization Complete!" -ForegroundColor Green
Write-Host "Database file: webagent.db" -ForegroundColor Cyan
Write-Host "Ready to start WebAgent backend server" -ForegroundColor Cyan
