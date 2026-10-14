# task-0157-go-preflight-exempt-own-task-record

- id: `task-0157-go-preflight-exempt-own-task-record`
- title: `Worker 파이프라인 main 검사에서 실행 대상 task 자신의 기록 파일만 예외 처리`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-14 14:51 UTC`
- updated_at: `2026-10-14 16:14 UTC`
- summary: `Discord /go가 Worker 실행 전에 task 기록에 상태 전이를 쓰고 멈춘 실행은 실패 결과를 기록에 쓰므로, 기록이 이미 커밋된 task는 추적 파일 변경 검사(main_tree_dirty, accept_main_dirty)에 항상 걸린다(task-0143 재시도 실패로 확인). 실행 전, accept 승인 전, 반영 직전 세 검사가 실행 대상 task 자신의 기록 파일 하나만 예외로 두고 그 밖의 추적 변경은 그대로 막게 하며, 커밋된 기록의 TODO·FAILED 재시도·resume·accept 회귀 테스트와 SOP 10.2 한 문장을 더한다. push는 하지 않는다.`
- source_command: `Owner 승인: A안으로 수정 진행`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `a022887d3654e226796dcca8e4190fea073cfe3e` (main HEAD = origin/main, push 직후) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 보존 대상 | task-0143 `-r3` worktree/branch(`e05c69c`), task-0149 worktree/branch 2개, task-0154 worktree/branch |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=2`, `repair_count=2` (repair 1 뒤 1, Owner가 예산을 2로 증액한 뒤 repair 2로 2) |

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
| A7 | 파일 소유 | 승인이 이름 붙인 3개: `orchestrator/worker/claude_worker.py`, `orchestrator/worker/run_smoke_tests.py`, `docs/jarvis-multi-agent-sop-v0.1.md`. 이 기록은 승인 원문에 없고, SOP 정식 task 생성 절차에 따라 Manager가 더한 것이다 |
| A8 | Owner 결정 (1): accept 승인 전 검사(`_accept_main_check()`)도 같은 예외 | repair 1에서 `_accept_main_check()`가 같은 `_main_tracked_changes()`를 쓴다. 실제 순서(커밋된 기록 → 실행이 멈추며 실패 결과를 기록에 씀 → accept → 반영)의 회귀 테스트와 다른 추적 변경은 여전히 `accept_main_dirty`로 막는 테스트를 둔다. SOP 문장을 "실행 전, accept 승인 전, 반영 직전"으로 고친다 |
| P1 | `a022887 push해줘` | 이 task 생성 전에 끝났다: fetch 뒤 원격이 `12d0a9d`이고 `a022887`의 부모가 `12d0a9d`, 앞섬 1·뒤처짐 0, 변경 task-0143 기록 1개, `git diff --check` 통과를 확인하고 `12d0a9d..a022887`만 push했다. push 뒤 원격 HEAD `a022887`. G1의 "push 없음"은 이 task의 candidate와 checkpoint에만 해당한다 |
| X1 | 범위 밖 | `bot_minimal.py`, task 기록 형식, 다른 task 기록, Console은 바꾸지 않는다. (첫 candidate의 X1은 `_accept_main_check()`를 범위 밖으로 두고 "승인 전에는 기록이 아직 바뀌지 않아 무관하다"고 적었으나 틀렸다. 멈춘 실행이 실패 결과를 기록에 쓰기 때문이다. Owner 결정 (1)로 A8에서 다룬다) |
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

## Reviewer 결과 (candidate `7c57141f8518fa7b64a32962fdce4d2bca069b68`): FINDINGS

`self_deviations: []`, `unverified` 8건. findings 3건:

1. major: 실제 accept 경로는 여전히 막힌다. 커밋된 기록의 실행이 `qa_unverified_owner_review`로 멈추면 봇의 기록 콜백이 실패
   결과를 그 기록에 쓰고(커밋하지 않음), `/go <id> accept`의 `_accept_main_check()`는 엄격한 검사라 `accept_main_dirty`로 멈춘다.
   기록을 먼저 커밋하면 `accept_baseline_moved`다. 추가한 accept 테스트는 기록을 바꾸지 않는 가짜 `record_result`를 써서 이 순서를
   재현하지 않았다. Manager 요약 X1("승인 전에는 기록이 아직 바뀌지 않아 무관")은 틀렸다.
2. minor: Manager 요약에 승인 조건 "a022887 push해줘"와 그 충족이 없다.
3. minor: 승인은 소유 파일 3개를 이름 붙였는데 A7이 이 기록을 표시 없이 4번째로 넣었다.

Manager 판정: 1은 `bot_minimal.py:1991-2004`(기록 콜백이 `_apply_execution_result`로 기록에 씀)와 `claude_worker.py:650`(엄격 검사)로
확인했다. 고치려면 A안에 적히지 않은 `_accept_main_check()`를 바꿔야 해 범위 확대이므로 SOP 6절에 따라 멈추고 Owner에게
escalation했다. 선택지는 (1) A를 `_accept_main_check()`까지 넓혀 고침, (2) 범위 유지·알려진 제약으로 기록이었다.

