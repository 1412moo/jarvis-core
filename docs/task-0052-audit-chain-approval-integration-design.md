# task-0052 승인 경로 ↔ 감사 해시체인 연동 설계

- task: `task-0052-audit-chain-approval-integration`
- 선행: `task-0044`(감사 해시체인 코어, commit `116fe2d`)
- 상태: **설계 단계. 구현 없음. 착수는 Owner 승인 대상**(§5)
- 작성: 2026-09-05

## 1. 목적/배경

task-0044는 Owner 결정 3(a)에 따라 **코어와 CLI만** 만들었다. 그 결과 현재 저장소에는
동작하는 해시체인이 있지만 **그것을 호출하는 코드가 한 곳도 없다**(전수 검색 0건).
체인 파일은 비어 있고, 확정된 두 스키마(`owner_approval` / `execution_result`)는 정의만
존재한다.

이 task는 그 공백을 메운다. **승인·실행 사건이 실제로 체인에 기록되게 하는 것**이 유일한
목적이며, 새 스키마나 새 기능을 만들지 않는다.

task-0044 설계 §2.1의 발견을 다시 적어둔다 — 이 저장소에는 **승인 감사 기록이 아직 하나도
없다.** Owner가 승인 권한을 행사한 사실을 남기는 기록이 어디에도 없다. task-0038 §7.1-4가
"승인 게이트를 외부에 위임하지 마라, 그것을 넘기는 순간 Jarvis-Core에는 남는 것이 없다"고
했는데, 그 승인이 행사된 증거가 없다는 것은 **자산의 증거가 없다**는 뜻이다.

## 2. 현재 구조 분석 (실측)

모든 행 번호는 `adapters/discord/bot_minimal.py`(2,580행), commit `116fe2d` 기준이다.

### 2.1 사건이 발생하는 실제 지점

```text
/approve <id> approve|reject
  └ _run_approve_parse                 (1308)
     └ _build_approve_draft            (709)   decision → transition_to
        └ _build_approve_writer_result (1225)
           ├ _apply_task_status_transition(NEEDS_APPROVAL → DOING|FAILED)  (1285)  ← 쓰기 ①
           └ _run_execution_flow(task_id, "approve_file_write_result")     (1291)

/run <id>   └ _run_run   (1051) └ _run_execution_flow(task_id, "run")      (1091)
/retry <id> └ _run_retry (991)  └ _run_execution_flow(task_id, "retry")    (1039)

_run_execution_flow (965)
  ├ _build_execution_result_real       (1137)  ← subprocess.run (화이트리스트 경유)
  ├ _write_execution_review_metadata   (852)   ← 쓰기 ②
  └ _apply_execution_result_status_transition (1205)
     └ _apply_task_status_transition(DOING → DONE|FAILED)                  (1221)  ← 쓰기 ③
```

`_run_execution_flow`는 **세 곳에서 호출되고 셋 다 서브프로세스에 도달한다.** 승인만
기록하면 실행의 3분의 2가 감사에서 빠진다 — task-0044 결정 2가 `execution_result`를
포함시킨 이유가 이것이다.

### 2.2 스키마가 이미 맞는다 (좋은 소식)

task-0044의 payload 스키마는 바로 이 지점들을 보고 설계됐다. 필드를 다시 협의할 필요가 없다.

| 스키마 필드 | 이 지점에서의 출처 | 확보 |
| --- | --- | --- |
| `owner_approval.command` | `_run_approve_parse`의 `command_text` | ✅ |
| `owner_approval.decision` | `_build_approve_draft`의 `decision` (`approve`/`reject`) | ✅ |
| `owner_approval.transition{from,to}` | `applied_transition` | ✅ |
| `owner_approval.applied` | `_apply_task_status_transition` 반환 | ✅ |
| `owner_approval.reason` | 실패 시 `reason` 문자열 | ✅ |
| `execution_result.source` | `_run_execution_flow(source=...)` | ✅ |
| `execution_result.execution_status_transition_applied` | 반환 dict 동일 키 | ✅ |
| `execution_result.execution_status_transition_reason` | 반환 dict 동일 키 | ✅ |
| `execution_result.result_kind` | `execution_result.executed/success`에서 파생 | ⚠ 매핑 규칙 필요(§9-4) |

