# task-0134-reviewer-owner-approval-binding

- id: `task-0134-reviewer-owner-approval-binding`
- title: `Reviewer 정의에 Owner 승인 원문 필수 조건(Approval binding)을 넣고 validator 가 새 SOP 조항과 이 조건을 필수 문구로 검사`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-09-17 12:57 UTC`
- updated_at: `2026-09-17 16:28 UTC`
- summary: `task-0133 은 SOP 에 Manager 가 Reviewer 에게 Owner 승인 원문을 넘기는 의무를 추가했지만 Reviewer 정의는 여전히 호출자가 준 계약만 받아 원문 없이 요약으로 PASS 할 수 있었고 validator 는 새 SOP 조항을 검사하지 않았다. .claude/agents/reviewer.md 에 Approval binding (fail closed) 를, .codex/agents/reviewer.toml 에 같은 조건을 넣고, validator 에 SOP 조항과 reviewer.toml 문구의 필수 검사와 negative self-test 를 추가한다. SOP 문서, 다른 agent 정의, 기존 task, Console 문서는 무변경. DONE 은 Reviewer/QA 후 Owner 가 Console Complete 로 결정한다.`
- source_command: `Owner 가 승인한 task-0134 Reviewer 승인 원문 강제 work package 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `cf4df99344c8b36b7270e135b964fa26e838d18b` |
| 작업 전 상태 | tracked 수정 없음, untracked `jarvis.bat` 만, 로컬 main 은 origin 보다 10 commit 앞섬 |
| validator | `python -B scripts/validate_multi_agent_sop.py` → `negative_checks=28`, `negative_failures=0`, `status=PASS` |

## 무엇이 문제였나

task-0133 이 추가한 SOP §3 조항은 Manager 의 의무다. 그 의무를 강제하는 곳이 없었다.

| 위치 | 상태 |
| --- | --- |
| `.claude/agents/reviewer.md` | hash 가 없으면 `BLOCKED` 로 fail closed 하지만 Owner 승인 원문 요구는 없음. 호출자가 준 "approved contract" 만으로 PASS 가능 |
| `.codex/agents/reviewer.toml` | 같은 구조. "approved contract" 만 언급 |
| `scripts/validate_multi_agent_sop.py` | reviewer 관련 필수 문구는 `reviewer.toml` 의 read-only 네 문구뿐. task-0133 SOP 조항은 필수 문구가 아님 |

## Owner 승인 원문

승인 메시지:

