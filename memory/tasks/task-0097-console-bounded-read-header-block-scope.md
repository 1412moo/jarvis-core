# task-0097-console-bounded-read-header-block-scope

- id: `task-0097-console-bounded-read-header-block-scope`
- title: `Console bounded read 를 파일 크기 검사에서 header block 추출로 전환`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-09 08:23 UTC`
- updated_at: `2026-09-09 08:23 UTC`
- summary: `read_task_view_text 가 4096 byte 상한을 read bound 가 아니라 파일 전체에 대한 입장 심사로 써서, header 가 멀쩡한데 본문이 긴 task 기록을 파서에 닿기도 전에 거부하고 있었다. 84 건 중 43 건이 여기 걸렸고 그 중 42 건은 header 가 정상이었다. 화면에 보이는 10 건이 전부 metadata_review 였고 Start / Complete / Record Completion Evidence 는 고를 수 있는 valid task 가 하나도 없었다. 상한은 그대로 두고 같은 bounded prefix 안에서 header block 만 잘라 파서에 넘기도록 고쳤다. prefix 안에서 block 이 닫히지 않으면 종전대로 fail closed 다. 이 기록까지 포함한 전수 85/85 valid, 화면 metadata_review 10 에서 0.`
- source_command: `task-0097 investigation 결과에 따른 Design A 구현 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`285987f`** = `origin/main` |
| 직전 작업 | task-0096 (파서 header block 경계 수정) |
| 변경 파일 | `run_web_app.py` · `run_smoke_tests.py` · task-0096 기록 · 이 기록 |

## 원인

`OVERVIEW_SNIPPET_BYTES` 는 **읽기 상한**인데 `read_task_view_text` 만 이것을
**파일 전체에 대한 입장 심사**로 썼다.

```python
raw = file.read(OVERVIEW_SNIPPET_BYTES + 1)
if len(raw) > OVERVIEW_SNIPPET_BYTES:
    raise ValueError("task metadata exceeds bounded read")   # 파일을 거부
```

`project_task_view_items` 가 이 `ValueError` 를 `invalid_task_view("invalid_text")`
로 바꾼다. 필요한 것은 header block 뿐인데, 거부 사유는 **본문**의 성질이었다.

같은 상수를 쓰는 형제 reader 가 이 해석에 동의하지 않는다는 점이 근거다.

| | `read_overview_title_and_summary` | `read_task_view_text` (before) |
| --- | --- | --- |
| 읽기 | `file.read(OVERVIEW_SNIPPET_BYTES)` | `read(... + 1)` |
| 초과 시 | 앞부분만 쓰고 계속 | **파일 거부** |

`docs/jarvis-console-v0.1-checkpoint.md` 는 이 상수를 "prefix/snippet 만 읽는다"
로 규정한다. 쓰기 경로(`preview_task_transition`, completion evidence)는 애초에
`read_bytes()` 로 파일 전체를 읽으므로, 이 상한은 시스템 전역 불변식도 아니었다.
더 엄격한 쪽이 read-only 쪽이었다.

그리고 이 분기는 **한 번도 테스트된 적이 없었다.** 도입 커밋 `e1e0c0b` 이후 함수는
수정된 적이 없고, 모든 projection 테스트가 `text_reader` 를 주입해 reader 를 건너뛴다.

## 무엇을 바꿨나

상한은 그대로다. 같은 bounded prefix 안에서 header block 만 잘라 파서에 넘긴다.

```python
raw = file.read(OVERVIEW_SNIPPET_BYTES + 1)
truncated = len(raw) > OVERVIEW_SNIPPET_BYTES
if truncated:
    raw = raw[:OVERVIEW_SNIPPET_BYTES]
end = task_view_header_block_end(raw, truncated)
if end is None:
    raise ValueError("task metadata header block exceeds bounded read")
return raw[:end].decode("utf-8", errors="strict")
```

경계 규칙은 task-0054 / task-0096 과 **같은 규칙을 bytes 로** 적용한 것이다.
들여쓴 줄은 위 필드의 연속이고, block 은 첫 column-0 `- ` 줄에서 열려 `- ` 가
아닌 첫 column-0 줄에서 닫힌다. `_execution_header_block_end` 가 이미 같은 일을
bytes 로 하고 있어 그 선례를 따랐다.

bytes 로 처리하는 이유가 두 가지다.

1. 자르는 지점이 항상 줄바꿈이고, 줄바꿈은 언제나 UTF-8 문자 경계다.
   `raw[:4096]` 을 통째로 strict decode 하는 방식은 이 성질이 없어서 실제 corpus
   조사 시점 84 건 중 **12 건에서 `UnicodeDecodeError`** 가 났다(한국어가 4096 에서 잘림).
2. truncated 상태에서 마지막 줄이 줄바꿈으로 끝나지 않으면 잘린 조각이므로
   metadata 로 읽지 않는다.

prefix 안에서 block 이 닫히지 않으면 **fail closed** 다. 잘린 곳 너머를 볼 수
없으므로 header 가 이어졌는지 알 수 없다.

## 전후 수치 — 실제 85 개 파일 전수

working tree 의 같은 85 개 파일(이 기록 포함)에 옛 reader 와 새 reader 를
각각 돌린 결과다.

| | before | after |
| --- | ---: | ---: |
| 전체 | 85 | 85 |
| `<= 4096B` | 41 | 41 |
| `> 4096B` | 44 | 44 |
| Console valid | 41 | **85** |
| Console invalid | **44** | **0** |
| oversized 정상 header 오판정 | **44** | **0** |
| 전체 텍스트 파서와 불일치 | 44 | **0** |

