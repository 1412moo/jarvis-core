# task-0096-console-task-view-header-block-scope

- id: `task-0096-console-task-view-header-block-scope`
- title: `Actionable Task View 메타데이터 파서를 header block 으로 한정`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-09 06:13 UTC`
- updated_at: `2026-09-09 06:13 UTC`
- summary: `parse_task_view_text 가 파일 전체에서 - 로 시작하는 모든 줄을 metadata 로 읽어, 본문에 평범한 Markdown 목록이 있는 task 기록을 Needs metadata review 로 떨어뜨리고 있었다. 84 건 중 35 건이 오판정이었다. task-0054 가 task_file_writer 에서 같은 결함을 이미 고쳐 두었고 그 header block 경계 규칙을 그대로 이식했다. 경계만 옮겼고 필드 검증은 어휘 타입 길이 인접성 모두 그대로다. 파서 기준 84/84 valid, 회귀 0. 다만 Console 화면의 metadata_review 건수는 이 수정만으로 줄지 않는다. read_task_view_text 가 4096 byte 를 넘는 파일을 파싱 전에 거부하고 84 건 중 43 건이 여기 걸리며 파서 오판정 35 건은 그 43 건의 부분집합이라, 화면 수치는 43 에서 43 으로 그대로다. 이 크기 상한은 지시 범위 밖이라 건드리지 않았고 별도 결정으로 남긴다. regression test 를 self-test 와 smoke 양쪽에 추가했고 mutation probe 로 옛 규칙 복원 시 반드시 깨지는 것을 확인했다.`
- source_command: `A1 감사에서 분리한 R6 Console metadata_review 버그 수정 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`bf9b178`** = `origin/main` |
| 직전 작업 | task-0095 (handoff 현재 상태 정정) |
| 변경 파일 | `apps/jarvis-console/run_web_app.py` + 이 기록 |

## 원인

`parse_task_view_text` 는 파일 **전체**를 훑으며 `- ` 로 시작하는 모든 줄을
metadata 로 간주했다.

```python
for line_index, line in enumerate(text.splitlines()):
    if not line.lstrip().startswith("- "):
        continue
    match = TASK_VIEW_METADATA_PATTERN.fullmatch(line)
    if match is None:
        return invalid_task_view("invalid_text", ...)
```

task 기록 본문에 평범한 Markdown 목록이 있으면 그 줄이 metadata 로 읽히고,
`TASK_VIEW_METADATA_PATTERN` 을 만족하지 못해 파일 전체가 `invalid_text` 가 된다.

여기에 **자체 모순**이 하나 더 있었다. 줄을 고를 때는 `line.lstrip()` 으로
들여쓰기를 무시하는데, 정작 패턴은 `^- ` 로 **column 0 에 고정**돼 있다. 그래서
들여쓴 bullet 은 metadata 후보로 뽑히지만 **어떤 경우에도 매치될 수 없어** 반드시
`invalid_text` 가 된다. 이 저장소의 `task-template.md` 가 각 필드 아래에 두는
`  - 규칙:` 주석이 정확히 그 형태다.

증상은 두 가지로 나타났다.

| reason_code | 건수 | 예 |
| --- | --- | --- |
| `invalid_text` | 34 | `- S1 CLI stdio 왕복(claude/codex/agy) — PASS` (task-0046) |
| `unsupported_field` | 1 | `task-0066` 본문 L77 의 `- valid: ` 값이 필드로 오인 |

두 번째는 본문 줄이 **우연히 metadata 문법을 만족**해 버린 경우다. 원인은 같다.

## task-0054 와의 관계

이것은 새로운 버그가 아니라 **이미 진단된 버그의 미수정 인스턴스**다.

`task_file_writer.py:468` 에 task-0054 가 남긴 주석이 그대로 있다.

```
# task-0054: metadata is the header block, not "every line starting with -".
```

task-0054(`38b9027`)는 intake writer 를 header block 으로 한정했지만, **Console 의
Actionable Task View reader 에는 같은 수정이 적용되지 않았다.** 두 파서의
`TASK_METADATA_PATTERN` / `TASK_VIEW_METADATA_PATTERN` 은 **바이트 단위로 동일**하다.

