# task-0099-console-discovery-name-filter-tasks-scope

- id: `task-0099-console-discovery-name-filter-tasks-scope`
- title: `memory/tasks 에서의 secret-like 파일명 필터 동작을 테스트로 고정`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-09 10:10 UTC`
- updated_at: `2026-09-09 10:10 UTC`
- summary: `is_overview_candidate_path 의 secret-like 파일명 필터는 memory/tasks 에도 적용되어 task-0043-no-secrets-enforcement.md 를 discovery 에서 제외한다. 조사 결과 이것은 의도된 정책이었다. 이 필터는 TASK_FILE_PATTERN 검사보다 먼저 돌고 Recent Tasks 는 패턴 필터 없이 파일 내용 앞부분을 읽어 표시하므로, 그 디렉터리에서도 실제 방어를 수행한다. 다만 기존 픽스처가 전부 docs 기준이라 이 동작이 테스트가 아니라 우연으로 유지되고 있었다. production 코드는 건드리지 않고 self-test 와 smoke 양쪽에 3 개 단언을 추가해 현재 계약을 고정했다.`
- source_command: `task-0098 후속 조사에서 확인한 discovery 필터 관찰의 테스트 고정 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`55f0adc`** = `origin/main` |
| 직전 작업 | task-0098 (ON_HOLD status 편입) |
| 변경 파일 | `run_web_app.py` · `run_smoke_tests.py` + 이 기록 |
| production 코드 변경 | **없음** — 테스트만 추가 |

## 배경

task-0098 후속 조사에서 `memory/tasks/task-0043-no-secrets-enforcement.md` 가
Console discovery 에서 빠진다는 것을 발견했다. 파싱하면 `valid / DONE /
completed` 인 정상 record 인데, slug 의 `secrets` 가
`SECRET_LIKE_NAME_PARTS = ("secret", "token", "credential", "password", ".env")`
에 걸린다.

조사 결론은 **의도된 정책**이었다. 근거 넷.

| 근거 | 내용 |
| --- | --- |
| 도입 | `e53d109`(2026-06-30) 에서 discovery 안전 규칙의 일부로 처음부터 존재 |
| 공개 | `/api/overview` 가 `"excluded": [..., "secrets-like file names"]` 를 응답에 실어 보낸다 |
| 픽스처 | 기존 테스트가 `docs/secret-plan.md` 를 쓴다 — 평범한 문서 이름을 일부러 골라 과다 제외를 계약으로 못 박았다 |
| 원칙 | `README.md` · `docs/jarvis-console.md` 가 secrets/credentials/tokens 비저장을 반복 선언한다 |

## 왜 memory/tasks 에도 필요한가

조사 도중 한 번 "그 디렉터리는 `TASK_FILE_PATTERN` 으로 제약되니 휴리스틱이
오탐만 만든다"고 판단했는데 **틀렸다.** 실제 배선은 이렇다.

```python
discovered_tasks = discover_recent_items(("memory_tasks",))   # 이름 필터 적용
tasks            = project_task_view_items(discovered_tasks)  # 여기서 처음 TASK_FILE_PATTERN
recent_groups   += recent_group("tasks", "Recent Tasks", ..., discovered_tasks)
                                                              # ← 패턴 필터 없음
```

패턴 제약은 **projection 단계에서만** 걸린다. `recent_group("tasks", ...)` 는
패턴을 거치지 않은 목록을 그대로 받고, 그 title/summary 는
`read_overview_title_and_summary` 가 **파일 내용 앞 4096 byte 를 읽어** 만든다.

따라서 `memory/tasks/` 에 `token.txt` 를 떨어뜨리면 패턴 필터는 막지 못하고
**내용 일부가 UI 에 렌더링된다.** 이름 필터가 그 경로를 실제로 막고 있다.

## 무엇을 고정했나

기존 픽스처가 전부 `docs/` 기준이라, `memory/tasks/` 에서의 동작은 테스트가
아니라 우연으로 유지되고 있었다. self-test 와 smoke 양쪽에 같은 3 개를 넣었다.

| 사례 | 기대 | 무엇을 지키는가 |
| --- | --- | --- |
| `memory/tasks/task-0043-no-secrets-enforcement.md` | `False` | 정상 Task 라도 이름으로 제외된다는 현 정책 |
| `memory/tasks/token.txt` | `False` | 패턴 밖 파일의 내용 노출 차단 — 필터의 존재 이유 |
| `memory/tasks/task-0500-ordinary-record.md` | `True` | 제외가 **이름** 때문이지 디렉터리 때문이 아님 |

세 번째가 앞의 둘을 정직하게 만든다. 이것이 없으면 앞의 두 단언은 엉뚱한 이유로도
통과할 수 있다.

`is_overview_candidate_path` 는 경로만 보는 함수라 파일이 실제로 존재할 필요가
없다. **새로 만든 fixture 파일은 0 개다.**

## mutation probe

"Task 패턴에 맞는 이름은 이름 휴리스틱에서 면제한다"는 완화를 넣어 보았다. 이것이
바로 이 테스트가 조용히 지나가지 못하게 하려는 변경이다.

```python
if not TASK_FILE_PATTERN.fullmatch(path.name) and any(
    part in lowered_name for part in SECRET_LIKE_NAME_PARTS
):
```

self-test 와 smoke **양쪽에서 실패**하고, 실패 지점이 정확히 새 task-0043 단언이다
(exit=1). `docs/secret-plan.md` 와 `token.txt` 단언은 그대로 통과하므로, 새 단언이
겨냥한 것만 움직인다는 확인이기도 하다.

## 이 기록의 파일명

처음 붙인 slug 는 `task-0099-console-secret-name-filter-tasks-scope` 였고, 그
이름이 바로 이 필터에 걸려 기록 자신이 discovery 에서 빠졌다. 이 문서가 설명하는
동작을 문서 자신이 시연한 셈이다. Console 에서 보이지 않을 이유가 없으므로
`secret` 을 뺀 slug 로 바꿨다. 정책을 우회한 것이 아니라 이름을 고른 것이다.

## 남겨 둔 판단

이 완화 자체는 **하지 않았다.** 공개된 `discovery.excluded` 계약을 바꾸는 일이고,
보안 필터에 예외를 내는 것은 Owner 판단이다. 현재 실사용 영향도 0 이다 —
제외되는 1 건은 `DONE` 이고 표시 상한 10 건 밖이다(mtime 36 위).

이 기록은 그 판단을 대신하지 않는다. **현재 동작이 무엇인지만 고정**해서, 나중에
어느 쪽으로 결정하든 그 결정이 의도적으로 이루어지도록 만든다.

## 바꾸지 않은 것

| 대상 | 상태 |
| --- | --- |
| `is_overview_candidate_path` · `SECRET_LIKE_NAME_PARTS` | 무변경 |
| `TASK_FILE_PATTERN` | 무변경 |
| `discovery.excluded` 공개 문구 | 무변경 |
| 기존 `docs/secret-plan.md` 픽스처 | 무변경 |
| task-0097 bounded read · task-0098 status 어휘 | 무변경 |
| production 코드 전체 | 무변경 |

`git diff --check` clean. `run_web_app.py` CRLF, `run_smoke_tests.py` LF 유지.
