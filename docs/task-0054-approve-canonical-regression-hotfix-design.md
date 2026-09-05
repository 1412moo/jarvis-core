# task-0054 `/approve` canonical 검증 회귀 hotfix 설계

- task: `task-0054-approve-canonical-regression-hotfix`
- 기준선: `a6c4ef3` (= `origin/main`)
- 원인 커밋: `a6c4ef3`(task-0052) — 승인 전이를 durable writer로 옮기면서 노출됨
- 상태: **설계 단계. 구현 없음.** Owner 결정 대기
- 작성: 2026-09-05

## 1. 무엇이 깨졌는가

task-0052가 승인 전이(`NEEDS_APPROVAL→DOING`/`FAILED`)를
`task_file_writer.transition_task_file_status`로 옮겼다. 이 함수는 전이 전에
`_transition_metadata`로 **파일 전체**를 검증한다. 그 결과 검증을 통과하지 못하는 기존 task
파일에 대해 `/approve`가 `write_failed`로 실패한다.

실측 — 같은 파일에 대해 durable 경로와 이전(inline) 경로를 나란히 실행:

```text
task-0034-local-team-manager-approval-boundary  durable=False(write_failed)  inline=True
task-0031-chatgpt-discord-claude-auto-collab    durable=False(write_failed)  inline=True
task-0037-gemini-cli-local-dev-environment      durable=False(write_failed)  inline=True
```

`memory/tasks/`의 task 파일 **53개 중 21개**가 canonical 검증에 실패한다.

task-0052의 self-check가 놓친 이유는 fixture가 **본문 없는 최소 형태**의 task 파일이기
때문이다. 실제 task 기록은 산문 본문과 불릿 목록을 갖고, summary도 길다.

## 2. 🔴 실패 원인은 하나가 아니라 넷이다

**여기서 이 hotfix의 범위가 결정된다.** 21건을 원인별로 분류했다(중복 없음, 첫 실패 원인 기준).

| 원인 | 건수 | 내용 | status 분포 |
| --- | --- | --- | --- |
| **A. metadata 값에 backtick** | 8 | `summary` 값이 `` `a54316f` `` 처럼 backtick을 포함해 `TASK_METADATA_PATTERN`에 불일치 | 전부 `DONE` |
| **B. 들여쓴 하위 bullet** | 1 | `task-template.md` — 각 metadata 줄 아래 `  - 규칙: …` 설명 | `TODO` |
| **C. 본문 최상위 bullet** | 7 | 본문 산문의 `- ` 목록을 metadata로 오인 | `DONE` 6, **`NEEDS_APPROVAL` 1**(task-0053) |
| **D. `summary` 500자 초과** | 5 | `MAX_SUMMARY_CHARS=500` 초과 | `DONE` 3, `DOING` 1, **`NEEDS_APPROVAL` 1**(task-0034) |

### 2.1 가장 중요한 사실 — `task-0034`는 B/C가 아니라 D다

지시받은 hotfix의 목적은 "기존 task 파일의 **metadata 인식 오류** 해결"이다. 그것은 원인
**B와 C**(8건)에 해당한다.

**그러나 실제로 `/approve`가 깨지는 `task-0034-local-team-manager-approval-boundary`는
원인 D다.** 실측:

```text
task-0034 summary 길이 = 524자   (상한 500,  초과 24자)
task-0034 의 비-metadata '- ' 줄 개수 = 0     ← bullet 문제가 전혀 없다
```

즉 **metadata 인식 오류를 고쳐도 `task-0034`의 `/approve`는 여전히 실패한다.**
이 hotfix가 "회귀 해소"를 표방하려면 A·D를 어떻게 할지도 함께 정해야 한다(§6 결정 2·3).

## 3. parser bug인가, 기존 format의 계약 위반인가

지시대로 원인별로 판정했다. **하나의 답이 아니다.**

### 3.1 B·C(bullet) — **parser 경계 결함으로 판정**

근거 넷:

1. **저장소 자체 템플릿이 거부된다.** `memory/tasks/task-template.md`는 이 저장소가 문서화한
   task 파일 형식인데 canonical 검증에 실패한다(`task_file_invalid_metadata`). 템플릿이 각
   metadata 줄 아래에 `  - 규칙: …` 설명을 다는 구조이기 때문이다. **문서화된 형식이 파서에
   거부된다면 계약 위반은 파일 쪽이 아니다.**
2. **`_transition_metadata`는 `line.lstrip().startswith("- ")`로 판정한다.** 들여쓰기를 벗겨서
   보므로 하위 bullet도 metadata 후보가 된다. 이는 "metadata는 문서 상단 헤더 블록"이라는
   실제 형식과 어긋난다.
3. **canonical writer 자신은 본문을 만들지 않는다.** `_render_task_markdown`은 제목 + metadata
   줄만 생성한다. 즉 파서의 가정("모든 `- ` 줄은 metadata")은 **자기가 만든 파일에 대해서만
   참**이고, 사람이 쓴 기록에 대해 검증된 적이 없다.
4. **같은 저장소의 두 파서가 다르게 동작한다.** `bot_minimal._read_task_metadata`는 패턴에
   맞지 않는 줄을 `continue`로 **건너뛴다**. canonical은 **거부**한다. 같은 형식을 읽는 두
   구현이 불일치한다.

→ metadata 줄로 인정하는 **범위**가 잘못됐다. 각 metadata 줄에 적용되는 검증(어휘·타입·길이·
빈값·제어문자)은 **하나도 건드릴 필요가 없다.** 범위를 바로잡는 것은 완화가 아니다.

### 3.2 A(backtick) — **파일 쪽 계약 위반으로 판정**

`TASK_METADATA_PATTERN`은 `` ^- (?P<field>[a-z][a-z0-9_]*): `(?P<value>[^`\r\n]*)`$ `` 이다.
값이 backtick으로 **구분**되므로 값 안의 backtick을 허용하면 형식이 모호해진다. 이 제약은
근거가 있다.

문제의 8개 파일은 summary에 `` `memory/tasks/…` ``, `` `a54316f` `` 같은 인용을 넣었다.
**파서가 아니라 내용이 계약을 어긴 것이다.** 파서를 고쳐 허용하면 형식이 무너진다.

→ **파서를 바꾸지 않는다.** 해결은 내용 정리(별도 마이그레이션) 또는 이스케이프 규칙 도입이며,
어느 쪽이든 이 hotfix의 최소 범위 밖이다.

### 3.3 D(길이 초과) — **파일 쪽 계약 위반으로 판정**

`MAX_SUMMARY_CHARS = 500`은 의도된 상한이고, 완화는 금지 사항이다. `task-0034`는 524자다.

→ **파서를 바꾸지 않는다.** 해결은 summary 축약이며 내용 변경이다.

## 4. 최소 수정안 (원인 B·C 한정)

`_transition_metadata`가 metadata로 인정하는 **범위**를 헤더 블록으로 한정한다.

```text
규칙:
  - 들여쓴 줄과 빈 줄은 건너뛴다 (metadata 도 아니고 블록 종료도 아니다)
  - 최상위(col 0) 줄만 본다
  - 첫 metadata 줄에서 블록이 시작된다
  - 시작 후 metadata 패턴에 맞지 않는 최상위 줄을 만나면 블록이 끝난다
검증:
  - 블록 안의 각 줄에는 현재와 동일한 검증을 그대로 적용한다
  - 어휘·타입·길이·빈값·제어문자 규칙은 한 글자도 바꾸지 않는다
