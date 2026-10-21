# task-0177-reviewer-reference-commits

- id: `task-0177-reviewer-reference-commits`
- title: `Reviewer 파일별 참조 커밋(reference commit) 지원`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-10-20 18:08 UTC`
- updated_at: `2026-10-21 03:51 UTC`
- summary: `Reviewer 정의에 파일별 참조 커밋(reference commit)을 더해, Manager가 지정하고 Owner 승인 원문에 적힌 scope 파일에 한해 Reviewer가 참조 커밋에서 candidate까지의 실제 diff를 독립적으로 읽을 수 있게 한다. candidate 변경 범위 판정과 검토 대상은 기존 baseline 규칙 그대로이고, 참조 diff는 그 파일의 검토 근거로만 쓰며 다른 변경을 승인하지 않는다. reviewer.md·reviewer.toml·validator·SOP·jarvis-reviewer-call Skill이 범위다. task-0176의 E2를 충족하려는 선행 작업이며 Worker 파이프라인은 바꾸지 않는다.`
- completion_evidence: `candidate 80cb647ad739f5505d4cd31161006aa74a3b2e81: Reviewer 4 retry PASS (findings 0, self_deviations 0; first run invalid, SOP 5 retry 1/1). QA PASS on the same candidate in a temp worktree: validator PASS 170/0 (15 new clauses x2 + 7), reference forms only merge-base and diff in both definitions, orchestrator unchanged, Worker smoke 494/0, Skill forms, Console smoke, Discord self-check 117 ok, check_task_record PASS, diff --check clean, jarvis.bat untracked. No push.`
- source_command: `Owner 결정: D1, Reviewer 파일별 참조 커밋 설계 task 등록 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `2f9dcc357e086d6ea77cd2792e5cbbe270b296e5` (등록 시점 main HEAD = task-0176 candidate, origin/main `7cf5c85`보다 9커밋 앞섬, push 없음). Start 때 다시 확인한다 |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 등록 방식 | 이 기록을 `TODO`로 작업 트리에만 만들었다(커밋·stage 없음). Start 승인 뒤 candidate에 포함한다 |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=3`, `repair_count=3` (SOP §5 기본값 1에서 Owner가 이 task에 한해 2로, 다시 3으로 증액. Reviewer 1·2·3 지적을 repair 1·2·3으로 고쳤다. 아래 "Repair 1"·"Repair 2"·"Repair 3") |

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
2. 대상 제한(F1). `<path>`는 Manager가 준 scope 파일이어야 하고, 같은 `<전체 40자 해시> -- <path>` 줄이 OWNER APPROVAL (verbatim) 절에 그대로 한 줄로 적혀 있어야 한다(repair 1). 해시와 경로가 승인 원문의 서로 다른 곳에 따로 있는 것으로는 부족하다. 하나라도 어긋나면 그 호출은 BLOCKED다(fail closed). `jarvis.bat`·`.env` 계열·디렉터리·와일드카드는 참조 대상이 될 수 없다.
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
| `scripts/validate_multi_agent_sop.py` | `REVIEWER_ROLE_CLAUSES`에 새 문장 14개(self-review 뒤 보고 규칙 1개 포함, repair 1 뒤 15개), `REVIEWER_REFERENCE_FORMS`(승인된 두 형식)와 `_validate_reviewer_reference_forms`(두 정의의 Allowed commands에서 `<reference>`가 든 줄이 정확히 두 형식인지), `SOP_REFERENCE_CLAUSES`(SOP 문장 3개, candidate 1에서 2개였고 repair 1에서 1개 추가), 관련 negative mutation 7개(각 정의에 `git log` 참조 형식 추가 2개, diff 줄에서 경로 제거 2개, SOP 문장 3개 제거. candidate 1에서는 6개)를 더했다. 새 문장마다 기존 규칙대로 두 정의에서 각각 지우는 mutation이 자동으로 생긴다: 15개 × 2 = 30개(candidate 1에서는 14개 × 2 = 28개). 따라서 negative 검사는 133 + 30 + 7 = 170이다(candidate 1에서는 133 + 28 + 6 = 167) |
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
| A2 | Owner 결정 (원문) | "현재 candidate `2f9dcc357e086d6ea77cd2792e5cbbe270b296e5`를 보존하세요." / "task-0176은 `DOING` 상태로 유지하고, Reviewer와 QA를 실행하지 마세요." / "새 설계 task는 등록 및 계획 작성까지만 수행하고, 구현이나 상태 전이는 하지 마세요." / "등록 후 Owner의 Start 승인을 기다리세요." | candidate `2f9dcc3`은 이력에 그대로 있다. `2f9dcc3`은 이 task의 baseline이자 candidate 1 `36631fb`의 parent이고, 그 뒤 candidate들의 조상이며 HEAD가 아니다("위험"의 HEAD 항목). task-0176은 DOING이며 Reviewer·QA를 실행하지 않았다. 등록 단계에서는 기록과 계획만 쓰고 Start 승인을 기다렸다(구현과 이 task의 Start는 Start 승인 뒤) |
| A3 | Owner 결정 (원문) | "설계 범위에는 `.claude/agents/reviewer.md`, `.codex/agents/reviewer.toml`, `scripts/validate_multi_agent_sop.py`, 관련 SOP 문서, `jarvis-reviewer-call` Skill을 포함하세요." | owned 행의 다섯 파일(reviewer.md, reviewer.toml, validator, SOP, Skill)이 이 범위다. "관련 SOP 문서"는 `docs/jarvis-multi-agent-sop-v0.1.md`로 보았다 |
| A4 | Owner 결정 (원문) | "참조 커밋은 지정된 파일의 실제 diff를 확인하기 위한 용도로만 사용하고, candidate의 변경 범위 판정과 최종 검토 대상은 기존 규칙대로 유지하는 설계를 우선하세요." / "참조 커밋을 통해 candidate에 포함되지 않은 변경을 임의로 승인하거나, 보호 범위 밖 파일을 수정할 수 없도록 검증 규칙을 명확히 하세요." | 참조 diff는 짝지어진 경로의 검토 근거로만 쓰고 변경 범위 판정과 검토 대상(baseline..candidate, candidate 시점의 파일)은 그대로다. 다른 경로의 변경은 검토하지도 승인하지도 않고 PASS는 scope 밖 변경을 덮지 않는다. 참조는 scope 파일이고 같은 `<해시> -- <path>` 줄이 승인 원문에 한 줄로 적혀 있고 baseline의 조상일 때만 쓰며, `jarvis.bat`·`.env`·디렉터리·와일드카드는 쓸 수 없다. validator가 이 문장들과 명령 형식을 강제한다 |
| A5 | Owner 결정 (원문) | "등록한 task ID, 변경 예정 파일, 설계 기준, 테스트 항목, 위험 요소를 보고한 뒤 멈추세요." | 등록 보고에서 task ID, 변경 예정 파일, 설계 기준, 테스트 항목, 위험을 보고하고 멈췄다 |
| A6 | Owner 결정 (원문) | "reset, revert, cherry-pick, push" / "기존 candidate 재구성" / "task-0175 기록 및 보호 대상 수정" / "Owner 승인 없는 구현이나 추가 상태 전이" | reset·revert·cherry-pick·push를 하지 않았고 기존 candidate를 재구성하지 않았으며 task-0175 기록과 보호 대상을 바꾸지 않았다. 상태 전이는 Owner의 Start 승인 뒤 이 task의 Console Start 하나뿐이다 |
| B1 | Owner 결정: F1~F3 (원문) | "Owner 결정 — task-0177" / "F1 승인: 참조 커밋은 Owner 승인 원문에 참조 경로와 전체 40자 해시가 명시된 경우에만 허용합니다." | 참조 줄은 같은 `<전체 40자 해시> -- <path>` 줄이 승인 원문에 한 줄로 적혀 있을 때만 유효하고(해시와 경로가 따로 있는 것으로는 부족, repair 1), 아니면 Reviewer는 BLOCKED다(정의, SOP, Skill preflight) |
| B2 | Owner 결정: F1~F3 (원문) | "F2 부분 승인: 다음 두 명령만 새 허용 명령으로 승인합니다." / "`git merge-base --is-ancestor <reference> <baseline>`" / "`git diff <reference> <hash> -- <path>`" / "`git log` 형식은 승인하지 않습니다." / "꼭 필요하다고 판단되면 구현하지 말고 별도 보고하세요." | 허용 명령에 더한 것은 이 두 줄뿐이고 `git log` 형식은 넣지 않았다. validator가 Allowed commands에서 `<reference>`가 든 줄을 이 두 형식으로 한정하고, `git log` 형식을 더하거나 diff 줄에서 경로를 빼는 mutation을 잡는다. 구현 중 `git log` 형식이 필요하다고 판단한 곳은 없었다 |
| B3 | Owner 결정: F1~F3 (원문) | "F3 승인: Evidence와 Complete의 Preview/Confirm은 Owner가 직접 수행합니다." | Evidence와 Complete의 Preview/Confirm은 Owner가 직접 한다(실행 계획 5단계) |
| B4 | Owner 결정: F1~F3 (원문) | "이 결정은 task-0177의 Start 승인을 의미하지 않습니다." / "먼저 위 결정을 task-0177 기록에 반영하고, 계획과 validator·Skill 테스트 항목을 두 명령 기준으로 정리하세요." / "기록을 수정한 뒤 파서와 diff를 확인하고 보고하세요." / "아직 구현, candidate 커밋, 상태 전이, Reviewer·QA 실행, push는 하지 마세요." / "그 후 Owner의 명시적인 Start 승인을 기다리세요." | F1~F3 반영 때는 기록만 고치고 파서와 diff를 확인해 보고했으며, 구현·커밋·상태 전이·Reviewer·QA·push를 하지 않고 Start 승인을 기다렸다 |
| B5 | Owner 결정: F1~F3 (원문) | "기존 candidate `2f9dcc357e086d6ea77cd2792e5cbbe270b296e5`와 task-0176의 `DOING` 상태를 보존하고, 보호 대상과 task-0175 기록은 수정하지 마세요." | candidate `2f9dcc3`과 task-0176의 DOING을 보존했고 보호 대상과 task-0175 기록은 바꾸지 않았다 |
| C1 | Owner 결정: Start 승인 (원문) | "Owner 결정 — task-0177 Start 승인" / "task-0177 `reviewer-reference-commits`의 Start를 승인합니다." / "Console의 공식 Preview/Confirm 절차로 `START TASK`를 실행하세요." / "Discord `/go`는 사용하지 마세요." / "Start 결과와 상태를 확인한 뒤, task-0177에 등록된 범위에서만 구현하세요." | Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다. `/go`는 쓰지 않았고 기록에서 status 줄만 바뀐 것을 diff로 확인했다. 구현은 owned 다섯 파일과 이 기록뿐이다 |
| C2 | Owner 결정: Start 승인 (원문) | "참조 커밋 기능은 Owner 승인 원문에 명시된 전체 40자 해시와 경로만 허용하세요." / "새로 승인된 명령은 `git merge-base --is-ancestor <reference> <baseline>`과 `git diff <reference> <hash> -- <path>` 두 개뿐입니다." / "참조 diff는 검토 근거일 뿐입니다." / "변경 범위 판정과 최종 검토 대상은 기존 규칙을 유지하고, 참조를 통해 다른 파일의 변경을 승인하지 못하도록 검증하세요." | 정의 두 곳의 "Reference commits (optional)" 절, 허용 명령 두 줄, SOP Reviewer 항목, Skill preflight가 같은 제한을 적는다: 승인 원문에 한 줄로 적힌 `<40자 해시> -- <path>`만, 두 명령만, 참조 diff는 근거일 뿐이고 범위 판정·검토 대상은 그대로, 다른 경로의 변경은 승인하지 않음 |
| C3 | Owner 결정: Start 승인 (원문) | "Reviewer 정의 두 곳, validator, SOP, `jarvis-reviewer-call` Skill의 일관성을 확인하고 계획된 mutation 및 회귀 테스트를 실행하세요." / "Worker 파이프라인은 수정하지 마세요." | 두 정의의 같은 문장 15개를 `REVIEWER_ROLE_CLAUSES`에, SOP 문장 3개를 `SOP_REFERENCE_CLAUSES`에 넣어 강제했다(repair 1 반영). validator negative 검사 133 → 170, PASS. 회귀: Worker smoke 494건 실패 0, Console smoke, Discord self-check suite 통과. `orchestrator/worker/claude_worker.py`는 바꾸지 않았다(아래 "Implementer 검증") |
| C4 | Owner 결정: Start 승인 (원문) | "Self-review, 사전 점검, candidate 생성, Reviewer, 동일 candidate에 대한 QA 순으로 진행하세요." / "Reviewer와 QA가 PASS하지 않으면 후속 완료 절차로 넘어가지 마세요." | self-review → 사전 점검 → candidate → Reviewer → 같은 candidate에 QA 순서로 하고, 둘 다 PASS가 아니면 완료 절차로 가지 않는다 |
| C5 | Owner 결정: Start 승인 (원문) | "Evidence와 최종 Complete의 Preview/Confirm은 Owner가 직접 수행합니다." / "해당 단계에 도달하면 결과를 보고하고 멈추세요." / "Push는 하지 마세요." | Evidence와 Complete의 Preview/Confirm은 Owner가 직접 하며 그 지점에서 결과를 보고하고 멈춘다. push하지 않는다 |
| C6 | Owner 결정: Start 승인 (원문) | "보호 범위와 금지 사항은 그대로 유지합니다." / "`jarvis.bat`, task-0175·task-0176 기록, 보호 worktree를 수정하지 마세요." / "reset, revert, cherry-pick, 계획 밖 파일 수정이나 상태 전이가 필요해지면 실행하지 말고 먼저 보고하세요." | 보호 범위와 금지 사항을 유지했다: `jarvis.bat`, task-0175·0176 기록, 보호 worktree를 바꾸지 않았다. 계획 밖 수정이나 상태 전이가 필요한 경우는 없었다 |
| C7 | Owner 결정: Start 승인 (원문) | "각 단계의 실제 결과를 근거와 함께 보고하고, 성공을 추정하거나 미실행 검증을 PASS로 기록하지 마세요." | 단계마다 실행한 명령의 실제 결과만 적고, 실행하지 않은 검증은 PASS로 적지 않는다 |
| D1 | Owner 결정: Repair 1 (원문) | "Owner 결정 — task-0177 Reviewer repair 1 승인" / "제안한 repair 1을 승인합니다." / "Reviewer 지적 1을 반영하세요." / "참조 커밋은 Owner 승인 원문에 전체 40자 해시와 경로가 `<40자 해시> -- <path>` 형식으로 동일한 한 줄에 명시된 경우에만 유효하게 인정합니다." / "해시와 경로가 서로 다른 곳에 따로 존재하는 것으로는 승인 조건을 충족하지 못합니다." | 참조 줄은 같은 `<전체 40자 해시> -- <path>` 줄이 승인 원문에 한 줄로 적혀 있을 때만 유효하고, 해시와 경로가 따로 있는 것으로는 부족하다("Repair 1") |
| D2 | Owner 결정: Repair 1 (원문) | "Reviewer 두 정의, `REVIEWER_ROLE_CLAUSES` validator, SOP, `jarvis-reviewer-call` Skill, task-0177 설계 기준을 동일한 규칙으로 맞추세요." | 두 정의(같은 문장), `REVIEWER_ROLE_CLAUSES`, SOP 항목과 `SOP_REFERENCE_CLAUSES`, Skill 입력 표와 Step 4, 설계 기준 2를 이 규칙으로 맞췄다 |
| D3 | Owner 결정: Repair 1 (원문) | "Reviewer 지적 2도 제안대로 수정하세요." / "`2f9dcc3`은 현재 candidate의 parent이며 HEAD가 아니라는 사실을 기록에 정확히 반영하세요." | A2 해석을 `2f9dcc3`은 이력에 그대로 있고 이 task candidate의 parent이며 HEAD가 아니라고 고쳤다(candidate 1 기준 문구. 실제 관계는 repair 2에서 A2에 바로잡았다, E2) |
| D4 | Owner 결정: Repair 1 (원문) | "Reviewer 결과와 repair 내용을 task-0177 기록에 남기세요." | "Reviewer 1"과 "Repair 1" 절에 결과와 수정 내용을 적었다 |
| D5 | Owner 결정: Repair 1 (원문) | "repair 예산 1/1을 사용하므로 추가 repair는 하지 마세요." / "새 candidate에서 유효한 지적이 다시 나오면 즉시 중단하고 보고하세요." | repair 예산 1/1을 썼다(`repair_count=1`, repair 1 시점. 이후 Owner가 예산을 늘렸다, "Repair 2"·"Repair 3"). 새 candidate에서 유효한 지적이 나오면 고치지 않고 멈춰 보고한다 |
| D6 | Owner 결정: Repair 1 (원문) | "새 candidate를 만든 뒤 Reviewer를 다시 실행하고, PASS한 동일 candidate로 QA를 진행하세요." / "Reviewer와 QA가 모두 PASS하기 전에는 Evidence나 Complete 단계로 넘어가지 마세요." | 새 candidate에 Reviewer를 다시 실행하고 PASS한 같은 candidate로 QA를 한다. 둘 다 PASS가 아니면 Evidence·Complete로 가지 않는다 |
| D7 | Owner 결정: Repair 1 (원문) | "Push는 하지 마세요." / "task-0176은 별도 task이며, 이번 승인은 task-0176의 수정·상태 변경·Hold 실행을 승인하지 않습니다." | push하지 않는다. task-0176의 기록·상태·Hold는 이 승인으로 바뀌지 않으며 이 repair에서 건드리지 않았다 |
| D8 | Owner 결정: Repair 1 (원문) | "수정은 승인된 파일 범위에만 한정하세요." / "계획 밖 변경, 보호 대상 수정, 추가 상태 전이 또는 금지된 Git 작업이 필요해지면 실행하지 말고 먼저 보고하세요." / "각 검증은 실제 결과로 보고하고, repair 예산이 소진된 뒤에는 임의로 추가 수정을 하지 마세요." | 수정은 범위의 여섯 파일 안에서만 했고 계획 밖 변경·보호 대상·상태 전이·금지된 Git 작업은 없었다. 검증은 실행한 결과만 적고, 예산이 소진됐으므로 이후 추가 수정은 하지 않는다 |
| E1 | Owner 결정: Repair 2 (원문) | "결정: 1번 승인 — task-0177 추가 repair 1회를 허용합니다." / "허용 범위는 task-0177 기록 파일로 한정합니다." | repair 2를 1회 허용받았고 바꾼 파일은 이 기록 하나다 |
| E2 | Owner 결정: Repair 2 (원문) | "A2의 커밋 관계를 실제 Git 이력에 맞게 수정합니다." / "`2f9dcc3`은 candidate 1 `36631fb`의 parent이며, 현재 candidate의 조상입니다." | A2 해석을 `2f9dcc3`은 baseline이자 candidate 1 `36631fb`의 parent이고 그 뒤 candidate들의 조상이며 HEAD가 아니라고 고쳤다. Reviewer 2가 같은 근거로 든 "Repair 1" 절 문구와 D3 해석은 내용을 바꾸지 않고 candidate 1 기준 문구라는 표시만 더했다("Repair 2") |
| E3 | Owner 결정: Repair 2 (원문) | "구현 표의 validator 수치를 실제 상태와 일치시킵니다." / "`SOP_REFERENCE_CLAUSES` 3개, 관련 negative mutation 7개입니다." | 구현 표의 validator 행을 `SOP_REFERENCE_CLAUSES` 3개, 관련 negative mutation 7개로 맞췄다(candidate 1 때 값도 함께 적음) |
| E4 | Owner 결정: Repair 2 (원문) | "Reviewer 2의 FINDINGS 원문과 이번 Owner 승인 원문을 task 기록에 남깁니다." / "Manager summary에 이번 결정과 수정 범위를 반영합니다." | "Reviewer 2" 절에 FINDINGS 줄을, "Owner 결정: Repair 2 (원문)" 절에 이 결정을 그대로 남기고 이 E행을 더했다 |
| E5 | Owner 결정: Repair 2 (원문) | "`repair_budget=2`, `repair_count=2`로 기록을 정합화하고 `updated_at`을 갱신합니다." | 기준선 budget 행을 `repair_budget=2`, `repair_count=2`로 고치고 updated_at을 편집 시각으로 갱신했다(repair 2 시점. 이후 3으로 증액, "Repair 3") |
| E6 | Owner 결정: Repair 2 (원문) | "위 범위 밖의 변경은 금지합니다." / "Reviewer 정의, validator, SOP, Skill의 구현 규칙은 수정하지 마세요." / "`jarvis.bat`, task-0176, 보호된 워크트리 및 다른 task 기록은 건드리지 마세요." | 정의·validator·SOP·Skill은 바꾸지 않았고 `jarvis.bat`, task-0176, 보호 worktree, 다른 task 기록도 건드리지 않았다 |
| E7 | Owner 결정: Repair 2 (원문) | "새 candidate를 만든 뒤 Reviewer를 실행하세요." / "PASS일 때만 동일 candidate에 대해 QA를 실행합니다." / "새 candidate에서 유효한 FINDINGS가 다시 나오면 추가 수정 없이 중단하고 보고하세요." | 새 candidate에 Reviewer를 실행하고 PASS일 때만 같은 candidate로 QA를 한다. 유효한 지적이 다시 나오면 고치지 않고 멈춰 보고한다 |
| E8 | Owner 결정: Repair 2 (원문) | "Evidence 및 Console Complete Preview/Confirm은 Owner가 직접 수행합니다." / "push는 하지 마세요." | Evidence와 Complete의 Preview/Confirm은 Owner가 직접 한다. push하지 않는다 |
| E9 | Owner 결정: Repair 2 (원문) | "수정 전후 diff와 기록 정합성 검사 결과를 보고하고, 위 제한을 벗어나는 문제가 발견되면 임의로 확장하지 말고 멈춰서 보고하세요." | 수정 전후 diff와 기록 정합성 검사 결과를 보고하고, 범위 밖 문제는 고치지 않고 멈춰 보고한다 |
| G1 | Owner 결정: Repair 3 (원문) | "Owner 결정: task-0177 추가 repair 1회 승인." / "목표는 task 완료입니다." / "현재 HEAD `cdc689e623e6131253903183cf2bdde7349409cf`, task-0177 `DOING`, 기존 repair 예산 `2/2`입니다." / "이번 결정을 통해 repair 예산을 `3`으로 늘리고, 추가 repair 1회를 승인합니다." | repair 예산을 이 task에 한해 3으로 늘리고 repair 3을 1회 허용받았다(`repair_budget=3`, `repair_count=3`). 목표는 Owner의 공식 Complete까지 가는 것이다 |
| G2 | Owner 결정: Repair 3 (원문) | "수정 전 전체 정합성 점검" / "task-0177 기록 파일 전체를 확인하고, 기록에 등장하는 모든 수치와 커밋 관계를 실제 코드·validator·Git 이력과 대조하세요." / "특히 다음을 확인합니다." / "`14/15`, `2/3`, `6/7`, `167/170`, `133/170` 등 validator와 mutation 관련 숫자" / "`REVIEWER_ROLE_CLAUSES`의 실제 항목 수" / "`SOP_REFERENCE_CLAUSES`의 실제 항목 수" / "정의별 clause-removal mutation과 전체 mutation 수의 산술적 일치" / "후보별 parent, baseline, candidate 관계" / "Manager summary와 본문, repair 기록의 수치·사실관계 일치" / "`repair_budget`, `repair_count`, `updated_at` 등 task-model 필드의 일치" / "숫자를 일괄 치환하지 말고, 각 값이 어느 candidate 또는 시점을 가리키는지 구분하세요." / "과거 candidate의 기록은 당시 기준으로 정확하다면 그대로 유지하세요." | 수정 전에 기록 전체의 수치와 커밋 관계를 각 candidate의 validator 코드와 `git log`로 대조했고, 값마다 가리키는 candidate·시점을 나눠 당시 기준으로 맞는 과거 기록은 그대로 두었다("Repair 3" 표) |
| G3 | Owner 결정: Repair 3 (원문) | "허용된 repair" / "아래 범위만 수정합니다." / "Reviewer 3가 지적한 validator 행의 `14개`를 실제 값에 맞게 수정합니다." / "위 정합성 점검에서 발견된 task-0177 기록 내부의 관련 수치·커밋 관계 오류를 함께 바로잡습니다." / "Reviewer 3의 FINDINGS 원문과 이번 Owner 결정 원문을 기록합니다." / "Manager summary를 갱신해 결정과 수정 범위를 반영합니다." / "`repair_budget=3`, `repair_count=3`으로 정합화하고 `updated_at`을 갱신합니다." | 바꾼 것: 구현 표 validator 행 끝 문장(15개 × 2 = 30개, 133 + 30 + 7 = 170, candidate 1 값 병기), 점검에서 찾은 D5·E5 예산 서술의 시점 표기, Candidate 3 절, Reviewer 3 원문과 이 결정 원문, 이 G행, budget 행과 updated_at |
| G4 | Owner 결정: Repair 3 (원문) | "구현 규칙은 변경하지 마세요." / "Reviewer 정의, validator, SOP, Skill의 기능이나 정책은 수정 범위가 아닙니다." / "기록 외부에서 추가 수정이 필요해 보이면 임의로 범위를 넓히지 말고 보고하세요." | 정의·validator·SOP·Skill은 바꾸지 않았고 이 기록 밖에서 고칠 것은 찾지 못했다 |
| G5 | Owner 결정: Repair 3 (원문) | "새 candidate 검증" / "수정 전후 diff와 수치 대조 결과를 확인합니다." / "기록 검사와 관련 validator를 실행해 결과를 기록합니다." / "새 candidate를 생성합니다." / "공식 SOP에 따라 Reviewer를 실행합니다." / "Reviewer가 PASS하면 동일 candidate에 대해 QA를 실행합니다." / "QA가 PASS하면 Evidence를 준비하고, Owner가 직접 수행할 Console Complete Preview/Confirm 단계 직전까지 진행한 뒤 결과를 보고합니다." | 수정 전후 diff와 수치 대조를 확인하고 기록 검사와 validator를 돌린 뒤 새 candidate에 Reviewer를 실행한다. PASS면 같은 candidate로 QA를 하고, QA PASS면 Evidence 문안을 준비해 Owner의 Console Complete 직전에서 멈춘다 |
| G6 | Owner 결정: Repair 3 (원문) | "이번 추가 repair 이후 새 candidate에서 유효한 FINDINGS가 나오더라도, 자동으로 추가 수정하지 마세요." / "지적의 실제 근거와 범위를 정리해 보고하고, 별도 Owner 결정이 필요한 부분만 명확하게 요청하세요." / "단순히 지적이 나왔다는 이유로 다른 검증을 생략하거나 결과를 PASS로 처리하지 마세요." | 새 candidate에서 유효한 지적이 나와도 고치지 않고 근거와 범위를 정리해 보고하며, 다른 검증을 생략하거나 PASS로 처리하지 않는다 |
| G7 | Owner 결정: Repair 3 (원문) | "`jarvis.bat` 열람·수정·스테이징·삭제 금지" / "task-0176 및 다른 제외 task 기록 변경 금지" / "보호된 워크트리 변경 금지" / "승인되지 않은 코드·정책·범위 변경 금지" / "push 금지" / "task 상태를 수동으로 DONE으로 변경 금지" | `jarvis.bat`, task-0176과 다른 제외 기록, 보호 worktree, 승인되지 않은 코드·정책·범위를 건드리지 않고 push하지 않으며 상태를 DONE으로 직접 바꾸지 않는다 |
| G8 | Owner 결정: Repair 3 (원문) | "완료 목표 및 보고" / "이번 작업의 목표는 단순히 오류를 고치는 것이 아니라, 정합성 있는 candidate → Reviewer PASS → 동일 candidate QA PASS → Evidence 준비 → Owner의 공식 Complete 절차까지 도달하는 것입니다." / "최종 보고에는 다음을 포함하세요." / "새 candidate와 parent" / "수정된 기록 항목" / "전체 수치 대조 결과" / "validator 및 mutation 결과" / "Reviewer 원문 판정과 결과" / "QA 결과 및 미검증 항목" / "현재 HEAD, origin 대비 ahead/behind, 작업 트리 상태" / "Owner가 직접 수행할 다음 Console 단계" | 최종 보고에 새 candidate와 parent, 수정 항목, 수치 대조, validator·mutation 결과, Reviewer 원문 판정, QA 결과와 미검증 항목, HEAD·ahead/behind·작업 트리, Owner의 다음 Console 단계를 넣는다 |
| G9 | Owner 결정: Repair 3 (원문) | "불필요하게 작업을 다시 시작하거나 이미 확인한 검사를 반복하지 말고, 현재 기록과 기존 결과를 재사용할 수 있는 부분은 재사용하세요." / "단, 새 candidate에 필요한 검증은 생략하지 마세요." | Implementer 검증·self-review 등 기존 결과는 재사용하고, 새 candidate에 필요한 Reviewer와 QA는 생략하지 않는다 |

## 사전 점검과 Self-review

- 사전 점검 1회차(`check_task_record.py --baseline 2f9dcc3`): PASS, violations 0, staged 6, 인용 검사 49문장 모두 인용.
- self-review 1회(`claude -p --agent self-reviewer --tools Read,Grep,Glob`): 지적 4건(major 1, minor 3). candidate 전이라 repair가 아니다(SOP §3·§5). 처리:
  1. major, 설계 기준 5의 "보고서에 참조 diff를 본 파일을 따로 적는다"가 정의에 없음 → 두 정의의 "Reference commits (optional)" 절에 `commands_run`의 참조 diff 명령이 그 경로를 보여 준다는 규칙을 넣고 `REVIEWER_ROLE_CLAUSES`로 강제했다. 출력 템플릿에 새 필드를 두면 Worker 파이프라인이 Reviewer 보고를 읽는 방식에 영향을 줄 수 있어 필드는 더하지 않았고, 설계 기준 5를 그에 맞게 고쳤다.
  2. minor, 설계 기준 8의 "baseline..candidate 무변경"이 기준 4·Skill과 어긋남 → 기준 8을 기준 4와 같게 고쳤다.
  3. minor, SOP가 금지 경로·baseline 없음·보고 규칙을 적지 않음 → SOP 항목에 더했다.
  4. minor, T4의 "이름은 Start 때 확정" → Worker smoke로 적었다.
- 수정 뒤 사전 점검 2회차: PASS, violations 0, staged 6, 인용 검사 모두 인용. validator 167/0 PASS.
- 인용 문장과 승인 범위는 바꾸지 않았다. updated_at은 이 편집 시각 2026-10-20 18:26 UTC다(편집 스크립트가 UTC 시계를 읽어 넣음).

## Candidate 1

`36631fbf0f5af5739ce3a873d16882e1065b39b3`(parent `2f9dcc357e086d6ea77cd2792e5cbbe270b296e5`). 바뀐 파일은 범위의 여섯 개다.

## Reviewer 1 (`36631fb`, FINDINGS minor 2, `self_deviations` 없음 → 유효)

출처: candidate `36631fbf0f5af5739ce3a873d16882e1065b39b3`에 대한 Reviewer(subagent `reviewer`) 보고. 아래 블록은 그 보고의 `verdict`·`findings`·`self_deviations` 줄을 고치지 않고 옮긴 것이다(줄 번호는 `36631fb` 시점의 이 기록 기준).

```text
candidate_hash: 36631fbf0f5af5739ce3a873d16882e1065b39b3
verdict:        FINDINGS
findings:       - {severity: minor, evidence: ".claude/agents/reviewer.md and .codex/agents/reviewer.toml, Reference commits (optional): a reference line is valid when 'that exact hash and that exact path both appear in the section under `=== OWNER APPROVAL (verbatim) ===`'; .claude/skills/jarvis-reviewer-call/SKILL.md preflight uses the same test ('the same hash and path are not both written in the Owner approval verbatim'); task record line 61 (design criterion 2) has the same wording. The rule never checks that the hash and the path are paired with each other in the approval", impact: "approvals routinely quote baseline or earlier-candidate hashes and scope paths for other reasons (this task's own approval quotes 2f9dcc357e086d6ea77cd2792e5cbbe270b296e5 next to the scope paths), so a Manager could pair any quoted ancestor hash with any quoted scope path and the Reviewer would accept it, although the Owner never named that hash as the reference for that path. That weakens approval condition 6 ('참조 커밋을 통해 candidate에 포함되지 않은 변경을 임의로 승인 ... 할 수 없도록 검증 규칙을 명확히 하세요') and Start condition 3 ('Owner 승인 원문에 명시된 전체 40자 해시와 경로만 허용하세요')", minimum_correction: "in both definitions, the SOP item and the Skill preflight, require that the Owner approval verbatim names the hash and the path together as a reference pair (for example, the `<reference> -- <path>` line appears verbatim in the approval), and add the changed sentence to REVIEWER_ROLE_CLAUSES; otherwise get an explicit Owner decision that unpaired co-occurrence is enough"}
                - {severity: minor, evidence: "Manager summary row A2 (also memory/tasks/task-0177-reviewer-reference-commits.md:174): 'candidate `2f9dcc3`은 HEAD로 그대로 두었고'. git log 2f9dcc357e086d6ea77cd2792e5cbbe270b296e5..36631fbf0f5af5739ce3a873d16882e1065b39b3 shows the candidate 36631fbf0f5af5739ce3a873d16882e1065b39b3 committed on top of 2f9dcc3, so 2f9dcc3 is now the parent, not HEAD. The approval condition is only '현재 candidate `2f9dcc357e086d6ea77cd2792e5cbbe270b296e5`를 보존하세요.', and the record's own risk section (line 92) notes that stacking on 2f9dcc3 breaks HEAD = reviewed candidate for task-0176", impact: "a reader of the summary would wrongly conclude that 2f9dcc3 is still HEAD, so task-0176's Hold precondition (HEAD = reviewed candidate) would still hold, when it no longer does", minimum_correction: "reword A2 to say that 2f9dcc3 is kept unchanged in history as the parent of this candidate and is no longer HEAD, and point to the risk entry at line 92"}
