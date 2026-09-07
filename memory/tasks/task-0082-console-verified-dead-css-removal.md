# task-0082-console-verified-dead-css-removal

- id: `task-0082-console-verified-dead-css-removal`
- title: `Console 검증된 dead CSS 제거 (2단계)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-08 00:55 UTC`
- updated_at: `2026-09-08 00:55 UTC`
- summary: `task-0080 에서 REMOVE-SAFE 로 증명된 CSS 26줄만 제거했다. severity 계열 5개 selector 는 블록째 지웠고 codex-review-json 과 codex-review-summary p 는 selector 줄만 지웠다 — 두 블록을 codex-review-status 와 공유하기 때문이다. codex-review-status 는 project_control 의 Working tree 표시에서 실사용 중이라 보존했고 브라우저에서 해당 element 에 폰트와 overflow-wrap 이 실제로 적용되는지 무클래스 대조군과 비교해 확인했다. 1파일 +0 -26, CSS 외 변경 0건.`
- source_command: `task-0080 감사 결과 CSS REMOVE-SAFE 항목 제거 지시`

## 기준선

HEAD `15d9c0b` = `origin/main`, tracked 변경 0에서 시작.
1파일, **+0 / -26**. 순수 삭제.

## 제거 내용

### A — severity 계열 (24줄, 블록째)

`.severity-badge` / `.severity-low` / `.severity-medium` / `.severity-high` /
`.severity-unknown` 및 각 declaration. 구분 공백줄 1개 포함.

task-0073 의 codex_review 심각도 배지 잔재다. project_control 페이로드에도
`severity` 값이 있지만 `app.js` 는 이를 `<code>` **텍스트 내용**으로만 렌더하고
class 를 생성하지 않는다. 실제 값 `blocking` 에 대응하는 규칙이 애초에 없다는 점도
이들이 project_control 것이 아님을 뒷받침한다.

### B — codex-review dead selector (2줄, selector 줄만)

`.codex-review-json,` 와 `.codex-review-summary p,` 두 줄만 제거했다.
블록 자체는 `.codex-review-status` 와 selector 를 공유하므로 남겨야 한다.

## 보존 — `.codex-review-status`

`app.js:1791` 에서 project_control 카드의 Working tree 값이
`<code class="codex-review-status">` 로 렌더된다. 이름은 codex_review 잔재지만
스타일은 KEEP 영역에서 살아 있다. 제거했으면 Working tree 표시가 깨졌다.

## 정적 검증

| 항목 | 결과 |
| --- | --- |
| 제거 대상 7개 selector 가 `styles.css` 에 남아 있는지 | 각 **0건** |
| `.codex-review-status` 존치 | `styles.css:1007`, `:1011` 2건 |
| 제거 selector 를 참조하는 JS/HTML/py 코드 | `app.js` `index.html` `run_web_app.py` `run_smoke_tests.py` 전부 **0건** |
| diff 범위 | `styles.css` 1파일, 26 deletions, 0 insertions |
| line ending | LF 유지 (1125 → 1099줄) |

## 브라우저 검증 — Working tree 표시

`.codex-review-status` 가 **실제로 스타일을 적용받는지**를 클래스 없는 `<code>`
대조군과 비교해 확인했다. selector 가 존재한다는 것만으로는 증거가 되지 않는다.

| 항목 | 값 |
| --- | --- |
| Working tree element 발견 | 예 (`<dt>Working tree</dt>` 옆) |
| `font-family` | `SFMono-Regular, Consolas, monospace` |
| 대조군 `<code>` `font-family` | `monospace` |
| `overflow-wrap` | `anywhere` |
| 대조군 `overflow-wrap` | `normal` |
| **스타일 실제 적용 여부** | **true** |
| 로드된 stylesheet 의 `.codex-review-status` 규칙 수 | 2 |
| `severity-*` / `codex-review-json` / `codex-review-summary` 규칙 잔존 | **0** |

추가로 8개 탭 전부 렌더, overview-card 10개, Actionable Task View 정상,
risk 목록 렌더, task-0079 manual copy fallback 존치, **console error 0건**.

## 검증 결과

| 검증 | 결과 |
| --- | --- |
| Console self-test | PASS |
| Console smoke + browser shell | PASS |
| `/api/status` | PASS (skills 5) |
| `/api/overview` | PASS (`project_control.v0.1F`, card status=attention) |
| project_control 표시 | PASS (Working tree 스타일 적용 확인) |
| canonical 전수 | 72/72 PASS |
| SOP | status=PASS |
| bot self-check | 92/92 PASS |
| discord-intake | 95/95 PASS |
| audit-chain | 7 passed, 0 failed |
| buzz-bridge | 37/37 PASS |
| discord-nl-intent | 35/35 PASS |
| check_no_secrets --self-test | failures=0, PASS |
| node --check | OK |
| git diff --check | clean |

## 무변경 확인

`run_web_app.py`, `run_smoke_tests.py`, `app.js`, `index.html`, README,
master-plan, docs, skill registry, Research Council, Hermes, Discord,
audit-chain 전부 무변경.

task-0083 대상(`filesystem_stat_is_reparse_point`, `normalize_filesystem_path`,
`is_path_inside_repo`, `import stat`, 관련 self-test assert)과
기존 미사용 import 13건, 항진 assert, `.jarvis-local` 중복 검사도 손대지 않았다.
