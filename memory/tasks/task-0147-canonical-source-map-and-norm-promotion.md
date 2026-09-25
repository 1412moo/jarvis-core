# task-0147-canonical-source-map-and-norm-promotion

- id: `task-0147-canonical-source-map-and-norm-promotion`
- title: `AGENTS.md 기준 지도, Worker 파이프라인 규칙과 상태 전이 계약의 기준 문서 승격, validator 일관성 검사`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-09-25 02:19 UTC`
- updated_at: `2026-09-25 02:33 UTC`
- summary: `과거 memory/tasks 기록과 폐기된 설계가 현재 규칙으로 오인되지 않도록 AGENTS.md에 영역별 기준 지도와 판정 규칙을 두고, 서로 다른 우선순위 선언 3곳을 영역 한정으로 위임한다. task-0142/0144/0145의 Worker 파이프라인 규칙을 SOP 10절(실행 범위와 규칙 분리)로, 실제 상태 전이를 task-model 5절(계약과 발생 경로 분리)로 승격하고 validator가 지도와 코드 값의 일치를 검사한다. 코드와 agent 정의는 바꾸지 않으며 DONE은 Reviewer/QA 후 Owner가 결정한다.`
- source_command: `Owner 지시: task-0147-canonical-source-map-and-norm-promotion 최종 설계 승인 후 구현`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `c4eef3199a0182dfd6f83cd8df09c402f092894f` (main HEAD, push 전) |
| 작업 전 상태 | tracked 수정 없음(`git diff` 비어 있음). untracked `jarvis.bat`, task-0143·task-0146 기록 |
| 줄바꿈 | `core.autocrlf=true`, `.gitattributes` 없음. 대상 파일 index는 모두 LF, 작업 트리는 `AGENTS.md`·`task-model.md`·`execution-status-transition-policy.md`가 CRLF이고 나머지는 LF |
| 보존 대상 | task-0143 worktree/branch 3개(`a02dde9`, r2 `6eec227`과 미커밋 수정, r3 `e05c69c`), task-0146 worktree/branch와 candidate `7cc2b34`·`a0079a1` |

## Owner 결정 (원문)

설계 요청:

```text
좋아. 조사 결과를 바탕으로 다음 작업을 설계하자.

이번에는 task-0146을 재실행하지 않는다.

목표는 Jarvis-Core의 현재 normative/canonical 기준 체계를 정리해서,
과거 memory/tasks 기록이나 폐기된 설계가 현재 규칙으로 오인되지 않도록 만드는 것이다.

새로운 DECISIONS.md / ADR 시스템은 만들지 않는다.
기존 AGENTS.md + SOP + codex-operating-rules + task-model + agent definitions + validator 구조를 정리해서 해결한다.

우선 "기준 체계 정리"를 별도 task 하나로 설계해줘.

반드시 포함할 것:

1. AGENTS.md에 기준 지도 추가
   - 영역별 authoritative source
   - 현재 동작 / task 상태 / 목표·milestone / agent behavior의 구분
   - history로 취급할 문서와 memory/tasks의 위치
   - 같은 영역에서 충돌할 때의 우선순위
   - 안전 gate 충돌 시 fail-closed + Owner escalation
   - Owner 승인의 효력 범위
   - task 승인으로 생긴 상시 규칙을 normative 문서로 승격해야 한다는 규칙

2. 현재 서로 충돌하는 우선순위 선언을 정리
   - docs/ai-team-operating-model.md
   - docs/chatgpt-handoff.md
   - docs/manager-reporting-workflow-v0.1.md
   각각 전체 source-of-truth가 되려고 하지 않도록 기준 지도에 위임하는 형태로 수정

3. task-0144/0145에서 실제로 도입된 규칙 중
   현재 normative 문서에 없는 것을 찾아 SOP에 반영
   - repairable / not_repairable
   - repair budget
   - resume
   - repair_no_changes
   - Reviewer → repair → Reviewer 흐름
   - QA 조건
   - 자동 DONE 등

4. 실제 코드와 문서가 다른 상태 전이도 정리
   - docs/task-model.md
   - docs/execution-status-transition-policy.md
   - 실제 bot/worker 동작
   특히 DOING→FAILED, FAILED→TODO와 자동 전이의 관계를 명확히 할 것.

