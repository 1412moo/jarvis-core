# task-0089-console-owner-decision-finalization

- id: `task-0089-console-owner-decision-finalization`
- title: `Console Owner Decision Finalization`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-08 02:45 UTC`
- updated_at: `2026-09-08 02:45 UTC`
- summary: `task-0087 이 남겨둔 Owner Decision 을 확정하고 Console 의 현재 Task lifecycle 범위에 문서와 메타데이터를 맞췄다. Owner 가 지정한 status 값 active 는 registry 계약에 존재하지 않아 그대로 넣으면 RegistryError 로 콘솔 부트스트랩이 죽는 것을 실측 확인하고, 계약을 넓히는 대신 기존 어휘 available 을 썼다. copy-drift 가드는 승인 문자열이 파일 내 유일하다고 가정하는데 planned 와 available 은 다른 skill 에도 있어 선택적 raw anchor 를 최소 확장했고 mutation probe 6종으로 강도를 확인했다. 3파일 +39 -11, Console 런타임 코드 변경 0건.`
- source_command: `task-0087 Owner Decision 확정 반영 지시`

## 기본 정보

| 항목 | 값 |
| --- | --- |
| baseline | `0f28f02` |
| implementation commit | `165f679` |
| implementation commit message | `docs(console): finalize owner decisions for task lifecycle scope` |
| 변경 규모 | 3파일, **+39 / -11** |

## 목적

task-0087 read-only 감사가 `OWNER DECISION` 으로 분류해 남겨둔 항목을 확정하고,
Console 의 현재 Task lifecycle 범위와 문서·메타데이터를 일치시킨다.
기능 범위를 넓히는 작업이 아니라 이미 확정된 책임 범위를 반영하는 작업이다.

## Decision 1 — `planned` → `available`

**최초 Owner 표현은 `active` 였으나 현재 registry 계약에 `active` 는 존재하지 않았다.**
세 곳에서 독립적으로 확인했다.

| 근거 | 내용 |
| --- | --- |
| `run_web_app.py:393` | `ALLOWED_STATUSES = {"available", "planned", "experimental"}` |
| `contracts/skill-registry-v0.1.md:81-85` | `## Allowed Status Values` — 동일한 3개 |
| `web/styles.css:469,474,479` | `.status.available` / `.status.planned` / `.status.experimental` 만 존재 |

실측 검증:

```
validate_registry: RegistryError -> tasks_reports invalid status: active
```

장애 전파 경로도 확인했다.

```
validate_registry (RegistryError)
  -> load_registry -> status_payload()
  -> GET /api/status = 500
  -> app.js 의 유일한 부트스트랩 loadRegistryStatus() 실패
  -> registrySkills 미적재 -> Skills/Hermes/Radar/Settings 탭 공백,
     Voice Inbox 는 await registryLoadPromise 에서 정지
```

부분 장애가 아니라 **UI 전체 로드 실패**다.

따라서 계약을 확장하는 대신 기존 어휘 `available` 을 사용했다.
`tasks_reports` 는 현재 local Task 발견·조회, Actionable Task View,
`TODO -> DOING`, `DOING -> DONE`, completion evidence 를 실제로 제공하므로
`available` 이 Owner 의도에 부합한다. `available` 추가 요건
(`docs` or `tests` or `safe_next_action`)도 이미 충족한다.

**`active` 를 새로운 registry status 로 추가하지 않았다.**

`settings` 는 `planned` 로 남아 `app.js` 의 `isPlanned` 분기는 계속 사용자가 있다.
dead code 를 만들지 않았다.

## Decision 2 — Approval Queue

- Console 은 **Task lifecycle 화면**이다.
- Console 은 **approval 화면이 아니다.**

실측 확인한 사항:

| 항목 | 결과 |
| --- | --- |
| approval queue UI | 추가 **없음** (`web/` 무변경) |
| approval action | 추가 **없음** |
| `NEEDS_APPROVAL` transition | 추가 **없음** — `TASK_TRANSITION_ACTIONS` 는 `start`(TODO→DOING), `complete`(DOING→DONE) 그대로 |
| approval 전용 endpoint | 추가 **없음** |
| GET routes | `/api/status`, `/api/overview`, `/api/history`, `/api/skill` — 추가 0건 |

`NEEDS_APPROVAL` 상태의 Task 는 여전히 **표시**되며 처리는 콘솔 밖으로 안내한다:
"Review the summary and make the required decision outside Jarvis Console."

`short_description` 도 함께 정정했다.

| 전 | 후 |
| --- | --- |
| Future approval and report queue for Jarvis Console. | Local Task lifecycle status, reports, and checkpoints for Jarvis Console. |

**human approval 개념 자체를 폐기한 것이 아니다.** 향후 필요해지면 Console 의
Task lifecycle surface 와 분리된 별도 system/workflow 로 취급한다.

## Decision 3 — README

`README.md` Future Phases #5 를 수정했다.

| 전 | 후 |
| --- | --- |
| Consider an approval queue only after a separate human-approval design. | Treat human approval as a separate system, not a later console phase. Jarvis Console stays a Task lifecycle screen and adds no approval queue, approval action, or `NEEDS_APPROVAL` transition. |