```text
task-0134 진행 승인합니다.

Owner 결정:
1. `.claude/agents/reviewer.md`는 이번 validator 검사 대상에 포함하지 않습니다.
   - validator는 기존 구조대로 `.codex/agents/reviewer.toml`의 필수 문구를 검사합니다.
   - `.claude/agents/reviewer.md`와 `.codex/agents/reviewer.toml`의 장기적 정합성/validator 대상 확장은 별도 과제로 남깁니다.

2. QA에서 실제 Reviewer 동작 확인 2회를 승인합니다.
   - 검증 대상 candidate: `af929141bbc39c14d045feebfc8da603c0184cc5`
   - Owner 승인 원문 없이 호출:
     - 기대값: `verdict: BLOCKED`
     - blocking finding 확인
   - Owner 승인 원문을 지정된 표시 구역으로 포함하여 호출:
     - 정상 review 진행 확인
   - 두 호출 모두 read-only이며 저장소 변경이 없어야 합니다.
   - 변경된 Reviewer 정의를 검증하는 Reviewer는 변경 전 정의를 사용합니다. 이 점을 task-0134 기록에 명시하세요.

이번 작업의 핵심 acceptance criterion:
- Owner 승인 원문이 없으면 Reviewer가 PASS할 수 없어야 합니다.
- 실제 호출 결과가 `BLOCKED`가 아니면 candidate를 PASS 처리하지 말고 즉시 Owner에게 보고하세요.
- 원문을 포함한 호출에서는 정상적인 review가 진행되어야 합니다.

승인된 변경 범위:
- `.claude/agents/reviewer.md`
  - Approval binding (fail closed) 추가
- `.codex/agents/reviewer.toml`
  - Owner 승인 원문 필수 조건 추가
- `scripts/validate_multi_agent_sop.py`
  - 새 필수 조항 검사 및 negative self-test 추가
- `memory/tasks/task-0134-*.md`
  - task 기록 1개 생성

절대 변경하지 말 것:
- `docs/jarvis-multi-agent-sop-v0.1.md`
- manager.toml
- implementer.toml
- qa.toml
- docs.toml
- 기존 task 기록
- Console
- master-plan
- chatgpt-handoff
- Roadmap
- 새 gate 추가
- repair/retry budget 변경
- candidate 규칙 변경
- task-0131 결과 기록 commit 취급의 SOP 일반화
- `jarvis.bat`

절차:
1. 먼저 현재 baseline/read-only 상태 확인.
2. task-0134 기록 작성.
3. Implementer가 승인된 네 파일 범위만 수정.
4. validator 실행:
   `python -B scripts/validate_multi_agent_sop.py`
   - `status=PASS`
   - `negative_failures=0`
   - 기존 28개보다 추가된 negative self-test 수가 반영되어야 함.
5. 각 새 필수 문구를 제거하는 mutation 검증을 수행하고 validator가 FAIL하는지 확인.
6. Reviewer 동작 QA:
   A. `af929141...`에 Owner 승인 원문 없이 Reviewer 호출 → 반드시 `BLOCKED`
   B. 같은 candidate에 Owner 승인 원문 포함 → 정상 review
   C. 두 테스트 모두 저장소 변경 없음 확인
7. `git diff --check`
8. Console smoke:
   `python -B apps/jarvis-console/run_smoke_tests.py`
9. diff scope가 정확히 아래 4개 파일인지 확인:
   - `.claude/agents/reviewer.md`
   - `.codex/agents/reviewer.toml`
   - `scripts/validate_multi_agent_sop.py`
   - `memory/tasks/task-0134-*.md`
10. Reviewer → QA 순서로 진행.
11. Reviewer/QA 결과와 실제 동작 검증 결과를 task-0134 기록에 반영.
12. candidate checkpoint commit 생성.
13. 이번 결정상 push하지 않습니다.
14. `?? jarvis.bat`는 절대 건드리지 않습니다.

중요:
- task-0133에서 확정한 SOP 규칙을 이번 작업에 실제 적용하세요.
- Owner 승인 원문과 제안서가 충돌하는 경우 구현을 진행하지 말고 bounded question을 먼저 올리세요.
- Manager 요약과 Owner 승인 원문을 Reviewer에게 모두 전달하세요.
- 추측으로 범위를 넓히지 마세요.
- 문제가 발견되면 임의로 범위를 넓히지 말고 먼저 보고하세요.
```

구현 전 bounded question 과 Owner 답 (원문 조건과 실제 동작·SOP 순서 충돌 2 건):

```text
Q1. 승인 원문의 '변경된 Reviewer 정의를 검증하는 Reviewer는 변경 전 정의를 사용합니다. 이 점을 task-0134 기록에 명시하세요.'가 실제 동작과 충돌해요. Claude Code 문서에 따르면 .claude/agents/*.md를 고치면 같은 세션의 다음 호출부터 바뀐 정의가 적용돼요(재시작 불필요). 그래서 6단계 동작 확인과 10단계 candidate Reviewer 모두 새 정의로 돌아요. 어떻게 할까요?
A1. 실제 동작대로 기록 (Recommended)
Q2. 승인 절차에서 6단계 'Reviewer 동작 QA'가 10단계 'Reviewer → QA'보다 앞에 있어요. SOP는 QA를 Reviewer PASS 뒤에 두어요. 6단계 호출 2회를 어느 단계에서 할까요?
A2. Implementer 사전 확인 + QA 재현 (Recommended)
```

Q1 근거: Claude Code sub-agents 문서는 subagent 파일을 감시하고 편집을 몇 초 안에 감지해 다음 위임부터 갱신된 정의를 재시작 없이 쓴다고 설명한다(새 `agents` 디렉터리의 첫 파일, `--add-dir` 디렉터리, slash command 비활성 세션은 예외). 이 세션은 예외에 해당하지 않는다.