self_deviations: []
```

Manager 판정: 두 지적 모두 사실이다. 지적 1은 Owner 승인 원문을 쓰는 방식을 정하므로, 예산 안이지만 고치기 전에 Owner 결정을 받았다.

## Owner 결정: Repair 1 (원문)

```text
Owner 결정 — task-0177 Reviewer repair 1 승인
제안한 repair 1을 승인합니다.

1. Reviewer 지적 1을 반영하세요. 참조 커밋은 Owner 승인 원문에 전체 40자 해시와 경로가 `<40자 해시> -- <path>` 형식으로 동일한 한 줄에 명시된 경우에만 유효하게 인정합니다. 해시와 경로가 서로 다른 곳에 따로 존재하는 것으로는 승인 조건을 충족하지 못합니다.
2. Reviewer 두 정의, `REVIEWER_ROLE_CLAUSES` validator, SOP, `jarvis-reviewer-call` Skill, task-0177 설계 기준을 동일한 규칙으로 맞추세요.
3. Reviewer 지적 2도 제안대로 수정하세요. `2f9dcc3`은 현재 candidate의 parent이며 HEAD가 아니라는 사실을 기록에 정확히 반영하세요.
4. Reviewer 결과와 repair 내용을 task-0177 기록에 남기세요.
5. repair 예산 1/1을 사용하므로 추가 repair는 하지 마세요. 새 candidate에서 유효한 지적이 다시 나오면 즉시 중단하고 보고하세요.
6. 새 candidate를 만든 뒤 Reviewer를 다시 실행하고, PASS한 동일 candidate로 QA를 진행하세요. Reviewer와 QA가 모두 PASS하기 전에는 Evidence나 Complete 단계로 넘어가지 마세요.
7. Push는 하지 마세요. task-0176은 별도 task이며, 이번 승인은 task-0176의 수정·상태 변경·Hold 실행을 승인하지 않습니다.

