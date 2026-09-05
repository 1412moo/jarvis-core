# task-0052 승인 경로 ↔ 감사 해시체인 연동 설계

- task: `task-0052-audit-chain-approval-integration`
- 선행: `task-0044`(감사 해시체인 코어, commit `116fe2d`)
- 상태: **설계 확정. 구현 없음.** Owner 결정 7건 승인 완료(§10). **구현 착수는 여전히 Owner 승인 대상**(§5.4)
- 작성: 2026-09-05 / 결정 반영: 2026-09-05

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
| `execution_result.result_kind` | `execution_result.executed/success`에서 파생 | ⚠ 매핑 규칙 필요(§9.4) |

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

**결정 ⑤-b로 이 결함을 이번 task에서 고치기로 확정됐다**(§9.5) — `reject`가
`_run_execution_flow()`에 진입하지 않게 하는 최소 차단이다. 승인 의미론을 바꾸는 일이므로
감사 연동과 **구분해** 기술한다(§10.2).

이 사례는 **왜 감사 체인이 필요한지**를 가장 선명하게 보여준다 — 지금은 이런 일이 일어나도
남는 기록이 없다.

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

### 3.3 감사 외 범위 — `reject` 실행 차단 (결정 ⑤-b)

결정 ⑤-b에 따라 **`/approve <id> reject`가 `_run_execution_flow()`에 진입하지 않게 하는
최소 수정**이 이번 task 범위에 포함된다. 이는 감사 연동이 아니라 **의미론 버그 수정**이며,
같은 승인 경로에서 실제 실행을 방지하기 위해 함께 처리한다(§9.5, §10.2).

`_build_execution_candidate`에 전역 status 게이트를 두는 ⑤-c는 **범위 밖**이다 —
`/run`·`/retry` 동작까지 바꾼다.

## 4. 실패 처리 계약과 순서 문제

task-0044 §6.1이 정한 계약은 **감사 기록 실패 = 작업 실패**다. 그런데 연동 시점에
순서 문제가 생긴다. 전이(쓰기 ①)와 감사 append는 서로 다른 파일에 대한 두 번의 쓰기다.

순서 후보는 셋이다 — (i) 감사 먼저 → 전이, (ii) 전이 먼저 → 감사, (iii) 2단계(의도 기록 →
전이 → 확정 기록). 어느 것을 골라도 **한쪽만 성공하는 조합이 반드시 남는다.**

`owner_approval` 스키마에 **`applied: bool`이 이미 있다**는 점이 중요하다 — 전이가 실패해도
`applied: false`로 정직하게 기록할 수 있다. 다만 그러려면 전이 결과를 안 상태에서 기록해야
하므로 실질은 (ii)에 가깝다.

**세 순서의 전체 failure matrix와 권장안은 §9.1에 있다.** 여기서 표를 중복하지 않는다 —
두 벌을 두면 갈라진다. §2.3의 쓰기 내구성(§9.2)과 묶어서 정해야 하며, atomic replace가
있으면 (ii)의 잔여 위험이 크게 줄어든다.

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
3. **§2.5를 함께 고친다** — 결정 ⑤-b로 확정됐다. "거부가 실행을 유발하는가"라는
   **승인 의미론 변경**이므로, 감사 연동과 별개로 그 자체가 Owner 승인 사항이다.
   이 항목이 확정되면서 이 task는 기록 추가에 그치지 않고 **동작을 바꾸는 변경**이 됐다 —
   착수 승인의 필요성이 더 분명해진 것이지 약해진 것이 아니다.

### 5.4 결론

> `bot_minimal.py`는 **protected file이 아니다** — 운영 규칙 §6이 명시하는 protected file은
> `jarvis.bat` 하나뿐이므로, 규정을 근거로 수정 자체가 금지되지는 않는다.
>
> **그러나 구현 착수 전 Owner의 명시적 승인이 필요하다.** 이 파일에는 **P2-4가 세운 Owner
> 인가 게이트**(`PRIVILEGED_COMMANDS` / `_authorize_command` / `_load_owner_ids`)가 들어
> 있고 이 task는 그 게이트가 감싸는 경로의 실패 계약을 바꾸며(안전 계약 충돌), 감사 append
> 실패가 `/approve`를 거부하게 되므로 **운영 영향**이 있다. 둘 다 AGENTS.md의 budget과
> 무관한 즉시 escalation gate에 해당한다. 이 문서가 그 승인을 구하는 근거다.

승인 없이 진행 가능한 부분은 없다 — 이벤트 지점이 전부 이 파일 안에 있어 "안전한 일부만
먼저" 하는 분할이 성립하지 않는다.

## 6. task-0044와의 관계

