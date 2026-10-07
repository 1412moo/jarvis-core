# task-0152-existing-attempts-gap-numbering

- id: `task-0152-existing-attempts-gap-numbering`
- title: `Worker attempt 번호를 빈 번호와 무관하게 찾고 최대 번호 다음으로 새 attempt 만들기`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-07 07:38 UTC`
- updated_at: `2026-10-07 08:05 UTC`
- summary: `claude_worker._existing_attempts()가 attempt 1부터 연속일 때만 세서, task-0143처럼 -r3만 남으면 /go 재시도가 attempt 1부터 다시 시작해 세 번째에 기존 -r3와 부딪치고 /go resume은 resume_no_previous_attempt로 실패한다. _attempt_numbers()를 재사용해 빈 번호와 무관하게 찾고 다음 attempt를 최대 번호+1로 정한다. 구현은 candidate commit으로 기록되었으며 Reviewer·QA는 Owner 지시 대기다.`
- source_command: `Owner 지시: task-0152 _existing_attempts 결함 수정 승인과 결정 1~3`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `cbed30fd2c8b84706c1ac827c2ed126cb3fe3b0e` (main HEAD, push 전) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 선행 task | task-0151(DONE): accept 식별용 `_attempt_numbers()` 추가. 이 결함은 그 기록의 후속 task 후보 |
| 보존 대상 | task-0143 r3 worktree/branch(`e05c69c`), task-0149 worktree/branch 2개(`8f0c58e`, r2 `bd1622e`) |

## 조사 결과 (read-only, 코드·저장소 기준)

- `_existing_attempts()`(`orchestrator/worker/claude_worker.py`)는 attempt 1부터 `_attempt_name()`의 worktree 디렉터리나
  `jarvis/` branch가 있는 동안만 세고, 처음 없는 번호에서 멈춘다. attempt 1(`<id>`)이 없으면 첫 반복에서 빈 목록이다.
- 호출부는 둘이다. `run_pipeline` 2단계 `attempt = len(_existing_attempts(...)) + 1`(개수 기준), `_plan_resume`의 이전 attempt 목록.
- task-0143 현재 상태: status `FAILED`, `execution_summary: scope:repair_no_changes`. branch는 `jarvis/<id>-r3`(`e05c69c`)
  하나뿐이고 `<id>`, `-r2`는 없다. `-r3` worktree가 등록돼 있고 HEAD `e05c69c`, 미커밋 변경 없음. `e05c69c`의 parent
  `7483e64`, 변경 파일 `apps/studyroom/content/glossary.json`. 기록(`c5cf969`)은 worktree 3개 보존을 적었지만 지금은 r3만
  남아 있고, 언제 지워졌는지는 저장소 기록으로 확인할 수 없다.
- task-0143 영향(현재 코드): `/go` 재시도는 attempt 1(`<id>`, 지워진 이름 재사용) → 2(`-r2`) → 3(`-r3`)에서 `git worktree add -b`가
  기존 branch로 거부돼 `git:git_failed`로 실패한다(r3는 훼손되지 않음). `/go resume`은 빈 목록이라
  `resume_no_previous_attempt`이며, `current_attempt`가 1이라 목록에 3이 들어와도 `a < current_attempt`에서 걸러진다.
- 고쳐도 task-0143 resume은 `resume_conflict`일 가능성이 높다. r3가 바꾼 `glossary.json`을 main도 `7483e64` 뒤에 바꿨다.
- `_attempt_numbers()`(task-0151)는 `(set[int], ambiguous)`를 돌려주며 빈 번호와 무관하게 모든 branch·worktree 디렉터리
  이름을 본다. `sorted(numbers)`는 `_existing_attempts()`의 반환 형태(`list[int]`, 오름차순)와 같고, 연속인 경우 결과도 같다.

## Owner 결정 (원문)

````text
조사 결과를 확인했습니다. 이 작업은 진행하세요.
Owner 결정
1. `_existing_attempts()` 연속 번호 결함
수정 승인합니다.
최소 변경으로 진행하세요.

```
def _existing_attempts(repo_root, worktree_root, task_id) -> list[int]:
    numbers, _ = _attempt_numbers(repo_root, worktree_root, task_id)
    return sorted(numbers)
