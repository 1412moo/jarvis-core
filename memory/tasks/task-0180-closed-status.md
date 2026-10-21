# task-0180-closed-status

- id: `task-0180-closed-status`
- title: `CLOSED 상태와 Console Close 구현`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-21 10:28 UTC`
- updated_at: `2026-10-21 10:55 UTC`
- summary: `task-0178 설계 C안대로 새 종결 상태 CLOSED와 closed_reason을 구현한다. DOING에서 CLOSED로 가는 전이 하나만 열고, 수동 task(source_command가 /task가 아닌 task)만 대상으로 하며, 사유는 completion_evidence와 같은 형식 규칙으로 상태와 함께 원자적으로 쓴다. 경로는 Console Close(Preview 뒤 CLOSE TASK Confirm)뿐이고 Discord 종료 명령은 두지 않는다. CLOSED는 되돌리지 않는다. 이 task는 어떤 기존 task도 닫지 않는다. task-0175·0031을 닫을지는 구현 뒤 Owner가 정한다.`
- source_command: `Owner 지시: task-0180 등록하고 Start (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `4b7cb20ce3c60b35fe245ca567f1fe76ed6020e8` (등록 시점 main HEAD) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |
| 설계 | `docs/task-0178-manual-task-close-design.md` §4 추천안 C, §5 영향 범위, §7 테스트 계획 |

## Owner 결정 (원문)

```text
[Manager 제안]
다음: 2번 작업(CLOSED 상태 구현, task-0180)
task-0178 설계대로 하면 범위가 task 상태 기준 영역 전체에 걸칩니다. 바뀌는 파일은 다음과 같습니다.
- orchestrator/discord-intake/task_file_writer.py: 상태와 전이 추가, closed_reason
- apps/jarvis-console/run_web_app.py: Console의 CLOSE TASK
- adapters/discord/bot_minimal.py: 보고 집계에 CLOSED 추가
- docs/task-model.md
- scripts/validate_multi_agent_sop.py
이 범위로 task-0180을 등록하고 Start해도 될지 승인해 주세요. 승인하시면 바로 시작합니다. task-0175와 task-0031을 실제로 닫는 일은 구현이 끝난 뒤 따로 결정을 받겠습니다.

[Owner 답]
task-0180 등록하고 Start해
```

## Owner 결정 2: 상태 목록 문서 범위 (원문)

```text
[Manager 질문]
결정할 것: 범위 밖에 남은 상태 목록 5곳
- memory/tasks/task-template.md: 새 task 양식의 status 허용값 줄
- memory/README.md: 상태 허용값 목록
- reports/README.md: 상태 정의. task-model §2가 "이 정의를 재사용한다"고 적고 있습니다.
- reports/templates/task-report-template.md: 상태 목록
- SOP §8: DONE이 아닌 종결(CLOSED)도 있다는 한 문장. 설계 §5가 든 곳이고, 에이전트 행동 규칙 영역이라 무게가 다릅니다.
1. (권장) 앞의 4곳은 상태 목록에 CLOSED 한 줄씩만 더하는 것이라 이번 범위에 넣습니다. SOP §8은 규칙 문서라 빼고 별도 task로 다룹니다.
2. 5곳 모두 이번 범위에 넣습니다.
3. 모두 빼고, 어긋남을 기록한 뒤 별도 task로 고칩니다.

[Owner 답]
1로 진행
```

## 범위

Manager 제안의 다섯 파일과, 그 다섯 곳을 바꾸면 함께 바꿔야 하는 그 파일들의 짝(같은 기능의 화면·테스트·안내 문서)이다.

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/discord-intake/task_file_writer.py`, `orchestrator/discord-intake/run_smoke_tests.py`, `apps/jarvis-console/run_web_app.py`, `apps/jarvis-console/web/app.js`, `apps/jarvis-console/web/index.html`, `apps/jarvis-console/web/styles.css`, `apps/jarvis-console/run_smoke_tests.py`, `apps/jarvis-console/README.md`, `adapters/discord/bot_minimal.py`, `adapters/discord/README.md`, `docs/task-model.md`, `docs/status-report-contract.md`, `scripts/validate_multi_agent_sop.py`, `memory/tasks/task-0180-closed-status.md`, Owner 결정 2로 더한 `memory/tasks/task-template.md`, `memory/README.md`, `reports/README.md`, `reports/templates/task-report-template.md`(네 곳 모두 상태 목록·정의에 CLOSED만 더함) |
| deny | `jarvis.bat`, SOP(§8 포함, Owner 결정 2로 별도 task)·AGENTS·agent 정의, 다른 task 기록(어떤 task도 닫지 않음), 감사 체인 코드(`orchestrator/audit-chain/`), Worker 코드, 보호 worktree |

짝 파일 가운데 실제로 바꿀 필요가 없는 것은 바꾸지 않는다. 처음에는 설계 §5가 든 SOP §8 문장과 상태 목록을 적은 다른 문서를 제안 목록 밖이라 넣지 않았고, 구현 중 Owner에게 물어 Owner 결정 2로 상태 목록 문서 4곳만 넣었다.

## 계획

1. writer: `CLOSED`를 허용 상태에 넣고 `DOING → CLOSED` 전이를 더한다. 일반 전이 writer는 이 쌍을 거부하고, 전용 Close writer가 수동 task에만 상태와 `closed_reason`을 원자적으로 쓴다. 사유 형식은 `completion_evidence`와 같다.
2. Console: Close Preview/Confirm API(`CLOSE TASK`), 화면 버튼, Task View `Closed` 그룹(Completed 뒤)과 상태 규칙.
3. Discord: `REPORT_STATUS_ORDER`에 `CLOSED`, `/review-task` 안내. `/go`·`/go accept`·`/go recover`가 `CLOSED`를 거부하는 테스트를 더한다(`/run`·`/retry`는 task-0179에서 폐기).
4. 문서: task-model §2·§3·§5-1·§5-2와 `closed_reason` 절, status-report 계약, Console·Discord README.
5. validator: 전이 표 일치 검사가 새 쌍을 잡는지 확인하고, 필요하면 `closed_reason` 규칙 검사를 더한다.
6. 사전 점검 → self-review → candidate → Reviewer → QA(writer smoke, Console smoke, Discord self-check, Worker smoke, validator) → Evidence·Complete(Manager, G3와 같게) → checkpoint. push는 별도 승인.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-21 10:28 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다.

## 구현

- `orchestrator/discord-intake/task_file_writer.py`: `CLOSED`를 허용 상태에, `closed_reason`을 허용 메타데이터에, `DOING → CLOSED`를 전이 표에 더했다(`TASK_CLOSE_TRANSITIONS`). 헤더 검증은 `closed_reason`이 `CLOSED`일 때만, `completion_evidence` 형식 규칙으로 있어야 한다고 본다. 일반 전이 writer와 실행 결과 writer는 이 쌍을 `close_transition_requires_close_writer`로 거부한다. 새 `close_task_file`은 DOING이고 `source_command`가 `/task`가 아닌 task만 받아(`close_requires_manual_task`) status 줄 바로 뒤에 `closed_reason`을 넣고 `updated_at`과 함께 한 번에 원자적으로 바꾼다. 결과를 다시 검증한 뒤에만 쓰고, 실패하면 원본 그대로다.
- `apps/jarvis-console/run_web_app.py`: Close 동작(`TASK_CLOSE_ACTIONS`, `CLOSE TASK`). Preview는 Close일 때만 `closed_reason`을 받아 evidence 규칙으로 정규화하고, Worker 경로 task는 409 `close_requires_manual_task`, Preview에 안내·경고·`reversible: false`를 싣는다. Confirm은 Close writer를 부르고 receipt에 사유를 넣는다. Task View에 `Closed` 그룹(Completed 뒤, 순위 70)과 상태 규칙, view에 `closed_reason`·`source_command`를 더했다.
- `apps/jarvis-console/web/app.js`: 수동 DOING task에만 사유 입력칸과 Close 버튼, Confirm Close 표시, Preview·receipt·카드의 사유 표시, Closed 그룹과 안내 문구.
- `apps/jarvis-console/run_smoke_tests.py`: 새 `_test_task_close`(writer 바이트 단위 성공·LF·거부 상태·Worker 경로·잘못된 사유·stale, 파서 일치, Console Preview/Confirm·잘못된 문구·재사용 토큰·닫힌 뒤 모든 동작 거부, 화면 소스). 기존 검사의 상태 목록·전이 수(10 → 11)·view 키·선택 범위 fixture를 새 상태에 맞췄다(선택 범위의 바깥 기록은 가장 낮은 순위가 된 CLOSED로 바꿈).
- `adapters/discord/bot_minimal.py`: `REPORT_STATUS_ORDER` 끝에 `CLOSED`, `/review-task` 안내. self-check 4개를 더했다(`/report` 집계, `/retro today` follow-up 아님, `/review-task`, `/go`·accept·recover·resume 거부와 파일 무변경).
- `scripts/validate_multi_agent_sop.py`: task-model §3 상태 목록과 writer `TASK_ALLOWED_STATUSES`의 일치 검사(`status_vocabulary_parity`)와 음성 테스트 2개.
- 문서: task-model §2·§3·§5-1·§5-2·§6·새 §13, status-report 계약, Console·Discord README, Owner 결정 2의 네 곳.
- 바꾸지 않은 owned 파일: `orchestrator/discord-intake/run_smoke_tests.py`(저장소 기록 검증이 새 규칙을 그대로 씀), `apps/jarvis-console/web/index.html`, `apps/jarvis-console/web/styles.css`.

## Implementer 검증 (작업 트리)

- Discord self-check suite: ok, checks 108(이전 104에 CLOSED 검사 4개).
- Console smoke 통과(self-review 뒤 Close 토큰 만료 검사를 더함). `_test_task_close`가 Worker 경로 판정과 Close 허용 상태를 일부러 바꾼 두 변형을 잡는 것을 확인했다.
- Worker smoke total=494 failed=0, discord-nl-intent smoke 35건 통과, discord-intake smoke 통과, SOP validator PASS(negative_checks 172), `git diff --check` 통과, `node --check app.js` 통과.
- 사전 점검(`check_task_record`, baseline `4b7cb20`): status=PASS, violations 0, 경고 3건. 경고 3건은 구현 절의 "바꾸지 않은 owned 파일" 세 개와 같다.

## Self-review

candidate 전 1회(읽기 전용 self-reviewer). minor 4건을 모두 candidate 전에 고쳤다: 템플릿에 더했던 `closed_reason` 안내 문장과 task-model §6의 괄호 문장(둘 다 승인 범위 밖)을 지웠고, A1에 설계와 다른 점을 모두 적었으며, Close 토큰 만료 검사를 `_test_task_close`에 더하고, 사전 점검 결과를 위에 적었다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 제안]" / "다음: 2번 작업(CLOSED 상태 구현, task-0180)" / "task-0178 설계대로 하면 범위가 task 상태 기준 영역 전체에 걸칩니다. 바뀌는 파일은 다음과 같습니다." | task-0178 설계 C안(§4)을 구현했다. 설계와 다른 점: (1) 설계 §5가 든 SOP §8 문장은 Owner 결정 2로 별도 task로 넘겼다(A5). (2) 설계 §6·§7의 `/run`·`/retry` 거부 테스트는 두 명령이 task-0179에서 폐기돼 대상이 없어, 대신 `/go resume` 거부를 함께 고정했다. (3) 설계 §5의 validator 항목은 기존 전이 표 일치 검사가 새 쌍을 잡는 것을 확인하고, `closed_reason` 규칙 검사 대신 상태 어휘 일치 검사(`status_vocabulary_parity`)를 더했다. `closed_reason` 규칙은 writer와 Console 파서가 검사하고 Console smoke가 고정한다 |
| A2 | Owner 결정 (원문) | "- orchestrator/discord-intake/task_file_writer.py: 상태와 전이 추가, closed_reason" / "- apps/jarvis-console/run_web_app.py: Console의 CLOSE TASK" / "- adapters/discord/bot_minimal.py: 보고 집계에 CLOSED 추가" / "- docs/task-model.md" / "- scripts/validate_multi_agent_sop.py" | 다섯 파일 모두 바꿨다. 각 파일의 짝(Console 화면·smoke, README, status-report 계약)도 범위 절의 설명대로 바꿨다. 어느 쪽도 다른 task 기록이나 Worker·감사 코드는 건드리지 않았다 |
| A3 | Owner 결정 (원문) | "이 범위로 task-0180을 등록하고 Start해도 될지 승인해 주세요. 승인하시면 바로 시작합니다. task-0175와 task-0031을 실제로 닫는 일은 구현이 끝난 뒤 따로 결정을 받겠습니다." / "[Owner 답]" / "task-0180 등록하고 Start해" | 등록하고 Console로 Start했다. task-0175·0031을 포함해 어떤 task도 닫지 않았고, 닫을지는 구현 뒤 따로 묻는다 |
| A4 | Owner 결정 2: 상태 목록 문서 범위 (원문) | "[Manager 질문]" / "결정할 것: 범위 밖에 남은 상태 목록 5곳" / "- memory/tasks/task-template.md: 새 task 양식의 status 허용값 줄" / "- memory/README.md: 상태 허용값 목록" / "- reports/README.md: 상태 정의. task-model §2가 "이 정의를 재사용한다"고 적고 있습니다." / "- reports/templates/task-report-template.md: 상태 목록" | 네 문서에 CLOSED만 더했다. `reports/README.md`는 정의 한 줄, `memory/tasks/task-template.md`·`memory/README.md`는 목록과 개수(7 → 8), `reports/templates/task-report-template.md`는 목록만이다. 다른 문장은 더하지 않았다 |
| A5 | Owner 결정 2: 상태 목록 문서 범위 (원문) | "- SOP §8: DONE이 아닌 종결(CLOSED)도 있다는 한 문장. 설계 §5가 든 곳이고, 에이전트 행동 규칙 영역이라 무게가 다릅니다." / "1. (권장) 앞의 4곳은 상태 목록에 CLOSED 한 줄씩만 더하는 것이라 이번 범위에 넣습니다. SOP §8은 규칙 문서라 빼고 별도 task로 다룹니다." | SOP는 바꾸지 않았다. SOP §8 문장은 별도 task 후보로 남는다 |
| A6 | Owner 결정 2: 상태 목록 문서 범위 (원문) | "2. 5곳 모두 이번 범위에 넣습니다." / "3. 모두 빼고, 어긋남을 기록한 뒤 별도 task로 고칩니다." / "[Owner 답]" / "1로 진행" | Owner가 2·3이 아닌 선택지 1을 골랐다 |