`ALLOWED_EXECUTION_SOURCES = {approve_file_write_result, run, retry}`가 실제 호출부의
source 문자열 3개와 **정확히 일치**함을 실측 확인했다.

### 2.3 🔴 쓰기 내구성 — 체인의 전제가 아직 없다

`_apply_task_status_transition`(796)의 실제 쓰기는 이 한 줄이다.

```python
task_file.write_text(new_text, encoding="utf-8")
```

fsync도, atomic replace도, `expected_digest` 동시성 검사도 없다. 정작
`orchestrator/discord-intake/task_file_writer.py`에는 이 셋이 전부 구현돼 있는데
**승인 경로가 그것을 쓰지 않는다.**

task-0044 §6.3이 못박은 대로 — **찢어질 수 있는 쓰기 위에 체인을 얹으면 체인이 깨진 것인지
공격인지 구분할 수 없다.** 이 개선 없이 연동만 하면 체인은 장식이다.

### 2.4 🔴 P2-5 알림 패턴을 그대로 따라가면 안 된다

가장 헷갈리기 쉬운 지점이다. `_publish_approval_notification`(319)의 docstring은 이렇게
말한다 — best-effort이고, `result`를 변경하지 않으며, **절대 raise하지 않고**, 그 반환값이
승인 결과에 되먹임되지 않는다. 호출도 `_run_command`가 끝난 뒤 `on_message`(2536)에서
별도로 이뤄진다.

**이것은 의도된 올바른 설계다** — 알림은 놓쳐도 된다. 그러나 **감사 기록은 정반대다.**

| | 실패 시 | 호출 위치 |
| --- | --- | --- |
| P2-5 Buzz 알림 | 승인은 성공 유지, 별도 보고 | `on_message`(2536), 명령 처리 **바깥** |
| **감사 체인 append** | **승인 자체가 실패** | 명령 처리 **안쪽**, 전이와 같은 트랜잭션 |

기존 코드에 이미 있는 "부가 작업" 훅을 재사용하는 것이 편해 보이지만, 그렇게 하면
task-0044의 요점(fire-and-forget 금지)을 정확히 잃는다.

### 2.5 🔴 신규 발견 — `reject`도 실행 흐름에 도달한다

이번 조사에서 새로 확인한 사실이며, **task-0044 설계 문서에는 없던 내용**이다.

1. `_build_approve_draft`(709)는 `reject`를 `transition_to="FAILED"`, `apply_ready=True`로 만든다.
2. `_build_approve_writer_result`(1225)는 전이 적용 후 **decision과 무관하게** 무조건
   `_run_execution_flow(task_id, "approve_file_write_result")`(1291)를 부른다.
3. `_build_execution_candidate`(920)는 task의 **title/summary 키워드만** 본다 — `status`를
   보지 않는다.
4. 따라서 `/approve <id> reject`도 실행 후보를 만들고 `_build_execution_result_real`(1137)에
   도달한다. `(action, target)`이 `EXECUTION_SCRIPT_WHITELIST`(117)에 있으면 **거부했는데도
   서브프로세스가 돈다.**
5. 그 뒤 `_apply_execution_result_status_transition`(1205)은 `DOING → DONE|FAILED`를
   요구하는데 현재 status는 `FAILED`이므로 `status_mismatch`로 **조용히 실패**한다.

결과: **실행은 일어났고, 상태 전이는 안 됐고, 아무 기록도 남지 않는다.**

현재 화이트리스트 항목이 1개(`discord_intake_smoke_tests` → `run_smoke_tests.py`)뿐이라
실제 피해는 제한적이다. 그러나 이것은 우연한 안전이며, 화이트리스트가 하나만 늘어도 곧바로
커진다.

