# task-0086-console-orphaned-assertion-cleanup

- id: `task-0086-console-orphaned-assertion-cleanup`
- title: `Console 고아 assert 및 중복 tripwire 정리`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-08 01:45 UTC`
- updated_at: `2026-09-08 01:45 UTC`
- summary: `task-0085 가 REMOVE-SAFE 로 확정한 항진 assert 2쌍과 중복 tripwire 를 제거했다. 같은 before/after 모양을 가진 overview·history assert 2건은 사이에 실제 route 호출이 있는 살아 있는 write-free 가드라 보존했다 — 이름 패턴으로 일괄 삭제했다면 함께 지워졌을 것이다. tripwire 4종은 파일별로 정확히 1건씩 남겼다. 2파일 +0 -17, 전 회귀 통과.`
- source_command: `task-0085 감사 결과 — 항진 assert 및 중복 tripwire 정리 지시`

## 기준선

HEAD `cd56b6c` = `origin/main`, tracked 변경 0에서 시작.
2파일, **+0 / -17**. 순수 삭제.

## 삭제 A — 고아 항진 assert 2쌍 (6줄)

```python
before_memory_status = run_read_only_git(("status", "--short"))
after_memory_status  = run_read_only_git(("status", "--short"))
assert before_memory_status == after_memory_status

before_preview_status = run_read_only_git(("status", "--short"))
after_preview_status  = run_read_only_git(("status", "--short"))
assert before_preview_status == after_preview_status
```

두 스냅샷 사이에 아무 연산도 없어 회귀를 잡을 수 없었다.
원래는 `1e69c73` 이 `handle_get_api("/api/memory-skills")` 를,
`e4e58ad` 가 `handle_post_api(MEMORY_PREVIEW_ENDPOINT, ...)` 를 감싸던
write-free 가드였고 task-0071 이 가운데 줄만 제거했다.

## 보존 — 같은 모양이지만 살아 있는 가드 2건

| 위치 | 사이에 있는 연산 |
| --- | --- |
| `run_web_app.py:3919` `before_overview_status == after_overview_status` | `:3917` `handle_get_api("/api/overview")` |
| `run_web_app.py:4082` `before_history_status == after_history_status` | `:4080` `handle_get_api("/api/history")` |

**판정 기준은 이름이 아니라 "두 스냅샷 사이에 연산이 있는가" 였다.**
`before_*/after_*` 패턴으로 일괄 삭제했다면 이 두 route 의 write-free 보증이
조용히 사라졌을 것이다. 삭제 스크립트에 두 assert 가 범위 밖임을 확인하는
guard 를 넣어 실행했다.

## 삭제 B — 중복 tripwire (11줄)

같은 디렉터리 부재를 한 함수 안에서 여러 번 확인하던 중복만 제거했다.

| 파일 | 이전 | 이후 |
| --- | --- | --- |
| `run_web_app.py` | `.jarvis-local` 4건, `state` 2건 | 각 **1건** |
| `run_smoke_tests.py` | `.jarvis-local` 4건, `state` 2건 | 각 **1건** |

각 파일에서 종류별로 완결된 블록 하나만 남겼다.

```python
assert not (APP_ROOT / "state").exists()
assert not (APP_ROOT / "examples" / "memory-skills-sample.json").exists()
assert not (REPO_ROOT / ".jarvis-local").exists()
assert not (REPO_ROOT / "memory" / "skills").exists()
```

`parse_json_body` 검사는 tripwire 가 아니므로 위치 그대로 두었다.

## 삭제량 회계

| 파일 | A | B | 계 |
| --- | ---: | ---: | ---: |
| `run_web_app.py` | 6 | 6 (중복 assert 4 + 공백 2) | **12** |
| `run_smoke_tests.py` | 0 | 5 (중복 assert 4 + 공백 1) | **5** |
| 합계 | 6 | 11 | **17** |

지시서 예상(6 + 8 + 3 = 17)과 총량은 같고 파일별 배분만 다르다.
`run_web_app.py` 의 A·B 가 물리적으로 인접해 한 구간으로 잘렸기 때문이다.

## 정적 검증

| 항목 | `run_web_app.py` | `run_smoke_tests.py` |
| --- | --- | --- |
| `ast.parse` | OK | OK |
| dangling names | `__file__` 만 | 동일 |
| still-unused top-level defs | NONE | NONE |
| 새로 생긴 미사용 import | NONE | NONE |
| 미사용 지역변수 | `voice_needs_confirmation` 의 밑줄 관용구 2건(기존) | NONE |
| tripwire `state` / `.jarvis-local` / `sample.json` / `memory/skills` | 각 **1건** | 각 **1건** |
| KEEP assert 2건 + 사이의 route 호출 | 존재 확인 | — |

삭제한 변수 4개(`before_memory_status` 등)의 저장소 전체 참조 **0건**.
`run_read_only_git` 은 12곳에서 계속 사용된다.

## task-0078 guard

`run_web_app.py` 를 수정했으므로 재검증했다.

- `forbidden_source_patterns` 튜플 — `cd56b6c` 와 **diff 0**
- guard assert 4종 유지
- mutation probe — `shell=True` / `git commit` / `git push` / `os.system` 삽입,
  `READ_ONLY_GIT_COMMANDS` / `run_read_only_git` 제거 **전부 차단**
- probe 전후 byte identity 유지

## 검증 결과

| 검증 | 결과 |
| --- | --- |
| Console self-test | PASS |
| Console smoke + browser shell | PASS |
| KEEP route probe | 13/13 PASS |
| canonical 전수 | 75/75 PASS |
| SOP | status=PASS |
| bot self-check | 92/92 PASS |
| discord-intake | 98/98 PASS |
| audit-chain | 7 passed, 0 failed |
| buzz-bridge | 37/37 PASS |
| discord-nl-intent | 35/35 PASS |
| check_no_secrets --self-test | failures=0, PASS |
| node --check | OK |
| git diff --check | clean |
| task-0078 guard mutation probe | PASS |

line ending 유지 — `run_web_app.py` CRLF 4359, `run_smoke_tests.py` LF 5404.

## 범위 밖 (무변경)

기존 미사용 import(재수출 3건 + `__future__`), 결정성 테스트
(`first == second` 5건), README, master-plan, `skills.json`, `web/` 전체,
Research Council, Hermes, Discord, audit-chain, `jarvis.bat`.

## 남은 후속 후보

- README 의 Memory / Skills 섹션(~48줄)과 Future Phases #5 의 D1 충돌 문구
- `skills.json` 의 `tasks_reports` 카드 문구 — 이미 구현된 기능을 `planned` 로 기술
- master-plan §5 의 `Memory / Skills` workstream 정체성 (Owner 결정 필요)
- D6-c skill_registry / project_control — DEFER 유지
