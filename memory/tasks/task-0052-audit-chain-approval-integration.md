# task-0052-audit-chain-approval-integration

- id: `task-0052-audit-chain-approval-integration`
- title: `승인·실행 경로를 task-0044 감사 해시체인에 연동`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-05 10:20 UTC`
- updated_at: `2026-09-05 12:40 UTC`
- summary: `task-0044가 만든 감사 해시체인 코어를 실제 승인·실행 경로에 연결한다. task-0044는 코어(스키마·저장소·검증·CLI)를 만들었을 뿐 호출자가 없어 체인이 비어 있었고, 이 task가 그 호출자를 붙인다. Owner 결정 7건 승인 후 구현 완료, 검증 전건 PASS. 결정 ②는 구현 중 발견한 writer 스키마 비호환으로 범위가 축소 재결정됐다(승인 전이만 durable writer). 구현·검증·커밋까지 완료.`
- source_command: `task-0044 결정 3(a)가 분리한 후속 연동 task`

## 기준점

- 선행 커밋 `116fe2d` — task-0044 감사 해시체인 코어(이 task에서 수정하지 않음)
- 설계 기준점 `3c5ee1b` — `docs/task-0052-audit-chain-approval-integration-design.md` Owner 결정 정본
- 이 task의 구현은 `3c5ee1b` 위에서 이루어졌다

## task-0044와의 구분 (과장하지 않기 위해 명시)

| | 범위 |
| --- | --- |
| **task-0044** | 감사 해시체인 **코어** — 항목 스키마, canonical JSON, 도메인 분리 해시, 저장소 밖 append-only 저장, 무결성 검증, CLI. 호출자는 없었고 체인은 비어 있었다 |
| **task-0052 (이 task)** | 그 코어를 **승인·실행 경로에 연동**. 새 스키마·새 감사 기능을 만들지 않았다 |

이 task로 체인에 기록이 실제로 쌓이기 시작한다. 다만 **대상은 `/approve`·`/run`·`/retry`
경로뿐**이며, task-0044 결정 2가 정한 A+B(`owner_approval` + `execution_result`) 범위를
넓히지 않았다.

## Owner 결정 7건과 실제 반영 결과

| # | 결정 | 실제 반영 |
| --- | --- | --- |
| ① | (ii-b) 전이 먼저 → 감사, 롤백 없음 | `_build_approve_writer_result`에서 전이 적용 후 append. 실패 시 롤백하지 않고 승인을 실패로 응답 |
| ② | (d) `transition_task_file_status()` 재사용 | **A로 범위 축소 재결정**(아래 참조). 승인 전이 2쌍에만 적용 |
| ③ | 실패한 승인 시도도 기록 | `applied:false` + `reason`으로 기록. `apply_not_ready`, `task_not_found`, `status_mismatch` 등 |
| ④ | `result_kind`는 기존 `failure` 사용, 새 vocabulary 금지 | `executed and success` → `success`, 그 외 `failure`. 세부 구분은 기존 `execution_not_executed` 등이 담당 |
| ⑤ | (⑤-b) reject의 실행 흐름 진입 차단 | `decision == "reject"`면 `_run_execution_flow` 미호출 |
| ⑥ | 서명 미부착 | 부착하지 않음. `orchestrator` 역할 키를 만들지 않았다 |
| ⑦ | 외부 노출은 stable code만 | 응답에는 `code`만, `detail`은 stderr 로컬 진단으로만 |

## 결정 ②가 A로 재결정된 과정

### 발견 1 — 전이 표는 3쌍이 아니라 4쌍이다

설계 초판 §9.2는 "`FAILED→TODO`는 이 경로들이 안 쓰므로 추가하지 않는다"고 적었다.
**틀렸다.** `_run_retry`(1054행)가 재실행 준비로 `FAILED→TODO`를 수행한다. 첫 구현에서 retry
계열 self-check가 실패해 드러났고, **4쌍**으로 정정했다.

이 누락이 숨을 수 있었던 이유 자체가 문제였다 — `_validate_approve_transition_contract_sync()`가
`bot_minimal` 내부 표만 대조하고 `task_file_writer` 쪽 표는 보지 않았다. 그래서 이 검사를
**두 모듈 대조로 확장**했다(`approve_contract_writer_transition_missing`).

### 발견 2 — writer 스키마 비호환 (범위 축소의 직접 원인)

`transition_task_file_status`는 전이 전에 `_transition_metadata`로 파일 전체를 검증하고
**허용 목록 밖 metadata 필드가 하나라도 있으면 거부**한다. 그런데
`_write_execution_review_metadata`가 **두 전이 사이에** 실행 메타데이터를 쓴다.

```text
승인 전이 NEEDS_APPROVAL→DOING   ← 파일이 깨끗해 통과
  → 실행 → _write_execution_review_metadata  ← 13개 필드 기록
  → 실행결과 전이 DOING→DONE      ← task_file_unsupported_metadata 로 거부