5. validator가 기준 지도와 핵심 규칙의 존재 및 일관성을 검사하도록 설계
   단순 문자열 검사가 아니라 현재 validator 구조에서 최소 변경으로 가능한 범위를 제안할 것.

6. 반드시 "이번 task에서 무엇을 canonical로 승격하지 않는가"도 명확히 할 것.
   특히:
   - memory/tasks의 일반적인 내용
   - 과거 design 문서
   - handoff
   - master-plan
   을 새로운 normative source로 만들지 말 것.

7. 이번 task의 범위에서 Worker/Reviewer 코드 자체는 수정하지 않는다.
   Worker/Reviewer 연결은 다음 별도 task로 분리한다.

8. 기존 파일에 실제 내용 변경이 있는지 먼저 확인한다.
   현재 작업 디렉터리에 대량 CRLF 변경이 있었다는 이전 관찰이 있으므로,
   기존 변경을 덮어쓰거나 정상 파일을 통째로 재작성하지 않는 방법을 사용한다.

9. untracked jarvis.bat은 절대 건드리거나 stage하지 않는다.
   task-0143/task-0146의 기존 worktree/branch/candidate도 보존한다.

결과는 구현하지 말고 아래 형식으로만 보고해줘.

A. 제안 task ID와 제목
B. 정확한 변경 파일 목록
C. 파일별 변경 목적
D. 현재 문서 충돌과 해결 방식
E. task-0144/0145 규칙 중 normative 승격 목록
F. validator 변경 내용
G. 제외 범위
H. 검증 계획
I. Reviewer가 검증할 핵심 계약
J. 이 task 완료 후 다음 Worker/Reviewer 연결 task에서 해야 할 일
K. task-0146을 재실행할 수 있는 정확한 조건

추측하지 말고 실제 현재 repo를 기준으로 설계해줘.
파일은 아직 수정하지 마.
```

설계 수정 지시:

```text
설계 좋습니다. 구현 전에 3가지만 수정해줘.

1. SOP §10에서 task-0142의 "실험/지원 범위"와 Jarvis 전체에 적용되는 "파이프라인 규칙"을 분리해줘.

특히:
- Studyroom 콘텐츠 1종
- apps/studyroom/content/
- jarvis.bat 금지
- 저장소 밖 worktree

등은 현재 v0.2 E2E 실행 범위인지, 일반 규칙인지 구분해서 명시해줘.
현재 실험 범위를 전체 normative rule로 과도하게 승격하지 말 것.

반대로:
- repairable / not_repairable
- repair budget
- resume
- Reviewer → repair → fresh Reviewer
- non-FINDINGS 즉시 실패
- repair_no_changes
- QA 조건
- ff-only / 자동 DONE의 적용 조건

처럼 파이프라인 자체의 규칙은 normative로 분리해줘.

2. task-model.md의 상태 전이 계약과 구현 경로를 분리해줘.

상태 전이 자체:
TODO→DOING
DOING→DONE
DOING→FAILED
FAILED→TODO
NEEDS_APPROVAL→DOING
NEEDS_APPROVAL→FAILED

와

각 전이를 발생시키는 명령/코드 경로

를 별도로 표현해줘.
명령 이름을 상태 전이 정의 자체와 섞지 말 것.

3. "Reviewer FINDINGS를 Owner가 수용하고 QA로 진행"은 이번 task에서 일반 normative rule로 확정하지 말 것.

현재 SOP의 PASS→QA와 실제 수동 작업 관행이 충돌하는 지점이므로,
Owner 결정이 필요한 미결 사항으로 명시하고 다음 task의 결정 사항으로 넘겨줘.

이 세 가지를 반영한 최종 task-0147 설계만 다시 보여줘.
아직 파일은 수정하지 마.
```

구현 승인:

```text
최종 설계 승인.

task-0147-canonical-source-map-and-norm-promotion을 구현하라.

방금 확정한 최종 설계를 그대로 기준으로 삼는다.

구현 범위:
- AGENTS.md
- docs/jarvis-multi-agent-sop-v0.1.md
- docs/task-model.md
- docs/execution-status-transition-policy.md
- docs/ai-team-operating-model.md
- docs/chatgpt-handoff.md
- docs/manager-reporting-workflow-v0.1.md
- scripts/validate_multi_agent_sop.py
- memory/tasks/task-0147-canonical-source-map-and-norm-promotion.md

