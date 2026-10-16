# task-0160-self-check-suite-exit-code

- id: `task-0160-self-check-suite-exit-code`
- title: `Discord --self-check-suite가 검사 실패 시 종료 코드 1을 내게 하고 README에 실행법과 종료 코드를 적기`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-16 12:04 UTC`
- updated_at: `2026-10-16 14:46 UTC`
- summary: `adapters/discord/bot_minimal.py --self-check-suite는 검사가 실패해 결과 JSON의 ok가 false여도 종료 코드 0을 내서, JSON을 직접 읽지 않으면 실패를 놓친다(task-0158 V4c 오판정). 출력 JSON은 그대로 두고 ok가 false면 종료 코드 1로 끝나게 하며, Discord README에 --self-check-suite 실행법과 종료 코드를 적는다. 단일 명령 --self-check의 종료 코드는 바꾸지 않고 push는 하지 않는다.`
- source_command: `Owner 결정: --self-check-suite 종료 코드 A안 진행, README도 같이 수정`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `fa48edd8aa6caffe70d9e59cd9e2b0f0137b8e44` (main HEAD = origin/main) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 환경 | Windows ACP 949, Python 3.12.10, `PYTHONUTF8`·`PYTHONIOENCODING` 미설정 |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (시작 시점. 이후 Owner가 `repair_budget`을 2로 늘렸고 현재 `repair_count=2`, 아래 "Reviewer와 repair 이력") |

## 조사 결과 (read-only, 정적 분석 기준)

1. `bot_minimal.py:3856-3858`은 `--self-check-suite` 결과 JSON을 출력하고 `return`해서 종료 코드가 항상 0이다. 실패는 JSON의
   `ok: false`와 실패한 검사 목록 `failed`(`:3728-3731`)에만 나타난다. 검사 도중 처리되지 않은 예외만 종료 코드 1이 된다.
2. 호출하는 곳: `scripts/`, `orchestrator/`, Console, Worker(`TEST_COMMAND`는 Studyroom smoke), `.claude`, `.codex`에 호출이 없다.
   봇 `/run` 허용 목록(`EXECUTION_SCRIPT_WHITELIST`)은 discord-intake smoke 하나다. README·SOP 문서에도 실행법이 없고, task 기록
   6건(0142/0144/0145/0150/0158/0159)에 수동 실행 기록만 있다. `jarvis.bat`은 지침상 열지 않아 확인하지 않았다.
3. 다른 smoke(discord-intake, discord-nl-intent는 `raise SystemExit(1 if failed else 0)`, Worker·audit-chain smoke, validator)는
   실패 시 0이 아닌 값으로 끝난다. 실패에도 0을 내는 것은 `--self-check-suite`뿐이다.
4. 단일 명령 `--self-check '<명령>'`은 명령 응답(오류 응답 포함)을 보여주는 도구라 종료 코드 0이 맞고, 빈 입력만 2다. 바꾸지 않는다.
   (정정, 구현 중 T5에서 확인: 2는 공백만 있는 입력일 때다. 빈 문자열 `''`은 아래 "검증 중 발생한 사건" 참고.)

## Owner 결정 (원문)

```text
A안으로 진행해, README도 같이 고쳐줘
```

A안(조사 보고 원문 요약): `ok`가 false면 종료 코드 1, 출력 JSON은 그대로. 범위는 `bot_minimal.py`의 `main()`과 Discord README.

정식 시작 승인(원문):

```text
task-0160 Console Start 진행하고 구현 시작해줘
```

candidate·Reviewer 진행 지시(원문 발췌, 문구 그대로):

```text
허용된 파일:

* `adapters/discord/bot_minimal.py`
* `adapters/discord/README.md`
* `memory/tasks/task-0160-self-check-suite-exit-code.md`

