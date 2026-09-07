# task-0088-console-stale-documentation-correction

- id: `task-0088-console-stale-documentation-correction`
- title: `Console 문서의 stale Memory / Skills 및 Task/Reports metadata 정정`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-08 02:10 UTC`
- updated_at: `2026-09-08 02:10 UTC`
- summary: `task-0087 read-only 감사가 증거와 함께 확정한 사실관계 오류만 고쳤다. task-0071 이 지운 memory_skills 구현을 현재형으로 기술하던 README 섹션, 이미 배포된 기능을 placeholder 로 부르던 skills.json 의 tasks_reports 문구 4건, 제거된 구현이 남아 있다고 주장하던 master-plan 4곳이 대상이다. 제품 방향이 걸린 항목 4건은 의도적으로 손대지 않았다 — status planned, future approval queue 문구, README Future Phases 5, Memory / Skills workstream 행. 4파일 +45 -53, Console 코드 변경 0건.`
- source_command: `task-0087 감사 결과 — 사실관계 오류만 수정 지시`

## 성격

**문서 사실관계 수정 작업이며 Owner Decision 은 유보했다.**
코드 동작을 바꾸지 않았고, 제품 방향에 대한 판단도 하지 않았다.
task-0087 이 `REMOVE` 로 분류한 항목만 반영했고 `OWNER DECISION` 항목은 전부 그대로 두었다.

## 기준선과 결과

| 항목 | 값 |
| --- | --- |
| baseline | `da2805b` |
| 변경 commit | `875a865` |
| diff | **+45 / -53**, 4파일 |

변경 파일:

- `apps/jarvis-console/README.md`
- `apps/jarvis-console/skills.json`
- `apps/jarvis-console/run_smoke_tests.py`
- `docs/master-plan.md`

## 지시서 내부 충돌 1건

검증 항목 4가 "copy-drift 테스트를 새 문구에 맞게 갱신"을 요구하는데
금지사항에 `run_smoke_tests.py` 변경이 함께 있었다. 동시에 만족할 수 없다.

`_test_tasks_reports_registry_copy` 는 baseline 커밋 `064f82b` 의 `skills.json`
바이트 전체를 현재와 대조하고, `replacements` 표에 없는 문자열이 하나라도 다르면
실패한 뒤 교체를 되돌려 `restored_raw == baseline_raw` 까지 확인한다.
문구를 바꾸면서 표를 갱신하지 않을 방법이 없다.

구체적 요구(항목 4)를 따르고 표에 4항목만 추가했다.
기준선 쪽과 바이트 복원 비교, 배열 길이 검사는 손대지 않아 가드 강도는 그대로다.

## 변경 1 — README.md

`### Memory / Skills` 의 Phase 2B~2C-4f 현재형 서술 48줄을 제거했다.
서술된 candidate inbox, write-free preview, route-free save/session primitive 는
task-0071(`8d21efe`) 이 전량 삭제했다.

**섹션을 통째로 지우지는 않았다.** 지시가 "실제 존재하는 historical
design/readiness 문서 링크는 삭제하지 않는다"고 했는데 README 안의 유일한 그 링크가
삭제 대상 섹션 안에 있었다. 두 조건을 함께 만족시키려면 링크를 담을 자리가 필요해
11줄짜리 **과거형** 기록으로 대체했다. 상태 주장이 아니라 이력 서술이고,
design 2건 + readiness 1건 링크를 모두 보존했다(대상 파일 4/4 실재 확인).

## 변경 2 — skills.json `tasks_reports` 문구 4건

배열 요소를 지우지 않고 **제자리 치환**했다. 서식과 줄 종결자 무변경.

| 필드 | 전 | 후 |
| --- | --- | --- |
| `when_to_use` | Use later when Jarvis Console has a local task and report queue. | Use when reviewing discovered local Task status, reports, and checkpoints. |
| `safe_next_action` | Use this as a placeholder for future task and report visibility. | Review the Actionable Task View; every Task write needs Preview and explicit Confirm. |
| `primary_next_action_label` | Review placeholder | Review local Tasks |
| `action_guide[0]` | Review planned task/report concepts. | Review discovered local Task status, reports, and checkpoints. |

`action_guide[1]`, `action_guide[2]`, `safety_notes`, `non_goals`,
`route_keywords`, 배열 길이는 전부 불변이다.

## 변경 3 — copy-drift 테스트

`replacements` 표에 위 4건을 추가했다(+29줄).
각 신규 문구가 파일 전체에서 정확히 1회만 등장하는지, 기존 문구가 0회인지
테스트가 요구하는 조건을 사전 확인했다.

