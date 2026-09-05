# task-0053 실행결과 전이의 durable writer 적용 설계

- task: `task-0053-execution-result-durable-transition`
- 기준선: `38b9027` (= `origin/main`, task-0054 hotfix 반영)
- 선행: `task-0052`(승인 전이 durable 적용, `3c5ee1b`·`a6c4ef3`), `task-0044`(감사 체인 코어, `116fe2d`)
- 상태: **설계 단계. 구현 없음.** Owner 결정 대기
- 작성: 2026-09-05

## 1. 목적/배경

task-0052는 승인 전이(`NEEDS_APPROVAL→DOING`/`FAILED`)만 `task_file_writer`의 durable
writer로 옮기고, 실행결과 전이는 **의도적으로 기존 경로에 남겼다**. 이유는 실행 메타데이터가
canonical metadata schema와 호환되지 않았고, 그 검증을 완화하지 않기로 했기 때문이다.

이 task는 그 잔여 약점을 해소한다. **목표는 실행결과 전이도 승인 전이와 같은 durable 원칙을
쓰게 만드는 것**이며, canonical 검증을 완화하지 않고 달성해야 한다.

기준선 확인 결과 지시하신 `docs/task-0044-audit-chain-design.md`는 존재하지 않는다. 실제
파일명은 `docs/task-0044-audit-hash-chain-design.md`이며 그것을 기준선으로 읽었다.

## 2. 현재 실행결과 경로 (실측)

행 번호는 `a6c4ef3` 기준.

```text
/approve <id> approve
  └ _run_approve_parse(1602) → _build_approve_draft(830) → _build_approve_writer_input(852)
     └ _build_approve_writer_result(1489)
        ├ _apply_task_status_transition(NEEDS_APPROVAL→DOING)      ← durable (task-0052)
        ├ _audit_owner_approval  … E1
        ├ decision=="reject" → 실행 흐름 미진입 (task-0052 ⑤-b)
        └ _run_execution_flow(task_id, "approve_file_write_result")

/run   <id> └ _run_run(1300)   └ _run_execution_flow(…, "run")
/retry <id> └ _run_retry(1236)
               ├ _apply_task_status_transition(FAILED→TODO)        ← inline
               ├ _apply_task_status_transition(TODO→DOING)         ← inline
               └ _run_execution_flow(…, "retry")

_run_execution_flow(1157)
  ├ _build_execution_candidate(1119)        ← status를 보지 않음
  ├ _build_execution_request(1150)
  ├ _build_execution_result_dry_run(1330)
  ├ _build_execution_result_real(1364)      ← subprocess.run (화이트리스트 경유)
  ├ _write_execution_review_metadata(896)   ← 쓰기 ①  비원자적 write_text()
  ├ _apply_execution_result_status_transition(1432)
  │    └ _apply_task_status_transition(DOING→DONE|FAILED)  ← 쓰기 ②  inline 경로
  └ _audit_execution_result … E2
```

**이 task의 대상은 쓰기 ①과 쓰기 ②다.** 둘 다 `write_text()` 위에 있고, 둘 사이에도
원자성이 없다.

`_apply_task_status_transition`(920)은 `DURABLE_STATUS_TRANSITIONS`(승인 2쌍)만 durable
경로로 보내고 나머지는 `_apply_task_status_transition_inline`(1010)을 탄다.

## 3. canonical schema와 실제 metadata 대조 (실측)

`_run_execution_flow`를 실제로 실행해(실제 subprocess 포함) 생성된 task 파일을
`task_file_writer._transition_metadata`로 검증한 결과다. **추측이 아니라 측정값이다.**

canonical 검증 결과: **`REJECT: task_file_unsupported_metadata`**

