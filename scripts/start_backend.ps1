param(
    [string]$BindAddress = '127.0.0.1',
    [int]$Port = 8000,
    [switch]$Reload
)

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $python)) {
    throw "Project virtual environment not found at $python. Follow README.md to create it."
}

$uvicornArguments = @(
    '-m', 'uvicorn', 'backend.main:app',
    '--host', $BindAddress,
    '--port', $Port.ToString()
)

if ($Reload) {
    $uvicornArguments += '--reload'
}

Write-Host "Starting Trading Buddy at http://${BindAddress}:$Port" -ForegroundColor Cyan
Push-Location $projectRoot
try {
    & $python @uvicornArguments
} finally {
    Pop-Location
}



