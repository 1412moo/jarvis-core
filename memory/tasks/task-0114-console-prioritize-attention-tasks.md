# task-0114-console-prioritize-attention-tasks

- id: `task-0114-console-prioritize-attention-tasks`
- title: `Task View selection을 recency 대신 display priority 기준으로 전환`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-09 16:37 UTC`
- updated_at: `2026-09-09 16:37 UTC`
- summary: `discovery 의 mtime cap 이 Task status 판정보다 먼저 돌아 오래된 NEEDS_APPROVAL 이 화면에서 완전히 사라졌다. 실제로 NEEDS_APPROVAL 6 건과 DOING 1 건이 안 보이는 채 DONE 10 건만 표시되고 Needs attention 은 0 이었다. discover_recent_items 에 apply_caps seam 을 추가해 Task 경로만 전체 후보를 받고, projection 결과에 기존 cap 을 적용해 selection 이 task_view_sort_key 를 따르게 했다. 표시 총량 10 과 cap 상수는 그대로이고 Recent Tasks group 은 mtime 의미를 유지한다. mutation 6 종 전부 새 테스트가 잡는다.`
- source_command: `task-0113 설계 + Owner DECISION 1/2 확정에 따른 구현 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`4f65a95`** = `origin/main` |
| 직전 작업 | task-0111 (dead helper 삭제) |
| 조사 근거 | task-0112 (BUG 확정) · task-0113 (design D 확정) |
| 변경 파일 | `run_web_app.py` · `web/app.js` · `run_smoke_tests.py` + 이 기록 |
| diff | +259 / −7 |

## Owner 결정

| 결정 | 확정 내용 |
| --- | --- |
| DECISION 1 — scan 범위 | Task View 는 `memory/tasks` 후보를 **전량 scan**. 단 파일당 read 는 `read_task_view_text` bounded contract 그대로, `OVERVIEW_SNIPPET_BYTES` 무변경 |
| DECISION 2 — 표시 총량 | **10 유지**. `OVERVIEW_MAX_ITEMS_PER_DIRECTORY` 값 무변경. attention 이 11 건 이상이어도 총량 10. selection 은 기존 `task_view_sort_key` 재사용 |

## 원인

Task View 는 자기 표시 순서를 명시한다 — metadata review, NEEDS_APPROVAL,
BLOCKED, ON_HOLD, FAILED, DOING, TODO, DONE. 그러나 그 순서는 **discovery 가
이미 넘겨준 것만 재배열**할 수 있었고, discovery 는 **파일 mtime** 으로 자른다.
그래서 오래된 NEEDS_APPROVAL 은 status 가 읽히기도 전에 탈락했다.

```
discover_recent_items(("memory_tasks",))   ← ① mtime 정렬 + cap 10 / total 50
  → project_task_view_items(...)           ← ② display_rank 우선순위 정렬
```

②의 우선순위가 ①에 의해 구조적으로 무력화된다.

실제 저장소에서 **NEEDS_APPROVAL 6 건 + DOING 1 건이 전부 보이지 않는 상태**로
`{completed: 10}` · `Needs attention: 0` 이 표시되고 있었다. 이는 문서가 이
surface 의 책임으로 규정한 바와 어긋난다 — README `"show … items needing
attention"`, `"listed under Needs attention so the owner can see it"`,
`docs/jarvis-console.md` `"Show approval-needed items"`.

history 상 이 cap 은 `e53d109`(2026-06-30) 에서 **일반 파일 대시보드용**으로
만들어졌고, Task 의미론은 3 주 뒤 `e1e0c0b` 이 그 위에 얹었다. "attention 도
recency 로 경쟁시킨다" 는 설계 결정의 흔적은 없다.

**두 cap 모두 풀어야 했다.** 7 건 중 6 건의 mtime rank 가 55~65 로
`OVERVIEW_MAX_TOTAL_ITEMS = 50` 밖이라, per-directory cap 만 풀면 1 건만 복구된다.

## 구현

### discovery — Task 를 모르는 seam 하나

```python
def discover_recent_items(..., apply_caps: bool = True) -> ...:
        items.extend(
            directory_items[:OVERVIEW_MAX_ITEMS_PER_DIRECTORY]
            if apply_caps else directory_items
        )
    ...
    return items[:OVERVIEW_MAX_TOTAL_ITEMS] if apply_caps else items
```

