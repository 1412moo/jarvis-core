# Task Model (Minimum)

`jarvis-core`에서 외부 명령을 내부 작업(Task)으로 기록/추적하기 위한 최소 데이터 구조를 정의한다.

## 1) Task ID 구조
- 형식: `task-####-slug`
- 규칙:
  - `####`: 4자리 순번(예: `0001`, `0002`)
  - `slug`: 작업 목적을 설명하는 짧은 소문자 하이픈 문자열
- 예시:
  - `task-0001-bootstrap`
  - `task-0002-report-system`

## 2) 상태값 정의 (기존 상태 재사용)
아래 상태값은 `reports/README.md`의 정의를 재사용한다.

- `TODO`: 시작 전 상태
- `DOING`: 진행 중 상태
- `BLOCKED`: 외부 요인으로 진행 불가
- `ON_HOLD`: Owner의 우선순위 판단으로 의도적 보류 (외부 요인이 아니라는 점에서 `BLOCKED`와 구분). 보류 전 상태를 `hold_from`에 기록하고, 해제는 그 상태로만 돌아간다(5-1, 12절)
- `DONE`: 검증까지 완료
- `FAILED`: 시도했으나 목표 달성 실패
- `NEEDS_APPROVAL`: 승인 필요 상태

## 3) 필수 필드
모든 Task는 아래 필드를 반드시 포함한다.

- `id`: Task 고유 식별자 (`task-####-slug`)
- `title`: 사람이 읽는 작업 제목
- `status`: 현재 상태 (`TODO | DOING | BLOCKED | ON_HOLD | DONE | FAILED | NEEDS_APPROVAL`)
- `repo`: 작업 대상 저장소 식별자 (예: `jarvis-core`, `subrepo-abc`)
- `created_at`: 생성 시각 (UTC, `YYYY-MM-DD HH:mm UTC`)
- `updated_at`: 마지막 수정 시각 (UTC, `YYYY-MM-DD HH:mm UTC`)
- `summary`: 현재 작업 요약(목표/진행상황/핵심 메모)

## 4) 저장 방식 선택
이번 단계에서는 **Markdown(`.md`) 파일 저장 방식**을 사용한다.

선택 이유:
1. 사람이 바로 읽고 수정할 수 있다.
2. 코드/도구 없이도 Git diff로 변경 이력을 쉽게 추적할 수 있다.
3. 초기 단계에서 구조/기록 중심 원칙에 맞고 운영 부담이 작다.
4. 추후 Discord 연동 시에도 텍스트 기반 파싱으로 확장 가능하다.

## 5) 상태 변경 흐름
기본 흐름과 예외 흐름을 함께 사용한다.

- 기본: `TODO → DOING → DONE`
- 차단 해소 흐름: `TODO → BLOCKED → DOING → DONE`
- 승인 기반 흐름: `TODO → NEEDS_APPROVAL → DOING`

운영 규칙:
- `DONE`은 검증 근거가 있을 때만 사용한다.
- `BLOCKED`는 차단 사유를 `summary`에 명시한다.
- `NEEDS_APPROVAL`는 승인 요청 항목/사유를 `summary`에 남긴다.

### 5-1) 허용 전이 계약

코드가 적용하는 상태 전이는 아래 10쌍뿐이다. 표에 없는 전이는 durable writer가
거부한다.

| from | to |
| --- | --- |
| `TODO` | `DOING` |
| `DOING` | `DONE` |
| `DOING` | `FAILED` |
| `FAILED` | `TODO` |
| `NEEDS_APPROVAL` | `DOING` |
| `NEEDS_APPROVAL` | `FAILED` |
| `TODO` | `ON_HOLD` |
| `NEEDS_APPROVAL` | `ON_HOLD` |
| `ON_HOLD` | `TODO` |
| `ON_HOLD` | `NEEDS_APPROVAL` |

`ON_HOLD`가 들어간 4쌍은 `hold_from`을 함께 쓰고 지우는 전용 writer만 적용한다. 일반 전이
writer는 이 4쌍을 거부한다. `DOING`에서는 실행이 진행 중일 수 있으므로 `ON_HOLD`로 가는
전이가 없다. 해제의 도착 상태는 `hold_from` 값 하나로 정해진다(12절).

자동 전이는 Owner가 승인한 실행의 결과로 코드가 적용하는 전이를 뜻한다. 그런
실행 없이 스스로 일어나는 전이는 없다.

### 5-2) 전이 발생 경로

아래는 현재 구현에서 5-1의 전이를 일으키는 경로다. 새 경로는 5-1에 있는 전이만
쓸 수 있다.

