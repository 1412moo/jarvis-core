# task-0147-canonical-source-map-and-norm-promotion

- id: `task-0147-canonical-source-map-and-norm-promotion`
- title: `AGENTS.md 기준 지도, Worker 파이프라인 규칙과 상태 전이 계약의 기준 문서 승격, validator 일관성 검사`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-09-25 02:19 UTC`
- updated_at: `2026-09-25 02:38 UTC`
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
| V0 | 작업 전 기존 변경 확인(설계 요청 8) | 구현 전 `git status --short`와 `git diff`로 tracked 내용 변경이 없음을 확인하고 대상 파일의 `git ls-files --eol`을 기록했다(위 기준선 표) |
| V1 | `python -B scripts/validate_multi_agent_sop.py` | PASS, documents=8, negative_checks=113(기존 92 + 신규 21), negative_failures=0 |
| V2 | 변경 범위 | 계획 commit의 이 기록 + 8개 파일(`AGENTS.md`, SOP, `task-model.md`, `execution-status-transition-policy.md`, 위임 문서 3개, validator). 코드·agent 정의·master-plan·codex-operating-rules·WORKFLOW 계열 무변경 |
| V3 | 줄바꿈 | baseline..candidate에서 `git diff --stat`과 `git diff --ignore-cr-at-eol --stat`이 같음(repair 1 뒤 9개 파일 944 추가, 11 삭제). 대상 파일 index EOL 전후 동일(i/lf). CRLF 작업 파일 3개는 CRLF만, 나머지는 LF만 |
| V4 | `git diff --check` | exit 0 |
| V5 | 코드 무변경 smoke | Worker 132/132, Discord self-check 92/92, discord-intake 122/122(task 파일 수에 따라 늘어남, 실패 0), audit-chain PASS, studyroom 5/5, Jarvis Console smoke PASS |
| V6 | 보존 | task-0143 worktree/branch 3개와 r2 미커밋 수정, task-0146 worktree/branch와 candidate 2개, `jarvis.bat` 미추적 |
| V7 | 이 기록의 task 파서 적합성(구현 승인 검증 기준) | Jarvis Console `parse_task_view_text`로 `valid`, status `DOING` |

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

## 후속 task: Worker/Reviewer 연결 (설계 요청 7에 따라 분리)

이번 task는 Worker/Reviewer 코드와 agent 정의를 바꾸지 않았다. 다음 별도 task에서 할 일(최종 설계 J):

- 위 미결 사항 1·2의 Owner 결정
- `worker_prompt`의 사실 출처 규칙: 요청이 출처를 지정하면 그 파일의 문구만 쓰고, History는 "기록에 따르면"으로만 인용하며, 현재 동작은 코드에서만 가져온다
- `evidence_paths`에 기준 지도나 구현 파일을 포함할지 결정
- `.claude/agents/reviewer.md`와 `.codex/agents/reviewer.toml`을 함께 수정: "approved contract" 정의, 미결 2 반영, validator의 Reviewer 문구 일치 조항 갱신
- Reviewer 자기 한계 보고 항목의 repair 분류 보완
- task-0146 유형(기록 밖 사실 추가)을 재현하는 smoke

## 최종 설계 (대화 보고의 압축 전사)

Reviewer가 설계 A–K와 대조할 수 있도록, Owner가 승인한 최종 설계 보고의 내용을 옮긴다. 원문 그대로가 아니라 표와 강조 서식을 줄이고 문장을 압축한 전사이며, 항목과 값은 원래 보고와 같다. 구현이 이 설계와 달라진 네 가지는 위 "구현 메모"와 Owner 수용 기록을 따른다.

```text
A. 제안 task ID와 제목
- ID: task-0147-canonical-source-map-and-norm-promotion
- 제목: AGENTS.md 기준 지도, Worker 파이프라인 규칙과 상태 전이 계약의 기준 문서 승격, validator 일관성 검사

