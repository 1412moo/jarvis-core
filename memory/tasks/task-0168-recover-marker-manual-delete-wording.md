# task-0168-recover-marker-manual-delete-wording

- id: `task-0168-recover-marker-manual-delete-wording`
- title: `task-0167 후속: 보존된 invalid 실행 표지를 수동 삭제한 뒤 recover 결과 서술 정정(문서·주석만)`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-19 06:22 UTC`
- updated_at: `2026-10-19 07:02 UTC`
- summary: `task-0167 Reviewer minor(429d5c8, Owner가 SOP §8로 수용하며 후속 정정을 조건으로 둠)를 고친다. 보존된 invalid 표지를 Owner가 직접 지우면 recover를 다시 쓸 수 있다는 세 서술(claude_worker.py 주석, SOP §10.2 13항, task-0167 기록 "운영상 결과")을 실제 동작에 맞춘다. 동작 변경 없음, push 없음. candidate `beb2b92`에 Reviewer minor 1건(Owner §8 수용), QA PASS. DONE은 Owner Console Complete 대기.`
- source_command: `task-0167 Reviewer minor 수용 조건(SOP §8)에 따른 후속 정정, Director 세션 요청`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `70e440f5c184a0e2f3fc57ce4edf2e70f31066c5` (main HEAD, origin/main `4416b04`보다 5 commit 앞섬, push 안 함) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat`, `memory/tasks/task-0166-studyroom-glossary-r1-1.md`(보존, 건드리지 않음) |
| 선행 task | task-0167 (`DOING`, QA PASS on `429d5c8`; DONE·master-plan·push는 별도 Owner 승인 대기) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (기본값) |

## 조사 결과 (read-only, 등록 전 확인)

1. `worker_marker_state`(`orchestrator/worker/claude_worker.py`)는 어느 attempt든 읽을 수 없는 표지가 있으면 `invalid`, 그렇지 않으면 마지막 attempt의 표지만 본다. 마지막 attempt에 표지가 없으면 `missing`이다(`latest not in markers`).
2. `_run_recover`(`adapters/discord/bot_minimal.py`)는 `missing`을 `recover_worker_marker_missing`, `invalid`를 `recover_worker_marker_invalid`로 거절한다. `gone`만 진행한다.
3. 따라서 보존된 invalid 표지가 마지막 attempt 자신의 것이면, Owner가 지운 뒤에도 recover는 `recover_worker_marker_missing`으로 거절되고 거절 사유만 바뀐다. 수동 삭제 뒤 recover가 다시 되는 것은 그 표지가 더 이전 attempt의 것이고 더 새 attempt가 자기 표지(프로세스 모두 종료)를 남긴 채 멈춘 경우뿐이다.

## Owner 승인 (원문)

```text
Owner 승인: task-0168을 기록된 범위대로 Start한다(문서·주석만, 동작 변경 없음, push 없음).
```

2026-10-19 06:54 UTC `TODO → DOING`.

## 범위

| 파일 | 변경 |
| --- | --- |
| `orchestrator/worker/claude_worker.py` | `EARLIER_UNREADABLE_KEY` 위 주석만 정정(코드 변경 없음) |
| `docs/jarvis-multi-agent-sop-v0.1.md` | §10.2 13항의 "Owner가 확인하고 그 표지를 직접 지울 때까지" 문장 정정 |
| `memory/tasks/task-0167-stalled-doing-detection-and-owner-recover.md` | "Repair 3" 절 "운영상 결과" 문단은 고쳐 쓰지 않고 날짜를 단 정정 주석만 덧붙임(history) |
| 이 기록 | 진행·검증·Reviewer·QA 결과 |

비범위: 동작·테스트 변경, task-0167 상태 전환(DONE)·master-plan·push, `jarvis.bat`·`.env`·`docs/master-plan.md`·task-0166 기록과 그 worktree.

## 완료 기준

- 세 서술이 위 조사 결과 3과 일치한다.
- `python -B scripts/validate_multi_agent_sop.py` 통과.
- SOP 흐름대로 exact candidate commit에 Reviewer → QA.
- push하지 않는다.

## 구현 (candidate `beb2b92063b053b8f39fa1d13502730cc51441c2`)

| 파일 | 변경 |
| --- | --- |
| `orchestrator/worker/claude_worker.py` | `EARLIER_UNREADABLE_KEY` 위 주석: 보존된 동안 invalid로 거절, 수동 삭제만으로는 진행되지 않으며 마지막 attempt의 표지였다면 missing으로 거절, 더 새 attempt의 자기 표지만 진행을 허용 |
| `docs/jarvis-multi-agent-sop-v0.1.md` | §10.2 13항 같은 내용으로 정정 |
| `memory/tasks/task-0167-stalled-doing-detection-and-owner-recover.md` | "운영상 결과" 문단 뒤 `정정(2026-10-19, task-0168)` 주석 추가. 기존 줄 삭제 0 |
| 이 기록 | 신규 |

Implementer 검증: `python -B scripts/validate_multi_agent_sop.py` → `status=PASS`(negative_failures=0), `py_compile` 통과.

## Reviewer

1차 호출은 Manager 요약에 `=== OWNER APPROVAL (verbatim) ===` 표지 줄이 없어 `BLOCKED`(검토 없음). 입력만 고친 재실행으로 `retry_count=1`(source 변경 없음).

2차 결과 `FINDINGS`, minor 1건: Manager 요약에 승인 조건 "push 없음"이 빠졌다(이 기록 완료 기준에는 있음). 세 서술과 `worker_marker_state`·`_run_recover`의 일치, 주석·문서만 바뀐 diff, 범위 밖 변경 없음, 기록 형식에는 지적이 없었다.

Owner 수용 원문:

```text
Owner 수용(SOP §8, candidate beb2b92 한정): Reviewer minor(Manager 요약에 'push 없음' 누락)를 수용한다. task-0168 기록에 이미 push 금지가 있고 candidate 내용 결함이 아니다. 같은 candidate로 QA를 진행한다.
```

이 수용은 candidate `beb2b92`에만 효력이 있다.

## QA (candidate `beb2b92`)

2026-10-19, `.env`·`jarvis.bat`이 없는 새 local clone(scratchpad, 확인 뒤 삭제)에서 candidate를 체크아웃(작업 트리 변경 0)해 실행했다. 비교 기준 `70e440f`. 문서·주석만 바뀐 작업이므로 smoke test 대신 동작 불변을 AST로 확인했다.

| 검사 | 결과 |
| --- | --- |
| 변경 파일 | 범위의 4개뿐(M 3, A 1) |
| `claude_worker.py` 주석 아닌 변경 줄 | 0 |
| `claude_worker.py` AST 기준선과 동일 | `True` |
| `python -B scripts/validate_multi_agent_sop.py` | `status=PASS` |
| 세 서술 존재(주석 280-282행, SOP 371행, task-0167 390행 정정 주석) | 확인 |
| task-0167 기록 기존 줄 삭제 | 0 |
| push 없음 | `origin/main` = `4416b04` 그대로 |
| `jarvis.bat`·task-0166 기록 | untracked 그대로 |

결과: PASS. Docs: `not_required`(이 작업 자체가 문서 정정).

## 남은 일

- DONE: Owner Console Complete로 결정(Manager는 바꾸지 않음).
- push: 별도 Owner 승인. task-0167과 함께 처리 여부는 Owner 결정.