| 경로 | 적용 전이 |
| --- | --- |
| Jarvis Console Start | `TODO` → `DOING` |
| Jarvis Console Complete | `DOING` → `DONE` |
| Discord `/go` (TODO task) | `TODO` → `DOING` |
| Discord `/go` 재시도·resume, `/retry` (FAILED task, `/retry`는 `/work`로 만든 task 제외, task-0167) | `FAILED` → `TODO`, 바로 이어서 `TODO` → `DOING` |
| Discord `/go <id> accept` (`qa_unverified_owner_review` 기록이 있는 FAILED task, QA 재실행 통과 뒤에만) | `FAILED` → `TODO`, 바로 이어서 `TODO` → `DOING` |
| Discord `/approve` 승인 / 거절 | `NEEDS_APPROVAL` → `DOING` / `NEEDS_APPROVAL` → `FAILED` |
| 실행 결과 기록 `_apply_execution_result` (`/approve`·`/run`·`/retry`·`/go` 실행 뒤) | 성공 `DOING` → `DONE`, 실패 `DOING` → `FAILED` |
| Discord `/go <id> recover` (`/work`로 만든 DOING task, 실행 중인 Worker가 없고 마지막 시도의 실행 표지가 가리키는 프로세스가 모두 끝났을 때만, task-0167) | `DOING` → `FAILED` (실패 기록과 함께, 재실행 없음) |
| Jarvis Console Hold (표시된 task, `HOLD TASK`, `hold_from`에 출발 상태를 함께 기록, task-0173) | `TODO` → `ON_HOLD`, `NEEDS_APPROVAL` → `ON_HOLD` |
| Jarvis Console Resume (표시된 task, `RESUME TASK`, `hold_from`이 가리키는 상태로만 복귀하고 `hold_from`을 지움, task-0173) | `ON_HOLD` → `TODO` (`hold_from`이 `TODO`일 때), `ON_HOLD` → `NEEDS_APPROVAL` (`hold_from`이 `NEEDS_APPROVAL`일 때) |

Hold와 Resume은 승인도 거절도 아니며 실행하지 않는다. 승인 대기였던 task는 Resume 뒤에도
`NEEDS_APPROVAL`이므로 실행에 이르는 길은 Discord `/approve`뿐이다.

## 6) 새 Task 생성 체크리스트
새 Task를 만들 때 아래 항목을 순서대로 확인한다.

1. `memory/tasks/task-template.md`를 복사해 새 파일(`task-####-slug.md`)을 만든다.
2. 파일명과 `id`가 동일한지 확인한다.
3. `status`가 7개 허용값 중 하나인지 확인한다.
4. `repo`, `created_at`, `updated_at`를 실제 값으로 채운다.
5. `summary`를 1~3문장으로 작성하고 범위/확인 필요사항을 반영한다.
6. 커밋 전 최소 1회 자체 검토로 누락 필드가 없는지 확인한다.

## 7) updated_at 갱신 규칙
- `status`가 바뀌면 반드시 `updated_at`를 현재 UTC 시각으로 갱신한다.
- `summary`, `title`, `repo` 등 본문 의미가 바뀌어도 `updated_at`를 갱신한다.
- 오탈자만 수정해도 이력이 중요하면 갱신하고, 단순 포맷 정리는 팀 규칙에 따라 생략할 수 있다.

## 8) DONE 전환 최소 검증 근거
`status: DONE`으로 바꾸기 전에 아래 최소 근거를 남긴다.

1. 완료 산출물(문서/커밋/PR/리포트) 식별 정보 1개 이상.
2. 사람이 재확인 가능한 검증 흔적(체크 결과, 리뷰 코멘트, 보고서 링크) 1개 이상.
3. 범위 내 미완료 항목이 없거나, 남아 있다면 후속 Task로 분리했다는 메모.

## 9) BLOCKED / NEEDS_APPROVAL 시 summary 필수 기재 정보
- `BLOCKED`: 무엇이 막았는지(원인), 누가/무엇이 해소 가능한지(의존 주체), 다음 재시도 조건을 반드시 남긴다.
- `NEEDS_APPROVAL`: 어떤 항목의 승인이 필요한지(대상), 왜 필요한지(사유), 승인되면 바로 할 다음 작업을 반드시 남긴다.
- `ON_HOLD`: 보류를 결정한 주체(Owner), 보류 사유, 재개 조건(재개에 필요한 Owner 결정)을 Hold 전에 summary에 남긴다. 보류 결정을 담은 별도 task 기록이 있으면 그 id를 summary에 적는다(예: task-0156). 보류 전 상태는 `hold_from`이 기록하며 Resume은 그 상태로만 되돌린다. Jarvis는 summary에 사유가 있는지 판정하지 않는다.

## 10) Optional Execution Metadata
Execution-related fields are optional. The canonical writer
(`record_task_execution_result` in `orchestrator/discord-intake/task_file_writer.py`)
records them after the execution flow produces a result, in the same atomic replace
that applies the resulting status transition (task-0055). They live **inside the
metadata header block** — the contiguous run of metadata lines at the top of the file —
not appended at the end of the document (task-0054).

