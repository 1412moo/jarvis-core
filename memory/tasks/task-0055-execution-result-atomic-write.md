# task-0055-execution-result-atomic-write

- id: `task-0055-execution-result-atomic-write`
- title: `실행 메타데이터와 결과 전이를 한 번의 원자적 쓰기로 (U2)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-05 18:00 UTC`
- updated_at: `2026-09-06 11:05 UTC`
- summary: `task-0053이 U1로 모든 상태 전이를 durable writer로 보냈지만 실행 메타데이터 쓰기 1회가 명령마다 비원자로 남았다. 두 쓰기 사이에서 중단되면 실행은 성공으로 기록되고 task는 DOING인 자기모순 상태가 남는 것을 실측으로 재현했다. U2는 두 쓰기를 하나의 os.replace로 합쳐 그 창을 닫는다. 전이가 일어나지 않는 정상 조합도 지원해야 하며, durable 꼬리가 이미 두 벌이라 세 번째 복제를 피하는 구현 형태가 핵심 결정이다. Owner가 C(꼬리 추출 후 새 함수)와 추천안 전부를 승인해 구현·검증까지 완료했다. 실행 경로의 비원자 쓰기가 0이 됐다.`
- source_command: `task-0053 §10.2 결정 A가 별도 결정으로 남긴 U2`

## 기준선

- HEAD `41501a5` = `origin/main`
- 선행: `41501a5`(task-0053 U1), `38b9027`(task-0054 경계), `a6c4ef3`(task-0052 감사 연동)
- 변경: `orchestrator/discord-intake/task_file_writer.py`, `adapters/discord/bot_minimal.py`, 설계 문서, 이 기록

## 무엇이 남았는가

task-0053이 U1을 끝내 **모든 상태 전이**가 durable writer를 통과한다. 그러나 명령마다
**비원자 쓰기 1회**가 남는다 — 실행 메타데이터 쓰기다.

| 명령 | 쓰기 | 원자 | 비원자 |
| --- | --- | --- | --- |
| `/approve … approve` | 3 | 2 | **1** |
| `/run` | 2 | 1 | **1** |
| `/retry` | 4 | 3 | **1** |

U2는 그 쓰기를 없애는 것이 아니라 **실행결과 전이와 하나의 `os.replace`로 합치는 것**이다.
두 쓰기는 논리적으로 한 사건이다.

## 🔴 U2가 닫는 창 (실측)

메타데이터 쓰기 직후·전이 직전에 중단시켜 남는 상태를 측정했다.

| 시나리오 | task status | 실행필드 | canonical | 판정 |
| --- | --- | --- | --- | --- |
| 정상 완주 | `DONE` | 8 | PASS | 일치 |
| **중간 중단** | **`DOING`** | **8** | PASS | 🔴 **자기모순** |

중단 상태에서 `/status`가 실제로 보여주는 것:

```text
execution_status = 'success'    ← 실행은 성공으로 기록됨
task status      = 'DOING'      ← 그런데 완료되지 않음
```

완주한 흐름에서는 나올 수 없는 조합인데 **파일은 canonical 검증을 통과하므로 어떤 검사도
잡지 못한다.**

부수 이득 — 현재 메타데이터 쓰기에는 `expected_digest` 검사가 **없고** 전이는 그 쓰기 *이후*에
digest를 계산한다. 합치면 **하나의 digest가 두 변경을 모두 덮어** 동시성 안전이 강해진다.

## 반드시 지원해야 하는 조합 — 전이 없는 정상 상태

U2를 "항상 전이한다"로 만들면 정상 동작이 깨진다. 실측:

```text
화이트리스트 미등록 → executed=False
  → 메타데이터는 쓰인다 (execution_status=not_executed)
  → 전이는 없다 (status=DOING 유지)
  → 상태=DOING 실행필드=8 canonical=PASS  ← 모순이 아니라 정상
```

§2의 모순과 이 정상 상태는 **파일 모양이 같다.** 구별은 `execution_status` 값이 한다 —
`success`/`failed`면 모순, `not_executed`면 정상.

## 필요한 능력과 제약

