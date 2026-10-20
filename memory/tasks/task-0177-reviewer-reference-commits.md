# task-0177-reviewer-reference-commits

- id: `task-0177-reviewer-reference-commits`
- title: `Reviewer 파일별 참조 커밋(reference commit) 지원`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-20 18:08 UTC`
- updated_at: `2026-10-20 18:26 UTC`
- summary: `Reviewer 정의에 파일별 참조 커밋(reference commit)을 더해, Manager가 지정하고 Owner 승인 원문에 적힌 scope 파일에 한해 Reviewer가 참조 커밋에서 candidate까지의 실제 diff를 독립적으로 읽을 수 있게 한다. candidate 변경 범위 판정과 검토 대상은 기존 baseline 규칙 그대로이고, 참조 diff는 그 파일의 검토 근거로만 쓰며 다른 변경을 승인하지 않는다. reviewer.md·reviewer.toml·validator·SOP·jarvis-reviewer-call Skill이 범위다. task-0176의 E2를 충족하려는 선행 작업이며 Worker 파이프라인은 바꾸지 않는다.`
- source_command: `Owner 결정: D1, Reviewer 파일별 참조 커밋 설계 task 등록 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `2f9dcc357e086d6ea77cd2792e5cbbe270b296e5` (등록 시점 main HEAD = task-0176 candidate, origin/main `7cf5c85`보다 9커밋 앞섬, push 없음). Start 때 다시 확인한다 |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 등록 방식 | 이 기록을 `TODO`로 작업 트리에만 만들었다(커밋·stage 없음). Start 승인 뒤 candidate에 포함한다 |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문)

```text
Owner 결정: D1을 선택합니다.
task-0176의 E2(Reviewer의 독립적인 실제 diff 검토)는 완화하지 않습니다. Reviewer 정의에 파일별 참조 커밋을 지원하는 공식 기능을 추가하는 방안을 별도 task로 등록하세요.
제약:

1. 현재 candidate `2f9dcc357e086d6ea77cd2792e5cbbe270b296e5`를 보존하세요.
2. task-0176은 `DOING` 상태로 유지하고, Reviewer와 QA를 실행하지 마세요.
3. 새 설계 task는 등록 및 계획 작성까지만 수행하고, 구현이나 상태 전이는 하지 마세요. 등록 후 Owner의 Start 승인을 기다리세요.
4. 설계 범위에는 `.claude/agents/reviewer.md`, `.codex/agents/reviewer.toml`, `scripts/validate_multi_agent_sop.py`, 관련 SOP 문서, `jarvis-reviewer-call` Skill을 포함하세요.
5. 참조 커밋은 지정된 파일의 실제 diff를 확인하기 위한 용도로만 사용하고, candidate의 변경 범위 판정과 최종 검토 대상은 기존 규칙대로 유지하는 설계를 우선하세요.
6. 참조 커밋을 통해 candidate에 포함되지 않은 변경을 임의로 승인하거나, 보호 범위 밖 파일을 수정할 수 없도록 검증 규칙을 명확히 하세요.
7. 등록한 task ID, 변경 예정 파일, 설계 기준, 테스트 항목, 위험 요소를 보고한 뒤 멈추세요.

금지:

* reset, revert, cherry-pick, push
* 기존 candidate 재구성
* task-0175 기록 및 보호 대상 수정
* Owner 승인 없는 구현이나 추가 상태 전이
```

## 배경 (기록에 따르면)

- task-0176은 로컬 커밋 `86a5d98`이 다섯 task 기록에 만든 summary 변경을 다시 검토해야 한다. 그 변경은 task-0176의 baseline(`b86394d`)에 이미 들어 있어 baseline..candidate 변경 범위에 나타나지 않는다.
- 현재 Reviewer 정의(`.claude/agents/reviewer.md`의 Allowed commands)는 diff를 Manager가 준 baseline 하나에 대해서만 허용하고, scope·evidence 파일은 candidate 시점에서만 읽는다. baseline을 `7cf5c85`로 주면 task-0175 기록이 범위 밖 변경으로 지적된다(정의의 findings 규칙). 그래서 E2(Reviewer의 독립적인 실제 diff 검토)를 공식 절차로 충족할 수 없었다.

## 범위 (Start 승인으로 확정)