수정은 승인된 파일 범위에만 한정하세요. 계획 밖 변경, 보호 대상 수정, 추가 상태 전이 또는 금지된 Git 작업이 필요해지면 실행하지 말고 먼저 보고하세요. 각 검증은 실제 결과로 보고하고, repair 예산이 소진된 뒤에는 임의로 추가 수정을 하지 마세요.
```

## Repair 1

- 지적 1: 참조 줄의 유효 조건을 "같은 `<reference> -- <path>` 줄이 승인 원문에 그대로 한 줄로 적혀 있음"으로 바꾸고, 해시와 경로가 따로 있는 것으로는 부족하다는 문장을 더했다. 두 정의(같은 문장), `REVIEWER_ROLE_CLAUSES`(바뀐 문장과 새 문장), SOP 항목과 `SOP_REFERENCE_CLAUSES`(새 문장 1개), Skill의 입력 표와 Step 4 BLOCKED 조건, 설계 기준 2를 같은 규칙으로 맞췄다. Manager 요약 A4·B1·C2·C3 해석도 같은 규칙과 수치로 고쳤다.
- 지적 2: Manager 요약 A2를 "`2f9dcc3`은 이력에 그대로 있고 이 task의 candidate의 parent이며 HEAD가 아니다"(candidate 1 기준 문구. 실제 관계는 아래 "Repair 2")로 고치고 "위험"의 HEAD 항목을 가리켰다.
- 기준선 budget 행을 `repair_count=1`로 고쳤다. 이 repair가 예산 1/1을 쓰므로 추가 repair는 하지 않는다. 새 candidate에서 유효한 지적이 나오면 멈추고 보고한다.
- 검증(작업 트리): validator status=PASS, negative_checks=170, negative_failures=0. `tomllib` 파싱 통과.
- updated_at은 이 repair 편집 시각 2026-10-20 18:36 UTC다(편집 스크립트가 UTC 시계를 읽어 넣음).

## Candidate 2 (repair 1)

`3fc152b0ec53136763d3103d4a5f5a6ddcebe556`(parent `36631fbf0f5af5739ce3a873d16882e1065b39b3`).

## Reviewer 2 (`3fc152b`, FINDINGS minor 2, `self_deviations` 없음 → 유효)

출처: candidate `3fc152b0ec53136763d3103d4a5f5a6ddcebe556`에 대한 Reviewer(subagent `reviewer`) 보고. 아래 블록은 그 보고의 `verdict`·`findings`·`self_deviations` 줄을 고치지 않고 옮긴 것이다(줄 번호는 `3fc152b` 시점의 이 기록 기준).

```text
candidate_hash: 3fc152b0ec53136763d3103d4a5f5a6ddcebe556
verdict:        FINDINGS
findings:       - {severity: minor, evidence: "memory/tasks/task-0177-reviewer-reference-commits.md:174 (row A2) and Manager summary row A2 both say '이 task의 candidate가 그 위에 쌓여 `2f9dcc3`은 그 parent이고 HEAD가 아니다'; Repair 1 line 249 says the same. git log --format=\"%H %P %s\" 2f9dcc357e086d6ea77cd2792e5cbbe270b296e5..3fc152b0ec53136763d3103d4a5f5a6ddcebe556 shows candidate 3fc152b0ec53136763d3103d4a5f5a6ddcebe556 has parent 36631fbf0f5af5739ce3a873d16882e1065b39b3, and only 36631fbf0f5af5739ce3a873d16882e1065b39b3 has parent 2f9dcc357e086d6ea77cd2792e5cbbe270b296e5. The wording follows repair condition 3 ('`2f9dcc3`은 현재 candidate의 parent이며 HEAD가 아니라는 사실을 기록에 정확히 반영하세요'), but that condition's premise holds only for candidate 1", impact: "a reader would wrongly conclude that the reviewed candidate 3fc152b0ec53136763d3103d4a5f5a6ddcebe556 sits directly on 2f9dcc3, when there is an intermediate commit 36631fb between them", minimum_correction: "have A2 (record and summary) say that 2f9dcc3 is the baseline and an ancestor of the current candidate (the parent of candidate 1, 36631fb), not HEAD; or get an Owner decision that the 'parent' wording in repair condition 3 is accepted as written"}
                - {severity: minor, evidence: "memory/tasks/task-0177-reviewer-reference-commits.md:152 (구현 table, validator row) was partly updated for repair 1 ('repair 1 뒤 15개') but still says '`SOP_REFERENCE_CLAUSES`(SOP 문장 2개)' and 'negative mutation 6개(... SOP 문장 2개 제거)'. At the candidate, scripts/validate_multi_agent_sop.py has 3 SOP_REFERENCE_CLAUSES entries and 4 form mutations plus 3 SOP clause removals (7 mutations), which matches the 133 -> 170 count in row C3", impact: "a reader of the 구현 table would wrongly conclude that the validator enforces only two SOP reference sentences and that the new same-line SOP sentence ('해시와 경로가 승인 원문의 서로 다른 곳에 따로 있는 것으로는 참조 커밋이 되지 않는다.') is not enforced", minimum_correction: "change line 152 to say 3 SOP sentences and 7 negative mutations after repair 1, or mark the 2 and 6 counts as candidate 1 values"}
