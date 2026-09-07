# task-0079-console-manual-copy-fallback-restoration

- id: `task-0079-console-manual-copy-fallback-restoration`
- title: `Console 수동 복사 fallback 복구`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-08 00:20 UTC`
- updated_at: `2026-09-08 00:20 UTC`
- summary: `task-0071 이 memory_skills UI 를 지우면서 fallback markup 과 그것을 띄우던 두 버튼이 함께 사라져 showManualCopyFallback 이 항상 false 를 반환하고 있었다. 원본은 memory_skills 뷰 안에서만 렌더되는 구조였으므로 그대로 되살리면 memory_skills 복원이 된다. 대신 기능 중립적인 이름의 정적 패널을 status 패널에 두어 모든 탭에서 동작하게 했고 살아남은 copy 버튼들을 연결했다. 브라우저에서 clipboard 성공·실패 경로를 실제로 구동해 검증했고 같은 방식으로 다시 깨지지 않도록 self-test 가드를 추가했다. 4파일 +42 -5.`
- source_command: `task-0077 감사 결과 C-2 — manual copy fallback 복구 지시`

## 기준선

HEAD `cc73971` = `origin/main`. 4파일, **+42 / -5**.

## 원본 구조 (`8d21efe^`)

`memoryCopyFallback` 은 **`index.html` 에 존재한 적이 없다.**
`git log -S` 로 확인 — 이 문자열은 `index.html` 이력에 0건, `app.js` 이력에만 있다.

실제 구조는 memory_skills 뷰의 `innerHTML` 안에서 렌더되는 markup 이었다
(`old_app.js:2712`, "Sample Candidates" `overview-card` 내부).
그리고 `data-manual-copy-label` 을 넘기던 버튼은 **memory_skills 의 2개뿐**이었다
(`Copy Candidate`, `Copy Skill Draft Prompt`, `old_app.js:2645-2646`).

즉 fallback 은 처음부터 memory_skills 전용이었고, 다른 탭의 Copy 버튼에는
task-0071 이전에도 fallback 이 없었다.

## 현재 문제 원인

task-0071 이 뷰와 버튼을 지우면서 markup 과 label 공급원이 함께 사라졌고
`app.js` 의 `getElementById` 두 줄만 남았다. 결과:

- `showManualCopyFallback()` 은 항상 `false`
- clipboard 실패 시 사용자는 선택 가능한 textarea 대신 `Copy failed: ...` 문구만 받는다
- plain HTTP / non-secure context 에서 Console 의 유일한 handoff 수단인 Copy 가 막힌다

## 구현

원본을 그대로 복원하면 memory_skills UI 복원이 되므로 그렇게 하지 않았다.

1. `index.html` — status 패널 안에 **정적** 패널 추가.
   탭에 종속되지 않으므로 모든 탭의 Copy 버튼이 쓸 수 있다.
   id 는 `manualCopyFallback` / `manualCopyFallbackText` / `manualCopyFallbackClose`
   로 기능 중립적으로 지었다. `memory` 이름은 되살리지 않았다.
2. `app.js` — 두 lookup 을 새 id 로 교체, `setSelectionRange(0, length)` 추가,
   닫기 버튼 연결.
3. `app.js` — `copyCommand()` 실패 경로를 fallback 에 연결했다.
   Console 의 Copy 버튼 대부분이 `.copy-command` 이고 이 경로에는 원래 fallback 이
   전혀 없었다. 이걸 빼면 살아남은 버튼 2개만 복구되고 목적을 못 채운다.
4. `app.js` — `.copy-text` 핸들러가 `data-manual-copy-label` 부재 시
   버튼의 `aria-label` 을 쓰도록 했다. 살아남은 두 버튼은 그 속성이 없어서
   (브라우저에서 확인) 이것 없이는 label 이 빈 문자열이 되어 fallback 이 열리지 않는다.
5. `styles.css` — 닫기 버튼 정렬 1개 규칙만 추가.
   `.manual-copy-fallback` 스타일 본체는 task-0071 때 살아남아 원본과 identical 했다.
   `.codex-review-*` 등 무관한 dead selector 는 건드리지 않았다.

## 검증 — 실제 브라우저 구동

`http://localhost:8790` 에서 `navigator.clipboard` 를 stub 해 두 경로를 실제로 실행했다.

**A. clipboard 성공** — `.copy-command`, `.copy-text` 양쪽
clipboard 가 정확한 문자열 수신, fallback `display: none` 유지, 기존 status 문구 그대로.

**B. clipboard 실패** — `.copy-command`, `.copy-text` 양쪽
`display: grid` 로 표시, textarea 값이 대상 문자열과 정확히 일치(한글 포함),
`readOnly true`, `document.activeElement` 가 textarea, `selectionStart 0`
`selectionEnd = length` 전체 선택, 닫기 버튼으로 다시 숨김.

**C. DOM 회귀** — 8개 탭 전부 렌더, skill 카드 15개, skill detail copy 버튼 2개,
hermes/radar/settings 상세 렌더, Project Control 의 Actionable Task View 정상,
console error 0건.

## self-test 가드

같은 방식으로 다시 조용히 깨지지 않도록 `run_self_test` 에 가드를 넣었다 —
fallback 이 읽는 모든 id 가 `index.html` 에 실제로 존재하는지 검사한다.
task-0071 이 만든 파손이 정확히 이 검사에 걸린다.

임시 `WEB_ROOT` 사본으로 mutation probe 6종 수행, 실제 `web/` 파일은 byte-identical.

| probe | 결과 |
| --- | --- |
| 대조군 — 미변형 사본 | PASS |
| a. 패널 id 제거 | PASS |
| b. textarea id 제거 | PASS |
| c. 닫기 버튼 id 제거 | PASS |
| d. `app.js` lookup 제거 | PASS |
| e. `readonly` 제거 | PASS |

## 검증 결과

| 검증 | 결과 |
| --- | --- |
| Console self-test | PASS |
| Console smoke + browser shell | PASS |
| canonical 전수 | 70/70 PASS |
| SOP | status=PASS |
| bot self-check | 92/92 PASS |
| discord-intake | 93/93 PASS |
| audit-chain | 7 passed, 0 failed |
| buzz-bridge | 37/37 PASS |
| discord-nl-intent | 35/35 PASS |
| check_no_secrets | self-test PASS, 전수 비-fixture 0건 |
| node --check | OK |
| git diff --check | clean |
| fallback guard probe | 6/6 PASS |

## 부수 발견

`app.js:19` 의 `const researchDetails = document.getElementById("researchDetails")`
는 task-0075 가 Evaluate Idea 패널을 지우면서 남긴 고아다. 선언 외 사용처가 없다.
task-0077 의 dead code 목록에 없던 항목이므로 여기 기록만 하고 제거하지 않았다
(이번 작업은 dead-code cleanup 금지).