**이 결함을 이 task에서 고칠지는 Owner 결정 사항이다(§9-5).** 승인 의미론을 바꾸는 일이라
임의로 처리하지 않는다. 다만 이 사례는 **왜 감사 체인이 필요한지**를 가장 선명하게 보여준다 —
지금은 이런 일이 일어나도 남는 기록이 없다.

## 3. 범위 — 이벤트 생성 지점

### 3.1 권고 지점

| # | 사건 | 삽입 위치 | kind |
| --- | --- | --- | --- |
| E1 | Owner 승인/거부 | `_build_approve_writer_result`, 전이 적용 직후(1285 부근) | `owner_approval` |
| E2 | 실행 결과 | `_run_execution_flow` 반환 직전(985 부근) **단 한 곳** | `execution_result` |

**E2는 `/approve`·`/run`·`/retry` 세 호출부에 각각 심지 않는다.** `_run_execution_flow`
안쪽 한 곳에 두면 세 경로가 자동으로 덮이고, 나중에 네 번째 호출부가 생겨도 자동으로
포함된다. 호출부마다 심으면 새 호출부가 조용히 감사에서 빠진다 — §2.1이 보여준 실패
양식과 같은 것이다.

### 3.2 범위 밖으로 두는 후보

- `_write_execution_review_metadata`(852) — 쓰기 ②. 실행 메타데이터는 이미 task 파일에
  남고 체인 대상이 아니다(task-0044 결정 2가 A+B로 한정).
- `/task` 명령 — `PRIVILEGED_COMMANDS`에 포함되지만 상태 전이도 실행도 아니다.
- 읽기 전용 명령(`/status`, `/report`, `/help`, `/plan`, `/review-task`, `/retro`).

## 4. 실패 처리 계약과 순서 문제

task-0044 §6.1이 정한 계약은 **감사 기록 실패 = 작업 실패**다. 그런데 연동 시점에
순서 문제가 생긴다. 전이(쓰기 ①)와 감사 append는 서로 다른 파일에 대한 두 번의 쓰기다.

| 순서 | 감사 append 실패 시 | 문제 |
| --- | --- | --- |
| (i) 감사 먼저 → 전이 | 전이 안 됨. 깨끗함 | **일어나지 않은 전이가 기록**된다. 전이가 뒤이어 실패하면 체인이 거짓말을 한다 |
| (ii) 전이 먼저 → 감사 | 전이는 이미 적용됨 | 되돌릴 것인가? 되돌리기도 실패할 수 있다 |
| (iii) 2단계(의도 기록 → 전이 → 확정 기록) | 중간 상태가 체인에 남음 | 스키마에 `applied` 필드가 이미 있어 표현은 가능. 항목 수가 2배 |

`owner_approval` 스키마에 **`applied: bool`이 이미 있다**는 점이 중요하다 — (i)에서 전이가
실패해도 `applied: false`로 정직하게 기록할 수 있다. 다만 그러려면 전이 결과를 안 상태에서
기록해야 하므로 실질은 (ii)에 가깝다.

**이것이 이 task의 핵심 미해결 질문이다(§9-1).** §2.3의 쓰기 내구성 개선과 묶어서 정해야
한다 — atomic replace가 있으면 (ii)의 "되돌리기" 부담이 크게 줄기 때문이다.

## 5. 🔴 `bot_minimal.py` 직접 수정 여부와 안전 계약

사용자 요청에 따라 명시한다.

### 5.1 직접 수정은 불가피하다

§2.1의 이벤트 지점 **4개가 전부 `bot_minimal.py` 안에 있고**, 훅을 바깥에서 주입할 확장점이
없다. 이 파일을 건드리지 않고 감사 기록을 남기는 방법은 존재하지 않는다.
(로그 파싱 같은 우회는 감사 기록으로서 부적격이다 — 원본이 아니라 추정이 된다.)

