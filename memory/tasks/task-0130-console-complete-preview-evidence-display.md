# task-0130-console-complete-preview-evidence-display

- id: `task-0130-console-complete-preview-evidence-display`
- title: `Console Complete Preview 에 기록된 completion evidence 표시 (판정·차단 없음)`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-09-17 07:05 UTC`
- updated_at: `2026-09-17 07:25 UTC`
- summary: `Complete Preview 는 증거가 이미 기록된 경우에만 Confirm 하라고 경고하지만 기록 여부를 보여주지 않아 Owner 가 그 확인을 Console 안에서 할 수 없었다. complete preview payload 에 digest 로 묶인 같은 snapshot 의 completion_evidence 를 추가하고 화면에 표시한다. 표시는 평가가 아니며 Complete 를 승인하거나 차단하지 않는다. 경고 문구, 전이, writer, token, digest, Start Preview 는 무변경. Implementer 기준 mutation 9 종 전부 새 assertion 이 잡는다. DONE 은 Reviewer/QA 후 Owner 가 Console Complete 로 결정한다.`
- source_command: `Owner 가 승인한 work package "Console Complete Preview: 기록된 completion evidence 표시 (판정·차단 없음)" 구현 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `4fea24d0e3ff5449c6b9a8c876ff4d4bca20fbaa` |
| 작업 전 상태 | tracked 수정 없음, untracked `jarvis.bat` 만 |
| 근거 | task-0124/0125 Console dogfooding (같은 baseline commit) |

## 무엇이 문제였나

task-0124 를 Console 로 닫을 때 Complete Preview 에 표시된 항목은 Task ID, Title,
Current State, Transition, Proposed State, Updated at, Storage location, Execution,
notice, warning 이었다. warning 은 `Confirm Complete only if verification evidence is
already recorded.` 인데, **기록 여부는 어디에도 표시되지 않았다.** 직전에 evidence 를
기록했음에도 Complete 순간에는 그 사실을 화면에서 확인할 수 없어 Console 밖 `grep` 으로
확인했다.

서버는 이미 그 값을 갖고 있다. `preview_task_transition` 은 digest 를 계산하는 같은
`raw` 를 `parse_task_view_text` 로 읽고, projection 은 `completion_evidence` 를 반환한다.
payload 로 옮기지 않았을 뿐이다.

같은 dogfooding 에서 기록했던 "Evidence Confirm 후 결과 표시가 불명확하다" 는 관찰은
확인 방법의 오류였다. `Completion Evidence Receipt` 는 `web/app.js` 에 존재하고 confirm
후 렌더링된다. 이 task 의 근거가 아니다.

## Owner 결정 (승인 시 확정)

| # | 결정 |
| --- | --- |
| 1 | completion_evidence 를 Complete Preview 에 표시하는 것은 evidence 의 존재 여부나 유효성을 평가하는 것이 아니다 |
| 2 | 시스템은 evidence 가 있다고 Complete 를 승인하지 않고, 없다고 차단하지 않는다 |
| 3 | Owner 가 기록된 값을 보고 최종 완료 여부를 판단한다 |
| 4 | `Jarvis does not evaluate whether verification evidence exists` 원칙과 `TASK_TRANSITION_COMPLETE_WARNING` 은 그대로 유지한다 |

## 승인 범위

포함:

- complete preview payload 의 `completion_evidence` (기록 값, 없으면 `null`)
- Complete Preview 화면의 `Completion evidence` 행 (없으면 `Not recorded`)
- `apps/jarvis-console/README.md` Start / Complete 계약 문구 보강
- 관련 테스트와 mutation 검증, 기존 smoke suite 통과

제외: evidence 검증·평가·차단, Confirm 횟수 변경, bulk close, `TODO→DONE` 직행,
`NEEDS_APPROVAL`/`BLOCKED`/`ON_HOLD` 전이 추가, task-0030~0036 정리, Start Preview 변경,
기타 범위 밖 개선.

## Manager assignment

| 역할 | assignment |
| --- | --- |
| Implementer | `run_web_app.py` preview payload, `web/app.js` preview 렌더러, `run_smoke_tests.py`, `README.md`, 이 기록. candidate local commit 1 개 |
| Reviewer | candidate full hash 에 고정, 위 5 파일 scope, strict read-only |
| QA | Reviewer PASS 후 같은 candidate 에서 smoke suite 와 mutation 재현 |
| Docs | Implementer 의 README 변경으로 충족. 별도 Docs 실행 `not_required` |
| 완료 | Reviewer PASS 와 QA PASS 후에도 이 기록은 `DOING` 으로 남는다. evidence 기록과 `DOING → DONE` 은 Owner 가 Console 에서 Complete Preview 를 보고 결정한다 |

## 무엇을 바꿨나