| 구분 | 경로 |
| --- | --- |
| owned | `.claude/agents/reviewer.md`, `.codex/agents/reviewer.toml`, `scripts/validate_multi_agent_sop.py`, `docs/jarvis-multi-agent-sop-v0.1.md`, `.claude/skills/jarvis-reviewer-call/SKILL.md`, `memory/tasks/task-0177-reviewer-reference-commits.md` |
| deny | `jarvis.bat`, `.env` 계열, `orchestrator/worker/claude_worker.py`(Worker 파이프라인), 다른 agent 정의(`.codex/agents/*.toml` 중 reviewer 외, `.claude/agents/self-reviewer.md`), `memory/tasks/task-0175-team-manager-holds-to-on-hold.md`, `memory/tasks/task-0176-team-manager-holds-re-review.md`, task-0031·0035·0156 기록, 그 밖의 task 기록, master-plan(DONE 뒤 별도 기록 커밋 제외), 보호 worktree |

"관련 SOP 문서"는 `docs/jarvis-multi-agent-sop-v0.1.md`로 본다. `docs/codex-operating-rules.md`나 AGENTS.md를 바꿔야 한다고 판단되면 구현하지 않고 먼저 보고한다.

## 설계 기준

1. 선택 입력. Manager는 호출문에 `=== REFERENCE COMMITS ===` 블록을 둘 수 있다. 한 줄에 하나씩 `<40자 참조 커밋> -- <path>`. 블록이 없으면 Reviewer 동작은 지금과 같다(기존 호출과 Worker 파이프라인 호환).
2. 대상 제한(F1). `<path>`는 Manager가 준 scope 파일이어야 하고, 같은 경로와 참조 커밋의 전체 40자 해시가 OWNER APPROVAL (verbatim) 절에 명시돼 있어야 한다. 하나라도 어긋나면 그 호출은 BLOCKED다(fail closed). `jarvis.bat`·`.env` 계열·디렉터리·와일드카드는 참조 대상이 될 수 없다.
3. 참조 커밋 검증. 참조 커밋은 40자 전체 해시로만 받고, commit으로 해석되며 baseline의 조상이어야 한다. 아니면 BLOCKED.
4. 변경 범위와 검토 대상은 그대로. candidate 변경 범위 판정은 지금처럼 baseline..candidate다. 참조가 붙은 scope 파일은 baseline..candidate에 없어도 되는 유일한 scope 파일이며, 그 경우 baseline과 candidate 사이에서 바뀌지 않았어야 한다(바뀌었다면 기존 규칙대로 그 변경도 검토한다). 참조 diff는 그 파일의 검토 근거이며, 최종 검토 대상은 candidate 시점의 파일 내용이다.
5. 승인 확대 금지. 참조 커밋..baseline 사이의 다른 파일 변경은 검토하지 않고 승인하지도 않는다. Reviewer PASS는 지정된 파일의 candidate 내용과 baseline..candidate 변경에 대한 것일 뿐이며, 참조 diff를 본 파일은 보고서의 `commands_run`에 그 diff 명령(경로 포함)으로 남는다(출력 템플릿에 새 필드를 두지 않는다). 참조 diff에서 나온 결함은 다른 지적과 같은 findings다.
6. 새 허용 명령은 F2로 승인된 두 개뿐이다: `git merge-base --is-ancestor <reference> <baseline>`(설계 기준 3의 조상 확인), `git diff <reference> <hash> -- <path>`(경로 하나, 그 참조와 짝지어진 scope 파일). `git log` 형식은 넣지 않는다. 구현 중 꼭 필요하다고 판단되면 구현하지 않고 별도로 보고한다. 기존 형식과 마찬가지로 옵션 추가·파이프·리다이렉션 금지이며, 형식 밖 명령은 `self_deviations`다. 참조 커밋이 commit으로 해석되는지는 별도 명령 없이 `git merge-base --is-ancestor`의 결과로 함께 판정한다(조상이면 종료 0, 조상이 아니면 1, 해석할 수 없으면 오류). 0이 아니면 BLOCKED다.
7. 정의 일치. `.claude/agents/reviewer.md`와 `.codex/agents/reviewer.toml`이 같은 규칙 문장을 갖고, validator의 `REVIEWER_ROLE_CLAUSES`가 새 문장을 두 파일에서 강제한다.
8. 호출 조립. `jarvis-reviewer-call` Skill이 참조 블록을 조립하고, preflight에서 2·3의 조건(승인 원문에 적힘, scope 파일, 40자, 조상, 금지 경로)을 확인해 어긋나면 BLOCKED로 보고한다. 기준 4에 따라 참조가 붙은 scope 파일은 baseline..candidate에 없어도 되고, 있으면 기존 규칙대로 검토한다.
9. SOP. SOP에 참조 커밋의 목적·제한(1~5)을 적는다. retry·repair 예산, §8 완료 조건, §10 Worker 파이프라인은 바꾸지 않는다.

