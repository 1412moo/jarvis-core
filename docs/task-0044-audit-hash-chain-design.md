# task-0044: 승인·증거 감사 기록 해시체인 설계

[Document Type]
- design (설계만, 구현 없음 — §9)

## 1. 목적/배경

task-0038(Buzz/AI-agent 생태계 조사) Phase 1 항목 5:

> **감사 기록을 해시체인으로 만든다.** 각 승인/증거 기록에 `prev_hash` 포함.
> 🔴 단 Buzz와 달리 **fire-and-forget으로 두지 않는다** — 감사 기록 실패는 작업 실패다.

반면교사는 보고서 §7.2다. Buzz 이벤트 파이프라인의 10~12단계(검색·감사·워크플로)는
fire-and-forget이며 자체 문서가 *"A failure in any of these does not fail the event
submission"*이라고 인정한다. 즉 **감사 로그가 조용히 유실될 수 있다.** 보고서의 방어책은
"승인·증거 기록은 Jarvis 로컬에 반드시 이중 기록, Buzz 감사 로그를 단일 진실로 삼지 마라"다.

task-0044는 "착수 전 설계 문서로 **대상 이벤트 범위**(어떤 승인/증거 기록에 적용할지)를
먼저 합의 필요"를 게이트로 명시했다. 이 문서가 그 게이트를 채우기 위한 것이며,
**이 문서의 완성이 구현 착수를 자동으로 승인하지 않는다.**

## 2. 현재 구조 분석

### 2.1 🔴 가장 중요한 발견 — 체인을 걸 감사 기록이 아직 없다

task-0044의 제목은 "감사 기록을 해시체인으로 **전환**"이지만, 조사 결과 **전환할 대상이
존재하지 않는다.**

- 저장소 전체에서 승인 감사 로그를 검색한 결과 **감사 로그 파일도, 감사 기록 함수도 없다.**
  `audit`로 잡히는 것은 전부 보안 감사 결과를 설명하는 **코드 주석**(`audit CRITICAL#1`
  등)이고 감사 *기록*이 아니다.
- 즉 "누가 무엇을 언제 승인했는가"는 지금 **task 파일의 `status` 한 줄과 git 히스토리로만**
  남는다. `status: DOING`은 승인이 있었다는 사실의 **결과**이지 승인 기록이 아니다.
  누가 승인했는지, 어떤 명령으로 승인했는지, 그때 어떤 증거가 첨부됐는지는 남지 않는다.

**따라서 이 task의 실질은 "기존 기록에 `prev_hash`를 추가"가 아니라 "감사 기록을 처음
만들고, 그것을 체인으로 만든다"이다.** 범위 판단이 달라지므로 §3에서 다시 다룬다.

### 2.2 🔴 두 번째 발견 — 가장 감사가 중요한 경로가 가장 약한 쓰기를 쓴다

task 파일에 쓰는 경로가 **최소 5개** 존재하고, 내구성이 서로 크게 다르다.

| # | 경로 | 원자성/동시성 | 감사 기록 |
| --- | --- | --- | --- |
| 1 | `orchestrator/discord-intake/task_file_writer.py` | `os.link` no-overwrite publish, `os.replace`, `fsync`, **SHA-256 `expected_digest` 낙관적 동시성** | 없음 |
| 2 | `apps/jarvis-console/run_web_app.py` | #1을 import해서 사용(`run_web_app.py:72`) — 같은 보장 | 없음 |
| 3 | 🔴 **`adapters/discord/bot_minimal.py:_apply_task_status_transition`** (836행) | **`task_file.write_text()` 한 줄.** fsync 없음, atomic replace 없음, digest 동시성 검사 없음 | 없음 |
| 4 | `adapters/discord/bot_minimal.py:_write_execution_review_metadata` (914행) | 동일하게 `write_text()` | 없음 |
| 5 | 에이전트의 `.md` 직접 편집 | 없음(도구가 그냥 덮어씀) | 없음 |

**#3이 실제 `/approve` 경로다.** P2-4가 인가 게이트를 세운 바로 그 경로이자, 시스템에서
감사가 가장 중요한 단일 지점인데, 정작 쓰기는 read-modify-write + 평문 `write_text()`다.
#1에 이미 있는 fsync·원자적 publish·`expected_digest` 동시성 검사를 **쓰지 않는다.**

> 참고: `orchestrator/buzz-bridge/lib/task_append.js:appendRunRecord()`는 append-only이고
> taskId별 `wx` 락으로 동시 실행을 막는다(P2-2). 쓰기 경로 중 이것만 append 모델이다.