### 5.2 protected file인가 — **아니다**

`docs/codex-operating-rules.md` §6 "Protected files와 생성물"이 명시하는 protected file은
**`jarvis.bat` 하나뿐이다.** `bot_minimal.py`는 그 목록에 없다. 따라서 protected file
규정을 근거로 한 차단은 성립하지 않는다.

### 5.3 그러나 안전 계약상 Owner 승인은 필요하다 — **필요함**

protected file이 아닌 것과 승인이 필요 없는 것은 다르다. 근거 셋이다.

1. **AGENTS.md 즉시 escalation gate — "안전 계약 충돌".**
   P2-4가 바로 이 파일에 Owner 인가 게이트를 세웠다 — `PRIVILEGED_COMMANDS`(130),
   `_authorize_command`(207), `_load_owner_ids`(176), 그리고
   `JARVIS_OWNER_DISCORD_USER_IDS` 없이는 기동 자체를 거부하는 fail-closed 시작. 이
   task는 **그 게이트가 감싸고 있는 경로의 내부 동작과 실패 계약을 바꾼다.** 안전 계약
   표면을 건드리는 변경이므로 budget과 무관한 즉시 escalation 대상이다.
2. **AGENTS.md 원칙 3 — "운영 영향 작업".**
   이 파일은 실제로 도는 Discord 봇 런타임이다. §4의 계약을 적용하면 **감사 append가
   실패할 때 `/approve`가 거부된다.** 이는 의도된 설계지만 명백한 가용성 영향이며, Owner가
   그 트레이드오프를 알고 승인해야 한다.
3. **§2.5를 함께 고친다면** 그것은 "거부가 실행을 유발하는가"라는 **승인 의미론 변경**이다.
   이론의 여지 없이 Owner 결정 사항이다.

### 5.4 결론

> `bot_minimal.py`는 protected file이 아니므로 규정상 수정 자체가 금지되지는 않는다.
> 그러나 이 task의 변경은 **AGENTS.md의 즉시 escalation gate(안전 계약 충돌 · 운영 영향)에
> 해당하므로, 착수 전 Owner의 명시적 승인이 필요하다.** 이 문서가 그 승인을 구하는 근거다.

승인 없이 진행 가능한 부분은 없다 — 이벤트 지점이 전부 이 파일 안에 있어 "안전한 일부만
먼저" 하는 분할이 성립하지 않는다.

## 6. task-0044와의 관계

task-0044 §10 결정 중 **1·2·5·6·7은 그대로 승계**한다(독립 체인 / A+B / code+detail /
무제한+status 보고 / Python). 재협의 대상이 아니다.

- **결정 3**이 미룬 것이 이 task다.
- **결정 4(서명 미부착)** 는 여기서 재검토 대상이다. 서명을 붙이려면 `orchestrator` 역할 키
  발급이 필요하고 이는 task-0042 결정 5(reviewer/qa만 발급)의 확장이다(§9-6).

코어 API는 그대로 쓴다 — `record_owner_approval(...)`, `record_execution_result(...)`가
이미 이 용도로 존재한다(`audit_store.py` 257 / 288). 새 함수를 만들 필요가 없다.

**임포트 주의**: `orchestrator/audit-chain`은 하이픈 때문에 Python 패키지가 될 수 없다.
`bot_minimal.py`에서 쓰려면 형제 디렉터리 관례대로 sys.path에 디렉터리를 넣고 절대 임포트를
해야 한다(task-0044에서 이 문제로 초판 구현이 전혀 실행되지 않았다).

## 7. 검증 계획

- `adapters/discord/bot_minimal.py`의 자체 검사 스위트(`_run_self_check_suite`, 1633)에
  감사 관련 항목 추가 — 이 파일은 이미 자체 검사를 갖고 있다