```

### 4.1 후보 규칙 실측 비교

53개 파일에 대해 필수 metadata 7개 필드를 확보하는지로 평가했다.

| 규칙 | 필수필드 확보 | 남는 실패 |
| --- | --- | --- |
| 현재(`lstrip` 후 `- ` 전부) | 38/53 | 15 |
| col0 `- ` 줄만 | 39/53 | 14 |
| col0 + 패턴 일치만(불일치 무시) | 46/53 | 8 — **불일치를 조용히 넘겨 실제 오류를 숨긴다** |
| 연속 헤더 블록(들여쓴 줄에서 종료) | 45/53 | 9 — **템플릿이 더 나빠진다**(첫 하위 bullet에서 블록이 끊김) |
| **헤더 블록 + 들여쓴 줄 무시 (제안)** | **46/53** | **8 — 전부 원인 A** |

제안 규칙은 **B와 C를 모두 해소하고, 남는 8건은 정확히 원인 A**다. A는 §3.2대로 파서가
고칠 문제가 아니므로, 이 결과는 "고쳐야 할 것만 고쳤다"는 뜻이다.

### 4.2 이 수정이 완화가 아닌 이유

- 어휘(`TASK_ALLOWED_METADATA`), 타입(boolean/timestamp), 길이(`MAX_*_CHARS`),
  `allow_empty=False`, 제어문자 검사 — **전부 그대로다.**
- 바뀌는 것은 **"어느 줄이 metadata인가"** 뿐이다.
- 헤더 블록 안의 잘못된 metadata 줄은 **여전히 거부된다.**

### 4.3 이 수정이 남기는 위험

헤더 블록 **뒤**에 놓인 metadata 형태의 줄은 더 이상 검사되지 않는다. 두 가지 영향:

1. 본문에 실수로 쓴 `- status: \`DONE\`` 같은 줄이 무시된다 — 현재는 중복으로 거부된다.
2. **`_write_execution_review_metadata`가 파일 끝에 append하는 실행 메타데이터가, 본문이 있는
   파일에서는 헤더 블록 밖이 되어 검증을 받지 않는다.** 이는 task-0053과 직접 얽힌다
   (task-0053 §10.2 결정 C).

## 5. 재현과 테스트 계획

### 5.1 `task-0034` 재현 (필수)

```text
전제: memory/tasks/task-0034-local-team-manager-approval-boundary.md, status=NEEDS_APPROVAL
실행: /approve task-0034-local-team-manager-approval-boundary approve
현재: applied=False, reason='write_failed'   (durable 경로)
비교: inline 경로에서는 applied=True         (task-0052 이전 동작)
원인: summary 524자 > MAX_SUMMARY_CHARS(500) → task_file_field_too_long
```

**이 재현 테스트는 §4의 최소 수정만으로는 통과하지 않는다.** 원인 D이기 때문이다.
결정 3에서 D를 어떻게 처리할지 정해야 이 테스트가 녹색이 된다.

### 5.2 회귀 테스트 (반드시 추가)

| 테스트 | 내용 |
| --- | --- |
| **실제 저장소 파일 전수 검증** | `memory/tasks/*.md` 53개에 대한 canonical 검증 통과율. 현재 32/53 → 수정 후 기대 40/53(B·C 해소) |
| **`task-0034` `/approve`** | 지시받은 필수 항목. 원인 D가 해소돼야 통과 |
| 템플릿 검증 | `task-template.md`가 통과해야 한다 — 저장소가 문서화한 형식이므로 |
| 본문 bullet 파일 | 본문에 `- ` 목록이 있는 파일의 `/approve` |
| 헤더 블록 내 오류는 여전히 거부 | 블록 안에 미허용 필드·잘못된 타입·초과 길이를 넣으면 **거부되어야 한다** |
| 헤더 블록 밖 metadata | §4.3의 위험을 명시적으로 고정하는 테스트 |
| before/after 결정론적 대조 | task-0052에서 쓴 방식 — `a6c4ef3` 대비 21개 실패 파일의 `/approve` 결과 |
| 기존 회귀 | self-check 77건, audit-chain 6건, 회귀 10종, 콘솔 계약 테스트 |

## 6. Owner Decision

### 결정 1 — 최소 수정 범위를 B·C로 한정하는가 🔴

| | 선택지 | 바뀌는 파일 | 결과 |
| --- | --- | --- | --- |
| A | **B·C만 수정**(§4의 헤더 블록 규칙) | `task_file_writer._transition_metadata` | 21건 중 8건 해소. **`task-0034`는 여전히 실패** |
| B | B·C 수정 + A·D를 내용 정리로 함께 해소 | 위 + `memory/tasks/` 13개 파일 | 21건 전부 해소. 파일 변경이 커진다 |
| C | 파서를 건드리지 않고 내용만 정리 | `memory/tasks/` 21개 파일 | 템플릿까지 고쳐야 하고, 앞으로 쓰는 기록마다 같은 제약을 받는다 |

