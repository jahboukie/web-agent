# PowerShell script to format code with Black
Write-Host "Formatting code with Black..."

# Activate virtual environment and run black
.\venv\Scripts\python.exe -m black .

Write-Host "Code formatting completed!"
