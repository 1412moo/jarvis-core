# task-0109-reports-filter-before-cap

- id: `task-0109-reports-filter-before-cap`
- title: `reports 타입 필터를 디렉터리 상한 이전으로 이동`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-09 13:35 UTC`
- updated_at: `2026-09-09 13:35 UTC`
- summary: `reports 경로가 discover 후 상한을 먼저 적용하고 item_type 필터를 나중에 걸어, 한 디렉터리의 최신 10 건에 비-report 가 섞이면 디스크상 report 10 건이 8 건으로 줄어 표시됐다. discover_recent_items 에 item_types 인자를 추가해 name_contains 와 같은 자리에서 디렉터리 상한 이전에 걸도록 고쳤다. 상한 이전에 이미 모든 후보의 overview_file_item 을 만들므로 추가 파일 읽기는 없다. 실제 저장소에서는 어느 디렉터리도 상한에 닿지 않아 payload 무변경이고 잠복 결함만 닫혔다. tasks checkpoints docs_examples 경로는 무변경이다.`
- source_command: `task-0108 VERDICT(BUG 잠복)에 따른 최소 수정 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`5d2289c`** = `origin/main` |
| 직전 작업 | task-0107 (Recent/History 전체 최신순 정렬) |
| 변경 파일 | `run_web_app.py` · `run_smoke_tests.py` + 이 기록 |
| production diff | +19 / −5 |
| test diff | +99 / −0 |

착수 전 read-only 로 현재 HEAD 구현이 task-0108 분석과 일치함을 재확인했다.

## 원인

```python
reports = filter_overview_items(
    discover_recent_items(("reports", "research_examples", "daily_ai_radar_examples")),
    {"report"},
)
```

`discover_recent_items` 는 디렉터리별로 후보를 모아 정렬한 뒤 **상한 10 을 적용**하고,
필터는 **그 뒤에** 걸렸다. 따라서 비-report 파일이 상한 자리를 소비하면 디스크에 있는
report 가 화면에서 사라진다.

비-report 가 섞이는 경로는 실재한다.

- `infer_item_type` 은 `if "checkpoint" in stem` 을 `if directory_key == "reports"` **보다
  먼저** 검사한다. `reports/` 안의 checkpoint 이름 파일은 `report` 가 아니다.
- `research_examples` · `daily_ai_radar_examples` 는 stem 에 `report` 가 있는 것만
  `report` 이고 나머지는 `example` 이다. 현재 두 디렉터리 모두 `example` 을 담고 있다.

즉 **discovery 가 report-only scope 를 보장하지 않으며 필터가 실제로 작동한다.**
같은 함수의 checkpoints 경로는 이미 `name_contains` 를 discovery **내부**에서 걸어
filter-then-cap 을 택하고 있었다.

## 수정 (production, +19 / −5)

`checkpoints` 가 쓰던 in-discovery 필터 패턴을 그대로 따랐다.

```python
def discover_recent_items(
    directory_keys: tuple[str, ...],
    name_contains: str = "",
    item_types: set[str] | None = None,
) -> list[dict[str, Any]]:
    ...
            item = overview_file_item(path, directory)
            if item_types is not None and item["item_type"] not in item_types:
                continue
            directory_items.append(item)
        directory_items.sort(...)
        items.extend(directory_items[:OVERVIEW_MAX_ITEMS_PER_DIRECTORY])
```

호출부.

```python
reports = discover_recent_items(
    ("reports", "research_examples", "daily_ai_radar_examples"),
    item_types={"report"},
)
```

**추가 I/O 는 없다.** `discover_recent_items` 는 상한 적용 전에 이미 디렉터리의 모든
후보에 대해 `overview_file_item` 을 만든다(= 각 파일 앞 4096 byte 를 읽는다).
필터 위치만 옮긴 것이므로 읽는 파일 수는 그대로다.

## 검증 결과

fixture 3 종을 수정된 경로(`item_types={"report"}`)로 직접 확인했다.