이것이 설계에 주는 함의는 분명하다. **해시체인은 기록이 순서대로, 빠짐없이, 원자적으로
쌓일 때만 의미가 있다.** #3처럼 중간에 죽으면 파일이 찢어지는 쓰기 위에 체인을 얹으면
체인이 깨진 것인지 공격인지 구분할 수 없어 오히려 신호가 나빠진다. **감사 체인 도입은
승인 경로의 쓰기 내구성 문제와 분리해서 생각할 수 없다.**

### 2.3 재사용할 수 있는 것 (task-0042에서 이미 확보됨)

| 필요한 것 | 기존 자산 | 위치 |
| --- | --- | --- |
| 저장소 밖 append-only 저장소 | `resolve_review_store_paths()` + `manual_delete_only` 보존 정책 | `review_store.py` |
| 원자적 no-overwrite publish | `os.link()` + `O_CREAT\|O_EXCL` + fsync | `review_store.py`, `task_file_writer.py` |
| canonical JSON | `serialize_review_record()` 규칙 (Python) / `lib/canonical.js` (Node, **바이트 동일 확인됨**) | `review_record.py`, `orchestrator/role-signing/` |
| 도메인 분리 해시 | `sha256(prefix + canonical_bytes)` | `change_evidence.py` |
| 상수시간 비교 | `hmac.compare_digest()` / `crypto.timingSafeEqual()` | 양쪽 다 |
| **역할별 Ed25519 서명** | task-0042 구현 완료, 실제 키 발급·왕복 검증 완료 | `orchestrator/role-signing/` |
| 낙관적 동시성 패턴 | `expected_digest` — "마지막으로 읽은 이후 바뀌었으면 거부" | `task_file_writer.py:528` |

**`expected_digest` 패턴은 해시체인의 "마지막 `hash`를 모르면 append 거부"와 정확히 같은
구조다.** 새 메커니즘을 발명할 필요가 없다는 뜻이다.

### 2.4 task-0041과의 중복 — 반드시 먼저 해소해야 한다

`docs/task-0041-append-only-event-log-design.md` §3이 이미 이렇게 적어 두었다.

> `prev_hash`/`hash`: **task-0044(감사 해시체인)가 그대로 재사용할 수 있는 체인 구조를
> 지금 스키마에 넣어둔다. task-0044를 나중에 다시 설계하지 않아도 되게.**

즉 task-0041은 **task 상태 이벤트 로그**(`memory/tasks/events/task-XXXX.jsonl`)에 체인을
이미 설계해 두었다. 그러나:

