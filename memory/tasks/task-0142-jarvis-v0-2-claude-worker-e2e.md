# task-0142-jarvis-v0-2-claude-worker-e2e

- id: `task-0142-jarvis-v0-2-claude-worker-e2e`
- title: `Jarvis v0.2 첫 end-to-end 자동 실행: Discord /work·/go → Claude Worker → 테스트 → Reviewer → QA → commit → Discord 보고`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-09-24 13:29 UTC`
- updated_at: `2026-09-24 13:29 UTC`
- summary: `Discord에서 Owner가 /work로 Studyroom 콘텐츠 작업을 준비하고 /go로 승인하면, 저장소 밖 worktree에서 Claude Code Worker가 작업하고 테스트, candidate commit, Reviewer(claude --agent reviewer), 결정론적 QA, baseline이 그대로일 때만 main ff-only 반영, task DONE 기록과 checkpoint commit, Discord 결과 보고까지 자동으로 이어지는 최소 vertical slice다. 실패·timeout·범위 위반은 FAILED로 기록하고 선택지를 보고하며, push·외부 API·credential·Codex·다중 Worker·jarvis.bat 접근은 범위 밖이다.`
- source_command: `Owner 지시: Jarvis v0.2 첫 실제 end-to-end 자동 실행 최소 vertical slice 구현`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `fdcaa7547d5973c0aeebdf369b93d6a6732d85c8` (`origin/main`과 같음) |
| 작업 전 상태 | tracked 수정 없음, untracked `jarvis.bat`만 |

## Owner 결정 (원문)

```text
4개 모두 권장안대로 진행해.

1. 승인 방식
- `/work` + `/go` 방식으로 진행
- 기존 TODO→NEEDS_APPROVAL 전환 계약은 이번 작업에서 변경하지 않는다.
- `/go` 자체를 Owner 승인으로 취급한다.

2. 성공 처리
- baseline이 변경되지 않았을 때만 ff-only로 main에 반영
- 성공 후 task를 DONE 처리
- checkpoint commit 생성
- push는 하지 않는다.

3. worktree
- 저장소 밖 `C:\work\jarvis-core-worktrees\` 사용
- main worktree는 절대 Worker 작업 공간으로 사용하지 않는다.

4. E2E
- 구현 및 자체 테스트가 끝나면 실제 Discord E2E까지 진행한다.
- 기존 `adapters/discord/.env`의 토큰 값은 출력하거나 보고하지 않는다.
- 내가 Discord에서 `/work`와 `/go`를 직접 보내는 방식으로 검증한다.

추가 조건:
- 구현 전에 계획을 최종 확정하고 진행해.
- 기존 구조를 최대한 재사용하고 최소 diff로 구현한다.
- Studyroom content 수정 1종만 지원한다.
- Worker의 파일 변경 범위는 `apps/studyroom/content/`로 제한한다.
- `jarvis.bat`은 절대 접근/수정/스테이징하지 않는다.
- push, 외부 API, credential, Codex, 다중 Worker는 이번 범위에서 제외한다.
- 실패/timeout/범위 위반도 smoke test로 반드시 검증한다.

구현 → 테스트 → 실제 Discord E2E 순서로 진행해.
각 단계 결과는 PASS/FINDINGS와 핵심 내용만 보고해.
```

## 변경

| 파일 | 변경 |
| --- | --- |
| `orchestrator/worker/claude_worker.py` | 신규. worktree → Worker → 범위 검사 → 테스트 → candidate commit → Reviewer → QA → ff-only → task 결과 기록 → checkpoint commit 파이프라인 |
| `orchestrator/worker/run_smoke_tests.py` | 신규. 로컬 clone과 가짜 claude로 성공, 범위 위반, jarvis.bat 쓰기, worker timeout, worker 실패, 테스트 실패, Reviewer FINDINGS, main dirty, baseline 이동과 봇 /work·/go·재시도 흐름을 검증 |
| `adapters/discord/bot_minimal.py` | `/work`, `/go` 추가(Owner 전용), 긴 작업은 `asyncio.to_thread`로 실행 후 같은 채널에 보고, 도움말·거절 안내 갱신. 기존 명령과 전환 계약 무변경 |
| `adapters/discord/README.md` | `/work`·`/go` 설명 |
| 이 기록 | 신규 |

## 재사용한 기존 구조

- task 생성: `_run_task_pipeline`(기존 `/task` 경로, TODO로 생성)
- 상태 전이: `_apply_task_status_transition`(durable writer, 기존 `TODO→DOING`, `FAILED→TODO`, `DOING→DONE/FAILED` 쌍만 사용)
- 실행 결과 기록: `_apply_execution_result`(task-0055 원자적 쓰기)
- 감사: `_audit_owner_approval`, `_audit_execution_result`
- 승인 경계: 기존 Owner 전용 명령 게이트(`PRIVILEGED_COMMANDS`)
- Reviewer: `.claude/agents/reviewer.md`를 `claude -p --agent reviewer`로 매번 새로 읽어 실행

## 검증

| # | 항목 | 결과 |
| --- | --- | --- |
| V1 | `python -B orchestrator/worker/run_smoke_tests.py` | 62/62 PASS |
| V2 | `python -B adapters/discord/bot_minimal.py --self-check-suite` (UTF-8 모드) | 92/92 ok (변경 전과 동일) |

## 한계

- 지원 작업은 Studyroom 콘텐츠 수정 1종뿐이다. 요청에 studyroom이 없으면 hold한다.
- Reviewer FINDINGS가 나오면 자동 repair 없이 FAILED로 보고하고 Owner가 `/go`로 재시도한다.
- 봇 프로세스가 작업 중 종료되면 task는 DOING으로 남는다. 재개 기능은 없다.
- Codex Reviewer, 다중 Worker, push는 범위 밖이다.

## Repair 이력

retry_budget=1, retry_count=0, repair_budget=1, repair_count=0
