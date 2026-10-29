# task-0209-remove-old-attempt-worktrees

- id: `task-0209-remove-old-attempt-worktrees`
- title: `끝난 task의 attempt worktree 정리 (branch 유지)`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-29 16:36 UTC`
- updated_at: `2026-10-29 16:39 UTC`
- summary: `DONE·CLOSED task 네 개의 Worker attempt worktree 폴더 다섯 개를 git worktree remove(--force 없이)로 지운다. branch 다섯 개와 그 커밋은 남겨 필요하면 git worktree add로 다시 만들 수 있게 한다. 중첩 폴더 jarvis-core-worktrees/jarvis-core-worktrees와 잠금 파일, 코드·다른 기록은 바꾸지 않고 push는 하지 않는다.`
- source_command: `Owner 지시: 다음 권장 작업 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `5edb8ffe39bb945a89a482fc537c859119f11c4c` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문)

```text
[Owner 지시]
다음 권장작업 시작해

[Manager 권장안]
**worktree 폴더 5개만 정리하고 branch 5개는 남기는 것을 권합니다.**
- 사용하는 명령은 `git worktree remove`이고, 미커밋 변경이 없으니 `--force`는 쓰지 않습니다.
- branch가 남아 있어서 필요하면 `git worktree add`로 언제든 다시 만들 수 있습니다. 즉 되돌릴 수 있는 정리입니다.
- 정리 기록은 작은 task 기록 하나로 남기겠습니다.
- 중첩 폴더와 그 안의 잠금 파일은 이번 범위에서 빼고 그대로 둡니다.

[Owner 답]
worktree만 정리
```

## 조사 (등록 전, 읽기 전용)

| worktree (`jarvis-core-worktrees/` 아래) | HEAD | main 조상 | 미커밋 변경 | task 상태 |
| --- | --- | --- | --- | --- |
| `task-0143-studyroom-glossary-git-worktree-1-jarvis-example-task-0142-r3` | `e05c69c` | 아님 | 0 | DONE |
| `task-0149-studyroom-glossary-1` | `8f0c58e` | 아님 | 0 | DONE |
| `task-0149-studyroom-glossary-1-r2` | `bd1622e` | 아님 | 0 | DONE |
| `task-0154-studyroom-glossary-owner-accept-1-jarvis-example-task-0151` | `80a61a8` | 맞음 | 0 | DONE |
| `task-0200-studyroom-glossary-owner-accept-term-task-0154` | `f3bd53b` | 맞음 | 0 | CLOSED |

- main 조상이 아닌 세 시도는 실패한 이전 시도다. task-0143은 `47781ee`, task-0149는 `4c9873e`가 main에 반영돼 DONE이 됐다.
- 네 task(task-0143, task-0149, task-0154, task-0200) 모두 DONE이나 CLOSED라 `/go` 재시도·resume·accept가 받지 않는다(task-0180, task-0206). worktree가 없어도 Worker 동작에 영향이 없다.
- SOP §10.2 1항 "이전 시도의 worktree와 branch는 삭제하지 않는다."는 Worker 파이프라인이 스스로 지우지 않는다는 규칙이다. 이번 정리는 Owner 결정으로 하는 수동 작업이며 branch는 지우지 않는다.

## 범위

| 구분 | 대상 |
| --- | --- |
| 실행 | 위 표의 worktree 다섯 개에 `git worktree remove <path>`(`--force` 없음). 지운 뒤 `git worktree prune`은 쓰지 않는다(remove가 등록도 지움) |
| owned | `memory/tasks/task-0209-remove-old-attempt-worktrees.md` |
| deny | branch 삭제, `--force`, 중첩 폴더 `jarvis-core-worktrees/jarvis-core-worktrees`와 잠금 파일, `jarvis.bat`, 코드·문서·다른 task 기록, push |

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다(status·updated_at 줄만 바뀜, updated_at `2026-10-29 16:36 UTC`).

## 실행

worktree마다 미커밋 변경 0을 다시 확인한 뒤 `git worktree remove <path>`(`--force` 없음)를 차례로 실행했고 다섯 개 모두 성공했다.

확인:

- `git worktree list`에는 main(`C:/project/work/jarvis-core`)만 남았다.
- `jarvis/*` branch 다섯 개는 그대로다(`e05c69c`, `8f0c58e`, `bd1622e`, `80a61a8`, `f3bd53b`).
- `jarvis-core-worktrees/`에는 `.jarvis-worker.lock`과 중첩 폴더 `jarvis-core-worktrees/`(그 안의 `.jarvis-worker.lock`)만 남았고 둘 다 건드리지 않았다.
- 저장소 작업 트리 변경은 이 task 기록뿐이다(`jarvis.bat`은 미추적 그대로).

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다. "Manager 권장안"은 Manager가 쓴 문장을 Owner가 "worktree만 정리"로 받아들인 것이다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Owner 지시]" | 지시의 표지 |
| A2 | Owner 결정 (원문) | "다음 권장작업 시작해" | 직전 보고의 다음 권장 작업(오래된 attempt worktree 정리)을 시작하라는 지시. 먼저 읽기 전용 조사와 권장안을 냈다 |
| A3 | Owner 결정 (원문) | "[Manager 권장안]" | 권장안의 표지 |
| A4 | Owner 결정 (원문) | "**worktree 폴더 5개만 정리하고 branch 5개는 남기는 것을 권합니다.**" | 조사 표의 worktree 다섯 개만 지웠고 `jarvis/*` branch 다섯 개는 남았다(실행 절 확인) |
| A5 | Owner 결정 (원문) | "사용하는 명령은 `git worktree remove`이고, 미커밋 변경이 없으니 `--force`는 쓰지 않습니다." | 각 worktree의 미커밋 변경 0을 다시 확인하고 `git worktree remove`만 `--force` 없이 썼다 |
| A6 | Owner 결정 (원문) | "branch가 남아 있어서 필요하면 `git worktree add`로 언제든 다시 만들 수 있습니다." | branch와 커밋이 남아 있어 다시 만들 수 있다. 이번에 다시 만들지는 않았다 |
| A7 | Owner 결정 (원문) | "즉 되돌릴 수 있는 정리입니다." | 지운 것은 깨끗한 작업 트리 사본뿐이고 커밋은 branch에 남았다 |
| A8 | Owner 결정 (원문) | "정리 기록은 작은 task 기록 하나로 남기겠습니다." | 이 task 기록 하나가 그 기록이다. 다른 파일은 바꾸지 않았다 |
| A9 | Owner 결정 (원문) | "중첩 폴더와 그 안의 잠금 파일은 이번 범위에서 빼고 그대로 둡니다." | 중첩 폴더 `jarvis-core-worktrees/jarvis-core-worktrees`와 두 `.jarvis-worker.lock`은 그대로다(실행 절 확인) |
| A10 | Owner 결정 (원문) | "[Owner 답]" | 답의 표지 |
| A11 | Owner 결정 (원문) | "worktree만 정리" | 권장안대로 worktree만 정리하고 branch는 지우지 않았다 |

## Self-review

`self-reviewer`(`claude -p --agent self-reviewer --tools Read,Grep,Glob`, 첫 사전 점검 PASS 뒤 1회, API 환산 약 $0.28)의 지적 2건(모두 minor)을 고쳤다.

1. "task 다섯 개"라 적었지만 worktree 다섯 개는 task 네 개의 것(task-0149가 둘) → summary와 조사 절을 "task 네 개의 worktree 다섯 개"로 고쳤다.
2. SOP 인용 위치 "§10 1항"이 실제로는 §10.2 1항 → 고쳤다.

수정 뒤 사전 점검(`python -B scripts/check_task_record.py memory/tasks/task-0209-remove-old-attempt-worktrees.md --baseline 5edb8ffe39bb945a89a482fc537c859119f11c4c --require-quotes`)은 `status=PASS`였고, 그 뒤 `commit_candidate.py`로 첫 candidate `36f15501b064e22eb5ba910619f5e3636a187580`을 만들었다.

## Reviewer 결과 (첫 candidate)

- candidate `36f15501b064e22eb5ba910619f5e3636a187580`: Reviewer FINDINGS, 지적 1건(minor), self_deviations 0. Self-review 절 마지막 문장이 "아래 candidate 직전 실행"의 사전 점검 결과를 가리키지만 그 아래에 결과가 없다.
- Repair 1(`repair_count=1`, 예산 안, Manager 결정): 그 문장을 실제 사전 점검 명령과 결과(`status=PASS`)를 적는 문장으로 바꾸고 이 절을 더했다. 실행 내용과 Manager 요약은 바꾸지 않았다. 새 candidate에 Reviewer → QA를 다시 한다.
