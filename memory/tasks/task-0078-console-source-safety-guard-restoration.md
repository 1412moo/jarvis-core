# task-0078-console-source-safety-guard-restoration

- id: `task-0078-console-source-safety-guard-restoration`
- title: `Console self-test 의 소스 안전 가드 4건 복원`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-08 00:00 UTC`
- updated_at: `2026-09-08 00:00 UTC`
- summary: `task-0071 의 memory_skills 제거 과정에서 run_self_test 의 source 지역변수와 그것을 소비하던 assert 4건이 함께 사라져, forbidden_source_patterns 튜플만 남고 검사는 수행되지 않는 상태였다. Console 이 내거는 no commit / no push / no shell 불변식의 유일한 기계적 근거가 8d21efe 이후 비어 있었다. task-0071 직전 커밋 3acd0cb 에서 원본을 그대로 추출해 5줄을 복원했고 금지 패턴 목록은 한 건도 바꾸지 않았다. mutation probe 7종으로 가드가 실제로 차단하는지 확인했으며 원본 파일은 byte-identical 을 유지했다. 1파일 +5 -0, 전 회귀 통과.`
- source_command: `task-0077 감사 결과 C-1 — 소실된 소스 안전 가드 복원 지시`

## 기준선

HEAD `aa1436f` = `origin/main`. 1파일, **+5 / -0**. 삭제 0줄.

## 회귀의 정체

`3acd0cb` 까지 `run_self_test()` 안에 있던 코드:

```python
source = Path(__file__).read_text(encoding="utf-8")
forbidden_source_patterns = (...)
assert all(pattern not in source for pattern in forbidden_source_patterns)
assert ("shell" + "=True") not in source
assert "READ_ONLY_GIT_COMMANDS" in source
assert "run_read_only_git" in source
```

`8d21efe` (task-0071) 이후 튜플만 남고 `source` 정의와 assert 4건이 사라졌다.
`run_web_app.py` 를 대상으로 이 패턴들을 검사하는 테스트는 저장소 어디에도 없었다.
`run_smoke_tests.py` 의 동명 가드 2건은 `project_control_registry.py` 와
`recent_milestone_evidence.py` 만 스캔한다.

`git log` 로 커밋별 전수 확인했다 — `3acd0cb` 이전 40개 커밋 전부 검출 1건,
`8d21efe` 이후 전부 0건.

## 복원 내용

`3acd0cb:apps/jarvis-console/run_web_app.py` 에서 원본을 추출해 대조했다.
현재 파일의 `forbidden_source_patterns` 튜플 17줄은 원본과 **byte-identical** 이었으므로
튜플은 건드리지 않고 앞뒤로 5줄만 삽입했다.

금지 패턴 15종은 한 건도 추가·삭제·수정하지 않았다.
패턴이 `"git" + " add"` 처럼 연결식으로 적힌 이유는 가드가 자기 자신이 들어 있는
파일을 스캔하기 때문이다 — 리터럴로 적으면 가드가 스스로를 검출한다. 이 형태를 유지했다.

## mutation probe

실제 파일을 수정하지 않기 위해 모듈 전역 `__file__` 만 임시 파일로 바꿨다.
`Path(__file__).read_text()` 는 호출 시점에 전역을 해석하므로 **가드의 읽기 한 곳만**
우회되고, import 시점에 확정된 `APP_ROOT` / `REPO_ROOT` 와
`inspect.getsource` 의 `co_filename` 은 영향을 받지 않는다.
매번 실제 `run_self_test()` 를 끝까지 실행해 실제 assert 문이 발화하는지 확인했다.

| probe | 결과 | 차단한 assert |
| --- | --- | --- |
| 대조군 — 미변형 사본 | PASS (통과해야 정상) | — |
| a. `shell` + `=True` 삽입 | PASS | `forbidden_source_patterns` |
| b1. `git` + ` commit` 삽입 | PASS | `forbidden_source_patterns` |
| b2. `git` + ` push` 삽입 | PASS | `forbidden_source_patterns` |
| b3. `os.` + `system` 삽입 | PASS | `forbidden_source_patterns` |
| c1. `READ_ONLY_GIT_COMMANDS` 제거 | PASS | `READ_ONLY_GIT_COMMANDS` 존재 검사 |
| c2. `run_read_only_git` 제거 | PASS | `run_read_only_git` 존재 검사 |

probe 전후 `run_web_app.py` sha256 동일:
`4e909cba0ddf220db1b55467c1edcd1e0e556841596f794f13f137ac49f0a290`

### 정직한 한계

`assert ("shell" + "=True") not in source` 는 **단독으로는 발화할 수 없다.**
같은 문자열이 `forbidden_source_patterns` 에도 들어 있어 앞선 `all(...)` 검사가
항상 먼저 실패하기 때문이다. 원본에서도 동일하게 중복이었고, 지시가 기존 의미를
그대로 복원하라는 것이었으므로 중복을 제거하지 않고 그대로 복원했다.

## 검증

| 검증 | 결과 |
| --- | --- |
| Console self-test | PASS |
| Console smoke + browser shell | PASS |
| canonical 전수 | 69/69 PASS |
| SOP | status=PASS |
| bot self-check | 92/92 PASS |
| discord-intake | 92/92 PASS |
| audit-chain | 7 passed, 0 failed |
| buzz-bridge | total 37, failed 0 |
| discord-nl-intent | total 35, failed 0 |
| check_no_secrets --self-test | failures=0, status=PASS |
| node --check | OK |
| git diff --check | clean |
| mutation probe | 7/7 PASS |
| 원본 byte identity | 동일 |

## 범위 밖으로 남긴 것

task-0077 이 식별한 나머지는 이번 작업에 포함하지 않았다.

- C-2 manual copy fallback 파손
- dead code 약 204줄
- `README.md` 의 Memory / Skills 섹션과 D1 충돌 문구
- `skills.json` 의 `tasks_reports` 카드 문구
- D6-c skill_registry, project_control — DEFER 유지