```

그리고 `run_pipeline`의 다음 attempt 계산은 `len()`이 아니라 최대 번호 기준으로 바꾸세요.

```
attempt = max(_existing_attempts(...), default=0) + 1
```

목표:

* `-r3`만 존재 → 다음 `-r4`
* `-r1`, `-r3` 존재 → 다음 `-r4`
* `-r5`, `-r7` 존재 → 다음 `-r8`
* 빈 번호를 재사용하지 않음
* 기존 contiguous case의 동작은 유지

`_attempt_numbers()`의 docstring도 현재 의미에 맞게 최소 수정하세요.
2. `_plan_resume` 의미
이번 작업에서는 추가 변경하지 마세요.
가장 최근 attempt의 branch/worktree 불일치 등에 대한 별도 정책 변경은 범위 밖입니다. 기존 resume 규칙을 유지하세요.
3. `ambiguous`
이번 작업에서는 별도의 reject/error 상태를 만들지 마세요.
`_existing_attempts()`에서는 `_attempt_numbers()`의 `ambiguous` 플래그를 버리고 번호 목록만 기존 반환 형태로 제공하세요.
단, 구현 과정에서 실제로 다른 task 이름이 섞이는 안전성 문제가 확인되면 추측해서 수정하지 말고 보고하세요. 별도 follow-up으로 분리할 수 있습니다.
테스트
조사에서 제안한 테스트를 반영하세요.
최소 필수:

1. `_existing_attempts()` 직접 테스트
   * 없음
   * base만
   * 1,2,3
   * r3만
   * 1+r3
   * 5+r7
   * branch만
   * worktree만
2. 실제 경로 테스트
   * r3만 존재 → `/go`가 r4 생성
   * 기존 r3 branch/worktree/tip 보존
   * 1+r3 상태에서 resume이 r3 선택
   * r3만 존재하는 상태에서 `/go resume`이 `resume_no_previous_attempt`가 되지 않음
3. 기존 retry/resume 테스트 유지
4. 기존 전체 관련 smoke:
   * Worker smoke
   * Discord self-check
   * discord-intake
   * SOP validator
   * Console smoke
   * diff check

Console smoke는 조사에서 확인한 대로 `C:/work` 아래 LF checkout 조건에서 실행하세요.
범위
예상 변경:

* `orchestrator/worker/claude_worker.py`
* `orchestrator/worker/run_smoke_tests.py`
* 새 task 기록

SOP/task-model/validator/bot/Console은 실제 필요성이 확인되지 않는 한 수정하지 마세요.
작업 절차
아직 바로 코드를 수정하지 말고 먼저:

1. 새 task-0152 기록을 작성
2. 기존 task 생성/시작 규칙에 맞게 Console Start가 필요한지 확인
3. 실제 구현 전에 task 기록과 변경 계획을 먼저 보고

Owner 확인 없이 commit, DONE, push는 하지 마세요.
`jarvis.bat`은 이번에도 절대 건드리거나 stage하지 마세요.
최종 보고에는:

* task-0152 번호/상태
* 수정 파일
* 실제 diff 규모
* 테스트 결과
* task-0143에 대한 `/go` 및 `/go resume` 동작 변화
* 발견된 추가 위험
을 포함하세요.
````

## 변경 계획

| 파일 | 변경 |
| --- | --- |
| `orchestrator/worker/claude_worker.py` | `_existing_attempts()` 본문을 `numbers, _ = _attempt_numbers(...)`, `return sorted(numbers)`로 교체. `run_pipeline` 2단계를 `attempt = max(_existing_attempts(...), default=0) + 1`로. `_attempt_numbers()` docstring의 "Unlike _existing_attempts()" 문장을 현재 의미에 맞게 수정. `_plan_resume`은 변경 없음 |
| `orchestrator/worker/run_smoke_tests.py` | `_existing_attempts()` 직접 테스트 8가지, 실제 경로 테스트(-r3만 → /go가 -r4, r3 보존, 1+r3 resume이 r3 선택, -r3만에서 resume 진행) |
| 이 기록 | 계획·결정·구현·검증 기록 |

경우별 기대 동작(다음 attempt / resume 대상):

| 경우 | 다음 attempt | resume 대상 |
| --- | --- | --- |
| 없음 | 1 | 거절(`resume_no_previous_attempt`) |
| base(1)만 | 2 | 1 |
| 1, 2, 3 | 4 | 3 |
| `-r3`만 | 4 | 3 |
| 1 + `-r3` | 4 | 3 |
| `-r5` + `-r7` | 8 | 7(worktree 없으면 5) |
| branch만(worktree 없음) | 번호에 포함 | 기존 규칙대로 건너뜀(worktree 디렉터리 필요) |
| worktree 디렉터리만(branch 없음) | 번호에 포함 | 기존 규칙대로 선택, 이후 동작은 기존과 같음 |

## 완료 조건

1. `_existing_attempts()`가 `_attempt_numbers()`의 번호를 오름차순 `list[int]`로 돌려준다. `ambiguous`로 거절하지 않는다.
2. `run_pipeline`의 다음 attempt는 최대 번호 + 1이며 빈 번호를 재사용하지 않는다. 연속인 경우의 동작은 같다.
3. `_plan_resume`은 바뀌지 않는다.
4. 직접 테스트 8가지와 실제 경로 테스트 4가지를 추가하고, 기존 retry·resume 테스트를 유지한다.
5. Worker smoke, Discord self-check, discord-intake smoke, SOP validator, Console smoke(`C:/work` 아래 LF checkout), `git diff --check`,
   실제 변경 범위 확인이 모두 PASS한다.

## 범위 밖

- `_plan_resume` 의미 변경, 최근 attempt의 branch·worktree 불일치에 대한 새 정책
- `ambiguous`에 따른 거절이나 새 오류 상태
- SOP, task-model, validator, bot, Console 변경(실제 필요가 확인되지 않는 한)
- task-0143 자체의 재시도·resume 실행
- commit, DONE, push, `jarvis.bat`

## 구현 착수

Owner 지시("task-0152 계획을 확인했습니다. 그대로 진행하세요." 1. Console Start)로 `2026-10-07 07:40 UTC`에 Jarvis Console
Start(Preview + Confirm, `START TASK`)로 `TODO→DOING`을 적용했다. Console 결과는 `result_type: updated`, `TODO → DOING`,
`no_execution: true`였다.

## 구현 (Implementer)

baseline `cbed30fd2c8b84706c1ac827c2ed126cb3fe3b0e`. 아래 "candidate commit 근거"의 Owner 지시로 candidate commit에 기록한다.

| 파일 | 변경 |
| --- | --- |
| `orchestrator/worker/claude_worker.py` | `_existing_attempts()` 본문을 `numbers, _ = _attempt_numbers(...)`, `return sorted(numbers)`로 교체. `run_pipeline` 2단계를 `attempt = max(_existing_attempts(...), default=0) + 1`로 변경. `_attempt_numbers()` docstring을 현재 의미로 정정. `_plan_resume` 변경 없음 |
| `orchestrator/worker/run_smoke_tests.py` | `attempt_numbering()` 추가: `_existing_attempts()` 직접 테스트 8가지(없음, base, 1·2·3, `-r3`만, 1+`-r3`, `-r5`+`-r7`, branch만, worktree 디렉터리만), 실제 경로 테스트(`-r3`만일 때 `/go`가 `-r4`를 만들고 `-r3` branch·tip·worktree 유지, `-r3`만일 때 resume이 `-r3`를 가져와 `-r4`로 진행, 1+`-r3`일 때 resume이 `-r3`를 고르고 1과 `-r3` 유지). `main()`에서 호출 |

규모: 2개 파일 71 추가, 11 삭제(`claude_worker.py` 20줄 변경, `run_smoke_tests.py` 62줄 추가).

## 검증 (Implementer 실행)

| # | 항목 | 결과 |
| --- | --- | --- |
| V1 | Worker smoke (`PYTHONUTF8=1`) | 310/310 PASS (이전 289 + 신규 21). 기존 retry(`-r2`)·resume(none, resume, conflict, 거절 시 흔적 없음)·accept 검사 포함 |
| V2 | Discord self-check suite | 92/92 PASS |
| V3 | discord-intake smoke | 127/127, failed=0 (task 파일 수에 따라 늘어남) |
| V4 | `validate_multi_agent_sop.py` | PASS, negative_checks=129, negative_failures=0 |
| V5 | Jarvis Console smoke | PASS. `C:/work/jarvis-core` 메인 작업 트리(`skills.json` `w/lf`)에서 실행 |
| V6 | `git diff --check` | exit 0. `--stat`과 `--ignore-cr-at-eol --stat`이 같다 |
| V7 | 변경 범위 | 위 2개 파일과 이 기록. SOP·task-model·validator·bot·Console 변경 없음, `jarvis.bat` untracked 유지 |
| V8 | worktree | `git worktree list`는 main과 보존 대상 3개뿐. smoke는 임시 디렉터리에서만 실행 |

task-0143 실제 상태에 대한 확인(새 attempt를 만들지 않고 판단 함수만 호출, r3 HEAD 변화 없음):

- `_existing_attempts()`는 `[3]`(`ambiguous` False), 다음 attempt는 4(`jarvis/<id>-r4`). 수정 전에는 `[]`, 다음 attempt 1이었다.
- `_plan_resume(..., current_attempt=4)`는 r3를 찾은 뒤 `resume_conflict`(`apps/studyroom/content/glossary.json`)로 거절했다.
  수정 전에는 `resume_no_previous_attempt`였다.

추가로 확인한 위험(이번 task에서 수정하지 않음):

- 정리된 attempt 이름은 다시 쓰일 수 있다. 번호는 지금 남아 있는 branch·worktree 디렉터리에서만 찾으므로, 성공 뒤 정리된
  가장 높은 attempt나 손으로 지운 가장 높은 attempt의 이름은 다음 attempt가 다시 쓴다. 예: task-0149는 성공한 r3가 정리돼
  `[1, 2]`만 남아 다음이 3이다(task-0149는 DONE이라 `/go` 대상은 아니다). 수정 전에도 같았다.
- 계획 단계에서 보고한 `<id>-rN` 이름 겹침과 `_plan_resume`의 다른 task worktree 선택 가능성은 이번 구현·테스트에서 실제로
  발생하지 않았다. 현재 저장소에는 그런 task가 없다(task-0143 `ambiguous` False).

## candidate commit 근거

이 candidate commit은 아래 Owner 지시로 만든다. 범위는 지시가 정한 3개 파일이며 `jarvis.bat`은 제외한다. 이 절은 commit
직전에 기록했으므로 이 commit의 SHA는 여기에 적지 않는다.

```text
task-0152 구현과 자체 검증 결과를 확인했습니다. 다음 단계로 candidate commit을 만들어 주세요.
Candidate 범위
baseline:
`cbed30f`
포함할 파일은 정확히 3개입니다.

