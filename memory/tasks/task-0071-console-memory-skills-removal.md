# task-0071-console-memory-skills-removal

- id: `task-0071-console-memory-skills-removal`
- title: `Jarvis Console 축소 1단계 — memory_skills 기능군 제거 (D5)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-07 05:32 UTC`
- updated_at: `2026-09-07 05:32 UTC`
- summary: `D5 결정에 따라 Console 의 memory_skills 기능군을 제거했다. save 엔드포인트가 이미 404 라 동작 변화 없이 앱 본체의 3분의 1이 빠지는 유일한 덩어리였다. 경계는 이름이 아니라 실제 참조로 정해 이름만 비슷한 여섯 심볼을 남기고 이름에 memory 가 없는 전용 클래스 셋은 함께 지웠다. 삭제는 AST 줄 범위로 했고 self-test 는 고아 단언까지 고정점 반복으로 정리했다. 5,884줄 감소, 신규 심볼 0개, 전 회귀 통과. master-plan 의 승인 화면 문구도 D1 로 정정했다.`
- source_command: `D1/D5 Owner 결정에 따른 Console 축소 1단계 지시`

## 기준선

HEAD `b62f92e` = `origin/main`. Console 5파일 + `docs/master-plan.md` 2줄.

## 왜 이것부터인가

task-0070 조사에서 실측한 결과, Console 축소의 최대 대상은 "Buzz와 중복되는 협업 UI"가
아니라 **이미 잠겨서 쓸 수 없는 `memory_skills` 3,318줄**이었다. `/api/memory-skills/candidates`
save 는 POST allowlist 에 없어 **404**이고 master-plan 6절 잠금 목록에 있다. 즉 **동작 변화
없이** 앱 본체의 3분의 1을 걷어낼 수 있는 유일한 덩어리였다.

## 경계는 이름이 아니라 참조로 정했다

이름만 보고 지웠으면 여섯 개를 잘못 지웠을 것이다. 전 심볼의 실제 참조처를 훑어 다음을
**남겼다**.

| 남긴 심볼 | 실제 소유 기능 |
| --- | --- |
| `is_overview_candidate_path` | overview / history / task_transition 이 쓴다 |
| `is_history_candidate_name` | history |
| `voice_candidate_title` / `voice_candidate_summary` | Voice Inbox |
| `_normalize_evaluate_task_candidate_field` | evaluate-idea |
| `memory_string_has_valid_unicode` | **`_validate_evaluate_idea_payload`가 쓴다** |

마지막 항목이 유일한 경계 교차다. 이름은 `memory_`로 시작하지만 범용 유니코드 검증기이고,
이름을 바꾸면 범위 밖인 evaluate-idea 를 건드리게 되어 **그대로 뒀다.**

반대로 이름에 memory 가 없지만 memory 전용이라 **함께 지운 것**도 있다.

| 지운 심볼 | 근거 |
| --- | --- |
| `SessionRegistry` / `LocalRequestGuard` / `PreviewTokenRegistry` | 사용처가 memory coordinator 와 memory self-test 뿐. `JarvisConsoleHandler`에 연결되지 않았음을 기존 단언이 확인한다 |
| `default_jarvis_local_state_root` | 유일한 참조가 지워진 `MEMORY_SKILLS_STATE_ROOT_NAME` 이었다 |

`TaskTransitionRegistry`·`CreateLocalTaskRegistry`·`CompletionEvidenceRegistry`는 이 셋과
무관한 별도 클래스라 **task lifecycle 은 영향을 받지 않는다.**

## 방법 — AST 기반, 텍스트 추정 아님

top-level 심볼과 상수는 AST 노드의 실제 줄 범위로 잘라 여러 줄 상수와 데코레이터가 어긋나지
않게 했다. `run_self_test` 와 테스트 `main()` 은 두 규칙을 고정점까지 반복 적용했다.

1. 삭제된 심볼이나 삭제된 라우트 경로를 언급하는 **문장 전체**를 제거
2. 더 이상 대입되지 않는 지역 변수를 읽는 문장을 제거 — 1에 의해 고아가 된 단언을 걷어낸다

중간에 줄 단위 휴리스틱을 한 번 시도했다가 `IndentationError`를 냈고, **되돌린 뒤 AST 방식으로
다시 했다.** 문장 경계를 추정하면 안 되는 작업이었다.

