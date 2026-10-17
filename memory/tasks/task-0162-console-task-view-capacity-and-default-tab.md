# task-0162-console-task-view-capacity-and-default-tab

- id: `task-0162-console-task-view-capacity-and-default-tab`
- title: `Console Task View 상태별 미표시 task 수 표시(A3)와 첫 화면 Project Control(B)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-10-17 10:38 UTC`
- updated_at: `2026-10-17 13:13 UTC`
- summary: `Jarvis Console Actionable Task View는 10칸 중 6칸을 보류된 Team Manager task가 차지해 무엇이 빠졌는지 알 수 없고, 첫 화면은 Chat / Command다. Owner 승인 범위(A3+B)대로 /api/overview에 상태별 미표시 task 수를 읽기 전용 필드로 더해 화면에 보여 주고, 첫 활성 탭을 Project Control로 바꿔 처음 열 때 바로 불러온다. 진행 task 표시 보장(A1)과 ON_HOLD 전이(A2)는 제외해 별도 Owner 결정으로 남기고, 기존 Task View 계약 C1~C5는 바꾸지 않으며 push는 하지 않는다.`
- source_command: `Owner 결정: Console 작업 묶음 A+B, A 범위 A1+A3, A2 보류`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `6285f192b59e641e6cc80f52625ed3612ccff908` (main HEAD = origin/main) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 저장소 task 상태 | DONE 107, NEEDS_APPROVAL 5(task-0030/0032/0033/0034/0036), DOING 1(task-0031). 6건 모두 task-0156 Team Manager 보류 대상 |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` |

## Owner 결정 (원문)

```text
Owner 결정:

* 작업 묶음: A+B
* A 범위: A1+A3
* A2(ON_HOLD 상태 전이 추가)는 별도 결정 사항으로 보류

먼저 task-0114의 표시 순서 계약과 현재 Task View/Start/Complete의 공통 10개 제한을 확인하세요. A1은 단순 UI 정렬 변경이 아니라 실제 actionable 범위에도 영향을 주므로, 기존 계약과 충돌하지 않는 설계를 먼저 제시하세요.
A3은 미표시 task 개수를 상태별로 보여 주는 읽기 전용 표시로 제한합니다. task 상태나 데이터를 변경하지 마세요.
B는 Project Control을 첫 화면으로 설정하고, 최초 진입 시 해당 화면을 바로 불러오도록 합니다.
이번 단계에서는:

1. 범위와 영향 파일을 task 기록에 반영
2. 기존 계약과 회귀 위험 확인
3. Console Start Preview까지 준비
4. Preview 결과를 보고한 뒤 중단

