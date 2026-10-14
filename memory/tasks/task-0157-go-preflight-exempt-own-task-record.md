# task-0157-go-preflight-exempt-own-task-record

- id: `task-0157-go-preflight-exempt-own-task-record`
- title: `Worker 파이프라인 main 검사에서 실행 대상 task 자신의 기록 파일만 예외 처리`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-14 14:51 UTC`
- updated_at: `2026-10-14 15:14 UTC`
- summary: `Discord /go가 Worker 실행 전에 task 기록에 상태 전이를 쓰므로, 기록이 이미 커밋된 task는 사전 검사와 반영 직전 검사의 추적 파일 변경 검사(main_tree_dirty)에 항상 걸린다(task-0143 재시도 실패로 확인). 두 검사가 실행 대상 task 자신의 기록 파일 하나만 예외로 두고 그 밖의 추적 변경은 그대로 막게 하며, 커밋된 기록의 TODO·FAILED 재시도·resume·accept 회귀 테스트와 SOP 10.2 한 줄을 더한다. push는 하지 않는다.`
- source_command: `Owner 승인: A안으로 수정 진행`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `a022887d3654e226796dcca8e4190fea073cfe3e` (main HEAD = origin/main, push 직후) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 보존 대상 | task-0143 `-r3` worktree/branch(`e05c69c`), task-0149 worktree/branch 2개, task-0154 worktree/branch |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` |

## 조사 결과 (read-only, 코드와 재현 기준)

1. `adapters/discord/bot_minimal.py` `_run_go()`는 Worker 실행 전에 task 기록에 전이를 쓴다(FAILED면 `FAILED→TODO`, 이어서
   `TODO→DOING`). 그 뒤 `_run_worker_job()`이 `claude_worker.run_pipeline()`을 부른다.
2. `orchestrator/worker/claude_worker.py` `run_pipeline()` 사전 검사와 `_integrate_and_checkpoint()` 반영 직전 검사는
   `git status --porcelain --untracked-files=no` 결과가 비어 있지 않으면 `main_tree_dirty`로 멈춘다.
3. `/work`로 만든 task 기록은 커밋되지 않은 파일이라 2의 검사에 걸리지 않고, 파이프라인 checkpoint가 처음 커밋한다
   (task-0149 `c6c191d`, task-0154 `8631490`). 커밋된 기록이면 1이 만든 변경이 2에 걸린다. task-0143 기록은 `c5cf969`(2026-09-29)에
   커밋됐고, 2026-10-14 `/go` 재시도가 `preflight:main_tree_dirty`로 실패했다(`a022887`).
4. 재현(scratch clone, 가짜 claude, 감사 대체, 저장소 무변경): 커밋된 FAILED·TODO 기록은 `preflight:main_tree_dirty`, 커밋 안 된
   FAILED 기록(대조)은 사전 검사를 통과했다.
5. accept(`accept_candidate()`)는 `_accept_main_check()`를 승인 전이 전에 하므로 통과하지만, 승인 전이가 기록을 쓴 뒤
   `_integrate_and_checkpoint()`의 같은 검사에 걸린다(코드 흐름 기준).
6. Worker smoke는 task 기록을 커밋 안 된 파일로만 만들고(`write_task`), accept 테스트의 승인은 파일을 쓰지 않는 가짜라 이 경우를
   검사하지 않는다.

## Owner 결정 (원문)

```text
A안으로 수정 진행하고 a022887 push해줘
```

승인 대상인 A안은 Director 보고의 다음 원문이다.

```text
| **A (추천)** | 사전 검사(`:720`)와 반영 단계 검사(`:678`, accept 경로 포함)가 실행 대상 **task 자신의 기록 파일 하나만** 예외로 둡니다. 그 밖의 추적 파일 변경은 지금처럼 막습니다 | 변경이 가장 작습니다. 그 파일은 끝날 때 checkpoint 커밋에 들어가 흐름이 맞습니다. ff-only 반영도 candidate가 `apps/studyroom/content/`만 바꾸므로 충돌하지 않습니다 |

A에 함께 넣을 것:
- **회귀 테스트**: 커밋된 기록으로 TODO, FAILED 재시도, resume, accept를 실행하는 경우. 그리고 기록 외의 추적 파일이 바뀌어 있으면 여전히 막는지 확인하는 경우.
- **문서**: SOP §10.2에 예외 규칙 한 줄. 파일 소유는 `orchestrator/worker/claude_worker.py`, `orchestrator/worker/run_smoke_tests.py`, SOP 문서가 됩니다.
```