candidate `172a5990f09a0494b3bc20f5ec35017af945d948` Reviewer finding 1 (validator 의 SOP 조항 필수 검사가 승인 원문에 직접 명시되지 않음) 에 대한 Owner 결정:

```text
Owner 결정:
task-0133에서 확정한 SOP 규칙을 task-0134 validator가 실제로 필수 검사하도록 한 것과, 그에 대응하는 SOP negative self-test 3개를 추가한 것은 task-0134의 승인 범위에 포함됩니다.
```

## Manager 요약 (원문 해석)

| # | 조건 | 원문 근거 |
| --- | --- | --- |
| 1 | 변경 파일은 `.claude/agents/reviewer.md`, `.codex/agents/reviewer.toml`, `scripts/validate_multi_agent_sop.py`, 이 기록 네 개 | 승인된 변경 범위, 절차 9 |
| 2 | validator 는 SOP 의 task-0133 조항과 `reviewer.toml` 새 문구만 필수 검사. `reviewer.md` 는 검사 대상 아님 | 결정 1, 승인된 변경 범위, Reviewer finding 1 Owner 결정 |
| 3 | 새 필수 문구 각각의 negative self-test 추가. 기존 28 개보다 늘어야 함 | 절차 4, 5 |
| 4 | 승인 원문이 없으면 Reviewer 는 PASS 할 수 없고 `BLOCKED` 와 blocking finding | acceptance criterion, 결정 2 |
| 5 | 동작 확인 A/B 는 `af929141…` 대상. Implementer 사전 확인 1 회 + candidate Reviewer PASS 후 QA 재현 1 회. A 가 `BLOCKED` 가 아니면 PASS 처리하지 않고 즉시 Owner 보고 | 결정 2, acceptance criterion, A2 |
| 6 | candidate 를 리뷰하는 Reviewer 도 바뀐 정의로 동작한다는 실제 사실을 기록 | 결정 2 마지막 항목, A1 |
| 7 | SOP 문서, manager/implementer/qa/docs toml, 기존 task, Console, master-plan, handoff, Roadmap 무변경. 새 gate, budget·candidate 규칙 변경, task-0131 취급 일반화 없음 | 절대 변경하지 말 것 |
| 8 | candidate checkpoint commit 까지. push 하지 않음. `jarvis.bat` 무시 | 절차 12–14 |

## Manager assignment

| 역할 | assignment |
| --- | --- |
| Implementer | 위 네 파일. validator, mutation, 동작 사전 확인 A/B, `git diff --check`, smoke. candidate local commit 1 개 |
| Reviewer | candidate full hash 에 고정, 네 파일 scope, strict read-only. Manager 요약과 Owner 승인 원문을 표시 구역으로 받는다. 바뀐 정의로 동작 |
| QA | Reviewer PASS 후 같은 candidate 에서 validator, mutation, 동작 확인 A/B 재현, diff 범위, `git diff --check`, smoke |
| Docs | 별도 Docs 실행 `not_required` (변경 자체가 정의·검사 문서) |
| 완료 | Reviewer/QA PASS 후에도 `DOING`. `DOING → DONE` 은 Owner 가 Console 에서 결정 |

## Repair 이력

retry_budget=1, retry_count=0, repair_budget=1, repair_count=1

| # | 원인 | 조치 |
| --- | --- | --- |
| 1 | Reviewer minor 1 건 (candidate `172a5990f09a0494b3bc20f5ec35017af945d948`): validator 의 task-0133 SOP 조항 필수 검사와 SOP negative self-test 3 개가 승인 원문에 직접 명시되지 않아 Manager 해석으로 보임. 나머지 minor 2 건은 Reviewer 허용 명령으로 실행할 수 없는 검사를 QA 로 넘긴 제한 보고 | Owner 결정을 원문 그대로 기록하고 Manager 요약 2 행 근거에 추가. validator·agent 정의 무변경. 새 candidate 에 fresh Reviewer → QA |
