# task-0041: Task 상태 append-only 이벤트 로그 설계

[Document Type]
- design (Phase 0: 설계만, 구현 없음)

## 1. 목적/배경

task-0038(Buzz/AI-agent 생태계 조사) Phase 1 항목 2. Buzz의 kind 기반 이벤트 모델에서
"상태 변경은 append-only 이벤트로 기록하고, 현재 상태는 그 이벤트에서 파생된 뷰다"라는
아이디어만 차용한다(Nostr, relay, 외부 의존성은 전혀 필요 없음 — 순수 로컬 파일 구조 변경).

목표: `memory/tasks/task-XXXX.md`를 직접 덮어쓰는 지금 방식 대신, 상태 변경을 이벤트로
append하고 `.md`는 그 이벤트 로그에서 재생성되는 읽기 전용 뷰로 재정의한다. 사람이나 다른
에이전트가 오늘처럼 `.md` 파일을 그냥 열어서 읽을 수 있는 경험은 그대로 유지한다.

이 문서는 **설계만** 다룬다. 구현, 기존 파일 마이그레이션, validator 코드 변경은 이 단계의
범위가 아니다(§8 참고).

## 2. 현재 구조 분석

### 2.1 두 개의 서로 다른 "현재 구조"가 존재한다 — 중요한 발견

조사 결과, task 파일에는 **서로 다른 두 개의 쓰기 경로**가 이미 존재한다.

**(A) 엔지니어링된 경로 — `orchestrator/discord-intake/task_file_writer.py`**

- `write_task_file()`: draft object → 신규 `.md` 생성. attempt별 임시 파일 write/flush/
  fsync/close 후 `os.link()`로 no-overwrite atomic publish. 번호 충돌 시 재시도.
- `transition_task_file_status()`: **오직 두 개의 전이만 허용**한다 —
  `TASK_STATUS_TRANSITIONS = frozenset({("TODO", "DOING"), ("DOING", "DONE")})`.
  SHA-256 `expected_digest` 기반 optimistic concurrency(파일이 마지막으로 읽은 이후
  바뀌었으면 `stale`), `status`/`updated_at` 두 필드만 정규식으로 치환, temp-file +
  fsync + `os.replace()`로 원자적 반영, publish 직전 재확인(`_before_final_check`)까지
  포함한 진짜 엔지니어링된 상태 전이 API다.
- `record_task_completion_evidence()`: `DOING` 상태에서만, `completion_evidence` 필드를
  **정확히 한 번만** summary 다음 줄에 추가(재작성/삭제 불가), `updated_at`만 같이 갱신.
- 관련 계약 문서: `docs/task-model.md`, `docs/task-file-creation.md`.

**(B) 이 세션이 실제로 해온 경로 — 직접 파일 편집**

이번 세션(task-0037~0046) 전체에서 Claude Code는 **Read/Edit 도구로 task-XXXX.md를 직접
열어 status/summary/updated_at을 자유롭게 다시 썼다.** `BLOCKED→ON_HOLD→DOING→DONE`,
`TODO→DOING`, `NEEDS_APPROVAL→DONE` 등 (A)가 허용하지 않는 전이(예: `ON_HOLD`는
`docs/task-model.md`의 6개 허용값에도 없다 — 이번 세션이 즉석에서 만든 값)를 포함해서다.
즉 **현재 이 저장소에는 "허용된 좁은 전이만 원자적으로 수행하는 API"와 "그 API를 우회해
아무 필드나 자유롭게 바꾸는 실제 운영 관행"이 동시에 존재한다.** 이번 이벤트 로그 설계는
이 간극을 없애는 것도 목표에 포함해야 한다 — 그렇지 않으면 이벤트 로그도 다시 우회될 것이다.

### 2.2 `scripts/validate_multi_agent_sop.py`는 무관하다

