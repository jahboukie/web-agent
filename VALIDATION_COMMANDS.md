# WebAgent Phase 2B Validation Commands

**Status:** Phase 2B COMPLETE - Ready for validation testing
**Implementation:** Background task processing architecture fully operational

---

## 🚀 **Quick Validation Flow**

### **Step 1: Authentication**
```bash
# Get authentication token
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=Test123!" | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "Token: $TOKEN"
```

### **Step 2: Start Background Webpage Parsing**
```bash
# Parse webpage (returns immediately with task_id)
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/web-pages/parse" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://vercel.com",
    "include_screenshot": false,
    "wait_for_load": 2,
    "wait_for_network_idle": true
  }')

echo "Parse Response: $RESPONSE"

# Extract task_id
TASK_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])")
echo "Task ID: $TASK_ID"
```

### **Step 3: Monitor Real-time Progress**
```bash
# Check task status (repeat until completed)
curl -s "http://localhost:8000/api/v1/web-pages/$TASK_ID" \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Status: {data.get('status', 'unknown')}\")
print(f\"Progress: {data.get('progress_percentage', 0)}%\")
print(f\"Step: {data.get('current_step', 'unknown')}\")
print(f\"Message: {data.get('message', 'no message')}\")
"
```

### **Step 4: Get Semantic Analysis Results**
```bash
# Get comprehensive parsing results (when completed)
curl -s "http://localhost:8000/api/v1/web-pages/$TASK_ID/results" \
  -H "Authorization: Bearer $TOKEN" | \
  python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'result_data' in data:
        result = data['result_data']
        print('🎯 SEMANTIC ANALYSIS RESULTS:')
        print(f\"   URL: {result.get('url', 'N/A')}\")
        print(f\"   Title: {result.get('title', 'N/A')}\")
        print(f\"   Interactive Elements: {len(result.get('interactive_elements', []))}\")
        print(f\"   Content Blocks: {len(result.get('content_blocks', []))}\")
        print(f\"   Processing Time: {result.get('processing_time_ms', 0)}ms\")
    else:
        print('No results available yet')
except:
    print('Error parsing results')
"
```

---

## 🔧 **Alternative Validation Methods**

### **Method 1: Python Validation Script**
```bash
# Run comprehensive validation test
python3 validation_test.py
```

### **Method 2: PowerShell Script (Windows)**
```powershell
# Run PowerShell validation
.\simple_test.ps1
```

### **Method 3: Manual cURL Testing**

#### **Authentication:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=Test123!"
```

#### **Parse Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/web-pages/parse" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://vercel.com",
    "include_screenshot": true,
    "wait_for_load": 3
  }'
```

#### **Status Check:**
```bash
curl "http://localhost:8000/api/v1/web-pages/TASK_ID" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### **Results Retrieval:**
```bash
curl "http://localhost:8000/api/v1/web-pages/TASK_ID/results" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📊 **Advanced Testing Endpoints**

### **Cache Management:**
```bash
# Get cache statistics
curl "http://localhost:8000/api/v1/web-pages/cache/stats" \
  -H "Authorization: Bearer $TOKEN"

# Invalidate cache for specific URL
curl -X DELETE "http://localhost:8000/api/v1/web-pages/cache/https://vercel.com" \
  -H "Authorization: Bearer $TOKEN"
```

### **Task Metrics:**
```bash
# Get parsing metrics for last 24 hours
curl "http://localhost:8000/api/v1/web-pages/metrics?hours=24" \
  -H "Authorization: Bearer $TOKEN"

# Get active parsing tasks
curl "http://localhost:8000/api/v1/web-pages/active" \
  -H "Authorization: Bearer $TOKEN"
```

### **Task Management:**
```bash
# Retry failed task
curl -X POST "http://localhost:8000/api/v1/web-pages/$TASK_ID/retry" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🏥 **Health & Status Checks**

### **Application Health:**
```bash
# Check application health
curl "http://localhost:8000/health"

# Check detailed health with database status
curl "http://localhost:8000/health" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Status: {data.get('status', 'unknown')}\")
print(f\"Database: {data.get('database', {}).get('status', 'unknown')}\")
print(f\"Version: {data.get('version', 'unknown')}\")
"
```

### **API Documentation:**
```bash
# View API documentation (if debug enabled)
open http://localhost:8000/docs
```

---

## 🎯 **Expected Results**

### **Successful Parse Response:**
```json
{
  "task_id": 123,
  "status": "queued",
  "message": "Webpage parsing started",
  "estimated_duration_seconds": 30,
  "check_status_url": "/api/v1/parse/123",
  "url": "https://vercel.com"
}
```

### **Status Update Response:**
```json
{
  "task_id": 123,
  "status": "in_progress",
  "progress_percentage": 65,
  "current_step": "extracting_interactive_elements",
  "duration_seconds": 15.5,
  "memory_usage_mb": 256,
  "message": "Processing: extracting_interactive_elements"
}
```

### **Completed Results Response:**
```json
{
  "result_data": {
    "web_page": {
      "url": "https://vercel.com",
      "title": "Vercel: Develop. Preview. Ship.",
      "domain": "vercel.com",
      "interactive_elements_count": 45,
      "content_hash": "abc123...",
      "semantic_data": {...}
    },
    "processing_time_ms": 28500,
    "interactive_elements": [...],
    "content_blocks": [...],
    "action_capabilities": [...]
  }
}
```

---

## 🚨 **Troubleshooting**

### **Common Issues:**

1. **Server Not Running:**
   ```bash
   # Start the server
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Authentication Failed:**
   ```bash
   # Check if test user exists or create new one
   curl -X POST "http://localhost:8000/api/v1/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "test@example.com",
       "username": "testuser",
       "password": "Test123!",
       "confirm_password": "Test123!",
       "accept_terms": true
     }'
   ```

3. **Browser Context Issues:**
   ```bash
   # Install Playwright browsers
   python -m playwright install chromium
   ```

4. **Task Timeout:**
   - Tasks may take 30-60 seconds for complex pages
   - Check server logs for detailed error information
   - Verify network connectivity to target URL

---

This validation approach tests the complete Phase 2B background task processing architecture including authentication, task creation, real-time progress tracking, semantic analysis, and result retrieval.