| 필드 | canonical 분류 | 실측 len | 빈값 | 판정 |
| --- | --- | --- | --- | --- |
| `id` `title` `status` `repo` `created_at` `updated_at` `summary` | REQUIRED | 4~20 | – | ok |
| `execution_candidate` | **OPT_BOOL** (`true`/`false`만) | 216 | – | 🔴 **타입 불일치** — bot은 JSON을 쓴다 |
| `execution_request` | OPT_TEXT(≤500, non-empty) | 214 | – | ok |
| `execution_result` | OPT_TEXT(≤500, non-empty) | 427 | – | ⚠ 상한에 근접 |
| `executed` `success` `dry_run` | OPT_BOOL | 4~5 | – | ok |
| `error` | **없음** | 0 | ✅ | 🔴 `unsupported_metadata` |
| `mode` | **없음** | 4 | – | 🔴 `unsupported_metadata` |
| `reason` | **없음** | 0 | ✅ | 🔴 `unsupported_metadata` |
| `message` | **없음** | 223 | – | 🔴 `unsupported_metadata` |
| `execution_status` | **없음** | 7 | – | 🔴 `unsupported_metadata` |
| `execution_updated_at` | OPT_TS | 20 | – | ok |
| `execution_summary` | OPT_TEXT(≤500, non-empty) | 223 | – | ok |

### 3.1 경계 사례 실측

| 경계 | 측정 | 결과 |
| --- | --- | --- |
| `execution_result` 최악 길이 | 실측 **485자** (output_summary 220자 상한 + 긴 task_id + error_reason) | 상한 500까지 **여유 15자**. 통과하지만 사실상 한계 |
| stdout에 탭 포함 | `_summarize_execution_output`은 `\n`/`\r`만 치환하고 **탭은 남긴다** | canonical `_transition_text_is_valid`가 `task_file_invalid_text`로 **거부** |
| `execution_candidate` | JSON 211자 | canonical은 `true`/`false`만 허용 |

## 4. task-0052 회귀 — **task-0054로 분리**(Owner 결정 1)

기준선 대조 중 실제 task 파일 53개 중 21개가 canonical 검증에 실패하고, 그로 인해 일부
task의 `/approve`가 `write_failed`가 되는 것을 확인했다.

**Owner 결정 1에 따라 이 문제는 이 task에 섞지 않는다.** 원인 분석·최소 수정안·회귀
테스트는 별도 hotfix로 분리했다 —
[`docs/task-0054-approve-canonical-regression-hotfix-design.md`](task-0054-approve-canonical-regression-hotfix-design.md).

여기서는 task-0053에 영향을 주는 사실 하나만 남긴다.

> task-0054가 채택할 수 있는 "헤더 블록" 규칙은 **본문(`## ` 섹션)이 있는 파일에서 파일 끝에
> append된 실행 메타데이터를 canonical 검증 대상에서 제외**하게 된다. 반대로 canonical이
> 생성한 metadata-only 파일에서는 계속 검증 대상이다. 즉 **같은 실행 메타데이터가 파일 형태에
> 따라 검증되기도 하고 안 되기도 한다.** 이 비대칭은 **결정 C(§10.2)에서 C1로 해소하기로 확정**했다 — 실행 메타데이터를
> 헤더 블록 안에 기록해 파일 형태와 무관하게 일관 검증한다.

## 5. 핵심 판단 — 두 층을 합쳐야 하는가

지시대로 "필드를 전부 canonical에 추가하면 된다"로 결론 내리지 않고, 먼저 **미허용 5개
필드가 실제로 정보를 담고 있는지** 코드에서 확인했다.

`_write_execution_review_metadata`(896) 실제 대입값:

| 필드 | 값의 출처 | 정보량 판정 |
| --- | --- | --- |
| `error` | `execution_result["error_reason"]` | **중복** — `execution_result` JSON 안에 이미 있다 |
| `reason` | `error`와 **같은 변수**(`reason`) | **중복의 중복** — 두 필드 값이 항상 동일하다 |
| `message` | `execution_result["output_summary"]` | **중복** — `execution_result` JSON 안에 있다 |
| `mode` | 리터럴 `"real"` | **상수** — 이 경로에서 항상 `"real"` |
| `execution_status` | `executed`/`success`에서 파생 | **파생** — 두 필드가 이미 별도로 있다 |
| `execution_candidate` | 후보 객체 JSON | canonical은 "후보가 있었는가"라는 **불리언**을 기대한다 |

