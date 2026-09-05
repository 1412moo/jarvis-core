# task-0053-execution-result-durable-transition

- id: `task-0053-execution-result-durable-transition`
- title: `실행결과 전이에 durable writer 적용 (canonical schema 경계 정리)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-05 13:10 UTC`
- updated_at: `2026-09-05 17:30 UTC`
- summary: `task-0052가 승인 전이만 durable writer로 옮기고 남긴 잔여 약점 — 실행결과 전이가 비원자적 write_text() 위에 있는 문제 — 를 해소했다. Owner 결정 8건에 이어 C·B·A를 실측 기반으로 확정하고 그 순서로 구현했다. C=실행 메타데이터를 헤더 블록 안에 기록해 판독부와 검증기의 인식 범위를 일치시켰다. B=중복 5필드를 파일에서 제거하고 판독 시 파생해 사용자 출력을 그대로 유지했다. A=모든 전이를 durable writer로 보냈다(U1). 명령 전체 원자성(U3)은 서브프로세스가 중간에 있어 구조적으로 불가능하고, 통합 원자성(U2)은 Owner가 별도 결정으로 남겼다. 구현·검증 완료.`
- source_command: `task-0052 §10.3이 별도 task로 분리한 잔여 위험`

## 기준선

- HEAD `38b9027` = `origin/main` (task-0054 hotfix 반영 후)
- 선행: `a6c4ef3`(task-0052 승인 전이 durable), `116fe2d`(task-0044 감사 체인 코어)
- 이 단계 산출물: 설계 문서 + 이 기록. **코드 변경 없음**

지시받은 기준선 목록 중 `docs/task-0044-audit-chain-design.md`는 존재하지 않는다. 실제
파일명은 `docs/task-0044-audit-hash-chain-design.md`이며 그것을 읽었다.

## 이 task가 다루는 것

task-0052 §10.3이 남긴 잔여 위험 하나다.

| | 상태 |
| --- | --- |
| 승인 전이(`NEEDS_APPROVAL→DOING`/`FAILED`) | ✅ durable writer 적용 완료(task-0052) |
| **실행결과 전이(`DOING→DONE`/`FAILED`)** | ⬜ **비원자적 `write_text()`** ← 이 task의 대상 |
| 실행 메타데이터 기록 | ⬜ **비원자적 `write_text()`** ← 이 task의 대상 |
| retry 준비 전이(`FAILED→TODO`, `TODO→DOING`) | ⬜ 같은 이유로 inline |

## 실측 결과 — canonical schema 비호환

`_run_execution_flow`를 실제 subprocess 포함해 실행한 뒤 생성된 파일을
`task_file_writer._transition_metadata`로 검증했다. 결과 **`REJECT: task_file_unsupported_metadata`**.

| 비호환 | 실측 |
| --- | --- |
| canonical 어휘에 없는 필드 5개 | `error`, `mode`, `reason`, `message`, `execution_status` |
| 타입 불일치 | `execution_candidate` — canonical은 불리언, bot은 JSON 211자 |
| 길이 한계 근접 | `execution_result` 최악 **485자** / 상한 500 → 여유 15자 |
| 제어문자 | `_summarize_execution_output`이 `\n`/`\r`만 치환. **탭이 남아** canonical이 `task_file_invalid_text`로 거부 |

## 핵심 판단 — 필드를 전부 추가하면 되는 문제가 아니다

지시대로 "canonical에 다 넣으면 된다"로 결론 내리지 않고, 5개 필드의 **정보량**을 코드에서
확인했다.

| 필드 | 출처 | 판정 |
| --- | --- | --- |
| `error` | `execution_result["error_reason"]` | 중복 |
| `reason` | `error`와 **같은 변수** | 중복의 중복 |
| `message` | `execution_result["output_summary"]` | 중복 |
| `mode` | 리터럴 `"real"` | 상수 |
| `execution_status` | `executed`/`success`에서 파생 | 파생 |

**새 정보를 담은 필드가 하나도 없다.** 그리고 canonical이 `execution_candidate`를 불리언으로
둔 것은 실수가 아니라 설계 의도의 차이다 — canonical은 **압축된 기록** 층이고
`_write_execution_review_metadata`는 **디버그 덤프** 층이다.