self_deviations: []
```

Manager 판정: 두 지적 모두 사실이다. repair 예산(1/1)이 소진돼 고치지 않고 Owner에게 보고했다.

## Owner 결정: Repair 2 (원문)

```text
결정: 1번 승인 — task-0177 추가 repair 1회를 허용합니다.
허용 범위는 task-0177 기록 파일로 한정합니다.

1. A2의 커밋 관계를 실제 Git 이력에 맞게 수정합니다. `2f9dcc3`은 candidate 1 `36631fb`의 parent이며, 현재 candidate의 조상입니다.
2. 구현 표의 validator 수치를 실제 상태와 일치시킵니다. `SOP_REFERENCE_CLAUSES` 3개, 관련 negative mutation 7개입니다.
3. Reviewer 2의 FINDINGS 원문과 이번 Owner 승인 원문을 task 기록에 남깁니다.
4. Manager summary에 이번 결정과 수정 범위를 반영합니다.
5. `repair_budget=2`, `repair_count=2`로 기록을 정합화하고 `updated_at`을 갱신합니다.

제한 사항

* 위 범위 밖의 변경은 금지합니다. Reviewer 정의, validator, SOP, Skill의 구현 규칙은 수정하지 마세요.
* `jarvis.bat`, task-0176, 보호된 워크트리 및 다른 task 기록은 건드리지 마세요.
* 새 candidate를 만든 뒤 Reviewer를 실행하세요. PASS일 때만 동일 candidate에 대해 QA를 실행합니다.
* 새 candidate에서 유효한 FINDINGS가 다시 나오면 추가 수정 없이 중단하고 보고하세요.
* Evidence 및 Console Complete Preview/Confirm은 Owner가 직접 수행합니다.
* push는 하지 마세요.