`approval` 단어를 일괄 삭제하지 않았다. task-0087 조사에서 KEEP 으로 분류한
역사적·경계 설명 문구는 그대로 유지했다(파일 내 총 10건) — Non-Goals 의 금지 목록,
권한 부재 서술, Project Control 이 **표시**하는 승인 필요 여부,
work-package approval 과 `/approve` 의 분리 원칙, Radar/Research 출력 성격 서술.

## Decision 4 — Memory / Skills

이번 작업에서 **변경하지 않았다.**

- Memory / Skills 는 Jarvis-Core 의 **별도 workstream** 으로 유지
- Console 에 Memory / Skills UI **재도입 없음**
- `skill_registry` **DEFER 유지**
- `docs/master-plan.md` 의 `| Memory / Skills |` workstream 행 유지
- task-0088 이 넣은 README 역사 포인터와 design/readiness 문서 링크 유지

## 실제 변경 파일

정확히 3개다.

- `apps/jarvis-console/skills.json` — `status`, `short_description`
- `apps/jarvis-console/README.md` — Future Phases #5
- `apps/jarvis-console/run_smoke_tests.py` — copy-drift 표와 기대값

총 diff **+39 / -11**, implementation commit `165f679`.

## copy-drift guard 개선

`replacements` 표는 **승인 문자열이 파일 내 유일**하다고 가정한다.
그런데 `planned` 는 `settings` 에도, `available` 은 다른 3개 skill 에도 있다.
단순 문자열 replacement 만 쓰면 세 가지가 깨진다.

- `assert obsolete.encode() not in current_raw` — `settings` 의 `planned` 때문에 실패
- `assert current_raw.count(replacement.encode()) == 1` — `available` 4회로 실패
- byte restore 시 다른 skill 의 `available` 까지 `planned` 로 되돌려 손상

**다른 skill 의 status drift 를 검출하지 못할 위험**이 실재했다.

기존 8개 항목은 그대로 두고, 선택적 4번째 raw anchor 를 지원하도록 최소 확장했다.

```
def raw_anchor(entry):
    return entry[3] if len(entry) > 3 else (entry[0], entry[1])
```

`tasks_reports.status` 에는 바로 위의 고유한 `display_name` 줄을 포함한
anchor 를 썼다. 기존 검증 구조는 전부 유지했다.

- 구조적 대조 (`baseline_strings[path] == obsolete`, `current_strings[path] == replacement`)
- `obsolete not in raw`
- `replacement count == 1`
- 전체 byte restore round-trip

### mutation probe 6종 — 전부 PASS

| probe | 결과 |
| --- | --- |
| baseline (미변형, 통과해야 정상) | PASS |
| purpose drift (미승인 문자열) | 차단 |
| tasks_reports status rollback (`available` → `planned`) | 차단 |
| **research_council status tampering** (다른 skill 의 status 를 몰래 뒤집음) | **차단** |
| short_description drift | 차단 |
| approved string rollback (이전 승인 문구 되돌림) | 차단 |

세 번째 항목이 이번 확장의 핵심 검증이다 — 짧은 값을 승인 목록에 넣으면서
다른 skill 의 status 감시에 구멍이 생기지 않았음을 직접 확인했다.
probe 전후 실제 `skills.json` 의 **byte-identical 복원**도 확인했다.

## 테스트

| 검증 | 결과 |
| --- | --- |
| JSON parse | PASS |
| `tasks_reports.status == "available"` | PASS |
| registry validation | PASS |
| `/api/status` | 200 |
| `/api/overview` | 200 |
| `/api/skill?skill_id=tasks_reports` | 200 |
| copy-drift | PASS |
| mutation probe | 6/6 PASS |
| Console self-test | PASS |
| Console smoke + browser shell | PASS |
| KEEP route probe | 13/13 PASS |
| canonical 전수 | 77/77 PASS |
| SOP | status=PASS |
| bot self-check | 92/92 PASS |
| discord-intake | 100/100 PASS |
| audit-chain | 7 passed, 0 failed |
| buzz-bridge | 37/37 PASS |
| discord-nl-intent | 35/35 PASS |
| hermes-manager-pilot | PASS |
| research-council | PASS |
| check_no_secrets --self-test | PASS |
| node --check app.js | PASS |
| git diff --check | clean |

배열 구조도 불변이다 — `action_guide` 3, `safety_notes` 1, `non_goals` 2, skills 5.

## 변경하지 않은 영역

- Console Python runtime code (`run_web_app.py`) 변경 **없음**
- `web/` 변경 **없음**
- registry contract (`contracts/skill-registry-v0.1.md`) 변경 **없음**
- `ALLOWED_STATUSES` 변경 **없음**
- CSS status classes 변경 **없음**
- Memory / Skills implementation 재도입 **없음**
- `skill_registry` 변경 **없음**
- Research Council 변경 **없음**
- Hermes 변경 **없음**
- Discord 변경 **없음**
- `docs/` 변경 **없음**
- `jarvis.bat` 접근·수정·staging **없음**

## 후속 상태

- implementation commit: `165f679`
- 이 기록 추가 전 baseline: `165f679`
- task record 는 **별도 commit** 으로 남긴다 — `165f679` 를 amend 하거나 rebase 하지 않았다.
- commit 후 `HEAD == origin/main`, tracked working tree clean,
  `jarvis.bat` 은 `??` 상태 유지를 확인한다.
