# task-0121-primary-workstream-decision-jarvis-console

- id: `task-0121-primary-workstream-decision-jarvis-console`
- title: `Owner 결정 기록 — 현재 primary workstream 은 jarvis-console`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-10 08:40 UTC`
- updated_at: `2026-09-10 08:40 UTC`
- summary: `task-0120 감사가 드러낸 두 Owner 결정 중 A 를 기록한다. master-plan 은 여전히 Owner 가 workstream 을 고르지 않았다고 말하지만 실제로는 task-0038 승인 항목 2 와 D1 결정 이후 Console 축소가 21 개 task 에 걸쳐 실행됐다. 이 기록은 새 방향 선택이 아니라 이미 일어난 선택을 문서화하는 것이다. master-plan 반영과 selected 상태의 Console 표현은 스키마 제약 때문에 이 작업에서 하지 않고 후속 task 로 분리한다.`
- source_command: `task-0120 감사 후 Owner 가 확정한 DECISION A 기록 지시`

## 결정

**Jarvis-Core 의 현재 primary workstream 은 `jarvis-console` 이다.**

새 방향을 고르는 결정이 아니다. task-0038 승인 항목 ② 와 D1 결정(2026-09-06)
이후 실제로 실행된 Console 축소 작업을 현재 상태로 확정해 기록하는 것이다.

## 근거

| # | 근거 | 위치 |
| --- | --- | --- |
| 1 | Owner 승인 사실이 이미 문서에 있음 — "task-0038 승인 항목 ②, Owner 승인 완료" | `docs/master-plan.md` Owner Dashboard |
| 2 | D1 결정(2026-09-06) — Console 은 승인 화면이 아닌 task lifecycle 화면 | task-0063 · task-0064 |
| 3 | 축소 1 단계 실행 — `memory_skills` 제거 | task-0071 |
| 4 | 축소 2·3 단계 실행 — `codex_review`(D6-a) · `evaluate_idea`(D6-b) · skills.json ghost(D6-d) | task-0073 · task-0075 · task-0074 · task-0076 |
| 5 | 코드 실측 — 세 기능이 `skills.json` · `run_web_app.py` · `web/app.js` 에서 전부 0 건 | task-0120 |
| 6 | task-0071 이후 완료 task 21 건이 전부 Console 작업 | task-0073 ~ task-0119 |

## master-plan 과의 충돌 — 이번에 고치지 않는다

`docs/master-plan.md` §2 는 아직 다음 값을 갖는다.

```text
- Owner decision status: selection_required
- Owner decision recommendation: hermes-manager
```

같은 문서 Owner Dashboard 는 Console 이 이미 승인됐다고 적고 있어 **문서 내부가
서로 모순**이다. 이번 작업은 그 값을 바꾸지 않는다.

## 왜 지금 반영하지 않는가 — 스키마 제약

task-0120 이 실측한 제약이다.

`selected_workstream_id` 와 `desired_outcome` 을 master-plan 에서 읽는 **필드가
존재하지 않는다.** `MASTER_PLAN_FIELDS` 19 개에 없고 `owner_decision_data.py` 가
둘 다 `None` 으로 하드코딩한다. 그런데 `owner_decision.py` 의
`STATUSES_WITH_SELECTION` 은 그 둘을 필수로 요구한다.

in-memory 실측 결과다.

| `Owner decision status` | 문서만으로 도달 |
| --- | --- |
| `selection_required` (현행) | 가능 |
| `selection_rejected` | 가능하지만 의미가 맞지 않음 |
| `selected_for_proposal` | **불가 — `/api/overview` 500** |
| `superseded` | **불가 — `/api/overview` 500** |

즉 "선택됨"을 Console 에 표현하려면 production 변경이 필요하다. Owner 가 이번
작업에서 production 변경을 금지했으므로 분리한다.

## 후속 분리

| task | 범위 | production 변경 | 승인 |
| --- | --- | --- | --- |
| **T2** | master-plan 문서만 갱신 — §2 recommendation, 제거된 기능 서술, Owner Dashboard 현재 위치 | 없음 | 문서 전용 |
| **T3** | Console 이 selected 상태를 표현 — master-plan 필드 2 개 추가 + `owner_decision_data.py` 하드코딩 제거 + 테스트 | **있음** | **별도 Owner 승인 필요** |

T2 는 `status` 를 `selection_required` 로 둔 채 진행할 수 있고, 그것만으로도
문서 내부 모순의 절반이 해소된다. T3 없이는 Console UI 가 계속 선택을 요구한다.

## 이번 작업에서 하지 않은 것

| 대상 | 상태 |
| --- | --- |
| `docs/master-plan.md` | **무변경** |
| production 코드 | **무변경** |
| `MASTER_PLAN_FIELDS` · `owner_decision_data.py` · `owner_decision.py` | **무변경** |
| T2 · T3 | **착수하지 않음** |
