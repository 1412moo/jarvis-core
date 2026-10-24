<#
.SYNOPSIS
  task-0194: keep the Jarvis Discord bot running outside any Claude session.

.DESCRIPTION
  One action per call:
    -Run         supervisor loop: one supervisor per logon session, no second bot, restart with backoff
    -Register    register the "at log on" scheduled task for the current user (no admin rights)
    -Unregister  remove that scheduled task
    -Start       start the registered task now
    -Stop        end the supervisor and the bot
    -Status      show the task, the supervisor and bot processes, the last heartbeat, warnings and the log
    -SelfTest    check the repository, the bot file, python and the log folder; starts nothing
    -SmokeTest   run the supervisor against a stand-in bot in a temporary folder (no Discord, no task)

  The repository is found from this script's own location. The bot reads its token from
  adapters/discord/.env itself; this script never reads or writes it. Logs go outside the
  repository, under %LOCALAPPDATA%\jarvis-core\logs: the supervisor's lines in discord-bot.log,
  the running bot's output in discord-bot.out.log and discord-bot.err.log, which are moved into
  discord-bot.log when the bot ends and before the next start.

  task-0196: the supervisor writes a heartbeat line every -HeartbeatSeconds (600 by default) and keeps
  its record in supervisor-<instance>.json next to the log; a normal end is recorded there, so -Status
  can tell a supervisor that was killed from one that stopped.

  -BotScript, -LogDir, -MaxLaunches, -InstanceName and -HeartbeatSeconds exist so the smoke check can
  run the loop against a stand-in bot; normal use leaves them at their defaults.
#>
param(
    [switch]$Run,
    [switch]$Register,
    [switch]$Unregister,
    [switch]$Start,
    [switch]$Stop,
    [switch]$Status,
    [switch]$SelfTest,
    [switch]$SmokeTest,
    [string]$BotScript = "",
    [string]$LogDir = "",
    [int]$MaxLaunches = 0,
    [string]$InstanceName = "JarvisDiscordBot",
    [int]$HeartbeatSeconds = 600
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not $BotScript) { $BotScript = Join-Path $RepoRoot "adapters\discord\bot_minimal.py" }
if (-not $LogDir) { $LogDir = Join-Path $env:LOCALAPPDATA "jarvis-core\logs" }
$LogFile = Join-Path $LogDir "discord-bot.log"
$OutFile = Join-Path $LogDir "discord-bot.out.log"
$ErrFile = Join-Path $LogDir "discord-bot.err.log"
$MaxLogBytes = 5MB
$FirstDelaySeconds = 10
$MaxDelaySeconds = 300
$StableRunSeconds = 600
$ExternalBotPollSeconds = 30
$DefaultInstanceName = "JarvisDiscordBot"
# task-0196: the supervisor's own record, so a supervisor that ended without a word can be told apart.
$StateFile = Join-Path $LogDir "supervisor-$InstanceName.json"

function Write-ServiceLog([string]$Text) {
    if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Force -Path $LogDir | Out-Null }
    if ((Test-Path $LogFile) -and ((Get-Item $LogFile).Length -gt $MaxLogBytes)) {
        Move-Item -Force -Path $LogFile -Destination "$LogFile.1"
    }
    $stamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss 'UTC'")
    Add-Content -Path $LogFile -Value "[$stamp] [service] $Text" -Encoding UTF8
}

function Get-RestartDelay([int]$Previous, [double]$RanSeconds) {
    # The first wait and the wait after a long healthy run are FirstDelaySeconds; otherwise double, capped.
    if ($Previous -le 0 -or $RanSeconds -ge $StableRunSeconds) { return $FirstDelaySeconds }
    return [Math]::Min($Previous * 2, $MaxDelaySeconds)
}

function Get-PythonPath {
    $found = @(Get-Command python -CommandType Application -ErrorAction SilentlyContinue)
    $real = @($found | Where-Object { $_.Source -notlike "*\WindowsApps\*" })
    if ($real.Count -gt 0) { return $real[0].Source }
    if ($found.Count -gt 0) { return $found[0].Source }
    return $null
}

function Get-BotProcesses {
    # Any python process running a bot_minimal.py bot; self-check runs are not bots.
    $leaf = Split-Path -Leaf $BotScript
    @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object {
        $_.CommandLine -and $_.CommandLine -like "*$leaf*" -and $_.CommandLine -notlike "*--self-check*"
    })
}

