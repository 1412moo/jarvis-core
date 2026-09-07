# task-0073-console-codex-review-removal

- id: `task-0073-console-codex-review-removal`
- title: `Jarvis Console 축소 2단계 — codex_review adapter 제거 (D6-a)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-07 06:36 UTC`
- updated_at: `2026-09-07 06:36 UTC`
- summary: `D6-a 결정에 따라 Console 의 codex_review adapter 를 제거했다. 구현은 처음부터 hermes-manager-pilot 소유였고 Console 고유 로직은 검증 함수 하나뿐이었으며 외부 소비자도 없었다. 삭제하자 앱이 import 조차 되지 않았는데, 그 파일이 hermes 를 sys.path 에 얹는 유일한 지점이었고 project_control 의 두 모듈이 거기 의존하고 있었다. 경로 설정을 run_web_app 상단으로 옮겨 해결했다. 658줄 감소, hermes 는 무변경, 전 회귀 통과.`
- source_command: `D6-a Owner 결정 — Console codex_review REMOVE`

## 기준선

HEAD `8d21efe` = `origin/main`. Console 6파일 수정 + 1파일 삭제.

## 근거 — 이미 adapter 였다

`codex_review.py` 자신의 첫 줄이 *"Write-free Jarvis Console **adapter** for one fresh
Hermes review session"*이고, `hermes_manager_pilot`의 네 모듈(`approval_binding`,
`change_evidence`, `prompt_queue`, `schemas`)에서 구현을 전부 가져다 썼다. Console 고유
로직은 `_validate_pre_collection_review()` 하나와 응답 포맷팅뿐이었다.

hermes-manager-pilot 은 자체 웹 UI 로 전체 리뷰 워크플로를 제공한다("Copy Review Prompt",
"Save Review Object" 등). 외부 소비자는 0이었다.

## 제거 내역

| 대상 | 내용 |
| --- | --- |
| `codex_review.py` | **파일 삭제**(200줄) |
| `run_web_app.py` | import 1, 라우트 2줄, do_POST allowlist 1, self-test 단언 8 |
| `run_smoke_tests.py` | `import codex_review`, `_create_codex_review_fixture`(66줄), `_test_codex_review_vertical_slice`(117줄), `main()` 호출 1 |
| `web/app.js` | `renderCodexReview`·`renderCodexReviewFailure`·`loadCodexReview` 3함수, DOM 참조 4, 리스너 1 |
| `web/index.html` | 탭 버튼 + `#tab-codex-review` 패널 |
| `web/styles.css` | `.codex-review-*` 규칙 (공유 규칙 2개 제외) |
| `README.md` | 기능 목록 2항목, `### Codex Review` 절, 설계 문서 링크 2, 안전 원칙 1항목 |

## 🔴 삭제가 드러낸 숨은 의존 — sys.path

`codex_review.py` 는 adapter 이면서 동시에 **hermes-manager-pilot 을 `sys.path`에 얹는
유일한 지점**이었다. 파일을 지우자 `run_web_app.py` 가 import 조차 되지 않았다.

```
ModuleNotFoundError: No module named 'hermes_manager_pilot'
  run_web_app.py:40  from hermes_manager_pilot.director_reporting import ...
```

`director_reporting`·`manager_reporting_data` 는 **project_control(KEEP)** 소속이라 이
경로 설정은 살아 있어야 한다. 한 기능의 모듈이 다른 기능의 전제를 세우고 있었던 셈이라,
경로 설정을 `run_web_app.py` 상단으로 옮기고 그 이유를 주석에 남겼다. `APP_ROOT` 정의보다
앞이라 `Path(__file__)` 기준으로 썼다.

**이것이 이번 작업에서 KEEP 영역을 건드린 유일한 지점이며, 건드리지 않으면 앱이 뜨지
않는다.**

## 공유 자산은 남겼다

`.codex-review-status` CSS 클래스는 `renderProjectControl`(project_control, KEEP)이
`app.js:2748`에서 쓴다. 이 클래스를 포함한 CSS 규칙 **2개는 통째로 유지**했다. 결과적으로
`.codex-review-json` 셀렉터가 죽은 채 남지만, 규칙을 쪼개면 KEEP 영역을 건드리게 되어
그대로 뒀다.

`docs/codex-review-*-design.md` 두 문서는 **삭제하지 않았다** — 역사 기록이고 README 의
링크만 걷어냈다.

## 검증

| 검증 | 결과 |
| --- | --- |
| 라우트 | `/api/codex-review/preview` **404** / `/api/evaluate-idea` 400(정상 검증) / `/api/status`·`/api/skill` **200** |
| `jarvis-console` 스모크 + browser shell self-test | **PASS** |
| **`hermes-manager-pilot` 스모크** | **PASS** — 무변경 확인 및 sys.path 이관 후에도 정상 |
| canonical 전수 | **65/65 PASS** |
| `bot_minimal` self-check | **92/92 PASS** |
| `discord-intake` | **88/88 PASS** |
| `audit-chain` | **PASS** |
| `buzz-bridge` | **37/37 PASS** |
| `discord-nl-intent` | 35/35 PASS |
| `validate_multi_agent_sop` | `status=PASS` |
| `check_no_secrets --self-test` | `status=PASS` |
| `node --check web/app.js` | OK |
| `git diff --check` | clean |

## 줄 수

| 파일 | 전 | 후 | 증감 |
| --- | --- | --- | --- |
| `codex_review.py` | 200 | **삭제** | −200 |
| `run_smoke_tests.py` | 7,818 | 7,633 | −185 |
| `web/app.js` | 3,614 | 3,472 | −142 |
| `web/styles.css` | 1,302 | 1,230 | −72 |
| `README.md` | 515 | 481 | −34 |
| `web/index.html` | 233 | 213 | −20 |
| `run_web_app.py` | 5,824 | 5,819 | −5 |
| 합계 | 19,506 | 18,848 | **−658** |

`run_web_app.py` 가 −5 뿐인 것은 라우트·import 만 지우고 sys.path 6줄을 새로 넣었기
때문이다. 실제 삭제는 adapter 파일과 테스트·UI 쪽에 몰려 있다.

## 잔여 참조

| 잔여 | 유지 근거 |
| --- | --- |
| `.codex-review-status` (app.js, styles.css) | project_control 이 쓰는 **공유 클래스** |
| `run_web_app.py:40` 주석 | sys.path 이관 이유 설명 |
| `docs/codex-review-*-design.md` | 역사 설계 문서 |
| README 458행 부근 Hermes 관련 문구 | codex_review 기능이 아니라 Hermes 탭 안내 |

실행·라우팅 참조는 **0건**이다.

## 이번 단계 비범위

- `hermes-manager-pilot` — 무변경(`git status` 확인)
- `task_lifecycle`·`overview_status`·`project_control`·`skill_registry`·`evaluate_idea` — 무변경
- `memory_skills` — task-0071 에서 이미 제거, 재차 건드리지 않음
- D6-b(`evaluate_idea`)·D6-c(`skill_registry`) — 미결
- `jarvis.bat` — 건드리지 않았다
