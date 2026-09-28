# task-0142-jarvis-v0-2-claude-worker-e2e

- id: `task-0142-jarvis-v0-2-claude-worker-e2e`
- title: `Jarvis v0.2 첫 end-to-end 자동 실행: Discord /work·/go → Claude Worker → 테스트 → Reviewer → QA → commit → Discord 보고`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-24 13:29 UTC`
- updated_at: `2026-09-28 17:53 UTC`
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

## 실제 Discord E2E 기록

Owner가 Discord에서 `/work`와 `/go`를 직접 보내 실행했다. 아래는 실행 결과 기록이다. 마지막 행(task-0146 재시도)에서 성공 경로 전체가 실제로 확인되어 status를 `DONE`으로 바꿨다.

| 실행 | 파이프라인 코드 | 결과 | 보존 |
| --- | --- | --- | --- |
| task-0143 첫 시도 | `03f4579` | Reviewer FINDINGS. Reviewer가 요청에 적힌 task-0142 기록을 읽을 evidence 경로를 받지 못함 → `2a33b10`에서 수정 | 브랜치·worktree `a02dde9d29a752a47401c8166fef7ad9aa31868e` |
| task-0143 r2 (`/go` 재시도) | `2a33b10` | Reviewer FINDINGS major: `jarvis_example`이 task-0142 기록에 없는 사실 포함 → FAILED | `6eec22797addb334c426d8104b5cec9874f5b41c`와 worktree 미커밋 수정 |
| task-0143 r3 (`/go … resume`) | task-0144 (`7483e64`) | resume 재적용은 정상. Reviewer FINDINGS가 모두 고정 Manager Summary에 관한 것이라 repair Worker가 변경 없이 끝나 `scope:repair_no_changes` → task-0145에서 수정 | `e05c69cfe170534b19660a6d1accf7d169dced2a` |
| task-0146 (`/work` 새 작업 "Fast-forward merge" 용어 1개) | task-0145 (`775a602`) | candidate `7cc2b344a86eb4dbf9021bb103f476c91061a98b` → Reviewer FINDINGS(major 1: 기록에 없는 단계·상태 이름, minor 2) → evidence가 변경 파일을 가리켜 repair 가능 분류 → 자동 repair 1회 → candidate `a0079a135ad374cdd595afd06dae3c10d3d99006` → fresh Reviewer FINDINGS(minor 1: "작업 트리가 깨끗할 때만"은 task-0142 기록에 없는 사실, minor 2: Reviewer 자신의 명령 형식 이탈 보고) → repair 예산 1 소진 → `reviewer:reviewer_findings` FAILED | 브랜치 `jarvis/task-0146-…`, worktree `C:\work\jarvis-core-worktrees\task-0146-…`, candidate 2개 |
| task-0146 재시도 (`/go`, 2026-09-26 19:11 KST 시작, 19:20 KST 완료) | task-0148 반영 후 main `265161c105b0956f8db6a47d813b991163729cca` | candidate `add2c8f2b45d3712eb19034dd698b07594388bbb` → 자동 repair 1회 → candidate `20bc867acb3e1d9b36144d60bc6f35907093da3d` → Reviewer PASS → QA PASS(6개 검사) → main ff-only 반영 → task-0146 DONE 기록과 checkpoint commit `7da4dadbc2084af60787f9b53605df912cbf5b04` → Discord 성공 보고. push 없음 | main에 반영됨 |

실제 경로에서 확인된 것: Discord `/work`→TODO 생성, `/go`→DOING과 Owner 승인 감사, 저장소 밖 worktree, Worker 실행, 범위 검사, 테스트, candidate commit, Reviewer 호출(task-0145 요약 형식), FINDINGS 분류와 자동 repair 1회, fresh Reviewer, 예산 소진 시 FAILED 기록, 이전 시도 보존, main 무변경. Discord 결과 메시지 전송은 봇 로그에 오류가 없다는 것만 확인했고 메시지 내용은 확인하지 않았다.

task-0146 재시도에서 성공 경로도 실제로 확인됐다: Reviewer PASS 이후의 QA, main ff-only 반영, task DONE 기록(task-0146 `status: DONE`, `success: true`), checkpoint commit, Discord 성공 보고. 성공 보고 메시지 내용은 Owner가 Discord에서 확인해 원문을 전달했다(아래 완료 근거).

알려진 별도 이슈: 실행 결과 감사 기록이 `invalid_payload_source detail=/go`로 거부된다(Owner 지시로 미수정). → 커밋 2b03f23에서 source를 go로 바꿔 해결됐고, task-0149 실제 Discord /go에서 감사 체인에 execution_result(source: "go")가 정상 기록되고 [audit] append failed가 없음을 확인했다.

## 완료 근거 (task-model §8)

1. 산출물: 파이프라인 구현(위 변경 표), 실제 성공 실행의 candidate `20bc867acb3e1d9b36144d60bc6f35907093da3d`와 checkpoint `7da4dadbc2084af60787f9b53605df912cbf5b04`.
2. 검증 흔적: V1·V2 결과, task-0146 실행 결과 메타데이터(`worker candidate 20bc867 passed Reviewer and QA after 1 repair(s)`), Owner가 전달한 Discord 보고 원문:

```text
jarvis-bot앱 — 2026-09-26 오후 7:11
 승인됨 (재시도): task-0146-studyroom-glossary-fast-forward-merge-1-jarvis-example-task-0142 → Claude Worker 시작. 끝나면 이 채널에 보고합니다.
jarvis-bot앱 — 2026-09-26 오후 7:20
 완료: task-0146-studyroom-glossary-fast-forward-merge-1-jarvis-example-task-0142
   * 변경 파일: apps/studyroom/content/glossary.json
   * 테스트: ALL SMOKE TESTS PASSED (5/5 suites, 0 failures)
   * Reviewer: PASS
   * QA: PASS (6개 검사)
   * 자동 repair: 1회
   * candidate: 20bc867 / checkpoint: 7da4dad
   * push: 하지 않음
```

3. 이 task의 성공 조건 밖으로 남은 항목. 착수하려면 별도 task와 Owner 승인이 필요하다.
   - `/go` 실행 결과 감사 기록의 `invalid_payload_source detail=/go` 거부 → 해결(2b03f23, task-0149 E2E에서 확인)
   - 실패 시도의 브랜치·worktree 정리(task-0143 ×3, task-0146 첫 시도 ×1)