| 함수 | 변형 방식 |
| --- | --- |
| `transition_task_file_status` | `- status:` / `- updated_at:` 2개 정규식 치환 |
| `record_task_completion_evidence` | 필드 1개 삽입(고정 위치) + `updated_at` 치환 |
| `_write_execution_review_metadata` | 8개 필드 insert-or-update, 헤더 블록 끝 — **비원자** |

U2는 이 셋의 합집합이 필요하다: **8개 insert-or-update + status/updated_at 치환 + 전이 생략
모드**, 하나의 `os.replace`로.

**값 검증이 추가로 필요하다.** 기존 전이 함수는 원본만 검증하는데, status/updated_at은 이미
검증된 값이라 구성상 안전했다. 실행 필드 값은 **서브프로세스 출력에서 오므로** 쓰기 전 검증이
필요하다. 이는 완화가 아니라 강화이며 `_completion_evidence_is_valid` 선례가 있다.

**durable 꼬리가 이미 두 벌이다.** 두 함수의 temp+fsync+replace 꼬리를 비교했다:

```text
transition 78행  vs  evidence 91행   유사도 73%
차이는 temp 접미사·결과 타입·reason 접두사뿐
```

U2를 세 번째 독립 함수로 만들면 **꼬리가 세 번째 복제된다.** task-0053이 별도 execution
writer를 거부한 근거가 "내구성 원시코드를 두 벌 갖게 된다"였으므로 세 벌은 더 나쁘다.

## 선택지와 권장 (상세는 설계 문서 §5·§6)

| | 선택지 | 판정 |
| --- | --- | --- |
| A | 기존 전이 함수에 필드 인자 추가 | ❌ 승인 경로 함수의 책임이 넓어지고, 전이 없이 부르는 "전이 함수"가 된다 |
| B | 새 함수, 꼬리 세 번째 복제 | ⭕ 회귀 위험 최소, 그러나 중복이 커진다 |
| **C** | **꼬리 추출 후 새 함수** | ✅ **권장** — 중복 없음 |
| D | 하지 않는다 | ❌ 모순 창이 남고 탐지 도구도 없다 |

**권장 C**, 단 꼬리 추출을 **동작 변경 없는 순수 추출**로 한정하고 기존 두 함수의 테스트가
**수정 없이** 통과하는 것을 착수 조건으로 삼는다. 원칙 6이 막는 것은 "요청되지 않은"
리팩터링인데 이 추출은 U2 구현에 직접 필요하다. 부담스러우면 B가 합리적 차선이며, 그때는 세
번째 복제와 장차 갈라질 위험을 문서에 남긴다.

## 실패 semantics

task-0052 계약을 바꾸지 않는다. U2가 바꾸는 것은 **실패 지점의 개수**뿐이다 — 실패 지점 3(메타
기록)과 4(결과 전이)가 하나로 합쳐지고 **파일이 중간 상태로 남지 않는다.** 합쳐진 지점에서도
서브프로세스는 이미 실행됐고 되돌릴 수 없으므로 계약은 그대로 "크게 보고한다"이며 **새로운
자동복구를 추가하지 않는다.**

## Owner 결정 (2026-09-06 확정)

| # | 결정 |
| --- | --- |
| 1 | **C** — 꼬리 추출 후 새 함수 |
| 2 | `target_status=None`이면 메타데이터만 |
| 3 | 결과 필드 검증은 writer 내부에서 |
| 4 | `_write_execution_review_metadata` 제거 후 새 writer로 대체 |
| 5 | 착수 승인 |


## 구현 결과 (2026-09-06)

Owner 결정: 1=**C**, 2·3·4=추천안, 5=착수 승인. 기준선 `41501a5`.

### 1. durable 꼬리 추출 (결정 1의 C)

`_atomically_replace_task_file()`을 추가하고 `transition_task_file_status`와
`record_task_completion_evidence`가 그것을 쓰도록 바꿨다. 실패 키만 돌려주고 접두사는 호출부가
붙이므로 **기존 reason code는 그대로**다.