```

실측 비호환 4건:

| 비호환 | 내용 |
| --- | --- |
| 미허용 필드 5개 | `error`, `mode`, `reason`, `message`, `execution_status` |
| 타입 불일치 | `execution_candidate` — writer는 boolean 분류, bot_minimal은 JSON 기록 |
| 빈 값 거부 | `error`/`reason`이 빈 문자열인데 writer는 `allow_empty=False` |
| 길이 상한 | writer text 상한 500자, `execution_result` 실측 419자 (여유 거의 없음) |

실행결과 전이까지 적용하려면 **필드 추가·타입 재분류·빈 값 허용·길이 상향** 네 가지 완화가
필요했다. 이는 설계 초판이 내세운 "추가일 뿐 완화가 아니다"라는 근거와 정면으로 어긋난다.
**임의로 진행하지 않고 중단해 보고했고**, Owner가 A(범위 축소)를 승인했다.

이 발견은 **승인 경로가 애초에 왜 이 writer를 쓰지 않았는지**도 설명한다.

## `task_file_writer` metadata 검증은 완화하지 않았다

Owner 재결정 4항에 따라 **필드 추가·타입 재분류·빈 문자열 허용 확대·길이 제한 완화를 모두
하지 않았다.** `task_file_writer.py`의 변경은 `TASK_STATUS_TRANSITIONS`에 4쌍을 추가한 것과
그 주석뿐이다.

## 최종 범위 — 어느 전이가 durable writer를 쓰는가

| 전이 | writer | 근거 |
| --- | --- | --- |
| `NEEDS_APPROVAL→DOING` | ✅ **durable** | 감사 체인이 놓이는 토대 |
| `NEEDS_APPROVAL→FAILED` | ✅ **durable** | 위와 같음 |
| `DOING→DONE` | ⬜ 기존 경로 유지 | 실행 메타데이터 기록 뒤라 writer 스키마와 비호환 |
| `DOING→FAILED` | ⬜ 기존 경로 유지 | 위와 같음 |
| `FAILED→TODO` (retry 준비) | ⬜ 기존 경로 유지 | 이전 실행 메타데이터가 이미 있어 같은 이유 |
| `TODO→DOING` (retry 준비) | ⬜ 기존 경로 유지 | 위와 같음 |

구현은 `_apply_task_status_transition`이 `DURABLE_STATUS_TRANSITIONS`(승인 2쌍)로 분기하고
나머지는 원본 그대로인 `_apply_task_status_transition_inline`을 탄다. `(bool, reason)` 계약과
사유 어휘(`task_not_found` / `status_mismatch` / `write_failed`)는 **바뀌지 않아** 호출부가
이 분기를 알 필요가 없다.

**실행결과 전이가 여전히 `write_text()` 위에 있는 것은 알려진 잔여 위험이다**(아래 "알려진 한계").

## 감사 기록 지점

| | kind | 위치 | 비고 |
| --- | --- | --- | --- |
| **E1** | `owner_approval` | `_build_approve_writer_result` — 전이 시도 직후 | 성공·실패 모두 기록(결정 ③). `apply_not_ready`는 전이 시도 전이지만 전이 쌍이 확정돼 있어 기록 가능 |
| **E2** | `execution_result` | `_run_execution_flow` 반환 직전 — **단 한 곳** | `/approve`·`/run`·`/retry` 세 경로가 모두 이 함수를 지나므로 자동 포함 |

E2를 호출부 3곳에 각각 심지 않은 이유: 나중에 네 번째 호출부가 생기면 **조용히 감사에서
빠진다.** 그것이 지금 `/run`·`/retry`가 `/approve`를 우회하는 것과 같은 실패 양식이다.

## P2-4 신원 비노출 불변식 유지

`bot_minimal.py`의 P2-4 주석은 승인 경계가 `on_message()`의 게이트 **한 곳**에만 있고
승인 파이프라인은 **신원을 모르는 채로 둔다**고 못박고 있다. 이 task는 그 불변식을 지켰다.

- 감사 훅은 **인가 판단을 하지 않는다.** 두 번째 신원 경계를 만들지 않았다.
- payload에 Discord user id를 담지 않는다. task-0044의 `FORBIDDEN_PAYLOAD_KEYS`가
  `user_id`/`author_id`/`discord_user_id`/`owner_id`를 스키마 차원에서 거부하며,
  self-check `audit_payload_has_no_owner_identity`가 기록된 payload에 그 키가 없음을 검증한다.

## `reject` 실행 버그 (⑤-b) — 수정 전/후

이 수정은 **감사 연동이 아니라 의미론 버그 수정**이며, 같은 승인 경로에서 실제 실행을
막기 위해 이번 task에 포함했다.

### 수정 전 (`116fe2d`)

`_build_approve_draft`가 reject를 `apply_ready=True`로 만들고,
`_build_approve_writer_result`가 **decision과 무관하게** `_run_execution_flow`를 호출하며,
`_build_execution_candidate`는 status를 보지 않고 title/summary 키워드만 본다. 그 결과
화이트리스트에 걸리는 task를 거부하면 **서브프로세스가 실행됐다.** 이어지는 `DOING→…` 전이는
현재 status가 `FAILED`라 `status_mismatch`로 조용히 실패했다.

### 실측 대조

```text
[수정 전 116fe2d] executed=True   candidate=yes  reason='transition_not_applied:status_mismatch'
[수정 후        ] executed=None   candidate=no   reason='execution_skipped_on_reject'
```

**수정 전에는 실행이 일어났고, 전이는 안 됐고, 기록도 없었다.**

전역 status 게이트(⑤-c)는 `/run`·`/retry` 동작까지 바꾸므로 **하지 않았다**(범위 밖).

## `apps/jarvis-console` 계약 테스트 갱신 — 전이 표 확장의 필연적 영향

설계 문서에 없던 세 번째 모듈 영향이다.

`apps/jarvis-console/run_web_app.py`(65행)가 `transition_task_file_status`를 **그대로
재수출**하고 있었고, `run_smoke_tests.py`가 "허용 전이는 `TODO→DOING`·`DOING→DONE` 둘뿐"을
고정하는 계약 테스트를 갖고 있었다. 전이 표를 4쌍 넓히자 이 테스트가 깨졌다.

- **콘솔의 사용자 노출 동작은 바뀌지 않는다.** 콘솔은 자체 액션 맵(`run_web_app.py:292-293`)으로
  start(`TODO→DOING`) / complete(`DOING→DONE`) 두 가지만 제공하며 그것이 실제 관문이다.
- 따라서 갱신 대상은 계약 테스트 하나뿐이었고, **승인된 6쌍을 명시적으로 나열**하도록 고쳤다.
  writer에서 import해 오도록 만들지 않았다 — 그러면 항진명제가 되어 계약 테스트의 가치가
  사라진다. 앞으로 누가 더 넓히면 이 지점에서 다시 걸린다.

## 검증 (2026-09-05)

| 검증 | 결과 |
| --- | --- |
| `bot_minimal` self-check | **77/77 PASS** — 기존 63건 전부 유지 + 신규 14건 |
| `orchestrator/audit-chain` 스모크 | **6/6 PASS** |
| 기존 회귀 10종 | **전건 PASS** — team-manager-bot, daily-ai-radar, hermes-manager-pilot, jarvis-console, research-council, discord-intake, discord-nl-intent, buzz-bridge(35/35), role-signing(38/38), `validate_multi_agent_sop.py` |
| reject 차단 전/후 대조 | `116fe2d` `executed=True` → 수정 후 `candidate=no` |
| E2E | approve → `owner_approval`+`execution_result` 2건 / reject → `owner_approval` 1건만 / `verify-chain valid` |
| **실제 감사 체인 오염** | **없음.** `cli.py status`가 `exists: false`, `length: 0` |

### 실제 체인이 오염되지 않은 이유

self-check가 승인 경로를 실행하면 감사 append가 일어나고, 체인은 환경에서 저장 위치를
스스로 정한다. 격리가 없으면 테스트가 Owner의 **되돌릴 수 없는 append-only 체인**에
테스트 항목을 남긴다. 그래서 self-check 임시 블록 전체에 `JARVIS_LOCAL_STATE_DIR`을
임시 경로로 지정하고 종료 시 복원한다.

### 신규 self-check 14건

감사 기록 존재 · 체인 검증 · payload에 owner identity 부재 · reject 미실행 · reject
메타데이터 미생성 · reject 감사 항목 1건 · append 실패 시 승인 거부 · **롤백 안 함(DOING 유지)** ·
**reason에 detail 미유출** · 재시도 `status_mismatch` 차단 · 실패 시도 기록 · durable 분기 ·
writer 전이 표 드리프트 탐지.

## 알려진 한계

### 1. 감사 append 실패 시 `DOING` 고착 (결정 ①의 의도된 결과)

전이가 적용된 뒤 append가 실패하면 **롤백하지 않는다.** 그 결과:

- `/approve`는 **실패로 응답**한다(성공으로 보고하거나 삼키지 않는다). 사유는 stable code만.
- task 파일은 `DOING`으로 남고 체인에는 기록이 없다 — **의도된 가시적 불일치**다.
- 자동 재시도는 `NEEDS_APPROVAL→DOING`만 허용되므로 `status_mismatch`로 **구조적으로 막힌다.**
  이는 결함이 아니라 이중 실행·중복 기록을 막는 안전장치다.
- **복구는 Owner의 수동 편집뿐이고, 그 수동 편집 자체는 감사 체인에 남지 않는다.**
  이것이 이 설계가 감수한 공백이며, 숨기지 않고 계약으로 명시한다.

불일치 탐지 도구("`DOING`인데 승인 기록이 없는 task" 조회)는 **만들지 않았다**(범위 밖).

### 2. 실행결과 전이는 여전히 비원자적 쓰기 위에 있다

`DOING→DONE`/`DOING→FAILED`와 retry 준비 전이는 `write_text()`를 쓴다. 해소하려면
`_write_execution_review_metadata`의 형식을 writer 스키마에 맞추는 **별도 task**가 필요하다.

### 3. 스키마상 기록 불가한 조기 실패

`owner_approval` payload는 유효한 전이 쌍을 요구하므로, 전이 쌍이 확정되기 전에 거부되는
실패(`invalid_writer_input`, `approve_contract_mismatch`, `/approve` 파싱 실패)는
**기록되지 않는다.** 담으려면 task-0044 결정 2의 재개방이 필요해 하지 않았다.

### 4. E2 감사 실패는 작업을 되돌릴 수 없다

E2 지점에서는 서브프로세스가 이미 실행된 뒤다. append가 실패해도 되돌릴 수 없으므로
계약이 "작업 실패"가 아니라 **"크게 보고한다"**로 축소된다(`audit_error`를 결과에 실어 전달).
실행 사실 자체는 task 파일 실행 메타데이터에 남는다.

## 변경 파일

| 파일 | 내용 |
| --- | --- |
| `adapters/discord/bot_minimal.py` | durable 분기, 드리프트 검사 확장, E1/E2 감사 훅, `command`/`decision` 배선, ⑤-b 차단, self-check 격리 + 14건 |
| `orchestrator/discord-intake/task_file_writer.py` | `TASK_STATUS_TRANSITIONS` 4쌍 추가(+주석). **metadata 검증 무변경** |
| `apps/jarvis-console/run_smoke_tests.py` | 계약 테스트의 허용 전이 집합을 승인된 6쌍으로 갱신 |
| `docs/task-0052-audit-chain-approval-integration-design.md` | §9.2/§10.3 재결정 반영(커밋 `3c5ee1b` 이후 추가 정정 포함) |

## 이번 단계 비범위

- ⑤-c 전역 status 게이트 — `/run`·`/retry` 동작까지 바꾼다
- 실행결과 전이의 내구성 개선 — writer 스키마 비호환(별도 task)
- `task_file_writer` metadata 검증 완화 — 명시적으로 금지
- 불일치 탐지 도구 / 수동 복구 명령
- 감사 체인 서명 — 결정 ⑥
- C~F 대상 확대 — task-0044 결정 2가 A+B로 한정
- task-0044 코어 수정 — `116fe2d`을 기준점으로 유지

## 커밋

Owner 승인 후 커밋했다. 커밋에는 tracked 변경 4개(`bot_minimal.py`, `task_file_writer.py`,
`apps/jarvis-console/run_smoke_tests.py`, 설계 문서)와 이 기록이 들어간다. `jarvis.bat`은
protected file이라 stage하지 않았다.

커밋 전 최종 확인: staged diff에 metadata 검증 완화 없음(설계 문서 산문과 diff 컨텍스트
줄만 해당 심볼을 언급), 범위 밖 변경 없음, 감사 항목 중복 기록 없음 — approve 2건
(`owner_approval`+`execution_result`), reject 1건(`owner_approval`), `/run`·`/retry` 각 1건
(`execution_result`)을 실측 확인했다.
