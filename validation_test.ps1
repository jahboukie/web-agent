# WebAgent Phase 2B Validation Test
Write-Host "🚀 Starting WebAgent Phase 2B Validation Test..." -ForegroundColor Green

# Step 1: Login and get token
Write-Host "`n1. Authenticating..." -ForegroundColor Yellow
$loginBody = @{
    username = "testuser"
    password = "testpass123"
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method POST -Headers @{"Content-Type"="application/json"} -Body $loginBody
    $token = $loginResponse.access_token
    Write-Host "✅ Authentication successful!" -ForegroundColor Green
    Write-Host "Token: $($token.Substring(0,20))..." -ForegroundColor Gray
} catch {
    Write-Host "❌ Authentication failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 2: Submit webpage parsing request
Write-Host "`n2. Submitting webpage parsing request for https://vercel.com..." -ForegroundColor Yellow
$parseBody = @{
    url = "https://vercel.com"
    include_screenshot = $false
    wait_for_load = 2
    wait_for_network_idle = $true
} | ConvertTo-Json

try {
    $parseResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/web-pages/parse" -Method POST -Headers @{"Authorization"="Bearer $token"; "Content-Type"="application/json"} -Body $parseBody
    $taskId = $parseResponse.task_id
    Write-Host "✅ Parse request submitted!" -ForegroundColor Green
    Write-Host "Task ID: $taskId" -ForegroundColor Gray
} catch {
    Write-Host "❌ Parse request failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 3: Monitor task progress
Write-Host "`n3. Monitoring task progress..." -ForegroundColor Yellow
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

        Write-Host "   Attempt $attempt`: $status | $progress% | $step" -ForegroundColor Cyan

        if ($status -eq "COMPLETED") {
            Write-Host "✅ Task completed successfully!" -ForegroundColor Green
            break
        } elseif ($status -eq "FAILED") {
            Write-Host "❌ Task failed!" -ForegroundColor Red
            Write-Host "Error: $($statusResponse.error_message)" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "   Error checking status: $($_.Exception.Message)" -ForegroundColor Red
    }

} while ($attempt -lt $maxAttempts)

if ($attempt -ge $maxAttempts) {
    Write-Host "⚠️ Task did not complete within timeout" -ForegroundColor Yellow
    Write-Host "Final status: $status | $progress% | $step" -ForegroundColor Gray
}

# Step 4: Get results if completed
if ($status -eq "COMPLETED") {
    Write-Host "`n4. Retrieving semantic analysis results..." -ForegroundColor Yellow

    try {
        $resultsResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/web-pages/$taskId" -Method GET -Headers @{"Authorization"="Bearer $token"}

        Write-Host "✅ Results retrieved successfully!" -ForegroundColor Green
        Write-Host "`n📊 SEMANTIC ANALYSIS SUMMARY:" -ForegroundColor Magenta
        Write-Host "   URL: $($resultsResponse.url)" -ForegroundColor White
        Write-Host "   Title: $($resultsResponse.title)" -ForegroundColor White
        Write-Host "   Domain: $($resultsResponse.domain)" -ForegroundColor White
        Write-Host "   Interactive Elements: $($resultsResponse.interactive_elements.Count)" -ForegroundColor White
        Write-Host "   Content Blocks: $($resultsResponse.content_blocks.Count)" -ForegroundColor White
        Write-Host "   Action Capabilities: $($resultsResponse.action_capabilities.Count)" -ForegroundColor White
        Write-Host "   Parsing Duration: $($resultsResponse.parsing_duration_ms)ms" -ForegroundColor White
        Write-Host "   Content Hash: $($resultsResponse.content_hash)" -ForegroundColor White

        Write-Host "`nINTERACTIVE ELEMENTS (First 5):" -ForegroundColor Magenta
        $resultsResponse.interactive_elements | Select-Object -First 5 | ForEach-Object {
            Write-Host "   - $($_.tag_name): $($_.text_content.Substring(0, [Math]::Min(50, $_.text_content.Length)))..." -ForegroundColor White
        }

        Write-Host "`nACTION CAPABILITIES:" -ForegroundColor Magenta
        $resultsResponse.action_capabilities | ForEach-Object {
            Write-Host "   - $($_.action_type): $($_.description)" -ForegroundColor White
        }

    } catch {
        Write-Host "Failed to retrieve results: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "`nWebAgent Phase 2B Validation Test Complete!" -ForegroundColor Green
