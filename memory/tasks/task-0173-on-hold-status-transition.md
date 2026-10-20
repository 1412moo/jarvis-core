# task-0173-on-hold-status-transition

- id: `task-0173-on-hold-status-transition`
- title: `ON_HOLD 상태 전이 추가: Console Hold/Resume, hold_from 복귀, On hold 그룹, task-model 5-1·§9 (A2)`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-20 10:02 UTC`
- updated_at: `2026-10-20 11:19 UTC`
- summary: `Console Hold가 TODO·NEEDS_APPROVAL을 ON_HOLD로 옮기며 보류 전 상태를 hold_from에 함께 기록하고, Resume은 hold_from 상태로만 되돌린다(hold_from이 없거나 틀리면 거절). DOING은 보류하지 않으며, Task View에 TODO 뒤·DONE 앞의 On hold 그룹을 두고 task-model 5-1·§9와 master-plan D1 문구 두 군데를 고친다. Console Start 뒤 writer·Console·task-model·master-plan·README와 smoke를 구현했고 Implementer 검증을 마쳤으며, 사전 점검·self-review·Reviewer·QA 전이다. 기존 6건·감사 체인·Discord 코드는 바꾸지 않았고 push는 하지 않는다.`
- source_command: `Owner 요청: A2 ON_HOLD 전이 검토, 작업 기록과 work package 제안까지 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `3bc3fe59afe338d36d50e3da54aaabf69e6537d2` (등록 시점 main HEAD = origin/main). Start 때 다시 확인한다 |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 등록 방식 | 이 기록을 `TODO`로 작업 트리에만 만들었다(커밋·stage 없음). task-0162·0172와 같이 Start 승인 뒤 candidate commit에 함께 들어간다 |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (기본값, O9) |

## Owner 요청 1 (원문)

```text
Jarvis-Core 다음 작업으로 A2, `ON_HOLD` 상태 전이 추가(task-model 5-1)를 검토한다.
이번 단계는 작업 기록 및 work package 제안 작성까지만 진행한다. 구현 착수 승인은 아직 없다.
1. 시작 전 확인

* 실제 작업 경로 `C:\project\work\jarvis-core`에서 진행한다.
* 최신 `master-plan`, task-model 5-1 관련 문서, task-0156, task-0162, task-0172 및 관련 SOP를 먼저 읽는다.
* 기존 task 기록과 문서의 실제 근거를 확인한다. 기억이나 추측만으로 결론 내리지 않는다.
* 현재 Git 상태와 HEAD를 확인하되, 파일은 수정하지 않는다.

2. 작성할 내용
A2의 새 task 기록 초안과 work package 제안을 작성한다. 다음 항목을 포함한다.

1. 현재 문제와 근거: 보류 결정된 Team Manager task 0030·0031·0032·0033·0034·0036의 현재 상태, Task View에 미치는 영향
2. 작업 범위와 명시적 제외 범위
3. `ON_HOLD` 상태의 의미와 허용 상태 전이
4. 보류 해제 후 재개 규칙 및 Owner 승인 필요 여부
5. task parser, Console 표시, 검증기, 테스트와 문서에 미치는 영향
6. 기존 상태 및 이전 task와의 호환성
7. Reviewer·QA·repair budget·Console Complete 등 기존 SOP 준수 방안
8. 검증 계획과 완료 조건
9. 예상 변경 파일, 위험 요소, 작업량 및 구현 전 Owner가 결정해야 할 사항

특히 다음 두 가지는 구분해서 제안한다.

* `ON_HOLD` 상태와 상태 전이 기능을 구현하는 일
* 기존 6개 task의 상태를 실제로 변경하는 일

기존 6개 task의 상태 변경은 이번 구현 범위에 자동으로 포함하지 않는다. 필요하다면 별도의 Owner 결정 항목으로 제시한다. 상태 전이 규칙이나 재개 시 승인 정책이 문서에서 명확하지 않다면 임의로 정하지 말고 선택지를 제시한다.
3. 작업 제한

* 이번 단계에서 구현 코드를 수정하지 않는다.
* 기존 task 6개의 상태를 변경하지 않는다.
* 공식 Console Start 승인 없이 구현을 시작하지 않는다.
* 커밋, push, 기존 worktree·smoke 폴더 정리 작업을 하지 않는다.
* `jarvis.bat`은 읽기·수정·stage·삭제하지 않는다.
* task-0172에서 만든 self-review 기능은 새 제안의 검토 계획에 반영하되, 기존 Reviewer·QA 절차를 대체하지 않는다.
* 스케줄러, 백그라운드 실행, 외부 API/LLM 연동 등 별도 승인이 필요한 범위를 끌어들이지 않는다.

4. 완료 보고
작업 기록 초안과 work package 제안을 준비한 뒤 다음을 보고한다.

* 확인한 문서와 실제 근거
* 제안한 작업 범위 및 상태 전이 규칙
* Owner 결정이 필요한 사항
* 작성하거나 수정한 파일과 Git 상태
* 구현을 시작하지 않았다는 확인

문서 작성에 필요한 기존 task 기록이 이미 존재한다면 새 기록을 중복 생성하지 말고, 저장소의 기존 task 등록 규칙을 따른다. 작업 기록이나 제안 문서를 실제로 수정해야 한다면 변경 전 대상 파일과 변경 목적을 먼저 확인하고, 이번 단계의 범위를 벗어나는 변경은 하지 않는다.
최종적으로 Owner가 제안을 검토하고 공식 착수를 승인할 때까지 대기한다.
```

중복 확인: `memory/tasks`에 task-0173 파일, `0173` branch·worktree가 없었다. A2를 다루는 기존 기록은 task-0162(제외·보류로만 언급)와 task-0156(전이 부재 기록)뿐이라 새 기록을 만들었다.

## Owner 결정 2 (원문)

```text
task-0173 `ON_HOLD` 상태 전이 작업의 제안서를 다음 Owner 결정에 맞게 정리해 주세요.
1. Owner 결정

* O1 보류 진입: `TODO`, `DOING`, `NEEDS_APPROVAL` → `ON_HOLD` 허용
* O2 보류 해제: `ON_HOLD` → `TODO`만 허용
* O3 적용 경로: Console의 Hold/Resume + Preview/Confirm을 사용한다. 기존 D1 규칙과 충돌하지 않도록 필요한 최소 범위의 개정안을 명시한다.
* O4 Task View: `On hold`를 별도 그룹으로 두고 `TODO` 뒤, `DONE` 앞에 배치한다. 기존 상태의 정렬 및 표시 계약에 미치는 영향을 확인한다.
* O5 보류 사유: task-model §9에 기록 규칙을 추가한다.
* O6 감사 체인: 이번 작업에서는 변경하지 않는다.
* O7 Discord `/report` 집계: 이번 작업에서 제외한다.
* O8 기존 6건 상태 변경: 이번 작업에서 제외한다. 기능 완료 후 별도 Owner 결정으로 둔다.
* O9 Reviewer repair budget: 기본값을 유지한다(retry 1, repair 1).

2. 구현 전 필수 확인
기존 task-0173 초안과 관련 문서를 다시 확인하고, 특히 다음 사항을 구체화한다.

1. D1의 기존 규칙과 Console Hold/Resume 기능이 정확히 어디에서 충돌하는지
2. D1을 어떻게 최소한으로 개정할지와 그로 인해 허용되는 동작의 경계
3. `NEEDS_APPROVAL`에서 `ON_HOLD`로 이동할 때 기존 Owner 승인 의미가 보존되는지
4. `ON_HOLD`에서 `TODO`로 복귀할 때 기존 승인·실행 흐름을 우회하지 않는지
5. `On hold` 그룹의 정렬 순위와 Console parser, writer parser, validator, smoke test 사이의 일관성
6. 보류 사유를 어디에 기록하고 어떤 입력 검증을 적용할지
7. 기존 task 기록 및 이전 상태 데이터와의 호환성

문서에 근거가 없거나 정책 충돌을 확실하게 해결할 수 없는 부분은 임의로 결정하지 말고, 구체적인 선택지를 제시한다.
3. 이번 단계의 작업 제한

* task-0173 제안서와 task 기록을 정리하는 단계까지만 진행한다.
* 구현 코드 및 테스트 코드를 수정하지 않는다.
* 기존 6개 task의 상태를 변경하지 않는다.
* 공식 Console Start 승인 없이 구현을 시작하지 않는다.
* 커밋, stage, push를 하지 않는다.
* `jarvis.bat`은 읽기·수정·stage·삭제하지 않는다.
* 기존 worktree와 smoke 임시 폴더를 건드리거나 정리하지 않는다.
* Team Manager 재개, 자동 보류·해제, 감사 체인, Discord `/report`, master-plan 변경은 범위에 추가하지 않는다.

4. 완료 보고
수정한 task-0173 기록과 제안서를 기준으로 다음을 보고한다.

* O1~O9 결정 반영 여부
* D1 개정안의 정확한 내용과 근거
* 최종 구현 범위 및 제외 범위
* 예상 변경 파일과 검증 계획
* 남아 있는 Owner 결정 사항
* Git 상태 및 실제 수정 파일

모든 결정이 기존 정책과 일관되게 정리되면 Console Start 승인을 받을 준비가 된 상태로 보고하고 대기한다. 승인 전에는 구현하지 않는다.
```


## Owner 결정 3 (원문)

```text
task-0173의 C1~C4에 대해 다음과 같이 진행해 주세요. 이번 단계도 정책과 제안서 정리만이며, 구현과 Console Start는 아직 승인하지 않습니다.

* C1 수용: master-plan의 D1 관련 문구만 최소 수정 범위에 포함하는 안으로 정리합니다. 다른 master-plan 항목은 수정하지 않습니다.
* C2 재검토: `NEEDS_APPROVAL → ON_HOLD → TODO → DOING` 경로가 기존 Owner 승인 절차를 우회할 수 있는지 실제 전이 규칙과 코드로 확인합니다. Resume 경고만으로 충분하다고 가정하지 마세요. 원래 승인 대기였던 작업이 승인 없이 실행될 수 없도록 하는 최소 변경안을 제시하세요. 원래 `NEEDS_APPROVAL` 상태로 복귀하는 방법을 포함해 선택지를 비교하되, 정책을 임의로 확정하지 마세요.
* C3 재검토: Console이 Worker 실행 여부를 확인할 수 없다는 점을 고려해, `/task`로 생성된 `DOING` 작업의 Hold를 실제로 안전하게 거절할 수 있는지 확인합니다. 확인할 수 없다면 안전하다고 가정하지 말고, 실행 중 작업 보호를 보장할 수 있는 최소 대안을 제시하세요.
* C4 수용: 보류 사유는 기존 summary에 미리 기록하고, Hold Preview에서 사유 누락을 명확하게 안내하는 안으로 정리합니다. 입력 UI를 추가하지 않습니다.

수정된 task-0173 기록에 다음을 명시하세요.

1. 각 결정의 근거와 관련 코드·문서
2. 최종 상태 전이표와 승인 보존 방식
3. Worker 실행 중 작업에 대한 안전한 처리 방식
4. master-plan의 D1 변경 범위
5. 검증 계획과 예상 변경 파일
6. 여전히 Owner 결정이 필요한 사항

제한:

* 구현 코드와 테스트 코드는 수정하지 않습니다.
* 기존 6개 task의 상태를 변경하지 않습니다.
* Console Start, stage, commit, push를 하지 않습니다.
* `jarvis.bat`, 기존 worktree, smoke 임시 폴더를 건드리지 않습니다.

제안서가 정책적으로 일관되고 남은 결정 사항이 명확해지면 보고하고 대기하세요. 구현은 별도 Owner 승인 후 시작합니다.
```

