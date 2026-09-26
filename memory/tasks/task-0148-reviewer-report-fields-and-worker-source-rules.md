# task-0148-reviewer-report-fields-and-worker-source-rules

- id: `task-0148-reviewer-report-fields-and-worker-source-rules`
- title: `Reviewer 보고의 확인 불가·자기 이탈 필드 분리, Owner의 조건부 minor 수용 규칙, Worker 사실 출처 규칙`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-09-26 08:41 UTC`
- updated_at: `2026-09-26 10:08 UTC`
- summary: `Reviewer 보고에서 확인할 수 없는 항목(unverified)과 Reviewer 자신의 명령 이탈(self_deviations)을 findings와 분리해 판정은 findings로만 정하고, unverified는 QA로 넘기며 이탈은 retry 1회 뒤 reviewer_self_deviation으로 실패시킨다. Owner의 minor finding 수용을 수동 경로 한정 조건부 규칙으로 SOP 8절에 정하고, Worker가 요청이 지정한 출처의 사실만 쓰도록 worker_prompt를 바꾼다. DONE은 Reviewer/QA 후 Owner가 결정한다.`
- source_command: `Owner 지시: 결정 1·2 권장안 확정과 task-0148 설계 승인`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `5fdc863bfee3e9f85f0482c3146a21883e04b8a2` (main HEAD, push 전) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat`, task-0143·task-0146 기록 |
| 줄바꿈 | 대상 파일 index는 모두 LF. 작업 트리는 `AGENTS.md`만 CRLF, 나머지 LF |
| 보존 대상 | task-0143 worktree/branch 3개(`a02dde9`, r2 `6eec227`과 미커밋 수정, r3 `e05c69c`), task-0146 worktree/branch와 candidate `7cc2b34`·`a0079a1` |

## Owner 결정 (원문)

결정 1·2 확정:

```text
권장안대로 확정. task-0148 설계 가져와
```

위 확정이 가리키는 권장안 보고(대화 기록에서 그대로 옮김):

```text
결정 1·2를 선택지와 권장안으로 정리했습니다. 파일은 수정하지 않았습니다.

## 현재 사실
- **Reviewer 정의** (`.claude/agents/reviewer.md`, `.codex/agents/reviewer.toml`)
  - "확인하지 못한 항목"과 "자기가 쓴 명령의 한계"도 minor finding으로 적습니다.
  - finding이 하나라도 있으면 판정이 FINDINGS로 고정됩니다.
- **SOP §8:** QA는 Reviewer PASS 뒤에만 진행합니다. FINDINGS 수용은 미결로 적혀 있습니다.
- **실제 이력:** task-0144, 0145, 0147의 마지막 FINDINGS는 대부분 candidate 결함이 아니었습니다.
  - 테스트나 보존처럼 Reviewer 명령으로는 확인할 수 없는 항목
  - Reviewer 자신의 명령 형식 이탈
  - Manager 요약 누락

  매번 Owner가 수용하거나 repair를 추가 승인해서 넘어갔습니다.
- **파이프라인:** FINDINGS를 Owner가 수용하는 명령이 없어서, 항상 FAILED로 끝나고 Owner에게 넘어갑니다.

## 결정 1: Reviewer FINDINGS를 수용하고 QA로 갈 수 있는가

| 안 | 내용 | 장단점 |
| --- | --- | --- |
| A. 수용 금지 | PASS만 QA로 진행 | 가장 엄격함. 결정 2 없이 이 안을 고르면 거의 모든 task가 멈추고 Owner가 repair를 추가 승인하는 일이 반복됨 |
| **B. 조건부 Owner 수용 (권장)** | 아래 조건을 모두 만족할 때만 Owner가 수용하고 QA로 진행 | 지금까지의 관행을 규칙으로 고정하면서 수용 범위를 제한함 |
| C. Manager 판단으로 minor 수용 | Owner 개입 없음 | 빠르지만 승인 경계가 흐려짐. 권장하지 않음 |

**B안 조건**
- minor만 수용할 수 있습니다. blocking과 major는 수용할 수 없습니다.
- 지적마다 Owner가 수용한다는 원문을 task 기록에 남겨야 합니다.
- 수용은 그 candidate에만 효력이 있습니다. candidate가 바뀌면 무효입니다.
- QA는 그대로 전부 통과해야 합니다. 수용이 QA를 대신하지 않습니다.
- **파이프라인은 이번에 바꾸지 않습니다.** 지금처럼 FAILED로 끝나고 Owner에게 넘어갑니다. 수용 명령(예: `/go <id> accept`)은 필요해질 때 별도 task로 만듭니다.

## 결정 2: Reviewer 보고에서 확인 불가 항목과 자기 한계를 finding과 분리할까

| 안 | 내용 | 장단점 |
| --- | --- | --- |
| A. 현행 유지 | 모두 minor finding | PASS가 사실상 나오지 않음. 결정 1 B안에 계속 기대게 됨 |
| **B. 필드 분리 (권장)** | 보고 양식에 필드 두 개 추가, 판정은 findings만으로 결정 | 판정이 candidate 결함만 반영하게 되고, 확인 못 한 사항도 숨기지 않고 드러남 |
| C. 보고하지 않음 | 확인 못 한 사항을 적지 않음 | 투명성을 잃음. 권장하지 않음 |

**B안 세부**
- **`unverified:`** Reviewer 명령으로 확인할 수 없는 항목을 적습니다(테스트, worktree, 외부 자료). 이 항목은 QA가 넘겨받아 재현합니다.
- **`self_deviations:`** Reviewer 자신의 명령 형식 이탈을 적습니다. 이탈이 있으면 그 검토는 무효로 보고, **retry**(candidate 변경 없이 Reviewer 재실행, `retry_budget` 사용)로 처리합니다. repair가 아닙니다.
- **함께 정할 것 (권장):** Manager 요약 누락이나 승인 원문 전달 누락 같은 "호출 결함"도 candidate를 바꿀 일이 아니므로 retry로 처리합니다. 호출을 고쳐 같은 candidate를 다시 검토받습니다. 지금은 이런 지적이 repair 횟수를 소모하거나 FINDINGS로 남습니다.

**B안의 영향 범위** (task-0148 범위)
- Reviewer 정의 두 파일을 함께 수정해야 합니다.
- validator의 Reviewer 문구 일치 조항("verdict는 findings에서 기계적으로 결정", severity 목록 등)도 함께 바꿔야 합니다.
- 파이프라인이 findings 구간을 읽는 부분(`_split_findings`)은 새 필드에서 구간이 끝나도록 고쳐야 합니다.
- 파이프라인에서 `self_deviations`가 있으면 Reviewer를 1회 다시 실행하는 동작을 추가합니다.

## 권장 조합
**결정 2는 B안, 결정 1은 B안(수동 경로 한정)**을 권장합니다.
- 결정 2로 판정에서 잡음이 빠지면, FINDINGS가 나올 때는 실제 candidate 결함인 경우가 대부분이 됩니다.
- 결정 1은 그래도 남는 minor를 Owner가 명시적으로 수용하는 예외 통로로만 씁니다.

둘 다 확정하시면, 이 결정 원문을 포함한 task-0148 설계(A–K 형식)를 먼저 가져오겠습니다.
```