수정 전후 diff와 기록 정합성 검사 결과를 보고하고, 위 제한을 벗어나는 문제가 발견되면 임의로 확장하지 말고 멈춰서 보고하세요.
```

## Repair 2

- 지적 1: A2 해석을 "`2f9dcc3`은 이 task의 baseline이자 candidate 1 `36631fb`의 parent이고 그 뒤 candidate들의 조상이며 HEAD가 아니다"로 고쳤다. 같은 지적이 근거로 든 "Repair 1" 절의 문구와 D3 해석은 repair 1 당시의 기록이라 내용을 바꾸지 않고 "candidate 1 기준 문구"라는 표시와 이 절·E2를 가리키는 말만 더했다.
- 지적 2: 구현 표의 validator 행을 실제 코드와 맞췄다: `SOP_REFERENCE_CLAUSES` 3개, 관련 negative mutation 7개(candidate 1 때 값 2개·6개도 함께 적음).
- 기준선 budget 행을 `repair_budget=2`, `repair_count=2`로 고쳤다. 예산이 다시 소진됐으므로 새 candidate에서 유효한 지적이 나오면 고치지 않고 멈춰 보고한다.
- 위 Reviewer 2 결과와 Owner 결정 원문을 남기고 Manager 요약에 E행을 더했다. 이 기록 파일 밖은 바꾸지 않았다(정의·validator·SOP·Skill 무변경).
- updated_at은 이 repair 편집 시각 2026-10-20 18:47 UTC다(편집 스크립트가 UTC 시계를 읽어 넣음).

## Candidate 3 (repair 2)

`cdc689e623e6131253903183cf2bdde7349409cf`(parent `3fc152b0ec53136763d3103d4a5f5a6ddcebe556`). 바뀐 파일은 이 기록 하나다.

## Reviewer 3 (`cdc689e`, FINDINGS minor 1, `self_deviations` 없음 → 유효)

출처: candidate `cdc689e623e6131253903183cf2bdde7349409cf`에 대한 Reviewer(subagent `reviewer`) 보고. 아래 블록은 그 보고의 `verdict`·`findings`·`self_deviations` 줄을 고치지 않고 옮긴 것이다(줄 번호는 `cdc689e` 시점의 이 기록 기준).

```text
candidate_hash: cdc689e623e6131253903183cf2bdde7349409cf
verdict:        FINDINGS
findings:       - {severity: minor, evidence: "memory/tasks/task-0177-reviewer-reference-commits.md:152 (구현 table, validator row) now gives the repair 1 count '(... repair 1 뒤 15개)' and the corrected SOP and mutation counts (3 and 7), but the row's closing sentence still reads '새 문장 14개는 기존 규칙대로 두 정의에서 각각 지우는 mutation이 자동으로 생긴다'. At the candidate, REVIEWER_ROLE_CLAUSES gains 15 entries (scripts/validate_multi_agent_sop.py diff, task-0177 block), and the per-clause removal loop at scripts/validate_multi_agent_sop.py:1554 makes one removal mutation per clause for each definition: 15 x 2 = 30, plus 7 equals the 37 that takes the count from 133 to 170 (row C3, Repair 1 line 260). With 14, the row adds up to 168. Repair 2 condition 2 is '구현 표의 validator 수치를 실제 상태와 일치시킵니다.'", impact: "a reader of the 구현 table would wrongly conclude that per-definition removal mutations cover only 14 new clauses, so the same-line clause added in repair 1 ('A hash and a path that appear only apart from each other in the approval do not make a valid reference line.') looks unenforced, and the row cannot be reconciled with the 133 -> 170 count", minimum_correction: "change the closing sentence of line 152 to say 15 (or mark 14 as the candidate 1 value), or get an Owner decision accepting the row as written"}
self_deviations: []
```

Manager 판정: 사실이다. repair 2에서 같은 행의 SOP 문장 수와 mutation 수는 고쳤지만 끝 문장의 "14개"를 놓쳤다. 예산(2/2)이 소진돼 고치지 않고 Owner에게 보고했다.

## Owner 결정: Repair 3 (원문)

```text
Owner 결정: task-0177 추가 repair 1회 승인. 목표는 task 완료입니다.
현재 HEAD `cdc689e623e6131253903183cf2bdde7349409cf`, task-0177 `DOING`, 기존 repair 예산 `2/2`입니다. 이번 결정을 통해 repair 예산을 `3`으로 늘리고, 추가 repair 1회를 승인합니다.
1. 수정 전 전체 정합성 점검
task-0177 기록 파일 전체를 확인하고, 기록에 등장하는 모든 수치와 커밋 관계를 실제 코드·validator·Git 이력과 대조하세요. 특히 다음을 확인합니다.