## 테스트 항목

- T1 `python -B scripts/validate_multi_agent_sop.py`가 PASS하고 negative mutation 검사 수가 늘어난다.
- T2 새 규칙 문장(설계 기준 1~5)을 reviewer.md 또는 reviewer.toml 한쪽에서만 지우는 mutation이 실패로 잡힌다. 새 허용 명령 두 줄(`git merge-base --is-ancestor <reference> <baseline>`, `git diff <reference> <hash> -- <path>`)은 각각 두 파일에서 지우거나 글자를 바꾸면 실패로 잡힌다.
- T2a 두 정의에 승인되지 않은 `<reference>` 명령 줄(예: `git log` … `<reference>`)을 더하는 mutation이 실패로 잡힌다(허용 명령 목록에 `<reference>`가 들어간 줄은 승인된 두 줄뿐).
- T3 기존 규칙 문장과 허용 명령 줄이 그대로다(기존 mutation 검사 전부 통과).
- T4 Worker 파이프라인 무변경: `orchestrator/worker/claude_worker.py` diff 없음, validator의 pipeline parity 통과, Worker smoke(`orchestrator/worker/run_smoke_tests.py`) 통과.
- T5 Skill 문서: 참조 블록 형식, preflight BLOCKED 조건 2·3·4가 적혀 있다. Skill의 allowed-tools와 Step 1 명령에는 승인된 두 명령 외의 `<reference>` 형식이 없다(Reviewer가 문서로 확인, QA가 문자열로 확인).
- T6 Console smoke, Discord self-check suite, `check_task_record.py`, `git diff --check`, `jarvis.bat` untracked.
- 실제 Reviewer가 참조 블록을 받아 동작하는지는 이 task의 결정론적 테스트로 보증할 수 없다. 첫 실제 사용은 task-0176의 Reviewer 호출이며, 그 결과는 task-0176에서 판단한다.

## 실행 계획

1. Owner의 Start 승인 원문을 기록하고 Console Start(`START TASK`, Preview 확인 뒤 Confirm).
2. owned 파일 구현, 이 기록에 Manager 요약(출처 칸 사용).
3. 사전 점검 → self-review 1회 → 사전 점검 재통과 → candidate commit.
4. Reviewer(exact hash, 승인 원문, 허용 명령 형식 요구. 이 task의 Reviewer는 변경 전 정의로 동작한다) → 유효한 PASS일 때만 같은 candidate로 QA(T1~T6).
5. Evidence와 Complete는 Owner의 별도 승인 뒤 Owner가 Preview/Confirm을 직접 수행한다(F3). Manager는 근거와 결과를 검증하고 보고한다. 그 뒤 DONE checkpoint, master-plan 기록 커밋. push는 별도 승인.

## 위험

- 에이전트 행동 규칙을 바꾸는 일이다(AGENTS.md 기준 지도의 에이전트 행동 규칙 영역). 규칙이 넓게 쓰이면 참조 커밋으로 검토받지 않은 변경을 끌어들일 수 있으므로 설계 기준 2·5를 문장으로 고정하고 validator로 강제한다.
- 이 task의 candidate가 task-0176 candidate(`2f9dcc3`) 위에 쌓이면, task-0176이 Hold할 때 HEAD = 검토된 candidate(SOP §4.8)가 성립하지 않는다. task-0176을 다시 진행할 때 새 candidate(이 경우 task-0176 기록에 Reviewer 호출 근거를 더하는 기록 커밋)가 필요할 수 있고, `2f9dcc3`은 이력에 그대로 남는다. 그 방식은 task-0176 재개 때 Owner가 정한다.
- Claude Code 세션은 agent 정의를 세션 시작 때 읽을 수 있다. 바뀐 reviewer.md가 같은 세션의 Reviewer에 바로 반영되는지는 미확인이며, task-0176 재개 전에 확인한다.
- `.codex/agents/reviewer.toml` 쪽 실제 Codex 실행은 이 환경에서 확인할 수 없다(문장 일치만 validator로 검사).

