# task-0083-console-path-safety-orphan-removal

- id: `task-0083-console-path-safety-orphan-removal`
- title: `Console path-safety 고아 클러스터 및 잔여 self-test 지역변수 제거 (3단계)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-08 01:10 UTC`
- updated_at: `2026-09-08 01:10 UTC`
- summary: `dead-code cleanup 3단계이자 테스트를 함께 고치는 유일한 단계였다. production 호출이 0이고 self-test assert 로만 살아 있던 path-safety 함수 3개와 그 assert 4건, task-0081 에서 조건 불성립으로 남겨둔 import stat, task-0071 이 남긴 run_self_test 미사용 지역변수 6개를 제거했다. memory_skills 잔재 부재를 증명하는 tripwire assert 와 지시상 보류된 항진 assert 는 전부 보존했다. task-0078 source safety guard 는 mutation probe 7종으로 여전히 작동함을 확인했다. 2파일 +0 -68.`
- source_command: `task-0080 감사 3단계 — path-safety cluster 및 테스트 수정 동반 항목 제거 지시`

## 기준선

HEAD `5431498` = `origin/main`, tracked 변경 0에서 시작.
2파일, **+0 / -68**. 순수 삭제.

## 삭제 내용

### `run_web_app.py` — 59줄

| 항목 | 줄 |
| --- | ---: |
| `normalize_filesystem_path` / `filesystem_stat_is_reparse_point` / `is_path_inside_repo` | 26 |
| 두 함수의 self-test assert + `fake_reparse_stat` fixture | 7 |
| `import stat` (연쇄 고아) | 1 |
| `preview_request` 미사용 지역변수 | 10 |
| `invalid_preview_payloads` + `endpoint_candidate_id` + `endpoint_timestamp` | 13 |
| `fixed_candidate_id` + `fixed_timestamp` | 2 |

### `run_smoke_tests.py` — 9줄

`run_web_app.is_path_inside_repo` assert 3줄,
`fake_reparse_stat` fixture 5줄, `filesystem_stat_is_reparse_point` assert 1줄.

## `import stat` — 이번에 조건이 성립했다

task-0081 에서는 제거하지 않았다. 그 고아 판정은 path-safety cluster 를 함께
지울 때만 성립하는데 당시 범위가 그 3개를 명시적으로 보존했기 때문이다.
이번에 3개와 마지막 사용처(`stat.S_IFDIR` fixture)가 사라지면서 조건이 성립했다.

(`overview_file_item` 의 `stat.st_size` 등은 `stat = path.stat()` 지역변수
shadowing 이라 모듈 사용이 아니다.)

`import os` 는 유지했다 — `os.environ` 이 `run_read_only_git` 에서 살아 있다.

## 보안 판단 — 회귀가 아닌 이유

지운 3개는 일반적인 symlink/reparse-point 방어 헬퍼다. 이름만 보면 지우는 것이
위험해 보이므로 근거를 남긴다.

1. **production 호출 0.** task-0080 의 동적 probe 에서 세 함수를 각각 제거했을 때
   실패 지점이 전부 self-test assert 줄이었다. route 경로에서는 한 번도 걸리지 않았다.
2. **원래 memory_skills 전용이었다.** `83363ee`(harden memory skills candidate writer)
   가 도입했고 assert 가 검사하던 경로도
   `.jarvis-local/memory-skills/candidates` 다. 그 디렉터리는 존재하지 않으며
   존재하지 않음을 검사하는 tripwire 가 따로 살아 있다.
3. **현재 write 경로는 자체 containment 를 갖는다.** `task_file_writer.py` 의
   3개 write 함수(`transition`, `execution result`, `completion evidence`) 전부
   `tasks_dir.resolve()` 와 `target_path.parent != resolved_tasks_dir` 로
   `task_path_not_direct_child` 를 반환한다. `.resolve()` 는 symlink 를 따라가므로
   탈출 시도는 부모 비교에서 걸린다.

즉 방어가 사라지는 것이 아니라, 쓰이지 않는 두 번째 사본이 사라진다.

