# task-0054-approve-canonical-regression-hotfix

- id: `task-0054-approve-canonical-regression-hotfix`
- title: `/approve canonical 검증 회귀 hotfix (task-0052 후속)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-05 14:00 UTC`
- updated_at: `2026-09-05 15:20 UTC`
- summary: `task-0052가 승인 전이를 canonical durable writer로 옮기면서, 파일 전체를 검증하는 _transition_metadata에 걸려 기존 task 파일 다수의 /approve가 write_failed로 실패하는 회귀가 발생했다. 원인은 넷으로 갈렸고 그중 bullet 인식(B·C)만 parser 경계 결함이라 판정해 metadata 인정 범위를 헤더 블록으로 한정했다. 검증 규칙 자체는 완화하지 않았다. 실제 /approve 장애를 일으킨 것은 summary 길이 초과(D)였고 대상은 5건이 아니라 7건으로 정정됐다. 7개 파일은 원문을 본문으로 옮기고 summary만 규격 내로 재구성했다. task-0034 /approve 재현 PASS, 전체 검증 PASS.`
- source_command: `task-0053 설계 중 발견 → Owner 결정 1로 별도 hotfix 분리`

## 기준선

- HEAD `a6c4ef3` = `origin/main`
- 원인 커밋 `a6c4ef3`(task-0052) — 승인 전이의 durable writer 전환으로 노출됨

## 무엇이 깨졌는가

`transition_task_file_status`는 전이 전에 `_transition_metadata`로 **파일 전체**를 검증한다.
검증을 통과하지 못하는 기존 task 파일은 `/approve`가 `write_failed`가 된다.

실측(같은 파일, durable 경로 vs task-0052 이전 inline 경로):

```text
task-0034-local-team-manager-approval-boundary  durable=False(write_failed)  inline=True
task-0031-chatgpt-discord-claude-auto-collab    durable=False(write_failed)  inline=True
task-0037-gemini-cli-local-dev-environment      durable=False(write_failed)  inline=True
```

task-0052의 self-check가 이를 놓친 이유는 fixture가 **본문 없는 최소 형태**의 task 파일이기
때문이다. 실제 task 기록은 산문 본문과 불릿 목록을 갖고, summary도 길다.

## 🔴 수치 정정 — 20건이 아니라 21건

task-0053 설계 중 최초 보고는 **"53개 중 20개 실패"**였다. 이후 원인별로 분류하는 과정에서
**21건**으로 정정됐다. 사유는 그 사이에 `task-0053` task 기록을 새로 작성했고, 그 기록이
본문에 불릿 목록을 갖고 있어 같은 원인 C에 걸렸기 때문이다. 즉 파일이 하나 늘어난 것이지
계수 오류가 아니다.

**이 사실 자체가 원인 C의 성격을 보여준다** — 이 저장소에서 새 task 기록을 정상적으로 쓰면
그 파일은 곧바로 canonical 검증에 실패했다.

## 🔴 실패 원인은 넷이다 (중복 없는 분류, 21건)

| 원인 | 최초 | **정정** | 내용 | 판정 |
| --- | --- | --- | --- | --- |
| **A. metadata 값에 backtick** | 8 | 8 | summary가 `` `a54316f` `` 같은 인용을 포함해 `TASK_METADATA_PATTERN` 불일치 | 파일 쪽 계약 위반 → **이번 제외** |
| **B. 들여쓴 하위 bullet** | 1 | 1 | `task-template.md`의 `  - 규칙:` 설명 줄 | **parser 경계 결함 → 수정** |
| **C. 본문 최상위 bullet** | 7 | 7 | 본문 산문 목록을 metadata로 오인 | **parser 경계 결함 → 수정** |
| **D. summary 500자 초과** | 5 | **7** | `MAX_SUMMARY_CHARS=500` 초과 | 파일 쪽 계약 위반 → **내용 정정** |

### D가 5건에서 7건으로 정정된 경위

**parser 경계를 수정하자 가려져 있던 2건이 드러났다.** `task-0046`과 `task-0047`은 본문에
불릿 목록이 있어 `task_file_invalid_metadata`(원인 C)로 **먼저** 걸렸고, 그 뒤에 있는 길이
검사까지 도달하지 못했다. C를 해소하자 두 파일이 `task_file_field_too_long`으로 바뀌었다.

Owner가 7건 처리를 승인했다.

### 가장 중요한 사실 — `task-0034`는 B/C가 아니라 D였다

지시받은 hotfix 목적은 "metadata 인식 오류 해결"(= B·C)이었다. 그러나 실제로 `/approve`가
깨지던 `task-0034`는 원인 D였다.