`a022887` push는 이 task 생성 전에 끝났다(`12d0a9d..a022887`, 원격 HEAD `a022887` 확인).

## Manager 요약

| # | 승인 조건 | Manager 해석과 충족 방법 |
| --- | --- | --- |
| A1 | 사전 검사(`claude_worker.py:720`)가 실행 대상 task 자신의 기록 파일 하나만 예외 | `run_pipeline()` 사전 검사가 `memory/tasks/<task_id>.md` 한 경로만 제외한 추적 변경을 본다(git pathspec `:(exclude,literal)`). 그 밖의 추적 변경은 그대로 `main_tree_dirty` |
| A2 | 반영 단계 검사(`:678`, accept 경로 포함)도 같은 예외 | `_integrate_and_checkpoint()` 검사에 같은 함수를 쓴다. accept는 이 함수를 거치므로 함께 적용된다 |
| A3 | 그 밖의 추적 파일 변경은 지금처럼 막는다 | 예외는 정확히 그 한 경로. 다른 task 기록이나 다른 파일 변경은 막는다 |
| A4 | 회귀 테스트: 커밋된 기록으로 TODO, FAILED 재시도, resume, accept | Worker smoke에 추가: 봇 경로 TODO(커밋된 기록) `/go`, 봇 경로 FAILED 재시도(커밋된 기록, task-0143 형태), `run_pipeline` resume(커밋되고 바뀐 기록), `accept_candidate`(승인이 커밋된 기록을 쓰는 경우) |
| A5 | 회귀 테스트: 기록 외 추적 파일이 바뀌어 있으면 여전히 막음 | 사전 검사: 커밋되고 바뀐 기록 + 다른 추적 파일 변경 → `preflight:main_tree_dirty`. 반영 직전: Reviewer 단계에서 다른 추적 파일을 바꾸는 가짜 → `integrate:main_tree_dirty` |
| A6 | SOP 10.2에 예외 규칙 한 줄 | 9항 끝에 한 문장 |
| A7 | 파일 소유 | `orchestrator/worker/claude_worker.py`, `orchestrator/worker/run_smoke_tests.py`, `docs/jarvis-multi-agent-sop-v0.1.md`, 이 기록 |
| X1 | 범위 밖 | `_accept_main_check()`(accept 승인 전 검사, `:636`)는 A안에 적히지 않아 바꾸지 않는다. 승인 전에는 기록이 아직 바뀌지 않아 이 결함과 무관하다. `bot_minimal.py`, task 기록 형식, 다른 task 기록, Console은 바꾸지 않는다 |
| G1 | 저장소 공통 규칙 | `jarvis.bat` 접근 없음, push 없음, 외부 API·credential 없음, 명시 파일만 stage. task-0143 재실행은 이 task 밖이며 Owner의 Discord `/go`로 한다 |