위 파일 외에 이번 작업에서 새 변경사항을 만들지 마라. 기존에 존재하는 `jarvis.bat`은 보호 대상이다. 열기, 읽기, 수정, 스테이징, 커밋을 모두 금지한다.
`--self-check-suite` 종료 코드 수정이 원래 요구사항에 맞는지, 단일 `--self-check` 동작을 불필요하게 바꾸지 않았는지 확인하라. 빈 문자열 `--self-check ''` 문제는 이번 작업에서 수정하지 마라.
기존 사건 경위와 미확인 사항은 보존하라. 사건이 없었던 것으로 결론 내리거나 외부 영향이 없었다고 단정하지 마라.
```

Reviewer FINDINGS 뒤 repair 결정(원문):

```text
1. Repair 1회 승인: Manager 요약 표에 빠진 두 조건을 추가하고 X3의 근거를 `AGENTS.md`·SOP로 바로잡습니다. 코드와 README는 수정하지 않습니다.
2. QA는 Reviewer 재검토 이후: Reviewer가 실제로 PASS를 내면 기존 task 절차에 따라 QA로 진행합니다. FINDINGS가 남으면 다시 멈추고 보고받습니다.
3. 빈 문자열 결함은 별도 task로 등록: task-0160과 분리하되, 우선순위는 높게 둡니다. 기존 코드가 빈 문자열을 self-check 입력으로 처리하지 않고 실제 봇 기동 경로로 진입할 수 있다는 점을 별도 결함으로 다룹니다.
```

Reviewer 2 FINDINGS 뒤 repair 2 결정(원문 발췌, 문구 그대로):

```text
Owner가 repair 예산을 총 2회로 늘리고 Repair 2를 승인한다.
수정 대상은 task 기록 문서뿐이다. 코드와 README는 수정하지 마라.
Reviewer의 세 지적을 해결하라.

1. X4와 사건 절에 빈 문자열 결함의 처리 결정을 정확히 기록한다.
   * 후속 후보로만 남기지 말 것.
   * 별도 task로 등록하고 우선순위를 높게 설정한다는 Owner 결정을 반영할 것.
   * 별도 task 번호가 아직 확정되지 않았다면 임의로 번호를 만들어 쓰지 말고, 등록 후 확정된 번호를 기록할 것.
2. Reviewer가 실제 PASS를 낸 뒤에만 QA로 진행하며 FINDINGS가 남으면 중단하고 Owner에게 보고한다는 조건을 Manager 요약 표에 추가한다.
3. Repair 1은 task 기록만 변경했으며 코드와 README는 수정하지 않았다는 범위 조건을 Manager 요약 표 또는 해당하는 명확한 요약 위치에 추가한다.

