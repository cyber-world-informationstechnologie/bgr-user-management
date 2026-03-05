<#
.SYNOPSIS
    Scheduled task wrapper — runs Fix-ProfilePermissions.ps1 with -Fix to
    automatically repair all profile folder permissions.

.DESCRIPTION
    Intended to be registered as a Windows Scheduled Task.
    Logs output to a timestamped file under C:\ScheduledTasks\Logs\.

    Deploy this file to C:\ScheduledTasks\fix-perm.ps1 alongside
    Fix-ProfilePermissions.ps1 in the same directory.

    Register the task (run once as admin):
        schtasks /Create /TN "Fix Profile Permissions" `
            /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\ScheduledTasks\fix-perm.ps1" `
            /SC DAILY /ST 02:00 `
            /RU SYSTEM /RL HIGHEST /F

    Or via PowerShell:
        $action  = New-ScheduledTaskAction -Execute "powershell.exe" `
                     -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\ScheduledTasks\fix-perm.ps1"
        $trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM
        $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
        Register-ScheduledTask -TaskName "Fix Profile Permissions" `
            -Action $action -Trigger $trigger -Principal $principal -Force
#>

$ErrorActionPreference = "Stop"

$scriptDir = "C:\ScheduledTasks"
$logDir    = Join-Path $scriptDir "Logs"
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$logFile   = Join-Path $logDir "fix-perm_$timestamp.log"

# Ensure log directory exists
if (-not (Test-Path $logDir)) {
    New-Item -Path $logDir -ItemType Directory -Force | Out-Null
}

# Run the main script with -Fix, capture all output to log
& "$scriptDir\Fix-ProfilePermissions.ps1" -Fix 2>&1 | Tee-Object -FilePath $logFile

# Clean up logs older than 30 days
Get-ChildItem -Path $logDir -Filter "fix-perm_*.log" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
    Remove-Item -Force
