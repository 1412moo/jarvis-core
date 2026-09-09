# task-0105-task-view-disclosure-cleanup

- id: `task-0105-task-view-disclosure-cleanup`
- title: `죽은 TASK_VIEW_DISCLOSURE 삭제와 up-to-N drift 방지`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-09 12:21 UTC`
- updated_at: `2026-09-09 12:21 UTC`
- summary: `task-0104 결론에 따라 한 번도 참조된 적 없는 TASK_VIEW_DISCLOSURE 정의 4 줄을 삭제하고, 실제로 화면에 보이는 app.js 문장의 up to N 숫자가 OVERVIEW_MAX_ITEMS_PER_DIRECTORY 와 일치하는지 단언 하나를 붙였다. 상수는 도입 커밋에서부터 app.js 리터럴의 복제본으로 태어나 payload 에도 UI 에도 닿은 적이 없어 payload 는 삭제 전후 동일하고 화면 문구도 그대로다. 새 단언은 UI 문구를 고치면서 exact-text pin 은 맞추고 상한 상수는 두는 변형을 유일하게 잡는다. app.js 무변경, API shape 무변경.`
- source_command: `task-0104 조사 결론(C: 삭제 + drift guard)에 따른 실행 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`997398a`** = `origin/main` |
| 직전 작업 | task-0103 (Task View 안전 게이트 3 종 고정) |
| 변경 파일 | `run_web_app.py` · `run_smoke_tests.py` + 이 기록 |
| diff | +7 / −4 |

## 왜 삭제인가 (task-0104 근거 요약)

`TASK_VIEW_DISCLOSURE` 는 **연결이 끊긴 상수가 아니라 처음부터 연결된 적이 없는
상수**였다. `git log -S` 가 반환하는 커밋은 도입 커밋 `e1e0c0b`(2026-07-24) 하나뿐이고,
그 diff 에서 이름은 **정의 한 줄로만** 등장한다. 같은 커밋이 app.js 에 동일 문장을
리터럴로 넣었다.

```
run_web_app.py : +TASK_VIEW_DISCLOSURE = (        ← 정의뿐
web/app.js     : +<p class="muted">Shows up to 10 files ... not the full backlog.</p>
```

복구할 원래 연결이 없으므로 payload 에 싣는 선택지는 *복원*이 아니라 **새 API 계약을
만드는 일**이었다. 그리고 그럴 필요가 없다.

- `/api/overview` 는 이 정보를 이미 **구조화해 고지한다** —
  `discovery.max_items_per_directory` · `max_total_items` · `excluded`.
- 문서 참조 0 건. README · 루트 README · `docs/` 에서 `full backlog` · `up to 10 files`
  검색 결과 없음.
- app.js 의 형제 문단 3 개(읽기 전용 설명 · 이 문장 · Display order) 중 Python 짝이
  있는 것은 이 하나뿐이다. 이것만 서버에서 내려보내면 불일치가 줄지 않고 종류만 는다.

## 무엇을 바꿨나

### 삭제 (production, 4 줄)

```python
TASK_VIEW_DISCLOSURE = (
    "Shows up to 10 files selected by existing Recent Tasks discovery before "
    "task validation; this is not the full backlog."
)
```

참조 0, 동적 접근(`vars` · `getattr` · `dir`) 0, 테스트 0, 문서 0 이었으므로 삭제
위험이 없다.

### drift guard (test, 단언 1 개)

```python
assert (
    f"up to {run_web_app.OVERVIEW_MAX_ITEMS_PER_DIRECTORY} files" in app_js
)
```

기존 exact-text 단언 바로 뒤에 둔다. 기존 단언은 **문장 전체**를 고정하고, 새 단언은
그 문장 속 **숫자를 상한 상수에 묶는다.** 둘은 서로를 대신하지 않는다.

## 검증

| 항목 | 결과 |
| --- | --- |
| `TASK_VIEW_DISCLOSURE` 코드/문서 참조 | **0 건** |
| `/api/overview` 삭제 전후 | **동일** (live `working_tree_status` 제외 시 byte 동일) |
| `app.js` sha256 | **무변경** `6a1fff41070a4a74` |
| Console self-test | PASS |
| Console smoke | PASS |
| 전체 regression 9 종 sequential | 전부 exit=0 |
| `git diff --check` | clean |

payload 비교에서 유일하게 달라진 필드는 `repo.working_tree_status` 와
`project_control.project_cards[0].working_tree_status` 였다. 둘 다 live `git status`
출력이라 **작업 중인 편집 자체를 반영한 것**이지 삭제의 결과가 아니다. 그 두 필드를
제외하면 payload 는 완전히 동일하다.

## mutation probe

세 방향을 걸었고, **새 단언이 유일하게 잡는 것이 무엇인지** 를 분리해 확인했다.

| probe | 변형 | 결과 | 먼저 잡은 단언 |
| --- | --- | --- | --- |
| A | app.js 문구 `10 → 25` | exit=1 | **기존** exact-text pin |
| B | `OVERVIEW_MAX_ITEMS_PER_DIRECTORY` `10 → 25` | exit=1 | **기존** task-0103 `len(scope_statuses) == cap` |
| C | app.js 문구 `10 → 25` + exact-text pin 도 함께 갱신, 상한 상수는 유지 | exit=1 | **새 단언** (`run_smoke_tests.py:4743`) |

정직하게 적으면 A 와 B 는 기존 단언이 먼저 잡는다. 새 단언의 고유한 값은 **C** 다 —
UI 문구를 고치면서 pin 은 성실히 맞추고 상한 상수는 건드리지 않는, 가장 그럴듯한
copy 편집 시나리오다. 이 경우 기존 단언은 전부 통과하고 새 단언만 실패한다.

모든 probe 뒤 `app.js` · `run_web_app.py` · `run_smoke_tests.py` 를 byte-identical 로
복원했다.

## 규모

| 항목 | 값 |
| --- | --- |
| 추가 assertion | **1 개** |
| 삭제 assertion | **0 개** |
| 삭제 라인 | 4 줄 (죽은 상수 정의뿐) |
| 신규 helper · fixture | 없음 (기존 `app_js` 재사용) |

## 바꾸지 않은 것

| 대상 | 상태 |
| --- | --- |
| `web/app.js` | 무변경 (sha256 동일) |
| `/api/overview` shape · 필드 · 값 | 무변경 |
| UI 문구 | 무변경 |
| `OVERVIEW_MAX_ITEMS_PER_DIRECTORY` 등 상한 정책 | 무변경 |
| 기존 exact-text 단언 | 유지 |
| task-0097 ~ task-0104 | 무변경 |
