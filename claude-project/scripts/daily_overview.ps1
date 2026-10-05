# Runs /daily-overview headless -- invoked by Windows Task Scheduler at 5:00am
# (see scripts/register_daily_overview_task.ps1). Logs to data/logs/.
# Requires: Chrome running with the Claude extension connected, and the
# claude CLI on PATH. See .claude/skills/daily-overview/SKILL.md.
$ErrorActionPreference = "Continue"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$logDir = Join-Path $repo "data\logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir ("daily_overview_{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))
"=== $(Get-Date -Format o) starting daily overview ===" | Out-File -Append -Encoding utf8 $log

# The Claude in Chrome extension lives in the user's real Chrome profile.
if (-not (Get-Process chrome -ErrorAction SilentlyContinue)) {
    Start-Process "chrome.exe"
    Start-Sleep -Seconds 30
}

# Only the tools this run needs -- nothing else is pre-approved.
$allowed = @(
    "Bash(uv run academic-sync:*)",
    "Read", "Glob", "Grep",
    "Write(data/digests/**)", "Edit(data/digests/**)",
    "Skill", "ToolSearch",
    "mcp__claude-in-chrome",
    "mcp__claude_ai_Google_Calendar__list_events",
    "mcp__claude_ai_Google_Calendar__get_event",
    "mcp__claude_ai_Google_Calendar__create_event",
    "mcp__claude_ai_Google_Calendar__update_event",
    "mcp__claude_ai_Gmail__send_message",
    "mcp__claude_ai_Google_Drive__search_files",
    "mcp__claude_ai_Google_Drive__read_file_content"
)

& claude -p "/daily-overview" --chrome --allowedTools @allowed 2>&1 |
    Out-File -Append -Encoding utf8 $log
"=== $(Get-Date -Format o) finished (exit $LASTEXITCODE) ===" | Out-File -Append -Encoding utf8 $log
