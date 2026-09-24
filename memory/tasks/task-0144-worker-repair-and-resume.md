# task-0144-worker-repair-and-resume

- id: `task-0144-worker-repair-and-resume`
- title: `Jarvis v0.2 Worker 파이프라인에 Reviewer FINDINGS 자동 repair 1회와 /go resume 추가`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-09-24 14:02 UTC`
- updated_at: `2026-09-24 14:15 UTC`
- summary: `task-0142 Worker 파이프라인은 Reviewer FINDINGS에서 바로 FAILED가 되고 재시도는 매번 main에서 처음부터 다시 작성했다. Reviewer FINDINGS가 나오면 같은 candidate worktree에서 Worker가 지적만 고쳐 repair candidate를 만들고 fresh Reviewer와 QA를 다시 거치는 자동 repair를 최대 1회(SOP repair_budget 기본값) 추가하고, /go <task-id> resume으로 이전 실패 시도의 허용 경로 변경을 현재 main 위 새 시도에 재적용해 이어가게 한다. DONE은 Reviewer/QA 후 Owner가 Console Complete로 결정한다.`
- source_command: `Owner 지시: Worker 파이프라인 Reviewer FINDINGS → repair 1회 → 재검증과 /go resume을 task-0144로 구현`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `2a33b109d76300a5eb4c7259e20beeef2108fe42` (main HEAD, push 전) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat`, `memory/tasks/task-0143-…md` |
| 보존 대상 | task-0143 첫 시도 `a02dde9`, r2 candidate `6eec227`과 r2 worktree의 미커밋 수정(`glossary.json` git-worktree `jarvis_example`) |

## Owner 결정 (원문)

```text
세 가지 모두 다음과 같이 결정해.

1. 자동 repair budget = 1회
- Reviewer FINDINGS → 최대 1회 자동 repair → fresh Reviewer → QA
- 다시 FINDINGS면 FAILED + Owner escalation
- 무한 repair 금지

2. resume은 명시적으로 `/go <task-id> resume`
- 기존 `/go <task-id>` 동작은 유지
- resume일 때만 이전 실패 시도의 변경을 현재 main 위에 재적용
- 이전 worktree/branch는 보존
- baseline은 현재 main으로 새로 잡음

3. 새 기능은 task-0144로 기록

구현 전에 task-0144 범위와 최소 변경 계획을 확정하고 진행해.

중요:
- task-0143 r2 candidate `6eec227`과 worktree는 그대로 보존
- 현재 r2의 미커밋 수정도 보존
- task-0143 자체를 수동 commit하거나 main에 반영하지 말 것
- push 금지
- jarvis.bat 접근/수정/스테이징 금지
- 기존 TODO/DOING/DONE/FAILED 계약 유지
- 기존 Reviewer SOP와 repair_budget 의미를 최대한 재사용
- 구현 → smoke/integration test → Reviewer → QA → checkpoint commit 순서
- 마지막에 변경 내용, 테스트, commit hash만 간결하게 보고
```

## 확정한 범위와 최소 변경 계획

| 파일 | 변경 |
| --- | --- |
| `orchestrator/worker/claude_worker.py` | 자동 repair 루프(`REPAIR_BUDGET=1`), repair Worker 프롬프트(원래 요청 + Reviewer 지적 전문 + 지적만 고칠 것), repair candidate는 같은 브랜치에 이전 candidate를 parent로 commit, Reviewer 호출문에 Parent=이전 candidate와 이전 Reviewer 결과 무효 명시, 범위 검사·QA를 baseline..candidate 누적 기준으로, `resume` 진입(직전 시도의 허용 경로 변경을 현재 main 위 새 시도에 재적용, 같은 파일이 main에서 바뀌었으면 거절) |
| `adapters/discord/bot_minimal.py` | `/go <task-id> resume`(FAILED task만), 보고에 repair 횟수와 candidate 목록, 예산 소진 시 Owner 결정 필요 안내. `/go <task-id>` 기존 동작 유지 |
| `orchestrator/worker/run_smoke_tests.py` | FINDINGS→repair→PASS, FINDINGS→repair→FINDINGS→FAILED, repair 중 범위 위반, repair 프롬프트에 지적 전달, resume PASS(미커밋 수정 포함·Worker 미호출), resume 대상 없음, resume 충돌, 이전 시도 보존 |
| 이 기록 | 신규 |

유지: 전환 계약(TODO/DOING/DONE/FAILED 쌍), task 기록 방식, 감사 hook 위치(/go source 감사 거부 문제는 별도 이슈로 미수정), Owner 전용 게이트, 허용 경로 `apps/studyroom/content/`, push 금지, `jarvis.bat` 금지.

## 검증 (Implementer 실행, QA 재현 대상)

| # | 항목 | 결과 |
| --- | --- | --- |
| V1 | `python -B orchestrator/worker/run_smoke_tests.py` | 112/112 PASS (기존 74 + repair·resume 38, repair 1 후) |
| V2 | `python -B adapters/discord/bot_minimal.py --self-check-suite` (UTF-8 모드) | 92/92 ok |
| V3 | `orchestrator/discord-intake`, `orchestrator/audit-chain`, `apps/studyroom` smoke | 모두 PASS |
| V4 | `git diff --check` | exit 0 |
| V5 | task-0143 보존 | `a02dde9`, r2 `6eec227`, r2 worktree 미커밋 수정 그대로 |

구현 중 smoke가 잡은 결함: resume이 방금 만든 새 시도를 "직전 시도"로 골라 `resume_no_changes`가 되던 문제를 현재 시도보다 앞선 시도만 고르도록 고쳤다.

## Repair 이력

retry_budget=1, retry_count=0, repair_budget=1, repair_count=1

| # | 원인 | 조치 |
| --- | --- | --- |
| 1 | Reviewer FINDINGS (candidate `89686fb5f6309d94b1806f7f837e4b4324a67cb2`): major 1 — FINDINGS가 아닌 BLOCKED·UNKNOWN 판정도 자동 repair를 시작함. minor — 환경변수로 repair 예산을 1보다 크게 올릴 수 있음, 거절된 resume이 빈 시도를 남겨 다음 resume이 그것을 고름, Manager 요약이 checkpoint commit 시점을 밝히지 않음, 테스트·보존 주장은 QA 재현 대상 | FINDINGS일 때만 repair하고 다른 비PASS 판정은 즉시 실패, 예산을 최대 1로 제한(REPAIR_BUDGET_MAX), resume 검사를 새 worktree 생성 전으로 이동, smoke에 BLOCKED·UNKNOWN·예산 상한·거절된 resume 무흔적 검증 추가. checkpoint commit은 QA 후 이 기록의 QA 결과를 남기는 commit이다. 새 candidate에 fresh Reviewer → QA |
