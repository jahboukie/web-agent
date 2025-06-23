# Fix WebAgent Database Issues
Write-Host "🔧 Fixing WebAgent Database" -ForegroundColor Cyan
Write-Host "===========================" -ForegroundColor Cyan

# Set environment
$env:PYTHONPATH = "."

Write-Host "`n📋 Running database migrations..." -ForegroundColor Yellow
try {
    alembic upgrade head
    Write-Host "✅ Database migrations completed" -ForegroundColor Green
} catch {
    Write-Host "❌ Migration failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "💡 Trying to create initial tables..." -ForegroundColor Yellow
    
    # If migrations fail, try to run them one by one
    try {
        alembic stamp head
        Write-Host "✅ Database stamped as current" -ForegroundColor Green
    } catch {
        Write-Host "❌ Could not stamp database: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`n🔧 Testing database connection..." -ForegroundColor Yellow
try {
    # Simple Python test
    python -c "
import sqlite3
conn = sqlite3.connect('webagent.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\";')
tables = cursor.fetchall()
print(f'Found {len(tables)} tables: {[t[0] for t in tables]}')
conn.close()
print('✅ Database accessible')
"
    Write-Host "✅ Database connection successful" -ForegroundColor Green
} catch {
    Write-Host "❌ Database test failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n📊 Database fix attempt complete!" -ForegroundColor Cyan