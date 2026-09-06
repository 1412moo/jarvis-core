# task-0059-task-append-docstring-correction

- id: `task-0059-task-append-docstring-correction`
- title: `buzz-bridge task_append.js docstring을 task-0054 파서 계약에 맞춰 정정`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-06 14:27 UTC`
- updated_at: `2026-09-06 14:27 UTC`
- summary: `task_append.js의 docstring이 task-0054 이전 파서 동작을 근거로 asterisk 마커 규칙을 설명하고 있었다. 근거는 죽었지만 규칙은 살아 있다 — 실측 결과 dash로 바꿔도 metadata read는 통과하고, 대신 run record의 status 필드가 canonical status 줄과 충돌해 전이 writer 두 곳이 fail closed 된다. 진짜 이유를 적었고 마커는 그대로 뒀다. 작성 도중 decoupling guard 테스트가 실패해, 리팩터 대상 함수명을 적는 대신 설명으로 바꿨다.`
- source_command: `read-only audit 후속 작업 A 승인 (Owner)`

## 기준선

HEAD `d1b27ae` = `origin/main`. 변경은 `orchestrator/buzz-bridge/lib/task_append.js`의
**주석 블록 하나**와 이 기록뿐이다. 실행되는 줄은 한 곳도 건드리지 않았다.

## 문제 — 근거는 죽었는데 규칙은 살아 있었다

정정 전 docstring의 주장:

> Jarvis의 파서는 **파일 전체**에서 앞 공백을 제거한 뒤 `- `로 시작하는 모든 줄을
> metadata 후보로 보고 거부한다. 그래서 dash로 쓴 run record는 이후 모든 metadata
> read/transition을 fail closed 시킨다. asterisk는 그 스캔에 **보이지 않는다.**

task-0054가 파서 경계를 바꾼 뒤로 이 문단은 네 군데가 틀렸다.

| | docstring | 실제 |
| --- | --- | --- |
| 탐색 범위 | 파일 전체 | **header block 안에서만** |
| 들여쓴 줄 | 공백 제거 후 후보 | **continuation으로 건너뜀** |
| dash의 결과 | read/transition 모두 실패 | **read는 통과**, 전이만 실패 |
| asterisk의 역할 | 스캔에 안 보임 | dash도 똑같이 안 보임 |

## 실측 — 규칙은 왜 아직 필요한가

저장소 밖 temp tree에서 **실제 appender를 그대로 실행**해 얻은 바이트로 재봤다.

| writer | asterisk(현재) | dash(반사실) |
| --- | --- | --- |
| metadata read | PASS | **PASS** |
| 상태 전이 | `updated` | **`hold` / `task_file_invalid_status_metadata`** |
| 실행 결과 기록 | `recorded` | **`hold` / 같은 사유** |
| 완료 증거 기록 | `recorded` | `recorded` |

원인을 격리했다. run record에는 `status`라는 필드가 있어서 dash로 쓰면 본문에 두 번째
column-0 `- status:` 줄이 생긴다. 전이 writer 두 곳이 그 줄의 **유일성**을 요구한다.

**결정적 확인**: 그 필드 이름만 `run_status`로 바꾸면 dash로도 전이가 성공한다. 즉 마커가
아니라 **이름 충돌**이 원인이며, 마커는 그 충돌을 피하는 수단이다.

그래서 "이 모듈이 절대 되돌리면 안 되는 하나의 형식 규칙"이라는 취지는 그대로 뒀다.
**틀린 것은 근거였지 결론이 아니었다.**

## 작성 도중 테스트가 나를 막았다

초안에서 전이 writer들을 함수명 그대로 적었더니 buzz-bridge suite가 실패했다.

```
FAIL task_append_G_buzz_bridge_source_never_calls_jarvis_task_lifecycle_functions
     lib	ask_append.js must not reference "transition_task_file_status("
```

이 테스트는 buzz-bridge 소스에 Jarvis lifecycle 함수명이 **문자열로도 존재하지 않는다**는
것을 단순 검색으로 증명한다. 주석에 이름을 적으면 그 증명이 깨진다. 테스트가 옳고 내
초안이 틀렸다.

그래서 함수명을 쓰지 않고 **역할로 서술**했고, 나중에 누가 "친절하게" 이름을 되돌려
넣지 않도록 그 이유를 docstring 안에 남겼다. 가드 테스트는 손대지 않았다.

## 검증

| 검증 | 결과 |
| --- | --- |
| `buzz-bridge` 스모크 | **35/35 PASS** (`task_append` 관련 11건 전원 포함) |
| 금지 토큰 3종 잔존 | **0건** |
| JS 구문 검사 | OK |
| canonical 전수 | **58/58 PASS** |
| `discord-intake` 스모크 | **81/81 PASS** |
| `bot_minimal` self-check | **79/79 PASS** |
| `audit-chain` | **6/6 PASS** |
| `jarvis-console` 스모크 + self-test | PASS |
| `discord-nl-intent` | 35/35 PASS |
| `validate_multi_agent_sop` | `status=PASS` |
| `check_no_secrets --self-test` | `status=PASS` |
| `memory/tasks` scratch 잔여 | 0 (suite 기존 cleanup 경로) |
| diff | 주석 블록 1개, 실행 코드 0줄 |

## 이번 단계 비범위

- **asterisk 마커** — 바꾸지 않았다. 실측으로 여전히 필요하다
- **JS mirror(`run_smoke_tests.js`)** — `mirrorTransitionMetadataParse()`가 아직 task-0054 이전 규칙을 구현한다. 실제 기록 58건 중 12건을 거부하는데 fixture에 해당 형태가 없어 suite는 통과한다. **작업 B로 분리**한다
- Python 파서·canonical 규칙·테스트 fixture — 전부 무변경
- `jarvis.bat` — 건드리지 않았다
