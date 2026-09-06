# task-0060-mirror-parser-contract-sync

- id: `task-0060-mirror-parser-contract-sync`
- title: `buzz-bridge JS mirror를 task-0054 파서 경계에 맞추고 회귀 검증 추가`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-06 14:37 UTC`
- updated_at: `2026-09-06 14:37 UTC`
- summary: `buzz-bridge 스모크의 mirrorTransitionMetadataParse가 task-0054가 삭제한 whole-file 스캔 규칙을 그대로 갖고 있었다. 실제 기록 59건 중 13건을 거부하는데 suite의 fixture가 전부 header 전용이라 아무도 못 잡았다. 회귀 검증을 먼저 넣어 13건 실패를 재현한 뒤 mirror를 header block 경계로 맞춰 37/37로 만들었다. 실제 파서와의 차분 검증에서 65개 입력 전부 loop 결과와 수집 metadata가 일치했다. 프로덕션 코드와 canonical 규칙은 무변경이다.`
- source_command: `read-only audit 후속 작업 B 승인 (Owner)`

## 기준선

HEAD `911e3f7` = `origin/main`. 변경은 `orchestrator/buzz-bridge/run_smoke_tests.js`
**한 파일**과 이 기록뿐이다.

## 문제 — 조용히 통과하던 잘못된 계약

`mirrorTransitionMetadataParse()`는 Python `_transition_metadata()`의 loop 결과를
재현하는 테스트용 미러다. 그런데 task-0054가 제거한 규칙을 그대로 갖고 있었다.

한 줄이었다 — 앞 공백을 제거한 뒤 파일 전체에서 bullet 후보를 찾고, column-0 여부도 header block 여부도 보지 않았다.

앞 공백을 제거한 뒤 **파일 전체**에서 bullet을 찾는 방식이다. task-0054는 이것을
결함으로 판정하고 header block 경계로 바꿨다.

## 왜 아무도 못 잡았나

두 갈래 모두에서 미러가 실제 파서와 반대로 판정한다.

| 구조 | 실제 파서 | 수정 전 미러 |
| --- | --- | --- |
| 들여쓴 continuation (`  - 규칙:`) | 위 필드의 연속으로 무시 | **거부** |
| header block 밖 본문 bullet | 파싱 대상 아님 | **거부** |

그런데 suite의 fixture(`makeScratchTaskContent`)는 **header 7줄이 전부**다. 둘 중
어느 구조도 없어서 미러와 실제 파서가 갈리는 지점이 테스트 입력에 존재하지 않았다.

기존 drift 탐지기 `jarvis_task_parser_contract_mirror_matches_source`도 못 잡는다.
그것이 확인하는 건 필드 어휘·필드명 패턴·줄 마커 리터럴인데, **task-0054는 그 셋을 하나도
바꾸지 않았다.** 바뀐 건 경계이고, 경계에 대응하는 앵커가 없었다.

## 순서 — 검증을 먼저 넣고 실패를 확인했다

수정보다 회귀 검증을 먼저 커밋 대상에 넣어 **실제로 drift를 잡는지** 확인했다.

```
PRE-FIX  (미러 미수정)   total=37 failed=2
  FAIL mirror_honours_task_0054_header_block_boundary
       mirror must accept the task-0054 boundary shape, got: task_file_invalid_metadata
  FAIL mirror_accepts_every_real_task_record
       mirror rejects 13 of 59 real task records that the canonical parser accepts
```

거부된 13건: `task-0042`, `0044`, `0046`, `0047`, `0051`, `0052`, `0053`, `0054`,
`0055`, `0056`, `0057`, `0058`, `0059`. 전부 본문 산문 bullet이 원인이다.

> **수치 정정**: audit 시점 기준선 `d1b27ae`에서는 58건 중 12건이었다. 그 뒤 task-0059
> 기록이 추가됐고 그 기록도 `## 기준선` 절에 본문 bullet을 쓰므로 현재 기준선
> `911e3f7`에서는 **59건 중 13건**이다. 늘어난 1건은 task-0059 자신이다.

## 수정 — Python 구현을 문장 단위로 옮겼다

같은 판단을 같은 순서로 하도록 바꿨다.

| 단계 | 동작 | Python 대응 |
| --- | --- | --- |
| 1 | 들여쓴 줄은 continuation이므로 건너뛴다 | `line[:1].isspace()` |
| 2 | 블록 진입 전, column-0 필드 줄이 아니면 건너뛴다 | `if not in_header` 분기 |
| 3 | 블록 진입 후, column-0 비필드 줄을 만나면 종료한다 | `elif not line.startswith` 분기 |
| 4 | 이후 필드 검사(패턴·어휘·중복)는 기존 그대로 | 무변경 |

빈 줄이 블록을 닫는 동작까지 Python과 같다 — 빈 문자열은 양쪽 다 whitespace 판정이
거짓이라 continuation으로 빠지지 않고 종료 조건으로 간다.

## 차분 검증 — 실제 파서와 65개 입력 대조

의미적 동일성을 주장만 하지 않고 쟀다. 실제 기록 59건 + audit에서 만든 temp fixture 6건
(들여쓴 continuation, 본문 bullet, asterisk/dash append 변형 포함)을 양쪽에 넣고 비교했다.

```
loop 결과 일치 65 / 불일치 0   (수집된 metadata 완전 일치 65건)
```

pass/fail만이 아니라 **수집된 metadata 딕셔너리까지 65건 전부 동일**하다.

## 추가한 것

| 항목 | 역할 |
| --- | --- |
| `mirror_honours_task_0054_header_block_boundary` | 두 구조를 담은 fixture 1개. 저장소에 해당 형태 기록이 없어도 계약을 고정한다. 필드가 본문에서 새어 들어오지 않는지도 확인 |
| `mirror_accepts_every_real_task_record` | 실제 기록 전수. `records.length >= 10` 확인으로 **공허하게 통과하지 않도록** 막았다 |
| drift 탐지기 앵커 2개 | `in_header`, `line[:1].isspace()` — 경계 자체의 표현이라 경계가 다시 바뀌면 사라진다 |

fixture를 약화하거나 기존 검증을 제거하지 않았다. 기존 35개 테스트는 이름·의도·출력이
그대로이며 전부 통과한다.

## 검증

| 검증 | 결과 |
| --- | --- |
| **PRE-FIX** buzz-bridge | 35/37 — 신규 2건이 drift를 잡음 |
| **POST-FIX** buzz-bridge | **37/37 PASS** |
| 실제 파서 차분 | **65/65 일치**, metadata 65건 동일 |
| canonical 전수 | **59/59 PASS** |
| `discord-intake` 스모크 | **82/82 PASS** |
| `bot_minimal` self-check | **79/79 PASS** |
| `audit-chain` | **6/6 PASS** |
| `jarvis-console` 스모크 + self-test | PASS |
| `discord-nl-intent` | 35/35 PASS |
| `validate_multi_agent_sop` | `status=PASS` |
| `check_no_secrets --self-test` | `status=PASS` |
| `git diff --check` | clean |
| `memory/tasks` scratch 잔여 | 0 (suite 기존 cleanup 경로) |

## 이번 단계 비범위

- `*` 마커 — 무변경. task-0059에서 실측한 대로 여전히 필요하다
- Python 파서 · canonical 규칙 · production runtime — 전부 무변경
- `lib/task_append.js` — 무변경
- `jarvis.bat` — 건드리지 않았다