1. `orchestrator/worker/claude_worker.py`
2. `orchestrator/worker/run_smoke_tests.py`
3. `memory/tasks/task-0152-existing-attempts-gap-numbering.md`

`jarvis.bat`은 절대 stage/commit하지 마세요.
commit 전 확인

1. `git diff --check`
2. 변경 scope 확인
3. task-0152 기록이 현재 구현/테스트 결과와 일치하는지 확인
4. staged diff에 위 3개 파일만 있는지 확인
5. `git diff --cached --check`

commit message:
`fix(worker): handle sparse attempt numbering`
commit 후
다음을 확인하세요.

git status --short
git log -1 --oneline
git diff --stat cbed30f..HEAD

정상이라면 working tree에는 `?? jarvis.bat`만 남아야 합니다.
중요

* DONE 처리하지 마세요.
* Console Complete 실행하지 마세요.
* push하지 마세요.
* candidate commit 이후 Reviewer 단계로 넘어가기 전 결과를 보고하세요.

Reviewer/QA는 candidate SHA 확인 후 별도 지시하겠습니다.
```

(원문의 명령 3줄을 감싼 코드 블록 표시는 이 인용 블록 안에서 생략했다.)

## 다음 단계

status는 `DOING`이다. candidate commit 뒤 Reviewer·QA는 Owner 지시를 기다린다. push는 하지 않는다.