task-0044 §10 결정 중 **1·2·5·6·7은 그대로 승계**한다(독립 체인 / A+B / code+detail /
무제한+status 보고 / Python). 재협의 대상이 아니다.

- **결정 3**이 미룬 것이 이 task다.
- **결정 4(서명 미부착)** 는 여기서 재검토 대상이다. 서명을 붙이려면 `orchestrator` 역할 키
  발급이 필요하고 이는 task-0042 결정 5(reviewer/qa만 발급)의 확장이다(§9.6).

코어 API는 그대로 쓴다 — `record_owner_approval(...)`, `record_execution_result(...)`가
이미 이 용도로 존재한다(`audit_store.py` 257 / 288). 새 함수를 만들 필요가 없다.

**임포트 주의**: `orchestrator/audit-chain`은 하이픈 때문에 Python 패키지가 될 수 없다.
`bot_minimal.py`에서 쓰려면 형제 디렉터리 관례대로 sys.path에 디렉터리를 넣고 절대 임포트를
해야 한다(task-0044에서 이 문제로 초판 구현이 전혀 실행되지 않았다).

## 7. 검증 계획

- `adapters/discord/bot_minimal.py`의 자체 검사 스위트(`_run_self_check_suite`, 1633)에
  감사 관련 항목 추가 — 이 파일은 이미 자체 검사를 갖고 있다
- 승인 1건 → 체인 길이 1, `verify-chain` valid, payload에 owner user ID **부재** 확인
- 감사 append 실패 주입 시 `/approve`가 **거부**되는지, 그리고 응답에 **stable code만**
  나가고 `detail`이 새지 않는지(결정 ①·⑦)
- append 실패 후 재시도가 `status_mismatch`로 막히는지 — 중복 기록 방지의 실증(§10.1)
- 실패한 승인 시도가 `applied:false` + reason으로 기록되는지(결정 ③)
- **`/approve <id> reject`가 서브프로세스를 실행하지 않는지**(결정 ⑤-b) — 화이트리스트에
  걸리는 task로 수정 전 동작(실행됨)과 수정 후 동작(미실행)을 대조한다
- reject 시 `execution_result` 항목이 **생기지 않는지**
- `/run`·`/retry` 각각이 `execution_result` 항목을 남기는지
- `transition_task_file_status` 재사용 후 승인 경로 전이 3쌍이 실제로 통과하는지(결정 ②)
- `_validate_approve_transition_contract_sync()`가 두 모듈의 전이 표 드리프트를 잡는지
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
- **⑤-c 전역 status 게이트** — `/run`·`/retry` 동작까지 바꾸므로 별도 task(결정 ⑤)
- **불일치 탐지 도구** — "`DOING`인데 승인 기록이 없는 task" 조회. 필요성은 §9.1이 인정하나 이번 범위 밖
- **수동 복구 명령** — append 실패 후 고착 해제는 Owner의 수동 편집으로 남는다(§10.1의 알려진 공백)
- **전이 쌍 확정 전 실패의 기록** — 스키마상 표현 불가(§9.3). 담으려면 task-0044 결정 2 재개방이 필요하다
- 서명 부착 — 결정 ⑥
- **실행결과 전이의 내구성 개선** — writer의 metadata 검증과 비호환이라 §10.3이 범위에서 뺐다.
  해소하려면 `_write_execution_review_metadata`의 형식을 writer 스키마에 맞추는 별도 task가 필요하다
- **`task_file_writer` metadata 검증 완화** — 명시적으로 금지(§10.3)

## 9. Owner 결정 (7건) — 선택지와 확정 근거

**7건 모두 2026-09-05에 확정됐다.** 정본 요약은 §10에 있고, 이 절은 각 결정의 선택지와
확정 근거, 구현 시 따라오는 제약을 남긴다. 선택되지 않은 안도 지운다 — **왜 그것이 아닌지가
나중에 같은 논의를 반복하지 않게 한다.**

①②⑤는 서로 얽혀 있다. ②(내구성)가 ①(순서)의 잔여 위험을 줄이고, ⑤(reject 차단)는 ①이
무엇을 기록하게 되는지를 바꾼다.

### 9.1 결정 ① — 감사 append와 상태 전이의 순서 → **(ii-b) 확정**

전이(`T`, task 파일)와 감사 append(`A`, 체인 파일)는 **서로 다른 파일에 대한 두 번의 쓰기**다.
둘 사이에 원자성이 없으므로 한쪽만 성공하는 조합이 반드시 존재한다.

#### (i) 감사 먼저 → 전이 — **배제**

| `A` | `T` | 실제 task 파일 | 체인이 주장하는 것 | 판정 |
| --- | --- | --- | --- | --- |
| 실패 | 미실행 | 변화 없음 | 없음 | ✅ 승인 거부. 아무 일도 일어나지 않음 |
| 성공 | 성공 | 전이됨 | 전이됨 | ✅ 일치 |
| 성공 | **실패** | **변화 없음** | **전이됨** | 🔴 **체인이 허위를 기록** |