**추천 A + 결정 3의 D 처리.** §3의 판정대로 B·C만 파서 결함이고 A·D는 내용 문제다. 다만 A만
하면 지시받은 `task-0034` 재현 테스트가 통과하지 못하므로, D 처리를 함께 정해야 한다.
C는 저장소가 문서화한 템플릿까지 파서에 맞추라는 뜻이라 방향이 거꾸로다.

### 결정 2 — 원인 A(backtick)를 어떻게 처리하는가

| | 선택지 | 결과 |
| --- | --- | --- |
| A | **이번 hotfix에서 제외** | 8건(전부 `DONE`)은 계속 실패. `/approve` 대상이 아니라 실사용 영향은 없다 |
| B | 해당 파일들의 summary에서 backtick 제거 | 8개 파일 변경. 별도 커밋 |
| C | 형식에 이스케이프 규칙 도입 | 파서·writer·모든 판독부에 영향. hotfix 범위 초과 |

**추천 A.** 8건 전부 `DONE`이라 승인·실행 경로가 닿지 않는다. C는 형식 변경이라 hotfix가 아니다.

### 결정 3 — 원인 D(`summary` 500자 초과)를 어떻게 처리하는가 🔴

**`task-0034` 재현 테스트의 통과 여부가 여기에 달려 있다.**

| | 선택지 | 바뀌는 것 | 결과 |
| --- | --- | --- | --- |
| A | **해당 5개 파일의 summary를 500자 이내로 축약** | `memory/tasks/` 5개 파일 | `task-0034` `/approve` 복구. 길이 제한은 그대로 |
| B | `MAX_SUMMARY_CHARS` 상향 | `task_file_writer` | **금지 사항**(length validation 완화) |
| C | 이번 범위에서 제외 | 없음 | `task-0034` `/approve`가 계속 깨진 채로 남는다 |

**추천 A.** B는 금지, C는 지시받은 필수 재현 테스트를 포기하는 것이다. 축약은 내용 손실이므로
**원문 요약을 본문 섹션으로 옮기고 summary는 규격 안에서 다시 쓴다.**

### 결정 4 — 헤더 블록 밖 metadata를 어떻게 다루는가

§4.3의 위험이자 task-0053과 얽힌 항목이다.

| | 선택지 | 결과 |
| --- | --- | --- |
| A | **무시하고 문서화** | 구현 단순. 본문의 잘못된 metadata 줄이 조용히 지나간다 |
| B | 헤더 블록 밖에 metadata 형태 줄이 있으면 **거부** | 본문에 `- key: \`value\`` 형태를 쓸 수 없게 된다 — 기존 기록 다수가 다시 실패할 수 있다 |
| C | 경고만 남기고 통과 | 반환 형식에 경고 채널이 없다 |

**추천 A.** B는 §2의 실패를 되살릴 위험이 크다. 다만 이 선택이 task-0053의 실행 메타데이터
검증 비대칭을 만든다는 사실을 **양쪽 문서에 남긴다**.

### 결정 5 — hotfix를 task-0053보다 먼저 내보내는가

| | 선택지 | 결과 |
| --- | --- | --- |
| A | **hotfix 먼저 단독 커밋** | 회귀가 빨리 닫힌다. task-0053은 그 위에서 진행 |
| B | task-0053과 함께 | 회귀가 그동안 남는다 |

**추천 A.** `/approve`는 Owner의 핵심 경로이고 이미 push된 상태다.

## 7. 이번 단계에서 하지 않는 것

- **구현 일체** — 이 문서는 설계뿐이다
- metadata validation 완화 / `allow_empty` 확대 / max length 완화 / 타입 검증 우회 /
  canonical writer 기존 검증 삭제
- 원인 A(backtick)의 형식 이스케이프 규칙 도입
- task-0053의 실행결과 durable 전이 — 별도 task
- 기존 task 파일의 대규모 마이그레이션 — 결정 2·3에서 정해지는 최소 범위만
- `/run`·`/retry` 의미론 변경, audit event schema 변경