* `14/15`, `2/3`, `6/7`, `167/170`, `133/170` 등 validator와 mutation 관련 숫자
* `REVIEWER_ROLE_CLAUSES`의 실제 항목 수
* `SOP_REFERENCE_CLAUSES`의 실제 항목 수
* 정의별 clause-removal mutation과 전체 mutation 수의 산술적 일치
* 후보별 parent, baseline, candidate 관계
* Manager summary와 본문, repair 기록의 수치·사실관계 일치
* `repair_budget`, `repair_count`, `updated_at` 등 task-model 필드의 일치

숫자를 일괄 치환하지 말고, 각 값이 어느 candidate 또는 시점을 가리키는지 구분하세요. 과거 candidate의 기록은 당시 기준으로 정확하다면 그대로 유지하세요.
2. 허용된 repair
아래 범위만 수정합니다.

* Reviewer 3가 지적한 validator 행의 `14개`를 실제 값에 맞게 수정합니다.
* 위 정합성 점검에서 발견된 task-0177 기록 내부의 관련 수치·커밋 관계 오류를 함께 바로잡습니다.
* Reviewer 3의 FINDINGS 원문과 이번 Owner 결정 원문을 기록합니다.
* Manager summary를 갱신해 결정과 수정 범위를 반영합니다.
* `repair_budget=3`, `repair_count=3`으로 정합화하고 `updated_at`을 갱신합니다.

