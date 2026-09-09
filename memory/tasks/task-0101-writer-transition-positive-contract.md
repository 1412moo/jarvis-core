# task-0101-writer-transition-positive-contract

- id: `task-0101-writer-transition-positive-contract`
- title: `Writer 공식 6개 status 전이를 positive contract 로 고정`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-09 10:24 UTC`
- updated_at: `2026-09-09 10:24 UTC`
- summary: `TASK_STATUS_TRANSITIONS 의 허용 6 쌍 중 4 쌍이 어떤 regression suite 에서도 positive 로 검증되지 않았다. 7x7 거부 루프가 허용 쌍을 자기 하드코딩 리터럴로 건너뛰고, 그 리터럴과 writer 상수를 대조하는 단언도 없었다. writer 에서 한 쌍을 지워도 9 개 suite 가 전부 green 이었다. test-only 로 세 겹을 넣었다. 리터럴을 이름 있는 집합으로 빼고 writer 상수와 대조하는 drift guard, 개수 단언, 그리고 6 쌍 전부를 실제 파일로 수행하는 positive 검증이다. production 코드는 건드리지 않았고 기존 거부 43 쌍 검증도 그대로다.`
- source_command: `task-0100 조사에서 확인한 transition positive coverage gap 의 test-only hardening 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`ac0e4c4`** = `origin/main` |
| 직전 작업 | task-0099 (secret-like 파일명 필터 계약 고정) |
| 변경 파일 | `run_smoke_tests.py` + 이 기록 |
| production 코드 변경 | **없음** |

## 배경 — task-0100 조사 결과

task-0100 에서 writer 와 Console 의 transition contract 를 대조했고 **불일치는
0 건**이었다. writer 실측 7x7 행렬이 `TASK_STATUS_TRANSITIONS` 와 정확히 일치했고,
Console 이 노출하는 2 쌍은 그 부분집합이며, Console-only 쌍은 없었다.

문제는 계약이 아니라 **그 계약을 지키는 테스트**였다.

```python
if (source_status, target_status) in {
    ("TODO", "DOING"), ("DOING", "DONE"),
    ("NEEDS_APPROVAL", "DOING"), ("NEEDS_APPROVAL", "FAILED"),
    ("DOING", "FAILED"), ("FAILED", "TODO"),
}:
    continue
```

7x7 루프는 허용 6 쌍을 **자기 하드코딩 리터럴로 건너뛰고** 거부 43 쌍만 단언했다.
positive 단언은 `TODO -> DOING` 과 `DOING -> DONE` 둘뿐이었고, 나머지 4 쌍
(승인 경로 전이)은 어느 suite 에도 없었다. `orchestrator/discord-intake` smoke 는
`transition_task_file_status` 를 **0 회** 호출한다.

그 리터럴과 writer 상수를 대조하는 단언도 없었다. 주석은 "spelled out rather than
imported" 라고 의도를 밝혔지만, 그러면 두 사본이 갈라져도 아무도 모른다 —
status 어휘가 task-0098 까지 3 개월 갈라져 있던 것과 같은 구조다.

결과: **writer 에서 `("FAILED","TODO")` 를 지워도 9 개 suite 가 전부 green 이었다.**

유일한 방어였던 `adapters/discord/bot_minimal.py` 의
`_validate_approve_transition_contract_sync()` 와 그 drift 테스트는
`_run_self_check_suite()` 안에 있고, 그 함수는 `__main__` 에서 수동 실행할 때만
불린다. 정규 suite 중 이를 실행하는 것은 없다.

## 무엇을 넣었나 — 세 겹

| 겹 | 내용 | 잡는 것 |
| --- | --- | --- |
| drift guard | `official_transitions == TASK_STATUS_TRANSITIONS` | writer 쪽만 바뀐 경우 |
| count | `len(official_transitions) == 6` | 양쪽을 함께 줄인 경우 |
| positive | 6 쌍 전부를 실제 파일로 전이 수행 | 집합에는 있는데 **동작하지 않는** 경우 |

리터럴은 지시대로 유지했다. 이름만 `official_transitions` 로 빼서 대조 가능하게
만들었고, 거부 루프는 같은 집합을 그대로 쓰므로 **43 쌍 검증은 무변경**이다.

positive 검증은 상수 membership 검사가 아니다. 각 쌍마다 임시 fixture 에 source
status 로 파일을 쓰고 `transition_task_file_status` 를 호출해 `updated` 를 확인한
뒤, **파일 바이트가 status 와 updated_at 두 줄만 바뀐 결과와 정확히 일치**하는지
비교한다. CRLF 개수 보존도 함께 본다.

```python
for index, (source_status, target_status) in enumerate(
    sorted(official_transitions), start=7101
):
    ...
    assert positive_result.result_type == "updated"
    assert positive_after == positive_before.replace(status).replace(updated_at)
```

fixture 는 기존 `write_task` 헬퍼와 기존 `tasks_dir` 를 재사용한다. 새 헬퍼도,
새 디렉터리도 만들지 않았다. 파일 6 개는 기존 `finally` 의 `shutil.rmtree` 로
정리된다.

## mutation probe

**허용 6 쌍을 하나씩 writer 에서 제거** — 6/6 전부 smoke 실패(exit=1).

| 제거한 쌍 | 실패 지점 |
| --- | --- |
| `TODO -> DOING` | 기존 start positive 단언 |
| `DOING -> DONE` | 기존 complete positive 단언 |
| `NEEDS_APPROVAL -> DOING` | drift guard |
| `NEEDS_APPROVAL -> FAILED` | drift guard |
| `DOING -> FAILED` | drift guard |
| `FAILED -> TODO` | drift guard |

세 겹이 서로를 대신하지 않는다는 것도 따로 확인했다.

| probe | 결과 |
| --- | --- |
| 양쪽에서 `FAILED -> TODO` 동시 제거 | `assert len(official_transitions) == 6` 실패 |
| drift guard 와 count 를 지우고 writer 만 제거 | positive 단언 실패 — `('FAILED','TODO', TaskStatusTransitionResult(result_type='hold', ...))` |

즉 drift guard 없이도 positive 가 잡고, positive 없이도 drift guard 가 잡으며,
둘을 함께 우회해도 count 가 남는다.

## 테스트 결과

| 항목 | 결과 |
| --- | --- |
| Console self-test | PASS |
| Console smoke | PASS |
| writer smoke (`orchestrator/discord-intake`) | exit=0 |
| `git diff --check` | clean |
| 거부 쌍 검증 | 49 - 6 = **43 쌍 유지** |
| fixture 잔여물 | 없음 |

## 바꾸지 않은 것

| 대상 | 상태 |
| --- | --- |
| `TASK_STATUS_TRANSITIONS` | 무변경 — 새 전이 없음 |
| status vocabulary | 무변경 |
| Console production code (`run_web_app.py`) | 무변경 |
| Writer production code (`task_file_writer.py`) | 무변경 |
| `adapters/discord/bot_minimal.py` | 무변경 |
| 기존 거부 43 쌍 검증 | 무변경 |
| task-0097 · task-0098 · task-0099 | 무변경 |

## 남겨 둔 것

`adapters/discord/bot_minimal.py` 의 `_run_self_check_suite()` 를 정규 regression
suite 에 편입할지는 이번 범위 밖이라 손대지 않았다. 이번 drift guard 가 writer
상수의 축소를 잡으므로 그 경로의 시급성은 낮아졌지만, bot_minimal 자신의 로컬
전이 집합이 writer 와 어긋나는 경우는 여전히 수동 실행에만 의존한다.