설계 승인:

```text
설계안 검토했습니다. 전체적으로 승인합니다.

다만 구현 전에 아래 2가지만 명확히 반영해 주세요.

1. `unverified`는 FINDINGS 판정을 발생시키지 않을 뿐, 전체 task의 PASS/DONE을 의미하지 않는다는 점을 명확히 해 주세요.
   - Reviewer 단계에서는 findings가 없으면 PASS 가능
   - unverified는 반드시 QA로 전달
   - 최종 acceptance는 기존대로 QA가 검증한 뒤 결정
   - smoke의 "unverified만 있으면 PASS"도 Reviewer 단계의 PASS인지 명확히 해 주세요.

2. `self_deviations`는 retry 1회까지만 허용하고, 재검토에서도 다시 발생하면 `reviewer_self_deviation`으로 실패하며 repair 예산은 절대 사용하지 않는다는 계약을 명확히 해 주세요.

그 외 설계는 그대로 진행해 주세요.

`evidence_paths`도 이번 task에서는 변경하지 않는 것으로 확정합니다.

코드 수정 전에 계획 commit부터 진행해 주세요.
```

## 확정한 범위와 최소 변경 계획

이 계획은 구현 전에 이 기록만 담은 commit으로 먼저 남긴다. 설계 전문은 아래 "최종 설계 (대화 보고 원문)"이며, 설계 승인의 명확화 두 가지를 함께 따른다.

| 파일 | 변경 |
| --- | --- |
| `AGENTS.md` | 조직 흐름의 Reviewer 줄 뒤에 minor finding의 Owner 수용 예외는 SOP §8이라는 참조 1줄 |
| `docs/jarvis-multi-agent-sop-v0.1.md` | §5 retry 정의에 Reviewer 자기 명령 이탈로 무효가 된 검토의 재검토와 호출 결함을 고친 같은 candidate의 재검토 추가. §8 미결 문장을 결정 1 규칙(minor만, 지적별 Owner 원문 기록, 그 candidate 한정, QA 전부 통과, Manager 수용 불가, 파이프라인 미적용)으로 교체. §10.2에 unverified는 판정에 쓰지 않고 QA로 넘김, self_deviations는 retry 1회 뒤 `reviewer_self_deviation` 실패 |
| `.claude/agents/reviewer.md`, `.codex/agents/reviewer.toml` | 같은 문구로 `unverified:`와 `self_deviations:` 필드 추가(`findings:` 뒤, `note:` 앞), 확인 불가 항목과 명령 이탈을 findings에서 옮김, "확인 불가·획득 한계는 minor" 규칙 삭제, verdict는 findings로만 결정, approved contract 정의 |
| `scripts/validate_multi_agent_sop.py` | `REVIEWER_ROLE_CLAUSES`에 새 필드 조항, SOP 결정 1 필수 조항 검사로 미결 문장 검사 교체, 수용 관련 CONTRADICTIONS 패턴 교체(Manager 수용, major·blocking 수용, 파이프라인 자동 수용), `PIPELINE_REASON_PATTERN`에 `reviewer_self_deviation`, 음성 테스트 |
| `orchestrator/worker/claude_worker.py` | `worker_prompt` 사실 출처 규칙, `_split_findings`가 새 필드에서 findings 구간 종료, self_deviations가 있으면 같은 호출로 Reviewer 재검토 1회(`reviewer_retries`), 다시 있으면 `reviewer_self_deviation` 실패(repair 예산 미사용). `evidence_paths`와 Reviewer 호출 요약 무변경 |
| `orchestrator/worker/run_smoke_tests.py` | 가짜 Reviewer 모드(unverified만 있는 Reviewer 단계 PASS, 이탈 1회 뒤 PASS, 이탈 반복, 혼합)와 검사 |
| 이 기록 | 신규 |

설계 승인 명확화 반영:

1. `unverified`는 FINDINGS 판정을 만들지 않을 뿐 task 전체의 PASS나 DONE을 뜻하지 않는다. findings가 없으면 Reviewer 단계는 PASS가 될 수 있지만, unverified 항목은 반드시 QA로 넘기고 최종 acceptance는 기존대로 QA 검증 뒤에 결정한다. 이 문장을 SOP와 두 Reviewer 정의에 넣는다. smoke의 "unverified만 있는 경우"는 Reviewer 단계 PASS로 이름 붙이고, 파이프라인이 그 뒤 QA 단계를 실제로 거치는지도 확인한다.
2. `self_deviations`는 retry 1회까지만 허용한다. 재검토에서도 다시 나오면 `reviewer_self_deviation`으로 실패하며 repair 예산은 절대 쓰지 않는다. 이 계약을 SOP와 코드에 명시하고 smoke로 repair 0회를 확인한다.