전체를 읽은 결과, 이 validator는 `AGENTS.md`, `docs/jarvis-multi-agent-sop-v0.1.md`,
`docs/master-plan.md`, `.codex/agents/*.toml`만 검증한다. **`memory/tasks/*.md`는 전혀
읽지 않는다.** 역할 경계(Director/Manager/Implementer/Reviewer/QA/Docs)와 budget/승인
게이트 문서가 서로 모순되지 않는지만 정적으로 검사하는 별개 시스템이다. 따라서 이벤트 로그
전환은 이 validator에 어떤 변경도 요구하지 않는다 — task-0039 요약의 "validator 영향 범위
조사 필요"라는 우려는 **기각**한다(근거: 전체 소스 읽음, `memory/tasks` 문자열 매치 0건).

### 2.3 스키마 현황

`docs/task-model.md` 기준 필수 필드 7개(`id/title/status/repo/created_at/updated_at/
summary`) + 선택 필드(`completion_evidence`, `execution_*` 6종). 허용 상태값은 문서상
6개(`TODO/DOING/BLOCKED/DONE/FAILED/NEEDS_APPROVAL`)이지만 §2.1처럼 실제로는 `ON_HOLD`
같은 비표준 값도 쓰였다. task-0006, task-0020(초기), task-0038~0046(최근) 샘플 확인 결과
필드 이름과 형식 자체(백틱 값, UTC 타임스탬프 `YYYY-MM-DD HH:mm UTC`)는 전체 기간 동안
안정적으로 유지됐다.

## 3. 제안 스키마 (이벤트 레코드)

파일당 하나의 append-only 로그: `memory/tasks/events/task-XXXX.jsonl` (JSON Lines, 한 줄
= 이벤트 하나 = 불변).

```json
{"seq": 1, "task_id": "task-0041-task-model-append-only-event-log", "kind": "task_created", "ts": "2026-08-27 10:20 UTC", "actor": "owner-direct", "payload": {"title": "...", "repo": "jarvis-core", "summary": "...", "source_command": "..."}, "prev_hash": null, "hash": "sha256:..."}
{"seq": 2, "task_id": "task-0041-task-model-append-only-event-log", "kind": "status_changed", "ts": "2026-08-27 10:20 UTC", "actor": "claude-code-session", "payload": {"from": "TODO", "to": "DOING"}, "prev_hash": "sha256:...", "hash": "sha256:..."}
{"seq": 3, "task_id": "task-0041-task-model-append-only-event-log", "kind": "summary_updated", "ts": "2026-08-28 09:00 UTC", "actor": "claude-code-session", "payload": {"summary": "..."}, "prev_hash": "sha256:...", "hash": "sha256:..."}
```

- `kind` 후보(닫힌 집합으로 시작, Buzz처럼 숫자 kind가 아니라 사람이 읽는 문자열 사용 —
  외부 프로토콜 호환을 신경 쓸 필요가 없으므로): `task_created`, `status_changed`,
  `summary_updated`, `completion_evidence_recorded`, `field_corrected`(오탈자 등 비의미
  변경, `docs/task-model.md` §7의 "단순 포맷 정리는 생략 가능" 규정과의 접점).
- `prev_hash`/`hash`: task-0044(감사 해시체인)가 그대로 재사용할 수 있는 체인 구조를
  지금 스키마에 넣어둔다. task-0044를 나중에 다시 설계하지 않아도 되게.
- `actor`: task-0042(역할별 서명키)가 이 필드에 서명자 식별자와 서명값을 추가하는 것을
  전제로 필드를 미리 확보해 둔다(예: `actor: "implementer"`, 추후 `sig` 필드 추가).