| case | 구성 | 수정 전 | 수정 후 |
| --- | --- | ---: | ---: |
| A | `reports/` 12 건, 최신 2 건이 checkpoint 이름 | 8 | **10** |
| B | `research_examples` 12 건, 최신 2 건이 non-report | 8 | **10** |
| C (대조) | report 8 건만, 상한 미도달 | 8 | 8 |

실제 저장소 payload 는 **무변경**이다. `reports` 10 건, 전부 `item_type == "report"`,
전체 최신순. 어느 기여 디렉터리도 상한 10 에 닿지 않기 때문이며(디스크 기준
`reports` 8 · `research_examples` 2 · `daily_ai_radar_examples` 2), 이번 수정은
**잠복 결함만 닫는다.**

## 테스트 (+99, 단언 20 개 추가 · 삭제 0)

`_test_reports_filter_before_cap()` 를 추가하고 `main()` 에서 호출한다. fixture 는
`REPO_ROOT` 아래 임시 디렉터리에 만들고 `overview_directory_by_key` 를 임시 교체한 뒤
`finally` 에서 원복·삭제한다(task-0107 테스트와 같은 방식).

| 구분 | 내용 |
| --- | --- |
| A | `reports/` 상한 초과 → report 10 건, 전부 `report` 타입, 상한 이하, 최신순, **디스크상 report 이름 집합과 정확히 일치**(누락 0). 같은 디렉터리를 필터 없이 읽으면 비-report 2 건이 상한을 소비하는 것도 함께 고정 |
| B | `research_examples` 상한 초과 → report 10 건 |
| C | 상한 미도달 → 8 건, 필터 유무 결과 동일 |
| D | 다른 경로 무변경 — checkpoints 는 여전히 이름 필터가 discovery 내부에서 동작, docs_examples 는 타입 무필터, **tasks 는 cap-then-validate 유지**(recent group 이 검증 이전 슬라이스이고 Task View projection 이 그보다 넓어지지 않음, group 항목에 `task_view` 없음) |

## mutation probe

| 변형 | 결과 | 실패 지점 |
| --- | --- | --- |
| 타입 필터를 다시 **상한 뒤로** 이동 | **CAUGHT** (exit=1) | case A `assert len(found) == cap` |
| `item_types` 필터를 완전히 무력화 | **CAUGHT** (exit=1) | case A |

두 probe 뒤 `run_web_app.py` 를 byte-identical 로 복원했다.

## 전체 검증

| 항목 | 결과 |
| --- | --- |
| Console self-test | PASS |
| Console smoke | PASS |
| writer smoke (`orchestrator/discord-intake`) | exit=0 |
| 전체 regression 9 종 sequential | 전부 exit=0 |
| `git diff --check` | clean |
| fixture 잔여물 | 없음 |
| 삭제된 단언 | 0 개 |

## filter_overview_items

이번 수정으로 **호출부가 0 개**가 되었다(정의만 `run_web_app.py:1399` 에 남음).
smoke suite 가 이 함수를 직접 호출하는 테스트도 없다.

**이번 task 에서는 삭제하지 않는다.** production bug 수정과 dead-code cleanup 을
분리하기 위해서이며, task-0104/0105 가 `TASK_VIEW_DISCLOSURE` 를 다룬 것과 같은
절차(조사 → 결정 → 삭제)를 따르는 것이 맞다. **후속 task 후보로 남긴다.**

## 바꾸지 않은 것

| 대상 | 상태 |
| --- | --- |
| `OVERVIEW_MAX_ITEMS_PER_DIRECTORY` · `OVERVIEW_MAX_TOTAL_ITEMS` 값 | 무변경 |
| 디렉터리 목록 · `infer_item_type` 규칙 | 무변경 |
| task-0107 전체 recency 정렬 | 무변경 |
| tasks discovery 의 cap-then-filter · actionable selection gate | 무변경 |
| checkpoints 의 discovery 내부 필터 | 무변경 |
| docs_examples 경로 | 무변경 |
| API response shape · `web/app.js` | 무변경 |
| `filter_overview_items` 정의 | 무변경 (호출부만 0) |
| task-0097 ~ task-0108 | 무변경 |