B. 변경 파일 목록
1. AGENTS.md
2. docs/jarvis-multi-agent-sop-v0.1.md
3. docs/task-model.md
4. docs/execution-status-transition-policy.md
5. docs/ai-team-operating-model.md
6. docs/chatgpt-handoff.md
7. docs/manager-reporting-workflow-v0.1.md
8. scripts/validate_multi_agent_sop.py
9. memory/tasks/task-0147-canonical-source-map-and-norm-promotion.md (신규)
변경하지 않는 파일: 코드 전부, agent 정의 6개, docs/master-plan.md, docs/codex-operating-rules.md, docs/WORKFLOW.md, docs/codex-workflow.md

C. 파일별 변경 목적
AGENTS.md — 새 절 "## 기준 지도"를 추가하고 기존 본문은 바꾸지 않는다.
- 영역표: 에이전트 행동 규칙 = AGENTS.md → SOP·codex-operating-rules.md → agent 정의 / 현재 시스템 동작 = 코드와 결정론적 테스트 / task 상태 = memory/tasks/*.md의 상태 필드 + 형식·전이 계약 docs/task-model.md / 목표·milestone·approval state = docs/master-plan.md (이 영역 한정)
- History 목록: memory/tasks 본문, design 문서, handoff, WORKFLOW 계열, README.md, architecture.md
- 판정 규칙 6개: D절 참조
- Owner 승인 효력 범위와 승격 규칙
SOP
- §9: "§10의 승인된 예외는 제외"라는 참조를 한 줄 추가한다.
- §10 "승인된 예외: Worker 파이프라인" 신규 (E절 참조)
- §8: DONE 경로 구분, "Reviewer FINDINGS 상태에서 QA로 진행하는 예외는 정의돼 있지 않다. 과거 task 기록의 Owner 수용 사례는 해당 task 범위의 결정이다(미결)"
task-model.md §5 — 5-1 허용 전이 계약(전이 쌍만), 5-2 전이 발생 경로. 기존 흐름 설명은 유지한다.
execution-status-transition-policy.md — "자동 적용을 아직 하지 않는 이유"와 "Out of Scope: 자동 상태 전이 구현"을 현재 사실로 바꾼다. 자동 적용 위치는 _apply_execution_result(task-0053/0055). 자동 전이는 "Owner가 승인한 실행 명령의 결과로만 일어난다"고 정의한다.
위임 문서 3개 — 각 우선순위 절 첫머리에 "○○ 영역 한정, 영역 간 판정은 AGENTS.md 기준 지도" 한 줄. 목록 자체는 유지한다.
validator — F절 참조
task 기록 — Owner 원문, 확정 계획, 검증 결과, 미결 사항. 계획만 담은 commit을 구현 전에 먼저 남긴다.

D. 현재 문서 충돌과 해결 방식
- 우선순위 선언 3개가 서로 다름 → 각 목록을 영역 한정으로 만들고 영역 간 판정은 기준 지도로 넘김
- SOP §9는 자동 실행을 금지하는데 파이프라인이 이미 있음 → §10 승인된 예외로 명시하고 §9에서 참조
- task-model에 DOING→FAILED, FAILED→TODO가 없음 → §5-1 계약 표
- transition policy는 "자동 전이 미구현" → 현재 사실로 교체
- SOP §8은 Reviewer PASS 후 QA인데 수동 작업에서 Owner가 minor를 수용하고 QA로 간 사례가 있음 → 이번에 결정하지 않음. 미결로 명시하고 다음 task의 Owner 결정 사항으로 넘김
판정 규칙 6개
1. 영역을 먼저 판정한다. 영역이 다른 기준 파일끼리는 충돌로 보지 않는다.
2. 같은 영역 안에서는 위임 방향을 따른다. 하위 문서가 AGENTS의 원칙이나 gate와 모순되면 AGENTS가 우선하고, 그 모순은 validator 오류로 잡는다.
3. 안전 gate가 충돌하면 더 제한적인 쪽을 적용하고 gate_safety_conflict로 Owner에게 escalation한다.
4. Owner 승인은 그 task 범위에만 효력이 있다. 상시 규칙이 되려면 기준 문서의 "승인된 예외" 절로 승격해야 한다.
5. 기준 문서와 코드가 다르면 drift로 기록하고 해당 규칙을 쓰는 실행은 멈춘다(fail closed).
6. History 목록의 서술은 규칙의 근거가 되지 않는다. 인용은 "기록에 따르면" 형태로만 한다.

E. SOP §10 구성
§10.1 현재 실행 범위 (v0.2 E2E, 일반 규칙 아님): task-0142 Owner 승인이 정한 현재 실행 범위. 넓히거나 바꾸려면 새 Owner 승인과 §10.1 갱신이 필요하고 다른 작업이나 저장소 전체의 규칙으로 해석하지 않는다.
- 지원 작업: Studyroom 콘텐츠 수정 1종, studyroom 없으면 hold (WORK_KIND_MARKERS)
- Worker 변경 허용 경로: apps/studyroom/content/ (ALLOWED_PREFIX)
- 파이프라인 보호 경로: jarvis.bat (PROTECTED_PATHS)
- 테스트 명령: apps/studyroom/run_smoke_tests.py (TEST_COMMAND)
- worktree 위치: 저장소 밖 C:\work\jarvis-core-worktrees\ (WORKTREE_ROOT)
- 진입 명령: Owner 전용 /work, /go, 동시 실행 1개 (bot_minimal.py)
jarvis.bat 금지 자체는 이미 AGENTS와 SOP §6의 일반 gate이며, §10.1은 파이프라인 범위 검사가 이를 강제한다는 사실만 적는다.
§10.2 파이프라인 규칙 (normative, 범위 값과 무관)
1. candidate: attempt 브랜치의 candidate commit으로만 만들고 이전 시도는 삭제하지 않는다.
2. Reviewer 호출: Owner 요청 원문, baseline..candidate 변경 파일 목록, 범위 기대값만 전달. Worker 동작이나 테스트 결과를 주장하지 않는다. evidence는 요청에 이름이 나온 task 기록만 candidate 시점 기준으로 준다.
3. 판정 처리: PASS → QA. FINDINGS가 아닌 판정(BLOCKED, UNKNOWN, Reviewer 오류 종료)은 repair 없이 즉시 실패.
4. repair 가능 판정: 모든 항목 evidence가 변경 파일을 가리키지 않으면 reviewer_findings_not_repairable로 실패하고 repair 예산을 쓰지 않는다. 한 항목이라도 가리키면 repair 대상.
5. repair 예산: SOP §5 repair_budget과 같은 의미, 상한 1, 환경변수나 인자로 올릴 수 없음. 소진되면 reviewer_findings로 실패하고 Owner 결정을 기다린다.
6. repair 흐름: 같은 worktree에서 변경 파일을 가리키는 지적만 고친다. 변경 없으면 repair_no_changes. 새 candidate는 이전 candidate가 parent, 이전 Reviewer 결과 무효, fresh Reviewer.
7. resume: FAILED task에만, Owner가 명시적으로 요청할 때만. 직전 시도의 허용 경로 변경(commit·미커밋)을 현재 main baseline의 새 시도에 복사. 모든 검사는 새 worktree 생성 전. 거절 사유 resume_no_previous_attempt, resume_no_changes, resume_scope_violation, resume_conflict.
8. QA: head_is_candidate, change_set_matches, diff_check, jarvis_bat_absent, json_valid, tests_rerun 6개 모두 통과.
9. 반영: QA 통과 후 main HEAD가 baseline과 같을 때만 ff-only. 움직였으면 반영하지 않고 실패.
10. 자동 DONE: 9가 성공한 경우에만 실행 결과 기록과 DOING→DONE을 한 번의 원자적 쓰기로 적용하고 task 파일을 checkpoint commit. 파이프라인 경로에만 적용되는 예외이며 수동 SOP 작업의 DONE 경로(§8)를 바꾸지 않는다.
11. 실패 처리: 어떤 단계에서 실패해도 DOING→FAILED로 기록하고, main에 반영하지 않으며, 시도는 보존한다.
승격하지 않는 것: "canonical conflict"는 코드와 문서 어디에도 규칙으로 존재하지 않아 만들지 않는다.
task-model.md §5
5-1 허용 전이 계약 (명령 이름 없음, 6쌍): TODO→DOING, DOING→DONE, DOING→FAILED, FAILED→TODO, NEEDS_APPROVAL→DOING, NEEDS_APPROVAL→FAILED. 표에 없는 전이는 durable writer가 거부(TASK_STATUS_TRANSITIONS). 자동 전이란 Owner가 승인한 실행의 결과로 코드가 적용하는 전이이며 독립적인 자동 전이는 없다.
5-2 전이 발생 경로 (5-1의 쌍만 사용): Console Start / Complete → TODO→DOING / DOING→DONE; /go (TODO) → TODO→DOING; /go 재시도·resume, /retry (FAILED) → FAILED→TODO 직후 TODO→DOING; /approve → NEEDS_APPROVAL→DOING 또는 NEEDS_APPROVAL→FAILED; 실행 결과 기록(_apply_execution_result, /go·/approve·/run·/retry 실행 후) → 성공 DOING→DONE, 실패 DOING→FAILED. /approve, /run, /retry 각 경로가 실제로 호출하는 전이 쌍은 구현 단계에서 코드로 한 번 더 확인하고 표에 반영한다.

F. validator 변경 내용 (현재 구조 유지: _load_sources → 순수 _validate_* → 음성 mutation 검사)
1. 검사 대상 추가: DOCUMENT_PATHS에 위임 문서 3개, task-model.md, transition policy. CODE_PATHS에 claude_worker.py, task_file_writer.py, bot_minimal.py(값을 읽기 위한 것이며 기준 문서로 만드는 것이 아님).
2. _validate_source_map: 영역 4개, 표의 경로가 실제 파일, History 필수 항목, 행동 규칙 행에 master-plan·handoff·memory/tasks·design 문서가 있으면 오류.
3. _validate_delegation: 위임 문서 3개에 지도 참조. CONTRADICTIONS에 전체 source of truth 선언 정규식.
4. _validate_pipeline_parity: REPAIR_BUDGET_MAX(AST)와 §10.2 상한, §10.2 실패 사유 코드 집합과 claude_worker.py 사유 문자열 집합 양방향, QA 항목 6개와 qa["…"] 키 집합, §10.1 범위 값(ALLOWED_PREFIX, PROTECTED_PATHS, 테스트 명령 경로)과 코드 상수.
5. _validate_transition_contract: §5-1 쌍 집합과 TASK_STATUS_TRANSITIONS(AST) 일치, §5-2의 모든 전이가 §5-1 안, §5-1에 /로 시작하는 명령 이름이 있으면 오류.
6. 미결 사항 보호: "FINDINGS 수용 후 QA 진행"을 일반 규칙으로 정한 문장이 생기면 오류(CONTRADICTIONS), 미결 문장 존재 확인.
7. 음성 테스트: 새 검사마다 실패해야 하는 변형(약 +15개).

G. 제외 범위
- 코드와 agent 정의 수정(Worker/Reviewer 연결은 다음 task), master-plan.md 수정, 새 DECISIONS/ADR, WORKFLOW 계열 편집, audit /go 문제, task-0142 DONE, task-0146 재실행, push
- 이번 task에서 확정하지 않는 것: Reviewer FINDINGS를 Owner가 수용하고 QA로 가는 절차(미결로만 명시)
- canonical로 승격하지 않는 것: memory/tasks 일반 내용(상태 필드만 인정), 과거 design 문서, handoff, master-plan의 목표·milestone·approval state 외 서술, §10.1 실행 범위 값, task 기록 속 Owner 승인(§10으로 옮긴 항목 외)

H. 검증 계획
1. 작업 전: tracked 변경 없음 확인, 대상 파일 git ls-files --eol과 worktree/branch 목록 기록
2. 정확한 문자열 치환만, 전체 rewrite 금지, CRLF 작업본 유지
3. git diff --stat과 git diff --ignore-cr-at-eol --stat 동일, 저장본 i/lf 유지, git diff --check, 변경 파일은 B의 9개
4. validator PASS·음성 테스트 실패 0, Worker 132/132, Discord 92/92, discord-intake·audit-chain·studyroom smoke, Console 파서로 새 task 기록 valid
5. jarvis.bat 미추적·commit 없음, task-0143 3개와 r2 미커밋 수정, task-0146 worktree와 candidate 2개 보존
6. 순서: 계획 commit → 구현 commit → fresh Reviewer → QA → checkpoint → Owner Console Complete

I. Reviewer가 검증할 핵심 계약
- 지도와 판정 규칙이 Owner 원문 항목 1–7과 수정 3개를 충족하는지
- §10.1 값이 범위로만 표현되고 §10.2가 범위 값과 무관한 규칙인지
- §10.2와 §5-2의 각 문장이 현재 코드에 있는 동작인지(evidence: claude_worker.py, bot_minimal.py, task_file_writer.py), 코드에 없는 규칙이 새로 생기지 않았는지
- §5-1에 명령 이름이 없고 6쌍이 TASK_STATUS_TRANSITIONS와 같은지
- FINDINGS 수용 후 QA 진행이 미결로만 적혔는지
- master-plan, handoff, memory/tasks, design 문서가 행동 규칙의 근거로 승격되지 않았는지
- validator 새 검사가 값과 구조를 비교하고 음성 테스트가 각 검사를 실패시키는지
- 코드, agent 정의, jarvis.bat이 변경 집합에 없고 줄바꿈만 바뀐 줄이 없는지

J. 다음 Worker/Reviewer 연결 task에서 할 일
- Owner 결정 1: Reviewer FINDINGS를 Owner가 수용하고 QA로 진행할 수 있는지와 조건(수동·파이프라인 각각)
- Owner 결정 2: Reviewer가 확인하지 못한 항목·자기 명령 이탈을 finding과 분리할지
- worker_prompt 사실 출처 규칙, evidence_paths 범위, Reviewer 정의(reviewer.md와 reviewer.toml 함께, approved contract 정의, validator 문구 일치 조항 갱신), repair 분류 보완, task-0146 유형 smoke

K. task-0146을 재실행할 수 있는 정확한 조건
1. task-0147 DONE
2. J의 연결 task가 Owner 결정 1·2를 반영하고 DONE
3. 봇을 그 main HEAD로 재시작하고 새 코드 로드 확인
4. main tracked 변경 없음, task-0146 FAILED, 첫 시도(7cc2b34, a0079a1)와 worktree 보존
5. Owner가 Discord에서 /go task-0146-studyroom-glossary-fast-forward-merge-1-jarvis-example-task-0142 직접 전송(resume 아님)
6. 성공 판정은 task-0142 원래 조건(QA PASS → ff-only 반영 → DONE → checkpoint → Discord 성공 보고)으로 하고 결과를 task-0142 기록에 추가
```

## Repair 이력

retry_budget=1, retry_count=0, repair_budget=1, repair_count=1

| # | 원인 | 조치 |
| --- | --- | --- |
| 1 | Reviewer FINDINGS (candidate `188655172f7366af0f4cb4020e2ea2d1ef3232a4`): minor 6 — `execution-status-transition-policy.md`의 적용 범위 줄과 Future Scope 첫 항목이 새 "현재 적용 상태" 절과 모순, 요약에 설계 요청 8의 "기존 변경 먼저 확인"이 없음, 설계 요청 7의 Worker/Reviewer 연결 분리가 기록에 없음, 구현 승인의 "task 파서 적합성" 검증 항목이 없음, 설계 A–K가 저장소에 없어 대조 불가, V1–V6은 Reviewer가 재현할 수 없어 QA 대상 | 적용 범위 줄을 승인된 실행 4개로 맞추고 이미 구현된 Future Scope 항목을 삭제(같은 문서 안 모순 제거, Owner가 수용한 목적 절 수정과 같은 원칙), 검증 표에 V0(작업 전 확인)과 V7(task 파서) 추가, "후속 task" 절 추가, 최종 설계 보고 원문을 이 기록에 옮김. V1–V7은 QA에서 재현. 새 candidate에 fresh Reviewer → QA |
