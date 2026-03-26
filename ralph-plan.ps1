# Ralph Loop — Plan Mode (single-shot read-only analysis)
# Usage: .\ralph-plan.ps1

$ErrorActionPreference = "Stop"

$ClaudePath = if ($env:CLAUDE_PATH) { $env:CLAUDE_PATH } else { "claude" }
$RalphDir = ".ralph"
$LogsDir = "$RalphDir/logs"

New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null

$logFile = "$LogsDir/plan_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

Write-Host "[ralph-plan] Starting read-only analysis..."
Write-Host "[ralph-plan] Log: $logFile"

$prompt = Get-Content PLAN_PROMPT.md -Raw
Start-Process -FilePath $ClaudePath -ArgumentList "-p", "`"$prompt`"", "--output-format", "text" `
    -RedirectStandardOutput $logFile -NoNewWindow -Wait

$logContent = if (Test-Path $logFile) { Get-Content $logFile -Raw } else { "" }

if ($logContent -match '<promise>PLAN_COMPLETE</promise>') {
    Write-Host "[ralph-plan] Analysis complete."
    if (Test-Path "fix_plan.md") {
        $count = (Select-String -Path "fix_plan.md" -Pattern '^\- \[ \]' | Measure-Object).Count
        Write-Host "[ralph-plan] Found $count unchecked issues in fix_plan.md"
        Write-Host "[ralph-plan] Run 'python tools/triage_fix_plan.py' to convert to build tasks."
    }
} else {
    Write-Host "[ralph-plan] Analysis did not complete. Check log: $logFile"
}