## Owner 결정 필요 (Start 전)

| # | 결정 | 권고 |
| --- | --- | --- |
| F1 | 참조 커밋은 Owner 승인 원문에 경로·해시가 적혀 있을 때만 허용(설계 기준 2) | 승인 |
| F2 | 새 허용 명령 3개(설계 기준 6) | 승인. 줄이라면 `git log` 형식을 뺀다 |
| F3 | Evidence와 Complete의 Preview/Confirm을 누가 하는지 | Owner가 직접(task-0176 E4와 같게) |

## Owner 결정: F1~F3 (원문)

```text
Owner 결정 — task-0177

* F1 승인: 참조 커밋은 Owner 승인 원문에 참조 경로와 전체 40자 해시가 명시된 경우에만 허용합니다.
* F2 부분 승인: 다음 두 명령만 새 허용 명령으로 승인합니다.
   * `git merge-base --is-ancestor <reference> <baseline>`
   * `git diff <reference> <hash> -- <path>`
`git log` 형식은 승인하지 않습니다. 꼭 필요하다고 판단되면 구현하지 말고 별도 보고하세요.
* F3 승인: Evidence와 Complete의 Preview/Confirm은 Owner가 직접 수행합니다.

이 결정은 task-0177의 Start 승인을 의미하지 않습니다.
먼저 위 결정을 task-0177 기록에 반영하고, 계획과 validator·Skill 테스트 항목을 두 명령 기준으로 정리하세요. 기록을 수정한 뒤 파서와 diff를 확인하고 보고하세요. 아직 구현, candidate 커밋, 상태 전이, Reviewer·QA 실행, push는 하지 마세요. 그 후 Owner의 명시적인 Start 승인을 기다리세요.
기존 candidate `2f9dcc357e086d6ea77cd2792e5cbbe270b296e5`와 task-0176의 `DOING` 상태를 보존하고, 보호 대상과 task-0175 기록은 수정하지 마세요.
```

F1~F3은 위 원문으로 정해졌다. (F1~F3 결정 시점) Start 승인은 없다. 설계 기준 2·6, 테스트 T2·T2a·T5, 실행 계획 5단계를 이 결정에 맞췄다. 위 "Owner 결정 필요" 표의 F2 권고(명령 3개)는 결정 전의 제안이고, 승인된 것은 두 명령이다.

## Owner 결정: Start 승인 (원문)

```text
Owner 결정 — task-0177 Start 승인
task-0177 `reviewer-reference-commits`의 Start를 승인합니다.

1. Console의 공식 Preview/Confirm 절차로 `START TASK`를 실행하세요. Discord `/go`는 사용하지 마세요.
2. Start 결과와 상태를 확인한 뒤, task-0177에 등록된 범위에서만 구현하세요.
3. 참조 커밋 기능은 Owner 승인 원문에 명시된 전체 40자 해시와 경로만 허용하세요. 새로 승인된 명령은 `git merge-base --is-ancestor <reference> <baseline>`과 `git diff <reference> <hash> -- <path>` 두 개뿐입니다.
4. 참조 diff는 검토 근거일 뿐입니다. 변경 범위 판정과 최종 검토 대상은 기존 규칙을 유지하고, 참조를 통해 다른 파일의 변경을 승인하지 못하도록 검증하세요.
5. Reviewer 정의 두 곳, validator, SOP, `jarvis-reviewer-call` Skill의 일관성을 확인하고 계획된 mutation 및 회귀 테스트를 실행하세요. Worker 파이프라인은 수정하지 마세요.
6. Self-review, 사전 점검, candidate 생성, Reviewer, 동일 candidate에 대한 QA 순으로 진행하세요. Reviewer와 QA가 PASS하지 않으면 후속 완료 절차로 넘어가지 마세요.
7. Evidence와 최종 Complete의 Preview/Confirm은 Owner가 직접 수행합니다. 해당 단계에 도달하면 결과를 보고하고 멈추세요.
8. Push는 하지 마세요.

보호 범위와 금지 사항은 그대로 유지합니다. `jarvis.bat`, task-0175·task-0176 기록, 보호 worktree를 수정하지 마세요. reset, revert, cherry-pick, 계획 밖 파일 수정이나 상태 전이가 필요해지면 실행하지 말고 먼저 보고하세요.
각 단계의 실제 결과를 근거와 함께 보고하고, 성공을 추정하거나 미실행 검증을 PASS로 기록하지 마세요.
```