구현 규칙은 변경하지 마세요. Reviewer 정의, validator, SOP, Skill의 기능이나 정책은 수정 범위가 아닙니다. 기록 외부에서 추가 수정이 필요해 보이면 임의로 범위를 넓히지 말고 보고하세요.
3. 새 candidate 검증

1. 수정 전후 diff와 수치 대조 결과를 확인합니다.
2. 기록 검사와 관련 validator를 실행해 결과를 기록합니다.
3. 새 candidate를 생성합니다.
4. 공식 SOP에 따라 Reviewer를 실행합니다.
5. Reviewer가 PASS하면 동일 candidate에 대해 QA를 실행합니다.
6. QA가 PASS하면 Evidence를 준비하고, Owner가 직접 수행할 Console Complete Preview/Confirm 단계 직전까지 진행한 뒤 결과를 보고합니다.

이번 추가 repair 이후 새 candidate에서 유효한 FINDINGS가 나오더라도, 자동으로 추가 수정하지 마세요. 지적의 실제 근거와 범위를 정리해 보고하고, 별도 Owner 결정이 필요한 부분만 명확하게 요청하세요. 단순히 지적이 나왔다는 이유로 다른 검증을 생략하거나 결과를 PASS로 처리하지 마세요.
4. 절대 금지

* `jarvis.bat` 열람·수정·스테이징·삭제 금지
* task-0176 및 다른 제외 task 기록 변경 금지
* 보호된 워크트리 변경 금지
* 승인되지 않은 코드·정책·범위 변경 금지
* push 금지
* task 상태를 수동으로 DONE으로 변경 금지

