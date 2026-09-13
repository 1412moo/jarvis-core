# task-0128-owner-selection-visibility

- id: `task-0128-owner-selection-visibility`
- title: `T4 구현 — Project Control 에서 Owner 선택을 추천과 구분해 한눈에 보이게 한다`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-13 12:22 UTC`
- updated_at: `2026-09-13 12:22 UTC`
- summary: `T3 가 연결한 선택 데이터가 카드 깊은 곳 일반 텍스트로만 보이고 후보 카드에는 Recommended 만 있어 선택과 추천이 구분되지 않던 문제를 표시 계층에서만 고쳤다. 상단 사실 표 첫 칸에 현재 선택 workstream 행을 owner_action gate 밖에 추가했고 후보 카드는 Selected 와 Recommended 를 따로 표시한다. selected_for_proposal 만 선택으로 읽고 superseded 와 계약 guard 실패는 선택을 추측하지 않는다. API shape, backend, 계약, master-plan, CSS 는 무변경. mutation 9 종 전부 새 테스트가 잡는다.`
- source_command: `Owner 가 승인한 T4 구현 지시 (superseded 선택 없음, gate 독립 표시, 두 배지 병기, CSS 재사용 우선, handoff 갱신 포함)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`daec830`** = `origin/main` |
| 근거 | T4 설계 검토 (task-0127 이후 실사용 관찰), Owner 결정 8 건 |
| baseline 검증 | Console self-test exit 0, smoke exit 0 (구현 전 실행) |

## 실사용에서 확인된 문제

T3 이후 데이터 경로는 정상이었다. 실측한 원인은 전부 표시 계층이다.

| # | 원인 | 실측 |
| --- | --- | --- |
| 1 | 선택이 카드 6 번째 섹션에만 있음 | 카드 상단 기준 약 5,280px |
| 2 | 추천은 `<code>` 박스, 선택은 일반 텍스트 | DOM computed style |
| 3 | 후보 배지가 `Recommended`/`Candidate` 두 종류뿐 | `selected_for_proposal` 과 `selection_required` 에서 배지 6 개가 완전히 동일 (node probe) |
| 4 | 선택 정보가 `owner_action` gate 에 묶임 | `Approval state: none` 이면 선택 사실까지 사라짐 |

## Owner 결정

| # | 결정 |
| --- | --- |
| 1 | T4 착수 승인 |
| 2 | `superseded` 는 선택 없음. `Selected` 도 `Superseded` 배지도 표시하지 않음 |
| 3 | 상단 `현재 선택 workstream` 행은 `owner_action` gate 와 독립 |
| 4 | 선택 → `Selected`, 추천 → `Recommended`, 같으면 두 배지, 그 외 `Candidate` |
| 5 | CSS 는 기존 class 재사용 우선 |
| 6 | 상태 배지 색 교정(C-lite) 제외 |
| 7 | `docs/chatgpt-handoff.md` Current UI 갱신 |
| 8 | `8d21efe` 에서 사라진 Owner Decision 이외 Project Control 정적 단언 복원은 제외, 후보로만 기록 |

## 무엇을 바꿨나

### `apps/jarvis-console/web/app.js`

| 변경 | 내용 |
| --- | --- |
| `isOwnerDecisionContract` 신설 | 기존 `renderOwnerDecision` guard 를 그대로 옮긴 공용 판정 |
| `ownerDecisionSelection` 신설 | guard 통과 + `status === "selected_for_proposal"` + 후보 안의 선택 + outcome 이 모두 있을 때만 선택을 반환, 그 외 `null` |
| `renderOwnerSelectionFact` 신설 | 선택이면 `표시명 (ID) — outcome`, 선택 없음이면 `Not selected`, guard 실패면 `Unavailable` |
| `ownerDecisionCandidateBadges` 신설 | `Selected` 와 `Recommended` 를 **독립적으로** 붙이고 둘 다 없을 때만 `Candidate` |
| `renderProjectControl` | `owner-milestone-facts` 첫 칸에 선택 행 1 개. `owner_action` gate 줄은 그대로 |
| `renderOwnerDecision` | guard 를 공용 판정으로 교체, `현재 선택`/`원하는 결과` 와 후보 배지가 같은 선택 판정을 사용 |

