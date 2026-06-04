# Registers the Slay the Spire 2 Run Doctor pipeline in Windows Task Scheduler.
# Run this script from PowerShell. If registration fails, open PowerShell as
# Administrator and run it again.

$ErrorActionPreference = "Stop"

# Task Scheduler metadata.
$TaskName = "SP2_RunDoctor_Pipeline"
$TaskDescription = "Runs the Slay the Spire 2 Run Doctor data pipeline daily at 02:00 AM."

# Full paths required by the scheduled task action.
$ProjectRoot = "C:\Users\24364\sp2_project"
$PythonExe = "C:\Users\24364\AppData\Local\Programs\Python\Python314\python.exe"
$PipelineScript = Join-Path $ProjectRoot "pipeline_runner.py"
$LogsDir = Join-Path $ProjectRoot "logs"
$ArchiveDir = Join-Path $ProjectRoot "archive"
$LatestInsights = Join-Path $ProjectRoot "data\latest_insights.json"

# Create folders now so the first scheduled run has the expected structure.
New-Item -ItemType Directory -Force -Path $LogsDir, $ArchiveDir | Out-Null

# The scheduled task runs this PowerShell command:
# 1. Ensures logs/ and archive/ exist.
# 2. Runs pipeline_runner.py using the full python.exe path.
# 3. Copies data/latest_insights.json into archive/ with a timestamped filename
#    when the merged JSON file exists.
$RunCommand = @"
`$ErrorActionPreference = 'Continue'
New-Item -ItemType Directory -Force -Path '$LogsDir', '$ArchiveDir' | Out-Null
& '$PythonExe' '$PipelineScript'
`$ExitCode = `$LASTEXITCODE
if (Test-Path '$LatestInsights') {
    `$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    `$ArchiveFile = Join-Path '$ArchiveDir' "latest_insights_`$Stamp.json"
    Copy-Item -Path '$LatestInsights' -Destination `$ArchiveFile -Force
}
exit `$ExitCode
"@

# Use PowerShell as the task action so folder checks and archive rotation happen
# immediately before each pipeline run.
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -Command $([System.Management.Automation.Language.CodeGeneration]::QuoteArgument($RunCommand))" `
    -WorkingDirectory $ProjectRoot

# Daily trigger at 02:00 AM local machine time.
$Trigger = New-ScheduledTaskTrigger -Daily -At "02:00AM"

# Run whether the user is logged on or not when possible, and start when
# available after a missed schedule caused by a restart or powered-off machine.
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel LeastPrivilege

# Replace any existing task with the same name so updates are idempotent.
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description $TaskDescription `
    -Force | Out-Null

Write-Host "Scheduled task registered: $TaskName"
Write-Host "Runs daily at 02:00 AM."
Write-Host "Pipeline: $PythonExe $PipelineScript"
Write-Host ""
Write-Host "Check the task:"
Write-Host "  Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Get-ScheduledTaskInfo -TaskName '$TaskName'"
Write-Host ""
Write-Host "Run the task manually:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "Remove the task:"
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