**다섯 필드 중 새로운 정보를 담은 것은 하나도 없다.** 전부 중복·상수·파생이다.

그리고 canonical이 `execution_candidate`를 불리언으로 분류한 것은 실수가 아니라 **설계
의도의 차이**를 보여준다 — canonical은 "실행이 있었는가"를 압축해 기록하는 층이고,
`_write_execution_review_metadata`는 **디버그 덤프**를 남기는 층이다.

따라서 이 문제의 성격은 "canonical이 너무 엄격하다"가 아니라 **"두 층이 서로 다른 목적을
가진 채 같은 파일에 섞여 있다"** 이다. 이 판단이 아래 선택지 비교의 축이다.

## 6. 설계 선택지

### A. canonical schema에 5개 필드를 정식 편입

canonical에 `error`/`mode`/`reason`/`message`/`execution_status`를 추가하고
`execution_candidate`를 text로 재분류한다.

| 항목 | 내용 |
| --- | --- |
| 변경 파일 | `task_file_writer.py`(스키마·검증), 콘솔 계약 테스트 |
| schema 영향 | canonical 어휘가 6개 늘고, `execution_candidate` 타입이 바뀐다 |
| 하위 호환 | 기존 파일 그대로 통과 |
| `/approve`·`/run`·`/retry` | 동작 불변 |
| failure semantics | 불변 |
| audit-chain | 무관 |
| 테스트 | 스키마 테스트 + 콘솔 계약 테스트 |
| diff | 작음 (~40행) |
| 위험 | 🔴 `error`/`reason`은 **성공 시 빈 문자열**이라 `allow_empty` 확대가 필요하다 → **금지 사항 위반**. 또 §4의 회귀(본문 불릿·summary 길이)를 **전혀 해결하지 못한다** |

**부적격.** 금지 제약을 어기고, 회귀도 남는다.

### B. durable primitive를 분리해 실행결과 전용 전이 함수를 만든다

`transition_task_file_status`가 하는 두 가지 — ① 원자적 쓰기(temp+fsync+`os.replace`+
`expected_digest`) ② 파일 전체 canonical 검증 — 은 현재 한 함수에 묶여 있다. ①을 내부
primitive로 분리하고, 실행결과 전용 전이 함수가 **자기 계약으로** ①을 재사용한다.

| 항목 | 내용 |
| --- | --- |
| 변경 파일 | `task_file_writer.py`(primitive 분리 + 신규 함수), `bot_minimal.py`(호출부) |
| schema 영향 | **기존 canonical 검증은 한 글자도 바뀌지 않는다.** 신규 함수가 자기 검증을 갖는다 |
| 하위 호환 | 기존 파일 그대로. 기존 `transition_task_file_status` 동작 불변 |
| `/approve`·`/run`·`/retry` | 실행결과 전이가 원자적으로 바뀐다. 의미론 불변 |
| failure semantics | §7 |
| audit-chain | 무관 (E2 위치·스키마 불변) |
| 테스트 | primitive 단위 테스트 + 실행결과 전이 테스트 + 기존 회귀 |
| diff | 중간 (~150행) |
| 위험 | ⚠ 같은 파일에 **검증 강도가 다른 두 writer**가 생긴다. "canonical이 단일 진실"이라는 성질이 흐려진다. 완화책: 신규 함수는 자신이 쓰는 필드만 검증하고 나머지 줄은 **건드리지 않음**을 계약으로 못박는다 |

### C. `_write_execution_review_metadata`를 canonical에 맞게 재작성 (중복 제거)

§5의 분석에 따라 **중복·상수·파생 5개 필드를 task 파일에서 없애고**,
`execution_candidate`를 canonical대로 불리언으로 바꾼다. 그러면 실행 메타데이터가 canonical
어휘 안에 들어오고, 실행결과 전이가 기존 `transition_task_file_status`를 **그대로** 쓸 수 있다.