체인은 **append-only여서 지울 수 없고**, 보상 항목을 덧붙이는 것도 그 append가 또 실패할 수
있다. "기록이 없을 수 있다"는 복구 가능한 결함이지만 **"기록이 거짓일 수 있다"는 복구
불가능하다.** 배제한다.

#### (ii) 전이 먼저 → 감사 — **채택**

| `T` | `A` | 실제 task 파일 | 체인이 주장하는 것 | 판정 |
| --- | --- | --- | --- | --- |
| 실패 | 미실행 | 변화 없음 | 없음 | ✅ 안전. 실패 시도로 기록(§9.3) |
| 성공 | 성공 | 전이됨 | 전이됨 | ✅ 일치 |
| 성공 | **실패** | **전이됨** | **없음** | ⚠ 기록 누락. 아래 운영 계약으로 처리 |

- **(ii-a) 롤백 시도** — 배제. 롤백 자체가 실패할 수 있고, 그 사이 다른 프로세스가 이미
  읽었을 수 있으며, **롤백에 성공해도 그 사실 역시 기록되지 않는다.**
- **(ii-b) 롤백 없이 실패 보고** — **채택.**

#### (iii) 2단계(의도 → 전이 → 확정) — 배제

계약상 가장 정직하지만 `owner_approval` 스키마에 **두 항목을 짝지을 필드가 없다.**
`task_id`는 여러 승인에 재사용되고 `entry_id`는 항목마다 다르다. 짝짓기를 하려면 스키마에
상관 필드를 추가해야 하고 이는 **task-0044 결정 2의 재개방**이다. 항목 수와 `seq` 소비도
2배가 된다.

#### (ii-b) 운영 계약 — 감사 실패를 조용히 삼키지 않는다

`T` 성공 / `A` 실패 조합에서 지켜야 할 것을 명시한다.

| 항목 | 계약 |
| --- | --- |
| **응답** | `/approve`는 **반드시 실패로 답한다.** 성공으로 보고하지 않고, 무응답으로 삼키지 않는다. 사유는 Q7에 따라 **stable code만** 노출하고 `detail`은 로컬 로그에만 남긴다 |
| **고착 상태** | task 파일은 `DOING`, 체인에는 기록 없음. 이 불일치가 **의도된 가시적 상태**다 |
| **재시도** | `/approve <id> approve` 재실행은 `_validate_approve_transition`이 `NEEDS_APPROVAL→DOING`만 허용하므로 현재 `DOING`에서는 `status_mismatch`로 거부된다. **자동 재시도는 구조적으로 불가능하다** — 이는 결함이 아니라 이중 실행과 중복 기록을 막는 안전장치다 |
| **복구** | Owner의 수동 개입만이 경로다. task 파일 `status`를 `NEEDS_APPROVAL`로 되돌린 뒤 재승인한다. **이 수동 편집 자체는 체인에 남지 않는다** — 알려진 공백이며 §8의 비범위다 |
| **중복 방지** | 정상 경로에서 같은 전이가 두 번 기록될 수 없다(재시도가 위와 같이 막히므로). Owner가 수동 복구 후 재승인해 두 번째 항목이 생기는 경우, 그것은 **실제로 두 번 일어난 승인 행위**이므로 중복이 아니라 정확한 기록이다. 체인은 두 시도를 모두 보여준다 |
| **탐지** | `status`가 `DOING`인데 `owner_approval` 기록이 없는 task가 불일치 신호다. **탐지 도구는 이번 task에서 만들지 않는다**(§8) |

**잔여 위험은 결정 ②로 줄어든다.** `transition_task_file_status`의 atomic replace가 들어가면
`T`의 실패 자체가 드물어지고, 남는 창은 "쓰기는 성공했는데 append가 실패한" 좁은 구간뿐이다.

#### E2(실행 결과)의 비대칭 — 되돌릴 수 없다

E1(승인)은 전이만 남기므로 (ii-b)의 "작업 실패로 보고" 가 성립한다. **그러나 E2 지점에서는
서브프로세스가 이미 실행된 뒤다.** 감사 append가 실패해도 실행을 되돌릴 수 없다.

따라서 E2에서 계약은 "작업 실패"가 아니라 **"크게 보고하고 체인에 구멍이 있음을 알린다"** 로
축소된다. 실행 사실 자체는 task 파일의 실행 메타데이터(쓰기 ②)에 남으므로 완전한 유실은
아니다. **이 비대칭을 문서에 남기지 않으면 "왜 E2는 롤백하지 않는가"라는 질문이 반복된다.**