function Test-SameInstance([string]$CommandLine) {
    # task-0196: the default instance is the one started without -InstanceName; others match their exact name.
    $named = [regex]::Match($CommandLine, "-InstanceName\s+`"?([^\s`"]+)")
    if (-not $named.Success) { return $InstanceName -eq $DefaultInstanceName }
    return $named.Groups[1].Value -eq $InstanceName
}

function Get-SupervisorProcesses {
    $leaf = Split-Path -Leaf $PSCommandPath
    @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object {
        $_.ProcessId -ne $PID -and $_.CommandLine -and $_.CommandLine -like "*$leaf*" -and $_.CommandLine -like "*-Run*" `
            -and (Test-SameInstance $_.CommandLine)
    })
}

function Get-UtcStamp { return (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") }

function ConvertFrom-UtcStamp([string]$Stamp) {
    return [datetime]::ParseExact($Stamp, "yyyy-MM-ddTHH:mm:ssZ", [System.Globalization.CultureInfo]::InvariantCulture,
        [System.Globalization.DateTimeStyles]::AdjustToUniversal)
}

function Write-SupervisorState([hashtable]$State) {
    if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Force -Path $LogDir | Out-Null }
    ($State | ConvertTo-Json -Compress) | Set-Content -Path $StateFile -Encoding UTF8
}

function Read-SupervisorState {
    if (-not (Test-Path $StateFile)) { return $null }
    try { return (Get-Content -Raw -Path $StateFile -Encoding UTF8 | ConvertFrom-Json) } catch { return $null }
}

function Update-Alive([hashtable]$State) {
    # task-0196 repair 1: every state write by a live supervisor also marks it alive, so a bot that
    # ends quickly or a restart wait never leaves last_heartbeat behind.
    $State.last_heartbeat = Get-UtcStamp
    Write-SupervisorState $State
}

function Write-Heartbeat([hashtable]$State, [string]$BotPid) {
    $State.last_heartbeat = Get-UtcStamp
    $State.bot_pid = $BotPid
    Write-SupervisorState $State
    $up = [int]((Get-Date).ToUniversalTime() - (ConvertFrom-UtcStamp $State.started)).TotalSeconds
    Write-ServiceLog "heartbeat (supervisor pid $PID, bot pid $BotPid, up $up s)"
}

function Save-PreviousOutput {
    foreach ($file in @($OutFile, $ErrFile)) {
        if ((Test-Path $file) -and ((Get-Item $file).Length -gt 0)) {
            Get-Content -Path $file -Encoding UTF8 | Add-Content -Path $LogFile -Encoding UTF8
            Clear-Content -Path $file
        }
    }
}

function Invoke-Supervisor {
    $mutex = New-Object System.Threading.Mutex($false, "Local\$InstanceName-supervisor")
    try {
        $owned = $mutex.WaitOne(0)
    }
    catch [System.Threading.AbandonedMutexException] {
        # The previous supervisor was killed while holding it; the mutex is ours now.
        $owned = $true
    }
    if (-not $owned) {
        Write-ServiceLog "another supervisor is running; this one ends"
        return 0
    }
    try {
        $python = Get-PythonPath
        if (-not $python) { Write-ServiceLog "python not found; supervisor ends"; return 1 }
        if (-not (Test-Path $BotScript)) { Write-ServiceLog "bot script not found: $BotScript"; return 1 }
        $env:PYTHONIOENCODING = "utf-8"
        $state = @{ pid = $PID; started = (Get-UtcStamp); last_heartbeat = (Get-UtcStamp); bot_pid = ""; launches = 0;
                    heartbeat_seconds = $HeartbeatSeconds; ended = $false; ended_at = "" }
        Update-Alive $state
        Write-ServiceLog "supervisor started (pid $PID, repo $RepoRoot, heartbeat every $HeartbeatSeconds s)"
        $delay = 0
        $launches = 0
        $lastBeat = Get-Date
        $announced = ""
        while ($true) {
            # @() keeps a one-item result a list: a single CimInstance has no usable Count in PowerShell 5.1.
            $others = @(Get-BotProcesses)
            if ($others.Count -gt 0) {
                $otherPids = ($others | ForEach-Object { $_.ProcessId }) -join ","
                if ($otherPids -ne $announced) {
                    Write-ServiceLog "a bot is already running (pid $otherPids); not starting another"
                    $announced = $otherPids
                    $state.bot_pid = "external:$otherPids"
                    Update-Alive $state
                }
                if ($MaxLaunches -gt 0) { return 0 }
                Start-Sleep -Seconds ([Math]::Min($ExternalBotPollSeconds, $HeartbeatSeconds))
                if (((Get-Date) - $lastBeat).TotalSeconds -ge $HeartbeatSeconds) { Write-Heartbeat $state "external:$otherPids"; $lastBeat = Get-Date }
                continue
            }
            $announced = ""
            Save-PreviousOutput
            $started = Get-Date
            $bot = Start-Process -FilePath $python -ArgumentList @("-B", "-u", "`"$BotScript`"") -WorkingDirectory $RepoRoot `
                -RedirectStandardOutput $OutFile -RedirectStandardError $ErrFile -WindowStyle Hidden -PassThru
            # Reading Handle now keeps it open, so ExitCode is still readable after the process ends.
            $null = $bot.Handle
            $launches += 1
            $state.launches = $launches
            $state.bot_pid = [string]$bot.Id
            Update-Alive $state
            $lastBeat = Get-Date
            Write-ServiceLog "bot started (pid $($bot.Id), launch $launches)"
            # task-0196: wait in heartbeat-sized steps so the log shows the supervisor is alive.
            while (-not $bot.WaitForExit($HeartbeatSeconds * 1000)) { Write-Heartbeat $state ([string]$bot.Id); $lastBeat = Get-Date }
            $ran = ((Get-Date) - $started).TotalSeconds
            Save-PreviousOutput
            Write-ServiceLog ("bot ended (exit " + $bot.ExitCode + ", ran " + [int]$ran + "s)")
            $state.bot_pid = ""
            Update-Alive $state
            if ($MaxLaunches -gt 0 -and $launches -ge $MaxLaunches) { return 0 }
            $delay = Get-RestartDelay $delay $ran
            Write-ServiceLog "restarting in $delay s"
            # task-0196 repair 1: a long restart wait keeps writing heartbeats too.
            $until = (Get-Date).AddSeconds($delay)
            while ((Get-Date) -lt $until) {
                Start-Sleep -Seconds ([Math]::Max(1, [Math]::Min($HeartbeatSeconds, [int][Math]::Ceiling(($until - (Get-Date)).TotalSeconds))))
                if (((Get-Date) - $lastBeat).TotalSeconds -ge $HeartbeatSeconds) { Write-Heartbeat $state "none (restarting)"; $lastBeat = Get-Date }
            }
        }
    }
    finally {
        # task-0196: a normal end is recorded; a killed supervisor never reaches this, which -Status reports.
        if ($state) {
            $state.ended = $true
            $state.ended_at = Get-UtcStamp
            Write-SupervisorState $state
            Write-ServiceLog "supervisor ended (pid $PID)"
        }
        $mutex.ReleaseMutex()
        $mutex.Dispose()
    }
}

function Get-UserId { return "$env:USERDOMAIN\$env:USERNAME" }

if ($Run) { exit (Invoke-Supervisor) }

if ($Register) {
    $argument = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Run"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument -WorkingDirectory $RepoRoot
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User (Get-UserId)
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
        -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    $principal = New-ScheduledTaskPrincipal -UserId (Get-UserId) -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $InstanceName -Action $action -Trigger $trigger -Settings $settings -Principal $principal `
        -Description "Jarvis Discord bot supervisor (task-0194)" -Force | Out-Null
    Write-Output "registered: $InstanceName (at log on, $(Get-UserId))"
    exit 0
}

if ($Unregister) {
    if (Get-ScheduledTask -TaskName $InstanceName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $InstanceName -Confirm:$false
        Write-Output "unregistered: $InstanceName"
    } else {
        Write-Output "not registered: $InstanceName"
    }
    exit 0
}

if ($Start) {
    Start-ScheduledTask -TaskName $InstanceName
    Write-Output "started: $InstanceName"
    exit 0
}

if ($Stop) {
    # The supervisor first, so it cannot restart the bot it is about to lose.
    foreach ($p in (Get-SupervisorProcesses)) {
        Stop-Process -Id $p.ProcessId -Force
        Write-Output "stopped supervisor $($p.ProcessId)"
        # task-0196: a supervisor ended by -Stop cannot record its own end, so -Stop records it.
        $state = Read-SupervisorState
        if ($state -and [string]$state.pid -eq [string]$p.ProcessId -and -not $state.ended) {
            $record = @{}
            $state.PSObject.Properties | ForEach-Object { $record[$_.Name] = $_.Value }
            $record.ended = $true
            $record.ended_at = Get-UtcStamp
            $record.ended_by = "-Stop"
            Write-SupervisorState $record
            Write-ServiceLog "supervisor stopped by -Stop (pid $($p.ProcessId))"
        }
    }
    foreach ($p in (Get-BotProcesses)) { Stop-Process -Id $p.ProcessId -Force; Write-Output "stopped bot $($p.ProcessId)" }
    exit 0
}

if ($Status) {
    $task = Get-ScheduledTask -TaskName $InstanceName -ErrorAction SilentlyContinue
    $taskState = if ($task) { [string]$task.State } else { "not registered" }
    Write-Output "task: $InstanceName = $taskState"
    $supervisors = @(Get-SupervisorProcesses)
    $bots = @(Get-BotProcesses)
    Write-Output ("supervisor pids: " + (($supervisors | ForEach-Object { $_.ProcessId }) -join ","))
    Write-Output ("bot pids: " + (($bots | ForEach-Object { $_.ProcessId }) -join ","))
    $state = Read-SupervisorState
    if ($state) {
        $age = [int]((Get-Date).ToUniversalTime() - (ConvertFrom-UtcStamp $state.last_heartbeat)).TotalSeconds
        Write-Output "last heartbeat: $($state.last_heartbeat) ($age s ago, supervisor pid $($state.pid), ended $($state.ended))"
        $alive = [bool](Get-Process -Id ([int]$state.pid) -ErrorAction SilentlyContinue)
        if (-not $alive -and -not $state.ended) {
            Write-Output "WARNING: the last supervisor (pid $($state.pid)) ended without recording it; it was last seen at $($state.last_heartbeat)"
        }
        # task-0196 repair 2: an ended supervisor's pid may belong to another process now; no stale warning then.
        if ($alive -and -not $state.ended -and $age -gt (2 * [int]$state.heartbeat_seconds)) {
            Write-Output "WARNING: the supervisor (pid $($state.pid)) has not written a heartbeat for $age s"
        }
    } else {
        Write-Output "last heartbeat: none recorded ($StateFile)"
    }
    if ($bots.Count -gt 0 -and $supervisors.Count -eq 0) {
        Write-Output "WARNING: a bot is running without a supervisor; if it stops, nothing starts it again"
    }
    Write-Output "log: $LogFile"
    exit 0
}

if ($SelfTest) {
    $python = Get-PythonPath
    $delays = @()
    $d = 0
    foreach ($ran in @(1, 1, 1, 1, 1, 1, 1, 700, 1)) { $d = Get-RestartDelay $d $ran; $delays += $d }
    $checks = [ordered]@{
        repo_root           = $RepoRoot
        bot_script_found    = (Test-Path $BotScript)
        python              = $python
        log_dir             = $LogDir
        log_dir_outside_repo = -not ([System.IO.Path]::GetFullPath($LogDir).StartsWith([System.IO.Path]::GetFullPath($RepoRoot), [StringComparison]::OrdinalIgnoreCase))
        restart_delays      = ($delays -join ",")
    }
    $checks.GetEnumerator() | ForEach-Object { Write-Output "$($_.Key): $($_.Value)" }
    $ok = $checks.bot_script_found -and $python -and $checks.log_dir_outside_repo
    Write-Output ("selftest: " + $(if ($ok) { "PASS" } else { "FAIL" }))
    exit $(if ($ok) { 0 } else { 1 })
}

if ($SmokeTest) {
    # Runs the supervisor against a stand-in bot in a temporary folder: no Discord, no scheduled task.
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("jarvis-bot-service-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $tmp | Out-Null
    $results = [ordered]@{}
    $self = $PSCommandPath
    $ps = (Get-Process -Id $PID).Path
    try {
        $quick = Join-Path $tmp "standin_quick_bot.py"
        Set-Content -Path $quick -Encoding ASCII -Value "import os, sys`nprint('standin bot ran in ' + os.getcwd())`nsys.exit(3)"
        $slow = Join-Path $tmp "standin_slow_bot.py"
        Set-Content -Path $slow -Encoding ASCII -Value "import time`nprint('standin slow bot')`ntime.sleep(20)"
        $logs = Join-Path $tmp "logs"
        $name = "JarvisBotServiceSmoke" + [guid]::NewGuid().ToString("N").Substring(0, 8)

        # 1. One launch: the bot runs from the repository root, its output and exit reach the log.
        & $ps -NoProfile -ExecutionPolicy Bypass -File $self -Run -BotScript $quick -LogDir $logs -MaxLaunches 1 -InstanceName $name
        $log = Get-Content -Raw -Path (Join-Path $logs "discord-bot.log")
        $results["launch_logged"] = ($log -match "bot started \(pid \d+, launch 1\)") -and ($log -match "bot ended \(exit 3, ran \d+s\)")
        $results["runs_from_repo_root"] = $log.Contains("standin bot ran in " + $RepoRoot)

        # 2. A second supervisor with the same name ends at once while the first one holds the mutex.
        $logs2 = Join-Path $tmp "logs2"
        $log2 = Join-Path $logs2 "discord-bot.log"
        $first = Start-Process -FilePath $ps -PassThru -WindowStyle Hidden -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$self`"", "-Run", "-BotScript", "`"$slow`"", "-LogDir", "`"$logs2`"", "-MaxLaunches", "1", "-InstanceName", $name)
        $deadline = (Get-Date).AddSeconds(15)
        while ((Get-Date) -lt $deadline -and -not ((Test-Path $log2) -and ((Get-Content -Raw -Path $log2) -match "bot started"))) {
            Start-Sleep -Milliseconds 300
        }
        & $ps -NoProfile -ExecutionPolicy Bypass -File $self -Run -BotScript $slow -LogDir $logs2 -MaxLaunches 1 -InstanceName $name
        $results["second_supervisor_ends"] = (Get-Content -Raw -Path $log2) -match "another supervisor is running; this one ends"

        # 3. With that bot still running, a supervisor under another name does not start a second bot.
        $logs3 = Join-Path $tmp "logs3"
        & $ps -NoProfile -ExecutionPolicy Bypass -File $self -Run -BotScript $slow -LogDir $logs3 -MaxLaunches 1 -InstanceName ($name + "b")
        $log3 = Get-Content -Raw -Path (Join-Path $logs3 "discord-bot.log")
        $results["no_second_bot"] = ($log3 -match "a bot is already running \(pid \d+") -and ($log3 -notmatch "bot started")
        $first.WaitForExit(40000) | Out-Null

        # 3b. A bot that ends is started again after the first wait (10 s), and its output stays in the log.
        $logs4 = Join-Path $tmp "logs4"
        & $ps -NoProfile -ExecutionPolicy Bypass -File $self -Run -BotScript $quick -LogDir $logs4 -MaxLaunches 2 -InstanceName ($name + "c")
        $log4 = Get-Content -Raw -Path (Join-Path $logs4 "discord-bot.log")
        $results["restarts_after_exit"] = ($log4 -match "restarting in 10 s") -and ($log4 -match "bot started \(pid \d+, launch 2\)") `
            -and ([regex]::Matches($log4, "standin bot ran in ").Count -eq 2)

        # 3c. A supervisor killed while holding the mutex leaves it abandoned; the next one takes it over.
        $logs5 = Join-Path $tmp "logs5"
        $log5 = Join-Path $logs5 "discord-bot.log"
        $victim = Start-Process -FilePath $ps -PassThru -WindowStyle Hidden -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$self`"", "-Run", "-BotScript", "`"$slow`"", "-LogDir", "`"$logs5`"", "-MaxLaunches", "1", "-InstanceName", ($name + "d"))
        $deadline = (Get-Date).AddSeconds(15)
        while ((Get-Date) -lt $deadline -and -not ((Test-Path $log5) -and ((Get-Content -Raw -Path $log5) -match "bot started"))) {
            Start-Sleep -Milliseconds 300
        }
        Stop-Process -Id $victim.Id -Force
        & $ps -NoProfile -ExecutionPolicy Bypass -File $self -Run -BotScript $slow -LogDir $logs5 -MaxLaunches 1 -InstanceName ($name + "d")
        $text5 = Get-Content -Raw -Path $log5
        $results["abandoned_mutex_taken_over"] = ([regex]::Matches($text5, "supervisor started").Count -eq 2) -and ($text5 -notmatch "another supervisor is running")
        foreach ($p in @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like "*$slow*" })) {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        }

        # 3c2. A bot that ends at once still refreshes the record, and the restart wait writes heartbeats.
        $logs9 = Join-Path $tmp "logs9"
        & $ps -NoProfile -ExecutionPolicy Bypass -File $self -Run -BotScript $quick -LogDir $logs9 -MaxLaunches 2 -InstanceName ($name + "h") -HeartbeatSeconds 3
        $log9 = Get-Content -Raw -Path (Join-Path $logs9 "discord-bot.log")
        $state9 = Get-Content -Raw -Path (Join-Path $logs9 "supervisor-$($name)h.json") | ConvertFrom-Json
        # Both stamps are whole seconds; the 10 s restart wait lies between the start and the last mark.
        $beat9 = (ConvertFrom-UtcStamp ([string]$state9.last_heartbeat)) - (ConvertFrom-UtcStamp ([string]$state9.started))
        $results["short_bot_keeps_heartbeat"] = ([regex]::Matches($log9, "heartbeat \(supervisor pid \d+, bot pid none \(restarting\)").Count -ge 2) `
            -and ($state9.launches -eq 2) -and ($beat9.TotalSeconds -ge 10)

        # 3d. Heartbeats while the bot runs, the state file, and a recorded normal end.
        $mid = Join-Path $tmp "standin_mid_bot.py"
        Set-Content -Path $mid -Encoding ASCII -Value "import time`nprint('standin mid bot')`ntime.sleep(4)"
        $logs6 = Join-Path $tmp "logs6"
        & $ps -NoProfile -ExecutionPolicy Bypass -File $self -Run -BotScript $mid -LogDir $logs6 -MaxLaunches 1 -InstanceName ($name + "e") -HeartbeatSeconds 1
        $log6 = Get-Content -Raw -Path (Join-Path $logs6 "discord-bot.log")
        $state6 = Get-Content -Raw -Path (Join-Path $logs6 "supervisor-$($name)e.json") | ConvertFrom-Json
        $results["heartbeat_and_normal_end"] = ([regex]::Matches($log6, "heartbeat \(supervisor pid \d+, bot pid \d+, up \d+ s\)").Count -ge 2) `
            -and ($log6 -match "supervisor ended") -and ($state6.ended -eq $true) -and ($state6.launches -eq 1)

        # 3e. A supervisor killed while its bot runs: -Status warns twice (no supervisor, ended without a record).
        $logs7 = Join-Path $tmp "logs7"
        $log7 = Join-Path $logs7 "discord-bot.log"
        $killed = Start-Process -FilePath $ps -PassThru -WindowStyle Hidden -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$self`"", "-Run", "-BotScript", "`"$slow`"", "-LogDir", "`"$logs7`"", "-MaxLaunches", "1", "-InstanceName", ($name + "f"))
        $deadline = (Get-Date).AddSeconds(15)
        while ((Get-Date) -lt $deadline -and -not ((Test-Path $log7) -and ((Get-Content -Raw -Path $log7) -match "bot started"))) {
            Start-Sleep -Milliseconds 300
        }
        Stop-Process -Id $killed.Id -Force
        Start-Sleep -Seconds 1
        $status7 = (& $ps -NoProfile -ExecutionPolicy Bypass -File $self -Status -BotScript $slow -LogDir $logs7 -InstanceName ($name + "f")) -join "`n"
        $results["status_warns_after_kill"] = ($status7 -match "WARNING: a bot is running without a supervisor") `
            -and ($status7 -match "WARNING: the last supervisor \(pid $($killed.Id)\) ended without recording it")
        foreach ($p in @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like "*$slow*" })) {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        }

        # 3f. -Stop records the end of the supervisor it stops, so -Status does not report it as lost.
        $logs8 = Join-Path $tmp "logs8"
        $log8 = Join-Path $logs8 "discord-bot.log"
        $stopped = Start-Process -FilePath $ps -PassThru -WindowStyle Hidden -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$self`"", "-Run", "-BotScript", "`"$slow`"", "-LogDir", "`"$logs8`"", "-MaxLaunches", "1", "-InstanceName", ($name + "g"))
        $deadline = (Get-Date).AddSeconds(15)
        while ((Get-Date) -lt $deadline -and -not ((Test-Path $log8) -and ((Get-Content -Raw -Path $log8) -match "bot started"))) {
            Start-Sleep -Milliseconds 300
        }
        $stopOut = (& $ps -NoProfile -ExecutionPolicy Bypass -File $self -Stop -BotScript $slow -LogDir $logs8 -InstanceName ($name + "g")) -join "`n"
        Start-Sleep -Seconds 1
        $status8 = (& $ps -NoProfile -ExecutionPolicy Bypass -File $self -Status -BotScript $slow -LogDir $logs8 -InstanceName ($name + "g")) -join "`n"
        $state8 = Get-Content -Raw -Path (Join-Path $logs8 "supervisor-$($name)g.json") | ConvertFrom-Json
        $results["stop_records_the_end"] = ($stopOut -match "stopped supervisor $($stopped.Id)") -and ($stopOut -match "stopped bot") `
            -and ($state8.ended -eq $true) -and ($state8.ended_by -eq "-Stop") -and ($status8 -notmatch "WARNING") `
            -and ((Get-Content -Raw -Path $log8) -match "supervisor stopped by -Stop")

        # 3g. An ended record whose pid is alive again (reused) and whose heartbeat is old gives no warning;
        #     the same record without the end mark does warn.
        $logs10 = Join-Path $tmp "logs10"
        New-Item -ItemType Directory -Path $logs10 | Out-Null
        $file10 = Join-Path $logs10 "supervisor-$($name)i.json"
        $old = (Get-Date).ToUniversalTime().AddHours(-3).ToString("yyyy-MM-ddTHH:mm:ssZ")
        $record10 = @{ pid = $PID; started = $old; last_heartbeat = $old; bot_pid = ""; launches = 1; heartbeat_seconds = 600; ended = $true; ended_at = $old }
        ($record10 | ConvertTo-Json -Compress) | Set-Content -Path $file10 -Encoding UTF8
        $status10 = (& $ps -NoProfile -ExecutionPolicy Bypass -File $self -Status -BotScript $quick -LogDir $logs10 -InstanceName ($name + "i")) -join "`n"
        $record10.ended = $false
        ($record10 | ConvertTo-Json -Compress) | Set-Content -Path $file10 -Encoding UTF8
        $status10b = (& $ps -NoProfile -ExecutionPolicy Bypass -File $self -Status -BotScript $quick -LogDir $logs10 -InstanceName ($name + "i")) -join "`n"
        $results["no_stale_warning_after_end"] = ($status10 -notmatch "WARNING") -and ($status10b -match "has not written a heartbeat")

        # 4. The restart wait doubles from 10 s up to 300 s and starts over after a long run.
        $d = 0; $seen = @()
        foreach ($ran in @(1, 1, 1, 1, 1, 1, 1, 700, 1)) { $d = Get-RestartDelay $d $ran; $seen += $d }
        $results["restart_delays"] = ($seen -join ",") -eq "10,20,40,80,160,300,300,10,20"

        # 5. The log rotates once it passes the size limit.
        $big = Join-Path $logs "discord-bot.log"
        $fs = [System.IO.File]::Open($big, "Append"); $fs.SetLength($MaxLogBytes + 1); $fs.Close()
        $script:LogDir = $logs; $script:LogFile = $big
        Write-ServiceLog "rotation check"
        $results["log_rotates"] = (Test-Path "$big.1") -and ((Get-Item $big).Length -lt 1KB)

        # 6. The script holds no machine-specific path and never touches the token.
        $text = Get-Content -Raw -Path $self
        $results["no_fixed_paths_or_token"] = ($text -notmatch "(?i)[a-z]:\\\\?(project|work|game|users)") -and ($text -notmatch ("DISCORD_BOT_" + "TOKEN")) -and ($text -notmatch "(?i)\.env['`"]")
    }
    finally {
        Remove-Item -Recurse -Force -Path $tmp -ErrorAction SilentlyContinue
    }
    $results.GetEnumerator() | ForEach-Object { Write-Output "$($_.Key): $($_.Value)" }
    $ok = -not ($results.Values -contains $false)
    Write-Output ("smoketest: " + $(if ($ok) { "PASS" } else { "FAIL" }))
    exit $(if ($ok) { 0 } else { 1 })
}

Write-Output "usage: discord_bot_service.ps1 -Run | -Register | -Unregister | -Start | -Stop | -Status | -SelfTest | -SmokeTest"
exit 2