따라서 문제의 성격은 "canonical이 지나치게 엄격하다"가 아니라 **"목적이 다른 두 층이 한
파일에 섞여 있다"** 이다.

## task-0052 회귀 — task-0054로 분리 (Owner 결정 1)

기준선 대조 중 실제 task 파일 53개 중 21개가 canonical 검증에 실패하고 일부 `/approve`가
`write_failed`가 되는 것을 확인했다. **Owner 결정 1에 따라 이 task에 섞지 않는다.**
원인 분석·최소 수정안·`task-0034` 재현 테스트는
`memory/tasks/task-0054-approve-canonical-regression-hotfix.md`와 그 설계 문서로 분리했다.

여기에는 task-0053에 영향을 주는 사실 하나만 남긴다 — task-0054가 채택할 "헤더 블록" 규칙은
본문이 있는 파일에서 **파일 끝에 append된 실행 메타데이터를 canonical 검증 대상에서
제외**하게 된다. metadata-only 파일에서는 계속 검증된다. 이 비대칭 처리는 두 task에 걸친
미결이다(설계 문서 §10.2 결정 C).

## 설계 선택지 (상세는 설계 문서 §6)

| | 선택지 | 판정 |
| --- | --- | --- |
| A | canonical에 5필드 정식 편입 | ❌ `error`/`reason`이 빈 값이라 `allow_empty` 확대 필요 → **금지 위반**. 회귀도 미해결 |
| B | durable primitive 분리 + 실행결과 전용 전이 함수 | ⭕ canonical 무변경. 단 writer가 둘이 된다 |
| C | 중복 5필드 제거 + `execution_candidate` 불리언화 후 기존 writer 재사용 | ⭕ **권장.** 근원 제거. 단 마이그레이션·판독부 변경 필요 |

초판에 있던 선택지 D(canonical parser 경계 정정)는 Owner 결정 1에 따라 **task-0054로 이관**했다.

**확정: C**(Owner 결정 2). 5개 필드가 전부 중복·상수·파생이라 제거해도 정보를 잃지 않고,
근원을 없애면 writer가 하나로 유지된다. 별도 execution writer는 만들지 않는다.

## 유지할 계약 (task-0052에서 확정, 변경하지 않음)

- `owner_approval`은 승인 전이 이후 기록
- `execution_result`는 `_run_execution_flow`에서 기록(단 한 곳)
- reject는 실행이 없으므로 `execution_result`를 남기지 않음
- 서명 없음
- 외부에는 stable `code`만, internal `detail`은 노출 금지
- 감사 append 실패는 롤백하지 않고 크게 보고 (서브프로세스는 되돌릴 수 없다)

**audit event schema는 이 task에서 바꾸지 않는다.** 핵심은 상태·메타데이터 전이의 durability다.

## Owner 결정 (2026-09-05 확정)

| # | 결정 | 이 task 반영 |
| --- | --- | --- |
| 1 | 회귀는 **별도 hotfix(task-0054)** | 선택지 D 제외 |
| 2 | **C 채택** — 중복 5필드 제거, `execution_candidate` 불리언화, 기존 durable writer 재사용, 별도 writer 금지, validation 완화 금지 | 확정안 |
| 3 | 원자적 쓰기 **확정 보류** — 두 쓰기를 한 함수로 감싸는 것은 atomicity가 아니다 | 설계 문서 §8.1에 분석 조건 명시 |
| 4 | 마이그레이션 **제외** | 별도 task/커밋 |
| 5 | `/status`·`/report` 출력 **동일 유지** | `execution_status`는 파생 계산 |
| 6 | 길이 완화 금지 — **중복 제거로 여유 확보** | `execution_result`에서 `output_summary` 제거 |
| 7 | 제어문자는 **요약 생성 단계에서 정규화** | canonical 검증 유지 |
| 8 | **audit event schema 유지** | E1/E2 위치·스키마 불변 |

### 결정 C·B·A 확정 (2026-09-05, 실측 기반)

