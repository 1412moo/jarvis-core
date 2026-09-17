# task-0132-master-plan-handoff-console-cycle-reconciliation

- id: `task-0132-master-plan-handoff-console-cycle-reconciliation`
- title: `Console 실사용 사이클 결과(task-0124~0131)를 master-plan / chatgpt-handoff 현재 상태에 반영`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-09-17 11:28 UTC`
- updated_at: `2026-09-17 11:28 UTC`
- summary: `실사용 → 제안 → 승인 → 구현 사이클이 task-0130 과 task-0131 로 두 번 완결됐지만 Console Project Control 카드가 읽는 master-plan 2 절은 task-0128 까지만 담고 handoff 는 해결된 빈 evidence 문제를 Planned 로 두었다. master-plan 2 절 Current workstream 과 Current milestone, Owner Dashboard 항목 1 개, handoff 의 DOING 행과 Technical Debt 한 행씩을 사실대로 맞춘다. Roadmap 은 Owner 지시에 따라 바꾸지 않는다. 코드, 테스트, 승인·Owner 결정 필드, historical hash, task-0038 보류, SOP 는 무변경. DONE 은 Reviewer/QA 후 Owner 가 Console Complete 로 결정한다.`
- source_command: `Owner 가 승인한 task-0132 문서 정합화 work package 지시 (handoff 378 통계 유지, task-0131 evidence commit 취급은 사실로만 기록, SOP 일반화 금지)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `5b3f6176f0cecb9a5ea89b9d59dfbcbc30df0297` |
| 작업 전 상태 | tracked 수정 없음, untracked `jarvis.bat` 만 |
| overview 기준 | 같은 baseline 에서 `GET /api/overview` 200 응답 저장 |

## 무엇이 문제였나

`GET /api/overview` 의 owner card 는 `current_workstream` 과 `current_milestone` 을
master-plan §2 에서 읽는다. baseline 에서 두 값은 task-0127/0128 에서 끝났다. master-plan
어디에도 task-0130, task-0131 이 없었다.

`docs/chatgpt-handoff.md` 에서 이 task 가 맞추는 두 곳은 사실과 달랐다.

| 위치 | 기존 | 사실 |
| --- | --- | --- |
| Console behavior 표 `DOING` without evidence 행 | Complete Preview 가 evidence 를 보여준다는 설명 없음 | task-0130 (`4ce60c4`) 이후 Complete Preview 가 기록 값 또는 `Not recorded` 를 표시 |
| Technical Debt "Evidence can be submitted empty before succeeding" | `Planned`, "No product change has been selected" | task-0131 (`5b9a774`) 이 빈 입력을 요청 없이 안내하도록 해결 |

Roadmap 4 "Decide whether observed Evidence-entry friction warrants a bounded slice" 도
`Planned` 로 남아 있지만, Owner 가 승인 시 Roadmap 갱신을 제외했으므로 이 task 에서 바꾸지 않는다.

## Owner 결정 (승인 시 확정)

| # | 결정 |
| --- | --- |
| 1 | 범위는 `docs/master-plan.md`, `docs/chatgpt-handoff.md`, 이 기록뿐. 코드·테스트 무변경 |
| 2 | handoff 의 task 수 통계("It now holds 73") 는 시점 기록으로 유지하고 고치지 않는다 |
| 3 | task-0131 의 evidence 기록 commit 취급은 master-plan 에 그 작업의 실제 사실로만 적는다. SOP 일반 규칙화나 §4 정책 수정은 하지 않는다 |
| 4 | D1, task-0124 결정 B, task-0129 결정, task-0038 보류 상태는 바꾸지 않는다 |
| 5 | 오래된 task 정리와 Roadmap 전반 갱신은 하지 않는다 |

## Manager assignment

| 역할 | assignment |
| --- | --- |
| Implementer | master-plan §2 두 필드와 Owner Dashboard 항목 1 개, handoff 두 행, 이 기록. candidate local commit 1 개 |
| Reviewer | candidate full hash 에 고정, 위 3 파일 scope, strict read-only |
| QA | Reviewer PASS 후 같은 candidate 에서 overview 비교, 필드 길이, `git diff --check`, smoke suite, hash ancestry |
| Docs | 이 package 자체가 문서 변경. 별도 Docs 실행 `not_required` |
| 완료 | Reviewer/QA PASS 후에도 `DOING`. evidence 기록과 `DOING → DONE` 은 Owner 가 Console 에서 결정 |

## 무엇을 바꿨나

### `docs/master-plan.md` (+3 −2)