### 9.2 결정 ② — 상태 파일 내구성 개선 범위 → **(d) 채택, 단 범위 축소(2026-09-05 재결정)**

현재 `_apply_task_status_transition`(796)의 쓰기는 `task_file.write_text(...)` 한 줄이다.
fsync도, atomic replace도, `expected_digest`도 없다.

**실측 사실 두 가지.**

- `orchestrator/discord-intake/task_file_writer.py`에 **상태 전이 전용 내구성 함수**
  `transition_task_file_status(...)`(524)가 이미 있다. `expected_digest` 인자, `os.replace`(521),
  `os.fsync`를 갖췄고 테스트용 주입 seam(`_open_temp_file`/`_replace_file`/`_fsync_file`)까지 있다.
- `bot_minimal.py`는 **이미 이 모듈을 임포트하고 있다**(46행, `write_task_file`만).

| 선택지 | 판정 |
| --- | --- |
| (a) 범위 밖 — 현행 유지 | ❌ 체인이 찢어질 수 있는 쓰기 위에 놓인다. task-0044 §6.3의 "체인은 장식" 상태 |
| (b) fsync + `os.replace`만 자체 추가 | ❌ read-then-write 경합 창이 남아 "깨진 건지 공격인지" 여전히 구분 못 함 |
| (c) (b) + `expected_digest` 자체 구현 | ❌ **내구성 원시코드를 두 벌 갖게 된다.** 갈라지는 순간 어느 쪽이 진실인지 알 수 없다 |
| **(d) `transition_task_file_status` 재사용** | ✅ **채택.** 별도 내구성 구현은 만들지 않는다 |

#### 🔴 초판 §9.2의 두 가지 오류 (구현 착수 후 발견, 2026-09-05)

이 절의 초판은 아래 두 가지를 **틀리게** 적었고, Owner 결정 ②는 그 틀린 근거 위에서
내려졌다. 정정해 기록한다.

**오류 1 — 전이는 3쌍이 아니라 4쌍이다.**
초판은 "`FAILED→TODO`는 이 경로들이 안 쓰므로 추가하지 않는다(최소 확장)"고 했다.
**틀렸다.** `_run_retry`(1054)가 재실행 전 준비 단계로 `FAILED→TODO`를 수행한다. 이 누락
때문에 첫 구현에서 retry 계열 self-check가 실패했다.

**오류 2 — "추가일 뿐 완화가 아니다"는 실행결과 전이에 대해 성립하지 않는다.**
초판은 전이 표 확장이 "추가(additive)이지 완화가 아니며 제거되는 제약이 없다"고 했다.
**승인 전이에 대해서는 맞지만 실행결과 전이에 대해서는 틀렸다.**

`transition_task_file_status`는 전이 전에 `_transition_metadata`로 파일 전체를 검증하고,
**허용 목록에 없는 메타데이터 필드가 하나라도 있으면 거부한다**(`task_file_unsupported_metadata`).
그런데 `_write_execution_review_metadata`(852)가 **두 전이 사이에** 실행 메타데이터를 쓴다.

```text
승인 전이 NEEDS_APPROVAL→DOING     ← 파일이 깨끗해 통과
  → 실행 → _write_execution_review_metadata   ← 13개 필드 기록
  → 실행결과 전이 DOING→DONE        ← 거부됨
```

실측 대조:

| 비호환 | 내용 |
| --- | --- |
| 미허용 필드 5개 | `error`, `mode`, `reason`, `message`, `execution_status` — writer의 `TASK_ALLOWED_METADATA`에 없다 |
| 타입 불일치 | `execution_candidate`를 writer는 **boolean**으로 분류하는데 bot_minimal은 **JSON**을 쓴다 |
| 빈 값 거부 | `error`/`reason`은 빈 문자열로 기록되는데 writer의 text 검증은 `allow_empty=False` |
| 길이 상한 | writer text 필드 상한 **500자**, `execution_result` 실측 **419자** — 오늘은 통과하나 여유가 거의 없다 |

실행결과 전이까지 (d)를 적용하려면 **필드 추가 · 타입 재분류 · 빈 값 허용 · 길이 상향**의
네 가지 완화가 필요하다. 이는 다른 모듈이 소유한 task 파일 검증기를 **실질적으로 약화**시키는
일이며, 초판이 내세운 "제거되는 제약이 없다"는 근거와 정면으로 어긋난다.

이 발견은 **승인 경로가 애초에 왜 이 writer를 쓰지 않았는지**도 설명한다.

#### 재결정 — 범위 축소 (Owner 승인, 2026-09-05)