| 항목 | 내용 |
| --- | --- |
| 변경 파일 | `bot_minimal.py`(기록·판독부), 관련 self-check |
| schema 영향 | **canonical 무변경.** bot 쪽이 canonical에 맞춘다 |
| 하위 호환 | 🔴 기존 task 파일에 남은 5개 필드는 여전히 `unsupported_metadata`다 → **마이그레이션 필요** |
| `/approve`·`/run`·`/retry` | 의미론 불변. `/status`·`/report` 출력에서 `execution_status` 등이 사라지거나 파생으로 대체된다 |
| failure semantics | §7 |
| audit-chain | 무관 |
| 테스트 | 기록·판독 왕복, `/status`·`/report` 출력, 마이그레이션 |
| diff | 중간~큼 (~200행 + 마이그레이션) |
| 위험 | ⚠ 판독부(`_read_execution_review_metadata`, `_read_execution_status_metadata`, `/status`, `/report`)가 5개 필드를 참조한다. 파생으로 대체 가능하지만 **출력이 바뀔 수 있다** |

### 조합 판단 (Owner 결정 반영)

- **A는 부적격** — `error`/`reason`이 성공 시 빈 문자열이라 `allow_empty` 확대가 필요하고,
  이는 금지 사항이다.
- 초판에 있던 선택지 D(canonical의 metadata 줄 인식 범위 정정)는 **Owner 결정 1에 따라
  이 task에서 제외**하고 task-0054로 옮겼다.
- **Owner 결정 2로 C가 채택됐다.**

## 7. 확정안 — C (Owner 결정 2)

**중복 5개 필드를 제거하고 `execution_candidate`를 canonical의 불리언으로 맞춘 뒤, 기존
`transition_task_file_status`를 그대로 재사용한다.** 별도 execution writer를 만들지 않고,
canonical metadata validation은 완화하지 않는다.

근거는 §5다 — 다섯 필드가 전부 중복·상수·파생이므로 제거해도 정보를 잃지 않는다. 근원을
없애면 writer가 하나로 유지되고 "canonical이 단일 진실"이라는 성질이 보존된다.

확정에 따라 함께 따라오는 것:

| 항목 | 결정 | 근거 |
| --- | --- | --- |
| `execution_result` 길이(485/500) | **중복 제거로 여유를 확보한다.** `output_summary`는 이미 `execution_summary`에 있으므로 `execution_result` JSON에서 뺀다 | 결정 6. 길이 완화는 금지 |
| 제어문자(탭) | **`_summarize_execution_output` 등 요약 생성 단계에서 정규화한다** | 결정 7. canonical의 제어문자 검증은 그대로 유지 |
| `/status`·`/report` 출력 | **기존과 동일하게 유지한다.** `execution_status`는 `executed`/`success`에서 파생 계산 | 결정 5 |
| audit event schema | **변경하지 않는다** | 결정 8 |
| 기존 파일 마이그레이션 | **이 task에서 제외**, 별도 task/커밋 | 결정 4 |
| 원자적 쓰기 | **이번 설계에서 확정하지 않는다** | 결정 3 — §8 참조 |

## 8. 실패 semantics

task-0052 §9.1/§10.1의 계약을 **바꾸지 않는다.**

| # | 실패 지점 | task 상태 | 롤백 | 재시도 | task-0052 대비 |
| --- | --- | --- | --- | --- | --- |
| 1 | 실행 시작 전 전이 실패(`/retry`의 `FAILED→TODO` 등) | 원래 상태 유지 | 불필요 | 가능 | 불변 |
| 2 | subprocess 실행 실패 | `DOING → FAILED`(전이는 성공) | 해당 없음 | `/retry` 가능 | 불변 |
| 3 | 실행 메타데이터 기록 실패 | `DOING` 유지, 메타데이터 없음 | 없음 | 가능 | 현재는 `write_failed`만 반환하고 흐름이 계속된다 |
| 4 | 실행결과 상태 전이 실패 | `DOING` 유지 | 없음 | 가능 | 현재도 `execution_status_transition_applied=false`로 보고된다 |
| 5 | 감사 append 실패 | 위 상태 그대로 | 없음 | – | **불변** — 서브프로세스는 되돌릴 수 없다. `audit_error`로 보고만 |