## Owner 결정 4 (원문)

```text
task-0173의 남은 Owner 결정 E1~E3을 다음과 같이 확정합니다.

* E1: E1-a 수용. Hold 시 `hold_from`에 보류 전 상태를 기록하고, Resume은 해당 상태로 복귀시킵니다.
* E2: E2-a 수용. `DOING → ON_HOLD` 전이는 허용하지 않습니다. 실행 중 작업은 이번 기능으로 보류하지 않습니다. task-0031을 비롯한 기존 task의 상태는 변경하지 않습니다.
* E3: 수용. `hold_from`이 없거나 허용되지 않는 값이면 Resume을 거절합니다(fail closed).

이 결정을 task-0173 기록에 반영하고, 구현 착수 전 최종 제안서를 정리해 주세요.
구현 전 확인할 사항

1. `hold_from`의 허용값이 `TODO`, `NEEDS_APPROVAL`로 제한되는지 확인합니다.
2. Hold에서 상태와 `hold_from`이 일관되게 저장되는지, 실패 시 부분 변경이 남지 않는지 확인합니다.
3. Resume은 `hold_from` 값과 현재 상태를 검증한 뒤 원래 상태로 복귀시키고, 복원 후 메타데이터를 어떻게 처리할지 명확히 합니다.
4. `NEEDS_APPROVAL`에서 보류된 작업이 Resume 후에도 `/approve`와 기존 승인 감사 절차를 거치지 않고 실행될 수 없는지 검증합니다.
5. `DOING` 작업을 Hold할 수 없다는 규칙이 서버 측에서도 강제되는지 확인합니다.
6. 기존 6건은 변경하지 않고 blob 불변 검사를 유지합니다.
7. master-plan의 D1 개정은 승인된 최소 범위만 반영하고, task-model·writer·Console의 전이 규칙이 서로 일치하는지 검증합니다.
8. 기존 SOP의 self-review, Reviewer, QA, repair budget 및 Console Complete 절차를 그대로 따릅니다.

작업 제한

* 이번에는 task-0173 기록과 제안서만 정리합니다.
* 구현 코드와 테스트 코드를 수정하지 않습니다.
* Console Start, stage, commit, push를 하지 않습니다.
* `jarvis.bat`, 기존 worktree, smoke 임시 폴더를 건드리지 않습니다.
* 기존 6개 task의 상태를 변경하지 않습니다.

최종 제안서에 남은 정책 충돌이 없으면 변경 파일, 검증 계획, 완료 조건을 보고하고 대기하세요. 구현은 별도 Console Start 승인 이후에만 시작합니다.
```

## 확정된 결정

| # | 확정 내용 | 출처 | 근거 |
| --- | --- | --- | --- |
| O1 + E2 | 보류 진입은 `TODO → ON_HOLD`, `NEEDS_APPROVAL → ON_HOLD`뿐. `DOING → ON_HOLD`는 허용하지 않는다 | 결정 2(O1), 결정 4(E2-a) | 실행은 DOING에서만 진행되고 Console은 실행 여부를 확인할 수 없다(F8~F12) |
| O2 + E1 | 해제는 `hold_from` 상태로만: `ON_HOLD → TODO`(`hold_from` TODO), `ON_HOLD → NEEDS_APPROVAL`(`hold_from` NEEDS_APPROVAL) | 결정 2(O2), 결정 4(E1-a) | TODO로만 해제하면 승인 대기 task가 `/approve` 없이 실행된다(아래 "승인 보존") |
| E3 | `hold_from`이 없거나 허용값이 아니면 Resume 거절(fail closed) | 결정 4 | 추측으로 상태를 정하지 않는다 |
| O3 | Console Hold/Resume + Preview/Confirm, D1 최소 개정 | 결정 2 | 기존 Start/Complete 경계 재사용 |
| O4 | On hold 그룹, TODO 뒤·DONE 앞(rank 55) | 결정 2 | 보류 task가 진행 task 칸을 차지하지 않게 한다 |
| O5 + C4 | task-model §9 보류 사유 규칙. 사유는 Hold 전에 summary에 기록, 입력 UI 없음, Hold Preview 안내 | 결정 2, 결정 3 | writer는 summary를 바꾸지 않는다(F14) |
| O6 | 감사 체인 무변경. Hold/Resume은 task-0044 §3.1의 G | 결정 2 | 승인성 전이 A는 `/approve`로 한정(F13) |
| O7 | Discord `/report` 제외 | 결정 2 | — |
| O8 + E2 | 기존 6건과 task-0031 포함 기존 task 상태 무변경, 패키지 B는 별도 결정 | 결정 2, 결정 4 | — |
| O9 | budget 기본값(retry 1, repair 1) | 결정 2 | — |
| C1 | master-plan은 D1 관련 문구 두 군데만 | 결정 3 | AGENTS.md 판정 규칙 5(기준 문서와 코드 drift 금지) |

남은 정책 충돌은 없다. 아래 "구현 단계에서 정할 세부"는 정책이 아니라 문구·이름 수준이며, Start 승인 때 Owner가 바꿀 수 있다.

### C2·C3 확인 근거와 비교한 선택지 (결정 3 → 결정 4)

C2(승인 우회): O2(`ON_HOLD → TODO`만)대로면 승인 대기였던 task가 `NEEDS_APPROVAL → ON_HOLD → TODO` 뒤 Console Start로 DOING이 되고, `/run`(DOING이면 출처와 관계없이 실행, F10)이나 `/retry`(`/task` 출처가 아니면 DOING 실행, F10)로 `/approve`와 `owner_approval` 감사 없이 실행에 이른다. `/go`는 TODO를 받지만 `owner_approval`로 기록한다(F10). 비교한 선택지:

| 안 | 내용 | 결과 |
| --- | --- | --- |
| E1-a | Hold가 `hold_from`을 기록하고 Resume은 그 상태로만 복귀 | **채택**(결정 4). 승인 대기 task는 NEEDS_APPROVAL로 돌아가 `/approve`만 실행으로 이어진다. 선택 메타데이터 1개 추가 |
| E1-b | 해제는 항상 NEEDS_APPROVAL | 원래 TODO였던 task도 `/approve`를 거쳐야 하고 `/approve`가 실행 흐름을 돌려(F9) 원치 않는 실행이 생길 수 있음 |
| E1-c | NEEDS_APPROVAL 보류 제외 | 가장 작지만 6건 중 5건을 보류할 수 없음 |
| E1-d | O2 유지 + Resume 경고 | 우회를 막지 못해 제외 |

C3(실행 중 작업): `/go`는 출처와 관계없이 TODO에서 Worker를 실행하므로(F11) `/task` 출처 검사로는 Worker 실행 task를 가릴 수 없고, `/run`·`/retry`는 잠금도 표지도 없이 실행한다(F10). Worker 잠금 탐침은 잠금을 잠깐 잡아 `/go`를 방해할 수 있다(F11). 실행 중에 상태가 바뀌면 결과 기록이 실패한다(F12). 비교한 선택지:

| 안 | 내용 | 결과 |
| --- | --- | --- |
| E2-a | `DOING → ON_HOLD` 제외 | **채택**(결정 4). 실행이 진행될 수 있는 유일한 상태를 빼서 보장 |
| E2-b | 실행 경로 공통 잠금과 Console 확인 | Discord·Worker 코드 변경이 필요해 범위 밖 |
| E2-c | `/task` 출처 DOING만 거절 | 위 이유로 불충분 |
| E2-d | Worker 잠금·표지 탐침 | `/run`·`/retry`를 못 보고 `/go`를 방해할 수 있어 불충분 |

## 근거 (read-only 조사)

### 대상 6건 (변경하지 않음)

| task | status | updated_at | blob |
| --- | --- | --- | --- |
| `task-0030-codex-chatgpt-team-manager-discord` | `NEEDS_APPROVAL` | 2026-08-26 11:08 UTC | `5bae2580d369` |
| `task-0031-chatgpt-discord-claude-auto-collab-plan` | `DOING` | 2026-08-26 11:29 UTC | `5d7dbb80335c` |
| `task-0032-chatgpt-team-manager-integration-research` | `NEEDS_APPROVAL` | 2026-08-26 11:32 UTC | `ede13b3278fe` |
| `task-0033-local-llm-team-manager` | `NEEDS_APPROVAL` | 2026-08-26 11:42 UTC | `999c8e29a6b3` |
| `task-0034-local-team-manager-approval-boundary` | `NEEDS_APPROVAL` | 2026-08-26 11:46 UTC | `d22b5656479e` |
| `task-0036-cloud-llm-candidates` | `NEEDS_APPROVAL` | 2026-08-26 12:26 UTC | `d11c6ce0bd55` |

참고: `task-0035-local-team-manager-model-benchmark` `DONE`, blob `d494ed175848`(task-0156 QA). baseline `3bc3fe5`에서 확인했다. 기록 124건(template 제외, 이 기록 등록 전) 중 `ON_HOLD` 0건, `hold_from` 줄 0건이다.

### 코드·문서상 사실