| 전이 | writer | 근거 |
| --- | --- | --- |
| `NEEDS_APPROVAL→DOING` | ✅ **durable** | 감사 체인이 놓이는 토대. §2.3이 지목한 지점이다 |
| `NEEDS_APPROVAL→FAILED` | ✅ **durable** | 위와 같음 |
| `DOING→DONE` | ⬜ 현행 유지 | 실행 메타데이터 기록 뒤라 writer 스키마와 비호환 |
| `DOING→FAILED` | ⬜ 현행 유지 | 위와 같음 |
| `FAILED→TODO`(retry 준비) | ⬜ 현행 유지 | 이전 실행 메타데이터가 이미 파일에 있어 같은 이유 |
| `TODO→DOING`(retry 준비) | ⬜ 현행 유지 | 위와 같음 |

**`task_file_writer`의 기존 metadata 검증은 완화하지 않는다** — 필드 추가, 타입 재분류,
빈 문자열 허용 확대, 길이 제한 완화를 모두 하지 않는다(Owner 재결정 4항).

실행결과 전이는 여전히 `write_text()` 위에 남는다. **이것은 알려진 잔여 위험이며**, 해소하려면
`_write_execution_review_metadata`의 메타데이터 형식을 writer 스키마에 맞추는 별도 task가
필요하다(§8).

#### 구현 시 동반해야 하는 변경

| # | 변경 | 이유 |
| --- | --- | --- |
| 1 | `task_file_writer.TASK_STATUS_TRANSITIONS`에 **4쌍 추가** — `NEEDS_APPROVAL→DOING`, `NEEDS_APPROVAL→FAILED`, `DOING→FAILED`, `FAILED→TODO` | 현재 표는 `TODO→DOING`, `DOING→DONE` 2쌍뿐이다. durable 경로가 실제로 쓰는 것은 앞의 2쌍이지만, 표를 승인 경로 전체의 상위집합으로 유지해 2번 검사가 의미를 갖게 한다 |
| 2 | `_validate_approve_transition_contract_sync()`(775) 확장 | 현재 이 검사는 `bot_minimal` 내부 표만 대조하고 **`task_file_writer` 쪽 표는 보지 않는다.** 두 표가 조용히 갈라진 것이 오류 1의 원인이다. writer의 전이 표가 `ALLOWED_STATUS_TRANSITIONS`의 **상위집합인지** 검사에 포함한다 |
| 3 | `expected_digest` 산출 지점 | read 시점의 digest를 계산해 전달한다 |
| 4 | 반환 타입 매핑 | `TaskStatusTransitionResult(result_type, reason)` → 기존 `(bool, str)` 시그니처로 변환. `"updated"`→성공, `"stale"`→`status_mismatch`, 나머지→`write_failed`. **호출부 계약과 사유 어휘를 바꾸지 않는다** |
| 5 | 전이 쌍에 따른 분기 | `_apply_task_status_transition`이 승인 전이 2쌍에만 durable writer를 쓰고 나머지는 기존 경로를 탄다. **분기 이유를 코드 주석에 남긴다** — 그러지 않으면 다음 사람이 "왜 반만 쓰지"라고 묻는다 |

`planned_updated_at` 형식은 양쪽 모두 `%Y-%m-%d %H:%M UTC`로 **이미 일치**함을 확인했다.

### 9.3 결정 ③ — 실패한 승인 시도도 기록한다 → **확정**

승인 게이트가 자산이라면 **거부된 시도야말로 남겨야 할 증거**다. 넓게 시작해 좁히는 것은
가능하지만 그 반대는 소급 복구가 불가능하다.

#### 성공/실패의 구분

| | `applied` | `reason` | 기록 시점 |
| --- | --- | --- | --- |
| **성공** | `true` | `""` | `_apply_task_status_transition`이 성공을 반환한 **직후** |
| **실패** | `false` | 거부 사유의 stable code | 거부가 확정된 **직후**, 응답을 반환하기 전 |

`owner_approval` 스키마의 `applied: bool`이 이미 이 구분을 담는다 — **스키마 변경이 필요 없다.**

#### 🔴 기록 가능 범위의 경계 (스키마 제약)

`owner_approval` payload는 `transition{from,to}`를 요구하고 두 값이 모두
`ALLOWED_STATUSES`에 있어야 한다. 따라서 **전이 쌍이 확정되기 전에 발생하는 실패는 현재
스키마로 표현할 수 없다.**

| 실패 | 기록 | 사유 |
| --- | --- | --- |
| `_apply_task_status_transition` 실패(`task_not_found`, `status_mismatch`, `write_failed`) | ✅ 기록 | 전이 쌍이 확정된 뒤다 |
| `apply_not_ready`(hold) | ✅ 기록 | 전이 쌍 확정 뒤다 |
| `_validate_approve_transition` 실패 | ❌ 불가 | 전이 쌍이 **유효하지 않아** payload를 만들 수 없다 |
| `invalid_writer_input`, `approve_contract_mismatch` | ❌ 불가 | 같은 이유 |
| `/approve` 파싱 실패(`usage:...`) | ❌ 불가 | `decision`·전이 쌍이 아직 없다 |