`evidence_paths`는 이번 task에서 변경하지 않는다(Owner 확정).

제외: 파이프라인 FINDINGS 수용 명령, `adapters/discord/bot_minimal.py`, `evidence_paths`, audit `/go` 문제, task-0142 DONE, task-0143 정리, task-0146 재실행, 봇 재시작, push, master-plan, codex-operating-rules, task-model, 나머지 agent 정의, Skill, 새 DECISIONS/ADR.

## 검증 (Implementer 실행, QA 재현 대상)

| # | 항목 | 결과 |
| --- | --- | --- |
| V0 | 작업 전 확인 | tracked 변경 없음, 대상 파일 EOL 기록(기준선 표) |
| V1 | `python -B scripts/validate_multi_agent_sop.py` | PASS, negative_checks=125(기존 113 + 신규 12), negative_failures=0. repair 1 뒤 128 |
| V2 | Worker smoke | 147/147(기존 132 + 신규 15), repair 1 뒤 160/160(`qa` 짝 사례 13 추가), repair 2 뒤 173/173. Reviewer 단계 PASS와 QA 6항목 통과를 따로 확인, 이탈 1회 재검토 뒤 PASS, 이탈 반복 시 `reviewer_self_deviation`과 repair 0회 |
| V3 | 기타 smoke | Discord self-check 92/92, discord-intake 123/123(task 파일 수에 따라 늘어남, 실패 0), audit-chain PASS, studyroom 5/5, Jarvis Console smoke PASS |
| V4 | `git diff --check`, 줄바꿈 | exit 0. `git diff --stat`과 `--ignore-cr-at-eol --stat` 동일. `AGENTS.md` 작업 파일은 CRLF만 |
| V5 | 변경 범위 | 계획 commit의 이 기록 + 7개 파일. `bot_minimal.py`, `evidence_paths`, master-plan 무변경 |
| V6 | 보존 | `jarvis.bat` 미추적, task-0143·task-0146 worktree/branch/candidate |
| V7 | 이 기록의 task 파서 | `valid`, `DOING` |

구현 메모:

- SOP §5의 새 문장은 처음에 "Manager → Director로 escalation한다."로 썼다가, 기존 budget 소진 조항과 같은 조각이 먼저 나와 validator 음성 테스트(`budget_escalation_removed`)의 치환 대상이 바뀌었다. 뜻은 같게 "Manager가 Director에게 escalation한다."로 바꿨다.
- 파이프라인은 `unverified` 항목을 결과(`reviewer_unverified`)에 기록한다. 봇 보고 문구는 이번 범위(`bot_minimal.py` 무변경)가 아니어서 바꾸지 않았다. repair 1 뒤에는 각 항목의 `qa` 짝을 QA 뒤에 확인한다(아래 repair 1).

## repair 1: `unverified`의 QA 짝 규칙

Reviewer FINDINGS(candidate `580aa40e2107dc321e388694b9b5b47a9813c158`)의 major — 파이프라인에서 `unverified`가 실제로 QA로 전달되지 않음 — 뒤 Owner가 처리 규칙 설계를 요청했고, 설계안을 확정했다. 구현: Reviewer 정의 두 파일에 `qa` 짝 규칙, Reviewer 호출에 파이프라인 QA 6개 검사 목록(`QA_CHECKS`), QA 통과 뒤 `qa`가 6개 검사 중 하나가 아닌 항목이 있으면 반영 전에 `qa_unverified_owner_review`로 실패(candidate 보존, main 무변경, FAILED 기록, 새 상태 없음), SOP §10.2 3·9항, validator 조항과 사유 코드, smoke. 봇, 전이 계약, `evidence_paths`는 바꾸지 않았다. 부정확했던 코드 주석("Owner가 보도록 기록")은 실제 동작에 맞게 고쳤다.

처리 규칙 설계 요청 Owner 원문:

```text
Reviewer 결과 확인했습니다.

B안을 그대로 확정하지 말고, `unverified`를 자동으로 무시하거나 무조건 FAILED로 만드는 대신 검증 가능 여부에 따라 처리하는 방안을 먼저 설계해 주세요.

원칙은 다음과 같습니다.

- Reviewer의 `unverified` 자체는 FINDINGS가 아닙니다.
- QA가 자동으로 검증할 수 있는 항목이면 QA가 검증하고 계속 진행합니다.
- QA에서도 검증할 수 없는 항목이면 자동 DONE시키지 않고 Owner 확인 대상으로 남겨야 합니다.
- 따라서 `unverified`가 있다는 이유만으로 항상 실패해서도 안 되고, 항상 무시해서도 안 됩니다.
- 기존 고정 QA 6항목과 어떤 관계로 처리할지 명확히 설계해 주세요.
- 이 구조가 현재 task-0148 범위에 들어갈 정도인지, 아니면 별도 task로 분리하는 게 맞는지도 판단해 주세요.

그리고 현재 candidate에 대해서는 지금 바로 repair하지 말고, 위 처리 규칙을 먼저 확정한 뒤 진행합시다.
```

처리 규칙 설계 보고(대화 기록에서 그대로 옮김):

