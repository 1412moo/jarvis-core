# task-0196-supervisor-heartbeat

- id: `task-0196-supervisor-heartbeat`
- title: `봇 감시자 heartbeat`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-24 15:37 UTC`
- updated_at: `2026-10-24 15:52 UTC`
- summary: `봇 감시자(scripts/discord_bot_service.ps1 -Run)가 언제 끝났는지 알 수 있게 한다. 감시자가 주기적으로 heartbeat 줄을 로그에 남기고 상태 파일(pid, 시작, 마지막 heartbeat, 봇 pid, 정상 종료 여부)을 갱신하며, 정상 종료 때 그 사실을 남긴다. -Status는 마지막 heartbeat 시각과, 감시자 없이 봇만 도는 경우, 감시자가 기록 없이 끝난 경우, heartbeat가 오래된 경우를 경고한다. 감시자 찾기는 같은 인스턴스 이름의 감시자로 좁힌다.`
- source_command: `Owner 지시: 감시자 heartbeat 보강 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `bc40e1b3a92e5a0e22f80f62bc93dd7fdaaa1e53` (등록 시점 main HEAD, task-0195까지 push 완료) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=1` (SOP §5 기본값, 사용 내역은 Repair 절) |

## Owner 결정 (원문)

```text
[Manager 보고: 봇 재시작 중 발견한 현상]
- `-Stop`은 봇만 끝냈다고 출력했고, 감시자를 끝냈다는 줄은 없었습니다. 확인해 보니 오후에 띄운 이전 감시자(pid 16392)는 그 전에 이미 없었습니다.
- 봇(pid 36080)은 감시자 없이 혼자 계속 돌고 있었습니다. 감시 로그에 "bot ended" 줄이 없어, 봇이 아니라 감시자만 먼저 끝난 것으로 보입니다.
- 언제, 왜 끝났는지는 확인하지 못했습니다. 작업 스케줄러의 운영 로그는 이 PC에서 꺼져 있고, 감시자는 강제로 끝나면 로그를 남기지 못합니다.
- 영향: 그동안 봇은 정상으로 돌았습니다. 다만 그 사이 봇이 죽었다면 아무도 다시 띄우지 않았을 것입니다.

제안 (작은 후속 task)
- 감시자가 주기적으로 살아 있다는 줄(heartbeat)을 로그에 남기게 합니다. 그러면 언제 끝났는지 알 수 있습니다.
- `-Status`에 "봇은 있는데 감시자는 없음" 같은 경고를 띄웁니다.
- 원하시면 이 원인 확인과 보강을 task로 진행하겠습니다.

