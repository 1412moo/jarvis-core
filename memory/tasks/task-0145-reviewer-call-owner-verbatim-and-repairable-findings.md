# task-0145-reviewer-call-owner-verbatim-and-repairable-findings

- id: `task-0145-reviewer-call-owner-verbatim-and-repairable-findings`
- title: `Worker 파이프라인 Reviewer 호출의 고정 Manager Summary를 Owner 요청 원문 전달로 바꾸고 콘텐츠와 무관한 FINDINGS는 repair 없이 escalation`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-09-24 16:47 UTC`
- updated_at: `2026-09-24 16:50 UTC`
- summary: `task-0143 resume E2E에서 reviewer_call의 고정 Manager Summary가 Owner 승인 범위를 넓게 바꿔 쓰고 Reviewer가 확인할 수 없는 Worker 동작과 테스트 통과를 주장해 FINDINGS가 났고, 콘텐츠만 고칠 수 있는 repair Worker는 변경 없이 끝났다. Summary를 Owner 요청 원문, git diff로 확인 가능한 변경 파일과 Pipeline limit로 바꾸고, 변경 파일과 무관한 FINDINGS만 있으면 repair 없이 reviewer_findings_not_repairable로 실패시킨다. DONE은 Reviewer/QA 후 Owner가 결정한다.`
- source_command: `Owner 지시: read-only 조사 결과 기준으로 task-0145 진행`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `7483e641b38c536d92992df23816ba2e196325e1` (main HEAD, push 전) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat`, `memory/tasks/task-0143-…md` |
| 보존 대상 | task-0143 worktree/branch 3개(`a02dde9`, r2 `6eec227`과 미커밋 수정, r3 `e05c69c`) |

## Owner 결정 (원문)

```text
read-only 조사 결과 기준으로 task-0145를 진행해.

범위:
1. reviewer_call()의 고정 Manager Summary를 제거하고 Owner 요청 원문을 verbatim으로 전달.
2. Pipeline limit은 Owner 조건과 명확히 분리해서 Reviewer가 git diff로 확인 가능한 사실만 전달.
3. Worker 동작/테스트 결과처럼 Reviewer가 확인할 수 없는 주장은 Summary에서 제거.
4. Reviewer FINDINGS 중 candidate 변경 파일과 무관한 Manager Summary/승인 전달/evidence 문제만 있는 경우 repair Worker를 실행하지 않고 `reviewer_findings_not_repairable`로 FAILED + Owner escalation.
   - 이 경우 repair budget을 소비하지 않는다.
5. 콘텐츠 지적이 포함된 FINDINGS는 기존 repair 흐름을 유지하되, Worker가 candidate 변경 파일에 해당하는 지적만 수정하도록 명시.
6. 관련 smoke test 추가.
7. task-0145 기록 작성.

제외:
- audit `/go` 문제
- task-0142 DONE 처리
- task-0143 재실행

구현 전 task-0145 범위와 최소 변경 계획을 먼저 확정한 뒤 구현할 것.

구현 → smoke/integration test → fresh Reviewer → QA → checkpoint commit 순서.
push 금지.
jarvis.bat 접근/수정/스테이징 금지.
task-0143 r2/r3 worktree와 기존 미커밋 수정 보존.

마지막에 변경 내용, 테스트, Reviewer, QA, commit hash만 간결하게 보고해.
```

## 확정한 범위와 최소 변경 계획

이 계획은 구현 전에 이 기록만 담은 commit으로 먼저 남긴다. 구현은 그 다음 commit이다.

| 파일 | 변경 |
| --- | --- |
| `orchestrator/worker/claude_worker.py` | (범위 1–3) `reviewer_call`의 고정 4행 Summary 삭제. 대신 Owner 요청 원문을 그대로 한 줄 인용(유일한 Owner 조건), baseline..candidate 변경 파일 목록(`git diff --name-status`로 확인 가능), Owner 조건이 아닌 Pipeline limit(`apps/studyroom/content/` 밖과 `jarvis.bat` 변경 거부, 변경 파일 목록으로 확인 가능)을 분리해 적고, Worker 동작과 테스트 결과는 주장하지 않으며 테스트는 Reviewer 뒤 QA 단계가 다시 실행한다고만 밝힌다. (범위 4) Reviewer 보고의 findings를 항목별로 나눠 각 항목의 `evidence`가 candidate 변경 파일을 가리키는지 본다. 가리키는 항목이 하나도 없으면 repair Worker를 부르지 않고 repair 횟수를 늘리지 않은 채 `reviewer_findings_not_repairable`로 실패한다. 형식을 알 수 없는 보고는 기존처럼 repair 대상으로 둔다. (범위 5) repair 프롬프트에 변경 파일 목록을 넣고 그 파일을 가리키는 지적만 고치며 Manager Summary·승인 전달·evidence 지적은 무시하라고 명시한다 |
| `adapters/discord/bot_minimal.py` | 실패 보고에 `reviewer_findings_not_repairable`이면 "Reviewer 지적이 변경 파일과 무관해 Worker가 고칠 수 없습니다. Owner 결정이 필요합니다." 한 줄 추가. 그 외 무변경 |
| `orchestrator/worker/run_smoke_tests.py` | (범위 6) 가짜 Reviewer 기본 FINDINGS의 evidence를 변경 파일 경로로 바꾸고, 요약만 지적하는 모드와 콘텐츠·요약 혼합 모드 추가. 검증: Reviewer 호출에 요청 원문 포함·고정 주장 문장 없음·Pipeline limit 분리, 요약만 지적 → Worker 미호출·repair 0회·`reviewer_findings_not_repairable`, 혼합 → repair 1회 후 PASS, repair 프롬프트에 변경 파일과 지적 한정 문구, 분류 함수 단위 검사 |
| 이 기록 | 신규 |

유지: TODO/DOING/DONE/FAILED 전환 계약, repair 예산 상한 1과 의미, resume, 허용 경로, Owner 전용 게이트. 제외: audit `/go` 문제, task-0142 DONE 처리, task-0143 재실행.

## 검증 (Implementer 실행, QA 재현 대상)

| # | 항목 | 결과 |
| --- | --- | --- |
| V1 | `python -B orchestrator/worker/run_smoke_tests.py` | 131/131 PASS (task-0144 115 + task-0145 16) |
| V2 | `python -B adapters/discord/bot_minimal.py --self-check-suite` (UTF-8 모드) | 92/92 ok |
| V3 | `orchestrator/discord-intake`, `orchestrator/audit-chain`, `apps/studyroom` smoke | 모두 PASS |
| V4 | `git diff --check` | exit 0 |
| V5 | task-0143 보존 | `a02dde9`, r2 `6eec227`과 미커밋 수정, r3 `e05c69c` 그대로 |
| V6 | 실제 task-0143 r3 Reviewer 보고(세션 기록에서 읽음, 저장소 밖)로 분류 함수 확인 | 항목 3개, repair 불가로 분류 |

구현 메모: 가짜 Reviewer의 기본 FINDINGS가 evidence에 경로가 없는 형식이었어서, 새 분류에서는 repair 불가로 바뀌지 않도록 기본 FINDINGS의 evidence를 변경 파일 경로로 바꿨다. 기존 repair 사례들의 기대값은 그대로다.

## Repair 이력

retry_budget=1, retry_count=0, repair_budget=1, repair_count=0