```text
`unverified` 처리 규칙을 설계했습니다. 파일은 수정하지 않았고 repair도 하지 않았습니다. 핵심은 Reviewer가 확인하지 못한 항목마다 "파이프라인 QA의 어느 검사가 이것을 대신 확인하는지"를 명시적으로 짝지어 적게 하고, 짝이 없는 항목이 하나라도 있으면 자동 DONE을 막는 것입니다.

## 1. 처리 규칙
1. `unverified`는 판정에 쓰지 않습니다(결정 2 그대로).
2. 각 `unverified` 항목은 두 종류 중 하나로 나뉩니다.
   - **QA로 검증 가능:** 파이프라인 고정 QA 6항목 중 하나가 그 항목을 직접 확인합니다.
   - **QA로 검증 불가:** 6항목 중 어느 것도 확인하지 못합니다.
3. 파이프라인은 Reviewer 단계 PASS 뒤 QA 6항목을 그대로 돌립니다.
   - 모든 `unverified` 항목이 검증 가능이고 해당 QA 검사가 통과하면 → 그대로 반영과 자동 DONE으로 진행합니다.
   - 검증 불가 항목이 하나라도 있으면 → QA가 통과해도 **반영 전에 멈춥니다**. main 반영과 자동 DONE은 하지 않고 Owner 확인 대상으로 남깁니다.
   - `unverified`가 없으면 → 지금과 같습니다.
4. 분류가 불확실하면 검증 불가로 봅니다(fail closed). 짝이 적혀 있지 않거나, 목록에 없는 검사 이름이거나, `none`인 경우입니다.

## 2. 고정 QA 6항목과의 관계

| QA 검사 | 대신 확인하는 `unverified` 예 |
| --- | --- |
| `tests_rerun` | "Studyroom smoke test가 통과한다" (Reviewer가 가장 자주 적는 항목) |
| `diff_check` | 공백·줄 끝 오류 없음 |
| `json_valid` | 콘텐츠 JSON이 올바름 |
| `change_set_matches` | 변경 파일이 목록과 같고 허용 경로 안임 |
| `jarvis_bat_absent` | `jarvis.bat`이 candidate에 없음 |
| `head_is_candidate` | worktree HEAD가 검토한 candidate임 |
| 없음 (`none`) | 저장소 밖 자료, 사실 정확성, 사람 판단이 필요한 것 |

QA 6항목 자체는 바꾸지 않습니다. 새 규칙은 "어떤 `unverified`가 이 6개로 확인되는가"만 판정합니다.

## 3. 분류는 누가 하는가

| 안 | 방식 | 평가 |
| --- | --- | --- |
| **L. Reviewer가 짝을 적음 (권장)** | 파이프라인이 Reviewer 호출에 QA 검사 목록과 각 검사의 의미를 넣습니다. Reviewer는 각 `unverified` 항목에 `qa: <검사 이름 또는 none>`을 붙입니다 | 판단 근거가 보고서에 남음. 목록 밖 이름이나 누락은 검증 불가로 처리 |
| K. 파이프라인이 문구로 추측 | "test", "json" 같은 단어로 짝을 추측 | 오분류가 생기면 확인 안 된 항목이 자동 DONE으로 넘어갈 수 있음. 권장하지 않음 |

**L안의 세부**
- Reviewer 정의 두 파일에 한 줄을 추가합니다. `qa` 값은 Manager가 QA 검사 목록을 준 경우에만 적고, 그 검사 하나만으로 그 항목이 확인될 때만 그 이름을 씁니다. 아니면 `none`입니다.
- 수동 경로에서는 Manager가 목록을 주지 않으므로 `qa`가 없어도 됩니다. 수동 QA는 지금처럼 사람이 판단합니다.
- 남는 위험은 Reviewer가 짝을 잘못 적는 경우입니다. 목록 밖 이름과 누락은 검증 불가로 막지만, 틀린 짝 자체는 막지 못합니다. Reviewer 정의에 "그 검사 하나로 확인될 때만"을 명시해 좁힙니다.

## 4. "Owner 확인 대상"으로 남기는 방법
- 현재 전이 계약(6쌍)에는 DOING에서 "보류"로 가는 전이가 없습니다. 그래서 실행 결과를 **FAILED**로 기록하고 사유를 `qa_unverified_owner_review`로 구분합니다. 검증 불가 항목은 사유 상세에 남깁니다.
- candidate, worktree, branch는 보존하고, main에는 반영하지 않습니다.
- **한계:** FAILED는 "목표 달성 실패"라는 뜻이라 "Owner 확인 대기"와 의미가 딱 맞지 않습니다. 새 상태나 새 전이를 만들려면 전이 계약(task-model 5-1)을 바꿔야 하므로 범위 밖으로 둡니다.
- **Owner가 확인한 뒤 이어가는 방법:** 보존된 candidate를 반영하는 명령(예: `/go <id> accept`)이 아직 없습니다. 당분간은 수동 SOP 경로로 처리합니다.

## 5. 범위 판단: 두 task로 나누기를 권장

**task-0148에 넣을 것** (repair 1회, 설계 보완으로 처리)
- 분류 규칙과 멈춤: SOP §10.2 3·9항 문구, `claude_worker.py`
  - Reviewer 호출에 QA 검사 목록 추가
  - `qa` 짝 파싱
  - 검증 불가 항목이 있으면 반영 전에 `qa_unverified_owner_review`로 멈춤
- Reviewer 정의 두 파일에 `qa` 항목 한 줄
- validator: 새 조항과 새 사유 코드의 일치 검사
- smoke 사례:
  - `qa: tests_rerun`만 있으면 진행
  - `none`이 있으면 멈춤
  - 목록 밖 이름이면 멈춤
  - 멈춘 뒤 main이 바뀌지 않았는지
- 이 정도면 결정 2와 명확화 1을 실제로 충족하는 최소 구현이고, 봇과 전이 계약은 건드리지 않습니다.

**별도 task(task-0149 후보)로 나눌 것**
- Owner가 확인한 뒤 보존된 candidate를 반영하는 명령(`/go <id> accept` 등): 봇 명령, 감사, 상태 처리가 필요합니다.
- "Owner 확인 대기"를 FAILED가 아닌 별도 상태로 둘지: 전이 계약 변경이 필요합니다.
- 봇 보고에 `unverified` 항목 표시

**이렇게 나누면**
- task-0148 뒤 task-0146을 다시 돌릴 때 Reviewer가 "테스트 미실행"만 적으면 `tests_rerun`으로 확인되어 성공 경로로 갈 수 있습니다.
- 사실 정확성처럼 QA로 확인할 수 없는 항목이 나오면 자동 DONE하지 않고 멈춥니다.

**확정해 주실 것**
1. 분류 방식: L안(Reviewer가 짝을 적음)
2. 멈춤 기록 방식: FAILED + `qa_unverified_owner_review`, 새 상태는 만들지 않음
3. 범위: 위 내용은 task-0148 repair 1회로 반영하고, 이어가기 명령과 상태 확장은 별도 task로

확정하시면 현재 candidate `580aa40`에 repair 1을 적용한 뒤 fresh Reviewer → QA 순서로 진행합니다.
```