| # | 사실 | 근거 |
| --- | --- | --- |
| F1 | `ON_HOLD`는 이미 7번째 공식 status다. 전이만 없다 | `docs/task-model.md:20,30`, `orchestrator/discord-intake/task_file_writer.py:87`, task-0041 결정 ②, task-0098 |
| F2 | writer 전이 표는 6쌍이고 표 밖의 전이는 `invalid_task_transition`으로 거절된다 | `task_file_writer.py:39-56,692,871` |
| F3 | validator는 task-model 5-1과 writer 표가 같은지, 5-2의 `` `X` → `Y` ``가 5-1 안에 있는지, 5-1에 명령 이름이 없는지 검사한다 | `scripts/validate_multi_agent_sop.py:1036-1063` |
| F4 | Console smoke가 공식 전이 집합·개수(6)·7×7 거절 행렬을 고정한다 | `apps/jarvis-console/run_smoke_tests.py:2161-2200` |
| F5 | Console 동작 표는 동작당 (출발, 도착, 확인 문구) 한 쌍이고, Preview는 요청에서 `task_id`와 `action`만 받으며 snapshot status가 출발 상태와 다르면 `task_status_transition_not_allowed`로 거절한다 | `run_web_app.py:315-318,2715-2768` |
| F6 | 메타데이터 허용 목록은 writer `TASK_ALLOWED_METADATA`와 Console `TASK_VIEW_ALLOWED_FIELDS` 두 곳뿐이고 smoke가 둘이 같은지 검사한다. 저장소에 다른 허용 목록은 없다 | `task_file_writer.py:57-86`, `run_web_app.py:174-214`, `run_smoke_tests.py:3608` |
| F7 | writer의 원자적 교체 helper는 바뀐 파일 전체를 임시 파일에 쓰고 flush·fsync·짧은 쓰기 확인 뒤 최종 digest를 다시 확인하고 한 번의 replace로 바꾼다. 실패하면 임시 파일을 지우고 원본은 그대로다 | `task_file_writer.py:565-672` |
| F8 | Discord `_read_task_metadata`는 필수 필드만 읽고 모르는 메타데이터 줄은 무시한다. Discord 전이는 writer parser를 쓴다 | `adapters/discord/bot_minimal.py:623-639` |
| F9 | `/approve <id> approve`는 `NEEDS_APPROVAL → DOING`, `owner_approval` 감사, 실행 흐름 순서다. reject는 `→ FAILED`이고 실행하지 않는다 | `bot_minimal.py:1689-1830` |
| F10 | `/run`은 `DOING`만, `/retry`는 `FAILED`·`DOING`만(`/task` 출처 제외), `/go`는 `TODO`·`FAILED`만(DOING은 상태 안내) 받는다. `/run`·`/retry`는 잠금 없이 실행한다 | `bot_minimal.py:102-103,1375-1497,1934-2044` |
| F11 | `/go`는 출처와 관계없이 TODO에서 Worker를 실행한다. Worker 프로세스 잠금 탐침은 잠금을 잠깐 잡는다 | `bot_minimal.py:1906-1960`, `orchestrator/worker/claude_worker.py:125-181` |
| F12 | 실행 결과는 끝날 때 DOING에서 DONE/FAILED로 digest·상태를 확인하며 기록된다. 그 사이 상태가 바뀌면 기록이 실패한다 | task-model 5-2, `record_task_execution_result` |
| F13 | 감사 kind는 `owner_approval`·`execution_result` 둘이고 A는 "`/approve`로 인한 상태 전이"다. Console 전이는 G다 | `orchestrator/audit-chain/audit_entry.py:34-37`, `docs/task-0044-audit-hash-chain-design.md` §3.1·§3.3 |
| F14 | task-model §9는 BLOCKED·NEEDS_APPROVAL의 summary 기재만 정하고, writer 전이는 summary를 바꾸지 않는다 | `docs/task-model.md:112-114` |
| F15 | 화면 그룹 목록이 `web/app.js:1324-1330`에 서버와 별도로 복사돼 있다 | `web/app.js:1320-1330` |
| F16 | smoke가 고정하는 표시 계약: 상태 규칙 표, 동작·읽기 전용 badge 분할, 7개 상태 혼합 순서, 표시 순서 문구, 상태 어휘 == 상태 규칙 키 | `run_smoke_tests.py:4522-4560,5310-5325,6885-6900,5230,3611` |
| F17 | Discord `/report`·`/retro`는 ON_HOLD를 상태별 count에 넣지 않는다(O7 제외, 후속 후보) | `bot_minimal.py:104,670-673,741` |
| F18 | task-model 5 기본 흐름의 BLOCKED 흐름은 5-1에 전이가 없다(기존 drift 후보, 범위 밖) | `docs/task-model.md:48-50` |

## 최종 상태 전이표

| from | to | 경로 | 조건 |
| --- | --- | --- | --- |
| `TODO` | `DOING` | Console Start, Discord `/go`, 재시도 경로 | 기존 |
| `DOING` | `DONE` | Console Complete, 실행 결과 기록 | 기존 |
| `DOING` | `FAILED` | 실행 결과 기록, `/go … recover` | 기존 |
| `FAILED` | `TODO` | `/go` 재시도·resume·accept, `/retry` | 기존 |
| `NEEDS_APPROVAL` | `DOING` | Discord `/approve … approve` | 기존, 승인 감사 |
| `NEEDS_APPROVAL` | `FAILED` | Discord `/approve … reject` | 기존, 승인 감사 |
| `TODO` | `ON_HOLD` | **Console Hold** | `hold_from: TODO`를 함께 기록 |
| `NEEDS_APPROVAL` | `ON_HOLD` | **Console Hold** | `hold_from: NEEDS_APPROVAL`을 함께 기록 |
| `ON_HOLD` | `TODO` | **Console Resume** | `hold_from`이 `TODO`일 때만, `hold_from` 삭제 |
| `ON_HOLD` | `NEEDS_APPROVAL` | **Console Resume** | `hold_from`이 `NEEDS_APPROVAL`일 때만, `hold_from` 삭제 |

- task-model 5-1과 writer 표는 이 10쌍이다. `DOING → ON_HOLD`, `BLOCKED`·`FAILED`·`DONE → ON_HOLD`, `ON_HOLD → DOING` 등 나머지 쌍은 없다.
- 조건(`hold_from`)은 5-2 경로 표에 쓴다. 5-1에는 명령 이름을 쓰지 않는다(F3).

## `hold_from` 규칙 (확인 항목 1·2·3)

### 형식과 검증

| 항목 | 규칙 |
| --- | --- |
| 줄 형식 | ``- hold_from: `TODO` `` 또는 ``- hold_from: `NEEDS_APPROVAL` `` |
| 허용값 | 정확히 `TODO`, `NEEDS_APPROVAL` 두 개. 그 밖의 값(빈 값, 소문자, `DOING` 등)은 canonical 검증 실패 |
| 존재 조건 | status가 `ON_HOLD`이면 정확히 한 줄 있어야 하고, 다른 status에서는 없어야 한다. 위반하면 writer parser는 `task_file_invalid_hold_from_metadata`(이름은 구현 때 확정)로, Console parser는 invalid(metadata review)로 읽는다 |
| 위치 | 메타데이터 머리 블록 안, `status` 줄 바로 뒤(구현에서 확정, 아래 "설계와의 차이" D1. 제안 단계에서는 `summary` 줄 뒤로 적었다). parser는 위치를 검사하지 않는다 |
| 허용 목록 | writer `TASK_ALLOWED_METADATA`와 Console `TASK_VIEW_ALLOWED_FIELDS`에 함께 추가(smoke 동일성 검사 유지, F6) |
| 쓰는 주체 | Console Hold·Resume Confirm뿐. 다른 쓰기 경로는 이 줄을 만들거나 지우지 않는다 |
| 표시 | Task View 항목과 Resume Preview에 "Held from" 값 |

### Hold의 저장 일관성

새 writer 함수(예: `hold_task_file`, 이름은 구현 때 확정)가 아래를 한 번에 한다. 기존 `transition_task_file_status`의 "status와 updated_at만 바꾼다" 계약은 그대로 둔다.

1. 입력 검증: task id 형식, `(current_status, ON_HOLD)`가 writer 표에 있는지(즉 current가 TODO·NEEDS_APPROVAL), `planned_updated_at` 형식, 직계 자식 경로.
2. 원본을 읽고 Preview의 `expected_digest`와 같은지 확인(다르면 `stale`).
3. 원본을 canonical 검증하고 status가 `current_status`인지, `hold_from` 줄이 없는지 확인.
4. 메모리에서 status를 `ON_HOLD`, updated_at을 계획 시각으로 바꾸고 `hold_from: <current_status>` 줄을 넣은 결과를 만든다.
5. **결과 바이트를 다시 canonical 검증**한다(ON_HOLD + `hold_from` 정확히 한 줄).
6. 기존 원자적 교체 helper로 한 번에 교체한다(F7).

status와 `hold_from`은 같은 바이트열에 들어 한 번의 replace로 바뀐다. 2~6 중 어디서 실패해도 원본 파일은 그대로이고 임시 파일은 지워진다. "status만 ON_HOLD이고 `hold_from`이 없는" 중간 상태는 디스크에 생길 수 없다. 5단계 덕분에 잘못된 결과가 쓰이지도 않는다.

### Resume의 검증과 복원 뒤 처리

1. 입력 검증과 digest 확인(Hold와 같음).
2. 원본 canonical 검증: status가 `ON_HOLD`인지, `hold_from` 줄이 정확히 하나이고 값이 `TODO`·`NEEDS_APPROVAL`인지. **아니면 거절**(E3, fail closed). 줄이 없거나 값이 틀린 기록은 이미 canonical 검증에서 실패하므로 Console에는 metadata review로 보이고 Resume 동작 자체가 제공되지 않는다.
3. 도착 상태는 **`hold_from` 값으로만** 정한다. 요청은 `task_id`와 `action`만 받으므로(F5) 클라이언트가 도착 상태를 고를 수 없다. `(ON_HOLD, hold_from)`이 writer 표에 있는지도 확인한다.
4. status를 `hold_from` 값으로, updated_at을 계획 시각으로 바꾸고 **`hold_from` 줄을 지운다**. 복원 뒤 이 줄은 남기지 않는다. 기록이 보류 전 기록과 같은 형식으로 돌아가며, 보류 이력은 updated_at과 Git 이력, 필요하면 수동 SOP 기록에 남는다.
5. 결과 바이트 재검증(ON_HOLD 아님 + `hold_from` 없음) 뒤 원자적 교체.

## 승인 보존 (확인 항목 4)

승인 대기였던 task가 지나는 상태와 각 상태에서 받는 실행 경로:

| 상태 | `/approve` | `/run` | `/retry` | `/go` | Console Start |
| --- | --- | --- | --- | --- | --- |
| `NEEDS_APPROVAL`(Hold 전) | 받음(승인 감사 + 실행) | 거절(DOING 아님) | 거절 | 거절(`status_not_startable`) | 거절(TODO 아님) |
| `ON_HOLD`(`hold_from` NEEDS_APPROVAL) | 거절(NEEDS_APPROVAL 아님) | 거절 | 거절 | 거절 | 거절 |
| Resume 뒤 `NEEDS_APPROVAL`(`hold_from` 삭제) | 받음(승인 감사 + 실행) | 거절 | 거절 | 거절 | 거절 |

- 근거: F9·F10의 상태 조건, F5의 Console Start 출발 상태(TODO만), 이 제안의 Resume 도착 규칙(`hold_from`만 따름).
- 따라서 Hold → Resume을 몇 번 거쳐도 승인 대기였던 task가 실행에 이르는 길은 `/approve … approve`(승인 감사 기록) 하나뿐이고, 거절은 `/approve … reject`뿐이다. Hold·Resume은 승인도 거절도 아니고 실행하지 않는다.
- Hold와 `/approve`가 겹치면: Hold가 먼저면 `/approve`는 상태 확인에서 거절되고, `/approve`가 먼저면 Console Confirm이 digest 불일치(`stale`)로 거절된다.
- QA는 이 표를 fixture task로 실제 확인한다(Q5). Discord 코드는 바꾸지 않으므로 저장소 테스트가 아닌 QA 임시 스크립트로 bot 함수를 부른다.

## DOING Hold 금지의 서버 측 강제 (확인 항목 5)

세 겹으로 막는다. 화면 버튼 유무에 기대지 않는다.

