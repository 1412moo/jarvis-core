# task-0107-recent-item-global-ordering

- id: `task-0107-recent-item-global-ordering`
- title: `Recent / History 목록을 디렉터리 결합 후 전체 최신순으로 정렬`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-09 13:07 UTC`
- updated_at: `2026-09-09 13:07 UTC`
- summary: `discover_recent_items 와 discover_history_items 가 디렉터리별로 정렬한 뒤 결합 리스트를 재정렬하지 않아 Recent 목록이 recency 순이 아니었다. UI 가 각 항목의 수정 시각을 표시하므로 어긋난 순서가 그대로 보였고 Docs / Examples 25 건에서 역전 쌍이 89 개였다. 총량 상한도 최신순이 아니라 디렉터리 순으로 잘렸고 early break 는 뒤쪽 디렉터리를 통째로 건너뛸 수 있었다. 결합 후 전체 정렬을 넣고 break 를 제거했다. 파일 선택 집합과 API shape 는 그대로이고 순서만 바뀐다. mutation 3 종 모두 새 테스트가 잡는다.`
- source_command: `task-0106 ISSUE-1 수정 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`2450815`** = `origin/main` |
| 직전 작업 | task-0105 (죽은 disclosure 상수 정리) |
| 변경 파일 | `run_web_app.py` · `run_smoke_tests.py` + 이 기록 |
| diff | +123 / −4 |

## 원인

두 discovery 함수가 **디렉터리별로만** `(modified, path)` 내림차순 정렬하고,
결합한 리스트는 그대로 반환했다.

```python
directory_items.sort(key=..., reverse=True)
items.extend(directory_items[:OVERVIEW_MAX_ITEMS_PER_DIRECTORY])
if len(items) >= OVERVIEW_MAX_TOTAL_ITEMS:
    break
return items[:OVERVIEW_MAX_TOTAL_ITEMS]   # ← 결합 리스트 재정렬 없음
```

결과는 recency 순이 아니라 **디렉터리 순으로 묶인 목록**이었다. 수정 전 실측:

| 그룹 | 항목 | 순서 역전 쌍 | 최악 |
| --- | ---: | ---: | --- |
| Recent Tasks | 10 | 0 | 단일 디렉터리 |
| Recent Reports | 10 | 5 | 78 일 더 최신인 항목이 3 칸 아래 |
| Recent Checkpoints | 2 | 1 | 31 일 |
| Recent Docs / Examples | 25 | **89** | `jarvis_console/README.md` 가 103 일 더 최신인데 11 칸 아래 |
| `/api/history` | 6 | 정렬 안 됨 | — |

세 가지가 겹쳐 실제 결함이 된다.

1. 그룹 제목이 `Recent ...` 다.
2. UI 가 각 항목의 **수정 시각을 실제로 출력한다**([app.js:824](../../apps/jarvis-console/web/app.js)).
   어긋난 순서가 화면에 그대로 보인다.
3. recency 정렬 **의도가 코드에 있다** — 디렉터리별 `reverse=True` 가 그 증거이고,
   같은 파일의 `project_task_view_items` 는 결합 리스트를 제대로 재정렬한다.

부작용이 둘 더 있었다. 총량 상한이 "가장 오래된 것"이 아니라 **"뒤쪽 디렉터리 것"**
을 잘랐고, `break` 는 뒤쪽 디렉터리를 **스캔 자체를 건너뛸** 수 있었다.

## 수정 (production)

두 함수 모두 동일하게 4 줄이 오간다.

```diff
         items.extend(directory_items[:OVERVIEW_MAX_ITEMS_PER_DIRECTORY])
-        if len(items) >= OVERVIEW_MAX_TOTAL_ITEMS:
-            break
+    items.sort(key=lambda item: (item["modified"], item["path"]), reverse=True)
     return items[:OVERVIEW_MAX_TOTAL_ITEMS]
```

정렬 키는 같은 함수가 디렉터리별로 이미 쓰던 것을 그대로 쓴다.

`break` 제거는 관련 없는 정리가 아니라 **수정의 일부**다. break 가 남아 있으면
뒤쪽 디렉터리의 항목이 비교 대상에 오르기도 전에 사라져 전체 정렬이 의미를 잃는다.
현재 키 집합은 최대 5 개 디렉터리 × 10 = 50 = 상한이라 break 가 실제로 발동하지
않으므로, 제거의 오늘자 동작 변화는 **없다.** 앞으로 6 번째 디렉터리가 추가될 때
같은 버그가 재발하는 것을 막는다.

디렉터리별 수집·디렉터리별 상한·필터·scope 정책은 **무변경**이다.

## contract 영향

| 항목 | 결과 |
| --- | --- |
| `/api/overview` payload 키 | 무변경 |
| `/api/history` payload 키 | 무변경 |
| item 키 15 개 | 무변경 |
| **선택된 파일 집합** | **네 그룹 모두 동일** (아래) |
| 순서 | reports · checkpoints · docs_examples 변경, tasks 무변경 |
| UI 코드 | 무변경 |