## 자산별 판단

| 자산 | 판정 | 근거 |
| --- | --- | --- |
| `skills.json` 의 `memory_skills` 항목 | **유지** | skill **registry** 데이터이지 memory_skills 기능군이 아니다. registry 는 이번 범위 밖(D6 미결) |
| `memoryCopyFallback` DOM id | **유지** | 이름만 memory 일 뿐 여러 기능이 공유하는 범용 복사 fallback |
| master-plan 5절 `Memory / Skills` workstream 행 | **유지** | project_control 은 이번 범위 유지(D4 미결)이고 파서가 6행 고정 이름을 요구한다 |

## UI 제거가 강제한 범위 밖 접촉 3곳

콘솔 UI 에서 memory 코드를 지우면 **남겨두는 것이 더 나쁜** 상태가 된다 — 사라진 함수를
호출하는 코드가 남기 때문이다. 그래서 제거했고, 그 과정에서 불가피하게 세 곳을 건드렸다.

1. Voice Inbox 의 skill-detail 카드에서 `memory_skills` 분기 — 사라진 두 함수를 호출했다
2. skill registry 의 `renderSkillDetails("memory_skills", "memory")` — 대상 탭이 없어졌다
3. 추천 목록의 "Repeated workflow -> Memory / Skills" 한 줄

**세 곳 모두 죽은 참조를 지운 것이고 다른 기능의 동작을 바꾸지 않는다.**

## 검증

| 검증 | 결과 |
| --- | --- |
| **신규 심볼** | `run_web_app` **0개**, `run_smoke_tests` **0개** (제거만 113개) |
| 라우트 | `/api/memory-skills` **404**, preview **404** / `/api/overview`·`/api/status`·`/api/skill` **200** |
| `jarvis-console` 스모크 + browser shell self-test | **PASS** |
| `bot_minimal` self-check | **92/92 PASS** |
| canonical 전수 | **64/64 PASS** |
| `discord-intake` | **87/87 PASS** |
| `audit-chain` | **7/7 PASS** |
| `discord-nl-intent` | 35/35 PASS |
| `buzz-bridge` | **37/37 PASS** |
| `validate_multi_agent_sop` | `status=PASS` |
| `check_no_secrets --self-test` | `status=PASS` |
| `node --check web/app.js` | OK |
| master-plan 파서 | 전/후 **PASS**, `next_user_visible_milestone` 58 -> 115 (상한 500) |
| `git diff --check` | clean |

`git diff` 는 대규모 삭제 탓에 재정렬 artifact 로 2,732 개의 `+` 줄을 보여주지만,
**AST 로 대조한 신규 심볼은 0개**다.

## 줄 수

| 파일 | 전 | 후 | 증감 |
| --- | --- | --- | --- |
| `run_web_app.py` | 10,321 | 5,824 | **-4,497** |
| `run_smoke_tests.py` | 8,750 | 7,818 | -932 |
| `web/app.js` | 3,992 | 3,614 | -378 |
| `web/styles.css` | 1,364 | 1,302 | -62 |
| `web/index.html` | 248 | 233 | -15 |
| 합계 | 24,675 | 18,791 | **-5,884** |

## master-plan D1 반영

117행과 173행의 "Jarvis 전용 **승인 화면**으로 축소"를 **"Jarvis task lifecycle 화면"**으로
정정했다. task-0063 이 확인한 대로 **콘솔은 승인 전이를 수행할 수 없고**(`TODO -> DOING`,
`DOING -> DONE` 둘뿐), D1 이 `NEEDS_APPROVAL` 추가를 배제했으므로 기존 문구는 없는 기능으로
축소하라는 말이 된다.

## 이번 단계 비범위

- `task_lifecycle`·`overview_status`·`project_control` — 무변경(Owner 지시)
- `skill_registry`(1,564줄)·`evaluate_idea`·`codex_review`·`voice_inbox` — D6 미결
- `skills.json` — registry 자산이라 유지
- Console 외 앱 — `hermes-manager-pilot` 이 Memory/Skills 를 문구로 언급하나 별개 앱이라 무변경
- `jarvis.bat` — 건드리지 않았다