[Owner 답]
감시자 heartbeat 보강 task로 진행해
```

## 원인 조사 (등록 전, 읽기만)

- 감시 로그(`%LOCALAPPDATA%\jarvis-core\logs\discord-bot.log`)에는 `2026-10-24 11:42:29 UTC`의 "supervisor started (pid 16392)", "bot started (pid 36080)" 다음 줄이 `14:57:24 UTC`의 새 감시자 시작이다. 그 사이 감시자의 줄은 없다.
- 작업 스케줄러 정보: 실행 시간 제한 없음(PT0S), 배터리로 멈추지 않음, 새 인스턴스는 무시(IgnoreNew). `14:57` 시작 때 작업이 이미 끝난 상태였기에 새 감시자가 떴다. Task Scheduler 운영 로그는 이 PC에서 이벤트가 없다(꺼져 있음).
- 저장소에서 프로세스를 끝내는 코드는 `-Stop`, `-SmokeTest`의 대역 봇·대역 감시자 정리, Worker 시간 초과 때 자기 자식 프로세스 정리뿐이다. 등록(`11:42`) 이후 `-Stop`은 `14:57` 재시작 때 처음 실행됐고 `-SmokeTest`는 실행하지 않았다. 원인은 확인하지 못했다.
- 봇은 감시자와 별개 프로세스라 감시자가 끝나도 계속 돌았다.

## 설계

1. `scripts/discord_bot_service.ps1`의 감시 루프:
   - 봇을 기다리는 동안 `-HeartbeatSeconds`(기본 600초)마다 "heartbeat" 줄(감시자 pid, 봇 pid, 감시자 가동 시간)을 로그에 남긴다. 다른 봇이 이미 떠 있어 기다릴 때도 같은 간격으로 남긴다. 그때의 "a bot is already running" 안내 줄은 그 봇이 바뀔 때만 쓴다(예전에는 30초마다 같은 줄을 썼다). 살아 있다는 표시는 heartbeat가 맡는다.
   - 상태 파일 `<로그 폴더>\supervisor-<인스턴스 이름>.json`에 pid, 시작 시각, 마지막 heartbeat 시각, 봇 pid, 실행 횟수, 정상 종료 여부를 쓴다. 시작, 봇 실행, heartbeat, 종료 때 갱신한다.
   - 정상으로 끝날 때(루프가 끝나거나 오류로 빠져나올 때) "supervisor ended" 줄과 정상 종료 표시를 남긴다. 강제로 끝나면 남지 않으므로, 그 경우는 마지막 heartbeat로 끝난 시각의 범위를 안다. `-Stop`은 감시자를 강제로 끝내므로, `-Stop`이 끝낸 감시자가 상태 파일의 감시자면 `-Stop`이 대신 종료 표시(`ended_by: -Stop`)와 "supervisor stopped by -Stop" 줄을 남긴다(self-review 반영).
2. `-Status`: 상태 파일의 마지막 heartbeat 시각과 경과 시간을 보이고 경고를 붙인다.
   - 봇은 있는데 감시자가 없음: 봇이 끝나도 다시 띄우지 않는다는 경고.
   - 상태 파일의 감시자 pid가 살아 있지 않은데 정상 종료 표시가 없음: 기록 없이 끝났다는 경고와 마지막 heartbeat 시각.
   - 감시자는 살아 있는데 마지막 heartbeat가 간격의 두 배(기본 1200초)를 넘게 지남: 멈춘 것 같다는 경고.
3. 감시자 찾기(`-Status`, `-Stop`)를 같은 인스턴스 이름의 감시자로 좁힌다(기본 이름은 `-InstanceName`을 주지 않은 감시자). 그래야 smoke의 대역 감시자와 실제 감시자가 섞이지 않는다.
4. `-SmokeTest`: heartbeat 줄과 상태 파일, 정상 종료 표시, 감시자를 강제로 끝낸 뒤의 `-Status` 경고(감시자 없음, 기록 없이 끝남)를 확인하는 시나리오를 더한다.
5. README의 상시 실행 절에 heartbeat, 상태 파일, 경고를 적는다.
6. 작업 스케줄러 등록 설정과 봇 코드는 바꾸지 않는다. 적용은 완료 뒤 Owner 지시로 감시자를 다시 시작할 때다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `scripts/discord_bot_service.ps1`, `adapters/discord/README.md`(상시 실행 절), `memory/tasks/task-0196-supervisor-heartbeat.md` |
| deny | `jarvis.bat`, `adapters/discord/.env`, 봇과 다른 코드, `apps/`, AGENTS·agent 정의, validator, 다른 task 기록, 외부 API·credential, 보호 worktree, 이 task 안에서의 작업 스케줄러 재등록·감시자 재시작 |

## 계획

1. 스크립트 변경.
2. 검사: 구문 오류 0, ASCII만, `-SelfTest`, `-SmokeTest`(새 시나리오 포함), 실제 감시자가 도는 지금 `-Status`가 경고 없이 heartbeat 시각을 보이는지(새 감시자는 재시작 뒤에야 상태 파일을 씀을 기록), 실제 감시자·봇이 smoke로 영향을 받지 않는지.
3. 사전 점검 → self-review → candidate → Reviewer → QA → Evidence·Complete(Manager, G3와 같게) → checkpoint. push와 감시자 재시작은 별도 지시.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-24 15:37 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다.

## 구현

- `scripts/discord_bot_service.ps1`(ASCII만):
  - 인자 `-HeartbeatSeconds`(기본 600)와 상태 파일 `supervisor-<인스턴스>.json`(로그 폴더). 함수 `Test-SameInstance`, `Get-UtcStamp`, `ConvertFrom-UtcStamp`, `Write-SupervisorState`, `Read-SupervisorState`, `Write-Heartbeat`를 더했다.
  - 감시 루프: 시작 때 상태 파일을 쓰고 시작 줄에 heartbeat 간격을 적는다. 봇은 `WaitForExit(간격)`으로 나눠 기다리며 간격마다 heartbeat 줄과 상태 파일을 갱신한다. 다른 봇이 떠 있어 기다리는 동안에는 그 봇이 바뀔 때만 안내 줄을 쓰고(예전에는 30초마다 같은 줄을 썼다), 간격마다 heartbeat를 쓴다. 봇을 띄울 때 상태 파일에 봇 pid와 실행 횟수를 쓴다. `finally`에서 정상 종료 표시와 "supervisor ended" 줄을 남긴다.
  - `-Status`: 마지막 heartbeat 시각과 경과 초, 감시자 pid, 종료 여부를 보이고, 설계 2의 세 가지 경고를 `WARNING` 줄로 띄운다.
  - `Get-SupervisorProcesses`: 명령줄의 `-InstanceName` 값으로 같은 인스턴스만 고른다(값이 없으면 기본 인스턴스). `-Stop`과 `-Status`가 이것을 쓴다.
  - `-Stop`: 끝낸 감시자가 상태 파일의 감시자이고 종료 표시가 없으면 종료 표시(`ended_by: -Stop`)와 로그 줄을 대신 남긴다.
  - `-SmokeTest`: 시나리오 세 개를 더했다. `stop_records_the_end`(감시자를 `-Stop`으로 끝낸 뒤 상태 파일의 종료 표시와 `ended_by`, 로그 줄, `-Status`에 경고 없음)와, `heartbeat_and_normal_end`(heartbeat 1초, 4초 도는 대역 봇으로 heartbeat 줄 2개 이상, "supervisor ended", 상태 파일의 종료 표시와 실행 횟수 1), `status_warns_after_kill`(대역 봇을 띄운 감시자를 강제로 끝낸 뒤 `-Status`가 두 경고를 띄움). 머리말 도움말에 heartbeat와 상태 파일을 적었다.
- `adapters/discord/README.md`: 상시 실행 절에 heartbeat 항목과 smoke 설명.

## Implementer 검증 (작업 트리)

- 구문 분석 오류 0, ASCII 밖 바이트 0.
- `-SelfTest`: PASS.
- `-SmokeTest`: PASS 12/12(새 세 시나리오 포함), 약 46초.
- 실제 `-Status`: 작업 Running, 감시자 35140(바뀐 인스턴스 판정으로도 찾음), 봇 34260, "last heartbeat: none recorded". 지금 감시자는 바뀌기 전 코드라 상태 파일이 없다. 경고 없음. smoke 뒤에도 실제 감시자와 봇은 그대로였다.
- 남은 한계: 강제로 끝난 감시자의 끝난 시각은 마지막 heartbeat 뒤 최대 10분 범위로만 알 수 있다. `-Status`의 생존 판정은 상태 파일의 pid가 살아 있는지로 하므로, 그 pid를 다른 프로세스가 다시 쓰면 경고를 놓칠 수 있다. 원인 조사 절의 이전 감시자 종료 원인은 여전히 모른다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "- 감시자가 주기적으로 살아 있다는 줄(heartbeat)을 로그에 남기게 합니다. 그러면 언제 끝났는지 알 수 있습니다." / "[Owner 답]" / "감시자 heartbeat 보강 task로 진행해" | 10분마다 heartbeat 줄과 상태 파일을 남기고 정상 종료를 기록한다. repair 1부터 봇 실행·종료·재시작 대기 중에도 살아 있다는 표시를 갱신해, 봇이 금방 끝나 재시작을 되풀이해도 heartbeat가 끊기지 않는다. 강제로 끝나면 마지막 heartbeat로 끝난 시각의 범위(한 간격, 기본 10분)를 안다 |
| A2 | Owner 결정 (원문) | "- `-Status`에 \"봇은 있는데 감시자는 없음\" 같은 경고를 띄웁니다." | 그 경고와 함께, 기록 없이 끝난 감시자와 heartbeat가 오래된 감시자 경고도 띄운다. smoke로 앞의 두 경고를 확인했다 |
| A3 | Owner 결정 (원문) | "- 원하시면 이 원인 확인과 보강을 task로 진행하겠습니다." | 원인 확인: 로그, 작업 스케줄러 정보, 저장소의 프로세스 종료 코드를 봤지만 원인을 찾지 못했다(원인 조사 절). 보강은 위와 같다 |
| A4 | Owner 결정 (원문) | "- `-Status`에 "봇은 있는데 감시자는 없음" 같은 경고를 띄웁니다." | 설계 3(감시자 찾기를 같은 인스턴스로 좁힘)은 이 경고를 위한 수단이다. smoke의 대역 감시자가 실제 감시자로 세어지면 "감시자 없음" 경고가 맞게 뜨지 않는다. 그 결과 `-Stop`이 끝내는 감시자도 같은 인스턴스로 좁아진다. 기본 인스턴스(작업 스케줄러가 띄운 감시자)는 예전과 같이 찾는다(실제 `-Status`로 확인). 같은 이유로 `-Stop`이 종료를 대신 기록하게 했다. 이것이 없으면 정상 정지도 "기록 없이 끝남"으로 보인다 |

## Self-review

candidate 전 1회. minor 5건을 모두 반영했다.

1. 경고 기준이 코드는 간격의 두 배에 60초를 더했고, 기록과 README는 두 배라고 했다. 코드에서 60초를 빼 두 배로 맞췄다.
2. `-Stop`은 감시자를 강제로 끝내 `finally`가 돌지 않으므로, 정상 정지 뒤에도 `-Status`가 기록 없이 끝났다고 경고했을 것이다. `-Stop`이 대신 종료를 기록하게 코드를 고쳤고, smoke `stop_records_the_end`로 확인했다. 설계 1, README, 구현에 적었다.
3. 설계 3(같은 인스턴스로 좁힘)이 요약에 없었다. A4 행을 더했다.
4. 다른 봇을 기다리는 동안의 안내 줄 변경이 설계에 없었다. 설계 1에 적었다.
5. 계획에 있던 `-SelfTest` 결과가 검증 절에 없었다. 적었다(PASS).

고친 뒤 구문 오류 0, ASCII 밖 바이트 0, `-SelfTest` PASS, `-SmokeTest` 12/12, 실제 `-Status`는 앞과 같았다(감시자 35140, 봇 34260, 경고 없음).

## Repair

- candidate `18b6cd65a6c1944ac0d54b1abf1b5440a008dcd6`: Reviewer FINDINGS(유효, self_deviations 0).
  - (major) `last_heartbeat`는 봇이 간격보다 오래 돌 때의 `WaitForExit` 루프에서만 바뀌었다. 봇이 간격보다 빨리 끝나 재시작을 되풀이하면(대기 최대 300초) heartbeat가 전혀 갱신되지 않아, 살아 있는 감시자를 `-Status`가 "heartbeat 없음"으로 경고했을 것이다. 문제를 살필 때가 바로 그런 때다.
  - (minor) README가 pid 재사용 한계와 강제 종료 시각의 범위를 말하지 않았다.
- repair 1(`repair_count=1`, 기본 예산 안):
  - 새 함수 `Update-Alive`를 더했다. 감시자가 상태 파일을 쓰는 곳(시작, 다른 봇 안내, 봇 실행, 그리고 새로 더한 봇 종료)에서 `last_heartbeat`를 갱신한다.
  - 재시작 대기를 간격 단위로 나눠 자며, 간격이 지나면 heartbeat 줄("bot pid none (restarting)")을 쓴다. 봇을 띄운 시각부터 `WaitForExit` 간격을 다시 센다.
  - smoke `short_bot_keeps_heartbeat`를 더했다(바로 끝나는 대역 봇, heartbeat 3초, 두 번 실행: 재시작 대기 중 heartbeat 줄 2개 이상, 실행 횟수 2, 마지막 표시가 시작보다 10초 이상 뒤).
  - README에 두 한계와 "경고가 없다고 살아 있다는 증거는 아님"을 적었다.
  - 검사를 만드는 중 한 번 실패했다. 비교 기준 시각이 밀리초까지 있고 상태 파일은 초 단위라 경계에서 9.x초가 나왔다. 상태 파일의 시작 시각과 비교하도록 검사를 고쳤다(코드 결함 아님).
- 다시 돌린 결과: 구문 오류 0, ASCII 밖 바이트 0, `-SmokeTest` PASS 13/13을 두 번 연속, 실제 `-Status`는 앞과 같았다(감시자 35140, 봇 34260, 경고 없음). 검증 절의 12/12는 첫 candidate 기준이다.