## Owner 결정: escalation 답 (원문)

```text
(1)로 진행해
```

(1)의 내용(Director 보고 원문):

```text
- **(1, 추천) A를 `_accept_main_check`까지 넓힘.** accept 승인 전 검사에도 같은 자기 기록 예외를 둡니다. accept 테스트를 실제 순서로 다시 짭니다: 커밋된 기록 → 실패 결과가 기록에 씀 → accept → 반영. 다른 추적 변경이 있으면 여전히 `accept_main_dirty`로 막히는 경우도 넣습니다. SOP §10.2 문장도 "실행 전, accept 승인 전, 반영 직전"으로 고칩니다. 이렇게 해야 커밋된 기록의 accept가 실제로 쓸 수 있습니다.
```

## repair 1

| 파일 | 변경 |
| --- | --- |
| `orchestrator/worker/claude_worker.py` | `_accept_main_check(repo_root, baseline, task_id)`가 `_main_tracked_changes()`를 쓴다(호출 1곳 갱신). 사유 코드 `accept_main_dirty`는 그대로 |
| `orchestrator/worker/run_smoke_tests.py` | accept 테스트를 실제 순서로 다시 짰다: 기록 커밋 → attempt(`qa_unverified_owner_review`) → 실패 결과를 기록에 씀(봇 콜백 대신 직접) → `README.md`도 바뀌어 있으면 `accept_main_dirty`(아무것도 바뀌거나 기록되지 않음, 재시도 가능) → `README.md` 복구 뒤 accept(승인이 기록에 다시 씀) → 반영, checkpoint에 실패 결과와 승인 전이가 모두 들어감 |
| `docs/jarvis-multi-agent-sop-v0.1.md` | 9항 문장을 "실행 전, accept 승인 전, 반영 직전"과 "상태 전이와 실행 결과 기록이 쓰는"으로 고쳤다 |
| 이 기록 | Manager 요약 A7(이 기록은 SOP 절차로 더함), A8(Owner 결정 (1)), P1(push 조건과 충족), X1 정정, budget, 위 Reviewer 결과와 Owner 결정 |

이 repair로 candidate가 바뀌므로 이전 Reviewer 결과는 무효이고 새 candidate에 Reviewer → QA를 다시 실행한다.

repair 1 검증(Implementer 실행, 작업 트리): Worker smoke(`PYTHONUTF8=1`) total=347 failed=0. 강도(임시 worktree): 예외 제거 FAIL 21개,
모든 task 기록으로 확대 FAIL 4개, 반영 직전 검사만 이전 방식 FAIL 19개, accept 승인 전 검사만 이전 방식 FAIL 4개(실제 순서 accept
테스트가 `accept_main_dirty`로 멈춤), 복구본 347/0. Discord self-check(`PYTHONUTF8=1`) total=92 실패 0, discord-intake total=132
failed=0, SOP validator PASS, Console smoke PASS, `git diff --check` exit 0. 임시 worktree·스크립트 삭제.

## Reviewer 결과 (candidate `dac06daaff94c32dbd13b56670254a122e89e7f4`, repair 1 뒤): FINDINGS

`self_deviations: []`, `unverified` 8건. findings 1건(minor): 메타데이터 `summary`가 예외를 두 검사(사전 검사·반영 직전)에만 적용한다고
적는데, 코드는 Owner 결정 (1)과 SOP 문장대로 세 곳(실행 전, accept 승인 전, 반영 직전)에 적용한다. task 상태 영역의 기준인 메타데이터가
코드와 다르다.

Manager 판정: 지적이 맞다. 고치려면 이 기록을 바꿔야 하지만 repair 예산(1)이 소진됐고 호출 결함이 아니라 retry도 아니므로 SOP 5절에
따라 멈추고 Owner에게 escalation했다. 선택지는 (a) repair 예산을 2로 증액해 summary 수정, (b) SOP 8절에 따라 minor 수용이었다.

## Owner 결정: repair 예산 증액 (원문)

```text
(a)로 진행해, repair 예산 2로 늘려줘
```

이 증액은 task-0157에만 효력이 있다.

## repair 2

- 메타데이터 `summary`를 세 검사(실행 전, accept 승인 전, 반영 직전)와 멈춘 실행의 실패 결과 기록(`accept_main_dirty`)까지 적도록 고쳤다
  (3문장 유지).
- `updated_at`을 이 수정 시각 `2026-10-14 15:50 UTC`으로, 기준선 budget 행을 `repair_budget=2`, `repair_count=2`로 고치고 위 Reviewer 결과와 Owner 결정을 기록했다.
- 코드·테스트·SOP는 바꾸지 않았다(repair 1 candidate `dac06da`와 같다).

이 repair로 candidate가 바뀌므로 이전 Reviewer 결과는 무효이고 새 candidate에 Reviewer → QA를 다시 실행한다.

## Reviewer 결과 (candidate `cb36a384aedc489c218d86038a4ba70365957361`, repair 2 뒤): PASS