| 층 | 장치 | 결과 |
| --- | --- | --- |
| Console Preview | `hold` 동작의 허용 출발 집합이 `TODO`·`NEEDS_APPROVAL`뿐이고, snapshot status가 집합 밖이면 거절 | `task_status_transition_not_allowed`(409) |
| Console Confirm | Preview 토큰에 묶인 snapshot의 digest와 status를 잠금 아래 다시 확인 | 그 사이 DOING이 됐으면 `stale` |
| writer | `(DOING, ON_HOLD)`가 `TASK_STATUS_TRANSITIONS`에 없음 | `invalid_task_transition`. 다른 어떤 호출자도 DOING을 보류할 수 없다 |

화면은 DOING 항목에 Hold 버튼을 그리지 않는다. 이것은 편의일 뿐이며, Q4가 버튼 없이 API를 직접 불러 세 층의 거절을 확인한다.

## 규칙 일치 (확인 항목 7)

| 쌍 | 장치 |
| --- | --- |
| task-model 5-1 ↔ writer 표 | validator `transition_contract_parity`(기존) |
| task-model 5-2 경로 ↔ 5-1 | validator `transition_path_unknown`(기존) |
| writer 표 ↔ smoke 고정 집합·개수(10)·7×7 행렬 | smoke(기존 검사의 고정값 갱신) |
| Console 동작 표의 (출발, 도착) 쌍 ↔ writer 표 | **smoke 검사 1건 추가**: Console 동작이 만들 수 있는 모든 쌍(hold의 출발 집합 × ON_HOLD, resume의 ON_HOLD × `hold_from` 허용값)이 writer 표의 부분집합이고, writer 표의 ON_HOLD 관련 4쌍이 모두 Console 동작으로 덮인다 |
| writer `hold_from` 허용값 ↔ Hold 출발 집합 | smoke 검사: 두 집합이 같다(`TODO`, `NEEDS_APPROVAL`) |
| writer ↔ Console 메타데이터 허용 목록 | smoke 동일성 검사(기존, F6) |
| 서버 ↔ 화면 그룹 목록 | smoke 검사 1건 추가(F15) |
| Discord self-check | writer 표가 Discord 표의 상위집합(기존). 넓혀도 유지 |

## master-plan D1 개정 범위 (C1, 확인 항목 7)

충돌 지점(확인 항목 1): master-plan 118행 "콘솔은 `NEEDS_APPROVAL` 전이를 갖지 않고 앞으로도 추가하지 않는다"와 203행 "NEEDS_APPROVAL 전이는 추가하지 않는다"는 Hold(`NEEDS_APPROVAL → ON_HOLD`)와 Resume(`ON_HOLD → NEEDS_APPROVAL`)과 정면으로 충돌한다. 118행의 "Console의 쓰기는 … 뿐이다" 열거와 Console README의 "adds no approval queue, approval action, or `NEEDS_APPROVAL` transition"(Possible later phases 5)·Start/Complete 쓰기 범위 서술은 Hold·Resume이 빠져 사실과 달라진다. 충돌하지 않는 것은 "승인 화면이 아니다", 승인·거절 동작과 approval queue가 없다는 것, 승인성 전이 A는 `/approve`로 한정된다는 task-0044 §3.1 분류다. task-0044 §3.3("콘솔은 `NEEDS_APPROVAL`을 출발로도 도착으로도 갖지 않는다")과 task-0064는 history라 고치지 않는다.

두 군데만 바꾼다. 다른 master-plan 서술은 바꾸지 않는다.

| 위치 | 현재 | 변경 뒤 |
| --- | --- | --- |
| 118행 해당 부분 | 콘솔은 `NEEDS_APPROVAL` 전이를 갖지 않고 앞으로도 추가하지 않는다(task-0063/0064). Console의 쓰기는 Preview + Confirm 경계 안의 Task 생성·`TODO→DOING`·`DOING→DONE`·completion evidence 1회 append뿐이다 | 콘솔은 승인·거절 동작이 없고, `NEEDS_APPROVAL`에 관한 전이는 Hold(`NEEDS_APPROVAL→ON_HOLD`)와 보류 전 상태로 되돌리는 Resume(`ON_HOLD→NEEDS_APPROVAL`)뿐이며 둘 다 승인이 아니다(task-0063/0064, task-0173 개정). Console의 쓰기는 Preview + Confirm 경계 안의 Task 생성·`TODO→DOING`·`DOING→DONE`·Hold·Resume·completion evidence 1회 append뿐이다 |
| 203행 괄호 | (task-0038 승인 항목 ②, D1 결정 — 승인 화면이 아니며 NEEDS_APPROVAL 전이는 추가하지 않는다) | (task-0038 승인 항목 ②, D1 결정 — 승인 화면이 아니며 승인·거절 전이는 두지 않는다. task-0173 개정: Hold/Resume만 NEEDS_APPROVAL을 보류·복귀에 쓴다) |

- 203행은 Console Project Control이 그대로 표시하는 §2 필드다. 길이 제한은 없고 표시 때 잘릴 뿐이다(`run_web_app.py:92,1235,1309`). QA가 Project Control 표시와 validator를 확인한다.
- task-0044 §3.3과 task-0064는 history라 고치지 않는다.

Console README에 둘 개정 D1 정식 문구:

> **D1 (개정, task-0173)**: Console은 승인 화면이 아니다. Console에는 승인·거절 동작과 approval queue가 없다. `NEEDS_APPROVAL`에 관한 Console 전이는 Hold(`NEEDS_APPROVAL → ON_HOLD`)와, Hold가 기록한 보류 전 상태가 `NEEDS_APPROVAL`인 task를 그 상태로 되돌리는 Resume(`ON_HOLD → NEEDS_APPROVAL`) 둘뿐이다. 둘 다 승인도 거절도 아니며 실행하지 않고 summary를 바꾸지 않는다. 승인 대기 task가 실행에 이르는 길은 Discord `/approve`뿐이다. Hold/Resume은 task-0044 §3.1의 G(일반 전이)이며 승인 감사 대상이 아니다.

## 보류 사유 (O5, C4)

task-model §9에 더할 문구:

> - `ON_HOLD`: 보류를 결정한 주체(Owner), 보류 사유, 재개 조건(재개에 필요한 Owner 결정)을 Hold 전에 summary에 남긴다. 보류 결정을 담은 별도 task 기록이 있으면 그 id를 summary에 적는다(예: task-0156). 보류 전 상태는 `hold_from`이 기록하며 Resume은 그 상태로만 되돌린다.

- 기록 위치는 기존 summary다. Hold 전에 수동 SOP 편집으로 적는다(task-model §7, updated_at 갱신). Console 입력 UI는 없다.
- 새 입력이 없으므로 summary의 기존 canonical 검증(1–500자, backtick·제어 문자 금지)만 적용된다. Jarvis는 사유가 있는지 판정하지 않는다.
- Hold Preview는 현재 summary를 보여 주고 아래 고정 안내를 띄운다.
  > Hold changes only status, updated_at and hold_from. Before you confirm, this Task's summary must already state who decided the hold, why, and what decision resumes it (task-model §9). Jarvis does not check the summary. If the reason is missing, cancel and record it first.
- NEEDS_APPROVAL Hold Preview 추가 안내: "Hold does not approve or reject this Task. Resume returns it to NEEDS_APPROVAL, where only Discord /approve can approve it."
- Resume Preview: Held from 값과 도착 상태를 보여 준다.

## 표시 계약 영향 (O4)

| 구성 요소 | 지금 | 변경 뒤 |
| --- | --- | --- |
| Console `TASK_VIEW_GROUPS`와 화면 복사본 | 5그룹 | `ready`와 `completed` 사이에 `("on_hold", "On hold")` |
| `ON_HOLD` 규칙 | needs_attention, 25 | on_hold, 55. 사전 항목도 TODO와 DONE 사이로 옮겨 `task_view_counts` 순서를 표시 순서와 맞춘다 |
| 정렬 | … ON_HOLD(25), FAILED(30), DOING(40), TODO(50), DONE(60) | … FAILED(30), DOING(40), TODO(50), ON_HOLD(55), DONE(60). 나머지 rank·그룹은 그대로 |
| 동작 badge | 동작 TODO·DOING / 읽기 전용 5개 | 동작 TODO(Start·Hold), DOING(Complete·Evidence), NEEDS_APPROVAL(Hold), ON_HOLD(Resume) / 읽기 전용 BLOCKED·FAILED·DONE |
| ON_HOLD 안내 문구 | "Review the summary and make the required decision outside Jarvis Console." | "Resume only after the Owner re-prioritizes this Task; the summary records why it is on hold." |
| 표시 순서 문구(`app.js:1344`) | … BLOCKED, ON_HOLD, FAILED, DOING, TODO, DONE | … BLOCKED, FAILED, DOING, TODO, ON_HOLD, DONE |
| "Not shown" 문구 | "cannot be started or completed here" | "cannot be changed here" |
| 총량 10(C1), 조작 = 표시 목록(C3), C4 안내, Recent Tasks(C5) | — | 무변경 |

ON_HOLD 기록이 0건이라 지금 화면 결과는 달라지지 않는다. 보류 task가 많아 10칸을 넘으면 Resume 대상이 밀릴 수 있고 "Not shown" 수로만 보인다. 해결은 A1 범위다.

## 패키지 A 범위

1. writer: 전이 4쌍 추가, `hold_from` 허용·검증(값, ON_HOLD와의 동시 존재), Hold·Resume 전용 원자적 함수(결과 바이트 재검증 포함).
2. `docs/task-model.md`: 5-1 10행, 5-2에 Console Hold·Resume 행(조건 포함), §2 ON_HOLD 설명에 해제 규칙 한 줄, §9 ON_HOLD 규칙, `hold_from` 절(형식·허용값·존재 조건·쓰는 주체).
3. Console 서버: `hold`(출발 TODO·NEEDS_APPROVAL, 확인 문구 `HOLD TASK`)·`resume`(도착 = `hold_from`, `RESUME TASK`). 기존 Preview + Confirm·토큰·digest·잠금·표시 목록 제한을 재사용하고, 동작 표를 (출발 집합, 도착 규칙, 문구)로 넓히되 start·complete의 동작은 그대로 둔다. `hold_from` 허용 목록, 표시 규칙(O4).
4. Console 화면: 버튼, Preview, 확인 버튼 이름, 안내 문구, 그룹 목록, 표시 순서 문구.
5. smoke: F4·F6·F16 고정값 갱신, 위 "규칙 일치"의 새 검사, Hold·Resume·`hold_from` 검사.
6. Console README: Hold/Resume 절, 개정 D1 문구, 쓰기 범위 서술.
7. master-plan: 위 두 군데.

## 명시적 제외

- 기존 6건과 task-0035를 포함한 기존 task 기록의 상태·본문 변경(O8, E2). 패키지 B는 A DONE 뒤 별도 Owner 결정이다. task-0031(DOING)은 이 기능으로 보류할 수 없다
- `DOING → ON_HOLD`, 실행 경로 공통 잠금
- 감사 체인(O6), Discord 코드와 `/report`(O7), Worker 코드, `scripts/`
- Team Manager 재개, 외부 API·LLM·credential, 스케줄러·백그라운드 실행, 자동 보류·해제
- A1, 총량 10 변경, BLOCKED 전이(F18)
- 두 군데 밖의 master-plan, push, worktree·smoke 폴더 정리, `jarvis.bat`

