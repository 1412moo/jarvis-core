# task-0042-role-based-signing-keys

- id: `task-0042-role-based-signing-keys`
- title: `역할별(Implementer/Reviewer/QA/Docs) Ed25519 서명키 도입`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-08-27 10:20 UTC`
- updated_at: `2026-09-03 09:52 UTC`
- summary: `task-0038 Phase 1 항목 3. Implementer/Reviewer/QA/Docs 각 역할이 로컬 Ed25519 키페어를 갖고, 리뷰 결과·QA 결과 기록에 서명하도록 하는 설계·구현. Nostr/외부 relay 불필요 — 순수 로컬 키 관리(저장 위치는 기존 Review store 패턴 재사용 후보, %LOCALAPPDATA% 등 저장소 밖). 키 로테이션 절차도 함께 설계. 착수 전 설계 문서로 먼저 합의 필요. 설계·구현·키 생성·왕복 검증·커밋까지 완료.`
- source_command: `task-0038 승인 항목 ③(Phase 1 착수) 하위 실행 단위`

## 진행 기록

- `2026-08-27` 설계 문서 작성(`docs/task-0042-role-based-signing-keys-design.md`).
  미해결 질문 7건을 Owner 결정 사항으로 남기고 대기.
- `2026-09-03` **Owner 결정 1~7 승인.** AGENTS.md 원칙 5에 로컬 서명키 예외 명문화,
  Node stdlib `crypto` 경로 채택(신규 암호 의존성 0개), QA 스키마·평문 저장·발급 범위·
  검증 시점·Windows 한계 확정. 설계 문서의 "Python 암호 의존성 추가가 불가피" 전제는
  **틀린 것으로 정정**됨.
- `2026-09-03` 구현 완료 — `orchestrator/role-signing/`(라이브러리 + CLI + 스모크 테스트),
  `configs/jarvis-role-signing-keys.json`(tracked 공개키 레지스트리 — 구현 시점에는
  비었고, 이후 Owner가 실행한 키 생성으로 `reviewer`/`qa` 공개키 2건이 들어 있다).
  스모크 테스트 38/38 통과. canonical JSON은 Python `json.dumps` 출력과 바이트 단위 일치를
  대조 확인함.

## 실제 키 왕복 검증 (2026-09-03 06:00 UTC)

임시 디렉터리(저장소 밖)에서만 수행했고 산출물은 검증 후 전부 삭제했다. 개인키 값은
출력하지 않았고 저장소에 남기지 않았다(전수 문자열 검색으로 확인).

| 검증 | 결과 |
| --- | --- |
| 실제 `hermes_review_record` 서명 → 검증 | PASS (`reviewer`, key_status `active`) |
| Node canonical 바이트 vs Python `serialize_review_record()` | **942바이트 완전 동일** |
| Node canonical의 SHA-256 vs Python `review_record_digest()` | 일치 (`f85f8915…f373af`) |
| Python 재파싱·재직렬화 후 같은 서명 재검증 | PASS |
| `jarvis_qa_result` 서명 → 검증 | PASS (`qa`, key_status `active`) |
| `--dir` 짝 매칭 모드 | PASS (2쌍) |
| 레코드 1글자 변조 | 거부 `payload_digest_mismatch` (exit 1) |
| 서명 1바이트 변조 | 거부 `signature_invalid` (exit 1) |
| 역할 위장(reviewer 키에 `role: qa`) | 거부 `role_key_mismatch` |
| 타입 교차 재사용(review 봉투 ↔ QA 레코드) | 거부 `record_type_mismatch` |

**설계의 핵심 기술 주장이 실제 데이터로 확인됐다** — Python이 만든 진짜 ReviewRecord에
대해 Node가 계산한 서명 대상 바이트가 Python의 canonical 출력과 바이트 단위로 같다.
합성 객체가 아니라 `review_record.py`가 실제로 생성한 레코드로 확인한 것이다.

## 테스트 현황 (2026-09-03 06:05 UTC)

- 신규: `orchestrator/role-signing/run_smoke_tests.js` **38/38 PASS**
- 기존 회귀 9종 중 **8종 PASS** — team-manager-bot, daily-ai-radar, hermes-manager-pilot,
  research-council, discord-intake, discord-nl-intent, buzz-bridge,
  `validate_multi_agent_sop.py`
- `apps/jarvis-console` 발견 시점 **FAIL — task-0042와 무관한 기존 결함**(아래 참조).
  `task-0051`로 수정 완료되어 **현재는 전체 10종 전건 PASS**다.
- secret scan: 이번 세션 신규/변경 18개 파일 PASS. 전체 스캔의 findings 7건은 전부
  `scripts/check_no_secrets.py` 자신의 fixture 자체 히트(기존 상태).

### 발견된 기존 결함 (task-0042 범위 밖 → task-0051로 분리·수정 완료)

`apps/jarvis-console/run_smoke_tests.py`가 `RegistryError: master plan approval state is
invalid`로 실패한다. 원인은 `docs/master-plan.md`의 `- Approval state:` 값이 산문인데
`apps/jarvis-console/run_web_app.py`는 이 필드를 `{none, required, blocked}` enum으로
파싱하기 때문이다.

- 도입 커밋: `8843488`(2026-08-28, "record Phase 1 decisions and ON_HOLD state")
- 마지막 정상 커밋: `22b7398` — 이 시점 master-plan으로 바꿔 실행하면 테스트가 통과한다
- 내 편집을 전부 되돌린 HEAD 상태에서도 동일하게 실패함을 확인했다 — **이 세션의 변경이
  원인이 아니다**

`Approval state`는 승인 상태를 담은 거버넌스 필드여서 임의로 고치지 않고 Owner에게
보고했고, **Owner가 우선 수정을 지시**해 `task-0051`로 분리해 처리했다. 수정 후
`apps/jarvis-console`을 포함한 전체 스모크 10종이 전건 PASS다. 상세는
`memory/tasks/task-0051-master-plan-structured-field-drift.md` 참조.

`apps/jarvis-console` FAIL 기록은 발견 당시 사실이며, 현재는 해소되었다.

## 커밋 전 독립 재검증 (2026-09-03 09:52 UTC)

AGY 세션이 quota 제한으로 중단되어, 커밋 직전에 별도 세션이 위 기록을 그대로 믿지 않고
같은 검증을 처음부터 다시 실행했다. 재현되지 않는 항목은 없었다.

| 검증 | 결과 |
| --- | --- |
| `orchestrator/role-signing/run_smoke_tests.js` | **38/38 PASS** (exit 0) |
| 기존 회귀 10종 전건 | **전건 PASS** (아래) |
| `node cli.js verify-keys` (실제 등록 키) | `ok: true`, problems 0건 |
| tracked 레지스트리 ↔ 저장소 밖 개인키 일치 | `reviewer`/`qa` 2건 모두 일치 |
| 키 디렉터리가 저장소 밖인지 | `%LOCALAPPDATA%\Jarvis-Core\signing-keys\v1` — 저장소 밖 확인 |
| 저장소 내 `*.key` 파일 | 0건 |
| 저장소 내 PRIVATE KEY 블록 | 0건 |
| 테스트 실행이 저장소에 남긴 잔여 파일 | 0건 (`git status` 불변) |
| `check_no_secrets.py --staged` (staged 전체) | **PASS**, findings 0건 |

회귀 10종: team-manager-bot, daily-ai-radar, hermes-manager-pilot, jarvis-console,
research-council, discord-intake, discord-nl-intent, buzz-bridge(35/35),
role-signing(38/38), `validate_multi_agent_sop.py`(negative_failures=0).

`apps/jarvis-console`는 `task-0051`(`c199e7f`) 수정 이후 PASS이며, 이번 커밋은 그 위에서
독립적으로 이루어진다.

## 커밋 범위

이 커밋은 task-0042 파일만 담는다. 같은 working tree에 있던 `task-0044`(감사 해시체인)
관련 파일과 `jarvis.bat`은 **의도적으로 제외**했다 — 별개 작업 단위이므로 섞지 않는다
(원칙 7).

포함: `AGENTS.md`, `.gitignore`, `configs/jarvis-role-signing-keys.json`,
`docs/task-0042-role-based-signing-keys-design.md`, `orchestrator/role-signing/`,
`memory/tasks/task-0042-role-based-signing-keys.md`.

`configs/jarvis-role-signing-keys.json`에는 **공개키만** 들어 있다(스캔 PASS). 개인키는
저장소 밖에 있고 `.gitignore`의 `*.key`가 2차 방어선이다.

키 생성 명령은 이미 완료되었으므로 다시 실행하지 않는다 — 활성 키가 있는 역할에 대한
재생성은 `signing_key_already_exists`로 거부된다(교체가 필요하면 `rotate-key`).

## 남은 후속 (이번 범위 밖)

`docs/master-plan.md`는 아직 task-0042를 `NEEDS_APPROVAL`로 적고 있다(107/113/170행).
이번 커밋은 "이미 있는 변경을 검증해 커밋한다"는 범위로 한정되어 master-plan을 새로
편집하지 않았다. 상태 동기화는 Owner 확인 후 별도로 처리한다.