착수 조건이었던 "기존 두 함수의 테스트가 수정 없이 통과"를 충족했다 — 추출 직후
`discord-intake`와 `jarvis-console` 스모크가 그대로 통과했다.

**한 가지는 의도적으로 위로 맞췄다**: `record_task_completion_evidence`에는 short write 검사가
있었고 `transition_task_file_status`에는 없었다. 헬퍼는 검사를 유지하므로 **전이 경로가 그
검사를 얻는다.** 약화가 아니라 강화이며, 숨기지 않고 헬퍼 docstring에 적었다.

### 2. 새 writer — `record_task_execution_result()`

8개 실행 필드 insert-or-update + 선택적 status 전이 + `updated_at` 갱신을 **한 번의
`os.replace`**로 처리한다.

- **결정 2**: `target_status=None`이면 메타데이터만 쓴다. 실행이 일어나지 않은 경우
  (`execution_not_executed`)가 정상 조합이기 때문이다
- **결정 3**: 실행 필드 값을 **쓰기 전에** 검증한다. 값이 서브프로세스 출력에서 오기 때문이며,
  `transition_task_file_status`가 원본만 검증해도 됐던 것과 다르다
- 삽입 위치는 task-0054의 헤더 블록 경계를 바이트 단위로 그대로 따른다
- 기존 필드는 파일 어디에 있든 제자리 치환한다 — 헤더 밖 복사본이 있는 파일에서 중복이 나지
  않게 하기 위해서다
- **쓰기 직전 결과 전체를 `_transition_metadata`로 다시 검증한다.** 쓰기가 원자적이므로 검증을
  통과하지 못할 파일이 디스크에 닿아서는 안 된다

### 3. `bot_minimal` 연결 (결정 4)

`_write_execution_review_metadata`를 **제거**하고 `_apply_execution_result()`가 단일 호출로
대체한다. 비원자 경로를 남기지 않는다.

## 검증 (2026-09-06)

### 창이 닫혔는가 — 쓰기 실패 주입 대조

| | `41501a5` (U2 이전) | 현재 |
| --- | --- | --- |
| task status | `DOING` | `DOING` |
| 실행필드 | **8** | **0** |
| `execution_status` | **`'success'`** | `None` |
| 판정 | 🔴 자기모순 | ✅ **원본 그대로** |

호출부 보고는 `applied=False reason='transition_not_applied:write_failed'`로 계약을 지킨다.

### 쓰기 횟수와 원자성

| 명령 | `41501a5` | 현재 |
| --- | --- | --- |
| `/approve … approve` | 3회 (원자 2) | **2회 (원자 2)** |
| `/run` | 2회 (원자 1) | **1회 (원자 1)** |
| `/retry` | 4회 (원자 3) | **3회 (원자 3)** |

**실행 경로의 비원자 쓰기가 0이 됐다.**

### 전이 생략 모드

`executed=False`에서 메타데이터만 쓰이고 전이는 없으며 `execution_status='not_executed'` +
`status=DOING`으로 일관된다. 쓰기 1회, 전부 원자.

### 쓰기 전 검증 (결정 3)

| 주입 | 결과 | 파일 |
| --- | --- | --- |
| 제어문자(탭) | `hold` `task_file_invalid_text` | 불변 |
| 길이 초과(501자) | `hold` `task_file_field_too_long` | 불변 |
| 빈 값 | `hold` `task_file_invalid_text` | 불변 |
| 잘못된 불리언 | `hold` `task_file_invalid_text` | 불변 |
| 미지원 필드 | `hold` `unsupported_execution_field` | 불변 |

### 동시성

쓰기 직전 외부 변경을 주입하면 `stale` / `task_changed_since_preview`로 거부된다.
**하나의 digest가 두 변경을 모두 덮는다** — 이전에는 메타데이터 쓰기에 digest 검사가 아예
없었다.

### 그 외

| 검증 | 결과 |
| --- | --- |
| 출력 동일성(`41501a5` 대비 4종) | **완전 일치** |
| `bot_minimal` self-check | **77/77 PASS** |
| `discord-intake` 스모크 | **78/78 PASS** |
| `audit-chain` | **6/6 PASS** |
| 기존 회귀 8종 + SOP | 전건 PASS |
| canonical 전수 | 대상 55 중 PASS 47 / FAIL 8(backtick, 보류) |

