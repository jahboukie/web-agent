# WebAgent + Aura Complete Startup Script
Write-Host "🚀 Starting WebAgent + Aura Platform" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Set environment variables
$env:PYTHONPATH = "."
$env:DEBUG = "true"
$env:ENVIRONMENT = "development"

Write-Host "📋 Checking dependencies..." -ForegroundColor Yellow

# Check if uvicorn is available
try {
    $uvicornVersion = uvicorn --version 2>$null
    Write-Host "✅ uvicorn found: $uvicornVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ uvicorn not found. Please install: pip install uvicorn" -ForegroundColor Red
    exit 1
}

# Check if npm is available for frontend
try {
    $npmVersion = npm --version 2>$null
    Write-Host "✅ npm found: v$npmVersion" -ForegroundColor Green
} catch {
    Write-Host "⚠️ npm not found. Frontend won't be available" -ForegroundColor Yellow
}

Write-Host "`n🔧 Starting Backend Server..." -ForegroundColor Green
Write-Host "Backend will be available at: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "API Documentation: http://127.0.0.1:8000/docs" -ForegroundColor Cyan

# Start backend in background job
$backendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    $env:PYTHONPATH = "."
    $env:DEBUG = "true"
    uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
}

Write-Host "✅ Backend started (Job ID: $($backendJob.Id))" -ForegroundColor Green

Write-Host "`n🎨 Starting Frontend Server..." -ForegroundColor Blue
Write-Host "Frontend will be available at: http://localhost:3000" -ForegroundColor Cyan

# Change to frontend directory and start
if (Test-Path "aura") {
    Set-Location "aura"
    
    # Check if node_modules exists
    if (-not (Test-Path "node_modules")) {
        Write-Host "📦 Installing frontend dependencies..." -ForegroundColor Yellow
        npm install
    }
    
    Write-Host "✅ Starting frontend development server..." -ForegroundColor Blue
    npm run dev
} else {
    Write-Host "❌ Frontend directory 'aura' not found" -ForegroundColor Red
}

# Cleanup function
function Cleanup {
    Write-Host "`n🛑 Shutting down servers..." -ForegroundColor Yellow
    Stop-Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob -ErrorAction SilentlyContinue
    Write-Host "✅ Cleanup complete" -ForegroundColor Green
}

# Register cleanup on script exit
Register-EngineEvent PowerShell.Exiting -Action { Cleanup }