**이번 task는 기록 가능한 범위만 기록한다.** 나머지를 담으려면 스키마 확장이 필요한데,
그것은 task-0044 결정 2의 재개방이자 결정 ④가 정한 "새 vocabulary를 임의로 만들지 않는다"에
어긋난다. **기록 불가 범위가 있다는 사실 자체를 문서와 task 기록에 남긴다**(원칙 8).

### 9.4 결정 ④ — `result_kind`는 기존 `failure`를 쓴다 → **확정**

새 vocabulary를 만들지 않는다. 세부 구분은 **이미 존재하는 stable reason code**로 표현한다.

| `executed` | `success` | 사례 | `result_kind` | `execution_status_transition_reason` |
| --- | --- | --- | --- | --- |
| `true` | `true` | 스크립트 exit 0 | `success` | `""` |
| `true` | `false` | exit≠0, timeout | `failure` | `""` (전이는 `FAILED`로 적용됨) |
| `false` | `false` | 화이트리스트 미등록, `execution_type_not_allowed`, `execution_start_failed` | `failure` | **`execution_not_executed`** |

**핵심**: `_apply_execution_result_status_transition`(1205)이 이미
`execution_not_executed`를 반환하므로, **"정책이 막았다"와 "실행했는데 실패했다"는 기존
어휘만으로 구분된다.** 새 값을 만들 필요가 없다.

- 기존 reason 어휘를 그대로 채택한다 — `execution_result_missing`,
  `execution_not_executed`, `execution_executed_not_boolean`,
  `execution_success_not_boolean`, `transition_not_applied`.
- `transition_not_applied:{reason}`처럼 **값을 싣는 형태는 payload에 넣지 않는다.**
  task-0044 결정 5의 code/detail 원칙에 따라 **code 부분만** 넣는다(결정 ⑦과 일관).
- `dry_run`은 `_build_execution_result_dry_run` 전용이므로 이 자리에 쓰지 않는다.

**잃는 것**: 실행 거부의 *구체적* 사유(화이트리스트 미등록 / 타입 불허 / 시작 실패)는
체인에 남지 않고 task 파일 실행 메타데이터에만 남는다. 이는 새 필드를 만들지 않기로 한
결정의 대가이며, 필요해지면 그때 별도 결정으로 넓힌다.

### 9.5 결정 ⑤ — `reject`의 실행 흐름 진입을 차단한다 → **(⑤-b) 확정**

#### 수정 전 (현재, `116fe2d`)

```text
/approve task-XXXX-... reject
 → _build_approve_draft(709)           decision=reject → transition_to="FAILED", apply_ready=True
 → _apply_task_status_transition       NEEDS_APPROVAL → FAILED        ✅ 적용됨
 → _run_execution_flow(1291)           ← decision을 보지 않고 무조건 호출
    → _build_execution_candidate(920)  ← status를 보지 않고 title/summary 키워드만 확인
    → _build_execution_result_real(1137)
       → (action,target)이 EXECUTION_SCRIPT_WHITELIST(117)에 있으면  subprocess.run 실행  ⚠
    → _apply_execution_result_status_transition(1205)
       → _apply_task_status_transition(DOING → …) 요구, 현재 status는 FAILED
       → status_mismatch 로 조용히 실패
```

**결과: 실행은 일어났고, 상태 전이는 안 됐고, 아무 기록도 남지 않는다.**

#### 수정 후 (⑤-b)

```text
/approve task-XXXX-... reject
 → _build_approve_draft                decision=reject → transition_to="FAILED"
 → _apply_task_status_transition        NEEDS_APPROVAL → FAILED        ✅ 적용됨
 → decision == "reject" → _run_execution_flow 를 호출하지 않는다     ⛔ 차단
 → owner_approval(decision=reject, applied=true) 1건 기록
```

`execution_result` 항목은 생기지 않는다 — **실행이 일어나지 않았으므로 기록할 실행 결과가
없다.** 체인에는 거부 사실만 남는다.

| | 선택지 | 판정 |
| --- | --- | --- |
| ⑤-a | 기록만 붙이고 동작은 유지 | ❌ 결함을 알면서 실행을 계속 허용한다 |
| **⑤-b** | **거부 시 실행 흐름 차단 (최소 범위)** | ✅ **확정** |
| ⑤-c | `_build_execution_candidate`에 전역 status 게이트 | ❌ **이번 task에서 하지 않는다.** `/run`·`/retry`에도 적용돼 `NEEDS_APPROVAL` task에 대한 `/run` 동작까지 바뀐다 — 범위를 명백히 넘는다 |