```
r"^- (?P<field>[a-z][a-z0-9_]*): `(?P<value>[^`\r\n]*)`$"
```

즉 두 파서의 유일한 차이가 **경계 규칙**이었고, 이번 수정은 그 경계만 맞춘 것이다.
새 규칙을 발명하지 않고 **기존에 승인된 규칙을 이식**했다.

## 수정

`apps/jarvis-console/run_web_app.py` 의 `parse_task_view_text` 한 곳, **+11 / -2**.

```python
in_header = False
for line_index, line in enumerate(text.splitlines()):
    if line[:1].isspace():
        continue
    if not in_header:
        if not line.startswith("- "):
            continue
        in_header = True
    elif not line.startswith("- "):
        break
    match = TASK_VIEW_METADATA_PATTERN.fullmatch(line)
```

규칙 세 가지 모두 task-0054 와 동일하다.

| 규칙 | 의미 |
| --- | --- |
| 들여쓴 줄은 `continue` | 위 필드의 연속행이므로 metadata 도 종결자도 아니다 |
| header 진입 전 비 `- ` 줄은 `continue` | 제목·HTML 주석·빈 줄이 블록 위에 있다 |
| header 진입 후 첫 비 `- ` 줄에서 `break` | 그 아래는 전부 문서 본문이다 |

**경계만 움직였다.** 매치 이후의 필드 검증(어휘, 타입, 길이, `allow_empty`,
`completion_evidence` 인접성, id 일치, status, timestamp)은 **한 줄도 바꾸지 않았다.**

## 전후 수치 — 실제 84 개 파일 전수

파서에 전체 텍스트를 직접 넣었을 때의 판정이다.

| | before | after |
| --- | ---: | ---: |
| valid | 49 | **84** |
| invalid | **35** | **0** |
| `invalid_text` | 34 | 0 |
| `unsupported_field` | 1 | 0 |

| 전이 | 건수 |
| --- | ---: |
| invalid -> valid | **35** |
| **valid -> invalid** | **0** |
| valid 유지인데 group 변경 | **0** |

dogfood 23 건은 본문 목록이 없어 before 에도 전부 valid 였고 after 에도 그대로다.
**이 수정으로 상태가 나빠진 파일은 없다.**

### 그러나 Console 화면 수치는 이 수정만으로 바뀌지 않는다

파서를 고친 뒤에도 `/api/overview` 의 Actionable Task View 는 여전히 10 건 전부
`metadata_review` 다. **원인이 하나 더 있다.**

```
run_web_app.py:1591  read_task_view_text
    raw = file.read(OVERVIEW_SNIPPET_BYTES + 1)          # 4096
    if len(raw) > OVERVIEW_SNIPPET_BYTES:
        raise ValueError("task metadata exceeds bounded read")
```

`project_task_view_items` 가 이 `ValueError` 를 잡아
`invalid_task_view("invalid_text")` 로 바꾼다. 즉 **4096 byte 를 넘는 파일은
파서가 실행되기도 전에 거부**된다. 크기와 형식 불량을 같은 판정으로 뭉갠 것이다.

| 기준 | before | after |
| --- | ---: | ---: |
| 파서 (전체 텍스트) invalid | 35 | **0** |
| Console 파이프라인 invalid | 43 | **43** |

| 집합 | 건수 |
| --- | ---: |
| 파서 오판정 | 35 |
| 4096 byte 초과 | 43 |
| **교집합** | **35** |
| 파서만 문제 (크기는 정상) | **0** |
| 크기만 문제 (파서는 정상) | 8 |

**파서 오판정 35 건은 크기 초과 43 건의 부분집합**이다. 그래서 Console 화면에서는
이 버그가 크기 상한에 완전히 가려져 있었고, 파서만 고쳐서는 화면 수치가 움직이지 않는다.

그렇다고 이 수정이 무의미한 것은 아니다. **순서상 이 수정이 선행 조건**이다.
크기 상한을 먼저 풀었다면 그 43 건 중 35 건이 곧바로 파서 사유로 `metadata_review`
가 됐을 것이다.

크기 상한 변경은 이번 지시의 범위(`- ` bullet 파서 최소 수정)를 벗어나고,
bounded read 는 의도된 안전 장치라 임의로 완화하지 않았다. **별도 Owner 결정으로
남긴다.** 참고로 header block 은 항상 파일 앞부분에 있으므로, 상한을 올리지 않고도
읽어온 prefix 안에서 header block 만 파싱하는 방식이 가능하다 — 메모리 상한은
그대로 두면서 "큰 파일"과 "형식 불량"의 혼동만 제거하는 방향이다.

## 검증을 약화시키지 않았다

경계만 고치고 검증을 느슨하게 만들지 않았음을 16 개 사례로 확인했다.

| 사례 | 기대 | 결과 |
| --- | --- | --- |
| 정상 header | valid | valid |
| **본문 bullet (버그 대상)** | **valid** | **valid** |
| 본문에 필드 모양 bullet `- valid: ` | valid | valid |
| 본문에 `- status: ` 재등장 | valid | valid |
| 들여쓴 연속행 `  - 규칙:` | valid | valid |
| header 안 malformed field | invalid | invalid |
| header 안 unsupported field | invalid | invalid |
| header 안 duplicate field | invalid | invalid |
| required field 누락 | invalid | invalid |
| id / 파일명 불일치 | invalid | invalid |
| 잘못된 status | invalid | invalid |
| 잘못된 timestamp | invalid | invalid |
| `completion_evidence` 비인접 | invalid | invalid |
| `completion_evidence` 인접 | valid | valid |
| `summary` 빈 값 | invalid | invalid |
| boolean 필드 잘못된 값 | invalid | invalid |

**16/16 일치.** 본문은 무시하되 header block 안의 결함은 전부 그대로 잡는다.

## regression test

기존 self-test 블록 안에 추가했고 **새 파일이나 새 프레임워크를 만들지 않았다.**

| 위치 | 내용 |
| --- | --- |
| `run_web_app.py` self-test | header-block 경계 사례 |
| `run_smoke_tests.py` | 동일 사례 |

핵심 단언은 본문 bullet 이 있는 기록이 `valid` 로 파싱되고 그룹이
`metadata_review` 가 **아니어야** 한다는 것, 그리고 header block 안의 결함은
여전히 `invalid` 여야 한다는 것이다.

### mutation probe

메모리상에서 경계 규칙을 옛 전체 스캔 방식으로 되돌린 뒤 self-test 를 실행했다.
파일은 건드리지 않았다.

```
[PASS] 옛 전체 스캔 규칙 -> self-test 실패
[PASS] 복원 후 self-test 통과
       파일 byte-identical: True
```

**전체 스캔 규칙이 되돌아오면 테스트가 반드시 깨진다.**

## 범위 밖 — 건드리지 않은 것

| 항목 | 상태 |
| --- | --- |
| `NEEDS_APPROVAL` 의 정의·처리 | **무변경** — `TASK_VIEW_STATUS_RULES` 6 종 그대로 |
| `TASK_VIEW_ALLOWED_FIELDS` 등 필드 어휘 | 무변경 |
| `invalid_task_view` reason code 집합 | 무변경 |
| `TASK_VIEW_GROUPS` | 무변경 |
| `task_file_writer.py` | 무변경 — 이미 옳다 |
| Memory / Skills · Research Council · Hermes · Discord | 무변경 |
| Console 의 다른 기능과 UI | 무변경 |
| 기존 task 파일 내용 | 무변경 |
| `docs/master-plan.md` · `docs/chatgpt-handoff.md` · `.gitignore` | 무변경 |
| dogfood 23 건 · `jarvis.bat` | sha256 무변경 |

`docs/chatgpt-handoff.md` 는 task-0095 에서 이 버그와 `35 of 83` 수치를 기록해 두었다.
그 서술의 갱신은 이번 범위 밖이라 하지 않았다.