확정 Owner 원문:

```text
세 가지 모두 확정합니다.

1. L안 채택: Reviewer가 각 `unverified`에 `qa`를 명시합니다.
2. 검증 불가 항목은 `FAILED + qa_unverified_owner_review`로 기록하고, 새 상태/전이는 만들지 않습니다.
3. 제안한 task-0148 범위만 구현하고, Owner가 보존 candidate를 이어가는 명령/별도 상태/봇 보고는 별도 task-0149 후보로 분리합니다.

추가 설계안까지 확인했으니 현재 candidate `580aa40`에 repair 1을 적용하세요.

repair 후 fresh Reviewer → QA 순서로 진행하고, 기존 Git 정책대로 테스트 후 checkpoint commit까지 진행하세요.

`evidence_paths`는 이번에도 변경하지 않습니다.
```

## repair 2: 누락·형식 오류 필드의 fail-closed 처리

repair 1 candidate `8ff5d20eec78533e388a3c83a970c3d33e542fae`의 retry 검토가 FINDINGS minor 1건(누락·형식 오류 필드가 "항목 없음"으로 처리돼 fail-closed 원칙을 위반할 수 있음)을 보고했다. repair 예산 1/1을 이미 쓴 뒤라 Owner가 아래와 같이 추가 repair 1회를 승인했다. 이것은 이 task의 예외이며 repair budget을 올리는 일반 규칙이 아니다.

구현: `report_field`가 `[]`는 빈 목록, 필드 누락이나 `- {...}` 목록이 아닌 본문은 `None`(분류 불가)으로 돌려준다. `self_deviations`가 분류 불가이면 검토 무효로 보고 retry 1회, 재검토에서도 무효이면 `reviewer_self_deviation`. `unverified`가 분류 불가이면 짝 없는 항목 하나("unverified field missing or malformed")로 기록해 QA 뒤 `qa_unverified_owner_review`로 멈춘다. SOP §10.2 3·9항에 한 문장씩 추가. smoke 5개 검사 추가(가짜 Reviewer 정상 보고에는 두 필드를 넣음). 그 외 설계와 범위는 바꾸지 않았다.

구현 메모: 판정 줄이 없거나 Reviewer가 비정상 종료한 UNKNOWN 판정은 기존 규칙(FINDINGS가 아닌 판정은 즉시 실패, `reviewer_unknown`)이 먼저 적용되므로 `self_deviations` 무효 retry 대상에서 뺐다. 읽을 수 있는 판정(PASS, FINDINGS, BLOCKED)에만 적용한다.

추가 repair 승인 Owner 원문:

```text
추가 repair 1회를 승인합니다.

이번 지적은 minor 수용하지 않고 수정합니다. 확정한 fail-closed 원칙을 실제 파서가 위반할 수 있는 빈틈이므로 고쳐야 합니다.

다음 조건으로 좁게 수정해 주세요.

- `unverified` / `self_deviations` 필드가 없거나 예상 형식이 아니면 "항목 없음"으로 처리하지 말고 분류 불가로 처리
- `[]`는 정상적인 빈 목록으로 처리
- `unverified`의 분류 불가 항목은 `qa_unverified_owner_review`로 중단
- `self_deviations`의 분류 불가 항목은 검토 무효로 처리하고 retry
- 관련 smoke 사례를 각각 추가
- 그 외 설계와 범위는 변경하지 않음

수정 후 fresh Reviewer → QA → checkpoint 순서로 진행해 주세요.
이번에도 repair 예산과 retry 처리 결과를 정확히 기록해 주세요.
```

## Reviewer 결과 (candidate `9315f472931360181409f9622c7b4c607c89a36c`, repair 2 뒤 fresh)

PASS. findings `[]`, self_deviations `[]`. unverified 7건(V0–V7 재현, task-0143/0146 보존, 이전 검토 결과 기록의 사실 여부)은 아래 QA로 넘겼다.

## QA 결과 (candidate `9315f472931360181409f9622c7b4c607c89a36c`): PASS

| # | 항목 | 결과 |
| --- | --- | --- |
| V0 | 작업 전 확인 | 계획 commit `6a47fdd`는 baseline 대비 이 기록 추가 1건뿐 |
| V1 | validator | PASS, negative_checks=128, negative_failures=0 |
| V2 | Worker smoke | 173/173 |
| V3 | 기타 smoke | Discord self-check 92/92, discord-intake 123/123(실패 0), audit-chain PASS, studyroom 5/5, Jarvis Console smoke PASS |
| V4 | `git diff --check`, 줄바꿈 | baseline..candidate exit 0. `--stat`과 `--ignore-cr-at-eol --stat` 모두 8개 파일 769 추가, 47 삭제로 같음. 8개 파일 index 모두 i/lf, candidate의 `AGENTS.md`에 CR 없음 |
| V5 | 변경 범위 | 8개 파일(설계 B의 7개 + 이 기록). `adapters`, `apps`, master-plan, codex-operating-rules, task-model, 나머지 agent 정의, Skill 변경 0 |
| V6 | 보존 | `jarvis.bat` 미추적·commit 이력 없음. task-0143 worktree/branch 3개(`a02dde9`, r2 `6eec227` 미커밋 `glossary.json` 수정 유지, r3 `e05c69c`), task-0146 worktree/branch `a0079a1`(parent `7cc2b34`) 그대로 |
| V7 | task 파서 | candidate의 이 기록이 `valid`, `DOING` |
| H.5 | 새 Reviewer 정의 실제 출력 | `claude -p --agent reviewer`를 파이프라인 호출 형식으로 1회 실행. `unverified`와 `self_deviations` 필드가 출력됐고, `unverified` 항목마다 `qa: <검사 이름 또는 none>`이 붙었으며 `report_field`가 읽었다. 이 확인용 호출은 범위를 AGENTS.md 하나로 좁혀서 범위 밖 변경을 이유로 FINDINGS가 나왔고, candidate 결함 지적은 아니다 |