조사 시점 corpus 는 84 건이었고 oversized 43 건 중 42 건만 header 가 정상이었다.
나머지 하나가 task-0096 기록 자신이며, 아래 정정으로 그것까지 정상이 되었다.
여기에 이 기록이 더해져 최종 corpus 는 85 건, oversized 44 건이다.

전체 텍스트 파서 기준도 85/85 valid 다. 즉 **bounded reader 의 판정이 전체 파일을
읽었을 때의 판정과 85 건 전부 일치**한다.

HEAD 에 tracked 된 61 건만 따로 보면 valid 18 → 60 이고, `field_too_long` 1 건은
그대로 invalid 로 남았다. 크기 때문에 가려져 있던 진짜 결함을 새 reader 가
덮어주지 않는다는 확인이다.

## `/api/overview`

```text
status : 200
tasks  : 10
groups : {'needs_attention': 1, 'completed': 9}
reasons: {None: 10}
```

before 는 `{'metadata_review': 10}` / `{'invalid_text': 10}` 였다.

## Task transition

`selected_task_transition_items` 는 이 projection 에서 `parse_state == "valid"` 만
고른다. before 에는 valid 가 0 이라 Start / Complete / Record Completion Evidence
가 **모든 task 에 대해** `task_not_found_in_actionable_view` 를 반환했다.

after 는 10/10 이 valid 다. 선택은 성립하고, 응답은 상태에 맞는 사유로 바뀐다.

| 호출 | before | after |
| --- | --- | --- |
| `preview_task_transition` (start) | `task_not_found_in_actionable_view` | `task_status_transition_not_allowed` |
| `preview_completion_evidence` | `..._task_not_found_in_actionable_view` | `completion_evidence_task_not_doing` |

현재 선택 슬라이스에 TODO/DOING 이 없어 실제 전이는 일어나지 않는다. 확인한 것은
**선택 자체가 되살아났다**는 사실이다.

## 테스트

기존 projection 테스트는 전부 `text_reader` 를 주입해 이 결함을 지나친다. 그래서
새 테스트는 **임시 디렉터리에 실제 파일을 쓰고 진짜 `read_task_view_text`** 를
통과시킨다. self-test 와 smoke 양쪽에 넣었다.

| 사례 | 기대 |
| --- | --- |
| `<= 4096B` + 정상 header | valid |
| `> 4096B` + 정상 header | valid |
| `> 4096B` + 본문 column-0 bullet 목록 | valid |
| `> 4096B` + 들여쓴 연속 줄이 낀 header | valid |
| `> 4096B` + malformed field | `invalid_text` + field |
| `> 4096B` + unsupported field | `unsupported_field` |
| terminator 가 4096-3 … 4096 | valid |
| terminator 가 4096+1 … 4096+3 | fail closed |
| header 자체가 4096B 초과 | fail closed |
| UTF-8 multibyte 가 4096 에서 잘림 | valid (decode 오류 없음) |
| header 안 invalid UTF-8 | `UnicodeDecodeError` |
| 파일 없음 | `OSError` → projection `invalid_text` |

smoke 에는 두 가지를 더 넣었다.

- 읽기가 계속 bounded 인지 source 로 확인(`read_bytes` / `read_text` 금지)
- 실제 corpus 전수에 대해 **bounded reader 판정 == 전체 텍스트 판정**

## mutation probe

다섯 변형 모두 self-test 와 smoke **양쪽에서** 실패한다.

| 변형 | 결과 |
| --- | --- |
| 옛 whole-file rejection 복원 | CAUGHT |
| `raw[:4096]` 통째로 strict decode | CAUGHT |
| 닫히지 않은 block 을 buffer 끝으로 취급 | CAUGHT |
| 잘린 마지막 줄을 metadata 로 취급 | CAUGHT |
| `line.strip()` 기반 pre-task-0054 경계 복원 | CAUGHT |

마지막 변형은 처음에 잡히지 않았다. reader 쪽 테스트에 **들여쓴 연속 줄**이 없어
`isspace()` 분기가 비어 있었기 때문이다. 그 fixture 를 추가해 닫았다.

## task-0096 기록 정정

task-0096 기록 자신이 corpus 의 한 파일인데 `summary` 가 599 자로 500 자 한도를
넘겨 `field_too_long` 이었다. 목록 맨 위에 있으면서 유일하게 **진짜로** invalid 한
파일이었다.

- `summary` 를 495 자로 줄였다.
- `84/84 valid` 가 현재 기준으로 틀렸다는 정정 노트를 달았다(착수 시점 83/84).
- 크기 상한 문단에 task-0097 이 그 방향을 채택했다는 후속 노트를 달았다.

당시 측정값과 역사적 서술은 고치지 않았다.

## 바꾸지 않은 것

| 대상 | 상태 |
| --- | --- |
| `OVERVIEW_SNIPPET_BYTES` | 4096 그대로 |
| `parse_task_view_text` (task-0096) | 무변경 |
| `project_task_view_items` | 무변경 |
| `TASK_VIEW_REASON_CODES` · `TASK_VIEW_GROUPS` · `TASK_VIEW_STATUS_RULES` | 무변경 |
| `task_file_writer.py` · `web/app.js` | 무변경 |
| 다른 task 파일 내용 | 무변경 |

전체 회귀 9 종 sequential 통과. `git diff --check` clean. `run_web_app.py` CRLF,
`run_smoke_tests.py` LF 유지.