`renderOwnerDecision` 의 `현재 선택` 칸은 이전에 status 와 무관하게 `selected_workstream_id` 를
그대로 보여줬다. 이제 같은 판정을 쓰므로 `superseded` 에서는 `Not selected` 가 된다. Owner 결정
2 와 세 표시 지점(상단 행, 섹션 사실 표, 후보 배지)이 서로 어긋나지 않게 하기 위한 것이다.
현재 master-plan 은 `selected_for_proposal` 이라 live 화면 값은 바뀌지 않는다.

### CSS — 무변경

`Selected` 는 기존 `.overview-badge.source-area`(파랑)를, `Recommended` 는 기존
`.overview-badge.read-only`(초록)를 재사용했다. `styles.css` diff 0 줄.

### 구현 중 한 번 고친 것

첫 candidate 는 상단 행의 ID 를 `<code>` 로 감쌌다. 브라우저에서 좁은 grid 칸 안의 `<code>` 가
블록처럼 줄을 끊어 `Jarvis Console (` / 박스 / `) — …` 로 읽기 어려웠다. 상단 행에서만 `<code>`
를 빼 일반 텍스트로 바꾸고 테스트 기대값 4 곳을 함께 맞췄다. CSS 추가 없이 해결했다.

## 결과 (브라우저 실측, viewport 1024×768)

| 항목 | 값 |
| --- | --- |
| 상단 `현재 선택 workstream` | `Jarvis Console (jarvis-console) — Jarvis Console을 Jarvis task lifecycle 화면으로 축소해 실제 작업에 반복 사용한다` |
| 상단 행 위치 | 카드 상단 기준 **356px** (문서 기준 948px) |
| 후보 배지 | Jarvis Console `Selected + Recommended`, 나머지 5 개 `Candidate` |
| 페이지 전체 `Selected` 배지 수 | 1 |
| Decision 섹션 안 button/form/input | 0 |
| console error | 0 |

### 트레이드오프 — 정직하게 남긴다

상단 사실 표가 4 칸에서 5 칸이 되어 `다음 단계` 가 grid 두 번째 줄로 내려갔다. 그 칸의 긴 문장
때문에 `현재 위치와 다음 결정` 카드가 약 585px 길어졌고 아래 섹션이 그만큼 내려갔다
(Director Summary 카드 기준 1,392px → 1,977px, `다음 workstream 결정` 5,282px → 5,868px).
선택 사실은 첫 스크롤 안으로 올라왔지만 나머지 섹션은 더 멀어졌다. 레이아웃 재설계는 이번
범위가 아니다.

브라우저 첫 측정에서 상단 행이 문서 기준 3,434px 로 읽힌 적이 있다. 같은 세션의 재측정은
카드 상단 592px + 356px = 948px 로 일관됐고 위 표는 재측정값이다. 첫 값의 원인은 확인하지
못했다.

## 테스트

`_test_owner_decision_selected_visibility` 를 추가하고 `main()` 에 등록했다. 검사 본체
`_check_owner_decision_selected_visibility(app_js, live_card)` 는 source 를 인자로 받아 mutation
probe 가 파일을 건드리지 않고 변형본을 넣을 수 있다. 렌더링은 기존 Director renderer harness 와
같은 방식(`app.js` 에서 함수 추출 → `node -`)이다.

| 검사 | 내용 |
| --- | --- |
| S1 | 선택 = 추천 = `jarvis-console` → 그 카드에 `Selected` + `Recommended`, 나머지 `Candidate`, 상단 행과 섹션 사실 일치 |
| S2 | 선택 `hermes-manager` ≠ 추천 `jarvis-console` → 각 배지가 정확한 카드에만 |
| S3 | `selection_required` → `Selected` 0 건, `Not selected`/`Not provided` fallback 유지 |
| S4 | `superseded` → `Selected` 0 건, 선택 없음과 같은 표시 |
| S5 | `contract_type`/`version`/`read_only` 위반, `null` → 섹션 Unavailable, 선택 `null`, 상단 행 `Unavailable` |
| S6 | outcome 에 HTML·따옴표 → 섹션과 상단 행 모두 escape |
| S7 | 선택 관련 함수 5 개에 `<button` `<form` `<input` `fetch(` `navigator.clipboard` `addEventListener` `/api/` 없음, `/api/owner-decision` 부재, 상단 행이 사실 표 안에 gate 없이 1 회 |
| S8 | live payload → master-plan snapshot 과 일치, payload 키 13 개 정확히 고정 |