Reviewer unverified 중 "이전 검토 결과 기록의 사실 여부"는 이 세션의 Reviewer 보고(저장소 밖)를 근거로 Implementer가 기록한 것이라 QA로 재현할 수 없다.

## 다음 단계

status는 `DOING`으로 둔다. 이 checkpoint commit 뒤 Owner가 Jarvis Console Complete로 DONE을 결정한다. push는 Owner 지시가 있을 때만 한다.

## 후속 task 후보 (task-0149)

- Owner가 `qa_unverified_owner_review`로 멈춘 보존 candidate를 이어가는 명령
- "Owner 확인 대기"를 FAILED가 아닌 별도 상태로 둘지(전이 계약 변경)
- 봇 보고에 `unverified` 항목 표시

## 최종 설계 (대화 보고 원문)

```text
task-0148 설계입니다. 파일은 수정하지 않았습니다. 확정하신 결정 1·2는 SOP와 Reviewer 정의에 규칙으로 넣고, 파이프라인 동작은 필요한 만큼만 바꿉니다.

## A. 제안 task ID와 제목
- **ID:** `task-0148-reviewer-report-fields-and-worker-source-rules`
- **제목:** Reviewer 보고의 확인 불가·자기 이탈 필드 분리, Owner의 조건부 minor 수용 규칙, Worker 사실 출처 규칙

## B. 변경 파일 목록
1. `AGENTS.md`
2. `docs/jarvis-multi-agent-sop-v0.1.md`
3. `.claude/agents/reviewer.md`
4. `.codex/agents/reviewer.toml`
5. `scripts/validate_multi_agent_sop.py`
6. `orchestrator/worker/claude_worker.py`
7. `orchestrator/worker/run_smoke_tests.py`
8. `memory/tasks/task-0148-reviewer-report-fields-and-worker-source-rules.md` (신규)

변경하지 않는 파일: `adapters/discord/bot_minimal.py`, `jarvis-reviewer-call` Skill, `docs/master-plan.md`, `docs/codex-operating-rules.md`, `docs/task-model.md`, 나머지 agent 정의 4개

## C. 파일별 변경 목적

**`AGENTS.md`**
- 조직 흐름의 "Reviewer (finding이면 Repair 후 새 candidate)" 줄 뒤에 "minor finding의 Owner 수용 예외는 SOP §8" 참조를 한 줄 추가합니다.
- 이 참조가 없으면 SOP의 새 규칙이 AGENTS 원칙과 모순돼 보입니다(기준 지도 판정 규칙 2).

**SOP**
- **§5:** retry 정의에 두 경우를 추가합니다. 둘 다 candidate 변경이 없으므로 retry이고 `retry_count`를 씁니다.
  - "Reviewer 자기 명령 이탈로 검토가 무효가 된 경우의 재검토"
  - "Manager 요약·승인 원문 전달 누락(호출 결함)을 고친 같은 candidate의 재검토"
- **§8:** "미결" 문장을 결정 1 규칙으로 바꿉니다.
  - minor만 수용할 수 있고, blocking·major는 수용할 수 없습니다.
  - 지적마다 Owner 수용 원문을 task 기록에 남깁니다.
  - 수용은 그 candidate에만 효력이 있습니다.
  - QA는 그대로 전부 통과해야 합니다.
  - 수동 경로에만 적용되며, 파이프라인에는 적용하지 않습니다.
  - Manager는 수용할 수 없습니다.
- **§10.2:**
  - 3항: `self_deviations`가 있으면 같은 candidate를 Reviewer가 1회 다시 검토합니다(retry). 다시 있으면 `reviewer_self_deviation`으로 실패합니다.
  - 2항: `unverified` 항목은 판정에 쓰지 않고 QA가 넘겨받는다는 내용을 넣습니다.
  - 기존 문장은 유지합니다.

**Reviewer 정의 두 파일** (같은 문구로 함께 수정)
- 출력 양식의 `findings:` 뒤, `note:` 앞에 필드 두 개를 추가합니다.
  - `unverified:` Reviewer 명령으로 확인할 수 없는 Manager 요구와 주장(테스트, worktree, 외부 자료). 없으면 `[]`
  - `self_deviations:` 자기 명령이 허용 형식을 벗어난 경우. 없으면 `[]`
- 현재 findings 안에 들어가던 두 항목을 `unverified`로 옮깁니다. "허용 명령이 없어 충족하지 못한 Manager 요구"와 "검증했다고 오해될 수 있지만 검증하지 않은 것"입니다.
- 현재 규칙 "확인하지 못한 항목·획득 방식의 한계는 minor"를 삭제합니다.
- 명령 이탈은 findings가 아니라 `self_deviations`에 적습니다. "사후 공개는 준수로 보지 않는다"는 기존 문장은 유지합니다.
- "`verdict`는 `findings`로만 결정된다"를 유지하고, 두 새 필드는 판정에 쓰지 않는다고 명시합니다.
- "approved contract"를 "Manager가 scope나 evidence로 준 파일과 Owner 승인 원문"으로 정의합니다.

**validator**
- `REVIEWER_ROLE_CLAUSES`에 새 필드 조항 3~4개를 추가해, 두 정의의 문구 일치를 강제합니다.
- SOP 미결 문장 필수 검사를 "결정 1 조건 문장들 필수" 검사로 바꿉니다.
- `findings_acceptance_rule_contradiction`을 수정합니다. 기존에는 수용 자체를 금지했지만, 이제 "Manager가 finding을 수용", "major·blocking 수용", "파이프라인 자동 수용" 문장을 금지합니다.
- `PIPELINE_REASON_PATTERN`에 `reviewer_self_deviation`을 추가해 SOP와 코드의 일치 검사 대상에 넣습니다.
- 각 검사에 음성 테스트를 추가합니다.

**`claude_worker.py`**
- `worker_prompt`의 사실 출처 규칙을 바꿉니다.
  - "요청이 출처(예: task 기록)를 지정하면 그 출처에 적힌 사실만, 그 출처의 표현으로 쓰고 다른 파일의 세부를 덧붙이지 않는다"
  - "memory/tasks와 설계 문서는 History이므로 '기록에 따르면'으로만 인용하고 현재 규칙이라고 쓰지 않는다"
  - "현재 동작은 코드에서만 가져온다"
- `_split_findings`가 `unverified:`나 `self_deviations:`에서 findings 구간을 끝내도록 고칩니다.
- `self_deviations`가 비어 있지 않으면 같은 호출로 Reviewer를 1회 다시 실행합니다. 결과에 `reviewer_retries`를 추가합니다. 다시 이탈이 있으면 `reviewer_self_deviation`으로 실패하며, repair 예산은 쓰지 않습니다.
- `evidence_paths`와 Reviewer 호출 요약은 변경하지 않습니다(J 참고).

**smoke**
- 가짜 Reviewer 모드를 추가합니다: `unverified`만 있는 PASS, 이탈 1회 뒤 PASS, 이탈이 계속되는 경우, findings와 새 필드가 섞인 보고.
- 검사 내용:
  - `unverified`만 있으면 PASS로 진행
  - 이탈 → 재검토 1회 → PASS
  - 이탈 반복 → `reviewer_self_deviation`, repair 0회
  - 분류 함수가 새 필드를 findings로 읽지 않음
  - Worker 프롬프트에 출처 규칙 문구가 있음
  - task-0146 유형의 기존 FINDINGS 형식(기록 밖 사실)은 여전히 repair 가능으로 분류됨

**task 기록**
- Owner 확정 원문("권장안대로 확정. task-0148 설계 가져와")을 넣고, 그 원문이 가리키는 제 권장안 보고를 대화 기록에서 그대로 옮깁니다.
- 최종 설계 원문, 계획, 검증 결과도 담습니다.
- 계획만 담은 commit을 구현 전에 먼저 남깁니다.

## D. 현재 충돌과 해결 방식

| 충돌 | 해결 |
| --- | --- |
| SOP §8은 "PASS만 QA"와 "미결"인데, 실제로는 Owner가 여러 번 수용함 | 결정 1 조건을 §8 규칙으로 명시하고 미결 문장 삭제 |
| Reviewer 정의상 확인 불가 항목도 finding이라 PASS가 사실상 불가능 | 결정 2의 필드 분리. 판정은 findings로만 결정 |
| Reviewer 명령 이탈과 호출 결함이 repair 횟수를 소모함 | retry로 분류(§5). 파이프라인은 이탈 시 재검토 1회 |
| Worker 프롬프트의 "저장소에서 확인되는 사실"이 요청이 지정한 출처보다 넓음(task-0146 실패 원인) | 출처 한정 규칙 + History 인용 규칙 |
| AGENTS 흐름 줄만 보면 finding은 항상 repair | SOP §8 예외 참조 한 줄 |

## E. 기준 문서로 승격하는 결정
1. **결정 1 (SOP §8):** 수동 경로 한정 Owner minor 수용. 조건은 minor만, 지적별 원문 기록, 해당 candidate 한정, QA 전부 통과, Manager 수용 불가이고, 파이프라인에는 적용하지 않습니다.
2. **결정 2 (Reviewer 정의 두 파일 + SOP §5·§10.2):** `unverified`, `self_deviations` 필드와 판정 규칙, 이탈과 호출 결함의 retry 분류
3. **승격하지 않는 것**
   - 파이프라인 수용 명령(`/go <id> accept`): 권장안대로 별도 task로 미룹니다.
   - `evidence_paths` 확장: J 참고
   - 이번 task 기록의 개별 수용 사례들

## F. validator 변경 내용
task-0147 구조를 그대로 씁니다.
1. `REVIEWER_ROLE_CLAUSES`에 새 필드 조항을 추가합니다. 두 정의에서 한 줄씩 존재해야 하고, 음성 테스트는 기존 루프로 자동 생성됩니다.
2. SOP 결정 1 필수 조항을 검사합니다. 기존 `SOP_PENDING_CLAUSE` 검사를 이것으로 바꿉니다.
3. `CONTRADICTIONS`의 수용 관련 패턴을 교체합니다(Manager 수용, major·blocking 수용, 파이프라인 자동 수용).
4. `PIPELINE_REASON_PATTERN`에 `reviewer_self_deviation`을 추가합니다. SOP §10.2와 코드 양쪽에 있어야 합니다.
5. 음성 테스트를 새 조항과 패턴마다 추가합니다.

## G. 제외 범위
- 파이프라인 FINDINGS 수용 명령, `bot_minimal.py` 변경, `evidence_paths` 변경
- audit `/go` 문제, task-0142 DONE, task-0143 정리, task-0146 재실행, 봇 재시작, push
- master-plan, codex-operating-rules, task-model, 나머지 agent 정의, Skill
- 새 DECISIONS/ADR 문서

## H. 검증 계획
1. **작업 전:** tracked 변경이 없는지 확인하고, 대상 파일의 EOL과 worktree/branch 목록을 기록합니다.
2. **편집 방식:** 정확한 문자열 치환만 씁니다. 줄바꿈만 바뀐 줄이 없는지 두 diff stat으로 확인합니다.
3. **테스트**
   - validator PASS, 음성 테스트 실패 0
   - Worker smoke: 기존 132개 + 새 사례
   - Discord 92/92, intake, audit, studyroom, Console smoke
   - `git diff --check`
4. **보존:** `jarvis.bat` 미추적, task-0143·0146 worktree/branch/candidate가 그대로인지 확인합니다.
5. **Reviewer 정의 적용 시점:** 이 세션의 Reviewer subagent는 세션 시작 때 읽은 **기존** 정의를 씁니다. 새 정의는 검토 대상 자체이므로 기존 정의로 검토하는 것이 맞다고 봅니다. 새 정의로 실제 출력이 나오는지는 QA에서 `claude -p --agent reviewer`를 한 번 실행해 새 필드가 나오는지로 확인합니다. 이 호출은 파이프라인과 같은 로컬 Claude 호출이며 외부 API를 새로 쓰지 않습니다.
6. **순서:** 계획 commit → 구현 → fresh Reviewer → (repair 예산 1) → QA → checkpoint → Console Complete

## I. Reviewer가 검증할 핵심 계약
- 결정 1 조건이 SOP §8에 빠짐없이 들어갔는지. 특히 minor만, 원문 기록, candidate 한정, QA 필수, Manager 수용 불가, 파이프라인 미적용.
- 결정 2의 두 필드가 두 Reviewer 정의에 같은 문구로 있고 판정에 쓰이지 않는지
- 이탈과 호출 결함이 retry로 분류되고 repair 예산을 쓰지 않는지(SOP §5, 코드)
- `worker_prompt` 출처 규칙이 설계대로인지
- `_split_findings`와 재검토 동작이 smoke로 검증되는지
- validator의 새 조항과 음성 테스트가 실제로 실패를 잡는지
- 변경 파일이 8개를 벗어나지 않는지, `jarvis.bat`·master-plan·bot이 변경 집합에 없는지

## J. 이후 task로 남기는 것
- **파이프라인 FINDINGS 수용 명령:** 필요해질 때 Owner 결정 후 진행합니다.
- **`evidence_paths` 확장 (Owner 결정 필요):**
  - 권장은 이번에는 바꾸지 않는 것입니다. 새 Worker 출처 규칙으로 Worker가 요청이 지정한 기록만 쓰게 되므로, Reviewer도 그 기록만 보면 충분합니다.
  - task-0146 재실행 결과를 보고 다시 판단합니다.
- audit `/go` 거부 문제, task-0143 정리

## K. task-0146을 재실행할 수 있는 정확한 조건
1. task-0148이 Reviewer → QA → checkpoint → Console Complete로 DONE이 되어야 합니다.
2. 봇을 그 main HEAD로 재시작하고, 새 `worker_prompt`와 재검토 동작이 로드됐는지 확인해야 합니다.
3. main에 tracked 변경이 없어야 합니다. task-0146이 FAILED 상태여야 하고, 첫 시도(`7cc2b34`, `a0079a1`)와 worktree가 보존돼 있어야 합니다.
4. Owner가 Discord에서 `/go task-0146-studyroom-glossary-fast-forward-merge-1-jarvis-example-task-0142`를 직접 보내야 합니다. resume이 아니라 처음부터 재시도해야 새 프롬프트가 쓰입니다.
5. 성공 판정은 task-0142 원래 조건(QA PASS → ff-only 반영 → DONE → checkpoint → Discord 성공 보고)으로 하고, 결과를 task-0142 기록에 추가합니다.

설계를 승인하시면 계획 commit부터 진행합니다. `evidence_paths`는 권장대로 변경하지 않는 것으로 진행해도 될지 함께 알려 주세요.
```