```text
task-0034 summary 길이 = 524자  (상한 500, 초과 24자)
task-0034 의 비-metadata '- ' 줄 = 0개      ← bullet 문제가 전혀 없다
```

**parser만 고쳤다면 `task-0034`의 `/approve`는 복구되지 않았다.** 그래서 D 처리를 함께
포함했다.

## parser bug인가 계약 위반인가 — 원인별 판정

### B·C → **parser 경계 결함** (수정 대상)

1. **저장소가 문서화한 `task-template.md`가 거부된다.** 문서화된 형식이 파서에 거부되면
   계약을 어긴 쪽은 파일이 아니다.
2. `_transition_metadata`가 `line.lstrip().startswith("- ")`로 판정해 **들여쓴 하위 bullet까지**
   metadata 후보로 잡았다.
3. `_render_task_markdown`은 본문을 만들지 않는다 — 파서의 가정("모든 `- ` 줄은 metadata")은
   **자기가 만든 파일에 대해서만** 참이었고 사람이 쓴 기록에 대해 검증된 적이 없다.
4. `bot_minimal._read_task_metadata`는 불일치 줄을 `continue`로 **건너뛴다**. 같은 저장소의
   두 파서가 같은 형식을 다르게 읽고 있었다.

→ 잘못된 것은 **metadata로 인정하는 범위**다. 각 줄에 적용되는 검증은 손대지 않았다.

### A(backtick) → **파일 쪽 계약 위반** (이번 제외)

값이 backtick으로 **구분**되므로 값 안의 backtick 금지는 근거 있는 제약이다. 파서를 고쳐
허용하면 형식이 무너진다. 해당 8건은 전부 `DONE`이라 승인·실행 경로가 닿지 않는다.

### D(길이 초과) → **파일 쪽 계약 위반** (내용 정정으로 해소)

`MAX_SUMMARY_CHARS=500`은 의도된 상한이고 완화는 금지 사항이다. 파서를 바꾸지 않고 파일
내용을 규격에 맞췄다.

## 구현

### 1. parser 경계 수정 — `task_file_writer._transition_metadata`

```text
- 들여쓴 줄은 건너뛴다 (metadata 도 아니고 블록 종료도 아니다)
- 최상위(col 0) 줄만 본다
- 첫 최상위 '- ' 줄에서 헤더 블록이 시작된다
- 시작 후 '- ' 로 시작하지 않는 최상위 줄(빈 줄 포함)에서 블록이 끝난다
- 블록 안의 각 줄에는 기존과 동일한 검증을 그대로 적용한다
```

**validation 규칙 자체는 한 글자도 완화하지 않았다.** 어휘(`TASK_ALLOWED_METADATA`),
타입(boolean/timestamp), 길이(`MAX_*_CHARS`), `allow_empty=False`, 제어문자 검사가 전부
그대로다. 헤더 블록 **안**의 잘못된 줄은 여전히 거부된다.

### 2. 기존 task 파일 7건 정정 (원문 보존)

원문 summary를 **한 글자도 줄이지 않고** `## 요약 (원문)` 절로 옮기고, summary 필드만 규격
내에서 다시 썼다. **내용 삭제 없음, status 보존.**

| 파일 | summary 전 → 후 | status |
| --- | --- | --- |
| `task-0029-research-council-live-augmentation` | 881 → 442 | `DONE` 유지 |
| `task-0031-chatgpt-discord-claude-auto-collab-plan` | 668 → 382 | `DOING` 유지 |
| `task-0034-local-team-manager-approval-boundary` | 524 → 410 | `NEEDS_APPROVAL` 유지 |
| `task-0035-local-team-manager-model-benchmark` | 730 → 356 | `DONE` 유지 |
| `task-0038-ai-agent-collaboration-platform-buzz-research` | 1625 → 435 | `DONE` 유지 |
| `task-0046-local-buzz-relay-agent-bridge-feasibility` | 2300 → 377 | `DONE` 유지 |
| `task-0047-local-buzz-relay-handson-spike` | 1138 → 367 | `DONE` 유지 |

원문 보존은 기계적으로 확인했다 — 7건 모두 본문 절의 원문 길이가 원본 summary 길이와
**완전히 일치**한다(881/668/524/730/1625/2300/1138).

### 3. 테스트 추가 — `orchestrator/discord-intake/run_smoke_tests.py`

- **경계 단위 테스트 12건**: 정상예 5건(본문 최상위 bullet / 중첩 bullet / 빈 줄 뒤 bullet /
  필드 아래 들여쓴 설명 / 헤더만)과 **반례 7건**(헤더 안의 malformed 필드·미허용 필드·길이
  초과·중복 필드·필수 필드 누락·제어문자·빈 optional text → 전부 기존대로 실패해야 함)