**C — 실행 메타데이터를 헤더 블록 안에 기록한다.** 근거는 세 가지 측정이다.
(1) 배치가 파일 형태에 좌우된다 — 본문 없는 파일은 13/13이 헤더 안이라 검증에서 **FAIL**하고,
본문 있는 파일은 0/13이라 **PASS**한다. (2) 판독부는 13개를 보는데 검증기는 0개를 본다 —
`/status`가 보여주는 값을 durable writer가 검증하지 않는다. **task-0054가 고친 것과 같은
종류의 불일치다.** (3) 실행 메타데이터를 가진 저장소 파일이 **현재 0개**라 마이그레이션
대상이 없다 — 적용 최적 시점이다. 다만 헤더 밖에 이미 복사본이 있는 파일에서 중복이 나지
않도록 기존 필드 탐색은 파일 전체를 계속 훑는다.

**B — 판독 시 파생한다.** §5에서 5개 필드를 "중복·상수·파생"으로 판정했으나 그것은 *내용*의
판정이었고, **출력에는 전부 등장한다** — `_format_reply`의 status 분기가
`mode`/`reason`/`error`/`message`를 그대로 렌더링하고 `execution_status`는 `/status`와
`/review-task` 양쪽에 나온다. 따라서 파일에서 제거하되 `_read_execution_status_metadata`와
`_read_execution_review_metadata`에서 파생해 **출력을 그대로 유지**한다(Owner 결정 5).
파생 근거는 남는 필드 안에 전부 있다.

**A — 이번 범위는 U1(개별 쓰기 원자성), U2는 별도 결정.** 지시대로 실제 쓰기 구조를 먼저
계측했다.

| 명령 | task 파일 쓰기 | 원자성 |
| --- | --- | --- |
| `/approve … approve` | 3회 | 1회만 원자(승인 전이), 2회 비원자 |
| `/run` | 2회 | **전부 비원자** |
| `/retry` | 4회 | **전부 비원자** |

설계 초판의 "두 쓰기"는 부정확했다. 원자성 단위는 셋으로 나뉜다 — **U1**(개별 쓰기, 달성 가능),
**U2**(실행 메타 + 결과 전이를 한 번의 replace, 가능하되 writer에 새 능력 필요),
**U3**(명령 전체, **구조적으로 불가능** — 준비 전이와 결과 전이 사이에 되돌릴 수 없는
서브프로세스가 있다).

U2는 같은 모듈의 `record_task_completion_evidence`가 선례를 갖는다(필드 삽입 + `updated_at`
갱신을 한 번의 `os.replace`로). 그러나 실행 메타는 N개 필드 insert-or-update이고, 값이
서브프로세스 출력에서 오므로 **쓰기 전 결과 검증**이 추가로 필요하다. 무엇보다 결정 C와
결정 2가 끝나야 **필드의 개수와 위치가 확정**되므로, 그 전에 U2를 설계하면 정해지지 않은
집합을 대상으로 writer 능력을 만드는 셈이다. 따라서 U1을 이번 범위로 하고 U2는 별도 결정으로
재상정한다. U1은 모든 전이를 원자적으로 만든다. 실행 메타데이터 쓰기는 전이가 아니라 U1 대상이 아니며 명령마다 1회 비원자로 남는다(초판의 '6회 전부' 표현은 과장이라 정정했다).

U1 채택 후에도 실행 메타 쓰기와 결과 전이 쓰기 **사이의 창은 남는다**. 이는 §8 실패 지점 3·4이며
task-0052 계약대로 자동복구 없이 보고만 한다.


## 구현 결과 (2026-09-05)

C → B → A(U1) 순으로 구현했다. 기준선 `38b9027`.

### C — 실행 메타데이터를 헤더 블록 안에 기록

`_header_block_end()`를 추가해 새 필드를 헤더 블록 끝에 삽입한다. 기존 필드 탐색은 파일
전체를 계속 훑어 헤더 밖 복사본이 중복되지 않게 했다.

| | 본문 없는 파일 | 본문 있는 파일 |
| --- | --- | --- |
| 헤더 블록 안 실행필드 | **8/8** | **8/8** |
| canonical 검증 | **PASS** | **PASS** |
| 판독부 / 검증기가 보는 수 | **8 / 8** | **8 / 8** |

구현 전에는 각각 13/13·FAIL과 0/13·PASS였고 판독부 13 / 검증기 0이었다. **불일치가 닫혔다.**

### 결정 2·6·7 동반 구현