## Start

Console Start Preview(`task-0177-reviewer-reference-commits`, TODO → DOING, `no_execution: true`)를 확인하고 `START TASK`로 Confirm했다. receipt: previous `TODO`, current `DOING`, updated_at `2026-10-20 18:14 UTC`. Confirm 전후 기록을 비교하니 status 줄만 바뀌었다. Discord `/go`는 쓰지 않았다. Start 직후 HEAD = `2f9dcc357e086d6ea77cd2792e5cbbe270b296e5`(baseline과 같음), tracked 변경 없음. Console 서버는 Start 뒤 껐다.

## 구현

| 파일 | 변경 |
| --- | --- |
| `.claude/agents/reviewer.md` | Allowed commands에 `git merge-base --is-ancestor <reference> <baseline>`과 `git diff <reference> <hash> -- <path>` 두 줄, "Reference commits (optional)" 절(표지 줄 `=== REFERENCE COMMITS ===`, 참조 줄의 유효 조건, 조상 확인, BLOCKED 조건, 참조 diff는 근거일 뿐, 참조가 붙은 scope 파일만 baseline..candidate에 없어도 됨, 다른 변경 승인 금지, `commands_run`의 참조 diff 명령이 경로를 보여 준다는 보고 규칙, `<reference>` 정의)을 더했고, verdict 규칙에 "reference binding failure"를 더했다 |
| `.codex/agents/reviewer.toml` | 위와 같은 문장(developer_instructions) |
| `scripts/validate_multi_agent_sop.py` | `REVIEWER_ROLE_CLAUSES`에 새 문장 14개(self-review 뒤 보고 규칙 1개 포함), `REVIEWER_REFERENCE_FORMS`(승인된 두 형식)와 `_validate_reviewer_reference_forms`(두 정의의 Allowed commands에서 `<reference>`가 든 줄이 정확히 두 형식인지), `SOP_REFERENCE_CLAUSES`(SOP 문장 2개), negative mutation 6개(각 정의에 `git log` 참조 형식 추가, diff 줄에서 경로 제거, SOP 문장 2개 제거)를 더했다. 새 문장 14개는 기존 규칙대로 두 정의에서 각각 지우는 mutation이 자동으로 생긴다 |
| `docs/jarvis-multi-agent-sop-v0.1.md` | §3 Reviewer에 참조 커밋 항목(목적, 승인 원문·조상 조건, 두 명령, 근거일 뿐이라는 제한, 다른 변경 승인 금지, §10 파이프라인은 쓰지 않음) |
| `.claude/skills/jarvis-reviewer-call/SKILL.md` | 입력 표에 Reference commits 행, allowed-tools에 `Bash(git merge-base --is-ancestor:*)`, Step 1에 조상 확인, Step 4에 참조가 붙은 scope 파일의 변경 범위 예외와 참조 줄 BLOCKED 조건, Step 5 호출문에 `=== REFERENCE COMMITS ===` 블록과 그 제한 |

구현 중 처음 넣은 BLOCKED 문장이 기존 문구 "return verdict BLOCKED with a blocking finding and review nothing"을 그대로 반복해, 기존 mutation 3개(`claude/codex_reviewer_clause_08_removed`, `reviewer_blocks_without_approval_removed`)가 잡히지 않았다. 새 문장을 "the verdict is BLOCKED with a blocking finding, and nothing is reviewed"로 바꿔 기존 검사가 다시 잡히게 했다.

## Implementer 검증 (작업 트리 기준, candidate 전)

