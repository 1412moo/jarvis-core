# task-0044-audit-hash-chain

- id: `task-0044-audit-hash-chain`
- title: `승인·증거 감사 기록을 해시체인으로 전환 (fire-and-forget 금지)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-08-27 10:20 UTC`
- updated_at: `2026-09-05 10:40 UTC`
- summary: `task-0038 Phase 1 항목 5. 각 승인/증거 기록에 prev_hash를 포함하는 해시체인 구조를 도입하는 설계·구현 작업. Buzz의 감사 파이프라인이 fire-and-forget이라 감사 로그가 조용히 유실될 수 있다는 점(task-0038 보고서 §7.2)이 반면교사 — Jarvis-Core 구현에서는 감사 기록 실패 = 작업 실패로 처리해야 하며, 절대 fire-and-forget으로 만들지 않는다. 착수 전 설계 문서로 대상 이벤트 범위를 먼저 합의 필요 — 2026-09-03 설계 문서 작성, 2026-09-05 Owner 결정 7건 승인 후 코어+CLI 구현 완료. 결정 3(a)에 따라 승인 경로 연동은 별도 task로 분리했으므로 **스키마만 확정되고 실제 감사 기록은 아직 발생하지 않는다.**`
- source_command: `task-0038 승인 항목 ③(Phase 1 착수) 하위 실행 단위`

## 진행 기록

- `2026-09-03` 설계 문서 작성 — `docs/task-0044-audit-hash-chain-design.md`.
  구현·코드 변경 없음. task 자체가 "착수 전 설계 문서로 대상 이벤트 범위를 먼저 합의"를
  게이트로 명시했으므로 그 게이트를 채우는 단계다.

## 설계 중 확인된 사실 (구현 방향을 바꾸는 발견)

1. 🔴 **체인을 걸 감사 기록이 아직 없다.** 저장소 전체에 승인 감사 로그 파일도, 감사 기록
   함수도, `bot_minimal.py`의 로깅 호출조차 없다(`memory/` 아래에는 `tasks/`뿐). `audit`로
   잡히는 것은 전부 보안 감사 결과를 설명하는 **코드 주석**이다. 따라서 이 task의 실질은
   "기존 기록에 `prev_hash` 추가"가 아니라 **"감사 기록을 처음 만들고 체인으로 만든다"**다.
2. 🔴 **가장 감사가 중요한 경로가 가장 약한 쓰기를 쓴다.** task 파일 쓰기 경로가 최소 5개
   있는데, 실제 `/approve` 경로인
   `adapters/discord/bot_minimal.py:_apply_task_status_transition`(836행)은
   `task_file.write_text()` 한 줄이다 — fsync도, atomic replace도, `expected_digest`
   동시성 검사도 없다. 정작 `orchestrator/discord-intake/task_file_writer.py`에는 이 셋이
   전부 구현돼 있는데 승인 경로가 그것을 쓰지 않는다. **찢어질 수 있는 쓰기 위에 체인을
   얹으면 체인이 깨진 것인지 공격인지 구분할 수 없다.**
3. **`/run`·`/retry`는 `/approve`를 거치지 않고 서브프로세스 실행에 도달한다.**
   `_run_execution_flow`는 1039(`retry`)/1091(`run`)/1291(`approve`) 세 곳에서 호출된다.
   승인만 기록하면 실행의 3분의 2가 감사에서 빠진다.
4. **task-0041이 이미 같은 체인 구조를 설계해 뒀다**(`prev_hash`/`hash`를 task 상태 이벤트
   스키마에 넣고 "task-0044가 재사용하도록"이라고 명시). 그러나 task-0041은 미구현이고
   미해결 Owner 결정이 5건 남아 있다. **체인이 두 개 생기지 않게 관계를 먼저 정해야 한다.**
5. task-0042 덕분에 재사용 자산이 갖춰져 있다 — canonical JSON(Python/Node 바이트 동등성
   확인됨), 도메인 분리 해시, 저장소 밖 append-only 저장소 패턴, 역할별 Ed25519 서명.

## Owner 결정 7건 (2026-09-05 승인, 설계 문서 §10이 정본)

| # | 질문 | 결정 |
| --- | --- | --- |
| 1 | task-0041과의 관계 | **②독립 체인** |
| 2 | 대상 범위 | **A+B** (`owner_approval` + `execution_result`) |
| 3 | 승인 경로 연동·쓰기 내구성 포함 여부 | **(a) 코어 + CLI까지만.** 연동은 별도 task, `bot_minimal.py` 무수정 |
| 4 | 감사 체인 서명 | **이번엔 미부착** (task-0042 결정 5의 확장이라 별도 승인 사안) |
| 5 | 실패 시 노출 범위 | **B — `code` + `detail` 2계층 분리** |
| 6 | 보존 상한 | **무제한 + `status` 길이·바이트 보고**, 死상수 정리 |
| 7 | 구현 언어 | **Python** |

## 🔴 이번 단계의 산출물 성격 (결정 3의 귀결)

**스키마 확정, 실제 감사 기록은 후속 연동 task 전까지 발생하지 않는다.**

저장소 어디에서도 `audit_store`를 호출하지 않는다(전수 검색 0건). 따라서 결정 2가 정한
두 스키마는 **정의만 존재**하고 체인 파일에는 아무것도 쌓이지 않는다. 이 단계를 "감사
기록 도입 완료"로 적으면 원칙 8 위반이므로 그렇게 적지 않는다.

실제 기록이 시작되는 시점은 **승인 경로 연동 task**이며, 그 task는 아직 기안되지 않았다.

## 구현 (2026-09-05)