- 중복 5필드(`error`/`mode`/`reason`/`message`/`execution_status`)를 파일에서 제거
- `execution_candidate`를 canonical 타입대로 **불리언**으로 기록
- `execution_result` JSON에서 `output_summary` 제거 — `execution_summary`와 중복이며 485/500의
  최대 기여분이었다(결정 6)
- `_summarize_execution_output`이 모든 제어문자를 공백 하나로 정규화(결정 7). **공백 축약은
  하지 않는다** — 축약하면 요약 본문이 바뀌어 결정 5에 어긋난다

### B — 판독 시 파생

`_derive_execution_metadata()`가 5개 값을 정확히 재구성한다. `message`는 `executed`가 참일 때
`execution_summary`와 같다 — `_build_execution_result_real`이 `executed=True`면 항상 비어 있지
않은 `output_summary`("no_output" 최소)를, 거짓이면 빈 값을 내기 때문에 모호함이 없다.

`/status` payload에 파생 키가 실려야 해서 `TASK_EXECUTION_DERIVED_FIELDS`를 추가했다.
`_format_reply`·`/status`·`/review-task` 본체는 손대지 않았다.

**출력 동일성 검증**: `38b9027` 대비 성공·실패 × `/status`·`/review-task` **4종 응답 문자열
완전 일치**.

### A(U1) — 모든 전이를 durable writer로

`DURABLE_STATUS_TRANSITIONS`를 writer의 전이 표로 바꿨다. `ALLOWED_STATUS_TRANSITIONS`가
아니라 writer 표를 쓴 이유는 **`DOING→FAILED`가 전자에 없기 때문**이다 —
`_apply_execution_result_status_transition`이 실제로 수행하는데도 빠져 있다(발견 사항).

| 명령 | 쓰기 | 구현 전 | 구현 후 |
| --- | --- | --- | --- |
| `/approve … approve` | 3회 | 원자 1 | **원자 2** |
| `/run` | 2회 | 원자 0 | **원자 1** |
| `/retry` | 4회 | 원자 0 | **원자 3** |

명령마다 남는 1회 비원자 쓰기는 실행 메타데이터 쓰기이며, 이는 전이가 아니라 U1 대상이 아니다.
원자화하려면 canonical 모듈에 새 writer 능력이 필요하고 그것이 **U2**다.

## 검증

| 검증 | 결과 |
| --- | --- |
| 출력 동일성(`38b9027` 대비 4종) | **완전 일치** |
| 배치·판독부/검증기 일치 | 두 파일 형태 모두 8/8, PASS |
| `bot_minimal` self-check | **77/77 PASS** |
| `discord-intake` 스모크 | **77/77 PASS** |
| `audit-chain` | **6/6 PASS** |
| 기존 회귀 8종 + SOP | 전건 PASS |

`bot_minimal` self-check의 `approval_transition_is_durable`은 task-0052가 좁힌 범위를 고정한
계약 테스트였다. task-0053이 의도적으로 넓혔으므로 `every_performed_transition_is_durable`로
갱신해 **수행하는 6쌍 전부**가 durable임을 고정한다.

## 이번 단계 비범위

- 구현 일체
- metadata validation 완화 / `allow_empty` 확대 / max length 완화 / 타입 검증 우회 /
  canonical writer 기존 검증 삭제
- 별도 DB·새 persistence·UI
- `/run`·`/retry` 의미론 임의 변경
- ⑤-c 전역 status gate (task-0052가 명시적으로 제외)
- **task-0052 회귀 전체** — 결정 1에 따라 task-0054
- **기존 파일 마이그레이션** — 결정 4에 따라 별도 task/커밋
- **통합 원자성(U2)** — 결정 A에서 별도 Owner Decision으로 재상정
- **명령 전체 원자성(U3)** — 구조적으로 불가능(서브프로세스가 중간에 있음)
- 불일치 탐지 도구 / 수동 복구 명령
- audit event schema 변경
- `summary` 500자 초과 5건 처리 — task-0054 소관

## U2를 남겨둔 이유

C·B·A(U1) 구현과 검증이 모두 끝났다. U2(실행 메타 + 결과 전이를 한 번의 replace)는 Owner가
별도 결정으로 남겨두었고 이 task 범위가 아니다.