## 호환성

- 기존 124개 기록에는 ON_HOLD와 `hold_from`이 없어 새 존재 조건을 위반하지 않는다. 해석과 `check_task_record.py` 결과는 바뀌지 않는다.
- 기존 6쌍 전이와 그 경로는 그대로다. Discord self-check의 상위집합 조건은 유지된다. Discord는 모르는 메타데이터를 무시하고(F8) 전이는 writer parser를 쓴다.
- 손으로 만든 ON_HOLD 기록(`hold_from` 없음)은 canonical 검증에서 실패한다. 이전에는 ON_HOLD만 쓴 기록이 유효했으므로 규칙이 더 엄격해지는 것이지만, 해당 기록이 0건이라 실제 영향은 없다. task-model에 이를 적는다.
- `/report` count는 ON_HOLD를 세지 않는다(F17). 패키지 B 전에 다룰지는 그때 정한다.
- task-0156·0098·0064와 task-0044 §3.3은 history로 둔다. 코드의 task-0098 주석("ranks after BLOCKED")은 새 규칙에 맞게 고친다.

## SOP 절차 (확인 항목 8)

1. Owner의 Start 승인 원문을 이 기록에 그대로 붙이고 Manager 요약에 조건별 해석을 따로 적는다.
2. Jarvis Console Start(Preview + `START TASK`)로 `TODO→DOING`.
3. Implementer가 owned 파일만 고치고 결정론적 검증을 돌린다.
4. 첫 candidate 전: `python -B scripts/check_task_record.py memory/tasks/task-0173-on-hold-status-transition.md --baseline <baseline>` → `jarvis-self-review` Skill로 self-review 1회 → 지적 처리와 `Self-review` 절 기록 → 사전 점검 재통과(task-0171·0172). self-review는 Reviewer 판정을 대신하지 않고, 여기서 고친 것은 repair가 아니다.
5. candidate commit → `check_summary_quotes.py` 참고 출력 → `jarvis-reviewer-call` Skill로 Reviewer(exact hash, 승인 원문 동봉) → 같은 candidate로 QA. budget은 retry 1, repair 1. candidate가 바뀌면 Reviewer → QA를 다시 하고, 소진되면 Director를 거쳐 Owner에게 escalation한다.
6. Docs 판정 기록, 같은 candidate의 Reviewer PASS·QA PASS를 SOP §8과 대조, Console Complete(`COMPLETE TASK`)로 DONE. push하지 않는다.
7. 즉시 escalation: 승인과 다른 전이·필드가 필요해지거나, master-plan 변경이 두 군데를 넘거나, Discord·감사·Worker 코드가 필요해지면 멈추고 묻는다.

## 검증 계획 (QA)

| # | 항목 | 확인 항목 |
| --- | --- | --- |
| Q1 | writer: 새 4쌍만 허용, 나머지 (from, to) 전부 거절, 집합·개수(10) 고정값 일치. `DOING → ON_HOLD` 거절 | 5, 7 |
| Q2 | validator PASS. 변형: 5-1에서 새 쌍 제거 → `transition_contract_parity`, 5-2에 5-1 밖 쌍 → `transition_path_unknown` | 7 |
| Q3 | `hold_from` 검증: 허용값 `TODO`·`NEEDS_APPROVAL`만, 빈 값·소문자·`DOING`·`ON_HOLD`·중복 줄·ON_HOLD 밖의 존재·ON_HOLD인데 없음을 writer와 Console parser가 모두 거절 | 1 |
| Q4 | Hold 원자성: TODO·NEEDS_APPROVAL 각각 status·updated_at·`hold_from`만 바뀌고 나머지 바이트 동일. 교체·fsync·쓰기 실패와 digest 불일치를 주입하면 원본 바이트가 그대로이고 임시 파일이 남지 않음. DOING·BLOCKED·FAILED·DONE·ON_HOLD의 Hold를 API 직접 호출로 Preview·Confirm·writer 세 층에서 거절 | 2, 5 |
| Q5 | Resume: `hold_from` 값대로 복귀하고 줄이 지워짐, 나머지 바이트 동일. `hold_from` 없음·허용 밖 값이면 거절(E3), 클라이언트가 도착 상태를 지정할 수 없음 | 3 |
| Q6 | 승인 보존: fixture로 `NEEDS_APPROVAL → Hold → Resume`이 `NEEDS_APPROVAL`로 끝나고, ON_HOLD와 복귀 뒤 상태에서 `/run`·`/retry`·`/go`·Console Start가 거절되고 `/approve … approve`만 받음을 QA 임시 스크립트로 확인. 저장소 Discord 코드·테스트는 바꾸지 않음 | 4 |
| Q7 | 규칙 일치: Console 동작 쌍 ⊂ writer 표, ON_HOLD 4쌍 모두 Console이 덮음, `hold_from` 허용값 == Hold 출발 집합, 메타데이터 허용 목록 동일, 서버·화면 그룹 목록 동일 | 7 |
| Q8 | Task View: On hold 그룹·rank 55, TODO 뒤·DONE 앞, `task_view_counts` 순서, 나머지 순서·총량 10·C3·C4 유지 | — |
| Q9 | master-plan diff가 118행 해당 부분과 203행 괄호뿐. Project Control 표시 정상, validator PASS | 7 |
| Q10 | 6건과 task-0035의 blob·status·updated_at이 위 표와 같음(baseline과 candidate 모두) | 6 |
| Q11 | Console smoke 전체, Discord self-check suite, `check_task_record.py`, `git diff --check baseline candidate`, `jarvis.bat` untracked, listener·임시 worktree 없음 | 8 |
| Q12 | 변형 확인: 새 전이 제거, `hold_from` 쓰기 제거, Resume 도착을 TODO로 고정, DOING을 Hold 출발 집합에 추가, ON_HOLD 규칙 되돌림, 화면 그룹 목록 누락이 각각 smoke 실패로 드러남 | 1~5, 7 |
| Q13 | 브라우저에서 Hold/Resume Preview·안내 문구·Confirm 확인(임시 fixture task, 실제 6건 미사용) | — |

## 완료 조건

1. 같은 candidate에 Reviewer PASS와 QA PASS(Q1~Q13). 이전 candidate의 결과는 쓰지 않는다.
2. self-review 1회와 사전 점검 통과가 기록에 남아 있다.
3. Docs 판정이 기록에 있다.
4. 변경 파일이 owned 안에만 있고 master-plan은 두 군데뿐이다. 기존 6건과 task-0035 blob이 같다.
5. Console Complete(`COMPLETE TASK`)로 DONE. push 없음.

## 예상 변경 파일 (Start 승인 시 확정)

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/discord-intake/task_file_writer.py`, `docs/task-model.md`, `docs/master-plan.md`(D1 두 군데만), `apps/jarvis-console/run_web_app.py`, `apps/jarvis-console/web/app.js`, `apps/jarvis-console/run_smoke_tests.py`, `apps/jarvis-console/README.md`, `memory/tasks/task-0173-on-hold-status-transition.md` |
| deny | `jarvis.bat`, 대상 6건과 task-0035 기록, 그 밖의 task 기록, `adapters/discord/`, `orchestrator/audit-chain/`, `orchestrator/worker/`, `scripts/`, 설계 문서(history), 그 밖의 모든 파일 |

`web/index.html`은 바꿀 필요가 없어 owned에서 뺐다(Start 뒤 구현에서 확정).

## 위험

| # | 위험 | 대응 |
| --- | --- | --- |
| R1 | 5-1 확장으로 쓰기 경로 허용 범위가 넓어짐 | 4쌍을 Owner 결정으로 고정. Q1·Q2·Q7이 행렬과 세 곳의 일치를 검사. 새 쌍의 경로는 Console Hold/Resume뿐 |
| R2 | `hold_from`이 허용 목록 한쪽에만 들어감 | smoke 동일성 검사와 Q3 |
| R3 | Hold 결과가 부분적으로 쓰임 | 한 바이트열 + 결과 재검증 + 기존 원자적 교체 helper. Q4 실패 주입 |
| R4 | 승인 우회 | Resume 도착이 `hold_from`뿐이고 Q6이 모든 실행 경로를 확인 |
| R5 | 표시 계약과 smoke 고정값 다수 변경 | F16에 나열, Q12 변형 확인 |
| R6 | 10칸을 넘으면 보류 task를 Resume할 수 없음 | "Not shown" 수로 보인다. A1 범위 |

## 작업량

중간 이상. 코드 3개(writer는 전이 4쌍·`hold_from` 검증·Hold/Resume 원자적 함수, Console 서버는 동작 표 확장·Resume 도착 규칙·표시 규칙, 화면), 테스트 1개, 문서 3개(task-model, Console README, master-plan 두 군데). task-0162보다 크다.

## 구현 단계에서 정할 세부 (정책 아님)

Start 승인 때 Owner가 바꾸지 않으면 아래 기본값으로 진행한다.

| 항목 | 기본값 |
| --- | --- |
| 확인 문구 | `HOLD TASK`, `RESUME TASK` |
| 그룹 이름 / id | `On hold` / `on_hold` |
| writer 거절 코드 | `task_file_invalid_hold_from_metadata`, Resume의 `hold_from` 문제는 같은 코드 |
| writer 함수 이름 | `hold_task_file`, `resume_task_file` |
| 안내 문구 | 위 "보류 사유"와 "표시 계약 영향"의 문구 |

## Start 승인 (원문)

```text
task-0173의 최종 제안과 Owner 결정 사항을 기준으로 진행해.
1. 먼저 공식 Start 승인

* Jarvis Console에서 `task-0173-on-hold-status-transition.md`의 Preview를 확인해.
* 기존에 합의한 범위와 정책이 일치하는지 검증해.
* 이상이 없으면 공식 Confirm 절차로 `START TASK`를 진행해.
* Start가 확인되기 전에는 구현하지 마.
* Preview가 실패하거나 승인 내용이 달라졌다면 임의로 진행하지 말고 이유를 보고해.

2. 구현 범위

* 합의된 Hold/Resume 상태 전이 4개만 구현해.
* `hold_from` 저장 및 검증, Resume 시 원래 상태 복구, 잘못된 값에 대한 fail-closed 처리를 적용해.
* `DOING → ON_HOLD`는 금지해.
* D1 문구는 합의된 최소 범위만 수정해.
* 기존 6개 보류 작업의 상태, Discord `/report`, Worker 실행 코드, 감사 기록 체계는 변경하지 마.
* 기존 워크트리와 임시 폴더를 보존해.
* `jarvis.bat`은 읽기·수정·스테이징하지 마.

3. 기존 SOP 준수

* 구현 후 preflight 실행.
* Self-review는 최초 후보 커밋 전에 1회만 실행.
* 후보 커밋 이후에는 정해진 Reviewer 및 QA 절차를 따를 것.
* Reviewer 재시도 1회, repair 1회 예산을 준수할 것.
* 승인된 범위를 벗어나는 문제가 발견되면 임의 확장하지 말고 보고할 것.
* 모든 검증과 공식 Console Complete가 끝나기 전에는 완료 처리하지 마.