`orchestrator/audit-chain/` — `audit_entry.py`(스키마·canonical JSON·도메인 분리 해시),
`audit_store.py`(저장소 밖 경로 정책·파일 락·fsync·append), `audit_verifier.py`(무결성 검증),
`cli.py`(`verify-chain` / `status`), `run_smoke_tests.py`.

### 인수인계 중 발견해 수정한 결함 4건

AGY의 초판 구현은 **한 번도 실행된 적이 없었다.** ①이 실행을 막고 있어 ②③④가 드러나지
않은 상태였다.

| # | 결함 | 성격 | 처리 |
| --- | --- | --- | --- |
| ① | `orchestrator/audit-chain`은 하이픈 때문에 Python 패키지가 될 수 없는데 4개 파일이 상대 임포트(`from .audit_entry`)를 썼다. 스모크·CLI 모두 `ImportError`로 즉사 | 순수 배선 오류 | 형제 디렉터리(`discord-intake`/`discord-nl-intent`) 관례인 sys.path + 절대 임포트로 정정 |
| ② | `AuditEntry`가 `slots=True` 데이터클래스라 `__dict__`가 없는데 append·검증 양쪽이 `entry.__dict__`를 썼다. 정작 그 용도로 만든 `audit_entry_to_dict()`는 어디서도 호출되지 않았다 | 순수 배선 오류 | `audit_entry_to_dict()` 호출로 교체 |
| ③ | 키집합 완전일치 검사가 `FORBIDDEN_PAYLOAD_KEYS` 루프보다 먼저 실행돼 **금지키 가드가 도달 불가능한 死코드**였고, 거부 메시지가 `user_id` 같은 배제 대상 키 이름을 그대로 되받아 적었다 | **설계 판단 필요** | Owner 결정 5 확정 후 처리 — 가드를 앞으로 옮기고 code는 고정, 키 이름은 `detail`로 |
| ④ | `parse_audit_entry_json`이 해시를 먼저 잡아 `reason`이 `entry_parse_error:hash_mismatch:expected_<64hex>_got_<64hex>`로 반환됐다. 설계 §8이 못박은 고정 code 계약 위반이자 해시 전문 노출 | **설계 판단 필요** | Owner 결정 5 확정 후 처리 — 파서의 고정 code를 그대로 `reason`으로, 해시 쌍은 `detail`로 |

①②는 버그라 즉시 고쳤고, ③④는 **에러 어휘 계약(결정 5)의 하위 문제**여서 Owner 결정
전까지 손대지 않고 대기했다.

### 결정 5·6이 만든 변경

- `AuditChainError(code, detail=None)` — raise 지점 **57곳 중 값을 싣고 있던 30곳**을
  2계층으로 정리했다. `str(exc)`는 code만 렌더링해 우발적 문자열 변환으로 detail이 새지
  않게 했다. 특히 `append_audit_entry_io_failed`는 OSError를 통해 **감사 저장소 절대 경로**를
  노출하고 있었다.
- `verify-chain` 실패 형식에 `detail` 추가(설계 §8 갱신).
- `status`가 `size_bytes`·`retention`을 보고(결정 6). 쓰이지 않던 `MAX_CHAIN_LINE_BYTES`
  死상수 제거 — 실제 건별 크기 제한은 `MAX_JSON_BYTES`가 걸고 있다.

## 검증 (2026-09-05)

- `orchestrator/audit-chain/run_smoke_tests.py` **6/6 PASS** — canonical JSON 결정론성,
  도메인 분리 해시, 스키마·금지키 거부, 저장소 밖 경로 정책, genesis(`seq=1`/`prev_hash=null`),
  `prev_hash` 체이닝, seq 연속성, 변조·삭제·순서뒤집기 탐지, 손상 체인에 대한 fail-closed
  append 거부, CLI 왕복
- CLI 실행 확인 — `verify-chain` exit 0, `status`가 체인 경로를
  `%LOCALAPPDATA%\Jarvis-Core\audit\v1\chain.jsonl`로 보고(**저장소 밖 확인**)
- 기존 회귀 **10종 전건 PASS** — team-manager-bot, daily-ai-radar, hermes-manager-pilot,
  jarvis-console, research-council, discord-intake, discord-nl-intent, buzz-bridge(35/35),
  role-signing(38/38), `validate_multi_agent_sop.py`
- `check_no_secrets.py --self-test` PASS(16/16), `--staged` PASS
- 설계 §10 결정 7건 ↔ 코드 전수 대조: 불일치 0건
- `adapters/discord/bot_minimal.py`, task-0042 파일, `task_file_writer.py`,
  `review_store.py` **무변경 확인**

## 이번 단계 비범위

- **승인 경로 연동** — 결정 3이 별도 task로 분리했다. 이것이 미완인 한 체인은 비어 있다
- `adapters/discord/bot_minimal.py` 수정 — 발견 2를 **지적만** 했고 코드는 한 줄도 바꾸지 않았다
- `task_file_writer.py` / `review_store.py` / task-0042 코드 수정
- 기존 승인 이력의 소급 감사 기록 생성 — 원본 데이터가 없어 재구성 불가능하며, git
  히스토리 기반 추정을 감사 기록으로 승격하지 않는다
- task-0041 구현 또는 그 미해결 결정 5건에 대한 판단
- `orchestrator` 역할 서명키 발급 — 결정 4가 미부착으로 정리했다

## 후속

승인 경로 연동 task가 **아직 기안되지 않았다.** 그 task가 §2.2의 쓰기 내구성 문제
(`bot_minimal.py:_apply_task_status_transition`의 `write_text()` 한 줄)와 함께 다뤄져야
체인이 실효를 갖는다. 착수는 AGENTS.md 안전 계약에 따라 Owner의 명시적 승인이 필요하다.