**새로운 자동복구를 추가하지 않는다.** 3·4의 고착은 task-0052의 승인 경로 고착과 같은
성격이며, 복구는 Owner의 수동 개입이다.

### 8.1 원자적 쓰기는 이번 설계에서 확정하지 않는다 (Owner 결정 3)

쓰기 ①(메타데이터)과 쓰기 ②(상태 전이)를 한 함수로 감싸는 것은 **atomicity가 아니다.**
확정 전에 아래를 먼저 분석해야 한다.

- `transition_task_file_status`는 `- status:` / `- updated_at:` **두 줄만** 정규식으로 치환한다.
  실행 메타데이터 13개 줄을 같은 방식으로 함께 쓰려면 치환 대상과 순서가 달라진다.
- `_write_execution_review_metadata`는 존재하는 필드는 **제자리 갱신**, 없는 필드는 **파일 끝에
  append** 한다. append 위치는 헤더 블록 밖일 수 있어 §4의 비대칭과 얽힌다.
- 현재 구조에서 진짜 원자성은 "하나의 temp 파일에 최종 내용을 쓰고 `os.replace` 한 번"이어야
  하며, 그러려면 **상태와 실행 메타데이터를 한 번에 렌더링하는 함수**가 필요하다. 이는
  `_render_task_markdown`의 책임 범위와 겹친다.

따라서 이 설계는 **"실행결과 전이가 기존 durable writer를 쓸 수 있게 만드는 것"까지만**
확정하고, 두 쓰기의 통합 원자성은 **별도 Owner Decision으로 다시 올린다**(§10 결정 A).

## 9. 테스트 계획

task-0052의 **결정론적 before/after 대조** 방식을 재사용한다(`116fe2d` 대조로 reject 버그를
증명했던 방식).

| 테스트 | 내용 |
| --- | --- |
| `/approve` 성공 | 승인 전이 + 실행 + 실행결과 전이가 모두 적용, 체인 2건 |
| `/approve reject` | 실행 미진입, 체인 1건 (task-0052 계약 유지 확인) |
| `/run` 성공 / 실패 | `DOING→DONE` / `DOING→FAILED` 전이와 메타데이터 |
| `/retry` 성공 / 실패 | `FAILED→TODO→DOING` 준비 전이 포함 |
| 실행 메타데이터 스키마 검증 | 기록 직후 파일이 canonical 검증을 **통과**하는지 |
| durable writer 실패 주입 | `_replace_file`/`_fsync_file` seam으로 실패를 주입해 §8의 3·4 상태 확인 |
| 감사 이벤트 중복 | approve 2건 / reject 1건 / run 1건 / retry 1건 — task-0052에서 쓴 실측 방식 |
| **기존 task 파일 호환** | `memory/tasks/` 실제 기록의 canonical 검증 통과율이 내려가지 않는지 (기준선 `38b9027`: 검증대상 54 중 PASS 46) |
| **before/after 대조** | `38b9027` 대비 `/run`·`/retry`의 쓰기 방식과 실행 메타데이터 배치 변화 |
| **결정 C — 배치 일관성** | 본문 있는 파일과 없는 파일 모두에서 실행 필드가 **헤더 블록 안**에 기록되는지. 두 형태 모두 canonical 검증 대상이 되는지 |
| **결정 C — 판독부·검증기 일치** | 판독부가 보는 실행필드 수 == 검증기가 보는 수 |
| **결정 C — 중복 방어** | 헤더 밖에 실행 필드가 이미 있는 파일에 기록해도 `task_file_duplicate_metadata`가 나지 않는지 |
| **결정 B — 출력 동일성** | 중복 5필드 제거 전/후 `/status`와 `/review-task` 응답 문자열 **완전 일치**. `_format_reply` 무변경 |
| **결정 B — 파생 정확성** | `execution_status`가 `executed`/`success` 조합 3종(success/failed/not_executed)에서 기존과 같은 값을 내는지 |
| **결정 A(U1) — 쓰기 원자성** | `/run` 2회·`/retry` 4회의 task 파일 쓰기가 전부 `os.replace` 경로인지 계측(현재는 전부 `write_text`) |
| **결정 A — U2 미적용 확인** | 실행 메타 쓰기와 결과 전이 쓰기 사이 창이 남는다는 사실을 실패 주입으로 고정 |
| 기존 회귀 | discord-intake 77건 + bot self-check 77건 + audit-chain 6건 + 회귀 9종 |