### Stored fields
Exactly these eight fields are stored on disk. Any other `- name:` line inside the
header block is rejected as `task_file_unsupported_metadata`.

| Field | Type | Meaning |
| --- | --- | --- |
| `execution_candidate` | boolean | Whether the execution flow selected a candidate. It is **not** the candidate itself. |
| `execution_request` | text | Compact JSON for the request built from the candidate. |
| `execution_result` | text | Compact JSON for the recorded execution result. Its `output_summary` is not repeated here, because `execution_summary` already carries it. |
| `executed` | boolean | Whether the run actually happened. |
| `success` | boolean | Whether the run succeeded. |
| `dry_run` | boolean | Whether the run was a dry run. |
| `execution_updated_at` | timestamp | Metadata update time in UTC, `YYYY-MM-DD HH:MM UTC`. |
| `execution_summary` | text | Short output or error summary. |

The three types are the canonical ones, enforced on every write and re-checked on
every read:

- **boolean**: the literal `true` or `false`, and nothing else — not `True`, not `1`, not an empty value.
- **text**: at most 500 characters, no control/format/surrogate characters, and not empty. A field with no value is omitted rather than written blank.
- **timestamp**: exactly `%Y-%m-%d %H:%M UTC`.
- No value of any type may contain a backtick, which is the value delimiter itself.

Note that `execution_candidate` here is the task-file field. The payload of the
same name in `docs/execution-contract.md` — `approve_file_write_result.execution_candidate`,
an object or `null` — is a different thing. Only the boolean derived from it, whether a
candidate existed at all, reaches the file.

### Derived fields — reconstructed on read, never stored
`error`, `mode`, `reason`, `message` and `execution_status` were once stored here
too. task-0053 removed them from disk: each was a duplicate of, a constant beside,
or computable from the eight fields above, and none of them belongs to the canonical
vocabulary. **Writing any of the five into a task file now fails canonical
validation** (`task_file_unsupported_metadata`).

Command output did not change, because each value is reconstructed exactly when the
file is read:

| Derived value | Reconstructed from |
| --- | --- |
| `error`, `reason` | `error_reason` inside the stored `execution_result` JSON |
| `message` | `execution_summary` when `executed` is `true`; empty otherwise |
| `mode` | the constant `real` — the only mode this write path has ever used |
| `execution_status` | `success` when `executed` and `success`; `failed` when `executed` alone; `not_executed` otherwise |

### How the fields surface
- `/status` prints, in this order and skipping every empty value: `executed`, `success`, `dry_run`, `mode`, `reason`, `error`, `message`, `execution_status`, `execution_updated_at`, `execution_summary`. So stored and derived values appear side by side, indistinguishable in the output. `execution_candidate`, `execution_request` and `execution_result` are carried in the result payload but are not printed.
- `/review-task` reports `execution_status`, `execution_updated_at` and `execution_summary` only.
- A task with no execution metadata shows no execution section in either command.

These fields do not replace the required task fields. If no execution result has been recorded, all of them are absent.

## 11) Optional Completion Evidence

`completion_evidence` is an optional, append-once metadata field for a valid
`DOING` Task:

```markdown
- completion_evidence: `VALUE`
```

- Omit the field until evidence is recorded; never add an empty template row.
- Record Completion Evidence inserts the line immediately after the unique
  `summary` metadata line and updates only `updated_at`.
- The evidence value is normalized to one safe, non-empty line of 1–500 Unicode
  code points. It cannot contain Markdown backticks, control/format/surrogate
  characters, or Unicode line/paragraph separators.
- Evidence recording does not validate the claim, execute work, change status,
  or automatically complete the Task. `Complete` remains a separate explicit
  Preview + Confirm action.
- An existing evidence value cannot be overwritten, deleted, or appended again.

## 12) Hold metadata (`hold_from`, task-0173)

`hold_from` is an optional metadata field that exists exactly while a Task is
`ON_HOLD`:

```markdown
- hold_from: `NEEDS_APPROVAL`
```

- Allowed values are `TODO` and `NEEDS_APPROVAL`, the two statuses Hold accepts.
  Any other value, a duplicate line, an `ON_HOLD` Task without the field, or the
  field on a Task in any other status fails canonical validation in both the
  writer and the Console parser.
- Jarvis Console Hold writes the status, `updated_at` and this line (right after
  the `status` line) in one atomic replace. Jarvis Console Resume returns the Task
  to exactly the recorded status and removes the line in one atomic replace. The
  caller cannot choose the Resume target. Any failure leaves the file unchanged.
- No other path writes or removes the field. A hand-written `ON_HOLD` record
  without it is invalid and cannot be resumed; this is stricter than before
  task-0173, when no such record existed.
