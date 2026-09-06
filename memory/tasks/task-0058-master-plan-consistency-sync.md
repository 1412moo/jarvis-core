# task-0058-master-plan-consistency-sync

- id: `task-0058-master-plan-consistency-sync`
- title: `master-plan 정합성 갱신 (상태 오기 정정 + task-0051~0057 이력 반영)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-06 13:58 UTC`
- updated_at: `2026-09-06 13:58 UTC`
- summary: `master-plan이 task-0042를 NEEDS_APPROVAL, task-0044를 TODO로 기술하고 있었는데 둘 다 DONE이었고, 그중 하나는 Console이 읽는 구조화 필드 Recommended next step이었다. task-0051~0057 7건은 언급 자체가 없었다. Owner 승인 범위 6곳만 고쳤다 — 상태 오기 3곳, 이력 요약 1건 추가, Recent completed 보강, 그리고 승인자 ID 결정에 P2-4 불변식과 감사 스키마 3곳을 함께 바꿔야 한다는 비용을 명시했다. 구조화 필드는 파서로 전후 검증했다.`
- source_command: `read-only 점검 후보 2 승인 (Owner, 최소 범위 6항목)`

## 기준선

- HEAD `c2efa99` = `origin/main`
- 변경: `docs/master-plan.md` 1파일 + 이 기록
- **코드·canonical 규칙 변경 0건**

## 문제 — 두 종류가 섞여 있었다

read-only 분석에서 **잘못 표현**과 **누락**을 갈랐다. 위험도가 다르기 때문이다.

| 종류 | 내용 |
| --- | --- |
| **잘못 표현** | `task-0042`를 `NEEDS_APPROVAL`, `task-0044`를 TODO로 기술(113행·**170행 구조화**), "선택적 잔여 항목"(107행), 승인자 ID 결정을 제약 없이 열어 둠(117행) |
| **누락** | `task-0051`~`task-0057` **7건 전부 언급 0회**, `Recent completed`가 `task-0050`에서 멈춤 |

특히 170행은 자유 텍스트가 아니라 Console이 읽는 구조화 필드
`Recommended next step`이다. **Owner에게 보이는 "다음에 할 일"이 이미 끝난 두 작업을
미완으로 제시**하고 있었다.

## 파서 계약 — 먼저 실측하고 나서 고쳤다

`apps/jarvis-console/run_web_app.py`의 `read_master_plan_snapshot()`이 `## 2. 현재 기준점`을
읽는다. 이 문서를 고치다 이미 한 번 깨뜨린 전례가 있다 — `task-0051`(`c199e7f`)이
`Approval state`에 서술문을 써서 enum을 위반하고 ID 필드에 괄호를 붙여 패턴을 위반한 것을
수습했다. 그래서 이번에는 **수정 전후로 파서를 직접 돌리고 19개 필드 길이를 전부 쟀다.**

| 필드 | 전 | 후 | 상한 500 대비 |
| --- | --- | --- | --- |
| `recommended_next_step` | 283 | **246** | 여유 254 |
| `recent_completed` | 311 | **450** | 여유 50 |
| 나머지 17개 | — | **무변경** | — |

`recent_completed`는 여유가 50자로 가장 빠듯하다. 다음에 이 필드를 늘릴 때는 상한을 먼저
확인해야 한다.

파일 크기 50,941 → 53,217 bytes(상한 128,000). 작업 축 표 6행과 Manager 패키지 표는
손대지 않았다.

## 수정한 6곳

| # | 위치 | 내용 |
| --- | --- | --- |
| 1 | 113행 | `task-0042`/`task-0044`를 `DONE`으로 정정하고 각 커밋(`1557ad7`/`116fe2d`)을 붙였다 |
| 2 | **170행(구조화)** | 같은 오기 제거. 완료 사실과 `task-0052` 실연동으로 대체 |
| 3 | 107행 | "선택적 잔여 항목" → "이후 완료되어 실질 6/6" |
| 4 | 117행 | 승인자 ID 결정에 **변경 비용**을 명시(아래) |
| 5 | 112행 뒤 | `[2026-09-06]` 이력 항목 신설 — `task-0051`~`task-0057`을 커밋 해시와 함께 요약 |
| 6 | **174행(구조화)** | `Recent completed`에 감사 체인 실연동과 canonical 전수 PASS 반영 |

## 4번을 그냥 두지 않은 이유

master-plan은 "승인 감사 기록에 승인자 ID 추가 여부"를 **평범한 열린 결정**으로 적어
뒀는데, 실측해 보면 채택 시 **세 겹을 동시에 뒤집어야** 한다.

| 층 | 근거 |
| --- | --- |
| P2-4 불변식 | `on_message`의 게이트만 `author_id`를 보고 `_run_command`는 인자로 받지 않는다 — 파이프라인이 구조적으로 신원을 모른다 |
| 감사 스키마 3곳 | `KIND_ACTOR_MAP`은 `actor`를 역할 상수로 고정, `FORBIDDEN_PAYLOAD_KEYS`가 4개 ID 키를 거부, payload는 키 집합 **완전 일치**를 요구 |
| 회귀 테스트 | `audit_payload_has_no_owner_identity`가 부재를 단언 |

**결정 자체는 열어 뒀다.** Owner의 권한이기 때문이다. 다만 비용을 모른 채 결정되는 일은
막아야 해서 제약만 적었다.

## 이번에 일부러 건드리지 않은 것

Owner 지시에 따라 제외했다.

- `Last verified` / `Verified implementation HEAD` — 갱신은 "여기까지 검증했다"는 선언이라 Owner 판단 영역이다. 참고로 지금 값(`7d4394ee`)은 최근 5커밋 창 밖이라 Console이 `attention`으로 보고하는데, 이는 **설계된 fail-loud**이지 결함이 아니다
- §5 `Task / Discord / Dashboard` 표 — 감사 체인 연동을 반영하면 정확해지지만 6행 구조를 건드린다
- `Current milestone` — 여유가 186자로 좁아 `Recent completed` 쪽에 넣는 편이 안전했다

## 검증

| 검증 | 결과 |
| --- | --- |
| `read_master_plan_snapshot()` 수정 전 | PASS |
| `read_master_plan_snapshot()` 수정 후 | **PASS**, 19개 필드 전원 상한 내 |
| 변경 필드 | `recommended_next_step`·`recent_completed` **2개뿐**, 나머지 17개 무변경 |
| `jarvis-console` 스모크 + self-test | PASS |
| canonical 전수 | **58/58 PASS** |
| `discord-intake` 스모크 | 79/79 PASS |
| `bot_minimal` self-check | 79/79 PASS |
| `audit-chain` | 6/6 PASS |
| `validate_multi_agent_sop` | `status=PASS` |
| diff 범위 | 5개 hunk, 전부 107~175행 안 |

## 이번 단계 비범위

- 코드·canonical 규칙 변경 — 없다. 문서만 고쳤다.
- `orchestrator/buzz-bridge/lib/task_append.js`의 낡은 docstring — 별도 후보로 남겨 둔다.
- 감사 체인 운영 경로 자동 검증 — `task-0044` §9가 별도 범위로 명시했다.
- `jarvis.bat` — 건드리지 않았다.