Owner 결정 원문, 기존 사건 경위, 미확인 사항 및 Reviewer 이력을 보존하라. 요약 표와 본문 사이에 모순이 없도록 모든 조건을 대조하라.
repair_count는 총 2회 중 2회 사용으로 정확하게 기록한다. 이번 작업에서 코드나 README를 수정하지 마라.
```

```text
* PASS가 아니면 더 수정하지 말고 중단할 것. repair 예산은 이미 소진됐다.
* PASS여도 이번 작업에서는 QA를 시작하지 말고 Owner에게 결과를 보고한 뒤 멈출 것.
```

## Manager 요약

| # | 승인 조건 | Manager 해석과 충족 방법 |
| --- | --- | --- |
| P0 | 정식 SOP task 등록, Console Start 뒤 구현 | 이 기록을 `TODO`로 만들고 Start Preview를 제시한 뒤 멈춘다. Confirm(`START TASK`)과 구현은 Owner 승인 뒤 |
| S1 | `--self-check-suite`가 `ok=false`면 종료 코드 1 | `main()`에서 결과를 변수에 담아 지금과 같은 JSON을 출력한 뒤 `ok`가 true가 아니면 `raise SystemExit(1)` |
| S2 | 출력 JSON은 그대로 | `_run_self_check_suite()`와 출력 형식(`ensure_ascii=False, indent=2`)을 바꾸지 않는다 |
| S3 | README에 실행법과 종료 코드 | Discord README "최소 로컬 검증"에 `--self-check-suite` 절을 더해 실행법, 성공 0·실패 1, 판정은 JSON `ok`와 `failed`로도 확인할 수 있음을 적는다 |
| X1 | 단일 명령 `--self-check` 종료 코드 불변 | 해당 분기를 바꾸지 않는다 |
| X2 | 범위 밖 파일 수정 금지 | 소유 파일은 `bot_minimal.py`, `adapters/discord/README.md`, 이 기록뿐 |
| X3 | `jarvis.bat` 금지(Owner 지시), push 별도 승인(AGENTS.md·SOP의 escalation gate, 이번 승인 문구 아님) | 접근하지 않고 push하지 않는다. `jarvis.bat` 안의 호출 여부는 Owner 확인 사항으로 남긴다 |
| X4 | "빈 문자열 `--self-check ''` 문제는 이번 작업에서 수정하지 마라." / "빈 문자열 결함은 별도 task로 등록: task-0160과 분리하되, 우선순위는 높게 둡니다." | task-0160에서는 `main()`의 단일 `--self-check` 분기와 빈 문자열 판정을 바꾸지 않는다. 결함은 별도 task `task-0161-self-check-empty-string-starts-bot`로 `TODO` 등록했고 우선순위는 높음이다(그 task는 Start Preview까지만, Confirm·구현 없음) |
| X5 | "기존 사건 경위와 미확인 사항은 보존하라. 사건이 없었던 것으로 결론 내리거나 외부 영향이 없었다고 단정하지 마라." | "검증 중 발생한 사건" 절의 경위·확인 범위·미확인 항목을 지우거나 줄이지 않고, 추가 확인은 덧붙이기만 한다 |
| X6 | "QA는 Reviewer 재검토 이후: Reviewer가 실제로 PASS를 내면 기존 task 절차에 따라 QA로 진행합니다. FINDINGS가 남으면 다시 멈추고 보고받습니다." | Reviewer가 실제 PASS를 낸 candidate에만 QA를 시작한다. FINDINGS가 남으면 수정하지 않고 멈춰 Owner에게 보고한다. repair 2 뒤 Reviewer는 PASS여도 QA를 시작하지 않고 결과를 보고한 뒤 멈춘다(repair 2 지시) |
| X7 | repair 범위: "코드와 README는 수정하지 않습니다."(repair 1) / "수정 대상은 task 기록 문서뿐이다. 코드와 README는 수정하지 마라."(repair 2) | repair 1과 repair 2는 이 task 기록만 바꾼다. `bot_minimal.py`와 README의 내용은 첫 candidate `d77c01c` 그대로다 |

## File ownership

| 구분 | 경로 |
| --- | --- |
| owned | `adapters/discord/bot_minimal.py`(`main()`의 `--self-check-suite` 분기), `adapters/discord/README.md`, 이 기록 |
| deny | `jarvis.bat`, `docs/master-plan.md`, 다른 task 기록, 그 밖의 모든 파일 |

Docs 판정: README 변경이 승인 범위 안에 있어 Implementer candidate에 포함한다. 별도 Docs 단계는 `not_required`.

## 검증 계획

| # | 항목 |
| --- | --- |
| T1 | 설정 없음과 `PYTHONUTF8=1` 각각에서 `--self-check-suite` 종료 코드 0, JSON `ok=True`, 93/0 |
| T2 | 검사 하나를 실패시키는 변형(임시 worktree)에서 종료 코드 1, JSON이 끝까지 출력되고 `ok=false`, `failed`에 그 검사 이름 하나 |
| T3 | 수정을 뺀 같은 변형에서 종료 코드 0(이전 동작 재현) |
| T4 | 검사 도중 처리되지 않은 예외 변형에서 종료 코드 1(기존 동작 유지) |
| T5 | 단일 명령 `--self-check '/status invalid-id'` 종료 코드 0, `--self-check ''` 종료 코드 2(불변) |
| T6 | discord-intake smoke, Worker smoke, SOP validator, Console smoke, `git diff --check`, 변경 범위 |

## 구현 착수

2026-10-16 12:08 UTC에 Jarvis Console Start(Preview + Confirm, `START TASK`)로 `TODO→DOING`을 적용했다(Console 결과
`result_type: updated`, `TODO → DOING`, `no_execution: true`).

## 구현

| 파일 | 변경 |
| --- | --- |
| `adapters/discord/bot_minimal.py` | `main()`의 `--self-check-suite` 분기: 결과를 `suite_result`에 담아 같은 JSON을 출력한 뒤 `ok`가 `True`가 아니면 `raise SystemExit(1)`(S1·S2) |
| `adapters/discord/README.md` | "최소 로컬 검증"에 `--self-check` 종료 코드 한 줄과 "4) 회귀 자체 검사 묶음 (`--self-check-suite`)" 절(실행법, 종료 코드 0/1, 예외 시 0이 아님, `ok`·`total`·`failed`)을 더했다(S3) |

## Implementer 검증 (작업 트리 기준, candidate 전)

변형은 `HEAD` 임시 worktree에 작업 트리의 `bot_minimal.py`를 복사해 실행했고, 실행 뒤 worktree와 임시 폴더를 지웠다. 원본 checkout의
HEAD와 status는 실행 전후 같았다. 판정은 종료 코드와 함께 출력 JSON의 `ok`·`total`·`failed` 이름으로 했다.

| # | 결과 |
| --- | --- |
| T1 | 설정 없음·`PYTHONUTF8=1` 모두 종료 0, `ok=True`, 93/0 |
| T2 | `execution_output_utf8_and_none_safe`를 실패시킨 변형: 종료 1, `ok=False`, 93건 중 failed 1(`execution_output_utf8_and_none_safe`), JSON 끝까지 출력 |
| T3 | 같은 변형에서 종료 코드 처리 제거: 종료 0, `ok=False`(이전 동작 재현) |
| T4 | suite 첫 줄에서 예외: 종료 1, JSON 없음, stderr 마지막 줄 `RuntimeError: mutation: crash inside the suite` |
| T5 | `--self-check '/status invalid-id'` 종료 0(`result_type: error`). `--self-check ' '` 종료 2(`empty_input`). `''`은 아래 사건 참고 |
| T6 | `py_compile` 통과, discord-intake 135/0(새 task 기록 1건 포함), Worker smoke 354/0, SOP validator PASS, Console smoke PASS, `git diff --check` 통과, 변경 파일 2개와 이 기록 |

## 검증 중 발생한 사건 (Owner 보고 대상)

- T5에서 `--self-check ''`(빈 문자열)을 실행하자 `args.self_check`가 거짓으로 판정되어 `main()`의 self-check 분기를 모두 지나쳤다.
  그 뒤 `adapters/discord/.env`의 실제 환경으로 `_validate_required_env()`를 통과하고 `_start_discord_bot()`에 들어가 실제 Discord 봇
  프로세스가 기동됐다. 이번 변경과 무관한 기존 동작이다.
- 기동 시각은 2026-10-16 12:09 UTC 무렵이고, 검증 스크립트가 진행되지 않는 것을 보고 12:23 UTC 무렵 해당 자식 프로세스(PID 11820)만
  종료했다. 그 사이 봇 출력은 캡처 파이프로만 갔고 프로세스 종료와 함께 사라져, 연결 성공 여부와 메시지 처리 여부는 출력으로 확인할 수 없다.
- 읽기 전용으로 확인한 범위: 감사 체인(`%LOCALAPPDATA%\Jarvis-Core\audit\v1\chain.jsonl`) 최종 수정 2026-10-15, task 기록 중 30분 안에
  바뀐 것은 이 기록(Console Start)뿐, Worker worktree 새 항목 없음, 저장소 추적 변경은 이번 구현 2파일뿐이다. Discord 채널 쪽 응답 여부는
  확인하지 못했다.
- Discord 추가 확인(Owner가 앱 내장 브라우저에 로그인한 뒤, 읽기 전용): 의도치 않은 실행 시간 2026-10-16 12:09~12:23 UTC(한국 시각
  21:09~21:23)에 대해 javis-core 서버 `#일반`과 `@jarvis-bot` DM을 확인했고, 두 곳 모두 그 시간대에 봇이 보낸 메시지 기록이 없었다.
  `#일반`의 마지막 메시지는 2026-10-14 13:30 UTC의 task-0143 `/go` 실패 응답, DM의 마지막 메시지는 2026-10-15 04:33 UTC의 task-0143
  `/go` 완료 응답이다. 브라우저에서는 기록을 읽기만 했고 메시지 전송이나 설정 변경은 하지 않았으며, 조회용으로 바꾼 브라우저 창 크기는
  원래대로 되돌렸다.
- 여전히 확인하지 않은 것: 실제 Discord 연결 여부(온라인 표시 등), 다른 서버의 채널과 다른 DM, 서버 감사 로그, Developer Portal.
  두 위치에 메시지가 없다는 것만으로 외부 영향이 전혀 없었다고 단정하지 않는다.
- 빈 문자열 결함의 처리. 처음 기록: 후속 후보: `main()`이 `args.self_check is not None`으로 판정해 빈 문자열도 `empty_input`(종료 2)으로
  거절하게 하는 수정. task-0160 범위 밖이라 이번 candidate에 넣지 않는다. Owner 결정 뒤: 후속 후보로만 두지 않고, task-0160과 분리한
  별도 task `task-0161-self-check-empty-string-starts-bot`로 `TODO` 등록했다(우선순위 높음, 2026-10-16 14:36 UTC, Start Preview까지만,
  Confirm·구현 없음). task-0160에서는 이 결함을 수정하지 않는다.

## Reviewer와 repair 이력

| 회차 | candidate | 결과 |
| --- | --- | --- |
| Reviewer 1 | `d77c01c7200295e58b639e9c21953b45c5aab81f` | FINDINGS. major 2: Manager 요약에 Owner 조건 "빈 문자열 `--self-check ''` 수정 금지"와 "사건 경위·미확인 사항 보존, 외부 영향 없음 단정 금지"가 없음(candidate 자체는 두 조건을 지킴). minor 1: X3의 push 제한은 이번 승인 문구가 아니라 AGENTS.md·SOP 규칙 |
| repair 1 | (이 기록 수정) | Owner 승인으로 Manager 요약에 X4·X5를 더하고 X3 근거를 AGENTS.md·SOP로 표시했다. 승인 원문 블록을 "Owner 결정"에 옮겼다. 코드와 README는 바꾸지 않았다. `repair_count=1`(budget 1 소진) |
| Reviewer 2 | `18198d0c2a1a2d24bf15852f32f1ef5d149d01d3` | FINDINGS. major 1: X4와 사건 절이 빈 문자열 결함을 후속 후보로만 적어 Owner 결정(별도 task 등록, 우선순위 높음)과 다름. minor 2: Manager 요약에 "실제 PASS 뒤에만 QA, FINDINGS면 멈추고 보고" 조건과 repair 1의 "코드·README 미수정" 범위 조건이 없음 |
| repair 2 | (이 기록 수정) | Owner가 repair budget을 2로 늘리고 repair 2를 승인했다. 빈 문자열 결함을 `task-0161-self-check-empty-string-starts-bot`로 `TODO` 등록하고(우선순위 높음) X4와 사건 절에 반영했으며, Manager 요약에 X6(QA 조건)·X7(repair 범위)을 더했다. 코드와 README는 바꾸지 않았다. `repair_budget=2`, `repair_count=2`(2회 중 2회 사용, 소진) |
| Reviewer 3 | `1993db758282032e5b3bfe6a59a3f04dcb41f30f` | PASS, findings 없음. 미검증으로 밝힌 것: task-0161 기록(candidate 밖), T1~T6 실행 결과, 저장소 밖 사건 사실, Console Start 적용 |

## QA (candidate `1993db758282032e5b3bfe6a59a3f04dcb41f30f`)

2026-10-16에 candidate를 detached 임시 worktree로 꺼내 실행하고 끝난 뒤 지웠다. 그 worktree에는 `adapters/discord/.env`가 없고 실행 환경에
`DISCORD_BOT_TOKEN`도 없었다. 변형(T2~T4)은 그 worktree의 `HEAD`에서 다시 만든 임시 worktree에서 돌렸다. 판정은 종료 코드와 출력 JSON의
`ok`·`total`·`failed` 이름으로 했다.

| # | 결과 |
| --- | --- |
| T1 | PASS. 설정 없음·`PYTHONUTF8=1` 두 정상 실행 모두 종료 0, `ok=True`, 93/0 |
| T2 | PASS. `execution_output_utf8_and_none_safe`를 실패시킨 변형: 종료 1, `ok=False`, 93건 중 failed 1(`execution_output_utf8_and_none_safe`), JSON 끝까지 출력 |
| T3 | PASS. 같은 변형에서 종료 코드 처리 제거: 종료 0, `ok=False`(수정 전 결함 재현) |
| T4 | PASS. suite 안 예외 변형: 종료 1, stderr 마지막 줄 `RuntimeError: mutation: crash inside the suite` |
| T5 | PASS(실행한 범위). `--self-check '/status invalid-id'` 종료 0(`result_type: error`), `--self-check ' '` 종료 2(`empty_input`) |
| T6 | PASS. `py_compile` 통과, discord-intake 135/0, Worker smoke 354/0, SOP validator PASS, Console smoke PASS, `git diff --check`(baseline 대비) 통과, 변경 범위 3파일(`bot_minimal.py`, README, 이 기록), `jarvis.bat`은 tree에 없음, 코드·README는 `d77c01c` 대비 차이 0줄, 실행 뒤 QA worktree 변경 없음 |

실행 뒤 정리: 변형용·QA용 worktree를 지웠고 원본 checkout의 HEAD와 status는 실행 전후 같았다. `%TEMP%\jarvis_worker_smoke_*`는 39개
그대로이고 이번 실행으로 남은 임시 폴더는 없다. 남은 Python 프로세스와 8790 listener는 없다.

안전상 실행하지 않았거나 확인하지 않은 것(PASS로 보지 않는다):

- `--self-check ''`: 실제 봇 기동 위험 때문에 실행하지 않았다. `task-0161-self-check-empty-string-starts-bot`에서 따로 다룬다.
- `jarvis.bat`이 `--self-check-suite`를 부르는지: 접근 금지 조건 때문에 확인하지 않았다.
- 사건의 외부 영향: "검증 중 발생한 사건" 절의 미확인 사항은 그대로다.