수정 전 알고리즘을 그대로 재현해 비교한 결과다.

| 그룹 | old n | new n | 파일 집합 동일 | 순서 변경 |
| --- | ---: | ---: | --- | --- |
| tasks | 10 | 10 | 예 | 아니오 (단일 디렉터리) |
| reports | 12 | 12 | 예 | 예 |
| checkpoints | 2 | 2 | 예 | 예 |
| docs_examples | 25 | 25 | 예 | 예 |

즉 현재 데이터에서는 **순서만 바뀌고 무엇이 보이는지는 바뀌지 않는다.** 선택 집합이
달라지는 것은 총량 상한이 실제로 걸릴 때뿐이고, 그때 달라지는 방향이 바로 이 수정의
목적이다.

## 테스트

`_test_recent_item_ordering()` 하나를 추가하고 `main()` 에서 호출한다.
단언 13 개, 삭제 0 개.

**실제 payload** — 요구된 1~4 번.

- `/api/overview` 의 recent_groups 4 개 전부 `modified` 내림차순
- `overview["reports"]` · `["checkpoints"]` · `["docs_examples"]` 내림차순
- `/api/history` 의 `checkpoint_docs` · `related_items` 내림차순

`overview["tasks"]` 는 **의도적으로 제외**했다. 그 목록은 파일 recency 가 아니라
Task View 의 표시 순서(`task_view_sort_key`)를 따르므로 다른 계약이다.

**fixture** — 요구된 5~6 번. 실제 저장소 데이터는 "우연히 나온 순서"만 보여주므로
규칙을 증명하지 못한다. 그래서 `overview_directory_by_key` 를 임시 교체하고
`recent-order-test-fixture/` 아래에 시간 역전 fixture 를 만든다.

| case | 구성 | 기대 |
| --- | --- | --- |
| 시간 역전 | 3 디렉터리, mtime `100 / 300 / 200` | 결과가 `300, 200, 100` (= B, C, A) |
| 상한 경계 | 6 디렉터리 × 12 파일, 뒤쪽 디렉터리가 최신 | 50 건 반환, 전체 내림차순, 최신 항목이 첫 번째, **가장 오래된 디렉터리가 잘리고 마지막 디렉터리는 남음**, 각 디렉터리에서 남은 것이 그 디렉터리의 최신 10 건 |

두 번째 case 는 디렉터리당 파일 수를 디렉터리 상한보다 크게 잡아, 디렉터리별 정렬이
"그 디렉터리의 최신"을 고르는지까지 본다(`min(kept) > max(dropped)`, 5 개 디렉터리에서
실제로 검사됨). fixture 는 `finally` 에서 제거하고 `overview_directory_by_key` 를
원복한다.

## mutation probe

| 변형 | 결과 | 실패 지점 |
| --- | --- | --- |
| 결합 후 전체 sort 두 개 모두 제거 | **CAUGHT** | `AssertionError: Recent Reports` (실제 payload 단언) |
| 디렉터리별 sort 두 개 모두 제거 | **CAUGHT** | 상한 fixture `capped[0]["modified"] == newest_stamp` |
| `break` 복원 (recent 쪽) | **CAUGHT** | 상한 fixture `capped[0]["modified"] == newest_stamp` |

정직하게 적으면 2 번과 3 번은 둘 다 상한 fixture 의 "최신이 첫 번째" 단언에서
먼저 걸린다. 디렉터리별 최신 유지 단언은 그보다 뒤에 있어 이번 세 변형에서는
발동하지 않았지만, 5 개 디렉터리에 대해 실제로 평가되므로 비어 있는 단언은 아니다.

모든 probe 뒤 `run_web_app.py` 를 byte-identical 로 복원했다.

## 검증 결과

| 항목 | 결과 |
| --- | --- |
| Console self-test | PASS |
| Console smoke | PASS |
| 전체 regression 9 종 sequential | 전부 exit=0 |
| `git diff --check` | clean |
| fixture 잔여물 | 없음 |
| 삭제된 단언 | 0 개 |

## 바꾸지 않은 것

| 대상 | 상태 |
| --- | --- |
| API payload shape · 필드 | 무변경 |
| `web/app.js` | 무변경 |
| discovery scope · 필터 · 디렉터리별 상한 | 무변경 |
| `OVERVIEW_MAX_TOTAL_ITEMS` · `OVERVIEW_MAX_ITEMS_PER_DIRECTORY` 값 | 무변경 |
| `project_task_view_items` 및 Task View 정렬 | 무변경 |
| task-0097 ~ task-0106 | 무변경 |

## 남겨 둔 것

task-0106 의 GAP-2(`reports` 에 대한 cap-then-filter — 상한을 먼저 적용하고 타입
필터를 나중에 적용)는 이번 범위 밖이라 손대지 않았다. 현재 데이터에서는 재현되지
않는 잠재 결함이며, 같은 함수를 다루므로 후속 task 로 남긴다.
