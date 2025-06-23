# Check if WebAgent servers are running
Write-Host "🔍 Checking WebAgent + Aura Server Status" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Check Backend
Write-Host "`n🔧 Checking Backend (http://127.0.0.1:8000)..." -ForegroundColor Green
try {
    $backendResponse = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 5
    Write-Host "✅ Backend Status: $($backendResponse.status)" -ForegroundColor Green
    Write-Host "📋 Version: $($backendResponse.version)" -ForegroundColor Cyan
    Write-Host "🗄️ Database: $($backendResponse.database.status)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Backend not responding: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "💡 Start backend with: uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload" -ForegroundColor Yellow
}

# Check Frontend
Write-Host "`n🎨 Checking Frontend (http://localhost:3000)..." -ForegroundColor Blue
try {
    $frontendResponse = Invoke-WebRequest -Uri "http://localhost:3000" -Method Get -TimeoutSec 5
    if ($frontendResponse.StatusCode -eq 200) {
        Write-Host "✅ Frontend responding (Status: $($frontendResponse.StatusCode))" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Frontend responding but with status: $($frontendResponse.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Frontend not responding: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "💡 Start frontend with: cd aura && npm run dev" -ForegroundColor Yellow
}

Write-Host "`n📊 Server Status Summary:" -ForegroundColor Cyan
Write-Host "Backend API: http://127.0.0.1:8000" -ForegroundColor White
Write-Host "Frontend UI: http://localhost:3000" -ForegroundColor White
Write-Host "API Docs: http://127.0.0.1:8000/docs" -ForegroundColor White
