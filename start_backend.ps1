# Start WebAgent Backend Server
Write-Host "Starting WebAgent Backend Server on http://127.0.0.1:8000" -ForegroundColor Green

# Set environment variables
$env:PYTHONPATH = "."
$env:DEBUG = "true"

# Start the server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload