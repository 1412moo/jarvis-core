# task-0174-discord-report-on-hold-count

- id: `task-0174-discord-report-on-hold-count`
- title: `Discord /report·/retro today에 ON_HOLD 집계 추가와 상태 어휘 드리프트 가드`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-20 12:53 UTC`
- updated_at: `2026-10-20 13:08 UTC`
- summary: `Discord /report, /report today, /retro today의 상태 목록 REPORT_STATUS_ORDER에 ON_HOLD가 없어 보류 task가 total에는 들어가고 상태별 집계와 출력에서는 빠진다. ON_HOLD를 BLOCKED 바로 뒤에 더하고, 출력은 공통 목록을 반복하며, TASK_ALLOWED_STATUSES와의 드리프트 가드, /review-task의 ON_HOLD 안내, README 머리말 정정을 더했다. candidate ae2d992가 Reviewer PASS와 QA PASS를 받은 뒤 기록 시각 정정을 repair 1로 다뤄 새 candidate를 만들었고, 그 Reviewer·QA 결과는 본문에 기록한다.`
- source_command: `Owner 결정: task-0174 등록과 구현 전 계획 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `54cab645949780c57e432b5075f08b1a373ec671` (등록 시점 main HEAD = origin/main, fetch 후 확인). Start 때 다시 확인한다 |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 등록 방식 | 이 기록을 `TODO`로 작업 트리에만 만들었다(커밋·stage 없음). task-0173과 같이 Start 승인 뒤 candidate commit에 함께 들어간다 |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=1` (기본값. repair 1 사용, 아래 "Repair 1") |

## Owner 결정 (원문)

```text
task-0174에 대한 Owner 결정을 전달한다.
제목: Discord `/report`·`/retro today`에 ON_HOLD 집계 추가와 상태 어휘 드리프트 가드
확정 결정

1. ON_HOLD 출력 위치는 `BLOCKED` 바로 뒤로 한다.
2. `/retro today`의 follow-up 목록에는 ON_HOLD를 넣지 않는다. 의도적으로 보류된 작업은 FAILED·BLOCKED 후속 조치와 구분한다.
3. `/review-task`에서 ON_HOLD 상태에 맞는 명확한 안내를 추가한다.
4. README의 `/report today` 출력 예시 머리말 오류를 함께 바로잡는다.
5. 출력 생성은 공통 상태 목록을 반복하도록 개선하되 기존 상태 줄의 문구와 순서를 불필요하게 변경하지 않는다.
6. `REPORT_STATUS_ORDER`와 `TASK_ALLOWED_STATUSES` 사이의 드리프트 가드를 추가한다.
7. `/report`, `/report today`, `/retro today` 모두 ON_HOLD 집계와 출력이 정확한지 결정론적 테스트로 검증한다.
8. 상태별 합계와 total의 일치 여부도 테스트한다.

범위 제한

* 기존 6건의 task 상태는 변경하지 않는다.
* 승인·상태 전이·감사 체인은 수정하지 않는다.
* task-0173에서 완료한 Hold/Resume 기능을 재설계하지 않는다.
* 실제 Discord 전송 검증은 범위에서 제외한다.
* `jarvis.bat`, 기존 worktree, 임시 폴더를 보호한다.
* push는 별도 Owner 승인 전까지 금지한다.

진행 방식

1. 먼저 현재 `main`과 `origin/main`이 동기화되어 있는지 확인한다.
2. 기존 task 등록 규칙과 SOP를 확인하고 task-0174를 공식 절차에 따라 등록한다.
3. 구현 전 변경 파일과 테스트 계획을 제시한다.
4. 공식 Console Start 승인 전에는 구현하지 않는다.
5. 승인 후 기존 SOP대로 self-review, preflight, Reviewer, QA, Console Complete를 진행한다.
6. 실제 검증 결과와 변경 범위를 보고한다. 확인하지 않은 내용은 완료로 표현하지 않는다.