- `python -B scripts/validate_multi_agent_sop.py`: status=PASS, negative_checks=167, negative_failures=0(self-review 수정 뒤 다시 실행. 수정 전에는 165). 같은 명령을 baseline(`2f9dcc3`)의 임시 detached worktree에서 돌리면 negative_checks=133(그 worktree는 지웠다).
- `python -B orchestrator/worker/run_smoke_tests.py`: total=494 failed=0, 종료 0. 이 smoke는 저장소의 커밋된 HEAD를 임시 clone해 돌리므로 작업 트리의 이번 변경이 아니라 바뀌지 않은 Worker 파이프라인을 확인한다. candidate 위에서는 QA가 다시 돌린다.
- `python -B apps/jarvis-console/run_smoke_tests.py`: "Jarvis Console smoke tests passed", 종료 0.
- `python -B adapters/discord/bot_minimal.py --self-check-suite`: 종료 0, 결과의 `"ok"` 117개가 모두 true.
- `tomllib`로 `.codex/agents/reviewer.toml` 파싱 통과. `git diff --check` 통과. Skill에서 `<reference>`가 든 명령은 `git merge-base --is-ancestor <reference> <baseline>` 하나다(나머지 두 곳은 참조 줄 형식 `<reference> -- <path>`).
- `orchestrator/worker/claude_worker.py`, `jarvis.bat`, task-0175·0176 기록은 바뀌지 않았다(`git status --short`).

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "Owner 결정: D1을 선택합니다." / "task-0176의 E2(Reviewer의 독립적인 실제 diff 검토)는 완화하지 않습니다." / "Reviewer 정의에 파일별 참조 커밋을 지원하는 공식 기능을 추가하는 방안을 별도 task로 등록하세요." | D1에 따라 이 task를 등록했다. task-0176의 E2는 완화하지 않고, 이 task가 Reviewer 정의에 파일별 참조 커밋을 공식 기능으로 더한다 |
| A2 | Owner 결정 (원문) | "현재 candidate `2f9dcc357e086d6ea77cd2792e5cbbe270b296e5`를 보존하세요." / "task-0176은 `DOING` 상태로 유지하고, Reviewer와 QA를 실행하지 마세요." / "새 설계 task는 등록 및 계획 작성까지만 수행하고, 구현이나 상태 전이는 하지 마세요." / "등록 후 Owner의 Start 승인을 기다리세요." | candidate `2f9dcc3`은 HEAD로 그대로 두었고 task-0176은 DOING이며 Reviewer·QA를 실행하지 않았다. 등록 단계에서는 기록과 계획만 쓰고 Start 승인을 기다렸다(구현과 이 task의 Start는 Start 승인 뒤) |
| A3 | Owner 결정 (원문) | "설계 범위에는 `.claude/agents/reviewer.md`, `.codex/agents/reviewer.toml`, `scripts/validate_multi_agent_sop.py`, 관련 SOP 문서, `jarvis-reviewer-call` Skill을 포함하세요." | owned 행의 다섯 파일(reviewer.md, reviewer.toml, validator, SOP, Skill)이 이 범위다. "관련 SOP 문서"는 `docs/jarvis-multi-agent-sop-v0.1.md`로 보았다 |
| A4 | Owner 결정 (원문) | "참조 커밋은 지정된 파일의 실제 diff를 확인하기 위한 용도로만 사용하고, candidate의 변경 범위 판정과 최종 검토 대상은 기존 규칙대로 유지하는 설계를 우선하세요." / "참조 커밋을 통해 candidate에 포함되지 않은 변경을 임의로 승인하거나, 보호 범위 밖 파일을 수정할 수 없도록 검증 규칙을 명확히 하세요." | 참조 diff는 짝지어진 경로의 검토 근거로만 쓰고 변경 범위 판정과 검토 대상(baseline..candidate, candidate 시점의 파일)은 그대로다. 다른 경로의 변경은 검토하지도 승인하지도 않고 PASS는 scope 밖 변경을 덮지 않는다. 참조는 scope 파일이고 승인 원문에 적혀 있고 baseline의 조상일 때만 쓰며, `jarvis.bat`·`.env`·디렉터리·와일드카드는 쓸 수 없다. validator가 이 문장들과 명령 형식을 강제한다 |
| A5 | Owner 결정 (원문) | "등록한 task ID, 변경 예정 파일, 설계 기준, 테스트 항목, 위험 요소를 보고한 뒤 멈추세요." | 등록 보고에서 task ID, 변경 예정 파일, 설계 기준, 테스트 항목, 위험을 보고하고 멈췄다 |
| A6 | Owner 결정 (원문) | "reset, revert, cherry-pick, push" / "기존 candidate 재구성" / "task-0175 기록 및 보호 대상 수정" / "Owner 승인 없는 구현이나 추가 상태 전이" | reset·revert·cherry-pick·push를 하지 않았고 기존 candidate를 재구성하지 않았으며 task-0175 기록과 보호 대상을 바꾸지 않았다. 상태 전이는 Owner의 Start 승인 뒤 이 task의 Console Start 하나뿐이다 |
| B1 | Owner 결정: F1~F3 (원문) | "Owner 결정 — task-0177" / "F1 승인: 참조 커밋은 Owner 승인 원문에 참조 경로와 전체 40자 해시가 명시된 경우에만 허용합니다." | 참조 줄은 경로와 전체 40자 해시가 승인 원문에 모두 적혀 있을 때만 유효하고, 아니면 Reviewer는 BLOCKED다(정의, SOP, Skill preflight) |
| B2 | Owner 결정: F1~F3 (원문) | "F2 부분 승인: 다음 두 명령만 새 허용 명령으로 승인합니다." / "`git merge-base --is-ancestor <reference> <baseline>`" / "`git diff <reference> <hash> -- <path>`" / "`git log` 형식은 승인하지 않습니다." / "꼭 필요하다고 판단되면 구현하지 말고 별도 보고하세요." | 허용 명령에 더한 것은 이 두 줄뿐이고 `git log` 형식은 넣지 않았다. validator가 Allowed commands에서 `<reference>`가 든 줄을 이 두 형식으로 한정하고, `git log` 형식을 더하거나 diff 줄에서 경로를 빼는 mutation을 잡는다. 구현 중 `git log` 형식이 필요하다고 판단한 곳은 없었다 |
| B3 | Owner 결정: F1~F3 (원문) | "F3 승인: Evidence와 Complete의 Preview/Confirm은 Owner가 직접 수행합니다." | Evidence와 Complete의 Preview/Confirm은 Owner가 직접 한다(실행 계획 5단계) |
| B4 | Owner 결정: F1~F3 (원문) | "이 결정은 task-0177의 Start 승인을 의미하지 않습니다." / "먼저 위 결정을 task-0177 기록에 반영하고, 계획과 validator·Skill 테스트 항목을 두 명령 기준으로 정리하세요." / "기록을 수정한 뒤 파서와 diff를 확인하고 보고하세요." / "아직 구현, candidate 커밋, 상태 전이, Reviewer·QA 실행, push는 하지 마세요." / "그 후 Owner의 명시적인 Start 승인을 기다리세요." | F1~F3 반영 때는 기록만 고치고 파서와 diff를 확인해 보고했으며, 구현·커밋·상태 전이·Reviewer·QA·push를 하지 않고 Start 승인을 기다렸다 |
| B5 | Owner 결정: F1~F3 (원문) | "기존 candidate `2f9dcc357e086d6ea77cd2792e5cbbe270b296e5`와 task-0176의 `DOING` 상태를 보존하고, 보호 대상과 task-0175 기록은 수정하지 마세요." | candidate `2f9dcc3`과 task-0176의 DOING을 보존했고 보호 대상과 task-0175 기록은 바꾸지 않았다 |
| C1 | Owner 결정: Start 승인 (원문) | "Owner 결정 — task-0177 Start 승인" / "task-0177 `reviewer-reference-commits`의 Start를 승인합니다." / "Console의 공식 Preview/Confirm 절차로 `START TASK`를 실행하세요." / "Discord `/go`는 사용하지 마세요." / "Start 결과와 상태를 확인한 뒤, task-0177에 등록된 범위에서만 구현하세요." | Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다. `/go`는 쓰지 않았고 기록에서 status 줄만 바뀐 것을 diff로 확인했다. 구현은 owned 다섯 파일과 이 기록뿐이다 |
| C2 | Owner 결정: Start 승인 (원문) | "참조 커밋 기능은 Owner 승인 원문에 명시된 전체 40자 해시와 경로만 허용하세요." / "새로 승인된 명령은 `git merge-base --is-ancestor <reference> <baseline>`과 `git diff <reference> <hash> -- <path>` 두 개뿐입니다." / "참조 diff는 검토 근거일 뿐입니다." / "변경 범위 판정과 최종 검토 대상은 기존 규칙을 유지하고, 참조를 통해 다른 파일의 변경을 승인하지 못하도록 검증하세요." | 정의 두 곳의 "Reference commits (optional)" 절, 허용 명령 두 줄, SOP Reviewer 항목, Skill preflight가 같은 제한을 적는다: 승인 원문에 적힌 40자 해시와 경로만, 두 명령만, 참조 diff는 근거일 뿐이고 범위 판정·검토 대상은 그대로, 다른 경로의 변경은 승인하지 않음 |
| C3 | Owner 결정: Start 승인 (원문) | "Reviewer 정의 두 곳, validator, SOP, `jarvis-reviewer-call` Skill의 일관성을 확인하고 계획된 mutation 및 회귀 테스트를 실행하세요." / "Worker 파이프라인은 수정하지 마세요." | 두 정의의 같은 문장 14개를 `REVIEWER_ROLE_CLAUSES`에, SOP 문장 2개를 `SOP_REFERENCE_CLAUSES`에 넣어 강제했다. validator negative 검사 133 → 167, PASS. 회귀: Worker smoke 494건 실패 0, Console smoke, Discord self-check suite 통과. `orchestrator/worker/claude_worker.py`는 바꾸지 않았다(아래 "Implementer 검증") |
| C4 | Owner 결정: Start 승인 (원문) | "Self-review, 사전 점검, candidate 생성, Reviewer, 동일 candidate에 대한 QA 순으로 진행하세요." / "Reviewer와 QA가 PASS하지 않으면 후속 완료 절차로 넘어가지 마세요." | self-review → 사전 점검 → candidate → Reviewer → 같은 candidate에 QA 순서로 하고, 둘 다 PASS가 아니면 완료 절차로 가지 않는다 |
| C5 | Owner 결정: Start 승인 (원문) | "Evidence와 최종 Complete의 Preview/Confirm은 Owner가 직접 수행합니다." / "해당 단계에 도달하면 결과를 보고하고 멈추세요." / "Push는 하지 마세요." | Evidence와 Complete의 Preview/Confirm은 Owner가 직접 하며 그 지점에서 결과를 보고하고 멈춘다. push하지 않는다 |
| C6 | Owner 결정: Start 승인 (원문) | "보호 범위와 금지 사항은 그대로 유지합니다." / "`jarvis.bat`, task-0175·task-0176 기록, 보호 worktree를 수정하지 마세요." / "reset, revert, cherry-pick, 계획 밖 파일 수정이나 상태 전이가 필요해지면 실행하지 말고 먼저 보고하세요." | 보호 범위와 금지 사항을 유지했다: `jarvis.bat`, task-0175·0176 기록, 보호 worktree를 바꾸지 않았다. 계획 밖 수정이나 상태 전이가 필요한 경우는 없었다 |
| C7 | Owner 결정: Start 승인 (원문) | "각 단계의 실제 결과를 근거와 함께 보고하고, 성공을 추정하거나 미실행 검증을 PASS로 기록하지 마세요." | 단계마다 실행한 명령의 실제 결과만 적고, 실행하지 않은 검증은 PASS로 적지 않는다 |