## 변경 4 — docs/master-plan.md 사실관계 4건

| 위치 | 전 | 후 |
| --- | --- | --- |
| L90 진행 bar | `내부 coordinator 구현 — 저장 잠금` | `Console 구현 제거 — 저장 잠금 유지` |
| L203 §3 핵심 산출물 | `write-free preview와 안전한 저장·복구 흐름` | `설계·readiness 기록 (Console 구현은 task-0071에서 제거)` |
| L557 §5 사용자에게 보이는 기능 | `write-free preview` | `없음 — Console 구현은 task-0071에서 제거` |
| L565 §6 전제 | 다음 항목은 **구현 기반이 일부 존재하더라도** 사용자 기능으로 활성화되지 않았다. | 다음 항목은 사용자 기능으로 활성화되지 않았다. Memory / Skills 관련 구현은 task-0071에서 제거됐고, 나머지는 구현 기반이 남아 있다. |

진행 bar 의 막대(`██░░░`)는 바꾸지 않았다 — 성숙도 조정은 제품 판단이라
사실관계 수정 범위를 넘는다.

## Owner Decision — 변경하지 않았음

| 항목 | 상태 |
| --- | --- |
| `skills.json` `tasks_reports.status = "planned"` | **불변** |
| `tasks_reports.short_description` "Future approval and report queue…" | **불변** |
| README Future Phases #5 approval queue 문구 | **불변** |
| master-plan §5 `Memory / Skills` workstream 행과 식별자 | **불변** |
| D1 결정 기록, `NEEDS_APPROVAL` 미추가 결정 | **불변** |
| `keep locked` 역사 결정 5건 | **불변** |
| `MASTER_PLAN_WORKSTREAMS` 구조 | **불변** |

`status` 는 `app.js` 의 `isPlanned` 가 UI 구조(eyebrow, smoke tests/examples 섹션,
docs·limitation 제목, command intro)를 좌우하고 테스트가 값을 고정하므로
단순 copy 수정이 아니다. `short_description` 과 README #5 는 D1 과 충돌하는
제품 방향 문구다. 넷 다 Owner 결정 사항으로 남긴다.

## 검증 결과

| 검증 | 결과 |
| --- | --- |
| Console self-test | PASS |
| Console smoke + browser shell | PASS |
| KEEP route probe | 13/13 PASS |
| canonical 전수 | 76/76 PASS |
| SOP | status=PASS |
| bot self-check | 92/92 PASS |
| discord-intake | 99/99 PASS |
| audit-chain | 7 passed, 0 failed |
| buzz-bridge | 37/37 PASS |
| discord-nl-intent | 35/35 PASS |
| check_no_secrets --self-test | failures=0, PASS |
| node --check app.js | OK |
| git diff --check | clean |
| README 헤더 구조 / 링크 대상 | 15개 헤더 정상, 링크 4/4 실재 |
| `skills.json` JSON parse | PASS |
| `tasks_reports` 배열 길이 | 불변 (action_guide 3, safety_notes 1, non_goals 2) |
| copy-drift 테스트 | PASS |
| master-plan parser | PASS, 22 필드 |
| **`MASTER_PLAN_WORKSTREAMS` 6행** | **PASS**, id 순서 일치 |
| `/api/overview` | **200**, `project_control.v0.1F` |
| `/api/status` | 200, skills 5 |

## 범위 확인

- **Console 코드 변경 0건** — `run_web_app.py`, `web/` 무변경
- `jarvis.bat` **미접근**, `??` untracked 유지
- Discord / Hermes / Research Council / audit-chain / Buzz bridge 무변경
- D6-c, skill_registry 구조, 신규 cleanup 후보 미처리

## 남은 불일치 (기록만)

`tasks_reports` 카드는 여전히 내부 모순이다. `status: planned` 와
"Future approval and report queue" 는 유지했는데 나머지 문구는 이제 배포된
기능을 기술한다. 두 필드가 Owner Decision 이라 의도적으로 남긴 결과이며,
카드를 정합적으로 만들려면 그 둘에 대한 결정이 먼저 필요하다.

`docs/master-plan.md:567-568` 은 `POST /api/memory-skills/candidates` 와
"Memory / Skills UI Save 또는 Confirm" 을 여전히 잠긴 기능으로 나열한다.
지시가 §6 전제 문장만 정정하라고 해서 목록은 두었고, 새 전제 문장이
"task-0071 에서 제거됐다"고 밝히므로 모순은 아니다.
