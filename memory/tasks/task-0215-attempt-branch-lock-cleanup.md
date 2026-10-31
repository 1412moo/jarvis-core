# task-0215-attempt-branch-lock-cleanup

- id: `task-0215-attempt-branch-lock-cleanup`
- title: `남은 Worker attempt branch와 중첩 lock 폴더 정리`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-10-31 15:36 UTC`
- updated_at: `2026-10-31 16:26 UTC`
- summary: `task-0209가 남긴 로컬 jarvis/* branch 다섯 개(main에 들어간 두 개, 버려진 시도 세 개)와 저장소 밖 중첩 폴더 jarvis-core-worktrees/jarvis-core-worktrees(빈 lock 파일 하나)를 정리한다. Owner가 지울 대상 셋을 모두 승인했고 실행 직전 확인도 받아 지웠다. 바깥쪽 lock 파일, 코드, 다른 기록은 바꾸지 않고 push는 하지 않는다.`
- completion_evidence: `candidate 81ae6d892a3ea0521e7b01494deb2f9d9cd30d7b: Reviewer PASS (no findings), QA PASS (record checks, validator, diff --check; jarvis/* branches 0, commits kept as objects, origin unchanged, worktree list main only, only outer lock file left)`
- source_command: `Owner 지시: E1+E2 조사 뒤 task 등록 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `e1d7d2348233670c1b4bff40922d5f3cc0d1f983` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문)

```text
A안 승인, N2 종료. E1+E2는 조사만 진행하고 삭제는 별도 승인받는 방향을 추천합니다.

[Manager 질문]
Register the cleanup as a task and get deletion approval?

[Owner 답]
Register task
```

첫 줄의 "A안"과 "N2"는 이 task 범위가 아니다(N2 Team Manager ON_HOLD 다섯 개를 계속 보류한다는 결정이며, 이 기록은 그 결정을 옮겨 적을 뿐 다섯 기록을 바꾸지 않는다). E1·E2는 task-0213 기록 조사 절의 후보 표에 있는 행이다.

## Owner 결정 (원문, 착수 전 bounded question)

```text
[Manager 질문]
Which of the deletion targets do you approve?

[Owner 답]
Approve all as proposed
```

선택지 설명(Manager가 등록 보고 2절에 질문과 함께 보인 문구, Owner 원문 아님): "\"Approve all as proposed\"는 ①②③을 모두 지우는 안입니다." 여기서 ①은 main에 들어간 branch 2개(`80a61a8`, `f3bd53b`, `git branch -d`), ②는 버려진 시도 branch 3개(`e05c69c`, `8f0c58e`, `bd1622e`, `git branch -D`), ③은 중첩 폴더와 그 안의 빈 lock 파일이다. 같은 보고는 "어느 쪽이든 실제로 지우기 직전에 대상과 끝 커밋을 한 번 더 보여 드리고 확인받습니다."라고 적었다.

## 조사 (등록 전, baseline 기준)

### E1. 로컬 `jarvis/*` branch

`git ls-remote --heads origin`에 다섯 개 모두 없다(로컬에만 있다). `git worktree list`는 main 하나뿐이다.

| branch | 끝 커밋 | main 조상 | 내용 | 관련 task |
| --- | --- | --- | --- | --- |
| `jarvis/task-0143-studyroom-glossary-git-worktree-1-jarvis-example-task-0142-r3` | `e05c69c` | 아님 (main보다 1 앞) | glossary `git-worktree` 용어 추가. 같은 id가 main에 있다(`47781ee`) | task-0143 DONE |
| `jarvis/task-0149-studyroom-glossary-1` | `8f0c58e` | 아님 (1 앞) | glossary `vertical-slice` 용어 추가. task-0149 title은 Canonical Source Map이었고 이 id는 main에 없다 | task-0149 DONE |
| `jarvis/task-0149-studyroom-glossary-1-r2` | `bd1622e` | 아님 (1 앞) | glossary `canonical-source-map` 용어 추가. task-0149 기록의 execution_summary는 candidate `4c9873e`를 받았다고 적고, 같은 id가 main에 있다 | task-0149 DONE |
| `jarvis/task-0154-studyroom-glossary-owner-accept-1-jarvis-example-task-0151` | `80a61a8` | 맞음 | main 커밋을 가리킬 뿐 따로 남은 커밋 없음 | task-0154 |
| `jarvis/task-0200-studyroom-glossary-owner-accept-term-task-0154` | `f3bd53b` | 맞음 | 위와 같음 | task-0200 |

- 위 세 개는 main에 없는 커밋 하나씩을 가진 버려진 시도다. 지우면 잃는 내용은 `8f0c58e`의 `vertical-slice` 초안 하나이며 요청과 다른 용어였다. `git branch -D`가 필요하고 되돌리기 어렵다(reflog에 당분간 남음).
- 아래 두 개는 `git branch -d`로 지울 수 있다(main 조상이라 커밋을 잃지 않음).
- task-0209는 branch 다섯 개를 남겨 "필요하면 `git worktree add`로 다시 만들 수 있게" 했다(기록에 따르면). 이 task는 그 뒤의 정리다.

### E2. 저장소 밖 lock 폴더

- 저장소 옆 `../jarvis-core-worktrees/.jarvis-worker.lock`: 0바이트, 2026-10-18. `orchestrator/worker/claude_worker.py`의 `process_lock_path()`가 쓰는 Worker lock이며, OS 파일 잠금이라 프로세스가 끝나도 파일은 남는 것이 정상이다. 정리 대상이 아니다.
- 그 안의 중첩 폴더 `../jarvis-core-worktrees/jarvis-core-worktrees/`: `.jarvis-worker.lock`(0바이트, 2026-10-26 02:36) 하나만 있다.
- 생긴 이유(추정, 미확인): `WORKTREE_ROOT`의 기본값이 `REPO_ROOT.parent / "jarvis-core-worktrees"`라서, 코드가 attempt worktree 안에서 실행되면 이 중첩 경로가 lock 위치가 된다. 시각이 `jarvis/task-0200…` branch 끝 커밋(02:37)과 1분 차이다. 무엇이 실행됐는지는 확인하지 못했다.
- 그런 실행에서는 lock 파일이 달라져 "한 PC에 Worker 한 번만" 잠금이 공유되지 않는다. 이것은 코드 후보이며 이 task 범위 밖이다.

## 설계 방향 (등록 때 초안, A8·A15로 확정)

1. 실행 직전에 지울 대상과 끝 커밋을 모두 나열해 Owner에게 보이고 승인받은 것만 지운다(Owner 원문 "삭제는 별도 승인받는 방향").
2. 승인되면 main 조상 branch 두 개는 `git branch -d`, 버려진 시도 세 개는 지우기 직전 끝 커밋이 위 표와 같은지 다시 확인한 뒤 `git branch -D`로 지운다.
3. 중첩 폴더는 안에 `.jarvis-worker.lock` 하나뿐이고 그 파일을 잡은 프로세스가 없을 때만 지운다. 바깥쪽 lock 파일과 `jarvis-core-worktrees` 폴더 자체는 그대로 둔다.
4. 지운 뒤 branch 목록, `git worktree list`, 폴더 상태를 기록에 남긴다.

## 범위 (등록 때 초안, A8·A15로 확정)

| 구분 | 경로 |
| --- | --- |
| owned | 승인된 로컬 `jarvis/*` branch, 저장소 밖 중첩 폴더 `../jarvis-core-worktrees/jarvis-core-worktrees`, 이 task 기록 |
| deny | 승인되지 않은 branch, 원격 branch, 바깥쪽 `.jarvis-worker.lock`, lock 위치 코드 수정, 다른 task 기록, `jarvis.bat`, `.env`, push |

## 계획

1. Owner bounded question(지울 대상)에 답을 받는다.
2. Console Start(TODO → DOING).
3. 승인된 대상만 지우고 결과를 확인한다.
4. 사전 점검 → self-review → candidate(이 기록) → Reviewer → QA → Evidence·Complete → checkpoint. push는 별도 지시.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다(status·updated_at 줄만 바뀜, updated_at `2026-10-31 15:38 UTC`). Console은 실행 전에 껐다.

## Owner 결정 (원문, 삭제 직전 확인)

```text
[Manager 질문]
Delete now? (1) git branch -d: jarvis/task-0154-… (80a61a8), jarvis/task-0200-… (f3bd53b) — both main ancestors. (2) git branch -D: jarvis/task-0143-…-r3 (e05c69c), jarvis/task-0149-studyroom-glossary-1 (8f0c58e), jarvis/task-0149-studyroom-glossary-1-r2 (bd1622e) — not on main, none on origin. (3) Remove folder ../jarvis-core-worktrees/jarvis-core-worktrees (only an empty .jarvis-worker.lock). The outer lock file stays. The running Discord bot runs from the main repo, so it does not use the nested lock.

[Owner 답]
Delete all three groups (Recommended)
```

선택지 설명(Manager 문구, Owner 원문 아님): "Run (1), (2) and (3) exactly as listed, then record the results."

## 실행 전 재확인

- 다섯 branch의 끝 커밋이 조사 표와 같았다(`80a61a8`, `f3bd53b`는 main 조상, `e05c69c`, `8f0c58e`, `bd1622e`는 아님). `git ls-remote --heads origin`에는 다섯 개 모두 없었다. `git worktree list`는 main 하나뿐이었다.
- `../jarvis-core-worktrees` 안에는 바깥쪽 `.jarvis-worker.lock`, 중첩 폴더, 그 안의 `.jarvis-worker.lock` 세 항목만 있었다.
- 실행 중인 python 프로세스는 메인 저장소의 `adapters/discord/bot_minimal.py` 하나였다. 그 프로세스가 중첩 파일을 쓰지 않는다는 것은 추론이다. 근거는 기본 `WORKTREE_ROOT`(`REPO_ROOT.parent / "jarvis-core-worktrees"`)가 메인 저장소에서는 바깥쪽 폴더가 된다는 것이다. `JARVIS_WORKTREE_ROOT`는 사용자·시스템·현재 셸 환경변수에 없었다. `.env`는 열지 않아 거기 설정이 있는지는 확인하지 않았다. 직접 확인한 사실은 다음 절의 파일 삭제가 공유 위반 없이 성공했다는 것이다(Windows에서 잠긴 파일은 지울 수 없다).

## 실행

- `git branch -d`로 `jarvis/task-0154-…`(was `80a61a8`)와 `jarvis/task-0200-…`(was `f3bd53b`)를 지웠다.
- `git branch -D`로 `jarvis/task-0143-…-r3`(was `e05c69c`), `jarvis/task-0149-studyroom-glossary-1`(was `8f0c58e`), `jarvis/task-0149-studyroom-glossary-1-r2`(was `bd1622e`)를 지웠다.
- 중첩 폴더 안이 `.jarvis-worker.lock` 하나뿐인지 확인한 뒤 그 파일을 지우고 빈 폴더를 `rmdir`로 지웠다(재귀 삭제 없음). 두 명령 모두 오류 없이 끝났다.
- 설계 1과 같이, 지울 대상 셋은 질문 하나에 모두 나열해 보였고 Owner가 한 번에 승인했다(A15).

## 실행 결과 확인

- `git branch --list 'jarvis/*'`는 0개다. `git worktree list`는 main 하나뿐이다.
- `../jarvis-core-worktrees` 안에는 바깥쪽 `.jarvis-worker.lock`만 남았다.
- 세 커밋 `e05c69c`, `8f0c58e`, `bd1622e`는 지운 직후 `git cat-file -t`가 아직 `commit`이다(gc 전까지 객체가 남음).
- 원격 branch, 바깥쪽 lock 파일, 코드, 다른 기록은 바꾸지 않았다.

## 사전 점검

`check_task_record.py --require-quotes`는 violations=0, status=PASS다. 경고 `owned but not changed since the baseline: jarvis-core-worktrees/jarvis-core-worktrees`가 하나 나온다. 그 owned 항목은 저장소 밖 폴더이고(로컬 branch도 마찬가지로) git diff에 나타나지 않으므로 예상된 경고다. 실제 변화는 실행 결과 확인 절에 적었다.

## Self-review

staged 기록에 self-reviewer를 한 번 돌렸다(Reviewer 판정 아님). minor 네 건이 나왔고 candidate 전에 모두 고쳤다: 설계·범위 절 제목의 "초안" 표기, 설계 1의 "하나씩"과 실제 한 번 승인의 차이, 중첩 lock을 잡은 프로세스가 없다는 것이 추론임을 밝히지 않음, 사전 점검 결과와 경고 설명 누락과 owned 경로의 `../` 누락.

## Reviewer·QA 결과 (candidate `81ae6d892a3ea0521e7b01494deb2f9d9cd30d7b`)

- Reviewer: verdict PASS, findings 없음, self_deviations 없음. unverified로 남긴 것은 저장소 밖 사실과 로컬 branch 상태(허용된 명령 형식으로 볼 수 없음)이며 아래 QA가 확인했다.
- QA(기록만 바뀐 변경이라 가장 가벼운 충분한 방법, 메인 작업 트리에서 HEAD = candidate, task-0209와 같은 방식):
  - 변경 파일은 이 기록 하나이고, `jarvis.bat`은 트리에 없다. `git diff --check` 통과, `check_task_record.py --require-quotes` violations=0 PASS, SOP validator PASS.
  - `git branch --list 'jarvis/*'`는 0개다. 다른 로컬 branch는 남아 있다(전체 35개).
  - 다섯 커밋은 아직 commit 객체로 있고, `80a61a8`·`f3bd53b`만 main 조상이다.
  - `git ls-remote --heads origin 'jarvis/*'`는 0개다(원격은 원래 없었고 바뀌지 않았다).
  - `git worktree list`는 main 하나뿐이다. `../jarvis-core-worktrees` 안에는 바깥쪽 `.jarvis-worker.lock`만 남았다.
- QA 판정: PASS.

## Owner 결정 (원문, Complete)

```text
[Manager 질문]
task-0215 passed Reviewer (PASS) and QA (PASS) on candidate 81ae6d8. Record Completion Evidence and run Console Complete (DOING → DONE), then make the DONE checkpoint and master-plan date-entry commits (no push)?

[Owner 답]
Complete 진행 (Recommended)
```

선택지 설명(Manager 문구, Owner 원문 아님): "Record evidence and Complete in Console, then commit the DONE checkpoint and the master-plan date entry locally. No push."

## Complete

Record Completion Evidence(Preview 확인 뒤 Confirm, updated_at `2026-10-31 16:26 UTC`)로 completion_evidence를 남긴 뒤, Owner 결정에 따라 Console Complete Preview(DOING → DONE)를 확인하고 `Confirm Complete`로 DONE이 됐다(updated_at `2026-10-31 16:26 UTC`). Console은 끈 상태다. push는 하지 않았다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다. 오른쪽 칸에서 "Manager 해석"이라고 적은 부분은 승인 원문에 없는 내용이며, 근거가 선택지 설명(Manager 문구, Owner 원문 아님)이거나 Manager 판단이다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "A안 승인, N2 종료." | 이 task 범위가 아니다. N2 다섯 기록은 바꾸지 않았다 |
| A2 | Owner 결정 (원문) | "E1+E2는 조사만 진행하고 삭제는 별도 승인받는 방향을 추천합니다." | 조사 뒤 등록했고, 삭제는 A8·A15 승인 뒤에만 했다 |
| A3 | Owner 결정 (원문) | "[Manager 질문]" | 질문의 표지 |
| A4 | Owner 결정 (원문) | "Register the cleanup as a task and get deletion approval?" | A6의 질문 |
| A5 | Owner 결정 (원문) | "[Owner 답]" | 답의 표지 |
| A6 | Owner 결정 (원문) | "Register task" | 이 기록을 TODO로 등록했다 |
| A7 | Owner 결정 (원문, 착수 전 bounded question) | "Which of the deletion targets do you approve?" | A8의 질문 |
| A8 | Owner 결정 (원문, 착수 전 bounded question) | "Approve all as proposed" | Console Start 뒤 실행했다. Manager 해석(선택지 설명 근거): ①②③을 모두 지운다 |
| A9 | Owner 결정 (원문, 삭제 직전 확인) | "Delete now?" | A15의 질문 |
| A10 | Owner 결정 (원문, 삭제 직전 확인) | "(1) git branch -d: jarvis/task-0154-… (80a61a8), jarvis/task-0200-… (f3bd53b) — both main ancestors." | 실행 절 첫 줄 |
| A11 | Owner 결정 (원문, 삭제 직전 확인) | "(2) git branch -D: jarvis/task-0143-…-r3 (e05c69c), jarvis/task-0149-studyroom-glossary-1 (8f0c58e), jarvis/task-0149-studyroom-glossary-1-r2 (bd1622e) — not on main, none on origin." | 실행 절 둘째 줄. 끝 커밋과 원격 없음은 실행 전 재확인 절 |
| A12 | Owner 결정 (원문, 삭제 직전 확인) | "(3) Remove folder ../jarvis-core-worktrees/jarvis-core-worktrees (only an empty .jarvis-worker.lock)." | 실행 절 셋째 줄 |
| A13 | Owner 결정 (원문, 삭제 직전 확인) | "The outer lock file stays." | 바깥쪽 lock 파일은 남았다(결과 확인 절) |
| A14 | Owner 결정 (원문, 삭제 직전 확인) | "The running Discord bot runs from the main repo, so it does not use the nested lock." | 질문의 근거 설명. 실행 전 재확인 절의 프로세스 확인 |
| A15 | Owner 결정 (원문, 삭제 직전 확인) | "Delete all three groups (Recommended)" | 세 묶음을 질문에 적은 그대로 지웠다(실행·결과 확인 절) |
| A16 | Owner 결정 (원문, Complete) | "task-0215 passed Reviewer (PASS) and QA (PASS) on candidate 81ae6d8." | A18의 질문 배경. Reviewer·QA 결과 절과 같다 |
| A17 | Owner 결정 (원문, Complete) | "Record Completion Evidence and run Console Complete (DOING → DONE), then make the DONE checkpoint and master-plan date-entry commits (no push)?" | A18의 질문 |
| A18 | Owner 결정 (원문, Complete) | "Complete 진행 (Recommended)" | Console로 Completion Evidence를 남기고 Complete했다(Complete 절). DONE checkpoint와 master-plan 날짜 항목은 로컬 커밋만 하고 push하지 않는다 |
