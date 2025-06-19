# WebAgent Phase 2B Validation Test
Write-Host "Starting WebAgent Phase 2B Validation Test..." -ForegroundColor Green

# Step 1: Login and get token
Write-Host "1. Authenticating..." -ForegroundColor Yellow
$loginBody = @{
    username = "testuser"
    password = "Test123!"
}

try {
    $loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method POST -Headers @{"Content-Type"="application/x-www-form-urlencoded"} -Body $loginBody
    $token = $loginResponse.access_token
    Write-Host "Authentication successful!" -ForegroundColor Green
} catch {
    Write-Host "Authentication failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 2: Submit webpage parsing request
Write-Host "2. Submitting webpage parsing request for https://vercel.com..." -ForegroundColor Yellow
$parseBody = @{
    url = "https://vercel.com"
    include_screenshot = $false
    wait_for_load = 2
    wait_for_network_idle = $true
} | ConvertTo-Json

try {
    $parseResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/web-pages/parse" -Method POST -Headers @{"Authorization"="Bearer $token"; "Content-Type"="application/json"} -Body $parseBody
    $taskId = $parseResponse.task_id
    Write-Host "Parse request submitted! Task ID: $taskId" -ForegroundColor Green
} catch {
    Write-Host "Parse request failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 3: Monitor task progress
Write-Host "3. Monitoring task progress..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0

do {
    $attempt++
    Start-Sleep -Seconds 2
    
    try {
        $statusResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/web-pages/$taskId" -Method GET -Headers @{"Authorization"="Bearer $token"}
        $status = $statusResponse.status
        $progress = $statusResponse.progress_percentage
        $step = $statusResponse.current_step
        
        Write-Host "   Attempt $attempt : $status | $progress% | $step" -ForegroundColor Cyan
        
        if ($status -eq "COMPLETED") {
            Write-Host "Task completed successfully!" -ForegroundColor Green
            break
        } elseif ($status -eq "FAILED") {
            Write-Host "Task failed!" -ForegroundColor Red
            Write-Host "Error: $($statusResponse.error_message)" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "   Error checking status: $($_.Exception.Message)" -ForegroundColor Red
    }
    
} while ($attempt -lt $maxAttempts)

if ($attempt -ge $maxAttempts) {
    Write-Host "Task did not complete within timeout" -ForegroundColor Yellow
    Write-Host "Final status: $status | $progress% | $step" -ForegroundColor Gray
}

# Step 4: Get results if completed
if ($status -eq "COMPLETED") {
    Write-Host "4. Retrieving semantic analysis results..." -ForegroundColor Yellow
    
    try {
        $resultsResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/web-pages/$taskId" -Method GET -Headers @{"Authorization"="Bearer $token"}
        
        Write-Host "Results retrieved successfully!" -ForegroundColor Green
        Write-Host "SEMANTIC ANALYSIS SUMMARY:" -ForegroundColor Magenta
        Write-Host "   URL: $($resultsResponse.url)" -ForegroundColor White
        Write-Host "   Title: $($resultsResponse.title)" -ForegroundColor White
        Write-Host "   Domain: $($resultsResponse.domain)" -ForegroundColor White
        Write-Host "   Interactive Elements: $($resultsResponse.interactive_elements.Count)" -ForegroundColor White
        Write-Host "   Content Blocks: $($resultsResponse.content_blocks.Count)" -ForegroundColor White
        Write-Host "   Parsing Duration: $($resultsResponse.parsing_duration_ms)ms" -ForegroundColor White
        
    } catch {
        Write-Host "Failed to retrieve results: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "WebAgent Phase 2B Validation Test Complete!" -ForegroundColor Green
