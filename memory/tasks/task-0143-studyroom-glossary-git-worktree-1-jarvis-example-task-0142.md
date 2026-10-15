# task-0143-studyroom-glossary-git-worktree-1-jarvis-example-task-0142

- id: `task-0143-studyroom-glossary-git-worktree-1-jarvis-example-task-0142`
- title: `Studyroom glossary에 "Git Worktree" 용어 1개 추가 (jarvis_example은 task-0142 기록에 있는 사실만)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-24 13:35 UTC`
- updated_at: `2026-10-15 04:33 UTC`
- summary: `요청 사항(Studyroom glossary에 "Git Worktree" 용어 1개 추가 (jarvis_example은 task-0142 기록에 있는 사실만))을 작업 초안으로 정리한다. 이번 단계는 draft object 생성 규칙 정의까지만 포함한다.`
- source_command: `/task`
- execution_candidate: `true`
- execution_request: `{"action":"claude_worker_pipeline","execution_type":"claude_worker","requested_at":"2026-10-15 04:33 UTC","result_type":"execution_request","source":"/go","target":"studyroom_content","task_id":"task-0143-studyroom-glossary-git-worktree-1-jarvis-example-task-0142"}`
- execution_result: `{"action":"claude_worker_pipeline","error_reason":"","executed":true,"execution_type":"claude_worker","result_type":"execution_result","success":true,"task_id":"task-0143-studyroom-glossary-git-worktree-1-jarvis-example-task-0142"}`
- executed: `true`
- success: `true`
- dry_run: `false`
- execution_updated_at: `2026-10-15 04:33 UTC`
- execution_summary: `worker candidate 47781ee passed Reviewer and QA after 0 repair(s)`

## 시도 기록

Owner가 Discord `/work`로 만들고 `/go`로 실행한 task-0142 Worker 파이프라인의 첫 실제 E2E다. 위 메타데이터는 마지막 시도(r3)의 결과다. 실패 원인은 task-0142 기록의 "실제 Discord E2E 기록" 표를 따른다.

| 시도 | candidate | 기반 커밋 | 실패 원인 |
| --- | --- | --- | --- |
| 첫 시도 (`/go`) | `a02dde9d29a752a47401c8166fef7ad9aa31868e` | `03f4579f033a5c16e3bab50465278f0c798cf2dc` (task-0142 파이프라인) | Reviewer FINDINGS. Reviewer가 요청에 적힌 task-0142 기록을 읽을 evidence 경로를 받지 못했다. |
| r2 (`/go` 재시도) | `6eec22797addb334c426d8104b5cec9874f5b41c` | `2a33b109d76300a5eb4c7259e20beeef2108fe42` | Reviewer FINDINGS major: `jarvis_example`이 task-0142 기록에 없는 사실을 포함해 FAILED. |
| r3 (`/go … resume`) | `e05c69cfe170534b19660a6d1accf7d169dced2a` | `7483e641b38c536d92992df23816ba2e196325e1` (task-0144 DONE checkpoint) | Reviewer FINDINGS가 모두 고정 Manager Summary에 관한 것이라 repair Worker가 변경 없이 끝나 `scope:repair_no_changes`로 FAILED. |

## 이어진 수정

- `2a33b10` (task-0142): 첫 시도 실패와 관련된다. 커밋 메시지가 task-0143 실행이 evidence 경로 부재로 Reviewer에서 실패했다고 적고, 요청에 적힌 task 기록을 evidence 경로로 넘기며 재시도가 이전 시도를 지우지 않고 `-r2`, `-r3` 이름으로 실행되게 했다. r2는 이 커밋 위에서 실행됐다.
- task-0144 (자동 repair 1회와 `/go <task-id> resume`): r2와 관련된다. task-0144 기록은 r2 candidate `6eec227`과 r2 worktree의 미커밋 수정을 보존 대상으로 적는다. r3는 task-0144 DONE checkpoint 위에서 `resume`으로 r2의 변경을 재적용해 실행됐다. task-0144 기록은 자신이 r2 실패 때문에 시작됐다고 직접 적지는 않는다.
- task-0145 (reviewer_call Summary를 Owner 요청 원문으로 바꾸고 변경 파일과 무관한 FINDINGS는 `reviewer_findings_not_repairable`로 실패): r3와 관련된다. task-0145 summary가 task-0143 resume E2E의 Manager Summary FINDINGS와 변경 없이 끝난 repair Worker를 작업 이유로 적는다.

## 현재 상태

- task-0143은 `FAILED`로 남아 있다.
- "Git Worktree" 용어(`id: git-worktree`)는 main의 `apps/studyroom/content/glossary.json`에 반영되지 않았다.
- 세 시도의 worktree와 branch는 `C:\work\jarvis-core-worktrees\` 아래에 보존 중이다. r2 worktree에는 `apps/studyroom/content/glossary.json`의 미커밋 수정 1줄이 있다.

## 2026-10-14 `/go` 재시도: `preflight:main_tree_dirty`

Owner가 2026-10-14 13:30 UTC에 Discord `/go task-0143-studyroom-glossary-git-worktree-1-jarvis-example-task-0142`로 재시도했다. 봇이
`FAILED→TODO→DOING` 전이를 이 기록에 쓴 뒤 Worker 사전 검사가 추적 파일 변경(이 기록)을 보고 `main_tree_dirty`로 멈췄고, 결과 기록으로
`DOING→FAILED`가 됐다. 사전 검사에서 멈춰 새 attempt(`-r4`) worktree·branch는 만들어지지 않았고 `-r3`는 그대로다. main은 `12d0a9d`
그대로이고 push는 없었다.

위 메타데이터의 실행 필드(`execution_request`, `execution_result`, `execution_updated_at`, `execution_summary`)는 이 재시도의 값이다.
r3의 실패 사유 `scope:repair_no_changes`는 위 시도 기록 표에 남아 있다.

원인 메모: 이 기록은 r3 뒤인 2026-09-29(`c5cf969`)에 커밋돼 추적 파일이 됐다. `/go`가 Worker 실행 전에 추적 중인 task 기록을 전이로 바꾸므로,
커밋된 FAILED task의 `/go` 재시도는 사전 검사에 항상 걸린다. 원인 조사와 수정은 별도 작업이다. Owner 지시로 봇이 쓴 변경을 되돌리지 않고 이
절과 함께 기록 checkpoint로 남긴다(`updated_at`은 이 절을 더한 시각).