## 사전 점검과 Self-review

- 사전 점검 1회차(`check_task_record.py --baseline 2f9dcc3`): PASS, violations 0, staged 6, 인용 검사 49문장 모두 인용.
- self-review 1회(`claude -p --agent self-reviewer --tools Read,Grep,Glob`): 지적 4건(major 1, minor 3). candidate 전이라 repair가 아니다(SOP §3·§5). 처리:
  1. major, 설계 기준 5의 "보고서에 참조 diff를 본 파일을 따로 적는다"가 정의에 없음 → 두 정의의 "Reference commits (optional)" 절에 `commands_run`의 참조 diff 명령이 그 경로를 보여 준다는 규칙을 넣고 `REVIEWER_ROLE_CLAUSES`로 강제했다. 출력 템플릿에 새 필드를 두면 Worker 파이프라인이 Reviewer 보고를 읽는 방식에 영향을 줄 수 있어 필드는 더하지 않았고, 설계 기준 5를 그에 맞게 고쳤다.
  2. minor, 설계 기준 8의 "baseline..candidate 무변경"이 기준 4·Skill과 어긋남 → 기준 8을 기준 4와 같게 고쳤다.
  3. minor, SOP가 금지 경로·baseline 없음·보고 규칙을 적지 않음 → SOP 항목에 더했다.
  4. minor, T4의 "이름은 Start 때 확정" → Worker smoke로 적었다.
- 수정 뒤 사전 점검 2회차: PASS, violations 0, staged 6, 인용 검사 모두 인용. validator 167/0 PASS.
- 인용 문장과 승인 범위는 바꾸지 않았다. updated_at은 이 편집 시각 2026-10-20 18:26 UTC다(편집 스크립트가 UTC 시계를 읽어 넣음).
