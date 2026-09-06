# task-0057-task-model-execution-metadata-correction

- id: `task-0057-task-model-execution-metadata-correction`
- title: `task-model.md 실행 메타데이터 계약을 canonical 스키마에 맞춰 정정`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-06 13:14 UTC`
- updated_at: `2026-09-06 13:14 UTC`
- summary: `task-0053이 실행 메타데이터 5개를 디스크에서 제거하고 execution_candidate를 boolean으로 바꿨는데 계약 문서인 docs/task-model.md §10은 13개 필드와 JSON 후보를 그대로 기술하고 있었다. task-0054·0056으로 canonical 스키마가 예외 없이 강제되면서 이 문서대로 쓰면 곧바로 검증에 실패하는 상태였다. §10을 저장 8개와 판독 파생 5개로 나눠 다시 쓰고 타입 규칙과 /status·/review-task 노출 방식을 현재 동작에 맞췄다. 문서만 바꿨고 코드와 canonical 규칙은 무변경이다.`
- source_command: `read-only 전체 점검 후보 1 승인 (Owner)`

## 기준선

- HEAD `59e7d65` = `origin/main`
- 변경: `docs/task-model.md` 1파일 + 이 기록
- **코드·canonical 규칙 변경 0건**

## 문제 — 계약 문서가 계약과 달랐다

§10은 실행 메타데이터를 13개 필드로 기술하고 `execution_candidate`를 "compact JSON
metadata"라고 적어 뒀다. 실제로 강제되는 스키마는 다르다.

| | 문서(정정 전) | canonical 강제 |
| --- | --- | --- |
| 저장 필드 수 | 13 | **8** |
| `execution_candidate` | compact JSON | **boolean** |
| `error`·`mode`·`reason`·`message`·`execution_status` | 저장 필드 | **저장 불가** |

task-0053이 5개를 디스크에서 제거했고 task-0054·0056이 스키마를 예외 없이 강제한
결과, **문서대로 구현하면 canonical 검증에서 거부된다.** 오래된 서술이 아니라
지금 더 위험해진 서술이었다.

## 실측으로 확인한 강제 상태

임시 fixture에 각 형태를 넣고 `_transition_metadata()`로 판정했다.

| 넣은 것 | 결과 |
| --- | --- |
| 정본 8개 필드 | `PASS` |
| `mode` / `error` / `reason` / `message` / `execution_status` | 전부 `task_file_unsupported_metadata` |
| `execution_candidate` 에 JSON | `task_file_invalid_text` |
| `execution_candidate` 에 `True` / `1` / 빈 값 | 전부 `task_file_invalid_text` |
| `execution_summary` 빈 값 | `task_file_invalid_text` |
| `execution_summary` 501자 | `task_file_field_too_long` |
| `execution_updated_at` 에 시각 없는 날짜 | `task_file_invalid_updated_at` |

파생 5개의 재구성도 `_derive_execution_metadata()`로 4가지 입력에 대해 실측해
문서의 재구성 표와 한 칸씩 대조했다 — 성공·실패·미실행·메타데이터 없음 모두 일치했다.

## 수정 내용

§10만 교체했고 §1~§9와 §11은 한 글자도 바꾸지 않았다(전후 파일 head 82행·tail 대조로 확인).

1. **저장 필드** — 8개를 타입(boolean / text / timestamp)과 함께 표로 명시했다.
2. **타입 규칙** — boolean 은 `true`/`false` 리터럴만, text 는 500자 이하이며 빈 값 불가
   (값이 없으면 필드를 생략), timestamp 는 `%Y-%m-%d %H:%M UTC`, 모든 값에 backtick 불가.
3. **파생 필드** — 5개는 저장되지 않고 판독 시 재구성된다는 점과, **지금 파일에 쓰면
   검증에 실패한다**는 점을 명시하고 각각의 재구성 근거를 표로 적었다.
4. **노출 방식** — `/status`가 저장값과 파생값을 구분 없이 나란히 출력하되 빈 값은
   줄 자체를 생략하는 것, `execution_candidate`·`execution_request`·`execution_result`는
   payload에만 있고 출력되지 않는 것, `/review-task`는 3개만 보고하는 것을 적었다.
5. **이름 충돌** — `docs/execution-contract.md`의 `approve_file_write_result.execution_candidate`
   (객체 또는 `null`)와 task 파일 필드는 다른 것이며 파일에는 boolean만 들어간다는 주석을 달았다.

## 검증

| 검증 | 결과 |
| --- | --- |
| canonical 전수 | **56/56 PASS** |
| `discord-intake` 스모크 | **79/79 PASS** |
| `bot_minimal` self-check | **79/79 PASS** (`ok=true`) |
| `audit-chain` | **6/6 PASS** |
| `discord-nl-intent` / `jarvis-console` | PASS |
| `validate_multi_agent_sop` | `status=PASS` (negative_checks=28, failures=0) |
| `check_no_secrets --self-test` | 16/16, `failures=0` |
| §10 외 구간 무변경 | head 82행·tail 대조 결과 완전 일치 |

`check_no_secrets`의 저장소 전수 스캔은 자기 자신의 self-test fixture 7건을 잡아 FAIL로
끝나는데, 이는 이번 변경 이전부터 있던 상태이고 이번 변경과 무관하다(변경 파일은
`docs/task-model.md` 하나뿐).

## 이번 단계 비범위

- 코드·canonical 규칙 변경 — 없다. 문서만 고쳤다.
- `docs/master-plan.md` 갱신 — 별도 후보로 남겨 둔다.
- `orchestrator/buzz-bridge/lib/task_append.js`의 낡은 docstring — 별도 후보로 남겨 둔다.
- `jarvis.bat` — 건드리지 않았다.