| 위치 | 변경 |
| --- | --- |
| §2 `Current workstream` | "Owner 선택 표시(task-0127/0128)" 뒤에 실사용 사이클 2 회(task-0124/0125 Console 종료, task-0130, task-0131) 추가. 정규화 후 398 자 |
| §2 `Current milestone` | "Console 실사용 → 제안 → 승인 → 구현 사이클 2 회 완결(task-0130/0131)" 추가. 정규화 후 344 자 |
| Owner Dashboard | `[2026-09-17]` 항목 1 개를 task-0126 항목 뒤에 추가. task-0124/0125 종료, task-0130 표시와 평가 아님, task-0131 안내와 서버 검증 무변경, task-0131 repair 3 회와 결과 기록 commit 을 Owner 가 이 task 에 한해 새 candidate 가 아닌 결과 기록으로 취급한 사실, SOP 무변경, 승인·보류 상태 유지 |

§2 의 `Approval state`, `Approval note`, `Owner decision *`, `Recommended next step`,
`Next user-visible milestone`, `Manager reporting *`, `Last verified`,
`Verified implementation HEAD`, §4 historical hash, "최근 완료" 줄은 손대지 않았다.

### `docs/chatgpt-handoff.md` (+2 −2)

| 위치 | 변경 |
| --- | --- |
| Console behavior 표 `DOING` without evidence | Complete Preview 의 evidence 표시(task-0130, 평가 아님)와 빈 입력 안내(task-0131) 문장 추가 |
| Technical Debt "Evidence can be submitted empty before succeeding" | `Planned` → `Resolved`, task-0130 dogfooding 관찰과 task-0131 해결, 서버 검증 무변경 |

Roadmap 표는 Roadmap 4 행을 포함해 바꾸지 않았다.

"It now holds 73" 등 task 수 통계는 Owner 결정 2 에 따라 그대로 두었다.

## 검증 (Implementer 보고, QA 재현 대상)

| # | 항목 | 결과 |
| --- | --- | --- |
| 1 | §2 변경 필드 길이 (파서와 같은 정규화: 백틱·`**` 제거, strip) | Current workstream 398, Current milestone 344, 모두 500 이하. master-plan 60,773 bytes (한도 128,000) |
| 2 | `GET /api/overview` | 200 |
| 3 | overview 전후 비교 (baseline `5b3f617` 저장본 대비) | project_control 에서 바뀐 경로는 `current_workstream`, `current_milestone`, 같은 값을 옮기는 `owner_summary.current_milestone` 과 `manager_report.current_position`, 그리고 커밋 전 작업 트리를 보여주는 `working_tree_status` 뿐. `status` attention, `attention_reasons`, `owner_decision`, `workstreams`, `recent_milestone_evidence` 는 동일. manager/director report status 는 `milestone_complete` 유지. 그 밖의 차이는 파일 수정 시각 기반 discovery 목록(`recent_groups`, `docs_examples`, `tasks`)과 `repo.working_tree_status` 로, 문서 편집과 새 task 파일 때문에 생긴 것이다 |
| 4 | `git diff --check` | PASS |
| 5 | Console smoke suite | self-test passed, smoke tests passed, exit 0 |
| 6 | 새로 적은 hash 의 branch ancestry (`git merge-base --is-ancestor`) | `4fea24d`, `4ce60c4`, `991511f`, `5b9a774`, `32a3d22`, `5b3f617` 모두 ancestor |
| 7 | diff 범위 | `docs/master-plan.md`, `docs/chatgpt-handoff.md`, 이 기록 3 파일뿐. 세 파일 모두 LF |

## Repair 이력

retry_budget=1, retry_count=0, repair_budget=1, repair_count=1

| # | 원인 | 조치 |
| --- | --- | --- |
| 1 | Owner finding: 첫 candidate `08c204985b51bdc46a558ebe167da130861c397b` (Reviewer PASS, QA PASS) 가 handoff Roadmap 4 행을 `Planned` → `Implemented` 로 바꿨다. Owner 는 승인 시 Roadmap 갱신을 명시적으로 제외했으므로 승인 범위 밖 변경이다. 정책 변경이 아니라 Implementer 범위 이탈이다 | handoff Roadmap 4 행을 원래 문구로 복구하고, 이 기록의 Roadmap 관련 서술(summary, "무엇이 문제였나", Manager assignment, handoff 줄 수, "무엇을 바꿨나", "바꾸지 않은 것")만 실제 diff 에 맞게 정정. 첫 candidate 의 Reviewer/QA PASS 는 무효. 새 candidate 에 fresh Reviewer → QA |

## 바꾸지 않은 것

- `run_web_app.py`, `web/app.js`, `run_smoke_tests.py` 등 코드·테스트
- D1, task-0124 결정 B, task-0129 결정, task-0038 §6 ②/④/⑤ 보류
- SOP 문서와 §4 정책
- 오래된 task(task-0030~0036, task-0031), Roadmap 표 전체(Roadmap 4 행 포함), handoff task 수 통계