5. 완료 목표 및 보고
이번 작업의 목표는 단순히 오류를 고치는 것이 아니라, 정합성 있는 candidate → Reviewer PASS → 동일 candidate QA PASS → Evidence 준비 → Owner의 공식 Complete 절차까지 도달하는 것입니다.
최종 보고에는 다음을 포함하세요.

* 새 candidate와 parent
* 수정된 기록 항목
* 전체 수치 대조 결과
* validator 및 mutation 결과
* Reviewer 원문 판정과 결과
* QA 결과 및 미검증 항목
* 현재 HEAD, origin 대비 ahead/behind, 작업 트리 상태
* Owner가 직접 수행할 다음 Console 단계

불필요하게 작업을 다시 시작하거나 이미 확인한 검사를 반복하지 말고, 현재 기록과 기존 결과를 재사용할 수 있는 부분은 재사용하세요. 단, 새 candidate에 필요한 검증은 생략하지 마세요.
```

## Repair 3

수정 전 전체 정합성 점검(실제 값은 `cdc689e`와 각 candidate의 `scripts/validate_multi_agent_sop.py`를 스크립트로 세고, 커밋 관계는 `git log`로 확인했다):

| 항목 | 실제 값 | 기록 | 처리 |
| --- | --- | --- | --- |
| `REVIEWER_ROLE_CLAUSES` 새 문장 | baseline 33 → candidate 1 47(새 14), repair 1 뒤 48(새 15) | 구현 표 validator 행 앞부분 "14개(…, repair 1 뒤 15개)"는 맞음. 끝 문장 "새 문장 14개는"은 현재 값이 아님 | 끝 문장을 15개 × 2 = 30개(candidate 1에서 14개 × 2 = 28개)로 고쳤다 |
| `SOP_REFERENCE_CLAUSES` | candidate 1 2개, 이후 3개 | 구현 표·E3·C3 모두 맞음 | 유지 |
| 참조 형식·SOP 문장 mutation | candidate 1 4 + 2 = 6개, 이후 4 + 3 = 7개 | 구현 표·E3 맞음 | 유지 |
| negative 검사 산술 | self-review 전 133 + 26 + 6 = 165, candidate 1 133 + 28 + 6 = 167, 이후 133 + 30 + 7 = 170 (validator 실행 결과 170/0) | Implementer 검증의 165·167, 사전 점검 2회차의 167, C3·Repair 1의 170 모두 당시 기준으로 맞음 | 구현 표 끝 문장에 133 + 30 + 7 = 170 산식을 적었다 |
| 커밋 관계 | `36631fb` parent `2f9dcc3`, `3fc152b` parent `36631fb`, `cdc689e` parent `3fc152b` | Candidate 1·2 절, A2 맞음. Candidate 3 절 없음 | 위 "Candidate 3" 절을 더했다 |
| Manager 요약의 예산 서술 | 지금 `repair_budget=3` | D5(1/1), E5(2/2)는 각 repair 시점 값 | 시점 표기를 더했다(내용 유지) |
| budget 행·updated_at | — | `repair_budget=2`, `repair_count=2` | `repair_budget=3`, `repair_count=3`, updated_at 갱신 |

그 밖의 수치(Implementer 검증의 Worker smoke 494·Discord 117, self-review의 49문장, Repair 1·2 절의 예산 서술)는 작성 당시 기준으로 정확해 그대로 두었다. Reviewer 정의·validator·SOP·Skill은 바꾸지 않았다. 이 기록 파일 밖에서 고칠 것은 찾지 못했다.

- 검증(작업 트리): validator status=PASS, negative_checks=170, negative_failures=0.
- updated_at은 이 repair 편집 시각 2026-10-20 18:55 UTC다(편집 스크립트가 UTC 시계를 읽어 넣음). 이번 repair 뒤 새 candidate에서 유효한 지적이 나오면 고치지 않고 근거와 범위를 정리해 보고한다.