- 전이 허용 규칙은 (A)의 `TASK_STATUS_TRANSITIONS`를 **확장**해야 한다 — 지금 코드는
  `TODO→DOING`, `DOING→DONE` 두 개뿐이라 이 세션이 실제로 써온 `BLOCKED`,
  `NEEDS_APPROVAL`, 되돌아가는 전이(`ON_HOLD→DOING` 같은)를 표현할 수 없다. 이벤트
  로그 구현 시 `docs/task-model.md` §5의 3가지 흐름(`TODO→DOING→DONE`,
  `TODO→BLOCKED→DOING→DONE`, `TODO→NEEDS_APPROVAL→DOING`)을 명시적 상태 기계로
  다시 정의해야 한다(`ON_HOLD` 같은 비표준 값은 폐기하고 `BLOCKED`로 통일하는 것을 권고).

## 4. 저장 위치 / 파일 구조

```text
memory/tasks/
  task-0041-task-model-append-only-event-log.md   ← 이벤트 로그에서 파생된 읽기 전용 뷰
  events/
    task-0041-task-model-append-only-event-log.jsonl   ← append-only, 유일한 진실
  task-template.md                                 ← 변경 없음
```

- `.md` 파일은 이벤트 로그를 순서대로 재생(replay)해서 만드는 **캐시**다. 사람이 실수로
  `.md`를 직접 고쳐도 다음 재생성 때 덮어써진다(이게 §2.1의 우회 관행을 구조적으로 막는
  방법이다 — API만 남기고 우회로를 없앤다).
- `events/` 디렉터리는 신규. 기존 `memory/tasks/*.md` 파일명 규칙(`task-####-slug.md`)과
  1:1 대응.

## 5. 마이그레이션 전략 (기존 46개 파일)

1. 각 기존 `task-XXXX.md`를 **파싱**해서 필드를 추출한다(파서는 (A)의
   `_transition_metadata()`가 이미 정규식으로 이 작업을 하고 있으므로 재사용 가능).
2. 그 필드로 **합성 `task_created` 이벤트 1개**를 만든다. `ts`는 파일의 `created_at`
   그대로, `payload`는 마이그레이션 시점의 전체 필드 스냅샷.
3. 만약 파일에 `completion_evidence`가 있으면 합성 `completion_evidence_recorded`
   이벤트를 이어서 추가.
4. **`updated_at`이 `created_at`과 다른 파일**(즉 최소 1번은 수정된 파일 — 이번 세션에서
   만든 대부분)은 중간 변경 이력을 재구성할 방법이 없다(git 히스토리에서 복원 가능성은
   있으나 이 설계 문서의 범위 밖). 이런 파일은 합성 `status_changed`(from: null, to:
   현재 status) 이벤트로 "이력 압축, 마이그레이션 시점 스냅샷"이라고 명시적으로 표시한다.
   **아무것도 조용히 손실 처리하지 않는다** — payload에 `migration_note: "pre-migration
   history compressed, see git log for prior states"`를 남긴다.
5. 마이그레이션은 **한 번에 46개를 다 처리하지 않는다.** 먼저 스크립트를 만들어
   1개 파일(예: task-0006, 가장 단순한 형태)에 시험 적용하고 결과 `.md` 재생성본이
   원본과 필드 단위로 100% 일치하는지 diff로 확인한 뒤, 나머지에 적용한다.

## 6. 하위 호환성 / (A) API에 대한 영향

- (A)의 `write_task_file()`은 **이벤트 로그 모델에서도 그대로 유지 가능**하다 — "새 파일
  생성"을 "새 `events/task-XXXX.jsonl` 생성 + `task_created` 이벤트 1개 append + `.md`
  최초 렌더링"으로 바꾸기만 하면 된다. 번호 할당/충돌 재시도 로직은 그대로 재사용.
- `transition_task_file_status()`는 **로직 자체(원자적 write, staleness 검사)를
  버리지 않고 이벤트 append에 재사용**해야 한다 — 지금도 `expected_digest`로 마지막 읽은
  상태와 다르면 `stale`을 반환하는데, 이건 이벤트 로그의 "마지막 `seq`/`hash`를 모르면
  append 거부"와 정확히 같은 낙관적 동시성 패턴이다. 다만 허용 전이 집합은 §3에서 지적한
  대로 확장해야 한다.