먼저 task 등록과 구현 전 계획까지만 진행하고, 공식 Start 승인 전에는 코드를 수정하지 마.
```

등록 전 확인: fetch 뒤 `main` = `origin/main` = `54cab64`, 앞섬·뒤처짐 0. `memory/tasks`에 task-0174 파일 없음, `0174` branch 없음. 등록 관례는 task-0172·0173과 같다(작업 트리에 `TODO` 기록, Start 뒤 candidate에 포함).

## 조사 결과 (read-only, 등록 전 확인)

| # | 사실 | 근거 |
| --- | --- | --- |
| F1 | `REPORT_STATUS_ORDER`는 `TODO, DOING, BLOCKED, DONE, FAILED, NEEDS_APPROVAL` 6개이고 `ON_HOLD`가 없다. 공식 어휘(`TASK_ALLOWED_STATUSES`, task-model §2)는 7개다 | `adapters/discord/bot_minimal.py:104`, `orchestrator/discord-intake/task_file_writer.py` `TASK_ALLOWED_STATUSES` |
| F2 | 세 명령의 집계 루프는 `if task_status in counts:`로 목록 밖 상태를 버리지만 `total`은 읽힌 task 전부다. 그래서 ON_HOLD task가 있으면 상태별 합계가 total보다 작다 | `bot_minimal.py:666-685`(`/report`·`/report today` 공통 `_build_report_payload`), `:734-780`(`/retro today`) |
| F3 | 출력은 세 곳에서 상태 6줄을 하드코딩한다 | `_format_reply`의 `report_empty`(`:2819`), `report`(`:2833`), `retro_today`(`:2587`) |
| F4 | `REPORT_STATUS_ORDER`는 이 세 명령에서만 쓰인다. 승인·전이·실행·감사 경로와 관계없다 | `bot_minimal.py:104, 668, 670, 689, 741` |
| F5 | 재현(저장소 밖 임시 루트, ON_HOLD·TODO·BLOCKED 3건): 세 명령 모두 total 3, 상태별 합계 2, counts에 `ON_HOLD` 키 없음, 출력에 ON_HOLD 줄 없음. 보류 task는 최근 업데이트 목록에는 나온다. 현재 저장소는 ON_HOLD 기록 0건이라 total 125 = 합계 125 | 등록 전 읽기 전용 probe |
| F6 | `/retro today`의 follow-up은 FAILED·BLOCKED, completed는 DONE이다. `summary_line`은 FAILED+BLOCKED로 정한다 | `bot_minimal.py:756-771` |
| F7 | `/review-task`의 `_build_review_notes`·`_build_recommended_next_steps`에 ON_HOLD 분기가 없어 "상태 정보 점검 필요"·"task 메타데이터를 점검한다"가 나온다 | `bot_minimal.py:843-873` |
| F8 | README의 `/report today` 예시 머리말 "📊 task report (today, UTC)"는 코드에 없다. 코드는 `/report`와 `/report today` 모두 같은 `report` 결과 형식이라 "📊 task report"를 출력한다 | `adapters/discord/README.md:190`, `bot_minimal.py:2833-2849` |
| F9 | `docs/status-report-contract.md`의 counts 예시(§4.1·§4.2)와 `/status` status 열거(§3.1)에 ON_HOLD가 없다. README 출력 예시 3곳도 6줄이다 | `docs/status-report-contract.md`, `adapters/discord/README.md:171-215` |
| F10 | 결정론적 검사는 `bot_minimal.py --self-check-suite`(임시 저장소 루트, `_write_task` 헬퍼)에 있다. `/report`·`/retro today` 검사는 DONE·BLOCKED만 본다 | `bot_minimal.py:2905`, `:3210`, `:3705-3755` |
| F11 | 봇은 이미 `task_file_writer`에서 `TASK_STATUS_TRANSITIONS`를 import한다. `TASK_ALLOWED_STATUSES`도 같은 모듈에 있다 | `bot_minimal.py:55-60` |

## 설계 (Start 승인 시)

| # | 결정 | 구현 |
| --- | --- | --- |
| 1 | ON_HOLD는 BLOCKED 바로 뒤 | `REPORT_STATUS_ORDER = ("TODO", "DOING", "BLOCKED", "ON_HOLD", "DONE", "FAILED", "NEEDS_APPROVAL")`. 기존 6개의 상대 순서는 그대로다 |
| 2 | retro follow-up에 ON_HOLD 넣지 않음 | follow-up 조건 `{"FAILED", "BLOCKED"}`와 `summary_line` 계산을 바꾸지 않는다. ON_HOLD는 counts와 출력에만 들어간다 |
| 3 | `/review-task` ON_HOLD 안내 | `_build_review_notes("ON_HOLD")`: "의도적으로 보류된 상태로 보임(Owner 재우선순위 대기)". `_build_recommended_next_steps("ON_HOLD")`: "summary의 보류 사유와 재개 조건을 확인한다", "재개는 Owner 결정 뒤 Jarvis Console Resume으로 보류 전 상태(hold_from)로 되돌린다". 승인·실행을 권하지 않는다 |
| 4 | README 머리말 정정 | `/report today` 예시 머리말을 실제 출력 "📊 task report"로 고치고, 세 예시에 `- ON_HOLD: 0` 줄을 BLOCKED 뒤에 넣는다 |
| 5 | 공통 목록 반복 | 헬퍼 하나(예: `_status_count_lines(counts)`)가 `REPORT_STATUS_ORDER` 순서로 `- <STATUS>: <n>` 줄을 만들고, 세 출력 블록이 이를 쓴다. 기존 줄 문구(`- TODO: n` 형식)와 다른 줄(머리말, total, 최근 업데이트, completed·follow-up·summary)은 그대로다 |
| 6 | 드리프트 가드 | `task_file_writer`에서 `TASK_ALLOWED_STATUSES`를 import하고, self-check가 `set(REPORT_STATUS_ORDER) == TASK_ALLOWED_STATUSES`와 중복 없음을 검사한다 |
| 7·8 | 결정론적 테스트 | 아래 검증 계획 V1~V6 |

문서: `docs/status-report-contract.md` §4.1·§4.2 counts 예시에 `"ON_HOLD": 0`을 BLOCKED 뒤에, §3.1 status 열거에 `ON_HOLD`를 더한다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `adapters/discord/bot_minimal.py`, `adapters/discord/README.md`, `docs/status-report-contract.md`, `memory/tasks/task-0174-discord-report-on-hold-count.md` |
| deny | `jarvis.bat`, 기존 task 기록(보류 6건과 task-0035 포함), `orchestrator/discord-intake/`(writer·전이), `orchestrator/audit-chain/`, `orchestrator/worker/`, `apps/jarvis-console/`, `docs/task-model.md`, `docs/master-plan.md`, `scripts/`, 그 밖의 모든 파일 |

명시적 제외: 기존 6건 상태 변경, 승인·상태 전이·감사 체인, task-0173 Hold/Resume 재설계, 실제 Discord 전송 검증, `/status`·`/review-task`의 `hold_from` 표시, push.

`bot_minimal.py` 안에서 바꾸는 곳은 `REPORT_STATUS_ORDER`, `task_file_writer` import 한 줄, 세 출력 블록과 새 헬퍼, `_build_review_notes`·`_build_recommended_next_steps`의 ON_HOLD 분기, self-check 검사 추가뿐이다. 승인·전이·실행·Worker 함수는 건드리지 않는다.

## 검증 계획

| # | 검사 | 기대 |
| --- | --- | --- |
| V1 | self-check: `/report` 집계 | ON_HOLD fixture(`hold_from` 포함) 추가 전후 `counts["ON_HOLD"]`가 1 늘고, `sum(counts) == total` |
| V2 | self-check: `/report today` 집계 | 오늘 날짜 ON_HOLD fixture가 `counts["ON_HOLD"]`에 들어가고 `sum(counts) == total` |
| V3 | self-check: `/retro today` | ON_HOLD가 counts에 들어가고 `sum(counts) == total`, follow-up 목록과 `summary_line`에는 영향 없음(ON_HOLD만 있는 날은 "today moved forward") |
| V4 | self-check: 출력 | 세 출력(`report`, `report_empty`, `retro_today`)에 상태 줄이 정확히 `TODO, DOING, BLOCKED, ON_HOLD, DONE, FAILED, NEEDS_APPROVAL` 순서로 `- <STATUS>: <n>` 형식으로 나온다. ON_HOLD 줄을 빼면 기존 6줄과 같다 |
| V5 | self-check: 드리프트 가드 | `set(REPORT_STATUS_ORDER) == TASK_ALLOWED_STATUSES`, 길이 7, 중복 없음 |
| V6 | self-check: `/review-task` | ON_HOLD task에 새 안내 문구가 나오고, 다른 6개 상태의 문구는 그대로 |
| V7 | 회귀 | `bot_minimal.py --self-check-suite` 전체 `ok: true`, discord-intake smoke, Console smoke, SOP validator, `check_task_record.py`, `git diff --check` |
| V8 | 변형 확인(QA) | `REPORT_STATUS_ORDER`에서 ON_HOLD 제거, 출력 블록 하나를 하드코딩으로 되돌림, retro follow-up에 ON_HOLD 추가, 가드 제거가 각각 self-check 실패로 드러남 |
| V9 | 보존 | 보류 6건과 task-0035 blob 무변경, `jarvis.bat` untracked, 보존 worktree 그대로, listener 없음 |

완료 조건: 같은 candidate에 Reviewer PASS와 QA PASS, Docs 판정 기록, 범위 밖 변경 없음, Owner의 Console Complete로 DONE. push는 별도 승인.

## SOP 절차

1. Owner의 Start 승인 원문을 이 기록에 붙이고 Manager 요약을 작성한다.
2. Jarvis Console Start(Preview + `START TASK`)로 `TODO→DOING`.
3. 구현과 Implementer 검증.
4. `check_task_record.py` 사전 점검 → `jarvis-self-review` 절차로 self-review 1회 → 지적 처리와 `Self-review` 절 → 사전 점검 재통과.
5. candidate commit → `check_summary_quotes.py` → Reviewer(exact hash) → QA(임시 worktree). budget retry 1, repair 1. 소진되면 escalation.
6. Docs 판정, SOP §8 대조, 결과 기록 checkpoint, Owner의 Console Complete, DONE checkpoint. push 없음.

## 위험

| # | 위험 | 대응 |
| --- | --- | --- |
| R1 | 출력 리팩터링이 기존 줄 문구·순서를 바꿈 | V4가 7줄 순서와 형식을 고정하고, ON_HOLD 줄을 뺀 결과가 기존 6줄과 같은지 검사 |
| R2 | 출력 문자열을 파싱하는 소비자가 깨짐 | 저장소 안에서 이런 소비자를 찾지 못했다(추측: 사람만 읽는다). 줄 하나가 늘어날 뿐 기존 줄은 그대로다 |
| R3 | 다음 상태 추가 때 다시 누락 | V5 드리프트 가드 |
| R4 | self-check fixture가 누적돼 집계 기대값이 흔들림 | V1~V3은 절대값 대신 추가 전후 차이와 `sum == total`로 검사 |

## 작업량

작음. 코드 1개 파일(약 40~70줄, 대부분 self-check), 문서 2개.

## Owner 확인 사항

정책 결정은 모두 확정됐다. 구현 단계 기본값(바꾸려면 Start 승인 때 지정): `/review-task` ON_HOLD 문구(설계 3), 헬퍼 이름 `_status_count_lines`.

## Start 승인 (원문)

```text
task-0174 Console Start 승인한다, 계획대로 진행해
```

Start 전 확인(2026-10-20 12:55 UTC): fetch 뒤 branch `main`, HEAD `54cab645949780c57e432b5075f08b1a373ec671`(기준선과 같음, origin/main과 같음), tracked 변경 없음, untracked `jarvis.bat`과 이 기록. worktree 5개(main과 보존 worktree 4개). "계획대로"는 위 설계·범위·검증 계획·SOP 절차를 뜻한다. SOP §8에 따라 DONE은 Owner의 Console Complete 결정으로 남긴다.

## 구현 착수

2026-10-20 12:56 UTC에 Jarvis Console Start(Preview + Confirm, `START TASK`)로 `TODO→DOING`을 적용했다. Preview는 `current_state` TODO,
`transition` TODO → DOING, 저장 위치 이 기록, `no_execution: true`였다. Confirm 결과 `result_type: updated`, `no_execution: true`. 서버는
`--no-browser`로 띄운 뒤 그 프로세스만 종료했다.

## Manager 요약

원문 인용은 위 두 원문 블록의 문장을 그대로 옮겼다. 해석은 오른쪽 칸에만 적는다.

| # | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- |
| S1 | "task-0174에 대한 Owner 결정을 전달한다." / "제목: Discord `/report`·`/retro today`에 ON_HOLD 집계 추가와 상태 어휘 드리프트 가드" | 이 제목 그대로 task-0174로 등록했다 |
| S2 | "ON_HOLD 출력 위치는 `BLOCKED` 바로 뒤로 한다." | `REPORT_STATUS_ORDER`를 `TODO, DOING, BLOCKED, ON_HOLD, DONE, FAILED, NEEDS_APPROVAL`로 바꿨다. 세 출력 모두 이 순서로 상태 줄을 만든다(self-check `*_reply_status_lines`) |
| S3 | "`/retro today`의 follow-up 목록에는 ON_HOLD를 넣지 않는다." / "의도적으로 보류된 작업은 FAILED·BLOCKED 후속 조치와 구분한다." | follow-up 조건(`FAILED`·`BLOCKED`)과 `summary_line` 계산은 바꾸지 않았다. ON_HOLD는 counts와 출력에만 들어간다. self-check가 ON_HOLD 추가 전후 follow-up·completed·summary가 같고, ON_HOLD만 있는 날은 "today moved forward"임을 검사한다 |
| S4 | "`/review-task`에서 ON_HOLD 상태에 맞는 명확한 안내를 추가한다." | `_build_review_notes`와 `_build_recommended_next_steps`에 ON_HOLD 분기를 더했다(보류 사유·재개 조건 확인, Owner 결정 뒤 Console Resume). 승인·실행은 권하지 않는다. self-check가 7개 상태 문구 전체를 고정하고(`review_task_status_guidance`), ON_HOLD fixture에 `/review-task`를 실행해 응답의 두 필드와 출력에 새 안내가 나오는지 본다(`review_task_on_hold_command`) |
| S5 | "README의 `/report today` 출력 예시 머리말 오류를 함께 바로잡는다." | README `/report today` 예시 머리말을 실제 출력 "📊 task report"로 고쳤다 |
| S6 | "출력 생성은 공통 상태 목록을 반복하도록 개선하되 기존 상태 줄의 문구와 순서를 불필요하게 변경하지 않는다." | `_status_count_lines` 헬퍼가 `REPORT_STATUS_ORDER`를 반복해 `- <STATUS>: <n>` 줄을 만들고 세 출력 블록이 이를 쓴다. 기존 6줄의 문구와 상대 순서, 다른 줄은 그대로이며 self-check가 ON_HOLD를 뺀 순서가 기존 6개와 같음을 검사한다 |
| S7 | "`REPORT_STATUS_ORDER`와 `TASK_ALLOWED_STATUSES` 사이의 드리프트 가드를 추가한다." | `task_file_writer`에서 `TASK_ALLOWED_STATUSES`를 import하고 self-check `report_status_order_matches_vocabulary`가 집합 일치, 길이 7, 중복 없음, ON_HOLD가 BLOCKED 바로 뒤임을 검사한다 |
| S8 | "`/report`, `/report today`, `/retro today` 모두 ON_HOLD 집계와 출력이 정확한지 결정론적 테스트로 검증한다." / "상태별 합계와 total의 일치 여부도 테스트한다." | self-check가 세 명령 각각에서 ON_HOLD 추가 전후 `counts["ON_HOLD"]`와 total이 1씩 늘고 상태별 합계가 total과 같은지, 출력 상태 줄이 counts와 같은지 검사한다. report_empty 출력도 검사한다 |
| S9 | "기존 6건의 task 상태는 변경하지 않는다." / "승인·상태 전이·감사 체인은 수정하지 않는다." / "task-0173에서 완료한 Hold/Resume 기능을 재설계하지 않는다." / "실제 Discord 전송 검증은 범위에서 제외한다." / "`jarvis.bat`, 기존 worktree, 임시 폴더를 보호한다." / "push는 별도 Owner 승인 전까지 금지한다." | 기존 6건, 승인·상태 전이·감사 체인, task-0173 Hold/Resume 코드(writer·Console)는 바꾸지 않았다(deny). 실제 Discord 전송은 하지 않는다. `jarvis.bat`·기존 worktree·임시 폴더를 건드리지 않고 push하지 않는다 |
| S10 | "먼저 현재 `main`과 `origin/main`이 동기화되어 있는지 확인한다." / "기존 task 등록 규칙과 SOP를 확인하고 task-0174를 공식 절차에 따라 등록한다." / "구현 전 변경 파일과 테스트 계획을 제시한다." / "공식 Console Start 승인 전에는 구현하지 않는다." | 등록 전 fetch 뒤 `main` = `origin/main` = `54cab64`를 확인했고, task-0172·0173 관례대로 `TODO` 기록으로 등록해 변경 파일과 검증 계획을 제시했다. 코드는 Start 뒤에만 바꿨다 |
| S11 | "승인 후 기존 SOP대로 self-review, preflight, Reviewer, QA, Console Complete를 진행한다." / "실제 검증 결과와 변경 범위를 보고한다." / "확인하지 않은 내용은 완료로 표현하지 않는다." / "먼저 task 등록과 구현 전 계획까지만 진행하고, 공식 Start 승인 전에는 코드를 수정하지 마." | Start 뒤 SOP 순서(사전 점검 → self-review 1회 → candidate → Reviewer → QA)를 따르고 실제 결과만 기록한다. Console Complete는 SOP §8과 승인된 계획("Owner의 Console Complete로 DONE")에 따라 Owner의 결정으로 남기고, 그 전까지 완료로 쓰지 않는다 |
| S12 | "task-0174 Console Start 승인한다, 계획대로 진행해" | Console Start Preview(TODO → DOING, `no_execution: true`) 확인 뒤 `START TASK`로 Confirm했다("구현 착수" 절). "계획대로"는 이 기록의 설계·범위·검증 계획·SOP 절차다 |
| S13 | "task-0174의 Reviewer/QA 이후 task 기록 정정 사항부터 확인해." / "candidate `ae2d992`와 결과 기록 checkpoint `844e9d4`의 차이를 확인해." / "정정된 `updated_at`과 self-review 시각이 실제 근거와 일치하는지 확인해." / "관련 SOP에서 Reviewer/QA 이후 기록 변경에 필요한 절차를 확인해." | "Repair 1" 절의 확인 결과 1~3: 차이는 이 기록뿐(`updated_at`, summary, 결과 절), 정정 시각은 파일·커밋 시각과 일치, SOP §4.5~4.8에 따라 기록 변경은 새 candidate가 필요 |
| S14 | "필요한 추가 검토가 있다면 승인된 절차와 예산 안에서 진행해." / "새 candidate가 필요하다면 그 candidate를 기준으로 검토해야 하며, 기존 PASS를 새 candidate의 PASS로 간주하지 마." | 정정을 repair 1(예산 1/1)로 세어 새 candidate를 만들고 Reviewer → QA를 처음부터 실행한다. `ae2d992`의 PASS는 완료 판정에 쓰지 않는다. 추가 수정이 필요하면 escalation한다 |
| S15 | "기록과 검증 결과가 일치하고 완료 요건을 충족하면 공식 Console Complete Preview를 제시해." / "Preview가 정확하고 SOP 요건이 충족되면 공식 `COMPLETE TASK` 절차를 진행해." / "불일치나 추가 승인이 필요한 사항이 있으면 완료 처리 전에 보고해." | 새 candidate의 Reviewer PASS·QA PASS와 SOP §8 대조가 끝난 뒤에만 Console Complete Preview를 확인하고, 정확하면 `COMPLETE TASK`로 Confirm한다. 이 지시가 S11에서 Owner 결정으로 남겨 둔 Complete를 맡긴다. 불일치나 추가 승인 사항이 있으면 Confirm하지 않고 보고한다 |
| S16 | "완료 후 DONE checkpoint와 task 상태를 확인하고, 기존 절차대로 master-plan의 최근 완료 목록을 별도 기록 커밋으로 갱신해." / "단, push는 하지 마." / "기존 6건, `jarvis.bat`, 보존 worktree에는 손대지 마." | Complete 뒤 DONE checkpoint와 status를 확인하고, master-plan 최근 완료 목록을 별도 기록 커밋으로 갱신한다. push하지 않고 기존 6건·`jarvis.bat`·보존 worktree를 건드리지 않는다 |

## 구현

| 파일 | 변경 |
| --- | --- |
| `adapters/discord/bot_minimal.py` | `task_file_writer` import에 `TASK_ALLOWED_STATUSES` 추가. `REPORT_STATUS_ORDER`에 `ON_HOLD`를 BLOCKED 바로 뒤에 추가. 새 `_status_count_lines(counts)`가 그 순서로 `- <STATUS>: <n>` 줄을 만들고 `report_empty`·`report`·`retro_today` 출력이 이를 쓴다. `_build_review_notes`·`_build_recommended_next_steps`에 ON_HOLD 분기. self-check: `_write_task`가 ON_HOLD 기록에 `hold_from`을 넣고, 새 검사 12개(`report_status_order_matches_vocabulary`, 세 명령의 `*_counts_on_hold`·`*_reply_status_lines`, `retro_today_on_hold_not_follow_up`, `report_empty_reply_status_lines`, `retro_today_on_hold_only_moves_forward`, `review_task_status_guidance`, `review_task_on_hold_command`) |
| `adapters/discord/README.md` | 출력 예시 3곳에 `- ON_HOLD: 0`을 BLOCKED 뒤에 추가, `/report today` 예시 머리말을 "📊 task report"로 정정 |
| `docs/status-report-contract.md` | §3.1 status 열거에 ON_HOLD, §4.1·§4.2 counts 예시에 `"ON_HOLD": 0`(BLOCKED 뒤) |

retro의 follow-up 조건과 `summary_line`, 승인·전이·실행·Worker·감사 함수는 바꾸지 않았다.

## Implementer 검증 (작업 트리 기준, candidate 전)

| # | 검사 | 결과 |
| --- | --- | --- |
| I1 | `bot_minimal.py --self-check-suite` | exit 0, `ok: true`, 검사 116개 전부 통과(새 12개 포함, self-review S1 반영 뒤 재실행) |
| I2 | discord-intake smoke | exit 0 |
| I3 | Console smoke | exit 0, "Jarvis Console smoke tests passed" |
| I4 | SOP validator | `status=PASS` |
| I5 | `git diff --check` | 통과 |
| I6 | 실제 저장소 `/report`(읽기 전용 호출) | total 126 = 상태별 합계 126, counts 키 7개, 출력 `- BLOCKED: 0` 다음 줄이 `- ON_HOLD: 0` |
| I7 | 보호 대상 | `jarvis.bat` untracked·무접촉, 기존 task 기록 무변경(`git status`에 없음), 보존 worktree 그대로 |

이 검증 뒤의 단계는 아래 절에 차례로 적는다.

## 사전 점검 (첫 실행)

`python -B scripts/check_task_record.py memory/tasks/task-0174-discord-report-on-hold-count.md --baseline 54cab64…`: `staged_files=4`, `violations=0`, `quote_check_unquoted=0`, `status=PASS`.

## Self-review (첫 candidate 전 1회)

2026-10-20 13:00~13:06 UTC에 `jarvis-self-review` 절차대로 1회 실행했다. 사전 점검 PASS, 작업 트리 = index(`git diff --name-only` 출력 없음), 이 절 없음을 확인했다. 요청 파일은 저장소 밖 scratchpad에 두고 저장소 루트에서 `claude -p --agent self-reviewer --tools Read,Grep,Glob --output-format json`으로 실행했다(`is_error: false`). 실행 전후 `git status --short`가 같았다. self-review는 Reviewer 판정이 아니며, 여기서 고친 것은 repair가 아니다(SOP §5).

| # | 지적(요지) | 처리 |
| --- | --- | --- |
| S1 | V6는 ON_HOLD task에 대한 `/review-task` 검사처럼 읽히지만 self-check는 두 builder 함수만 상태 문자열로 부른다 | 수정. 기존 ON_HOLD fixture(`task-0111-report-on-hold`)에 `_run_review_task`를 실행해 `review_notes`·`recommended_next_steps`와 출력에 새 안내가 나오는지 보는 `review_task_on_hold_command`를 추가했다. self-check 116개 전부 통과. 구현 표, I1, Manager 요약 S4를 갱신했다 |
| S2 | 첫 사전 점검 결과가 기록에 없다 | 수정. 위 "사전 점검 (첫 실행)" 절에 적었다 |

수정 뒤 사전 점검: `staged_files=4`, `violations=0`, `quote_check_unquoted=0`, `status=PASS`.

## Candidate 1

`ae2d992c244c16b2ef2291f465624b3384db27eb`(parent = baseline `54cab64`, 커밋 2026-10-20 13:01 UTC). 변경 4개 파일 = owned. 커밋 전 사전 점검 PASS, HEAD = candidate, stage 없음, `jarvis.bat`은 tree에 없음.

## Reviewer 1 (`ae2d992`, PASS)

`findings: []`, `self_deviations: []`. 변경 집합 `54cab64..ae2d992` 4개 파일을 검토했다. `unverified` 6건(self-check·smoke·validator 실행, 변형 검사, 실제 `/report`, 보존 대상, 절차 사실)은 아래 QA로 넘겼다.

## QA (candidate `ae2d992c244c16b2ef2291f465624b3384db27eb`)

candidate를 detached로 checkout한 임시 worktree(scratchpad, 저장소 밖)에서만 실행했다. 끝나고 삭제했고 원본 checkout의 HEAD는 candidate 그대로다.

| # | 검사 | 결과 |
| --- | --- | --- |
| V1~V6 | `bot_minimal.py --self-check-suite` | exit 0, `ok: true`, 116개 전부 통과. 새 검사 12개가 모두 있음 |
| V7 | discord-intake smoke, Console smoke, SOP validator, `check_task_record.py`, `git diff --check 54cab64 ae2d992` | 모두 PASS |
| V8 | 변형이 self-check 실패로 드러나는지 | 모두 exit 1: `REPORT_STATUS_ORDER`에서 ON_HOLD 제거(가드·세 집계·retro·review 검사 실패), report_empty 출력을 옛 6줄 하드코딩으로 되돌림(`report_empty_reply_status_lines`), retro follow-up에 ON_HOLD 추가(`retro_today_on_hold_not_follow_up` 외 1), ON_HOLD review 안내 제거(`review_task_status_guidance`, `review_task_on_hold_command`). 계획의 "가드 제거"는 가드를 빼도 다른 검사가 실패할 이유가 없어 의미가 없으므로, 대신 공식 어휘 밖 상태(`PAUSED`)를 목록에 넣는 변형을 썼다. 이 변형은 `report_status_order_matches_vocabulary`와 `review_task_status_guidance`가 잡았다(가드만 잡을 것이라는 실행 전 예상은 틀렸다) |
| I6 | QA worktree에서 `/report` | total 126 = 상태별 합계 126, 키 7개, `- BLOCKED: 0` 다음 `- ON_HOLD: 0` |
| V9 | 보존 | 보류 6건과 task-0035 blob이 baseline·candidate 모두 0030 `5bae2580d369`, 0031 `5d7dbb80335c`, 0032 `ede13b3278fe`, 0033 `999c8e29a6b3`, 0034 `d22b5656479e`, 0036 `d11c6ce0bd55`, 0035 `d494ed175848`. `jarvis.bat`은 tree에 없고 untracked. 변경 파일 = owned 4개. 보존 worktree 그대로, listener 없음 |

## 정정 (candidate 기록의 시각)

candidate `ae2d992`의 이 기록에 적은 두 시각은 실제 시각을 확인하지 않고 쓴 값이었다. 위의 원래 문장은 이력으로 그대로 두고 여기서 정정한다.

- `updated_at` 13:08 UTC: candidate 커밋(13:01 UTC)보다 늦은 시각이었다. 이 checkpoint에서 실제 시각 13:04 UTC로 고쳤다.
- Self-review 절의 "13:00~13:06 UTC": 실제로는 요청 파일 작성 12:59:27 UTC, 결과 파일 13:00:31 UTC(scratchpad 파일 시각)다.

정정은 시각 사실만 바꾸며 코드·문서·검증 결과와 무관하다. Reviewer와 QA가 본 candidate 뒤의 기록 변경이므로 Owner에게 보고한다.

## Docs와 완료 조건 대조

- Docs: `not_required`. 문서 변경(README, status-report-contract)은 candidate 안에 있고 Reviewer·QA가 검토했다. master-plan 최근 완료 갱신은 DONE 뒤 관례적인 별도 기록이며 이 task 범위 밖이다.
- SOP §8: 같은 candidate `ae2d992`에 Reviewer PASS와 QA PASS. 범위 밖 변경·동시 source writer 없음(변경 4개 = owned). `jarvis.bat` untouched/untracked. push·외부 호출·실제 Discord 전송 없음. listener·임시 worktree 남지 않음.
- budget: `retry_count=0`, `repair_count=0`(이 절 작성 시점). 아래 "Repair 1"에서 1로 바뀌었다.

## 다음 단계

(이 절은 checkpoint `844e9d4` 시점의 계획이다. 아래 "Repair 1"이 이를 대신한다.)

## Owner 지시: 정정 확인 (원문)

```text
task-0174의 Reviewer/QA 이후 task 기록 정정 사항부터 확인해.