self-check의 `execution_status_transition_failure_non_blocking`은 주입 지점을
`_apply_task_status_transition`에서 새 writer의 replace seam으로 옮겼다. **단언은 그대로다** —
실행결과 전이 실패가 성공한 승인을 실패로 바꾸지 않는다.


## 후속 정정 — `DOING → FAILED` 전이표 등재 (2026-09-06)

task-0053 구현 중 발견해 보류했던 불일치를 최소 범위로 정정했다.

`_apply_execution_result()`는 실행이 실패하면 task를 `FAILED`로 옮기는데, 그 전이가
`ALLOWED_STATUS_TRANSITIONS`에는 **없었다.** task-0053은 `DURABLE_STATUS_TRANSITIONS`를
`task_file_writer`의 전이표 기준으로 잡아 우회했고, 그 우회는 **그대로 두었다.**

### 변경

| 항목 | 내용 |
| --- | --- |
| 전이표 | `"DOING": ("DONE",)` → `("DONE", "FAILED")` |
| 우회 로직 | **제거하지 않음** — `DURABLE_STATUS_TRANSITIONS = TASK_STATUS_TRANSITIONS` 유지 |
| 두 표의 관계 | 이제 **완전히 일치**한다(6쌍). 이전에는 겹치기만 했다 |

### 테스트

`DOING → FAILED`의 **실경로는 이미 검증되고 있었다** — `execution_status_transition_failed`가
실행 실패를 주입해 상태가 `FAILED`가 되는 것을 확인한다. 누락된 것은 검증표 등재뿐이었다.

다만 기존 `invalid_transition` 테스트가 **`DOING → FAILED`를 무효의 반례로 쓰고 있었다.**
표와 코드가 어긋난 채 유지된 이유가 바로 이것이다. 반례를 실제로 표에 없는 `DONE → DOING`으로
바꾸고 최소 검증 2건을 더했다.

| 신규 테스트 | 내용 |
| --- | --- |
| `execution_failure_transition_allowed` | `DOING → FAILED`가 검증을 통과하는지 |
| `transition_tables_agree` | 우회 로직이 표와 **일치**하는지(보상하는 게 아니라) |

self-check 77 → **79/79**.

### 동작 불변 확인 (`3f76d6d` 대비)

| 경로 | 기준선 | 현재 |
| --- | --- | --- |
| `/approve` | `NEEDS_APPROVAL → DONE` | 동일 |
| `/approve reject` | `NEEDS_APPROVAL → FAILED`, 실행 미진입 | 동일 |
| `/run` | `DOING → DONE` | 동일 |
| `/retry` | `FAILED → DONE` | 동일 |
| `/run` 실행 실패 | `DOING → FAILED` | 동일 |

`/status`·`/review-task` 4종 응답도 **완전 일치**. discord-intake 78/78, audit-chain 6/6,
기존 회귀 8종 + SOP 전건 PASS.

## 이번 단계 비범위

- canonical validation 완화 / `allow_empty` 확대 / max length 확대 / 타입 검증 우회
- 새 canonical 필드 추가(task-0053 결정 2 유지), audit event schema 변경(task-0052 계약 유지)
- **명령 전체 원자성(U3)** — 서브프로세스가 중간에 있어 구조적으로 불가능
- 불일치 탐지 도구 / 수동 복구 명령
- backtick 8건 — Owner 보류 (`DOING→FAILED` 누락은 위 후속 정정에서 해소)
- `/run`·`/retry` 의미론 변경, ⑤-c 전역 status gate

## 남은 것

**U3(명령 전체 원자성)은 구조적으로 불가능하다** — 준비 전이와 결과 전이 사이에 되돌릴 수 없는
서브프로세스가 있다. `/approve` 2회·`/retry` 3회의 쓰기는 각각 원자적이되 서로 묶이지 않으며,
이는 구현 한계가 아니라 문제의 성질이다.