- 승인 1건 → 체인 길이 1, `verify-chain` valid, payload에 owner user ID **부재** 확인
- 감사 append 실패 주입 시 `/approve`가 **거부**되는지(계약 §4)
- `/run`·`/retry` 각각이 `execution_result` 항목을 남기는지
- 기존 회귀 10종 + audit-chain 6/6 유지
- `check_no_secrets.py --staged`

**금지키 재확인**: `FORBIDDEN_PAYLOAD_KEYS`에 `user_id`/`discord_user_id`/`author_id`가
있고, task-0044에서 이 가드를 키집합 검사보다 앞으로 옮겼다. Discord author_id가 payload에
섞이면 **append가 fail-closed로 거부**된다. 연동 시 이 경로를 실제로 밟는 테스트가 필요하다.

## 8. 이번 단계에서 하지 않는 것

- **구현 일체** — 이 문서는 설계뿐이다
- `jarvis.bat` — protected file
- task-0044 코어 수정 — `116fe2d`을 기준점으로 유지한다
- task-0041 구현
- C~F 대상 확대(Review/QA/Buzz 기록) — task-0044 결정 2가 A+B로 한정했다
- 기존 승인 이력의 소급 기록 — 원본이 없어 재구성 불가능하며 추정을 감사 기록으로 승격하지 않는다

## 9. 미해결 질문 (Owner 결정 필요)

1. 🔴 **감사 append와 상태 전이의 순서**(§4). (i) 감사 먼저 / (ii) 전이 먼저 / (iii) 2단계.
   §2.3의 쓰기 내구성 개선과 묶어서 정해야 한다.
2. 🔴 **§2.3 쓰기 내구성 개선을 이 task에 포함하는가.** `_apply_task_status_transition`을
   `task_file_writer.py` 수준(fsync + `os.replace` + `expected_digest`)으로 올릴 것인가.
   **포함하지 않으면 체인은 장식**이라는 것이 task-0044 §6.3의 판단이다.
3. **실패한 승인 시도도 기록하는가.** `apply_not_ready`, `status_mismatch`,
   `approve_contract_mismatch`, `task_not_found` 등으로 거부된 시도. 기록하면 "누가 무엇을
   시도했는가"까지 남지만 체인이 잡음으로 커진다. 기록하지 않으면 실패한 승인 시도는
   여전히 흔적이 없다.
4. **`result_kind` 매핑 규칙.** 스키마는 `{dry_run, success, failure}`인데 실제 실행 결과는
   `executed`/`success` 두 불리언이다. `executed=False`(화이트리스트 미등록 등)를
   `failure`로 볼 것인가, 별도로 볼 것인가.
5. 🔴 **§2.5의 reject 결함을 이 task에서 고치는가.** 거부가 실행 흐름에 도달하는 것을
   막을 것인가(승인 의미론 변경), 아니면 감사 기록만 붙여 **드러나게만** 할 것인가.
   후자도 유효한 선택이다 — 이 task의 목적은 기록이지 수정이 아니다.
6. **감사 체인에 서명을 붙이는가**(task-0044 결정 4의 재검토). 붙이려면 `orchestrator`
   역할 키 발급이 필요하고 이는 task-0042 결정 5의 확장이다.
7. **감사 실패 시 Owner에게 보이는 메시지.** task-0044 결정 5(B)가 `code`/`detail`
   2계층을 정했으므로 어휘는 있다. 남은 것은 `/approve` 거부 사유로 **어느 code까지**
   노출할지다. P2-4는 인가 실패를 `unauthorized` 하나로 일반화했다.

## 10. 다음 단계

1. Owner가 §5.4의 착수 승인 여부를 결정한다 — **이것 없이는 §9의 나머지도 의미가 없다**
2. 승인되면 §9의 7건을 결정한다(1·2·5가 서로 얽혀 있으므로 함께)
3. 결정을 이 문서 §10에 정본으로 기록한다(task-0042/0044와 같은 형식)
4. 구현 → 검증 → 커밋