1. candidate `ae2d992`와 결과 기록 checkpoint `844e9d4`의 차이를 확인해.
2. 정정된 `updated_at`과 self-review 시각이 실제 근거와 일치하는지 확인해.
3. 관련 SOP에서 Reviewer/QA 이후 기록 변경에 필요한 절차를 확인해.
4. 필요한 추가 검토가 있다면 승인된 절차와 예산 안에서 진행해. 새 candidate가 필요하다면 그 candidate를 기준으로 검토해야 하며, 기존 PASS를 새 candidate의 PASS로 간주하지 마.
5. 기록과 검증 결과가 일치하고 완료 요건을 충족하면 공식 Console Complete Preview를 제시해.

Preview가 정확하고 SOP 요건이 충족되면 공식 `COMPLETE TASK` 절차를 진행해. 불일치나 추가 승인이 필요한 사항이 있으면 완료 처리 전에 보고해.
완료 후 DONE checkpoint와 task 상태를 확인하고, 기존 절차대로 master-plan의 최근 완료 목록을 별도 기록 커밋으로 갱신해. 단, push는 하지 마. 기존 6건, `jarvis.bat`, 보존 worktree에는 손대지 마.
```

## Repair 1 (Reviewer·QA 뒤 기록 정정)

확인 결과:

1. `ae2d992..844e9d4` 차이는 이 기록 1개뿐이다(41줄 추가, 2줄 변경). 바뀐 줄은 `updated_at`(13:08 → 13:04)과 summary 메타데이터이고, 나머지는 Candidate 1·Reviewer 1·QA·정정·Docs·다음 단계 절 추가다. 코드·문서 파일은 같다.
2. 정정한 시각은 근거와 맞는다. self-review 요청 파일 12:59:27 UTC, 결과 파일 13:00:31 UTC(결과 JSON `duration_ms` 57719), `ae2d992` 커밋 13:01:18 UTC, `844e9d4` 커밋 13:05:12 UTC로, `updated_at` 13:04는 그 checkpoint 커밋보다 이르다.
3. SOP §4: tracked file이 바뀌는 repair·Docs sync는 새 candidate를 만들고(5), candidate가 바뀌면 이전 Reviewer/QA 결과는 전부 무효이며(6), 새 candidate는 fresh Reviewer → fresh QA를 통과해야 하고(7), Manager는 final HEAD와 검토된 hash가 같은지 대조한다(8). `844e9d4`는 결과만 덧붙인 것이 아니라 Reviewer가 본 메타데이터(`updated_at`, summary)를 고쳤다.

Manager 판정: 이 정정을 Reviewer가 보지 않은 기록 변경으로 보고, 이 기록의 현재 내용으로 새 candidate를 만든다. SOP §5의 repair 정의는 "Reviewer finding 또는 QA 실패를 해결하기 위해 tracked source를 바꾸는 correction"이라 이 경우와 정확히 맞지 않지만, 예산을 우회하지 않도록 repair 1로 센다(`repair_count` 0→1, 예산 소진). `ae2d992`의 Reviewer·QA PASS는 완료 판정에 쓰지 않는다. 새 candidate에 Reviewer → QA를 처음부터 실행하고, 수정이 필요한 지적이나 QA 실패가 나오면 예산이 없으므로 고치지 않고 Director를 거쳐 Owner에게 escalation한다.

이 repair가 바꾸는 것은 이 기록뿐이다: summary, 기준선 budget 행, Docs 대조 절의 budget 문장, `844e9d4` 시점의 다음 단계 문장, 위 Owner 지시 원문과 이 절, updated_at. 코드·문서 파일은 `ae2d992`와 같다.