## 보존 확인

| 대상 | 상태 |
| --- | --- |
| tripwire `not APP_ROOT/"state"` | run_web_app 2건, smoke 2건 유지 |
| tripwire `not REPO_ROOT/".jarvis-local"` | run_web_app 3건, smoke 4건 유지 |
| tripwire `not APP_ROOT/"examples/memory-skills-sample.json"` | 양쪽 유지 |
| tripwire `not REPO_ROOT/"memory/skills"` | 양쪽 유지 |
| 항진 assert (`before_* == after_*`) | 4건 전부 유지 — 지시상 별도 판단 |
| `.jarvis-local` 중복 검사 | 유지 — 지시상 별도 판단 |
| 기존 미사용 import 13건 | 무변경 |

## closure 재검증

| 검사 | `run_web_app.py` | `run_smoke_tests.py` |
| --- | --- | --- |
| `ast.parse` | OK | OK |
| dangling names | `__file__` 만 (런타임 builtin) | 동일 |
| **still-unused top-level defs** | **NONE** | **NONE** |
| 새로 고아가 된 import | **NONE** (`stat` 는 이번에 함께 제거) | **NONE** |
| 미사용 지역변수 | `voice_needs_confirmation` 의 `_suggestion`/`_cleaned_transcript` 2건만 — 인자를 의도적으로 무시함을 표시하는 밑줄 관용구, 이전부터 존재 | NONE |

## task-0078 guard 재검증

같은 함수(`run_self_test`)를 편집했으므로 mutation probe 를 다시 돌렸다.

| probe | 결과 |
| --- | --- |
| 대조군 — 미변형 사본 | PASS |
| `shell`+`=True` / `git`+` commit` / `git`+` push` / `os.`+`system` 삽입 | 4건 전부 차단 |
| `READ_ONLY_GIT_COMMANDS` / `run_read_only_git` 제거 | 2건 전부 차단 |

`forbidden_source_patterns` 튜플은 `5431498` 와 **diff 0**, assert 4종 전부 1건씩 그대로.
probe 전후 `run_web_app.py` byte identity 확인.

## 검증 결과

| 검증 | 결과 |
| --- | --- |
| Console self-test | PASS |
| Console smoke + browser shell | PASS |
| KEEP route probe | 13/13 PASS |
| canonical 전수 | 73/73 PASS |
| SOP | status=PASS |
| bot self-check | 92/92 PASS |
| discord-intake | 96/96 PASS |
| audit-chain | 7 passed, 0 failed |
| buzz-bridge | 37/37 PASS |
| discord-nl-intent | 35/35 PASS |
| check_no_secrets --self-test | failures=0, PASS |
| node --check | OK |
| git diff --check | clean |
| task-0078 guard mutation probe | 7/7 PASS |

line ending 유지 — `run_web_app.py` CRLF 4375, `run_smoke_tests.py` LF 5417.

## dead-code cleanup 3단계 누계

| task | 파일 | 삭제 |
| --- | ---: | ---: |
| task-0081 | 3 | 130 |
| task-0082 | 1 | 26 |
| task-0083 | 2 | 68 |
| **합계** | — | **224** |

task-0080 이 예측한 226줄과 2줄 차이다. 원인은 `import stat` 1줄이 이미
0081 예측에 들어 있었고 실제로는 0083 에서 제거된 회계 차이, 그리고
`.severity-*` 블록 경계 계산 차이다. 판정 자체가 바뀐 항목은 없다.

## 남은 후속 후보 (이번 task 에 넣지 않음)

- 기존 미사용 import 13건 — `run_web_app.py` 7건, `run_smoke_tests.py` 6건
- 항진 assert 4건 (`before_* == after_*`, `git status` 를 자기 자신과 비교)
- `.jarvis-local` 중복 검사 — run_web_app 3건 중 2건, smoke 4건 중 3건
- README 의 Memory / Skills 섹션(~48줄)과 D1 충돌 문구
- `skills.json` 의 `tasks_reports` 카드 문구
