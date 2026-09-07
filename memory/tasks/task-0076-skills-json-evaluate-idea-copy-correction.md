# task-0076-skills-json-evaluate-idea-copy-correction

- id: `task-0076-skills-json-evaluate-idea-copy-correction`
- title: `skills.json 의 research_council 카드에서 제거된 Evaluate Idea 안내 정정`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-07 09:52 UTC`
- updated_at: `2026-09-07 09:52 UTC`
- summary: `task-0075 가 Evaluate Idea 를 제거했는데 skill registry 의 research_council 카드가 여전히 그 화면으로 사용자를 안내하고 있었다. 표시 전용 텍스트라 기능 의존은 0이지만 없는 UI 를 지시하는 오정보였다. 문구 3건을 제자리에서 치환했다 — 배열 길이를 바꾸면 위치 경로로 대조하는 copy-drift 가드가 통째로 깨지기 때문이다. 테스트는 replacement 쪽 3건만 갱신해 기준선 대조와 바이트 복원 비교를 그대로 남겼다. 2파일 +9 -10, 전 회귀 통과.`
- source_command: `task-0075 후속 — skills.json 잔여 Evaluate Idea 문구 정정 지시`

## 기준선

HEAD `5525605` = `origin/main`. 2파일, **+9 / -10**.

## 무엇이 틀려 있었나

task-0075 가 Console 에서 Evaluate Idea 를 전면 제거했는데, skill registry 의
`research_council` 카드가 여전히 그 화면으로 사용자를 안내하고 있었다. task-0074 의
`memory_skills` 유령 항목과 **같은 종류의 오정보**이고 크기만 작다.

문구는 코드가 파싱하거나 분기하지 않는 **표시 전용 텍스트**다. 기능 의존은 0이지만,
**존재하지 않는 UI 를 사용자에게 지시**한다.

## 정정한 문구 3건

| 위치 | 전 | 후 |
| --- | --- | --- |
| `action_guide[4]` | In Jarvis Console, review a successful Evaluate Idea recommendation before using Preview as Local Task. | Review the evidence gaps, risks, and minimum experiments in the launcher output. |
| `action_guide[5]` | Review the local TODO preview, then explicitly Confirm Create Local Task if the handoff is correct. | Bring any follow-up work into Jarvis yourself; the console creates no Task from this report. |
| `safety_notes[1]` | Jarvis Console does not run Research Council automatically; Evaluate Idea and Preview as Local Task are write-free, and only explicit Confirm Create Local Task writes one local TODO. | Jarvis Console does not run Research Council and creates no Task from its report. |

`action_guide[5]` 도 함께 고친 이유는, 그 "handoff" 가 Evaluate -> task 초안 경로를 가리켰고
그 경로가 사라졌기 때문이다. 남겨두면 [4] 만 고치고 [5] 가 없는 흐름을 계속 지시한다.

## 배열 길이를 바꾸지 않은 이유

`_test_tasks_reports_registry_copy` 는 레지스트리의 **모든 문자열을 위치 경로로** 기준
커밋과 대조한다. 항목을 삭제하면 이후 모든 인덱스가 밀려 그 가드 전체가 깨진다.
**제자리 치환**이 이 작업의 최소 diff 이자 최소 위험이다.

## 테스트 — 가드를 약화시키지 않았다

같은 테스트의 `replacements` 표에서 **`replacement` 쪽 3건만** 새 문구로 갱신했다.
기준선(`obsolete`) 쪽과 바이트 단위 복원 비교는 **손대지 않았다.** 따라서 이 파일이
기준 커밋과 "승인된 문구 교체 외에는 완전히 동일하다"는 보장이 그대로 유지된다.

테스트가 함께 확인하는 것: 기준선 문구가 현재 파일에 없을 것, 새 문구가 정확히 1회
등장할 것, 교체를 되돌리면 기준선 바이트와 일치할 것.

## 검증

| 검증 | 결과 |
| --- | --- |
| `jarvis-console` 스모크 + browser shell self-test | **PASS** |
| copy-drift 테스트 | **PASS** (가드 강도 유지) |
| canonical 전수 | **69/69 PASS** |
| `validate_multi_agent_sop` | `status=PASS` |
| `bot_minimal` self-check | **92/92 PASS** |
| `discord-intake` | **92/92 PASS** |
| `audit-chain` | PASS |
| `buzz-bridge` | failed 0 |
| `discord-nl-intent` | 35/35 PASS |
| `check_no_secrets --self-test` | `status=PASS` |
| `node --check web/app.js` | OK |
| `git diff --check` | clean |

## 남은 Evaluate 참조와 이유

| 잔여 | 이유 |
| --- | --- |
| `skills.json:15` `short_description` "Evaluate ideas, evidence gaps, risks..." | **Research Council 앱 자체의 목적** 설명이다. 제거된 Console 기능이 아니며, Owner 가 Research Council 설명은 변경하지 말라고 지정했다 |
| `README.md:296` "Purpose: evaluate ideas..." | 동일 — 앱 설명 |
| `run_web_app.py:303`, `run_smoke_tests.py:3037` | completion evidence 문구("does not evaluate whether verification evidence exists"). 무관 |
| `run_web_app.py:2050` | task-0075 가 남긴 설명 주석 |

**Console 기능으로서의 Evaluate Idea 를 가리키는 참조는 0건이다.**

## 이번 단계 비범위

- `run_web_app.py` · `web/app.js` · `index.html` · `styles.css` — 무변경
- skill_registry 구조 · Research Council · hermes-manager-pilot — 무변경
- `research_council` 카드의 설명 · 명령 · 라우팅 metadata — 무변경
- D6-c(skill_registry 존폐) — DEFER 유지
- `jarvis.bat` — 건드리지 않았다