이번 task에서는 코드와 agent 정의를 수정하지 않는다.
특히:
- orchestrator/worker/claude_worker.py 수정 금지
- adapters/discord/bot_minimal.py 수정 금지
- .claude/.codex agent 정의 수정 금지
- docs/master-plan.md 수정 금지
- docs/codex-operating-rules.md 수정 금지
- WORKFLOW 계열 문서 수정 금지
- 새 DECISIONS/ADR 문서 생성 금지

핵심은 방금 확정한 설계의 A~K를 그대로 구현하는 것이다.

구현 시 반드시 지킬 것:

1. §10.1은 task-0142의 현재 v0.2 실행 범위일 뿐 일반 규칙으로 승격하지 않는다.
2. §10.2만 범위와 무관한 pipeline normative rule로 둔다.
3. Studyroom/apps/studyroom/content/jarvis.bat/worktree 경로 등의 값은 §10.1의 범위 값으로만 취급한다.
4. task-model §5-1은 상태 전이 계약만, §5-2는 실제 발생 경로만 다룬다. 두 개를 섞지 않는다.
5. Reviewer FINDINGS를 Owner가 수용하고 QA로 진행하는 절차는 이번 task에서 결정하지 않는다. 미결로만 명시한다.
6. canonical_conflict를 새 규칙으로 만들지 않는다.
7. memory/tasks 일반 본문, design 문서, handoff, master-plan 일반 서술을 행동 규칙의 canonical source로 승격하지 않는다.
8. validator는 기존 구조를 최대한 재사용한다. 필요한 검사만 추가하고 validator 자체를 불필요하게 복잡하게 만들지 않는다.
9. §10.2와 실제 코드의 parity 검사는 설계에 적힌 범위까지만 구현한다. 새로운 규칙을 임의로 추가하지 않는다.
10. 정확한 문자열 치환 위주로 편집하고 파일 전체 rewrite는 피한다.
11. 줄바꿈 변경만 발생하지 않도록 한다.
12. jarvis.bat과 기존 실패 worktree/branch/candidate를 건드리지 않는다.

작업 순서:

1. 먼저 현재 작업 트리와 기존 task-0147 계획을 확인한다.
2. 설계와 실제 코드/문서를 대조한다.
3. 구현 전에 task-0147 계획 commit을 만든다.
4. 구현한다.
5. diff를 확인한다.
6. validator 및 기존 smoke들을 실행한다.
7. fresh Reviewer로 검증한다.
8. Reviewer 결과에 따라 필요한 범위 내 repair를 수행한다.
9. QA를 수행한다.
10. checkpoint commit을 만든다.
11. Console Complete까지 진행할 수 있는 상태로 정리한다.

검증 기준:
- 변경 파일은 설계의 9개를 벗어나지 않는다.
- git diff --check PASS
- validator PASS
- validator negative tests PASS
- Worker/Discord/intake/audit/Studyroom 기존 테스트가 코드 무변경 상태에서 기존 결과를 유지한다.
- task-0147 기록이 현재 task parser 규칙에 맞는다.
- jarvis.bat은 계속 untracked 상태이며 commit에 포함되지 않는다.
- 기존 task-0143/task-0146 worktree, branch, candidate는 그대로 보존한다.