## 10. Owner 결정 (전건 확정)

### 10.1 1차 확정 (2026-09-05, 결정 1~8)

| # | 결정 | 이 task에 미치는 영향 |
| --- | --- | --- |
| 1 | task-0052 회귀는 **별도 hotfix(task-0054)로 분리** | 선택지 D를 이 task에서 제외 |
| 2 | **C 채택** — 중복 5필드 제거, `execution_candidate` 불리언화, 기존 durable writer 재사용, 별도 execution writer 금지, canonical validation 완화 금지 | §7이 확정안 |
| 3 | 원자적 쓰기는 **이번 설계에서 확정하지 않는다** | §8.1. 필요하면 별도 결정으로 재상정 |
| 4 | 기존 파일 **마이그레이션 제외** | 별도 task/커밋 |
| 5 | `/status`·`/report` 출력 **기존과 동일 유지** | `execution_status`는 파생 계산 |
| 6 | 길이 완화 금지 — **중복 제거로 여유 확보** | `execution_result`에서 `output_summary` 제거 |
| 7 | 제어문자는 **요약 생성 단계에서 정규화** | canonical 검증은 유지 |
| 8 | **audit event schema 유지** | E1/E2 위치·스키마 불변 |

### 10.2 결정 C · B · A (2026-09-05 확정, 기준선 `38b9027`)

task-0054가 metadata 경계를 확정했으므로 세 항목을 순서대로 판단했다. 아래는 전부 실제 코드를
실행해 얻은 측정값이며, 모든 probe는 임시 디렉터리에서만 수행했다.

#### 결정 C — 실행 메타데이터를 헤더 블록 안에 유지한다 (C1 확정)

**측정 1 — 배치가 파일 형태에 좌우된다.**

| 파일 형태 | 헤더 블록 안 실행필드 | canonical 검증 |
| --- | --- | --- |
| 본문 없음(canonical 생성형) | **13/13** | **FAIL** `task_file_unsupported_metadata` |
| 본문 있음(사람이 쓴 기록) | **0/13** | **PASS** (검증 대상이 아니라서) |

같은 실행 메타데이터가 파일 형태에 따라 전이를 막거나, 아예 보이지 않는다.

**측정 2 — 기록·판독부와 검증기가 서로 다른 범위를 본다.**

본문 있는 파일에 `/run`을 실행한 뒤:

```text
판독부(_read_execution_status_metadata)가 보는 실행필드 : 13
검증기(_transition_metadata)가 보는 실행필드            : 0
canonical 검증                                          : PASS
```

`/status`는 값을 사용자에게 보여주는데 durable writer는 그 값을 검증하지 않는다.
**이것은 task-0054가 방금 고친 것과 같은 종류의 결함이다** — 한 저장소의 두 구성요소가
"무엇이 metadata인가"에 대해 다른 답을 갖는 상태.

**측정 3 — 지금이 적용 최적 시점이다.**

```text
실행 메타데이터를 가진 저장소 task 파일 : 0개
그중 헤더 블록 밖에 있는 파일           : 0개
```

아직 실행 메타데이터를 가진 파일이 하나도 없으므로 **마이그레이션 대상이 존재하지 않는다.**
실행이 한 번이라도 일어난 뒤에는 이 선택의 비용이 커진다.

| | 선택지 | 판정 |
| --- | --- | --- |
| C1 | **실행 메타데이터를 헤더 블록 안에 기록** | ✅ **확정.** 파일 형태와 무관하게 일관 검증, 판독부·검증기 일치 |
| C2 | 비대칭 수용 + 문서화 | ❌ 검증 우회를 제도화한다. 결정 2의 "완화하지 않는다" 취지와 어긋난다 |

