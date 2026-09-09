# task-0111-console-remove-dead-overview-filter-helper

- id: `task-0111-console-remove-dead-overview-filter-helper`
- title: `Remove Dead Overview Filter Helper`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-09 14:41 UTC`
- updated_at: `2026-09-09 14:41 UTC`
- summary: `task-0110 이 SAFE TO DELETE 로 확정한 filter_overview_items 를 삭제했다. task-0109 가 reports 필터를 discovery 내부 item_types 로 옮기면서 유일한 호출부가 사라졌고, 도입 커밋 bc5bde4 가 함수와 그 호출부를 함께 만들었으므로 처음부터 reports 전용 helper 였다. run_web_app.py 에서 8 줄 삭제이고 추가는 0 줄이며 테스트 문서 UI 는 손대지 않았다. 삭제 전후 status overview history payload 를 비교해 삭제로 인한 차이가 없음을 확인했고 self-test smoke regression 9 종 writer smoke 전부 통과했다.`
- source_command: `task-0110 VERDICT(A. SAFE TO DELETE)에 따른 dead code 삭제 지시`

## Status

DONE

## Summary

task-0110 에서 SAFE TO DELETE 로 확정된 `filter_overview_items` dead code 를
삭제했다.

## Background

task-0109 가 reports filtering 을 discovery 내부의 `item_types={"report"}` 로
옮기면서 이 함수의 **유일한 호출부가 제거**되었다. 이어진 task-0110 read-only
audit 이 다음을 확인했다.

| 확인 항목 | 결과 |
| --- | ---: |
| 실제 호출부 | 0 |
| Python 직접 · 간접 참조 | 0 |
| smoke / regression 직접 호출 | 0 |
| docs · README 참조 | 0 |
| JS 참조 | 0 |
| 동적 참조 (`getattr` · `vars` · `dir` · `importlib` · `globals()[...]`) | 0 |
| `__all__` · star-import | 없음 |

git history 상 이 심볼의 생애는 커밋 두 개뿐이었다. `bc5bde4`(2026-06-30) 가
**함수와 유일한 호출부를 같은 커밋에서** 만들었고 — 같은 커밋에서 checkpoints 는
discovery 내부 필터로, docs_examples 는 무필터로 작성했으므로 처음부터 공용
helper 가 아니라 reports 전용이었다 — `094404e`(task-0109) 가 그 호출부를
제거했다. `item_types=None` 기본값은 생애 전체에서 한 번도 호출된 적이 없다.

task-0110 은 런타임에서 심볼을 제거한 뒤 `/api/status` · `/api/overview` ·
`/api/history` payload 가 동일하고 `run_self_test()` 가 통과하는 것까지 확인했다.
이번 작업은 그 결과를 파일에 반영한 것이다.

## Change

- `apps/jarvis-console/run_web_app.py`
- `filter_overview_items` 삭제 (함수 6 줄 + 구분 빈 줄 2 줄)
- **8 lines deleted**
- **production additions 0**
- tests unchanged
- API / UI unchanged

```diff
-def filter_overview_items(items: list[dict[str, Any]], item_types: set[str] | None = None) -> list[dict[str, Any]]:
-    """Filter already discovered read-only items without touching the filesystem."""
-
-    if item_types is None:
-        return list(items)
-    return [item for item in items if item["item_type"] in item_types]
-
-
```

적용 스크립트에 가드를 걸어 삭제 전 심볼 등장 1 회, 삭제 라인 수 정확히 8,
삭제 후 심볼 0 회, 그리고 이웃한 `discover_history_items` 와 `recent_group` 사이
빈 줄이 정확히 2 줄로 유지되는지 확인했다.

## Validation

| 항목 | 결과 |
| --- | --- |
| Console self-test | PASS |
| Console smoke | PASS |
| regression 9 종 sequential | PASS (전부 exit=0) |
| writer smoke (`orchestrator/discord-intake`) | PASS |
| `git diff --check` | PASS (clean) |
| 삭제 후 reference 검색 | production · test · docs · JS 실제 참조 **0** |
| fixture 잔여물 | 없음 |

API 비교는 삭제 전 payload 를 저장해 두고 필드 단위로 대조했다.

| endpoint | status code | payload keys | 차이 나는 필드 |
| --- | --- | --- | --- |
| `/api/status` | 동일 | 동일 | **없음 (byte-identical)** |
| `/api/overview` | 동일 | 동일 | `repo.working_tree_status` · `project_control.project_cards[0].working_tree_status` |
| `/api/history` | 동일 | 동일 | `repo.working_tree_status` |

차이 나는 필드는 전부 live `git status` 출력이다. 작업 중 파일이 수정된 상태를
반영한 것이지 **삭제로 인한 behavior 변화가 아니다.** 그 필드를 제외하면 세
endpoint 모두 완전히 동일하다.

reference 검색 결과 남은 문자열은 task 기록의 서술적 언급뿐이며 코드 참조는 없다.

## Git

- Commit: `b3c34cb72dff38db17105051f41313c2c7636cfc`
- Message: `refactor(console): remove dead overview filter helper (task-0111)`
- Pushed: yes (`094404e..b3c34cb  main -> main`)
- HEAD == origin/main: yes
- tracked working tree: clean
- untracked baseline: 24
- merge: 하지 않음

## Scope

이번 task 에서는 dead helper 삭제 외의 변경을 하지 않았다.

| 대상 | 상태 |
| --- | --- |
| `discover_recent_items` · `item_types` 파라미터 | 무변경 |
| reports 호출부 · `infer_item_type` | 무변경 |
| `OVERVIEW_MAX_ITEMS_PER_DIRECTORY` · `OVERVIEW_MAX_TOTAL_ITEMS` | 무변경 |
| tasks · checkpoints · docs_examples discovery | 무변경 |
| API payload · `web/app.js` | 무변경 |
| 테스트 기존 assertion | 무변경 |
| 문서 · README | 무변경 |
| 그 밖의 dead-code cleanup · formatter · refactor | 없음 |

작업 중 추가 개선사항은 발견하지 않았다.