#### 🔑 ⑤-b가 최소 범위인 이유 — 감사 연동과 전제를 공유한다

`_build_approve_writer_result`(1225)는 현재 **`decision`도 `command`도 받지 않는다.**
`_build_approve_writer_input`(732)이 `draft_type`/`task_id`/`proposed_transition`/
`apply_ready`/`hold_reason`만 전달하기 때문이다.

그런데 `owner_approval` payload는 **`command`와 `decision`을 필수 필드로 요구한다.** 즉
감사 연동만으로도 두 값을 writer 단계까지 전달해야 한다. **그 배선이 들어가고 나면 ⑤-b는
`decision == "reject"` 한 줄 검사로 끝난다.**

두 변경이 같은 전제를 공유하므로, ⑤-b를 이번 task에 포함하는 것이 오히려 배선을 두 번
하지 않는 길이다.

`transition_to == "FAILED"`로 추론하는 방법도 있으나 **채택하지 않는다.** 감사 payload가
어차피 `decision`을 요구하므로 명시적 전달이 정직하고, 추론은 나중에 전이 표가 바뀌면
조용히 깨진다.

#### 성격 명시

이 수정은 **감사 연동과는 별개의 의미론 버그 수정**이다. 같은 승인 경로에서 실제 실행을
방지하기 위해 이번 task에 포함하되, 커밋 메시지와 task 기록에서 **감사 연동과 구분해
기술한다** — 나중에 문제가 생겼을 때 어느 쪽이 원인인지 가려낼 수 있어야 한다.

### 9.6 결정 ⑥ — 서명은 이번 task에서 부착하지 않는다 → **확정**

task-0044 결정 4를 그대로 유지한다. 부착하려면 `orchestrator` 역할 키 발급이 필요하고
이는 **task-0042 결정 5**(reviewer/qa만 발급)의 확장이라 별도 승인 사안이다. 체인 자체가
이미 변조 탐지를 제공하고, 이 단계에서 기록 주체는 여전히 하나(봇 프로세스)이므로 서명이
추가할 "누가 썼는가"의 실익이 낮다.

### 9.7 결정 ⑦ — 외부 노출은 stable code만 → **확정**

task-0044 결정 5(B)의 `code`/`detail` 2계층을 승인 경로 응답까지 그대로 연장한다.

| 계층 | 내용 | 노출 |
| --- | --- | --- |
| `code` | 값을 담지 않는 고정 어휘 | `/approve` 실패 응답에 **노출한다** |
| `detail` | 경로·해시·OS 오류 | **로컬 진단용.** Discord 메시지로 내보내지 않는다 |

단일 일반화(`audit_write_failed` 하나)는 배제한다 — P2-4의 `unauthorized`는 **적대적
상대에게 판별 정보를 주지 않으려는 것**이지만, 감사 실패는 **Owner 자신이 조사해야 하는
내부 사건**이다. `code`는 설계상 값을 담지 않으므로 노출해도 유출이 없다.

## 10. Owner 결정 (2026-09-05 승인)

§9의 7건은 모두 결정되었다. 아래가 확정된 계약이다.

| # | 질문 | 결정 | 반영 위치 |
| --- | --- | --- | --- |
| 1 | append와 전이의 순서 | **(ii-b) 전이 먼저 → 감사. append 실패 시 롤백하지 않는다.** 고착·복구·재시도·중복 방지 정책을 명시하고 **감사 실패를 조용히 삼키지 않는다** | §9.1 |
| 2 | 상태 파일 내구성 | **(d) `transition_task_file_status()` 재사용, 단 승인 전이에만**(2026-09-05 범위 축소 재결정). 전이 표에 **4쌍** 추가, `_validate_approve_transition_contract_sync()` 갱신, **별도 내구성 구현을 만들지 않고 writer의 metadata 검증도 완화하지 않는다** | §9.2, §10.3 |
| 3 | 실패한 승인 시도 | **기록한다.** 성공/실패 구분(`applied`)과 기록 시점을 명시. 스키마상 기록 불가한 조기 실패 범위도 명시 | §9.3 |
| 4 | `result_kind` | **기존 `failure`를 사용**하고 세부 구분은 stable reason code로 표현. **새 vocabulary를 임의로 만들지 않는다** | §9.4 |
| 5 | `reject`의 실행 진입 | **(⑤-b) 최소 범위로 차단.** `_run_execution_flow()`에 진입하지 않게 한다. 전역 status gate(⑤-c)는 이번 task에서 하지 않는다 | §9.5, §10.2 |
| 6 | 감사 체인 서명 | **부착하지 않는다**(task-0044 결정 4 유지) | §9.6 |
| 7 | 실패 사유 노출 | **stable code만 외부 노출**, `detail`은 내부 진단용 | §9.7 |

