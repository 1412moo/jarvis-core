# task-0081-console-verified-dead-code-removal

- id: `task-0081-console-verified-dead-code-removal`
- title: `Console 검증된 dead code 제거 (1단계)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-08 00:40 UTC`
- updated_at: `2026-09-08 00:40 UTC`
- summary: `task-0080 에서 REMOVE-SAFE 로 증명된 항목만 제거했다. 3파일에서 130줄을 순수 삭제했고 추가 코드는 한 줄도 넣지 않았다. 지시 목록의 import stat 은 제거하지 않았다 — 그 고아 판정은 path-safety cluster 3건을 함께 지울 때만 성립하는데 이번 범위는 그 3건을 명시적으로 보존하므로 stat 모듈이 여전히 살아 있다. 삭제 후 closure 재검증에서 2차 고아 0건, dangling 참조 0건을 확인했고 task-0078 safety guard 4종과 금지 패턴 튜플은 byte 단위로 그대로다. KEEP 기능 8종을 route 수준에서 직접 호출해 확인했다.`
- source_command: `task-0080 감사 결과 REMOVE-SAFE 항목 제거 지시`

## 기준선

HEAD `9fb588c` = `origin/main`. 3파일, **+0 / -130**. 순수 삭제.

## 삭제 목록

### `run_web_app.py` — 76줄

| # | 항목 | 줄 |
| --- | --- | ---: |
| 1 | `RESEARCH_COUNCIL_ROOT` sys.path 3줄 + `from research_council import` 6줄 + 공백 | 10 |
| 2 | `existing_path_chain_has_reparse_point` | 18 |
| 3 | `absolute_filesystem_path` | 6 |
| 4 | `memory_string_has_valid_unicode` | 12 |
| 5 | `_deep_copy_json` | 4 |
| 6 | `_canonical_json_fingerprint` | 9 |
| 7 | `_safe_positive_revision` | 8 |
| 8 | `read_overview_title` | 7 |
| 9 | `ROUTING_PRIORITY["memory_skills"]` | 1 |
| 10 | `JARVIS_LOCAL_STATE_DIR_ENV` | 1 |

### `run_smoke_tests.py` — 30줄

| # | 항목 | 줄 |
| --- | --- | ---: |
| 12 | `_run_fixture_git` | 15 |
| 13 | `main()` 미사용 지역변수 5개 | 15 |

### `web/app.js` — 24줄

| # | 항목 | 줄 |
| --- | --- | ---: |
| 14 | `overviewItemsMarkup` | 23 |
| 15 | `researchDetails` | 1 |

## 항목 11 `import stat` — 제거하지 않았다

지시서의 표현은 "위 삭제로 발생하는 고아 `import stat`" 이다.
task-0080 에서 그 고아 판정이 나온 것은 path-safety cluster **5개 전부**를 지우는
전제였다. 이번 범위는 그중 `filesystem_stat_is_reparse_point`,
`normalize_filesystem_path`, `is_path_inside_repo` 를 **명시적으로 보존**하도록
지시했으므로 전제가 성립하지 않는다.

현재도 `stat` 모듈은 살아 있다.

- `stat.S_ISLNK(...)` — 보존된 `filesystem_stat_is_reparse_point` 본문
- `getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", ...)` — 같은 함수
- `stat.S_IFDIR` — 보존된 self-test assert 의 fixture

(`overview_file_item` 의 `stat.st_size` 등은 `stat = path.stat()` 지역변수 shadowing 이라
모듈 사용이 아니다.)

지웠으면 `NameError` 로 self-test 가 즉시 깨졌을 것이다.
**task-0083 에서 cluster 3건을 지울 때 함께 제거해야 한다.**

## closure 재검증

| 검사 | `run_web_app.py` | `run_smoke_tests.py` |
| --- | --- | --- |
| `ast.parse` | OK | OK |
| dangling names | `__file__` 만 (런타임 builtin, task-0078 가드가 쓰는 live 참조) | 동일 |
| **still-unused top-level defs** | **NONE** | **NONE** |
| 이번 삭제로 새로 고아가 된 import | **NONE** | **NONE** |

`still-unused top-level defs = 0` 목표 달성 — 2차 고아를 남기지 않았다.

## reference 전수 확인