중요:
설계에 없는 규칙이나 canonical source를 새로 만들지 말 것.
구현 중 실제 코드와 설계가 불일치하면 임의로 설계를 바꾸지 말고 해당 불일치를 보고한 뒤 멈춰라.
```

## 확정한 범위와 최소 변경 계획

이 계획은 구현 전에 이 기록만 담은 commit으로 먼저 남긴다. 설계 전문은 대화의 최종 설계 A–K이며, 아래는 구현 기준이 되는 요약이다.

| 파일 | 변경 |
| --- | --- |
| `AGENTS.md` | 새 절 `## 기준 지도`만 추가(기존 본문 무변경). 영역표(에이전트 행동 규칙 / 현재 시스템 동작 / task 상태 / 목표·milestone·approval state와 각 기준 파일), History 목록(memory/tasks 본문, design 문서, handoff, WORKFLOW 계열, README, architecture), 판정 규칙 6개(영역 먼저 판정, 같은 영역은 위임 방향·AGENTS 우선, 안전 gate 충돌은 더 제한적인 쪽 + gate_safety_conflict escalation, Owner 승인은 그 task 범위 한정, 기준 문서와 코드 불일치는 drift로 기록하고 해당 실행 중단, History 서술은 규칙 근거 아님), 승격 규칙 |
| `docs/jarvis-multi-agent-sop-v0.1.md` | §9에 §10 예외 참조 1줄. 새 §10 "승인된 예외: Worker 파이프라인" = §10.1 현재 실행 범위(v0.2, 일반 규칙 아님: Studyroom 콘텐츠 1종, `apps/studyroom/content/`, 파이프라인 보호 경로 `jarvis.bat`, 테스트 명령, 저장소 밖 worktree 위치, Owner 전용 `/work`·`/go`와 동시 실행 1개) + §10.2 파이프라인 규칙 11항(candidate, Reviewer 호출, 판정 처리, repair 가능 판정, repair 예산, repair 흐름, resume, QA 6항목, ff-only 반영, 자동 DONE, 실패 처리). §8에 DONE 경로 구분과 "Reviewer FINDINGS 상태에서 QA로 진행하는 예외는 정의돼 있지 않다(미결)" |
| `docs/task-model.md` | §5에 §5-1 허용 전이 계약(6쌍, 명령 이름 없음)과 §5-2 전이 발생 경로(Console Start/Complete, `/go`, `/go` 재시도·resume와 `/retry`, `/approve`, 실행 결과 기록) 추가. 기존 흐름 설명 유지 |
| `docs/execution-status-transition-policy.md` | "자동 적용을 아직 하지 않는 이유"와 Out of Scope의 자동 전이 항목을 현재 사실(`_apply_execution_result`, task-0053/0055)로 교체. 자동 전이 = Owner가 승인한 실행 명령의 결과로만 일어나는 전이 |
| `docs/ai-team-operating-model.md`, `docs/chatgpt-handoff.md`, `docs/manager-reporting-workflow-v0.1.md` | 각 우선순위 절 첫머리에 영역 한정 + 영역 간 판정은 AGENTS.md 기준 지도라는 1줄. 목록 유지 |
| `scripts/validate_multi_agent_sop.py` | 기존 구조 재사용. 문서 5개와 코드 3개를 읽기 대상에 추가, 기준 지도 구조 검사, 위임 문구 검사와 전체 source-of-truth 선언 금지, 파이프라인 값 비교(repair 상한, 사유 코드 집합, QA 키 집합, §10.1 범위 값), 전이 계약과 `TASK_STATUS_TRANSITIONS` 비교와 §5-1 명령 이름 금지, FINDINGS 수용 후 QA 진행의 일반 규칙화 금지, 각 검사의 음성 테스트 |
| 이 기록 | 신규 |

설계와 코드 대조 결과(구현 전): §10.1 범위 값은 `ALLOWED_PREFIX`, `PROTECTED_PATHS`, `TEST_COMMAND`, `WORKTREE_ROOT`, `WORK_KIND_MARKERS`, `_WORKER_LOCK`과 일치. 사유 코드는 `resume_*` 4개, `repair_no_changes`, `reviewer_findings_not_repairable`이 문자열로 있고 `reviewer_findings`는 `reviewer_{판정}` 형태로 만들어진다. QA 키 6개 일치. `TASK_STATUS_TRANSITIONS`는 6쌍. 전이 발생 경로는 `/approve`(NEEDS_APPROVAL→DOING, 거절 시 NEEDS_APPROVAL→FAILED), `/run`(DOING에서 실행), `/retry`(FAILED→TODO→DOING 또는 DOING), `/go`(TODO→DOING, 재시도·resume은 FAILED→TODO→DOING), Console Start(TODO→DOING)·Complete(DOING→DONE), 실행 결과 기록 `_apply_execution_result`(DOING→DONE/FAILED)로 설계와 일치.

제외: 코드와 agent 정의, `docs/master-plan.md`, `docs/codex-operating-rules.md`, WORKFLOW 계열 문서, 새 DECISIONS/ADR, audit `/go` 문제, task-0142 DONE, task-0146 재실행, push. 이번 task에서 확정하지 않는 것: Reviewer FINDINGS를 Owner가 수용하고 QA로 진행하는 절차(미결). canonical로 승격하지 않는 것: memory/tasks 일반 본문, 과거 design 문서, handoff, master-plan의 목표·milestone·approval state 외 서술, §10.1 범위 값.