Start Confirm, 구현, DONE 처리, checkpoint 커밋, push는 별도 승인 전까지 하지 마세요. `jarvis.bat`은 계속 보호하고, 열기·읽기·수정·스테이징·커밋하지 마세요.
```

## 확인한 기존 계약 (read-only)

| # | 계약 | 근거 | 내용 |
| --- | --- | --- | --- |
| C1 | 표시 총량 10, 선택은 `task_view_sort_key` | task-0114 Owner DECISION 2 | "10 유지. `OVERVIEW_MAX_ITEMS_PER_DIRECTORY` 값 무변경. attention 이 11 건 이상이어도 총량 10. selection 은 기존 `task_view_sort_key` 재사용". 테스트 사례 2(DONE 10 + NEEDS_APPROVAL 12 → 총 10, 초과 2건 미표시)가 고정한다 |
| C2 | 표시 순서 | task-0114, `TASK_VIEW_STATUS_RULES` | metadata review(0), NEEDS_APPROVAL(10), BLOCKED(20), ON_HOLD(25), FAILED(30), DOING(40), TODO(50), DONE(60), 그다음 `updated_at` 최신순, path |
| C3 | 조작 대상 = 표시 목록 | task-0103, `selected_task_transition_items()` | Start/Complete/Record Evidence는 표시된 10개 안의 task만 받고 밖은 404(`task_not_found_in_actionable_view`)로 거절한다. live payload에서 `selected_task_transition_items() == tasks`를 확인한다 |
| C4 | 안내 문구 고정 | task-0105·0114 | "Shows up to 10 Tasks, attention first then most recently updated; this is not the full backlog."를 smoke가 정확한 문구로 고정한다(`run_smoke_tests.py:5229`) |
| C5 | Recent Tasks 그룹 | task-0114 | 파일 mtime 최신 10개, Task View와 다른 의미를 유지 |

## 조사로 정정한 사실

- 앞선 제안에서 A1을 "TODO·DOING이 최근 DONE에 밀리지 않게"로 설명했지만, C2에 따라 DONE은 이미 맨 뒤(60)라 TODO·DOING을 밀어내지 못한다. 그 설명은 틀렸다.
- 실제로 진행 task를 밀어내는 것은 attention 그룹(NEEDS_APPROVAL·BLOCKED·ON_HOLD·FAILED)이다. 지금은 보류 task 5건(NEEDS_APPROVAL)과 DOING task-0031이 앞 6칸을 차지해, 다른 DOING·TODO는 남은 4칸 안에서만 보이고 조작된다. Owner의 진행 중·대기 task가 4건을 넘으면 오래된 것부터 화면과 Start/Complete 대상에서 빠진다.
- A2(보류 task를 ON_HOLD로)만으로도 칸은 비지 않는다. ON_HOLD도 attention 그룹(rank 25)이라 DOING보다 앞에 온다.

## A1 설계안 (Owner 결정 필요)

C1·C2·C3를 모두 그대로 두면 진행 task의 표시·조작을 보장할 방법이 없다. 그래서 무엇을 바꾸는지가 다른 세 안을 제시한다.

| 안 | 내용 | 바뀌는 계약 | 유지되는 것 | 회귀 위험 |
| --- | --- | --- | --- | --- |
| A1-1 (권장) | 선택 규칙: attention 전부와 DOING·TODO 전부를 먼저 넣고(안전 상한 예: 30), 총량이 10보다 적으면 DONE으로 10까지 채운다. 순서는 C2 그대로 | C1의 "총량 10"을 "최소 10, attention·진행 task가 많으면 상한까지"로 바꿈(task-0114 Owner DECISION 2 개정) | C2 순서, C3(조작 대상 = 표시 목록), C5 | task-0114 테스트 사례 2의 기대값 변경 필요. 안내 문구(C4) 변경 필요. 표시가 길어질 수 있음 |
| A1-2 | 표시는 10 그대로 두고, Start/Complete는 전체 task 중 상태가 맞으면 받음 | C3(task-0103) 폐기 | C1, C2, C4 | 화면에 없는 task를 조작할 수 있어 "보이는 것만 Confirm" 안전 경계가 약해짐. task-0103 테스트 기대값 변경. 권장하지 않음 |
| A1-3 | 진행 task 칸 예약: 10칸 중 일정 수를 DOING·TODO에 먼저 배정 | C2(attention 우선 순서)와 C1 사례 2(attention 11건 이상이면 전부 attention) | C1 총량 10, C3 | 오래된 NEEDS_APPROVAL이 다시 안 보일 수 있어 task-0114가 고친 결함과 같은 방향의 회귀 |

- 권장 A1-1은 조작 대상과 표시 목록이 같다는 안전 경계(C3)를 지키고, 표시 순서(C2)도 그대로다. 바뀌는 것은 총량 10이라는 Owner 결정 하나뿐이며 이를 Owner가 명시적으로 개정해야 한다.
- 어느 안도 승인되지 않으면 A1은 이번 task에서 빼고 A3·B만 구현한다(A3로 미표시 수는 보이게 된다).

## A3 설계 (계약 충돌 없음)

- `/api/overview` 응답에 읽기 전용 필드 하나를 더한다(예: `task_view_hidden_counts`, 상태별 미표시 task 수). 기존 키·item 키·`task_view` 키는 바꾸지 않는다.
- 계산: 전체 projection(이미 전량 scan, task-0114 DECISION 1) 중 선택되지 않은 것을 status별로 센다. 새 파일 read는 없다.
- 화면: Actionable Task View 머리에 "표시되지 않은 task: DONE 101 …" 같은 한 줄. 버튼·조작 없음. task 상태·파일은 바꾸지 않는다.
- C4 안내 문구는 A1-1을 택할 때만 바꾼다. A3만으로는 바꾸지 않는다.

## B 설계 (계약 충돌 없음)

- `web/index.html`의 첫 활성 탭을 Project Control(`data-tab="tasks"`)로, 나머지 패널 `hidden` 상태를 그에 맞게 바꾼다.
- `web/app.js` 시작 시 `activateTab("tasks")`를 불러 Project Control을 바로 불러온다(`loadOverview()`). 탭 순서·다른 탭 동작은 바꾸지 않는다.
- smoke는 `activateTab` 소스와 `activateTab("tasks")` 호출을 일부 고정한다(`run_smoke_tests.py:5891`, `:5911`). 첫 탭 고정 검사가 있는지 구현 전에 다시 확인한다.

## 범위와 영향 파일

| 구분 | 경로 |
| --- | --- |
| owned | `apps/jarvis-console/run_web_app.py`(A3 필드, A1 승인 시 선택 규칙), `apps/jarvis-console/web/app.js`(A3 표시, B 시작 탭, A1 승인 시 안내 문구), `apps/jarvis-console/web/index.html`(B 첫 탭), `apps/jarvis-console/run_smoke_tests.py`(회귀 검사), 필요 시 `apps/jarvis-console/README.md`(첫 화면·미표시 수 설명), 이 기록 |
| deny | `jarvis.bat`, task 기록 데이터(다른 task 파일의 상태·내용), `docs/task-model.md`(A2 보류), `docs/master-plan.md`, Discord·Worker 코드, 그 밖의 모든 파일 |

## 회귀 위험과 검증 계획

| # | 항목 |
| --- | --- |
| R1 | C3 유지: 표시 목록과 조작 대상이 같은지(`selected_task_transition_items() == tasks`), 목록 밖 task는 여전히 404 |
| R2 | C2 유지: 선택된 목록이 `task_view_sort_key` 순서인지 |
| R3 | A3: 미표시 수 합 + 표시 수 = 유효 task 전체 수, status별 값이 실제와 같은지, 응답의 기존 키가 그대로인지 |
| R4 | A1(승인 시): 결정된 규칙에 맞춘 fixture(예: attention 6 + DOING 5 + DONE 다수)에서 DOING 5건이 모두 표시되고 Start/Complete 대상인지, 상한이 지켜지는지 |
| R5 | B: 첫 화면이 Project Control이고 열 때 overview를 한 번 불러오는지, 다른 탭 전환이 그대로인지 |
| R6 | 변형 확인: A3 계산 제거, B 시작 호출 제거, (A1 승인 시) 선택 규칙 되돌림이 각각 smoke 실패로 드러나는지 |
| R7 | Console smoke·self-test, SOP validator, discord-intake smoke, `git diff --check`, 변경 범위. Console 확인은 GET·Preview만 쓰고 task 파일에 쓰는 Confirm은 하지 않는다 |

## 정식 시작 승인과 확정 범위 (원문)

```text
Owner 결정:

