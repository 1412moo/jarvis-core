# task-0168-recover-marker-manual-delete-wording

- id: `task-0168-recover-marker-manual-delete-wording`
- title: `task-0167 후속: 보존된 invalid 실행 표지를 수동 삭제한 뒤 recover 결과 서술 정정(문서·주석만)`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-19 06:22 UTC`
- updated_at: `2026-10-19 06:54 UTC`
- summary: `task-0167 Reviewer minor(429d5c8, Owner가 SOP §8로 수용하며 후속 정정을 조건으로 둠)를 고친다. 보존된 invalid 표지를 Owner가 직접 지우면 recover를 다시 쓸 수 있다는 세 서술(claude_worker.py 주석, SOP §10.2 13항, task-0167 기록 "운영상 결과")을 실제 동작에 맞춘다. 동작 변경 없음, push 없음. Owner 승인으로 Start(DOING).`
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