## 검증 (Implementer 실행, QA 재현 대상)

| # | 항목 | 결과 |
| --- | --- | --- |
| V1 | `python -B scripts/validate_multi_agent_sop.py` | PASS, documents=8, negative_checks=113(기존 92 + 신규 21), negative_failures=0 |
| V2 | 변경 범위 | 계획 commit의 이 기록 + 8개 파일(`AGENTS.md`, SOP, `task-model.md`, `execution-status-transition-policy.md`, 위임 문서 3개, validator). 코드·agent 정의·master-plan·codex-operating-rules·WORKFLOW 계열 무변경 |
| V3 | 줄바꿈 | `git diff --stat`과 `git diff --ignore-cr-at-eol --stat`이 같음(507 추가, 9 삭제). 대상 파일 index EOL 전후 동일(i/lf). CRLF 작업 파일 3개는 CRLF만, 나머지는 LF만 |
| V4 | `git diff --check` | exit 0 |
| V5 | 코드 무변경 smoke | Worker 132/132, Discord self-check 92/92, discord-intake 122/122(task 파일 수에 따라 늘어남, 실패 0), audit-chain PASS, studyroom 5/5, Jarvis Console smoke PASS |
| V6 | 보존 | task-0143 worktree/branch 3개와 r2 미커밋 수정, task-0146 worktree/branch와 candidate 2개, `jarvis.bat` 미추적 |

구현 메모:

- validator 사유 코드 비교 범위는 설계대로 `resume_*`, `repair_no_*`, `reviewer_findings_not_repairable`이다. 처음 패턴 `repair_*`는 SOP §5 budget 이름 `repair_budget`까지 잡아서 설계 범위로 좁혔다. `reviewer_findings`는 코드에서 `reviewer_{판정}` 템플릿으로 만들어지므로 값 비교 대상이 아니다.
- 설계 F1은 `adapters/discord/bot_minimal.py`도 읽기 대상으로 적었지만, 설계의 값 비교(F4·F5)가 그 파일을 쓰지 않아 읽지 않는다. 새 검사를 추가하지 않기 위한 선택이다.
- §10.2 11항은 코드대로 적었다. ff-only 반영 전 실패는 main에 반영되지 않지만, 반영 뒤 기록 단계(checkpoint)에서 실패하면 candidate가 이미 main에 있다.
- `execution-status-transition-policy.md`는 설계의 두 절 외에 목적 절의 "자동 전이 구현은 포함하지 않는다" 한 줄도 같은 사실로 바꿨다. 같은 주장이 남아 있으면 문서 안에서 모순되기 때문이다.

위 네 가지 편차는 구현 뒤 Owner에게 보고했고 Owner가 모두 수용했다. §10.2 11항은 Owner 결정으로 확정됐고(아래 원문), `bot_minimal.py` 제외, 목적 절 수정, 사유 코드 비교 범위(`reviewer_<판정>` 형태 명시, `resume_*`·`repair_no_*`·`reviewer_findings_not_repairable`로 제한, `repair_budget` 제외)는 구현 편차로 수용됐다.

§10.2 11항 Owner 결정 (원문):

```text
[Owner 결정]
현재 구현에서는 ff-only main 반영(§10.2 9항)이 성공한 뒤에 실행 결과 기록과 checkpoint commit이 수행된다.
따라서 §10.2 11항의 "실패 시 main에 반영하지 않는다"는 문구는 9항 이전의 실패에만 적용한다.
9항의 main 반영 이후 기록/checkpoint 단계에서 실패한 경우에는 candidate가 이미 main에 반영된 상태이므로 자동으로 "main 미반영"으로 처리하지 않고 Owner 확인 대상으로 둔다.

이 결정은 현재 task-0147의 규칙과 실제 코드의 일치를 위한 것이다.
```

## 미결 사항 (다음 task의 Owner 결정)

1. Reviewer FINDINGS를 Owner가 수용하고 QA로 진행할 수 있는지와 그 조건. 수동 경로와 파이프라인 경로 각각.
2. Reviewer가 확인하지 못한 항목과 자기 명령 이탈 보고를 finding과 분리할지.

## Repair 이력

retry_budget=1, retry_count=0, repair_budget=1, repair_count=0