baseline `a022887d3654e226796dcca8e4190fea073cfe3e`, 누적 4개 파일. `findings: []`, `self_deviations: []`. `unverified` 9건 중 7건은
Q1–Q6로 넘겼다. `qa: none` 2건 중 "accept 테스트가 실패 결과를 봇 콜백 대신 직접 쓴다"는 아래 E2E로 확인했고, "a022887 push"는 Manager
요약 P1의 실행 근거(fetch·ls-remote)가 근거다.

## QA 결과 (candidate `cb36a384aedc489c218d86038a4ba70365957361`): PASS

candidate를 detached로 checkout한 임시 clean worktree(scratchpad)에서만 실행했다. QA 전·후 main HEAD와 candidate가 같았다.

| # | 검사 | 결과 |
| --- | --- | --- |
| Q1 | Worker smoke(`PYTHONUTF8=1`) | candidate total=347 failed=0(두 번, 두 번째는 새 worktree에서 실행 뒤 추적 변경 없음). baseline 비교는 아래 메모 |
| Q2 | Discord self-check(`PYTHONUTF8=1`), discord-intake | self-check total=92 실패 0, intake total=132 failed=0 |
| Q3 | SOP validator, Console smoke | validator PASS(negative_checks=129, negative_failures=0), Console smoke PASS |
| Q4 | `git diff --check a022887 cb36a38`, 범위 | exit 0. commit 3개(`7c57141`, `dac06da`, `cb36a38`), 4개 파일(M SOP·claude_worker·run_smoke_tests, A 이 기록). `jarvis.bat`은 candidate tree에 없음 |
| Q5 | 강도(변형마다 smoke 뒤 `git checkout` 복구) | 예외 제거 FAIL 21, 모든 task 기록으로 확대 FAIL 4, 반영 직전 검사만 이전 방식 FAIL 19, accept 승인 전 검사만 이전 방식 FAIL 4. 복구 뒤 347/0 |
| E2E | `qa: none` 항목: 실제 봇 콜백으로 커밋된 기록 accept | 임시 clone에서 `/work` → 기록 커밋 → `/go`(가짜 Reviewer `unverifiednone`) → `qa:qa_unverified_owner_review`로 멈추고 실제 기록 콜백이 실패 결과를 커밋된 기록에 씀(main 추적 변경은 그 기록 하나) → `/go <id> accept` → 반영, task `DONE`, checkpoint에 기록 포함, main 깨끗 |
| Q6 | 정리 | QA worktree 삭제, E2E 임시 디렉터리(`jarvis_qa0157_*`)는 파일 잠금으로 바로 안 지워져 뒤에 지웠다. 8790대 listener 없음, `jarvis.bat` untracked, 보존 worktree 4개와 task-0143 `-r3` branch 그대로 |

QA 메모:

- baseline 비교: 이번 QA의 baseline 실행(`a022887` detached worktree)은 `git rev-parse ''`로 멈췄다. smoke는 원본 checkout을 clone하는데,
  main이 `cb36a38`로 옮겨 `a022887`을 가리키는 branch가 없어 clone의 HEAD가 branch가 아니고 사전 검사의 `git symbolic-ref`가 실패한
  것이다. 이 테스트 하네스의 조건 문제이고 코드 차이와 무관하다. 같은 baseline은 main이 `a022887`이던 구현 단계(2026-10-14 14:5x UTC)에
  `PYTHONUTF8=1`로 total=310 failed=0이었고, 그 수치를 비교 기준으로 쓴다.
- 하네스 격리 약점(이 task 범위 밖, 수정하지 않음): resume 경우에서 앞 경우가 실패해 `exhausted.worktree`가 빈 문자열이면
  `Path("")`가 현재 디렉터리(원본 checkout)가 되어 smoke가 원본의 `apps/studyroom/content/glossary.json`을 고친다. 실패하는 실행
  (위 baseline, Q5 변형)에서만 생기고 통과하는 실행은 원본을 바꾸지 않는다(Q1 두 번째 실행 확인). baseline에도 같은 코드다. 후속 후보다.
- 임시 디렉터리: Worker smoke가 남기는 `%TEMP%\jarvis_worker_smoke_*`(task-0153 기록의 기존 잔여물 문제)는 이번 실행분도 남아 있다.
  task-0153 Owner 결정대로 지우지 않았다.

## Docs와 완료 조건 대조

- Docs: `not_required`(File ownership 절의 이유 그대로).
- SOP 8절: 같은 candidate `cb36a38`에 Reviewer PASS와 QA PASS. 이전 candidate의 Reviewer 결과(`7c57141`, `dac06da` FINDINGS)는 판정에
  쓰지 않았다. 범위 밖 변경·동시 source writer 없음. `jarvis.bat` untouched/untracked. push·외부 호출 없음. listener 없음.

## 다음 단계

status는 `DOING`이다. 이 기록을 record-only checkpoint commit으로 남긴다. DONE은 SOP 8절대로 Owner가 Jarvis Console Complete로 결정한다.
push는 하지 않는다. 반영 뒤 task-0143은 Owner의 Discord `/go`로 다시 실행할 수 있다(이 task 밖).