- `record_task_completion_evidence()`는 `completion_evidence_recorded` 이벤트로 거의
  1:1 대응. "정확히 한 번만 기록 가능"이라는 불변조건도 이벤트 로그가 자연스럽게 만족한다
  (append-only이므로 같은 kind를 두 번 append하면 재생 로직에서 거부하면 된다).
- **validator(`scripts/validate_multi_agent_sop.py`) 변경 불필요** — §2.2 근거.
- 전환 기간 중 공존 여부: **권장하지 않는다.** (A)와 (B)가 이미 공존하는 지금 상태가
  §2.1에서 지적한 문제의 원인이다. 이벤트 로그를 도입하면서 "직접 `.md` 편집"이라는 세 번째
  경로를 계속 열어두면 문제가 하나 더 늘 뿐이다. 전환은 **하드 컷오버**를 권고한다(모든
  status/summary 변경은 이벤트 append 함수를 통해서만).

## 7. 미해결 질문 (Owner 결정 필요)

1. **마이그레이션 범위**: 기존 46개 파일 전체를 이벤트 로그로 소급 이관할지, 아니면 이
   시점 이후 생성되는 **신규 task부터만** 이벤트 로그를 적용하고 기존 파일은 "레거시,
   `.md` 직접 편집 방식 그대로"로 동결할지. §5의 마이그레이션 비용(특히 이력 압축 문제)을
   감안하면 "신규 task부터만"이 훨씬 싸다. 다만 그러면 저장소 안에 두 가지 다른 규칙을 가진
   task 파일이 영구히 공존한다.
2. **`ON_HOLD` 등 비표준 상태값 정리**: 이번 세션이 실제로 만들어 쓴 `ON_HOLD`를
   `docs/task-model.md`의 공식 상태값에 편입할지, `BLOCKED`로 통일할지.
3. **`(A)` API를 실제로 강제할 방법**: 이벤트 append 함수를 만들어도, Claude Code(또는
   다른 agent)가 여전히 Edit 도구로 `.md`나 `.jsonl`을 직접 열어 고칠 수 있다. 이건
   OS 파일 권한이 아니라 **운영 규율**(AGENTS.md에 "task 파일은 이벤트 append 함수로만
   수정한다" 원칙 추가)로만 막을 수 있다 — task-0043(no-secrets 코드 강제)과 달리 이건
   결정론적 코드로 100% 막기 어렵다는 점을 Owner가 인지해야 한다.
4. **task-0042(서명키)와의 순서**: `actor`/서명 필드를 지금 스키마에 자리만 잡아뒀는데,
   실제 서명 검증 로직은 task-0042 몫이다. 두 task를 병렬로 설계할지, 이 설계를 먼저
   구현하고 task-0042가 위에 얹을지 순서를 정해야 한다(문서 작성자 권고: 이 설계 →
   task-0042가 스키마 위에 서명 필드를 채우는 순서, 반대로 하면 스키마를 두 번 바꾸게 됨).
5. **구현 우선순위**: task-0038 Phase 1 완료 조건은 "6개 중 4개 이상"이므로, 이 항목
   (마이그레이션 비용이 가장 큰 항목)을 반드시 지금 구현해야 하는지, 아니면 더 싼 항목
   (task-0043 no-secrets, task-0045는 이미 완료)로 4개를 채우고 이 항목은 뒤로 미룰지.

## 8. 이번 단계에서 하지 않는 것

- 이벤트 append 함수 구현 (Python 코드 작성 없음)
- `scripts/validate_multi_agent_sop.py` 수정 (필요 없음이 결론이지만, 실제 코드 수정도 안 함)
- 기존 `memory/tasks/*.md` 파일 어떤 것도 수정/이관하지 않음
- `memory/tasks/events/` 디렉터리나 `.jsonl` 파일 생성하지 않음
- §7의 미해결 질문에 대한 Owner 결정 없이 구현 착수하지 않음