discovery 는 여전히 **후보만 공급**한다. Task status 판정은 한 줄도 들어가지
않았다(architectural constraint 준수).

### Task View — 전체를 보고 자기 순서로 자른다

```python
task_candidates = discover_recent_items(("memory_tasks",), apply_caps=False)
discovered_tasks = task_candidates[:OVERVIEW_MAX_ITEMS_PER_DIRECTORY]   # Recent Tasks 용
tasks = project_task_view_items(task_candidates)[:OVERVIEW_MAX_ITEMS_PER_DIRECTORY]
```

새 우선순위를 만들지 않았다. `TASK_VIEW_STATUS_RULES` 와 `task_view_sort_key`
`(display_rank, -updated_at, path)` 를 그대로 재사용한다.

### disclosure

기존 문구가 새 selection 과 맞지 않아 한 문장만 고쳤다.

```diff
-Shows up to 10 files selected by existing Recent Tasks discovery before task validation; this is not the full backlog.
+Shows up to 10 Tasks, attention first then most recently updated; this is not the full backlog.
```

task-0105 의 `up to {OVERVIEW_MAX_ITEMS_PER_DIRECTORY}` guard 와 exact-text pin 을
새 문구로 함께 옮겨 **guard 를 유지**했다.

## 현재 corpus 결과

93 건(NEEDS_APPROVAL 6 · DOING 1 · DONE 86) 기준.

| | before | after |
| --- | --- | --- |
| tasks length | 10 | 10 |
| NEEDS_APPROVAL | **0** | **6** |
| DOING | **0** | **1** |
| DONE | 10 | 3 |
| groups | `{completed: 10}` | `{needs_attention: 6, in_progress: 1, completed: 3}` |

선택된 10 건(순서 그대로).

```
 1. rank=10 NEEDS_APPROVAL task-0094-b1-dogfood-owner-decision.md
 2. rank=10 NEEDS_APPROVAL task-0036-cloud-llm-candidates.md
 3. rank=10 NEEDS_APPROVAL task-0034-local-team-manager-approval-boundary.md
 4. rank=10 NEEDS_APPROVAL task-0033-local-llm-team-manager.md
 5. rank=10 NEEDS_APPROVAL task-0032-chatgpt-team-manager-integration-research.md
 6. rank=10 NEEDS_APPROVAL task-0030-codex-chatgpt-team-manager-discord.md
 7. rank=40 DOING          task-0031-chatgpt-discord-claude-auto-collab-plan.md
 8. rank=60 DONE           task-0111-console-remove-dead-overview-filter-helper.md
 9. rank=60 DONE           task-0109-reports-filter-before-cap.md
10. rank=60 DONE           task-0107-recent-item-global-ordering.md
```

task-0113 이 계산한 expected selection 과 정확히 일치한다.

**부수 효과**: `task-0031`(DOING) 이 다시 Complete / Record Evidence 대상이 된다
(Complete-eligible 0 → 1). 정상 DOING task 의 조작 가능성이 복원된 것이며 의도한
방향이다.

## Recent Tasks group

`overview_payload` 의 두 소비자가 **의도적으로 다른 의미**를 갖게 되었다.

| 소비자 | 의미 | 정렬 |
| --- | --- | --- |
| `tasks` (Task View) | status priority 기반 최대 10 | `task_view_sort_key` |
| `recent_groups` 의 Recent Tasks | 기존 그대로 "가장 최근 파일" 최대 10 | 파일 mtime 내림차순 |

전체 scan 결과(93 건)가 recent group 에 노출되지 않도록 같은 후보 리스트의
**capped prefix** 를 넘긴다. 코드 주석과 테스트로 이 차이를 고정했다.

## 테스트

`_test_task_view_attention_priority()` 추가, `main()` 에서 호출. fixture 는
`overview_directory_by_key` 를 교체해 **실제 `/api/overview` 배선을 통과**시킨다
(알고리즘만이 아니라 wiring 까지 검증). `finally` 에서 원복·삭제.