### 10.1 결정 1의 운영 계약 요약

`T` 성공 / `A` 실패에서 — `/approve`는 **실패로 답하고**(성공으로 보고하지 않는다), task는
`DOING`으로 고착되며, 자동 재시도는 `status_mismatch`로 **구조적으로 막힌다**(이중 실행·중복
기록 방지). 복구는 Owner의 수동 개입뿐이고 **그 수동 편집은 체인에 남지 않는다**(알려진 공백).
정상 경로에서 같은 전이가 두 번 기록되는 일은 없으며, 수동 복구 후 재승인으로 생기는 두 번째
항목은 **실제로 두 번 일어난 승인**이므로 정확한 기록이다.

E2(실행 결과)는 서브프로세스가 이미 돈 뒤라 되돌릴 수 없으므로, 계약이 "작업 실패"가 아니라
**"크게 보고한다"** 로 축소된다(§9.1 말미).

### 10.2 결정 5의 성격 — 감사 연동과 구분해 기술한다

⑤-b는 **감사 연동이 아니라 의미론 버그 수정**이다. 동일한 승인 경로에서 실제 실행을
방지하기 위해 이번 task에 포함하지만, 커밋 메시지·task 기록에서 두 변경을 **구분해 적는다.**
문제가 생겼을 때 감사 훅이 원인인지 실행 차단이 원인인지 가려낼 수 있어야 한다.

포함이 정당한 실무적 근거는 §9.5에 있다 — `owner_approval` payload가 `command`와 `decision`을
필수로 요구하므로 그 배선은 감사 연동만으로도 필요하고, **배선이 들어간 뒤 ⑤-b는 한 줄
검사로 끝난다.**

### 10.3 결정 2의 범위 축소 (2026-09-05 재결정)

구현 착수 후 초판 §9.2의 근거 두 가지가 **틀린 것으로 확인**되어 Owner가 범위를 축소했다.

1. **"전이 3쌍"이 틀렸다.** `_run_retry`(1054)가 `FAILED→TODO`를 쓴다 → **4쌍**으로 정정.
2. **"추가일 뿐 완화가 아니다"가 실행결과 전이에 대해 틀렸다.** `transition_task_file_status`는
   허용 목록 밖 metadata 필드를 거부하는데, `_write_execution_review_metadata`가 두 전이
   사이에 쓰는 13개 필드 중 **5개가 미허용**이고, `execution_candidate`는 **타입이 어긋나며**,
   `error`/`reason`은 **빈 값**이고, text 상한 **500자**에 `execution_result`가 419자로 붙는다.
   적용하려면 검증기를 네 군데 완화해야 한다.

**확정된 축소**:

| 항목 | 결정 |
| --- | --- |
| 승인 전이(`NEEDS_APPROVAL→DOING`/`FAILED`) | durable writer 재사용 |
| 실행결과 전이(`DOING→DONE`/`FAILED`) | **이번 task에서 durable writer를 적용하지 않는다.** 현행 경로 유지 |
| retry 준비 전이(`FAILED→TODO`, `TODO→DOING`) | 현행 경로 유지(같은 비호환) |
| `task_file_writer` metadata 검증 | **완화하지 않는다** — 필드 추가·타입 재분류·빈 문자열 허용·길이 완화 모두 금지 |
| 전이 표 | **4쌍 추가**(표를 승인 경로의 상위집합으로 유지해 드리프트 검사가 의미를 갖게 한다) |

실행결과 전이가 `write_text()` 위에 남는 것은 **알려진 잔여 위험**이다. 해소하려면
`_write_execution_review_metadata`의 형식을 writer 스키마에 맞추는 별도 task가 필요하다.

### 10.4 이 결정들이 바꾸지 않는 것

task-0044 §10의 결정 1·2·5·6·7(독립 체인 / A+B / code+detail / 무제한+status 보고 / Python)은
**그대로 승계**한다. 재협의 대상이 아니다.

## 11. 다음 단계

§9의 7건은 §10에 정본으로 기록되어 **결정이 끝났다.** 남은 것은 하나다.

1. 🔴 **Owner가 §5.4의 구현 착수 승인 여부를 결정한다.** 결정 ⑤-b가 포함되면서 이 task는
   기록 추가에 그치지 않고 **승인 경로의 동작을 바꾸는 변경**이 됐다. 안전 계약 충돌과
   운영 영향이 모두 해당하므로 이 승인 없이는 구현을 시작하지 않는다.
2. 승인되면 task 기록(`memory/tasks/task-0052-*.md`)을 만들고 구현에 착수한다.
3. 구현 → §7 검증 → 커밋. 커밋 메시지는 **감사 연동과 ⑤-b 버그 수정을 구분해** 기술한다(§10.2).