* task-0162는 A3+B 범위로 정식 시작 승인합니다.
* A1-1, A1-2, A1-3은 이번 범위에서 제외합니다.
* A2(ON_HOLD 전이 추가)도 제외합니다.

A3:

* `/api/overview`에 상태별 미표시 task 수를 제공하는 읽기 전용 필드를 추가합니다.
* 기존 응답 키는 유지합니다.
* 표시 수와 미표시 수의 합이 전체 task 수와 일치하는지 검증합니다.

B:

* Project Control을 첫 활성 탭으로 설정하고 최초 진입 시 해당 화면을 불러옵니다.
* 다른 탭 동작은 유지합니다.

기존 C1~C5 계약은 이번 작업에서 변경하지 마세요. A1의 구조적 해결은 별도 Owner 결정 사항으로 남깁니다.
기록에 이번 승인 범위를 명확히 반영한 뒤 구현과 R1~R7 검증을 진행하세요. `jarvis.bat`과 다른 task 기록의 데이터는 건드리지 마세요. master-plan도 이번 범위에서 수정하지 마세요.
QA 결과와 변경 범위를 보고한 뒤 중단하세요. Console Complete, DONE 처리, checkpoint 커밋, push는 별도 승인 전까지 하지 마세요.
```

candidate·Reviewer 진행 승인(원문):

```text
candidate 커밋해서 Reviewer 진행해
```
위의 "A1 설계안"과 "범위와 영향 파일"·"회귀 위험과 검증 계획" 중 A1 관련 내용은 등록 당시 제안이며, 확정 범위는 이 절과 아래 Manager 요약을 따른다.

## Manager 요약

| # | 승인 조건 | Manager 해석과 충족 방법 |
| --- | --- | --- |
| R0 | 등록 블록: "먼저 task-0114의 표시 순서 계약과 현재 Task View/Start/Complete의 공통 10개 제한을 확인하세요." / "기존 계약과 충돌하지 않는 설계를 먼저 제시하세요." / "A3은 미표시 task 개수를 상태별로 보여 주는 읽기 전용 표시로 제한합니다. task 상태나 데이터를 변경하지 마세요." / "1. 범위와 영향 파일을 task 기록에 반영 2. 기존 계약과 회귀 위험 확인 3. Console Start Preview까지 준비 4. Preview 결과를 보고한 뒤 중단" | 등록 단계에서 충족했다: C1~C5 계약 확인, A1 설계안 3개와 충돌 계약 제시, 범위·영향 파일·회귀 위험 기록, Start Preview 뒤 멈춤. A3은 읽기 전용 표시로만 구현했고 task 상태·데이터를 바꾸지 않는다 |
| P1 | "candidate 커밋해서 Reviewer 진행해" | candidate 커밋과 Reviewer 실행이 승인됐다. Console Complete·DONE·checkpoint 커밋·push는 여전히 별도 승인 사항이다(X5, push는 AGENTS.md·SOP) |
| P0 | "task-0162는 A3+B 범위로 정식 시작 승인합니다." | Console Start(`START TASK`) 뒤 A3와 B만 구현한다 |
| X1 | "A1-1, A1-2, A1-3은 이번 범위에서 제외합니다." / "A1의 구조적 해결은 별도 Owner 결정 사항으로 남깁니다." | Task View 선택 규칙·총량·조작 범위를 바꾸지 않는다 |
| X2 | "A2(ON_HOLD 전이 추가)도 제외합니다." | `docs/task-model.md`와 상태 전이를 바꾸지 않는다 |
| S1 | A3: "`/api/overview`에 상태별 미표시 task 수를 제공하는 읽기 전용 필드를 추가합니다." | `overview_payload()`에 새 키 하나를 더한다. 값은 이미 만든 전체 projection에서 선택되지 않은 task를 status별로 센 것이다. 새 파일 read·쓰기 없음. 화면에는 Actionable Task View에 읽기 전용 한 줄로 보인다 |
| S2 | "기존 응답 키는 유지합니다." | 기존 최상위 키, item 키, `task_view` 키를 바꾸거나 지우지 않는다 |
| V1 | "표시 수와 미표시 수의 합이 전체 task 수와 일치하는지 검증합니다." | smoke에 표시 수 + 미표시 수 합 = 전체 수, status별 일치 검사를 더한다. 여기서 "전체 task 수"(`total`)는 Task View가 다루는 task, 곧 discovery 후보의 projection 수다. 기존 discovery 규칙이 비밀정보처럼 보이는 파일 이름(`SECRET_LIKE_NAME_PARTS`)을 빼므로 `task-0043-no-secrets-enforcement.md`는 포함되지 않아, 실제 저장소에서 `total` 113은 템플릿을 뺀 task 파일 수 114보다 1 적다. 이 정의를 받아들일지는 Owner 확인 사항이다(discovery 규칙은 C 범위 밖이라 바꾸지 않았다) |
| S3 | B: "Project Control을 첫 활성 탭으로 설정하고 최초 진입 시 해당 화면을 불러옵니다." | `index.html` 첫 활성 탭·패널을 Project Control로, `app.js` 시작 시 `activateTab("tasks")` 호출 |
| S4 | "다른 탭 동작은 유지합니다." | `activateTab`과 탭 버튼 처리는 바꾸지 않는다 |
| X3 | "기존 C1~C5 계약은 이번 작업에서 변경하지 마세요." | 총량 10, 표시 순서, 조작 대상 = 표시 목록, 안내 문구, Recent Tasks 그룹을 그대로 둔다(R1·R2·C4 문구 불변으로 확인) |
| X4 | "`jarvis.bat`과 다른 task 기록의 데이터는 건드리지 마세요. master-plan도 이번 범위에서 수정하지 마세요." | 소유 파일은 아래 확정 범위뿐이다 |
| O1 | "기록에 이번 승인 범위를 명확히 반영한 뒤 구현과 R1~R7 검증을 진행하세요." | 이 기록의 "정식 시작 승인과 확정 범위"·Manager 요약·"확정 범위의 File ownership"을 먼저 적은 뒤 Console Start(2026-10-17 11:17 UTC)와 구현을 진행했고, 검증 결과는 "Implementer 검증"에 R1~R7로 적었다 |
| X5 | "QA 결과와 변경 범위를 보고한 뒤 중단하세요. Console Complete, DONE 처리, checkpoint 커밋, push는 별도 승인 전까지 하지 마세요." | 구현과 R1~R7 검증 결과를 보고하고 멈춘다. push는 AGENTS.md·SOP상으로도 별도 승인 사항이다 |

## 확정 범위의 File ownership

| 구분 | 경로 |
| --- | --- |
| owned | `apps/jarvis-console/run_web_app.py`(A3 필드), `apps/jarvis-console/web/app.js`(A3 표시, B 시작 탭), `apps/jarvis-console/web/index.html`(B 첫 탭), `apps/jarvis-console/run_smoke_tests.py`(회귀 검사), 필요 시 `apps/jarvis-console/README.md`(첫 화면·미표시 수 설명), 이 기록 |
| deny | `jarvis.bat`, 다른 task 기록, `docs/task-model.md`, `docs/master-plan.md`, Discord·Worker 코드, 그 밖의 모든 파일 |

## 구현 착수

2026-10-17 11:17 UTC에 Jarvis Console Start(Preview + Confirm, `START TASK`)로 `TODO→DOING`을 적용했다(Console 결과
`result_type: updated`, `TODO → DOING`, `no_execution: true`).

## 구현

| 파일 | 변경 |
| --- | --- |
| `apps/jarvis-console/run_web_app.py` | `task_view_counts()`를 더하고 `overview_payload()`가 이미 만든 전체 projection과 표시 수로 `task_view_counts`(`read_only`, `total`, `displayed`, `hidden`, `hidden_by_status`)를 응답에 넣는다. 선택은 같은 projection의 앞 10개 그대로라 순서·총량·조작 범위는 바뀌지 않는다. 유효하지 않은 기록은 `METADATA_REVIEW`로 센다(S1·S2) |
| `apps/jarvis-console/web/app.js` | `taskViewHiddenCountsMarkup()`로 Actionable Task View에 "Not shown: N of M Tasks (상태 수…)" 한 줄을 읽기 전용으로 보인다(버튼 없음, 값은 escape). 시작 시 `activateTab("tasks")`를 불러 Project Control을 바로 불러온다(S1·S3). `activateTab`과 다른 탭 처리는 그대로다(S4) |
| `apps/jarvis-console/web/index.html` | 첫 활성 탭 버튼과 보이는 패널을 Project Control로 바꾸고 Chat / Command 패널을 숨김으로 바꿨다(S3) |
| `apps/jarvis-console/run_smoke_tests.py` | `_test_task_view_hidden_counts_and_first_screen()`를 더했다(V1, R1~R5) |
| `apps/jarvis-console/README.md` | 첫 화면과 `task_view_counts` 설명 두 항목 |

C1~C5는 바꾸지 않았다. 안내 문구 "Shows up to 10 Tasks, …"(C4)와 Recent Tasks 그룹(C5)도 그대로다.

## Implementer 검증 (작업 트리 기준, candidate 전)

| # | 결과 |
| --- | --- |
| R1 | 새 검사가 fixture 세 가지에서 `selected_task_transition_items() == tasks`를 확인했다(조작 대상 = 표시 목록 유지). 목록 밖 404 계약은 기존 task-0103 검사가 그대로 통과 |
| R2 | 새 검사가 선택 목록이 `task_view_sort_key` 순서인지 확인했다. 기존 task-0114 검사(`_test_task_view_attention_priority`) 그대로 통과 |
| R3 | fixture 1(NEEDS_APPROVAL 5, DOING 5, TODO 2, DONE 8): 표시 10, 미표시 `{"TODO": 2, "DONE": 8}`, 표시 + 미표시 = 전체 20, status별 표시 + 미표시 = fixture 수, TODO는 화면에 없음. fixture 2(유효하지 않은 기록 12, DONE 1): 미표시 `{"METADATA_REVIEW": 2, "DONE": 1}`. fixture 3(DONE 3): 미표시 없음. 응답 최상위 키는 기존 12개 + `task_view_counts` 하나 |
| R4 | A1 제외로 해당 없음 |
| R5 | `index.html` 첫 활성 탭이 Project Control 하나뿐이고 보이는 패널도 그것 하나, `app.js` 끝에서 `activateTab("tasks")` 호출, `activateTab`의 `tasks` 분기는 `loadOverview()` 그대로. 화면 줄은 node로 렌더해 수·상태·escape를 확인하고 버튼·`fetch(`가 없음을 확인 |
| R6 | 작업 트리 복사본 임시 worktree에서 변형 5종이 모두 새 검사에서 실패: A3 계산 제거(AssertionError), 응답 필드 제거(KeyError), 시작 불러오기 제거, 첫 탭 Chat 복귀, 화면 줄 제거(각 AssertionError). 변형 없는 기준 실행은 통과. 임시 worktree·fixture 잔여물 없음, 메인 checkout 실행 전후 같음 |
| R7 | Console smoke·browser shell self-test PASS, SOP validator PASS, discord-intake 137/0, `git diff --check` 통과, 변경 파일 5개(위 표)와 이 기록 |

실제 저장소의 `/api/overview` GET(서버를 잠깐 띄워 조회 후 종료, 쓰기 없음): `task_view_counts`는 `total` 113, `displayed` 10, `hidden` 103,
`hidden_by_status` `{"DONE": 103}`. task 파일은 템플릿을 빼면 114개인데, 기존 discovery 규칙이 비밀정보처럼 보이는 이름을 빼서
`task-0043-no-secrets-enforcement.md`가 Task View 후보에 없다(이번 변경 전부터의 동작, C 범위 밖이라 그대로 둠). 그래서 `total`은
Task View가 다루는 task 수다.

## Reviewer와 repair 이력

| 회차 | candidate | 결과 |
| --- | --- | --- |
| Reviewer 1 | `10f7904ca13532891a920cfdb44e410af521906a` | FINDINGS(minor 2, 모두 이 기록), `self_deviations` 없음: V1이 "전체 task 수"를 discovery 후보 수로 좁힌 것을 밝히지 않음(실제 113 대 114), "기록에 승인 범위를 반영한 뒤 구현" 조건 행이 없음. 코드 지적 없음 |
| repair 1 | (이 기록 수정) | Manager가 budget 안에서 진행. V1에 `total`의 정의와 task-0043 제외 사유, Owner 확인 사항임을 적고, 기록-후-구현 조건 행(O1)을 더했다. 코드·README·테스트는 바꾸지 않았다. `repair_count=1`(budget 1 소진) |
| Reviewer 2 | `76db4a4c9504e9a35dc9ecd207a53b1f54d93ec9` | PASS, findings 없음, `self_deviations` 없음. 미검증으로 밝힌 것: smoke·R6·R7 실행 결과, 실제 `/api/overview` 값과 파일 수, 브라우저 첫 화면, Console Start 순서, `total` 정의의 Owner 수용 |

## QA (candidate `76db4a4c9504e9a35dc9ecd207a53b1f54d93ec9`)

2026-10-17에 candidate를 detached 임시 worktree로 꺼내 실행하고 끝난 뒤 지웠다. 브라우저 확인은 같은 candidate worktree에서 Console을
`--no-browser`로 띄워 앱 내장 브라우저로 조회·탭 전환만 했고, 끝난 뒤 그 서버 프로세스만 종료했다. Start/Complete Confirm 등 쓰기는 하지 않았다.

| # | 결과 |
| --- | --- |
| R1·R2·R3·R5 | PASS. Console smoke·browser shell self-test 통과(새 `_test_task_view_hidden_counts_and_first_screen` 포함): 조작 대상 = 표시 목록, `task_view_sort_key` 순서, 표시 + 미표시 = 전체(status별 포함), 응답 키 기존 12개 + 1개, 첫 탭 고정 |
| R4 | 해당 없음(A1 제외) |
| R6 | PASS. 변형 5종(A3 계산 제거, 응답 필드 제거, 시작 불러오기 제거, 첫 탭 Chat 복귀, 화면 줄 제거)이 모두 새 검사에서 실패. 변형 없는 기준 실행 통과, fixture 잔여물 없음, 메인 checkout 실행 전후 같음 |
| R7 | PASS. SOP validator PASS, discord-intake 137/0, `git diff --check`(baseline 대비) 통과, 변경 범위 6파일, `jarvis.bat`은 tree에 없음, 코드는 `10f7904` 대비 차이 0줄, C4 안내 문구 그대로, QA worktree 변경 없음 |
| 브라우저 | 첫 진입 시 활성 탭은 Project Control 하나, 보이는 패널은 `tab-tasks` 하나, overview 요청 1회, "Not shown: 103 of 113 Tasks (DONE 103). Read-only count; …" 한 줄과 "Displayed total: 10" 표시. Chat·Voice·Skills·History·Settings·Project Control 순 전환에서 각 탭과 패널만 보였고(Project Control 복귀 시 overview 재요청은 기존 동작), 브라우저 콘솔 오류 없음 |

실행 뒤 정리: QA worktree 삭제, 8790 listener·남은 Python 프로세스 없음, `%TEMP%\jarvis_worker_smoke_*` 39개 그대로.

## `total` 정의: Owner 조건부 수용과 확인 (원문)

```text
Owner 결정:

1. task-0162 QA 결과를 기록하고, task 기록 파일만 별도 checkpoint 커밋하는 것을 승인합니다.
2. `total`은 Task View 후보 집합 기준이라는 정의를 조건부 수용합니다. task-0043 제외 규칙을 포함해 API 필드와 UI 문구가 동일한 집합을 가리키는지 확인하세요. 기존 API의 `total` 의미를 변경해야 하는 상황이면 수정하지 말고 보고하세요.
3. 위 두 항목 확인 후 Console Complete Preview까지만 진행하세요.

제한:

* `jarvis.bat`은 열기·읽기·수정·스테이징·커밋하지 마세요.
* task-0162의 코드 변경은 수정하지 마세요.
* Complete Confirm, DONE 처리, DONE checkpoint, master-plan 수정, push는 별도 승인 전까지 하지 마세요.
* 작업 후 Git 상태와 커밋 범위를 보고하고 중단하세요.
```

확인 결과(코드 정적 확인과 메인 checkout HEAD `76db4a4`에서 Python으로 함수만 불러 읽기 전용 계산, 서버·쓰기 없음):

- 같은 집합: `overview_payload()`가 `discover_recent_items(("memory_tasks",), apply_caps=False)` → `project_task_view_items()`로 만든 하나의
  projection에서 `tasks`(앞 10개)와 `task_view_counts`(`total` = projection 수, `hidden` = 나머지)를 함께 만든다. UI는 같은 응답의
  `counts.total`·`counts.hidden`·`hidden_by_status`만 쓴다(`app.js` `taskViewHiddenCountsMarkup`). 실측: projection 113, `total` 113,
  `displayed` 10 = `tasks` 길이, `tasks` = projection 앞 10개, `hidden_by_status`는 projection 나머지 103건의 status 집계와 같다.
- task-0043 제외: discovery의 `SECRET_LIKE_NAME_PARTS`("secret" 등) 규칙으로 후보에서 빠진다. 템플릿을 뺀 task 파일 114개 중 projection에
  없는 것은 `task-0043-no-secrets-enforcement.md` 하나뿐이고 projection에만 있는 것은 없다. API의 `total`과 UI의 "of 113 Tasks", Task View
  선택이 모두 이 같은 집합을 가리킨다.
- 기존 의미 변경 없음: baseline의 `/api/overview`에는 `total` 필드가 없었다(`discovery.max_total_items`는 다른 상한 값으로 그대로).
  `task_view_counts`는 새 필드라 기존 API의 `total` 의미를 바꾸지 않는다. 따라서 수정할 것이 없고 코드는 바꾸지 않았다.
