# task-0194-discord-bot-always-on

- id: `task-0194-discord-bot-always-on`
- title: `Discord 봇 상시 실행`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-24 11:03 UTC`
- updated_at: `2026-10-24 11:17 UTC`
- summary: `Discord 봇이 Claude 세션과 무관하게 늘 떠 있게 한다. 저장소에 PowerShell 실행 스크립트 하나를 두어 저장소 위치를 스스로 찾고, 봇이 이미 떠 있으면 두 번째를 띄우지 않고, 봇이 죽으면 잠시 뒤 다시 띄우고, 로그는 저장소 밖 LOCALAPPDATA에 남긴다. Windows 로그인 때 이 스크립트를 창 없이 띄우는 작업 스케줄러 등록·해제·상태 명령도 넣는다. 실제 등록은 완료 뒤 Owner 확인을 받고 한다.`
- source_command: `Owner 지시: 봇 상시 실행, 작업 스케줄러 방식 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `6e68844bc477cf7f9d1e02a591142f4d48c9b5c3` (등록 시점 main HEAD, task-0193까지 push 완료) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=1` (SOP §5 기본값, 사용 내역은 Repair 절) |

## Owner 결정 (원문)

```text
[Manager 추천]
1. 봇 상시 실행 (가장 추천)
- 지금 봇은 이 Claude 세션의 백그라운드 작업이라, 세션이 끝나거나 컴퓨터를 끄면 멈춥니다. 어제도 그렇게 끊겼습니다.
- Discord에서 언제든 시키려면 봇이 세션과 무관하게 떠 있어야 합니다.
- 방법: Windows 로그인 때 봇을 띄우는 별도 실행 스크립트, 또는 작업 스케줄러 등록. `jarvis.bat`은 건드리지 않습니다.
- 이 PC에 자동 실행을 등록하는 일이라 승인이 필요하고, 비용은 들지 않습니다.

[Owner 답]
1번 봇 상시 실행 진행해

[Manager 질문]
봇 상시 실행을 어떤 방식으로 할까요? 저장소에는 지금 봇을 띄우는 실행 스크립트가 없습니다(jarvis.bat은 읽지 않는 파일이라 무엇을 띄우는지 모릅니다). 어느 방식이든 저장소에 PowerShell 실행 스크립트를 하나 두고(저장소 위치를 스스로 찾음, 데스크톱 전용 경로 없음), 봇이 이미 떠 있으면 두 번째는 띄우지 않고, 봇이 죽으면 잠시 뒤 다시 띄우며, 로그는 저장소 밖(%LOCALAPPDATA%)에 남깁니다. 토큰은 지금처럼 adapters/discord/.env에서 봇이 직접 읽습니다.
- 작업 스케줄러 등록 (권장): Windows 로그인 때 스크립트를 창 없이 띄우는 작업을 현재 사용자 권한으로 등록합니다(관리자 권한 불필요). 등록·해제 명령도 스크립트에 넣습니다. 등록 자체는 이 PC의 설정 변경이라 제가 실행하기 전에 한 번 더 확인받습니다.
- 시작 프로그램 폴더: 사용자 시작 프로그램 폴더에 바로가기를 둡니다. 가장 단순하고 직접 지우기 쉽지만, 창이 잠깐 보일 수 있고 설정 범위가 좁습니다.
- 스크립트만 (자동 등록 없음): 실행 스크립트만 만들고, 띄우는 것은 Owner가 직접 합니다. 세션과 무관하게 돌지만 컴퓨터를 켤 때마다 한 번 실행해야 합니다.