## Repair 이력

retry_budget=1, retry_count=1, repair_budget=1, repair_count=2 (1/1 소진 뒤 Owner가 추가 repair 1회를 별도 승인한 예외, 일반 규칙 아님)

| # | 원인 | 조치 |
| --- | --- | --- |
| 1 | Reviewer FINDINGS (candidate `580aa40e2107dc321e388694b9b5b47a9813c158`): major 1 — 파이프라인에서 `unverified`가 QA로 전달되지 않고 코드 주석이 부정확함. minor 2 — V0–V7은 QA 재현 대상, Reviewer 자신의 명령 형식 이탈 3건(이 세션 Reviewer는 기존 정의로 실행) | Owner 확정 설계대로 `qa` 짝 규칙과 `qa_unverified_owner_review` 멈춤 구현, 주석 정정. V0–V7은 QA에서 재현. 명령 형식 이탈은 새 candidate의 fresh Reviewer로 해소. 새 candidate에 fresh Reviewer → QA |
| retry 1 | candidate `8ff5d20eec78533e388a3c83a970c3d33e542fae`의 fresh 검토가 PASS였지만 `self_deviations` 2건(부모 해시를 직접 쓴 `git diff --stat`, 출력이 너무 커서 다 읽지 못한 `git show`) | 이 candidate의 SOP §5 규칙대로 검토 무효, 같은 candidate로 retry 1회(repair 예산 미사용). retry 검토는 `self_deviations: []` |
| 2 | retry 검토 FINDINGS (candidate `8ff5d20eec78533e388a3c83a970c3d33e542fae`): minor 1 — 누락·형식 오류 필드가 "항목 없음"으로 처리됨 | Owner의 추가 repair 승인(예외)에 따라 fail-closed 파싱으로 수정. 새 candidate에 fresh Reviewer → QA |