| 파일 | 변경 |
| --- | --- |
| `apps/jarvis-console/run_web_app.py` | `preview_task_transition` 의 preview dict 를 변수로 꺼내고 `action == "complete"` 일 때만 `completion_evidence` 를 붙인다. 값은 digest 를 계산한 같은 `raw` 에서 파싱한 `snapshot_view["completion_evidence"]` (카드와 같은 display 정규화, 없으면 `None`). 기존 키·값·순서, 경고, token record, digest 무변경 |
| `apps/jarvis-console/web/app.js` | `renderTaskTransitionPreview` 에 payload 가 필드를 가질 때만 `Completion evidence` 행을 렌더링. `escapeHtml(preview.completion_evidence \|\| "Not recorded")`. 버튼·disabled·분기 없음 |
| `apps/jarvis-console/README.md` | Start / Complete Task 절에 표시 계약 한 문단 (평가 아님, 승인·차단 없음, Owner 판단, Start 는 필드 없음) |
| `apps/jarvis-console/run_smoke_tests.py` | 아래 테스트 |

`confirm_task_transition`, `TaskTransitionRegistry`, writer, 확인 literal,
`TASK_TRANSITION_COMPLETE_WARNING`, Record Evidence 흐름, 카드 렌더러는 손대지 않았다.

## 테스트

`_test_task_transition_vertical_slice` 에 추가했다.

| # | 계약 |
| --- | --- |
| 1 | evidence 없는 DOING 의 complete preview 는 `completion_evidence is None`, 키 집합은 start preview 키 + `completion_evidence` 정확히 일치 |
| 2 | start preview 는 기존 exact dict 비교 유지 → 필드 없음 |
| 3 | evidence 있는 DOING(`task-8130`) complete preview 가 기록 값을 그대로 담고, 경고는 같은 상수, literal `COMPLETE TASK`, 파일 bytes 무변경 |
| 4 | preview 후 evidence 가 추가되면(`task-8131`) confirm 은 `task_changed_since_preview` 로 거부되고 status 는 `DOING` 유지 |
| 5 | evidence 없는 DOING(`task-8132`) 도 confirm 이 OK 이고 `DONE` 이 된다 (차단 없음) |
| 6 | `confirm_task_transition` + `TaskTransitionRegistry` 소스에 `completion_evidence` 가 없다 |
| 7 | app.js 렌더러: `"completion_evidence" in preview` 조건, escape 된 값과 `Not recorded`, `<dt>Completion evidence</dt>`, preview 렌더러에 `has_completion_evidence`·`disabled` 없음 |

## mutation probe — 9/9 (Implementer 보고, QA 재현 대상)

원본 bytes 를 보관해 한 번에 하나씩 바꾸고 전체 smoke 를 돌린 뒤 복원했다. 복원 후 diff digest 동일.

| mutation | 결과 |
| --- | --- |
| M1 complete payload 에서 필드 제거 | CAUGHT (KeyError) |
| M2 start 에도 필드 추가 | CAUGHT |
| M3 값을 항상 `None` | CAUGHT |
| M4 evidence 없으면 preview 차단 | CAUGHT |
| M5 confirm 이 evidence 를 읽음 | CAUGHT |
| M6 evidence 있으면 경고 제거 | CAUGHT |
| M7 UI 행 제거 | CAUGHT |
| M8 UI escape 제거 | CAUGHT |
| M9 UI `Not recorded` 제거 | CAUGHT |

## 결과 (Implementer 보고, QA 재현 대상)

- `python -B apps/jarvis-console/run_smoke_tests.py` → self-test passed, smoke tests passed, exit 0
- fixture 디렉터리 잔존 없음
- `scripts/check_no_secrets.py` 는 exit 1 이지만 baseline `4fea24d` 에서도 exit 1 이며 hit 두 건은 모두 스크립트 자신의 self-test fixture(`scripts/check_no_secrets.py:247-248`)다. 이 task 의 파일에서는 hit 가 없다. 범위 밖이므로 손대지 않았다

## Repair 이력

| # | 원인 | 조치 |
| --- | --- | --- |
| 1 | Reviewer major: 첫 candidate `b2f9320ff9799a54fab2c1f06d135d6d595da608` 가 Reviewer/QA 전에 이 기록을 `DONE` 으로 적고 결과를 검증된 것처럼 적었다 | status 를 `DOING` 으로, 결과 절을 Implementer 보고로 표기. 코드·테스트 무변경. 새 candidate 에 fresh Reviewer → QA |

## 바꾸지 않은 것

- evidence 검증·평가·차단, Confirm 횟수, bulk close, `TODO→DONE` 직행
- `NEEDS_APPROVAL`/`BLOCKED`/`ON_HOLD` 전이, task-0030~0036, Start Preview
- 경고 문구와 D1 원칙