[Owner 답]
작업 스케줄러 등록 (권장)
```

## 설계

1. 새 파일 `scripts/discord_bot_service.ps1`(Windows PowerShell 5.1). 저장소 위치는 스크립트 위치(`$PSScriptRoot`의 상위)로 찾고 `adapters/discord/bot_minimal.py`가 있는지 확인한다. 데스크톱 전용 절대경로는 넣지 않는다.
2. 동작(인자 하나):
   - `-Run`: 감시 루프. 로그온 세션별 이름 있는 mutex(`Local\` 네임스페이스)로 감시자를 하나만 둔다(두 번째 감시자는 바로 끝남). 봇을 띄우기 전에 다른 `bot_minimal.py` 봇 프로세스(`--self-check` 계열 제외)가 있으면 띄우지 않고 기다린다. 봇이 끝나면 10초부터 두 배씩 최대 300초 기다렸다 다시 띄우고, 10분 넘게 돈 뒤 끝났으면 대기를 처음으로 되돌린다. 봇은 `python -B -u adapters/discord/bot_minimal.py`, `PYTHONIOENCODING=utf-8`, 작업 디렉터리는 저장소 루트다.
   - `-Register`: 현재 사용자의 로그인 때 `powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File <이 스크립트> -Run`을 실행하는 작업 스케줄러 작업 `JarvisDiscordBot`을 등록한다(관리자 권한 불필요, 실행 시간 제한 없음, 같은 작업이 이미 돌고 있으면 새로 띄우지 않음, 실패하면 다시 시작, 배터리여도 실행). 등록 뒤 바로 한 번 시작하지는 않는다(`-Start`로 따로).
   - `-Unregister`: 그 작업을 지운다. `-Start`: 등록된 작업을 지금 시작한다. `-Stop`: 감시자와 봇 프로세스를 끝낸다. `-Status`: 작업 등록 여부, 감시자·봇 프로세스, 로그 위치를 보인다.
   - `-SelfTest`: 아무것도 띄우거나 등록하지 않고 저장소 위치, 봇 파일, python, 로그 폴더를 확인해 결과를 보인다.
   - `-SmokeTest`: 임시 폴더에서 대역 봇으로 감시 루프를 실제로 돌려 확인한다(Discord 접속·작업 등록 없음). 테스트용 인자 `-BotScript`, `-LogDir`, `-MaxLaunches`, `-InstanceName`은 이 확인을 위한 것이고 평소에는 기본값을 쓴다.
3. 로그: `%LOCALAPPDATA%\jarvis-core\logs`(저장소 밖). 감시자 줄은 시간을 붙여 `discord-bot.log`에 바로 쓰고 5MB를 넘으면 `.1`로 한 번 돌린다. 실행 중인 봇의 출력은 `discord-bot.out.log`·`discord-bot.err.log`에 쌓였다가 봇이 끝나거나 다음에 띄우기 전에 `discord-bot.log`로 옮긴다. 실행 중의 두 파일은 돌리지 않는다. 토큰은 스크립트가 읽지도 쓰지도 않는다(봇이 `.env`에서 직접 읽음).
4. 문서: `adapters/discord/README.md`에 상시 실행 절(명령, 로그 위치, 두 번째 봇을 막는 방식, `jarvis.bat`과의 관계는 확인하지 않았다는 점).
5. 바꾸지 않는 것: 봇 코드, `jarvis.bat`, `.env`, 다른 스크립트.
6. 실제 작업 스케줄러 등록과 지금 세션에서 띄운 봇의 교체는 task 완료 뒤 Owner 확인을 받고 한다(이 task의 범위 밖 실행 단계).

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `scripts/discord_bot_service.ps1`(새 파일), `adapters/discord/README.md`(상시 실행 절), `memory/tasks/task-0194-discord-bot-always-on.md` |
| deny | `jarvis.bat`, `adapters/discord/.env`, `adapters/discord/bot_minimal.py`와 다른 코드, `apps/`, Worker·팀장, writer·Console, AGENTS·agent 정의, validator, 다른 task 기록, 외부 API·credential, 보호 worktree, 이 task 안에서의 실제 작업 스케줄러 등록 |

## 계획

1. 스크립트 작성.
2. 검사: PowerShell 구문 분석 오류 0, `-SelfTest` 통과, `-Status`가 아무것도 바꾸지 않음, mutex로 두 번째 감시자가 끝남, 이미 떠 있는 봇이 있으면 새 봇을 띄우지 않음(가짜 봇 프로세스로), 재시작 대기 계산, 로그가 저장소 밖에 생기고 돌아감, 스크립트에 데스크톱 전용 경로·토큰 처리 없음. 실제 Discord 접속 없이 확인한다.
3. 사전 점검 → self-review → candidate → Reviewer → QA → Evidence·Complete(Manager, G3와 같게) → checkpoint. push, 등록, 봇 교체는 별도 확인.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-24 11:03 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다.

## 구현

- `scripts/discord_bot_service.ps1`(새 파일, ASCII만, PowerShell 5.1): 설계 2의 동작 `-Run`, `-Register`, `-Unregister`, `-Start`, `-Stop`, `-Status`, `-SelfTest`와 `-SmokeTest`. 감시자는 `Local\<이름>-supervisor` mutex로 하나만 두고, 앞 감시자가 강제로 끝나 mutex가 버려졌으면 그것을 넘겨받는다. 봇을 띄우기 전에 python 프로세스 가운데 명령줄에 봇 파일 이름이 있고 `--self-check`가 없는 것을 찾는다. 봇 출력은 실행마다 `discord-bot.out.log`·`discord-bot.err.log`에 받았다가 다음 실행 전과 종료 뒤 `discord-bot.log`에 옮겨 붙인다. python은 PATH에서 찾되 WindowsApps 별칭보다 실제 설치본을 쓴다.
- `adapters/discord/README.md`: 실행 절에 "4) 상시 실행" 절. 명령, 감시 동작, 로그 위치, 토큰을 다루지 않음, 검사 명령, `jarvis.bat`과의 관계를 적었다. 감시 루프의 봇이 떠 있는 동안 다른 경로로 봇을 또 띄우는 것은 막지 못한다는 한계도 적었다.
- 작업 중 `-SmokeTest`가 결함 두 개를 잡아 고쳤다: `Start-Process -PassThru`로 받은 프로세스의 종료 코드가 비어 로그에 남지 않던 것(시작 직후 `Handle`을 읽어 둠), PowerShell 5.1에서 결과가 하나뿐인 프로세스 목록의 개수가 비어 이미 떠 있는 봇을 놓치던 것(`@()`로 감쌈).

## Implementer 검증 (작업 트리)

- 구문 분석 오류 0, 파일에 ASCII 밖 바이트 0.
- `-SelfTest`: PASS(저장소 루트, 봇 파일, python 실제 설치본, 로그 폴더가 저장소 밖, 재시작 대기 10,20,40,80,160,300,300,10,20).
- `-Status`: 작업 미등록, 감시자 없음, 지금 세션에서 띄운 봇 1개를 찾음. 아무것도 바꾸지 않았다.
- `-SmokeTest`: PASS 7/7(실행과 종료 코드가 로그에 남음, 봇이 저장소 루트에서 실행됨, 두 번째 감시자가 끝남, 이미 떠 있는 봇이 있으면 띄우지 않음, 재시작 대기, 로그 돌림, 고정 경로·토큰 처리 없음), 약 22초. 지금 떠 있는 실제 봇에는 영향이 없었다(대역 봇은 이름이 달라 서로 보지 않음).
- 작업 스케줄러 등록은 하지 않았다(설계 6).
- `scripts/check_no_secrets.py`: findings 7건은 모두 그 검사 파일 자체의 예시 값(236~248행)이고, 이번 변경 파일에는 없다.
- 사전 점검(`check_task_record`, baseline `6e68844`): status=PASS, staged_files 3, violations 0.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "1번 봇 상시 실행 진행해" / "작업 스케줄러 등록 (권장)" | 작업 스케줄러 방식의 실행 스크립트를 만들었다. 다른 방식(시작 프로그램 폴더)은 쓰지 않았다 |
| A2 | Owner 결정 (원문) | "어느 방식이든 저장소에 PowerShell 실행 스크립트를 하나 두고(저장소 위치를 스스로 찾음, 데스크톱 전용 경로 없음), 봇이 이미 떠 있으면 두 번째는 띄우지 않고, 봇이 죽으면 잠시 뒤 다시 띄우며, 로그는 저장소 밖(%LOCALAPPDATA%)에 남깁니다." | 조건마다 확인한 검사: 스크립트 하나(`scripts/discord_bot_service.ps1`), 저장소 위치를 스스로 찾음(`-SelfTest`의 repo_root, smoke의 runs_from_repo_root), 데스크톱 전용 경로 없음(smoke의 no_fixed_paths_or_token), 두 번째 봇을 띄우지 않음(smoke의 no_second_bot, second_supervisor_ends), 죽으면 다시 띄움(smoke의 restarts_after_exit: 실제로 봇이 끝난 뒤 10초 기다려 두 번째로 띄움, restart_delays: 대기 계산), 로그는 저장소 밖(`-SelfTest`의 log_dir_outside_repo). 이미 떠 있는 봇 확인은 띄우기 직전에만 하므로, 감시 루프의 봇이 떠 있는 동안 다른 경로로 띄운 봇은 막지 못한다(README에 적음) |
| A3 | Owner 결정 (원문) | "토큰은 지금처럼 adapters/discord/.env에서 봇이 직접 읽습니다." | 스크립트는 토큰과 `.env`를 다루지 않는다(검사로 확인) |
| A4 | Owner 결정 (원문) | "Windows 로그인 때 스크립트를 창 없이 띄우는 작업을 현재 사용자 권한으로 등록합니다(관리자 권한 불필요). 등록·해제 명령도 스크립트에 넣습니다. 등록 자체는 이 PC의 설정 변경이라 제가 실행하기 전에 한 번 더 확인받습니다." | `-Register`·`-Unregister`를 넣었다. 등록은 현재 사용자·제한 권한(`RunLevel Limited`)이라 설계상 관리자 권한이 필요 없고, 창은 `-WindowStyle Hidden`으로 숨긴다. 다만 등록을 이 task에서 하지 않아 두 가지 모두 실제로는 확인하지 않았고, 숨긴 powershell도 로그인 때 콘솔 창이 잠깐 보일 수 있다. 완료 뒤 Owner 확인을 받고 등록할 때 확인한다 |
| A5 | Owner 결정 (원문) | "`jarvis.bat`은 건드리지 않습니다." | `jarvis.bat`은 읽지도 바꾸지도 않았다 |
| A6 | Owner 결정 (원문) | "Discord에서 언제든 시키려면 봇이 세션과 무관하게 떠 있어야 합니다." / "이 PC에 자동 실행을 등록하는 일이라 승인이 필요하고, 비용은 들지 않습니다." | 등록하면 작업 스케줄러가 로그인 때 감시 루프를 띄우므로 Claude 세션과 무관하게 돈다(등록 뒤 확인). 스크립트는 Windows 기본 기능(작업 스케줄러, PowerShell)과 이미 쓰던 python만 쓰고 유료 서비스나 외부 호출을 더하지 않는다. 등록은 승인 조건대로 완료 뒤 따로 확인받는다 |

## Self-review

candidate 전 1회. major 1건, minor 5건을 모두 반영했다.

1. (major) A4와 README가 "창 없이", "관리자 권한 불필요"를 확인하지 않은 채 단정했다. A4에 설계상의 근거와 미확인임을, README에 "설계상"과 창이 잠깐 보일 수 있다는 한계를 적었다. 실제 확인은 등록 때 한다.
2. 실행 중 봇 출력이 `discord-bot.log`가 아니라 out·err 파일에 쌓이고 그 두 파일은 돌리지 않는다는 점을 설계 3, README, 스크립트 머리말에 적었다.
3. `Local\` mutex는 사용자별이 아니라 로그온 세션별이다. 설계, README, 스크립트 주석을 고쳤다.
4. smoke 1번 주석은 저장소 루트 실행을 확인한다고 했지만 검사하지 않았다. 대역 봇이 작업 폴더를 출력하게 하고 `runs_from_repo_root` 검사를 더했다(smoke 7/7).
5. A2의 "네 조건"을 조건별 검사로 풀어 적었다.
6. 사전 점검 결과를 검증 절에 적었다.

## Repair

- candidate `9298d6070e86a7587b2052f0df341fe5e9adc593`: Reviewer FINDINGS(유효, self_deviations 0), minor 2건. (1) A2가 "죽으면 다시 띄움"을 smoke로 확인했다고 적었지만 smoke 감시자는 모두 `-MaxLaunches 1`이라 다시 띄우는 경로(대기, 두 번째 실행)를 돌린 적이 없다. (2) Manager 요약이 승인 조건 "세션과 무관하게 떠 있어야", "비용은 들지 않습니다"를 다루지 않는다.
- repair 1(`repair_count=1`, 기본 예산 안): `-SmokeTest`에 시나리오 두 개를 더했다. `restarts_after_exit`(`-MaxLaunches 2`로 봇이 끝나면 10초 뒤 두 번째로 띄우고 두 실행의 출력이 모두 로그에 남음), `abandoned_mutex_taken_over`(봇을 띄운 감시자를 강제로 끝낸 뒤 같은 이름의 새 감시자가 거절되지 않고 시작함, Reviewer가 미확인으로 남긴 항목). A2를 실제 검사로 고쳤고 A6 행을 더했다. README의 smoke 설명도 고쳤다.
- 다시 돌린 결과: 구문 분석 오류 0, ASCII 밖 바이트 0, `-SmokeTest` PASS 9/9(약 34초), `-Status`는 작업 미등록·실제 봇 1개 그대로. 위 검증 절의 7/7은 첫 candidate 기준이다.
