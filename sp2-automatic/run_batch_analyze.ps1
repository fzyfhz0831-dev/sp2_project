# Upload sample run JSON files to the FastAPI analyzer.
# Usage:
#   .\run_batch_analyze.ps1
#   .\run_batch_analyze.ps1 -ApiBaseUrl http://127.0.0.1:8000 -Limit 5

param(
    [string]$ApiBaseUrl = "http://127.0.0.1:8000",
    [int]$Limit = 20
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogsDir = Join-Path $ProjectRoot "logs"
$ScriptPath = Join-Path $ProjectRoot "batch_analyze.py"
$ManualLog = Join-Path $LogsDir "batch_analyze_manual.log"

New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null

"Batch analyze run started at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Tee-Object -FilePath $ManualLog
"Backend URL: $ApiBaseUrl" | Tee-Object -FilePath $ManualLog -Append

Push-Location $ProjectRoot
try {
    & python $ScriptPath --api-base-url $ApiBaseUrl --limit $Limit 2>&1 |
        Tee-Object -FilePath $ManualLog -Append
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