- **저장소 전수 검증**: `memory/tasks`의 실제 기록 전부. 합성 fixture가 아니라 승인 경로가
  실제로 쓰는 파일을 본다 — task-0052의 회귀가 숨었던 지점이다

## `task-template.md`는 canonical 전체 PASS 대상이 아니다

지시에는 "템플릿이 canonical validation을 통과해야 함"이 있었으나 **원리상 불가능**하다.

| 검사 | 템플릿 값 | 결과 |
| --- | --- | --- |
| `TASK_FILE_PATTERN` | `id: task-####-slug` | 불일치 |
| 파일명 일치 | `task-template.md` ≠ `task-####-slug.md` | `task_id_path_mismatch` |
| 타임스탬프 | `YYYY-MM-DD HH:mm UTC` | 형식 불일치 |

전부 **placeholder 값**이다. 통과시키려면 템플릿을 구체값으로 바꾸거나 id·타임스탬프 검증을
완화해야 하는데 전자는 템플릿의 목적을 훼손하고 후자는 금지 사항이다.

**다만 요구의 실질은 달성했다** — placeholder만 유효값으로 치환하면 **구조는 PASS**한다.
즉 들여쓴 `- 규칙:` 설명 줄이 더 이상 metadata로 잡히지 않는다. 이 사실은 경계 단위 테스트
`indented_note_under_field_ignored`가 고정한다. 전수 검증에서는 템플릿을 이유와 함께
명시적으로 제외했다.

## 검증

### `task-0034` `/approve` 재현

실제 저장소가 아니라 **temp fixture**에 파일을 복사해 실행했다.

| | `a6c4ef3` (수정 전) | 수정 후 |
| --- | --- | --- |
| status 전 | `NEEDS_APPROVAL` | `NEEDS_APPROVAL` |
| `/approve` 결과 | `applied=False`, `reason='write_failed'` | **`applied=True`, `reason=''`** |
| status 후 | `NEEDS_APPROVAL`(전이 실패) | **`DOING`** |
| `audit_error` | – | `None` |

### canonical validation 전수 (분모를 정확히 구분)

| 집합 | 개수 |
| --- | --- |
| `memory/tasks/task-*.md` 전체 | **55** |
| ├ `a6c4ef3` 시점 기존 task 기록 | 52 |
| ├ 이번 세션 신규 기록(task-0053, task-0054) | 2 |
| └ 템플릿(`task-template.md`) | 1 |
| **검증 대상** (= 전체 − 템플릿) | **54** |
| **PASS** | **46** |
| **FAIL** | **8** (전부 원인 A backtick, 이번 범위 밖) |

기존 task 기록 52개만 보면 **PASS 44 / FAIL 8**이다.
기준선 `a6c4ef3`에서는 같은 55개 기준 PASS 32였다.

### 그 외

| 검증 | 결과 |
| --- | --- |
| `orchestrator/discord-intake` 스모크 | **77/77 PASS** (기존 11 + 신규 66) |
| `bot_minimal` self-check | **77/77 PASS** |
| `orchestrator/audit-chain` | **6/6 PASS** |
| 기존 회귀 9종 | 전건 PASS |
| secret scan | 변경 파일 findings **0건**. 전체 7건은 `check_no_secrets.py` 자체 fixture(기존 상태) |
| probe 유입 | `memory/tasks`에 테스트·probe 파일 **0건** — 재현은 전부 temp state로 실행 |

## 남은 위험 (문서화)

헤더 블록 **밖**의 metadata 형태 줄은 더 이상 검사되지 않는다. 특히
`_write_execution_review_metadata`가 파일 끝에 append하는 실행 메타데이터는 본문이 있는
파일에서 검증을 받지 않게 된다. metadata-only 파일에서는 계속 검증된다.
**이 비대칭은 task-0053에서 다룬다**(task-0053 설계 문서 §10.2 결정 C).

## 이번 단계 비범위

- 원인 A(backtick) 8건 수정 — 파일 쪽 계약 위반이며 별도 결정
- 이스케이프 규칙 도입 등 형식 변경
- task-0053의 실행결과 durable 전이
- 헤더 블록 밖 metadata 비대칭 해소
- validation 완화 / `allow_empty` 확대 / max length 확대 / 타입 검증 완화 — 전부 금지 준수
- `/run`·`/retry` 의미론 변경, audit event schema 변경, ⑤-c 전역 status gate,
  불일치 탐지·수동 복구 기능