## File ownership

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/worker/claude_worker.py`, `orchestrator/worker/run_smoke_tests.py`, `docs/jarvis-multi-agent-sop-v0.1.md`, 이 기록 |
| deny | `jarvis.bat`, `adapters/`, `apps/`, 다른 `memory/tasks/*.md`, `docs/master-plan.md`, `scripts/` |

Docs 판정: `not_required`. SOP 한 줄은 승인 범위로 candidate에 함께 들어가 Reviewer·QA를 받는다.

## 검증 계획

| # | 항목 |
| --- | --- |
| V1 | Worker smoke 전체(`python -B orchestrator/worker/run_smoke_tests.py`, 가짜 claude) |
| V2 | Discord self-check, discord-intake smoke(봇 코드는 안 바꾸지만 같은 파이프라인을 쓴다) |
| V3 | SOP validator(10.2 parity 포함), Console smoke |
| V4 | `git diff --check`, 변경 범위가 owned 파일과 같음 |
| V5 | 강도: 예외를 없애면 새 회귀 테스트가 실패하고, 예외를 넓히면(모든 task 기록 제외) A5가 실패한다 |
| V6 | 정리: 임시 디렉터리·worktree·listener 없음, `jarvis.bat` untracked, 보존 worktree 그대로 |

## 구현 착수

2026-10-14 14:52 UTC에 Jarvis Console Start(Preview + Confirm, `START TASK`)로 `TODO→DOING`을 적용했다(Console 결과
`result_type: updated`, `TODO → DOING`, `no_execution: true`). 서버는 `--no-browser`로 띄운 뒤 소유 PID만 종료했다.

## 구현 (Implementer)

baseline `a022887d3654e226796dcca8e4190fea073cfe3e`.

| 파일 | 변경 |
| --- | --- |
| `orchestrator/worker/claude_worker.py` | `_main_tracked_changes(repo_root, task_id)` 추가: `git status --porcelain --untracked-files=no -- . ":(exclude,literal)memory/tasks/<task_id>.md"`. `run_pipeline()` 사전 검사와 `_integrate_and_checkpoint()` 반영 직전 검사가 이 함수를 쓴다. 사유 코드(`preflight:main_tree_dirty`, `integrate:main_tree_dirty`)는 그대로다. `_accept_main_check()`는 바꾸지 않았다(X1) |
| `orchestrator/worker/run_smoke_tests.py` | 가짜 Reviewer 모드 `dirtymain`(검토 중 main의 `README.md` 변경) 추가. `run_pipeline` 경우: 커밋되고 바뀐 자기 기록 → 성공하고 checkpoint가 바뀐 기록을 커밋, 자기 기록 + `README.md` 변경 → `preflight:main_tree_dirty`, 다른 task의 커밋된 기록 변경 → `preflight:main_tree_dirty`, 검토 중 `README.md` 변경 → `integrate:main_tree_dirty`, 커밋되고 바뀐 자기 기록으로 resume → 성공. 봇 경로: 커밋된 TODO 기록의 `/go` → DONE, task-0143 형태(실패 뒤 기록 커밋, `/go` 재시도) → DONE. accept: 커밋된 기록을 승인이 바꾸는 경우 → 반영 |
| `docs/jarvis-multi-agent-sop-v0.1.md` | 10.2 9항 끝에 예외 한 문장 |

## 검증 (Implementer 실행)

| # | 항목 | 결과 |
| --- | --- | --- |
| V1 | Worker smoke | `PYTHONUTF8=1`로 total=345 failed=0(baseline `a022887`은 같은 조건에서 310/0, 새 검사 35개). UTF-8 모드 없이는 baseline도 같은 8개가 실패한다(아래 환경 관찰) |
| V2 | Discord self-check, discord-intake smoke | self-check(`PYTHONUTF8=1`) total=92 모두 ok. intake total=132 failed=0 |
| V3 | SOP validator, Console smoke | validator PASS(negative_checks=129, negative_failures=0, 10.2 parity 포함), Console smoke PASS |
| V4 | `git diff --check`, 범위 | exit 0. 변경은 owned 3개 파일과 이 기록 |
| V5 | 강도(임시 worktree, `PYTHONUTF8=1`) | 예외 제거(이전 검사) FAIL 21개, 예외를 모든 task 기록으로 확대 FAIL 4개(다른 task 기록 변경을 통과시킴), 반영 직전 검사만 이전 방식 FAIL 19개. 복구본 345/0. 임시 worktree 삭제 |
| V6 | 정리 | 임시 worktree·스크립트 삭제, listener 없음, 보존 worktree 그대로, `jarvis.bat` untracked |

## 환경 관찰 (이 task 범위 밖, 수정하지 않음)

이 데스크톱의 Python 기본 인코딩은 `cp949`(`sys.flags.utf8_mode=0`)다. 이 상태에서 baseline `a022887`의 Worker smoke는 repair·resume
경우 8개가 실패하고 중간에 멈추며(가짜 claude가 한국어 prompt를 stdin에서 읽어 `FAKE_LOG`에 쓰다 예외), Discord self-check는
`_summarize_execution_output`의 `stdout`이 `None`이라 `AttributeError`로 멈춘다. `PYTHONUTF8=1`이면 둘 다 통과한다. 이 task의 변경과
무관한 기존 상태이며, 테스트 하네스·실행 출력 디코딩의 인코딩 고정은 후속 후보다. 이 task의 검증은 baseline과 같은 `PYTHONUTF8=1` 조건에서 비교했다.