콘솔 전체(`*.py *.js *.html *.css *.json`)에서 삭제 대상 12개 이름의 잔여 참조 **각 0건**.
`RESEARCH_COUNCIL_ROOT`, `JARVIS_LOCAL_STATE_DIR_ENV`, `researchDetails`,
`overviewItemsMarkup` 포함.

`memory_skills` 문자열 잔여 4건은 전부 `run_smoke_tests.py` 의 task-0074 copy-drift
baseline 필터 주석·조건이다. 의도된 보존 대상이다.

## safety guard 보존

| 항목 | 상태 |
| --- | --- |
| `source = Path(__file__).read_text(encoding="utf-8")` | 1건 그대로 |
| `assert all(pattern not in source for pattern in forbidden_source_patterns)` | 1건 그대로 |
| `assert ("shell" + "=True") not in source` | 1건 그대로 |
| `assert "READ_ONLY_GIT_COMMANDS" in source` | 1건 그대로 |
| `assert "run_read_only_git" in source` | 1건 그대로 |
| `forbidden_source_patterns` 튜플 17줄 | `9fb588c` 와 **diff 0** |

## KEEP 기능 route 수준 확인

| 기능 | 결과 |
| --- | --- |
| `/api/status` | PASS — skills 5, registry_version 0.1 |
| `/api/skill` | PASS — 정상 조회 + unknown 404 |
| `/api/overview` | PASS — tasks 10건 발견 |
| project_control | PASS — card status=attention, workstreams 6, manager/director report 생성 |
| `/api/history` | PASS — commit 10건 |
| `/api/suggest-skill` | PASS — research_council 라우팅 |
| Voice Inbox | PASS — 한글 transcript 후보 생성 |
| create-local-task preview+confirm | PASS — 임시 디렉터리에만 파일 생성 |

task-transition 과 completion-evidence 는 `overview_file_item` 이
`path.relative_to(REPO_ROOT)` 를 하므로 저장소 밖 임시 디렉터리로는 actionable view 에
잡히지 않는다. 이 둘은 저장소 안 fixture 를 쓰는 smoke 의 전용 vertical slice
(`_test_task_transition_vertical_slice`, `_test_completion_evidence_vertical_slice`)
가 커버하며 이번 실행에서 통과했다.

## 검증 결과

| 검증 | 결과 |
| --- | --- |
| Console self-test | PASS |
| Console smoke + browser shell | PASS |
| canonical 전수 | 71/71 PASS |
| SOP | status=PASS |
| bot self-check | 92/92 PASS |
| discord-intake | 94/94 PASS |
| audit-chain | 7 passed, 0 failed |
| buzz-bridge | 37/37 PASS |
| discord-nl-intent | 35/35 PASS |
| check_no_secrets --self-test | failures=0, PASS |
| node --check | OK |
| git diff --check | clean |
| KEEP route probe | 13/13 PASS |

## 보존 확인

- `filesystem_stat_is_reparse_point` / `normalize_filesystem_path` / `is_path_inside_repo` 및 self-test assert — 그대로
- `read_overview_title_and_summary` — live caller 유지
- `.codex-review-*` CSS 전체 — 무변경 (task-0082)
- 항진 assert, `.jarvis-local` 중복 검사 — 무변경
- `skills.json` / README / master-plan / Research Council / Hermes / Discord — 무변경
- line ending — `run_web_app.py` CRLF, `run_smoke_tests.py`·`app.js` LF 유지

## 후속 후보 (이번 task 에 넣지 않음)

이번 삭제와 무관하게 `9fb588c` 시점부터 이미 미사용이던 import 들이다.
내 변경이 새로 만든 고아가 아님을 before/after 비교로 확인했다.

- `run_web_app.py`: `TASK_ALLOWED_METADATA`, `CompletionEvidenceWriteResult`,
  `TaskStatusTransitionResult`, `TemporaryDirectory`, `base64`, `math`, `uuid`
- `run_smoke_tests.py`: `SimpleNamespace`, `ValidationError`, `nullcontext`,
  `REQUIRED_FORBIDDEN_ACTIONS`, `build_scope_approval_binding`, `normalize_prompt_queue`

`from __future__ import annotations` 는 정적 분석의 구조적 false positive 이므로 제외한다.