4. Git 및 보고

* `git push`는 하지 마. 별도 Owner 승인이 필요해.
* 작업 시작 전후의 브랜치·변경 파일을 확인하고, 보호 대상과 기존 작업이 보존됐는지 검증해.
* 각 단계의 실제 결과와 실패 항목을 근거와 함께 보고해.
* 이미 수행하지 않은 작업을 완료했다고 표현하지 마.

우선 공식 Start 승인 결과만 확인한 뒤, 승인 성공 시 위 범위대로 진행해.
```

Start 전 확인(2026-10-20 10:59 UTC): branch `main`, HEAD `3bc3fe59afe338d36d50e3da54aaabf69e6537d2`(기준선과 같음, origin/main과 같음), tracked 변경 없음, untracked `jarvis.bat`과 이 기록. worktree 5개(main과 보존 worktree 4개).

## 구현 착수

2026-10-20 10:59 UTC에 Jarvis Console Start(Preview + Confirm, `START TASK`)로 `TODO→DOING`을 적용했다. Preview는 `current_state` TODO,
`transition` TODO → DOING, `updated_at` 2026-10-20 10:59 UTC(기록과 같음), `storage_location` 이 기록, `no_execution: true`였고, 범위·정책은
위 최종 제안과 같다. Confirm 결과는 `result_type: updated`, `previous_state` TODO, `current_state` DOING, `no_execution: true`다. 서버는
`--no-browser`로 띄운 뒤 그 프로세스만 종료했고 8790에 listener가 남지 않았다.

## Manager 요약

원문 인용은 위 다섯 원문 블록의 문장을 그대로 옮겼다. 해석은 오른쪽 칸에만 적는다. 결정 2의 O1·O2는 결정 4(E1·E2)가 대체했고, 앞 단계 원문의 "구현하지 않는다"류 제한은 그 단계에 적용됐으며 Start 승인으로 구현 단계가 열렸다.

| # | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- |
| M1 | "Jarvis-Core 다음 작업으로 A2, `ON_HOLD` 상태 전이 추가(task-model 5-1)를 검토한다." / "이번 단계는 작업 기록 및 work package 제안 작성까지만 진행한다." / "구현 착수 승인은 아직 없다." | 등록 단계의 범위다. 그 단계에서는 기록·제안만 작성하고 구현 없이 대기했다. 구현은 아래 Start 승인(M15~M18)으로만 시작했다 |
| M2 | "시작 전 확인" / "실제 작업 경로 `C:\project\work\jarvis-core`에서 진행한다." / "최신 `master-plan`, task-model 5-1 관련 문서, task-0156, task-0162, task-0172 및 관련 SOP를 먼저 읽는다." / "기존 task 기록과 문서의 실제 근거를 확인한다." / "기억이나 추측만으로 결론 내리지 않는다." / "현재 Git 상태와 HEAD를 확인하되, 파일은 수정하지 않는다." | 등록 전 `C:\project\work\jarvis-core`에서 master-plan, task-model 5-1·5-2, task-0156·0162·0172, SOP §3을 읽고 근거를 "근거 (read-only 조사)" 절 F1~F18에 줄 번호와 함께 적었다. HEAD와 Git 상태를 확인했고 그 단계에서는 이 기록 외 파일을 바꾸지 않았다 |
| M3 | "작성할 내용" / "A2의 새 task 기록 초안과 work package 제안을 작성한다." / "다음 항목을 포함한다." / "현재 문제와 근거: 보류 결정된 Team Manager task 0030·0031·0032·0033·0034·0036의 현재 상태, Task View에 미치는 영향" / "작업 범위와 명시적 제외 범위" / "`ON_HOLD` 상태의 의미와 허용 상태 전이" / "보류 해제 후 재개 규칙 및 Owner 승인 필요 여부" / "task parser, Console 표시, 검증기, 테스트와 문서에 미치는 영향" / "기존 상태 및 이전 task와의 호환성" / "Reviewer·QA·repair budget·Console Complete 등 기존 SOP 준수 방안" / "검증 계획과 완료 조건" / "예상 변경 파일, 위험 요소, 작업량 및 구현 전 Owner가 결정해야 할 사항" | 아홉 항목을 이 기록의 절에 대응시켰다: 근거(대상 6건, F1~F18), 범위·제외(패키지 A 범위, 명시적 제외), 의미·전이(최종 상태 전이표), 재개 규칙(`hold_from` 규칙, 승인 보존), 영향(표시 계약 영향, 규칙 일치), 호환성, SOP 절차, 검증 계획·완료 조건, 예상 변경 파일·위험·작업량·Owner 결정 |
| M4 | "특히 다음 두 가지는 구분해서 제안한다." / "`ON_HOLD` 상태와 상태 전이 기능을 구현하는 일" / "기존 6개 task의 상태를 실제로 변경하는 일" / "기존 6개 task의 상태 변경은 이번 구현 범위에 자동으로 포함하지 않는다." / "필요하다면 별도의 Owner 결정 항목으로 제시한다." / "상태 전이 규칙이나 재개 시 승인 정책이 문서에서 명확하지 않다면 임의로 정하지 말고 선택지를 제시한다." | 기능 구현(패키지 A)과 기존 6건 상태 변경(패키지 B)을 나눴고 B는 이 task에 넣지 않았다. 문서에 근거가 없는 정책은 선택지(O·C·E)로 제시해 Owner가 정했다 |
| M5 | "이번 단계에서 구현 코드를 수정하지 않는다." / "기존 task 6개의 상태를 변경하지 않는다." / "공식 Console Start 승인 없이 구현을 시작하지 않는다." / "커밋, push, 기존 worktree·smoke 폴더 정리 작업을 하지 않는다." / "`jarvis.bat`은 읽기·수정·stage·삭제하지 않는다." / "task-0172에서 만든 self-review 기능은 새 제안의 검토 계획에 반영하되, 기존 Reviewer·QA 절차를 대체하지 않는다." / "스케줄러, 백그라운드 실행, 외부 API/LLM 연동 등 별도 승인이 필요한 범위를 끌어들이지 않는다." | 등록 단계의 제한이며 그 단계에서 지켰다. 구현은 Start 뒤에만 했다. `jarvis.bat`은 읽지도 바꾸지도 stage하지도 않았다. self-review는 SOP 절차 4로 반영했고 Reviewer·QA를 대체하지 않는다. 스케줄러·백그라운드·외부 API/LLM은 범위 밖이다 |
| M6 | "작업 기록 초안과 work package 제안을 준비한 뒤 다음을 보고한다." / "확인한 문서와 실제 근거" / "제안한 작업 범위 및 상태 전이 규칙" / "Owner 결정이 필요한 사항" / "작성하거나 수정한 파일과 Git 상태" / "구현을 시작하지 않았다는 확인" / "문서 작성에 필요한 기존 task 기록이 이미 존재한다면 새 기록을 중복 생성하지 말고, 저장소의 기존 task 등록 규칙을 따른다." / "작업 기록이나 제안 문서를 실제로 수정해야 한다면 변경 전 대상 파일과 변경 목적을 먼저 확인하고, 이번 단계의 범위를 벗어나는 변경은 하지 않는다." / "최종적으로 Owner가 제안을 검토하고 공식 착수를 승인할 때까지 대기한다." | 등록 단계 보고와 대기를 마쳤다. A2 전용 기존 기록이 없어(task-0162·0156은 언급만) 새 기록 하나를 task 등록 관례(작업 트리에 `TODO`로 등록, Start 뒤 candidate에 포함)대로 만들었다 |
| M7 | "task-0173 `ON_HOLD` 상태 전이 작업의 제안서를 다음 Owner 결정에 맞게 정리해 주세요." / "Owner 결정" / "O1 보류 진입: `TODO`, `DOING`, `NEEDS_APPROVAL` → `ON_HOLD` 허용" / "O2 보류 해제: `ON_HOLD` → `TODO`만 허용" / "O3 적용 경로: Console의 Hold/Resume + Preview/Confirm을 사용한다." / "기존 D1 규칙과 충돌하지 않도록 필요한 최소 범위의 개정안을 명시한다." / "O4 Task View: `On hold`를 별도 그룹으로 두고 `TODO` 뒤, `DONE` 앞에 배치한다." / "기존 상태의 정렬 및 표시 계약에 미치는 영향을 확인한다." / "O5 보류 사유: task-model §9에 기록 규칙을 추가한다." / "O6 감사 체인: 이번 작업에서는 변경하지 않는다." / "O7 Discord `/report` 집계: 이번 작업에서 제외한다." / "O8 기존 6건 상태 변경: 이번 작업에서 제외한다." / "기능 완료 후 별도 Owner 결정으로 둔다." / "O9 Reviewer repair budget: 기본값을 유지한다(retry 1, repair 1)." | O3~O9는 그대로 반영했다. O1·O2는 결정 4의 E2-a·E1-a가 대체했다: 보류 진입은 `TODO`·`NEEDS_APPROVAL`만(`DOING` 제외), 해제는 `hold_from` 상태로만. O4는 rank 55 `on_hold` 그룹, O5는 task-model §9 규칙, O6·O7·O8은 감사 체인·Discord·기존 6건을 deny로 두었고, O9 budget은 retry 1·repair 1이다 |
| M8 | "구현 전 필수 확인" / "기존 task-0173 초안과 관련 문서를 다시 확인하고, 특히 다음 사항을 구체화한다." / "D1의 기존 규칙과 Console Hold/Resume 기능이 정확히 어디에서 충돌하는지" / "D1을 어떻게 최소한으로 개정할지와 그로 인해 허용되는 동작의 경계" / "`NEEDS_APPROVAL`에서 `ON_HOLD`로 이동할 때 기존 Owner 승인 의미가 보존되는지" / "`ON_HOLD`에서 `TODO`로 복귀할 때 기존 승인·실행 흐름을 우회하지 않는지" / "`On hold` 그룹의 정렬 순위와 Console parser, writer parser, validator, smoke test 사이의 일관성" / "보류 사유를 어디에 기록하고 어떤 입력 검증을 적용할지" / "기존 task 기록 및 이전 상태 데이터와의 호환성" / "문서에 근거가 없거나 정책 충돌을 확실하게 해결할 수 없는 부분은 임의로 결정하지 말고, 구체적인 선택지를 제시한다." | 일곱 확인 사항을 "master-plan D1 개정 범위"(충돌 지점 포함), "승인 보존", "규칙 일치", "보류 사유", "호환성" 절에 구체화했다. 근거가 없는 부분(승인 우회, 실행 중 작업)은 선택지로 Owner에게 넘겼다 |
| M9 | "이번 단계의 작업 제한" / "task-0173 제안서와 task 기록을 정리하는 단계까지만 진행한다." / "구현 코드 및 테스트 코드를 수정하지 않는다." / "기존 6개 task의 상태를 변경하지 않는다." / "커밋, stage, push를 하지 않는다." / "기존 worktree와 smoke 임시 폴더를 건드리거나 정리하지 않는다." / "Team Manager 재개, 자동 보류·해제, 감사 체인, Discord `/report`, master-plan 변경은 범위에 추가하지 않는다." / "수정한 task-0173 기록과 제안서를 기준으로 다음을 보고한다." / "O1~O9 결정 반영 여부" / "D1 개정안의 정확한 내용과 근거" / "최종 구현 범위 및 제외 범위" / "예상 변경 파일과 검증 계획" / "남아 있는 Owner 결정 사항" / "Git 상태 및 실제 수정 파일" / "모든 결정이 기존 정책과 일관되게 정리되면 Console Start 승인을 받을 준비가 된 상태로 보고하고 대기한다." / "승인 전에는 구현하지 않는다." | 결정 2 단계의 제한이며 그 단계에서 지켰다. master-plan 변경 제외는 결정 3의 C1이 D1 문구 두 군데로 좁혀 허용했다(M10). 그 단계 보고 후 Start 승인 전까지 대기했다 |
| M10 | "task-0173의 C1~C4에 대해 다음과 같이 진행해 주세요." / "이번 단계도 정책과 제안서 정리만이며, 구현과 Console Start는 아직 승인하지 않습니다." / "C1 수용: master-plan의 D1 관련 문구만 최소 수정 범위에 포함하는 안으로 정리합니다." / "다른 master-plan 항목은 수정하지 않습니다." / "C2 재검토: `NEEDS_APPROVAL → ON_HOLD → TODO → DOING` 경로가 기존 Owner 승인 절차를 우회할 수 있는지 실제 전이 규칙과 코드로 확인합니다." / "Resume 경고만으로 충분하다고 가정하지 마세요." / "원래 승인 대기였던 작업이 승인 없이 실행될 수 없도록 하는 최소 변경안을 제시하세요." / "원래 `NEEDS_APPROVAL` 상태로 복귀하는 방법을 포함해 선택지를 비교하되, 정책을 임의로 확정하지 마세요." / "C3 재검토: Console이 Worker 실행 여부를 확인할 수 없다는 점을 고려해, `/task`로 생성된 `DOING` 작업의 Hold를 실제로 안전하게 거절할 수 있는지 확인합니다." / "확인할 수 없다면 안전하다고 가정하지 말고, 실행 중 작업 보호를 보장할 수 있는 최소 대안을 제시하세요." / "C4 수용: 보류 사유는 기존 summary에 미리 기록하고, Hold Preview에서 사유 누락을 명확하게 안내하는 안으로 정리합니다." / "입력 UI를 추가하지 않습니다." | C1: master-plan은 118행 해당 부분과 203행 괄호만 바꿨다. C2: 코드로 우회(Console Start 뒤 `/run`·`/retry`)를 확인하고 E1 선택지를 냈고 Owner가 E1-a를 골랐다. C3: `/task` 검사로는 막을 수 없음을 확인하고 E2 선택지를 냈고 Owner가 E2-a를 골랐다. C4: 사유는 summary에 미리 기록, Hold Preview가 summary와 고정 안내를 보여 주며 입력 UI는 없다 |
| M11 | "수정된 task-0173 기록에 다음을 명시하세요." / "각 결정의 근거와 관련 코드·문서" / "최종 상태 전이표와 승인 보존 방식" / "Worker 실행 중 작업에 대한 안전한 처리 방식" / "master-plan의 D1 변경 범위" / "검증 계획과 예상 변경 파일" / "여전히 Owner 결정이 필요한 사항" / "구현 코드와 테스트 코드는 수정하지 않습니다." / "기존 6개 task의 상태를 변경하지 않습니다." / "Console Start, stage, commit, push를 하지 않습니다." / "`jarvis.bat`, 기존 worktree, smoke 임시 폴더를 건드리지 않습니다." / "제안서가 정책적으로 일관되고 남은 결정 사항이 명확해지면 보고하고 대기하세요." / "구현은 별도 Owner 승인 후 시작합니다." | 여섯 항목을 "확정된 결정", "최종 상태 전이표", "승인 보존", "DOING Hold 금지의 서버 측 강제", "master-plan D1 개정 범위", "검증 계획", "예상 변경 파일" 절에 적었다. 그 단계의 제한(코드 무변경, 6건 무변경, Start·stage·commit·push 없음, `jarvis.bat`·worktree·임시 폴더 무접촉)을 지켰다 |
| M12 | "task-0173의 남은 Owner 결정 E1~E3을 다음과 같이 확정합니다." / "E1: E1-a 수용." / "Hold 시 `hold_from`에 보류 전 상태를 기록하고, Resume은 해당 상태로 복귀시킵니다." / "E2: E2-a 수용." / "`DOING → ON_HOLD` 전이는 허용하지 않습니다." / "실행 중 작업은 이번 기능으로 보류하지 않습니다." / "task-0031을 비롯한 기존 task의 상태는 변경하지 않습니다." / "E3: 수용." / "`hold_from`이 없거나 허용되지 않는 값이면 Resume을 거절합니다(fail closed)." | E1-a: Hold가 `hold_from`을 status와 같은 교체로 기록하고 Resume이 그 상태로만 되돌린다. E2-a: `DOING → ON_HOLD`는 writer 표에도 Console Hold 출발 집합에도 없다. 기존 task 상태는 바꾸지 않았다. E3: `hold_from`이 없거나 허용값이 아니면 parser가 invalid로 읽고 Resume writer가 거절한다 |
| M13 | "이 결정을 task-0173 기록에 반영하고, 구현 착수 전 최종 제안서를 정리해 주세요." / "구현 전 확인할 사항" / "`hold_from`의 허용값이 `TODO`, `NEEDS_APPROVAL`로 제한되는지 확인합니다." / "Hold에서 상태와 `hold_from`이 일관되게 저장되는지, 실패 시 부분 변경이 남지 않는지 확인합니다." / "Resume은 `hold_from` 값과 현재 상태를 검증한 뒤 원래 상태로 복귀시키고, 복원 후 메타데이터를 어떻게 처리할지 명확히 합니다." / "`NEEDS_APPROVAL`에서 보류된 작업이 Resume 후에도 `/approve`와 기존 승인 감사 절차를 거치지 않고 실행될 수 없는지 검증합니다." / "`DOING` 작업을 Hold할 수 없다는 규칙이 서버 측에서도 강제되는지 확인합니다." / "기존 6건은 변경하지 않고 blob 불변 검사를 유지합니다." / "master-plan의 D1 개정은 승인된 최소 범위만 반영하고, task-model·writer·Console의 전이 규칙이 서로 일치하는지 검증합니다." / "기존 SOP의 self-review, Reviewer, QA, repair budget 및 Console Complete 절차를 그대로 따릅니다." | 여덟 확인 사항을 구현과 검증에 대응시켰다: 1 허용값(writer·Console parser, Q3), 2 원자성(한 바이트열·결과 재검증·원자적 교체, Q4), 3 Resume 검증과 복원 뒤 `hold_from` 삭제(Q5), 4 승인 보존(Q6), 5 DOING 서버 측 거절(Preview·writer, Q4), 6 6건 blob(Q10), 7 D1 두 군데와 세 곳 규칙 일치(Q2·Q7·Q9), 8 SOP 절차 |
| M14 | "이번에는 task-0173 기록과 제안서만 정리합니다." / "구현 코드와 테스트 코드를 수정하지 않습니다." / "최종 제안서에 남은 정책 충돌이 없으면 변경 파일, 검증 계획, 완료 조건을 보고하고 대기하세요." / "구현은 별도 Console Start 승인 이후에만 시작합니다." | 결정 4 단계의 제한이며 그 단계에서 지켰다. 구현은 Start 승인 뒤에만 시작했다 |
| M15 | "task-0173의 최종 제안과 Owner 결정 사항을 기준으로 진행해." / "먼저 공식 Start 승인" / "Jarvis Console에서 `task-0173-on-hold-status-transition.md`의 Preview를 확인해." / "기존에 합의한 범위와 정책이 일치하는지 검증해." / "이상이 없으면 공식 Confirm 절차로 `START TASK`를 진행해." / "Start가 확인되기 전에는 구현하지 마." / "Preview가 실패하거나 승인 내용이 달라졌다면 임의로 진행하지 말고 이유를 보고해." | Console Preview가 TODO → DOING, updated_at 10:59, 이 기록 경로, `no_execution: true`로 합의 범위와 같음을 확인하고 `START TASK`로 Confirm했다("구현 착수" 절). Start 확인 전에는 코드를 바꾸지 않았다 |
| M16 | "합의된 Hold/Resume 상태 전이 4개만 구현해." / "`hold_from` 저장 및 검증, Resume 시 원래 상태 복구, 잘못된 값에 대한 fail-closed 처리를 적용해." / "`DOING → ON_HOLD`는 금지해." / "D1 문구는 합의된 최소 범위만 수정해." / "기존 6개 보류 작업의 상태, Discord `/report`, Worker 실행 코드, 감사 기록 체계는 변경하지 마." / "기존 워크트리와 임시 폴더를 보존해." / "`jarvis.bat`은 읽기·수정·스테이징하지 마." | 전이는 4쌍(`TODO`·`NEEDS_APPROVAL` → `ON_HOLD`, `ON_HOLD` → `TODO`·`NEEDS_APPROVAL`)만 더했다. `DOING → ON_HOLD`는 Console Preview와 writer가 모두 거절한다. D1은 master-plan 두 군데와 Console README만 고쳤다. 기존 6건, Discord 코드(`/report` 포함), Worker 코드, 감사 체인은 바꾸지 않았다(deny). 보존 worktree 4개와 임시 폴더를 건드리지 않았다. `jarvis.bat`은 접근하지 않았다 |
| M17 | "기존 SOP 준수" / "구현 후 preflight 실행." / "Self-review는 최초 후보 커밋 전에 1회만 실행." / "후보 커밋 이후에는 정해진 Reviewer 및 QA 절차를 따를 것." / "Reviewer 재시도 1회, repair 1회 예산을 준수할 것." / "승인된 범위를 벗어나는 문제가 발견되면 임의 확장하지 말고 보고할 것." / "모든 검증과 공식 Console Complete가 끝나기 전에는 완료 처리하지 마." | 구현 뒤 `check_task_record.py` 사전 점검 → self-review 1회 → 사전 점검 재통과 → candidate → Reviewer → QA 순서다. budget은 retry 1·repair 1이다. 범위 밖 문제는 확장하지 않고 보고한다. DONE은 Console Complete로만 한다 |
| M18 | "Git 및 보고" / "`git push`는 하지 마." / "별도 Owner 승인이 필요해." / "작업 시작 전후의 브랜치·변경 파일을 확인하고, 보호 대상과 기존 작업이 보존됐는지 검증해." / "각 단계의 실제 결과와 실패 항목을 근거와 함께 보고해." / "이미 수행하지 않은 작업을 완료했다고 표현하지 마." / "우선 공식 Start 승인 결과만 확인한 뒤, 승인 성공 시 위 범위대로 진행해." | push하지 않는다. 시작 전("Start 승인" 절 아래 확인)과 끝에 branch·HEAD·변경 파일·보존 worktree·`jarvis.bat`을 확인해 보고한다. 실행하지 않은 단계는 완료로 적지 않는다 |

## 구현

| 파일 | 변경 |
| --- | --- |
| `orchestrator/discord-intake/task_file_writer.py` | `TASK_STATUS_TRANSITIONS`에 4쌍 추가(10쌍). `TASK_HOLD_STATUS`, `TASK_HOLD_FROM_FIELD`, `TASK_HOLD_FROM_STATUSES`(`TODO`·`NEEDS_APPROVAL`), `TASK_HOLD_TRANSITIONS`(ON_HOLD가 들어간 4쌍). `hold_from`을 `TASK_ALLOWED_METADATA`에 추가하고 `_transition_metadata`가 "ON_HOLD이면 허용값 한 줄, 아니면 없음"을 검사(`task_file_invalid_hold_from_metadata`). `transition_task_file_status`와 `record_task_execution_result`는 hold 4쌍을 `hold_transition_requires_hold_writer`로 거절. 새 `hold_task_file`·`resume_task_file`(공통 `_hold_or_resume_task_file`): 입력·digest·원본 canonical 검증 → status·updated_at·`hold_from`을 한 바이트열로 만들고 결과를 다시 canonical 검증 → 기존 `_atomically_replace_task_file`로 한 번에 교체. Resume 도착은 파일의 `hold_from`으로만 정하고 줄을 지운다 |
| `apps/jarvis-console/run_web_app.py` | writer의 hold 상수·함수 import. `TASK_VIEW_ALLOWED_FIELDS`에 `hold_from`. `TASK_VIEW_GROUPS`에 `on_hold`(Ready 뒤·Completed 앞). `ON_HOLD` 규칙을 `on_hold`·55·새 안내 문구로 옮기고 사전 위치도 TODO와 DONE 사이로. parser가 writer와 같은 `hold_from` 규칙을 적용하고 view에 `hold_from` 키 추가. `TASK_HOLD_ACTIONS`(hold: 출발 `TODO`·`NEEDS_APPROVAL`, `HOLD TASK` / resume: 출발 `ON_HOLD`, `RESUME TASK`)와 Hold·Resume 안내 상수. Preview는 출발 상태 집합으로 거절하고 Resume 도착을 snapshot의 `hold_from`으로 정하며, Hold Preview에 summary·경고·(NEEDS_APPROVAL이면) 승인 안내를, Resume Preview에 `hold_from`을 담는다. Confirm은 hold·resume을 전용 writer로 보내고 결과 상태가 Preview와 다르면 거절. overview 안내 문구 갱신 |
| `apps/jarvis-console/web/app.js` | 상태별 버튼 표(`actionsByStatus`: TODO Start·Hold, DOING Complete, NEEDS_APPROVAL Hold, ON_HOLD Resume), "Held from" 행, Preview의 확인 버튼 이름·summary·`hold_from`·승인 안내, 그룹 목록에 On hold, 표시 순서 문구, "Not shown"·Task View 안내 문구 |
| `apps/jarvis-console/run_smoke_tests.py` | 공식 전이 집합 10쌍·hold 4쌍·범용 writer의 hold 쌍 거절·hold 쌍 양성 왕복, ON_HOLD fixture에 `hold_from`, 상태 규칙 표·순서·그룹 목록, parser의 `hold_from` 경우 10가지, badge 분할, 버튼 표와 Preview 문구, overview 안내 문구 고정값 갱신. 새 `_test_task_hold_resume`: 규칙 일치(Console 동작 쌍 = writer hold 4쌍, Hold 출발 = `hold_from` 허용값, 메타데이터 허용 목록, 서버·화면 그룹 목록), writer 왕복·거절·실패 주입·stale, Console Hold·Resume Preview/Confirm·잘못된 확인 문구·DOING 거절·도착 상태 지정 불가·보류 중 Start/Complete 거절·복귀 뒤 Start 거절·stale·깨진 ON_HOLD |
| `docs/task-model.md` | §2 ON_HOLD 설명, 5-1 10쌍과 hold 쌍 설명, 5-2 Console Hold·Resume 행과 승인 보존 문장, §9 ON_HOLD 규칙, 새 §12 `hold_from` |
| `docs/master-plan.md` | 118행의 D1 문장과 Console 쓰기 열거, 203행 괄호만(C1) |
| `apps/jarvis-console/README.md` | Hold / Resume 절과 개정 D1 문구, 쓰기 범위 서술 세 곳 |

바꾸지 않은 것: `adapters/discord/`, `orchestrator/audit-chain/`, `orchestrator/worker/`, `scripts/`, `apps/jarvis-console/web/index.html`, 기존 task 기록, `jarvis.bat`.

## 설계와의 차이

| # | 최종 제안 | 구현 | 이유 |
| --- | --- | --- | --- |
| D1 | `hold_from` 위치는 `summary` 줄 바로 뒤(`completion_evidence`가 있으면 그 뒤) | `status` 줄 바로 뒤에 쓴다. parser는 위치를 검사하지 않는다 | `completion_evidence`는 `summary` 바로 다음 줄이어야 한다는 기존 규칙과 부딪히지 않고, 위치 규칙을 새로 두지 않아도 된다. task-model §12에 적었다 |
| D2 | Console 동작 표를 (출발 집합, 도착 규칙, 문구)로 넓힘 | `TASK_TRANSITION_ACTIONS`(start·complete)는 그대로 두고 `TASK_HOLD_ACTIONS`를 따로 둠 | 기존 계약 테스트와 Start·Complete 경로를 바꾸지 않는다. 두 표가 겹치지 않음을 smoke가 검사한다 |
| D3 | (제안에 없음) | 범용 `transition_task_file_status`와 `record_task_execution_result`가 hold 4쌍을 거절 | 4쌍을 공용 표에 넣으면 범용 writer가 `hold_from` 없이 ON_HOLD를 쓸 수 있게 되어 새 규칙을 어기는 파일이 생긴다. 승인 범위("`hold_from` 저장 및 검증")를 지키기 위한 것이며 새 동작을 열지 않는다 |
| D4 | Resume 전 `hold_from` 형식 검사 | 깨진 ON_HOLD 기록은 Console parser에서 metadata review가 되어 Resume 대상 목록에 들어오지 않고(404), writer도 거절한다 | E3(fail closed)를 두 층에서 지킨다 |
| D5 | 확인 문구·그룹 이름·함수 이름 기본값 | 기본값 그대로(`HOLD TASK`·`RESUME TASK`, `On hold`/`on_hold`, `hold_task_file`·`resume_task_file`, `task_file_invalid_hold_from_metadata`) | — |

## Implementer 검증 (작업 트리 기준, candidate 전)

| # | 검사 | 결과 |
| --- | --- | --- |
| I1 | Console smoke 전체(`python -B apps/jarvis-console/run_smoke_tests.py`) | exit 0, "Jarvis Console smoke tests passed" |
| I2 | SOP validator | `status=PASS`, `negative_checks=133`, `negative_failures=0`(5-1 = writer 10쌍, 5-2 경로 ⊂ 5-1) |
| I3 | discord-intake smoke | exit 0 |
| I4 | Discord `bot_minimal.py --self-check-suite` | exit 0, `ok: true`(writer 표가 Discord 표의 상위집합 조건 포함) |
| I5 | 승인 보존(Q6 형태, 저장소 밖 임시 폴더에서 Discord 함수 직접 호출) | NEEDS_APPROVAL·ON_HOLD·복귀한 NEEDS_APPROVAL 모두에서 `/run` `run_not_allowed`, `/retry` `retry_not_allowed`, `/go` `status_not_startable`. ON_HOLD에서 `/approve`의 durable 전이는 `status_mismatch`. 복귀 뒤에는 `/approve`의 `NEEDS_APPROVAL → DOING`만 진행. 저장소 파일·감사 체인 무변경 |
| I6 | writer 수동 확인 | TODO·NEEDS_APPROVAL Hold→Resume 왕복 뒤 바이트 동일, DOING·BLOCKED·FAILED·DONE Hold 거절, 잘못된 `hold_from` Resume 거절, 범용 writer의 `TODO → ON_HOLD` 거절, replace 실패 주입 시 원본 그대로·임시 파일 없음, stale |
| I7 | `git diff --check` | exit 0 |
| I8 | `check_no_secrets.py` | exit 1, findings 7. 모두 `scripts/check_no_secrets.py` 자신의 236~248행 예시 문자열이며 baseline `3bc3fe5`(임시 worktree에서 실행 후 삭제)에서도 같은 7건이다. 이번 변경과 무관 |
| I9 | 보호 대상 | `jarvis.bat` untracked·무접촉, 보존 worktree 4개 그대로(`git worktree list` 5줄), 기존 6건과 task-0035 파일 무변경(`git status`에 없음) |

남은 단계: 사전 점검 → self-review 1회 → 사전 점검 재통과 → candidate → Reviewer → QA → Docs 판정 → Console Complete.

## Self-review (첫 candidate 전 1회)

2026-10-20 11:17~11:19 UTC에 `jarvis-self-review` 절차대로 1회 실행했다. 사전 점검 PASS(violations 0) 뒤, 작업 트리 = index(`git diff --name-only` 출력 없음), 이 절 없음을 확인했다. 요청 파일(staged diff와 사전 점검 출력)은 저장소 밖 scratchpad에 두고, 저장소 루트에서 `claude -p --agent self-reviewer --tools Read,Grep,Glob --output-format json`으로 실행했다(`is_error: false`). 실행 전후 `git status --short`가 같았다. self-review는 Reviewer 판정이 아니며, 여기서 고친 것은 repair가 아니다(SOP §5).

| # | 지적(요지) | 처리 |
| --- | --- | --- |
| S1 | Manager 요약 M8이 없는 절 "D1 충돌과 최소 개정안"을 가리키고, 기록 어디에도 D1 충돌 지점(확인 항목 1)이 없다 | 수정. M8을 "master-plan D1 개정 범위"(충돌 지점 포함)로 바꾸고, 그 절에 master-plan 118·203행과 Console README의 충돌 문장, 충돌하지 않는 것, history로 두는 문서를 적었다 |
| S2 | M10이 "선택지를 냈다"고 하지만 기록에 E1·E2 선택지 비교와 C2·C3 코드 근거가 없다 | 수정. "확정된 결정" 아래 "C2·C3 확인 근거와 비교한 선택지" 절을 추가했다(F9~F12 근거, E1-a~d, E2-a~d와 채택 결과) |
| S3 | `hold_from` 규칙 표의 위치 행이 `summary` 뒤로 적혀 있어 코드·task-model §12(`status` 뒤)와 다르다 | 수정. 위치 행을 `status` 줄 바로 뒤로 고치고 설계와의 차이 D1과 제안 단계 기재를 함께 적었다 |

세 지적 모두 이 기록만 고쳤고 코드·문서·테스트는 바꾸지 않았다. 수정 뒤 사전 점검(`check_task_record.py --baseline 3bc3fe5…`)은 `status=PASS`, `staged_files=8`, `violations=0`, `quote_check_unquoted=0`이다.