- task-0041은 **설계만 확정되고 구현되지 않았다**(status `DONE`이지만 "구현 보류 — Owner
  결정"). 코드에 `prev_hash`도 이벤트 로그도 없다.
- task-0041 §7에 **미해결 Owner 결정 5건**이 남아 있다(마이그레이션 범위, `ON_HOLD` 정리,
  API 강제 방법, task-0042와의 순서, 구현 우선순위).
- task-0042 설계는 이 이유로 **"이 설계는 task-0041에 의존해서는 안 된다"**고 명시했고,
  실제로 의존하지 않고 완료됐다.

**따라서 task-0044의 첫 번째 결정은 "무엇에 체인을 거는가"가 아니라 "task-0041과 어떤
관계로 둘 것인가"다.** 이것을 정하지 않고 스키마부터 그리면 체인이 두 개 생긴다.

## 3. 대상 범위 (이 task의 게이트 질문)

### 3.1 후보 대상

현재 저장소에서 "승인·증거"로 분류할 수 있는 사건은 다음과 같다.

| # | 사건 | 현재 기록 방식 | 감사 가치 |
| --- | --- | --- | --- |
| A | **Owner 승인**(`/approve`로 인한 상태 전이) | task 파일 `status` 한 줄 (§2.2 #3) | 🔴 최상 — 승인 권한 행사 그 자체 |
| B | 실행 결과(`/approve`·`/run`·`/retry` → `_run_execution_flow`) | `execution_*` 메타데이터 (§2.2 #4) | 🔴 최상 — `/run`·`/retry`는 `/approve` **없이도** 서브프로세스 실행에 도달한다 |
| C | Buzz run record | `task_append.js` append-only | 중간 — 이미 append-only |
| D | Review 결과(`ReviewRecord`) | `review_store.py` append-only + digest | 중간 — 이미 무결성 있음 |
| E | QA 결과(`jarvis_qa_result`) | task-0042로 스키마·서명 생김 | 중간 |
| F | 역할 서명 봉투(`jarvis_role_signature`) | task-0042, 파일로 존재 | 중간 |
| G | task 상태 전이 일반 | task-0041 설계 대상(미구현) | task-0041 소관 |

### 3.2 권고 — A(+B)로 좁게 시작한다

**A(Owner 승인)를 유일한 1차 대상으로 하고, B(실행 결과)를 같은 체인에 넣는 것을 권고한다.**
근거:

1. **A는 지금 기록이 아예 없다.** D/E/F는 이미 append-only이거나 digest·서명이 붙어 있어
   무결성이 어느 정도 있지만, 승인만 아무 기록도 없다. 가장 큰 공백부터 메우는 것이 맞다.
2. **A는 Jarvis-Core의 핵심 자산이다.** task-0038 §7.1-4가 "승인 게이트를 외부 시스템에
   위임하지 마라. 이것을 넘기는 순간 Jarvis-Core에는 남는 것이 없다"고 했다. 그 승인이
   행사된 기록이 없다는 것은 자산의 증거가 없다는 뜻이다.
3. **B는 A와 같은 체인에 있어야 순서가 증명된다.** 그리고 조사 결과 `_run_execution_flow`는
   승인 경로에서만 불리지 않는다 — `/run`(1091행), `/retry`(1039행),
   `/approve`(1291행) **세 곳**에서 호출된다. 즉 `/run`·`/retry`는 `/approve`를 거치지
   않고 서브프로세스 실행에 도달한다(그래서 P2-4가 이 둘을 `/approve`와 같은 권한군으로
   묶었다). **승인만 기록하면 실행의 3분의 2가 감사에서 빠진다.** B를 포함해야 하는 이유는
   A의 결과여서가 아니라 **A를 우회할 수 있기 때문**이다.
4. **좁게 시작하면 §2.2의 쓰기 내구성 문제를 한 경로에서만 풀면 된다.** 5개 경로를 동시에
   고치는 것은 이 task의 범위를 훨씬 넘는다.

C~F는 **2차 이후**로 미룬다. G는 task-0041 소관이며 §7에서 관계를 정리한다.

## 4. 체인 스키마

### 4.1 레코드

```json
{
  "contract_type": "jarvis_audit_entry",
  "version": "0.1A",
  "seq": 1,
  "entry_id": "audit_<24hex>",
  "kind": "owner_approval" | "execution_result",
  "ts": "YYYY-MM-DDTHH:MM:SSZ",
  "actor": "owner" | "orchestrator",
  "task_id": "task-XXXX-slug",
  "payload": { "...kind별 고정 스키마..." },
  "prev_hash": "<64hex>" | null,
  "hash": "<64hex>"
}
```

- `hash = sha256(b"jarvis-core/audit-chain/v0.1A\0" + canonical_bytes(entry_without_hash))`
  — `change_evidence.py`의 도메인 분리 패턴 그대로. `entry_without_hash`는 `hash` 키를
  제외한 나머지 전체이며 `prev_hash`는 **포함**한다(그래야 체인이 성립한다).
- canonical JSON 규칙은 **새로 만들지 않는다.** `review_record.py:serialize_review_record()`
  규칙을 그대로 쓴다. task-0042에서 Python/Node 바이트 동등성을 실제 레코드로 확인했으므로
  어느 쪽 언어로 구현해도 같은 체인이 나온다.
- `seq`는 1부터 연속. 빠진 번호는 그 자체로 결함이다.
- 제네시스 항목만 `prev_hash: null`.

### 4.2 payload (kind별 고정 스키마)

`owner_approval`:
`{"command": "/approve <task_id> <decision>", "decision": "approve"|"reject", "transition": {"from": "...", "to": "..."}, "applied": true|false, "reason": "<실패 시 코드>"}`

`execution_result`:
`{"source": "approve_file_write_result"|"run"|"retry", "execution_status_transition_applied": bool, "execution_status_transition_reason": "...", "result_kind": "dry_run"|"success"|"failure"}`

🔴 **payload에 Owner 식별자(Discord user id)를 넣지 않는다.** P2-4가 확립한 원칙 —
거부 사유를 일반화된 `unauthorized` 하나로 두어 Owner가 누구인지도 allowlist 설정 여부도
노출하지 않는다 — 을 감사 기록에도 그대로 적용한다. `actor: "owner"`는 **역할**이지
사람이 아니다(task-0042 §3.1의 "역할은 사람이 아니라 직무"와 같은 사상).

## 5. 저장 위치

```
<state_root>/audit/v1/chain.jsonl      # append-only, 저장소 밖
```

`review_store.py`의 3단 경로 정책(`JARVIS_LOCAL_STATE_DIR` → `%LOCALAPPDATA%\Jarvis-Core`
→ `~/.jarvis-core`)을 그대로 쓰고 마지막 세그먼트만 바꾼다. `("hermes-manager","reviews","v1")`,
`("signing-keys","v1")`의 형제.

**저장소 밖에 두는 이유** — 저장소 안에 두면 감사 기록이 `git checkout`·`git reset`·rebase로
조용히 되감긴다. 감사 기록이 감사 대상(저장소)과 같은 생명주기를 공유하면 안 된다.

**보존 정책은 `manual_delete_only`.** 자동 삭제·로테이션·압축을 두지 않는다. 체인은 중간을
잘라내면 그 자체로 깨진다.

## 6. 🔴 fire-and-forget 금지 — 실패 처리 계약

이 task의 핵심 요구사항이며, 스키마보다 이쪽이 본질이다.

### 6.1 계약

> **감사 기록 append가 실패하면 그 작업은 실패다.**
> 승인은 적용되지 않고, `/approve`는 성공을 반환하지 않는다.

구체적으로 `/approve` 경로에서:

1. 감사 항목을 **먼저** append하고 fsync한다.
2. append가 실패하면 **상태 전이를 수행하지 않고** 실패를 반환한다.
3. append 성공 후 상태 전이가 실패하면, 그 실패를 다시 감사 항목으로 append한다
   (`applied: false`, `reason: <코드>`). 실패도 기록되어야 감사다.

### 6.2 P2-5와의 구분 — 이것이 헷갈리기 쉬운 지점

P2-5(Buzz 아웃바운드 알림)는 **일부러** 승인과 격리되어 있다. publish 실패가 `/approve`
성공/실패를 바꾸지 않고 별도 메시지로만 보고된다. 이는 P2-2의 계약
*"A failed append must never look like a failed run"*을 상속한 의도된 설계다.

**감사 기록은 정반대다.** 알림은 놓쳐도 되지만 감사 기록은 놓치면 안 된다. 둘을 같은
"부가 작업" 범주로 묶으면 이 task의 요점을 잃는다.

| | 실패 시 |
| --- | --- |
| P2-5 Buzz 알림 | 승인은 성공 유지, 별도 보고 (fire-and-forget이 **맞는** 경우) |
| **감사 체인 append** | **승인 자체가 실패** (fire-and-forget이 **금지**된 경우) |

### 6.3 §2.2 문제와의 연결

6.1의 계약은 append가 **원자적**일 때만 성립한다. 지금 `/approve` 경로의 `write_text()`
(§2.2 #3)는 중간에 죽으면 파일이 찢어진다. 따라서 구현 시 최소한 승인 경로만이라도
`task_file_writer.py`가 이미 가진 fsync + `os.replace` + `expected_digest` 수준으로
끌어올려야 한다. **이것을 하지 않으면 체인은 장식이다.**

## 7. task-0041 / task-0042와의 관계

### 7.1 task-0041 (미구현)

두 체인이 생기는 것을 막아야 한다. 세 가지 선택지:

| 안 | 내용 | 평가 |
| --- | --- | --- |
| ① task-0041 구현을 먼저 하고 그 위에 얹는다 | task-0041의 이벤트 로그에 승인 이벤트를 하나의 kind로 추가 | 통합은 깔끔하나 **task-0041의 미해결 결정 5건이 전부 선행조건이 된다.** 마이그레이션 비용(기존 50여 파일)까지 떠안는다 |
| ② **독립 감사 체인으로 시작** | `<state_root>/audit/v1/chain.jsonl`. task 상태 이벤트와 별개 | **권고.** task-0041에 의존하지 않아 지금 착수 가능. task-0042가 같은 판단으로 성공한 선례가 있다 |
| ③ 둘 다 만들고 나중에 합친다 | — | 체인이 두 개가 되는 최악. 배제 |

**②를 권고한다.** 근거는 task-0042가 이미 검증한 것과 같다 — 미구현·미결정 설계에 의존하면
같이 멈춘다. 승인 감사와 task 상태 이벤트는 대상도 생명주기도 다르므로(전자는 저장소 밖
영구 보존, 후자는 저장소 안 `.md` 파생 뷰) 별개 체인이 부자연스럽지도 않다.

다만 **스키마는 task-0041과 호환되게 둔다**(`seq`/`kind`/`ts`/`actor`/`payload`/`prev_hash`/
`hash` 필드명 동일). 나중에 합치기로 결정하면 이관이 기계적이 되도록.

### 7.2 task-0042 (구현 완료)

역할 서명키가 이미 있으므로 **체인 헤드에 서명**할 수 있다. 서명 없는 체인은 "전체를 다시
계산해 덮어쓰기"에 무력하지만, 서명된 헤드는 개인키 없이는 위조할 수 없다.

단 task-0042 결정 5에 따라 현재 발급된 키는 `reviewer`/`qa`뿐이다. 감사 체인 서명에는
`orchestrator` 같은 새 역할 키가 필요하고, **이는 결정 5의 범위를 넘으므로 별도 Owner
결정 사항이다**(§10-4).

🔴 그리고 task-0042 §7.2의 불변식이 여기에도 그대로 적용된다 —
**`Valid signature != approval`.** 서명된 감사 기록은 "이 승인이 있었다"는 **증거**이지
승인 권한이 아니다. 감사 체인이 승인 경로가 되어서는 안 된다.

## 8. 검증

`verify-chain` 수동 점검 명령(task-0042의 `verify-records` 선례):

1. `seq`가 1부터 연속인가
2. 각 항목의 `hash`가 재계산과 일치하는가
3. 각 항목의 `prev_hash`가 직전 항목의 `hash`와 일치하는가(제네시스만 `null`)
4. (서명 도입 시) 헤드 서명이 유효한가

결과는 task-0042 §5.4와 같은 형식 — `{"valid": true, "length": N, "head_hash": "..."}` 또는
`{"valid": false, "reason": "<코드>", "first_bad_seq": N, "detail": <문자열|null>}`.
부분 통과나 경고 상태를 두지 않는다.

`reason`은 **결정 5(§10.2)가 정한 고정 어휘**이며 값을 담지 않는다. 조사에 필요한 값
(어긋난 seq, 해시 쌍, OS 오류)은 `detail`로 분리한다 — 로컬 조사용이며 사용자 대면
메시지로 쓰지 않는다.

## 9. 이번 단계에서 하지 않는 것

> 이 절은 설계 단계 기준으로 작성됐다. §10의 Owner 결정으로 **코어와 CLI 구현은 범위
> 안으로 들어왔고**(결정 3의 (a)), 아래는 그 이후에도 범위 밖으로 남는 것들이다.

- **승인 경로 연동** — 결정 3이 별도 task로 분리했다. 그래서 이번 단계의 체인에는
  실제 감사 기록이 쌓이지 않는다(§10.1)
- `adapters/discord/bot_minimal.py` 수정 — §2.2/§6.3의 쓰기 내구성 문제를 **지적만** 했고
  코드는 한 줄도 바꾸지 않았다
- `task_file_writer.py` / `review_store.py` / task-0042 코드 수정
- 기존 승인 이력의 소급 감사 기록 생성 — 원본 데이터가 없어 **재구성 불가능**하다.
  git 히스토리로 일부 추정은 가능하나 추정을 감사 기록으로 승격하지 않는다
- task-0041 구현 또는 그 미해결 결정 5건에 대한 판단
- 새 역할 서명키 발급 — 결정 4가 서명 미부착으로 정리했으므로 `orchestrator` 키는 만들지 않는다
- Buzz 감사 로그와의 연동 — 보고서가 "단일 진실로 삼지 마라"고 한 대상이다

## 10. Owner 결정 (2026-09-05 승인)

초판 §10의 미해결 질문 7건은 모두 결정되었다. 아래가 확정된 계약이다.

| # | 질문 | 결정 | 반영 위치 |
| --- | --- | --- | --- |
| 1 | task-0041과의 관계 | **②독립 체인.** task-0041은 미구현·미승인이라 의존(①)은 이 task를 무기한 블록하고, 병행(③)은 "어느 체인이 진실인가"라는 새 문제를 만든다 | §7.1, `audit_store.py` |
| 2 | 대상 범위 | **A+B**(`owner_approval` + `execution_result`). B가 필요한 이유는 A의 결과여서가 아니라 **A를 우회할 수 있기 때문**이다 — `_run_execution_flow`는 `/approve`·`/run`·`/retry` 3곳에서 호출된다 | §3.2, `ALLOWED_KINDS` |
| 3 | §6.3 쓰기 내구성·승인 경로 연동 포함 여부 | **(a) 코어 + CLI까지만.** 승인 경로 연동은 별도 task로 분리하고 `adapters/discord/bot_minimal.py`는 수정하지 않는다. AGENTS.md 안전 계약(escalation gate)을 이번에 열지 않는다 | §6.3, §9, §10.1 |
| 4 | 감사 체인 서명 부착 | **이번에는 미부착.** 부착은 `orchestrator` 역할 키 발급이 필요해 **task-0042 결정 5**(reviewer/qa만 발급)의 확장이며 별도 승인 사안이다. 후속 연동 task에서 재검토 | §7.2 |
| 5 | 실패 시 노출 범위 | **B — `code` + `detail` 2계층 분리.** 외부·사용자에게 노출되는 `reason`은 값 없는 고정 code만 쓰고, 조사 정보는 `detail`로 분리한다 | §8, §10.2 |
| 6 | 보존 상한 | **무제한 + status 보고.** 체인은 잘라낼 수 없으므로 삭제는 선택지가 아니고, fail-closed 상한은 감사 기능이 승인 기능을 인질로 잡는 구조가 된다. 대신 `status`가 길이·바이트를 보고한다 | §5, `cli.py status` |
| 7 | 구현 언어 | **Python.** 연동 지점인 `bot_minimal.py`가 Python이고, 결정 4가 미부착이므로 Node와 맞출 이유가 없다. **결정 4를 뒤집으면 이 결정도 함께 재검토 대상**이다 | 전체 |

### 10.1 결정 3의 귀결 — 이번 단계의 산출물 성격

Q3=(a)이므로 이번 task는 **감사 체인의 코어와 CLI만** 만든다. 저장소 어디에서도
`audit_store`를 호출하지 않으므로 **체인에 실제 감사 기록은 쌓이지 않는다.**

- 결정 2가 정한 두 스키마(`owner_approval` / `execution_result`)는 **정의만 존재**한다.
- 실제 기록이 발생하는 시점은 **후속 승인 경로 연동 task**다.
- 따라서 이 단계를 "감사 기록 도입 완료"로 기록하면 원칙 8 위반이다. task 기록에는
  **"스키마 확정, 실제 감사 기록은 후속 연동 task 전까지 발생하지 않음"**으로 적는다.

이 구분을 흐리지 않는 것이 §2.1의 발견(체인을 걸 감사 기록이 아직 없다)에 대한 정직한 대응이다.

### 10.2 결정 5의 계약 — 2계층 에러 표면

`AuditChainError(code, detail=None)`.

| 계층 | 내용 | 노출 |
| --- | --- | --- |
| `code` | 값을 담지 않는 **고정 어휘** 1개 | `verify-chain`의 `reason`, 사용자 대면 가능 |
| `detail` | 어긋난 값·경로·해시 쌍·OS 오류 | 로컬 조사용. 사용자 대면 메시지로 쓰지 않는다 |

`str(exc)`는 **code만** 렌더링한다 — 우발적 문자열 변환으로 detail이 새지 않게 하기 위해서다.

**P2-4의 `unauthorized` 일반화와 혼동하지 않는다.** 그쪽 목적은 적대적 상대에게 판별
정보를 주지 않는 것이다. 감사 체인 오류는 성격이 반대로 **Owner 자신이 조사해야 하는
내부 무결성 사건**이므로 상세가 필요하고, 다만 그 상세가 안정적 코드와 같은 문자열에
섞이면 안 된다. 그래서 축약이 아니라 분리다.

이 결정이 초판 구현의 결함 2건을 직접 규정했다.

1. **금지키 가드가 死코드였다.** 키집합 완전일치 검사가 `FORBIDDEN_PAYLOAD_KEYS` 루프보다
   먼저 실행돼 금지키 검사에 도달할 수 없었고, 거부 메시지가 `user_id` 같은 **배제 대상
   키 이름을 그대로 되받아 적었다.** → 가드를 키집합 검사보다 **앞으로** 옮기고,
   code는 `forbidden_key_in_payload` 고정 · 키 이름은 `detail`로 보냈다.
2. **verifier의 `reason`이 §8 계약을 지키지 않았다.** `parse_audit_entry_json`이 해시를
   먼저 검사해 `entry_parse_error:hash_mismatch:expected_<64hex>_got_<64hex>`가 반환됐다.
   → 파서의 고정 code를 그대로 `reason`으로 올리고 해시 쌍은 `detail`로 보냈다. 변조 시
   `reason`은 §8이 못박은 `hash_mismatch`다.