**구현 요건**: 새 필드는 헤더 블록 끝(첫 비-필드 최상위 줄 직전)에 삽입한다. 다만 기존 필드
탐색은 **파일 전체를 계속 훑어야 한다** — 헤더 밖에 이미 복사본이 있는 파일에서 헤더 안에
새로 삽입하면 `task_file_duplicate_metadata`가 된다. 저장소에는 그런 파일이 현재 0개지만
방어적으로 처리한다.

#### 결정 B — 판독 시 파생한다 (B1 확정)

**측정 — 5개 필드는 전부 사용자 대면 출력이다.** §5에서 "중복·상수·파생"이라고 판정했지만
그것은 *내용*의 판정이고, *출력*에는 전부 등장한다. `_format_reply`의 `status` 분기가
다음을 그대로 렌더링한다.

```python
for key in ("executed", "success", "dry_run", "mode", "reason", "error", "message"):
```

추가로 `execution_status`는 `/status`와 `/review-task`(`review_task_result`) 양쪽에 나온다.
따라서 파일에서 제거하려면 **판독 시점에 파생하지 않으면 출력이 바뀐다**(Owner 결정 5 위반).

파생 근거는 전부 남는 필드 안에 있다.

| 제거 필드 | 파생식 |
| --- | --- |
| `error`, `reason` | `execution_result["error_reason"]` |
| `message` | `execution_result["output_summary"]` |
| `mode` | 실제 실행 경로 상수 `"real"` (dry-run은 `dry_run` 필드가 구분) |
| `execution_status` | `executed`/`success` → `success` / `failed` / `not_executed` |

| | 선택지 | 판정 |
| --- | --- | --- |
| B1 | **판독부에서 파생** — `_read_execution_status_metadata` / `_read_execution_review_metadata` | ✅ **확정.** 호출부와 출력이 그대로 유지된다 |
| B2 | 파생값을 canonical 필드로 저장 | ❌ 새 필드가 필요해 결정 2와 충돌 |

**구현 요건**: 파생은 두 판독 함수 안에서 한다. `/status`·`/review-task`·`_format_reply`는
손대지 않는다. 출력 동일성은 before/after 문자열 비교로 고정한다.

#### 결정 A — 원자성: 이번 범위는 U1, U2는 별도 결정으로 올린다

Owner 지시대로 실제 파일 쓰기 구조를 먼저 계측했다.

**측정 — 명령별 task 파일 쓰기 횟수와 원자성**

| 명령 | 쓰기 | 내역 |
| --- | --- | --- |
| `/approve … approve` | **3회** | `os.replace`(원자, 승인 전이) + `write_text`(비원자, 실행 메타) + `write_text`(비원자, 실행결과 전이) |
| `/run` | **2회** | `write_text` ×2 — **전부 비원자** |
| `/retry` | **4회** | `write_text` ×4 — 준비 전이 2회 포함, **전부 비원자** |

설계 초판이 "두 쓰기"라고 쓴 것은 부정확했다. `/retry`는 네 번 쓴다.

**원자성 단위를 먼저 정의해야 한다.**

| 단위 | 내용 | 달성 가능성 |
| --- | --- | --- |
| **U1** | 개별 쓰기 각각이 원자적 | ✅ 달성 가능 — 모든 전이를 durable writer로 보내면 된다 |
| **U2** | "실행이 끝났고 결과가 이렇다" = 실행 메타 + 실행결과 전이를 **한 번의 replace**로 | ⚠ 가능하되 writer에 새 능력이 필요 |
| **U3** | 명령 전체(`/retry`의 4회)가 all-or-nothing | 🔴 **구조적으로 불가능** |

**U3이 불가능한 이유**: 준비 전이와 결과 전이 사이에 **서브프로세스 실행**이 있다. 되돌릴 수
없는 외부 효과가 중간에 있으므로 명령 전체를 트랜잭션으로 묶을 수 없다. 이는 구현 난이도가
아니라 구조의 문제다.

