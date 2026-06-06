param(
    [string]$TaskName = "EduAgentHebtuWeeklyCrawl",
    [string]$PythonExe = "D:\anaconde\envs\edu-agent\python.exe",
    [string]$RunTime = "02:00",
    [string]$Day = "SUN"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$UpdateScript = Join-Path $ProjectRoot "scripts\update_knowledge_base.ps1"

if (-not (Test-Path -LiteralPath $UpdateScript)) {
    throw "Update script not found: $UpdateScript"
}

$action = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$UpdateScript`" -PythonExe `"$PythonExe`""

schtasks /Create /TN $TaskName /SC WEEKLY /D $Day /ST $RunTime /TR $action /F
if ($LASTEXITCODE -ne 0) {
    throw "Failed to register scheduled task with exit code $LASTEXITCODE"
}

Write-Host "Registered weekly crawl task '$TaskName' at $Day $RunTime."
