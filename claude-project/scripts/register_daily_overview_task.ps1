# One-time setup: registers the "Academic Daily Overview" scheduled task --
# daily at 5:00am, wakes the PC from sleep, runs as the current user only
# while logged on (Chrome must be available). Re-running replaces it.
# Remove with: Unregister-ScheduledTask -TaskName "Academic Daily Overview"
$repo = Split-Path -Parent $PSScriptRoot
$script = Join-Path $repo "scripts\daily_overview.ps1"

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`"" `
    -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -At 5:00AM
$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName "Academic Daily Overview" -Action $action `
    -Trigger $trigger -Settings $settings -Force `
    -Description "Runs Claude Code /daily-overview: one Daily Overview email per course."