**U2의 실현 조건 — 선례는 있다.** 같은 모듈의 `record_task_completion_evidence`가 이미
동일한 primitive로 **필드 삽입 + `updated_at` 갱신을 한 번의 `os.replace`**로 처리한다.
값 검증(`_completion_evidence_is_valid`)을 쓰기 전에 수행하는 패턴도 갖춰져 있다.

그러나 실행 메타데이터는 선례보다 무겁다.

1. 선례는 **고정 위치에 1개 필드 삽입**이고, 실행 메타는 **N개 필드 insert-or-update**다.
2. `transition_task_file_status`는 `- status:` / `- updated_at:` **두 패턴만** 치환하며 각각
   정확히 1회 매치를 요구한다. N개 필드의 삽입·갱신은 다른 변형 모양이다.
3. 결정적으로, 이 함수는 **원본만 검증하고 결과는 검증하지 않는다.** status/updated_at은
   enum·형식 검증을 이미 통과한 값이라 구성상 안전하지만, 실행 필드 값은 **서브프로세스 출력에서
   온다.** U2를 하려면 **쓰기 전 결과 검증**을 추가해야 하며 이는 완화가 아니라 강화다.

| | 선택지 | 판정 |
| --- | --- | --- |
| A1 | 현행 유지 | ❌ `/run`·`/retry`가 전부 비원자로 남는다 |
| **A3(U1)** | **모든 전이를 durable writer로** — 각 쓰기가 원자적 | ✅ **이번 범위로 확정** |
| A2(U2) | 실행 메타 + 결과 전이를 한 번의 replace로 | ⏸ **별도 Owner Decision으로 재상정** |

**이번 범위를 U1로 두는 근거**: 결정 C(헤더 블록 안 기록)와 결정 2(중복 제거)가 끝나야 실행
필드의 **개수와 위치가 확정**된다. 그 전에 U2를 설계하면 아직 정해지지 않은 필드 집합을 대상으로
writer 능력을 만드는 셈이 된다. U1은 **모든 전이**를 원자적으로 바꾼다 — `/run` 1/2,
`/retry` 3/4, `/approve` 2/3이 원자적 쓰기가 된다.

**정정**: 이 절의 초판은 "6회의 비원자 쓰기가 전부 원자적으로 바뀐다"고 썼는데 **과장이었다.**
실행 메타데이터 쓰기는 전이가 아니라서 U1의 대상이 아니며, 명령마다 **1회의 비원자 쓰기가
남는다**. 그 쓰기를 원자적으로 만들려면 canonical 모듈에 새 writer 능력이 필요하고 그것이
곧 U2다.

**U1 채택 후에도 남는 창**: 실행 메타 쓰기와 결과 전이 쓰기 사이. 이 구간에서 중단되면
"메타데이터는 썼는데 상태는 안 바뀐" 상태가 남는다. 이는 §8 실패 지점 3·4이며 **task-0052의
계약 그대로** 자동복구 없이 보고만 한다. U2는 이 창을 닫는 것이 목적이므로, 필드 집합이 확정된
뒤 별도로 판단한다.


## 11. 이번 단계에서 하지 않는 것

- **구현 일체** — 이 문서는 설계뿐이다
- metadata validation 완화 / `allow_empty` 확대 / max length 완화 / 타입 검증 우회 /
  canonical writer의 기존 검증 삭제 — **전부 금지**
- 별도 DB·새 persistence 도입, UI 추가
- `/run`·`/retry` 의미론의 임의 변경
- ⑤-c 전역 status gate — task-0052가 명시적으로 제외했다
- 불일치 탐지 도구 / 수동 복구 명령
- audit event schema 변경
- **task-0052 회귀 전체** — 결정 1에 따라 task-0054로 분리
- **기존 task 파일 마이그레이션** — 결정 4에 따라 별도 task/커밋
- **두 쓰기의 통합 원자성(U2)** — 결정 A에서 별도 Owner Decision으로 재상정(§10.2)
- **명령 전체 원자성(U3)** — 서브프로세스가 중간에 있어 구조적으로 불가능