| # | 사례 | 기대 |
| --- | --- | --- |
| 1 | 최신 DONE 10 + 오래된 NEEDS_APPROVAL 1 | 총 10, NEEDS_APPROVAL 이 **1 번**. 옛 방식이면 DONE 만 나온다는 것도 함께 고정 |
| 2 | DONE 10 + NEEDS_APPROVAL 12 | 총 10, 전부 attention, **초과 2 건 미표시** |
| 3 | 7 status 혼합 | 정확히 `task_view_sort_key` 순서. status 집합이 `TASK_VIEW_STATUS_RULES` 와 같은지도 단언 |
| 4 | 동일 `updated_at` | **path 오름차순** tie-break |
| 5 | invalid metadata | `metadata_review` rank 0 최상위, `invalid_text` reason 유지 |
| 6 | secret-like filename | discovery 에서 계속 제외 |
| 7 | mtime rank가 total cap 밖 (55 건 + 1) | 후보 > 50, NEEDS_APPROVAL 이 **1 번** |
| 11 | Recent Tasks group | 10 이하, mtime 내림차순, `task_view` 없음 |

live payload 로 추가 검증: `tasks` 가 `task_view_sort_key` 정렬 상태,
`selected_task_transition_items() == tasks`(task-0103), reports/checkpoints/
docs_examples 의 global ordering(task-0107)·report 필터(task-0109) 무변경.

## mutation probe

**6/6 CAUGHT.** 전부 `_test_task_view_attention_priority` 에서 실패한다
(2 번만 `_test_reports_filter_before_cap` 이 먼저 잡는다).

| 변형 | 결과 |
| --- | --- |
| task discovery cap 을 10 으로 되돌림 | CAUGHT |
| 최종 projection cap 제거 | CAUGHT |
| `task_view_sort_key` 정렬 제거 | CAUGHT |
| attention priority → mtime priority | CAUGHT |
| total discovery cap 만 재적용 | CAUGHT (사례 7 이 잡는다) |
| secret-like filename 필터 제거 | CAUGHT |

첫 시도에서 1 · 4 · 5 가 통과해 버렸다. fixture 가 `overview_payload` 를 거치지
않고 알고리즘만 직접 호출하고 있었기 때문이다. 테스트를 실제 배선을 지나가도록
고쳐 닫았다. 5 번은 fixture 가 total cap(50) 을 넘지 않아 놓쳤고, 55 건짜리
사례 7 을 추가해 닫았다.

probe 후 `run_web_app.py` 를 byte-identical 로 복원했다.

## 성능

| 단계 | before | after | 증가 |
| --- | ---: | ---: | ---: |
| Task projection 후보 | 10 | 93 | +83 |
| bounded read 횟수 | 10 | 92 | +82 |
| Task projection 시간 | 67 ms | 90 ms | **+23 ms** |

`/api/overview` 전체는 393 ms(git subprocess 가 지배적이라 편차가 크다).
파일당 read 는 bounded 그대로이고, 새 parser 는 만들지 않았으며, 이중 read 도
없다. reports/checkpoints/docs discovery 는 영향이 없다.

비용은 corpus 크기에 선형(≈0.26 ms/건)이므로 corpus 가 크게 자라면 재검토가
필요하다 — 이번 범위에서는 조치하지 않았다.

## 검증

| 항목 | 결과 |
| --- | --- |
| Console self-test | PASS |
| Console smoke | PASS |
| writer smoke (`orchestrator/discord-intake`) | exit=0 |
| 전체 regression 9 종 sequential | 전부 exit=0 |
| `git diff --check` | clean |
| fixture 잔여물 | 없음 |
| API payload 키 · item 키 · task_view 키 | **무변경** |
| `/api/history` · `/api/status` | 200, 키 무변경 |

## 바꾸지 않은 것

| 대상 | 상태 |
| --- | --- |
| `OVERVIEW_MAX_ITEMS_PER_DIRECTORY` · `OVERVIEW_MAX_TOTAL_ITEMS` 값 | 무변경 |
| `TASK_VIEW_STATUS_RULES` · `task_view_sort_key` | 무변경 |
| status values · transition matrix · completion evidence 규칙 | 무변경 |
| reports · checkpoints · docs/examples · history discovery | 무변경 |
| API schema | 무변경 |
| 그 밖의 UI · 문서 | 무변경 |
| task-0098 · 0103 · 0107 · 0109 · 0111 계약 | 무변경 |

## 남겨 둔 것

`selected_task_transition_items` 의 **non-default `tasks_dir` 분기**는 여전히
mtime cap 후 projection 한다. 이 분기는 테스트 fixture 전용이고 production 은
default 분기(= 새 selection)를 쓰므로 사용자 영향은 없다. 이를 맞추면 task-0103
의 선택 범위 테스트 기대값이 바뀌므로 이번 범위에서 손대지 않았다. **후속 task
후보로 남긴다.**