S8 의 키 집합 단언은 이번에 새로 생겼다. 조사 시점에 owner_decision payload 키 집합을 직접
고정하는 단언은 없었다.

## mutation probe — 9/9

scratchpad 스크립트가 `app.js` 변형본을 메모리에서만 만들어 같은 검사에 넣었다. 저장소 파일은
바꾸지 않았다.

| 변형 | 결과 |
| --- | --- |
| M1 `Selected` 를 추천 기준으로 판정 | **CAUGHT** (S2) |
| M2 status 와 무관하게 `Selected` | **CAUGHT** (S4) |
| M3 선택과 같으면 `Recommended` 생략 | **CAUGHT** (S1) |
| M4 선택 helper 가 추천을 읽음 | **CAUGHT** (S2) |
| M5 선택 helper 의 계약 guard 제거 | **CAUGHT** (S5, `null` 입력에서 harness 실패) |
| M6 상단 행 outcome escape 제거 | **CAUGHT** (S6) |
| M7 상단 행 fallback 제거 | **CAUGHT** (S3) |
| M8 renderer 에 `fetch(` 추가 | **CAUGHT** (S7) |
| M9 상단 행을 `owner_action` gate 안으로 이동 | **CAUGHT** (S7) |

## 검증

최종 candidate 기준.

| 검증 | 결과 |
| --- | --- |
| `node --check apps/jarvis-console/web/app.js` | OK |
| targeted `_test_owner_decision_selected_visibility` | PASS |
| mutation probe | 9/9 CAUGHT |
| `python -B apps/jarvis-console/run_web_app.py --self-test` | exit 0 |
| `python -B apps/jarvis-console/run_smoke_tests.py` | exit 0 |
| `python -B apps/hermes-manager-pilot/run_smoke_tests.py` | exit 0 |
| `python -B orchestrator/discord-intake/run_smoke_tests.py` (Task parser/writer) | exit 0 |
| 브라우저 Project Control 실렌더링 | 위 결과 표 |
| `git diff --check` | exit 0 |

## 바꾸지 않은 것

| 대상 | 상태 |
| --- | --- |
| `/api/overview` response shape | **무변경** — owner_decision 13 키를 새 테스트가 고정 |
| Python backend (`run_web_app.py` 등) | **무변경** |
| `owner_decision.py` 계약 · `owner_decision_data.py` | **무변경** |
| `docs/master-plan.md` · `MASTER_PLAN_FIELDS` · `MASTER_PLAN_OPTIONAL_FIELDS` | **무변경** |
| task-0126 ancestry 검증 · `MAX_COMMITS = 5` · historical hash | **무변경** |
| `owner_action` gate (`app.js` Decision 섹션) | **무변경** — 상단 행만 gate 밖 |
| 상태 배지 색 (C-lite) | **무변경** — Owner 결정 6 |
| `styles.css` · `README.md` | **무변경** |
| `jarvis.bat` | **접근하지 않음** |
| write path · approval action · 선택 변경 UI · 외부 호출 | **추가하지 않음** |
| D2 · D3 · D4 | **추가하지 않음** |

## 남은 것

| 항목 | 상태 |
| --- | --- |
| `8d21efe`(task-0071) 에서 사라진 Owner Decision 이외 Project Control 정적 단언 (`현재 만드는 이유`, Director/Manager 순서, `Jarvis-Core 내부 workstream` 등) | **별도 task 후보** — Owner 결정 8, 이번에 복원하지 않음 |
| 상단 사실 표가 길어져 아래 섹션이 약 585px 내려감 | 관찰로만 기록, 레이아웃 변경은 범위 밖 |
| 상태 배지가 선택 완료도 주황 `approval-needed` | Owner 결정 6 으로 보류 |
