# Ralph Loop — Build Mode Harness (PowerShell)
# Usage: .\ralph.ps1 [-MaxIterations 20] [-GateMode warn|block|off] [-Timeout 1800] [-Force] [-DryRun]

param(
    [int]$MaxIterations = 20,
    [ValidateSet("warn", "block", "off")]
    [string]$GateMode = "warn",
    [string]$GateCmd = "python tools/smart_gate.py",
    [int]$Timeout = 1800,
    [int]$MaxFiles = 20,
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# ── Configuration ─────────────────────────────────────────────
$ClaudePath = if ($env:CLAUDE_PATH) { $env:CLAUDE_PATH } else { "claude" }
$RalphDir = ".ralph"
$LogsDir = "$RalphDir/logs"
$LockFile = "$RalphDir/lock"
$GateFailure = "$RalphDir/gate_failure.md"
$LastGood = "$RalphDir/last_known_good"
$Metrics = "$RalphDir/metrics.jsonl"
$HumanNote = "$RalphDir/human_note.md"
$PauseFile = "$RalphDir/pause"
$ConsecFailThreshold = 3

New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null

# ── Cleanup function ─────────────────────────────────────────
function Cleanup {
    if (Test-Path $LockFile) {
        Remove-Item $LockFile -Force
        Write-Host "[ralph] Lock released."
    }
}

try {

# ── Startup checks ────────────────────────────────────────────
if (-not $Force) {
    # Lock file
    if (Test-Path $LockFile) {
        $oldPid = (Get-Content $LockFile -First 1).Trim()
        $proc = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "[ralph] ERROR: Another Ralph Loop is running (PID $oldPid)."
            Write-Host "[ralph] Use -Force to override."
            exit 1
        } else {
            Write-Host "[ralph] Removing stale lock (PID $oldPid no longer running)."
            Remove-Item $LockFile -Force
        }
    }

    # Dirty tree
    $dirty = git status --porcelain | Where-Object { $_ -notmatch '^\?\?' }
    if ($dirty) {
        Write-Host "[ralph] WARNING: Working tree has uncommitted changes."
        $dirty | ForEach-Object { Write-Host "  $_" }
        $reply = Read-Host "Continue anyway? [y/N]"
        if ($reply -notmatch '^[Yy]') { exit 1 }
    }

    # Branch safety
    $branch = git branch --show-current
    if ($branch -in @("main", "master")) {
        Write-Host "[ralph] WARNING: Running on '$branch'. Consider using a feature branch."
        $reply = Read-Host "Continue on $branch? [y/N]"
        if ($reply -notmatch '^[Yy]') { exit 1 }
    }
}

# Write lock
$pid = $PID
@($pid, (git branch --show-current), (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")) | Set-Content $LockFile

$branch = git branch --show-current
Write-Host "[ralph] Starting on branch: $branch"
Write-Host "[ralph] Max iterations: $MaxIterations"
Write-Host "[ralph] Gate mode: $GateMode"
Write-Host "[ralph] Timeout: ${Timeout}s"

if ($DryRun) {
    Write-Host "[ralph] DRY RUN — validating setup only."
    Write-Host "[ralph] Required files:"
    foreach ($f in @("PROMPT.md", "plan.md", "activity.md", "CLAUDE.md", "tools/prepare_context.py", "tools/smart_gate.py")) {
        $status = if (Test-Path $f) { "OK" } else { "MISSING" }
        Write-Host "  $status  $f"
    }
    Write-Host "[ralph] Dry run complete."
    exit 0
}

# ── State tracking ────────────────────────────────────────────
$consecFailures = 0
$lastGateOutput = ""
$runId = Get-Date -Format "yyyyMMdd_HHmmss"

# ── Main loop ─────────────────────────────────────────────────
for ($iteration = 1; $iteration -le $MaxIterations; $iteration++) {
    Write-Host ""
    Write-Host ("=" * 64)
    Write-Host "  ITERATION $iteration / $MaxIterations  (run: $runId)"
    Write-Host ("=" * 64)

    $iterStart = Get-Date
    $logFile = "$LogsDir/iteration_$($iteration.ToString('D3')).log"

    # ── Check pause file ──────────────────────────────────────
    if (Test-Path $PauseFile) {
        Write-Host "[ralph] Paused. Options: r)esume, s)tatus, q)uit"
        while ($true) {
            $choice = Read-Host "[ralph] >"
            switch ($choice) {
                "r" { Remove-Item $PauseFile -Force; Write-Host "[ralph] Resuming."; break }
                "s" { python tools/ralph_status.py 2>$null }
                "q" { Write-Host "[ralph] Quitting."; exit 0 }
                default { Write-Host "  r/s/q?" }
            }
            if ($choice -eq "r") { break }
        }
    }

    # ── Prepare context ───────────────────────────────────────
    Write-Host "[ralph] Preparing context..."
    python tools/prepare_context.py

    # ── Invoke agent ──────────────────────────────────────────
    Write-Host "[ralph] Invoking Claude..."
    $prompt = Get-Content PROMPT.md -Raw
    $proc = Start-Process -FilePath $ClaudePath -ArgumentList "-p", "`"$prompt`"", "--output-format", "text" `
        -RedirectStandardOutput $logFile -RedirectStandardError "$logFile.err" `
        -NoNewWindow -PassThru -Wait

    # Clear human note (single-use)
    if (Test-Path $HumanNote) { "" | Set-Content $HumanNote }

    $iterDuration = ((Get-Date) - $iterStart).TotalSeconds

    # ── Check signals ─────────────────────────────────────────
    $logContent = if (Test-Path $logFile) { Get-Content $logFile -Raw } else { "" }

    if ($logContent -match '<promise>COMPLETE</promise>') {
        Write-Host "[ralph] COMPLETE signal received. All tasks done!"
        $tag = "v0.$(git rev-list --count HEAD)"
        git tag -a $tag -m "Ralph Loop completed: $runId" 2>$null
        Write-Host "[ralph] Tagged as $tag"
        exit 0
    }

    if ($logContent -match '<promise>BLOCKED</promise>') {
        Write-Host "[ralph] BLOCKED signal received. Check activity.md."
        exit 1
    }

    if ($logContent -match '<promise>NEEDS_REVIEW</promise>') {
        Write-Host "[ralph] NEEDS_REVIEW signal. Pausing for human review."
        "" | Set-Content $PauseFile
    }

    # ── Count changed files ───────────────────────────────────
    $filesChanged = (git diff --name-only HEAD 2>$null | Measure-Object -Line).Lines

    if ($filesChanged -gt $MaxFiles) {
        Write-Host "[ralph] WARNING: $filesChanged files changed (threshold: $MaxFiles). Pausing."
        "" | Set-Content $PauseFile
    }

    # ── Run gate ──────────────────────────────────────────────
    $gateResult = "skip"
    if ($GateMode -ne "off") {
        Write-Host "[ralph] Running gate..."
        $gateOutput = Invoke-Expression $GateCmd 2>&1 | Out-String
        if ($LASTEXITCODE -eq 0) {
            $gateResult = "pass"
            Write-Host "[ralph] Gate PASSED."
            "" | Set-Content $GateFailure
            $consecFailures = 0
            git rev-parse HEAD | Set-Content $LastGood 2>$null
        } else {
            $gateResult = "fail"
            Write-Host "[ralph] Gate FAILED."
            $consecFailures++

            @("# Gate Failure (iteration $iteration)", "", '```', $gateOutput, '```') | Set-Content $GateFailure

            if ($gateOutput -eq $lastGateOutput -and $consecFailures -ge $ConsecFailThreshold) {
                Write-Host "[ralph] $consecFailures consecutive identical failures. Auto-BLOCKED."
                exit 2
            }
            $lastGateOutput = $gateOutput

            if ($GateMode -eq "block") {
                Write-Host "[ralph] Gate mode is 'block'. Halting."
                exit 2
            }
        }
    }

    # ── Record metrics ────────────────────────────────────────
    $logSize = if (Test-Path $logFile) { (Get-Item $logFile).Length } else { 0 }
    $inputEst = [math]::Floor($logSize / 4)
    $outputEst = [math]::Floor($logSize / 8)
    $ts = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
    $metric = "{`"iteration`":$iteration,`"run_id`":`"$runId`",`"duration_s`":$([math]::Floor($iterDuration)),`"gate_result`":`"$gateResult`",`"files_changed`":$filesChanged,`"input_tokens_est`":$inputEst,`"output_tokens_est`":$outputEst,`"timestamp`":`"$ts`"}"
    $metric | Add-Content $Metrics

    Write-Host "[ralph] Iteration $iteration complete. Duration: $([math]::Floor($iterDuration))s, Files: $filesChanged, Gate: $gateResult"

    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host "[ralph] Max iterations ($MaxIterations) reached."
python tools/ralph_status.py --oneline 2>$null

} finally {
    Cleanup
}
