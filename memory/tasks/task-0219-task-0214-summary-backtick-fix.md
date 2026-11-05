# task-0219-task-0214-summary-backtick-fix

- id: `task-0219-task-0214-summary-backtick-fix`
- title: `task-0214 기록 summary의 백틱 제거`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-11-05 16:27 UTC`
- updated_at: `2026-11-05 16:44 UTC`
- summary: `task-0214 기록의 summary 끝에 candidate 해시를 감싼 백틱 두 개가 있어 writer와 Console 파서가 그 기록을 invalid로 읽고, discord-intake smoke의 저장소 기록 검사와 그 smoke를 쓰는 Discord self-check가 실패한다. 그 두 백틱만 지운다. 다른 문구, 다른 필드, 코드는 바꾸지 않고 push는 하지 않는다.`
- completion_evidence: `candidate de0b0b3353b000f37b05ba85e8bf6d7df15fdb42: Reviewer PASS (no findings), QA PASS (intake smoke rc=0, Discord self-check-suite rc=0, Console smoke, validator, preflight, task-0214 parses valid)`
- source_command: `Owner 지시: 고쳐줘 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `dc20165f9f97ccba28b3ae932bd12e8a1333f650` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문)

```text
[Manager 질문]
task-0214 summary 백틱을 고칠까요?

[Owner 답]
고쳐줘
```

직전 Manager 보고(Owner 원문 아님): discord-intake smoke와 Discord self-check는 task-0214 기록의 summary에 든 백틱 때문에 아직 실패하며, 이걸 고치면 두 검사가 다시 통과할 것으로 예상한다.

## 조사 (baseline 기준)

- task-0214 summary 줄의 끝에 "(candidate `20d9b15`)"가 있다. 메타데이터 값 안에 백틱이 들어 있어 `task_file_writer._transition_metadata`는 `task_file_invalid_metadata`를, Console `parse_task_view_text`는 `invalid`를 돌려준다. 이 문구는 task-0214 DONE checkpoint(`951b056`) 때 들어갔다.
- 그 결과 `orchestrator/discord-intake/run_smoke_tests.py`의 저장소 기록 검사 209건 중 `repo_task_validation:task-0214-console-name-rule-hidden-count.md` 1건이 실패하고(rc=1), 이 smoke를 허용 목록 실행으로 쓰는 Discord `--self-check-suite`가 109건 중 6건 실패한다(rc=1). task-0218 기록의 조사 절과 QA 결과 절이 같은 실패를 적었다. 그 기록의 "백틱 4개"는 값 전체를 감싸는 백틱 두 개를 함께 센 수이고, 값 안에 든 것은 이 두 개다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `memory/tasks/task-0214-console-name-rule-hidden-count.md`(summary 줄의 백틱 두 개만), 이 task 기록 |
| deny | task-0214의 다른 문구·필드(updated_at 포함), 다른 task 기록, 코드, 검사기, `jarvis.bat`, `.env`, push |

## Start

Console Create Local Task Preview를 확인하고 Confirm해 TODO 기록을 만들었다. Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다(updated_at `2026-11-05 16:28 UTC`). 그 전에 한 번은 잘못된 화면 요소를 눌렀고 한 번은 Confirm 전에 Console을 꺼서 Start가 반영되지 않았다. 둘 다 파일을 바꾸지 않았음을 git status로 확인했다. Console은 수정 전에 껐다. 그 뒤 title·summary·source_command를 이 task 내용으로 고쳤다.

## 구현

- task-0214 summary의 "(candidate `20d9b15`)"를 "(candidate 20d9b15)"로 바꿨다. 줄 하나, 백틱 두 개만 바뀐다.
- task-0214의 `updated_at`은 바꾸지 않았다. task-model 7절은 "단순 포맷 정리는 팀 규칙에 따라 생략할 수 있다"고 하며, 이를 정한 팀 규칙 문서는 없다. 뜻이 바뀌지 않는 형식 정리이고 Owner 질문이 summary 백틱으로 한정됐으며 범위 표가 updated_at을 deny로 두었으므로, 갱신하지 않은 것은 Manager 판단이다.

## Implementer 검증 (작업 트리)

- 바뀐 task-0214는 writer 파서(오류 없음)와 Console 파서(`valid`)가 모두 읽는다.
- discord-intake smoke(PYTHONUTF8=1) rc=0, Discord `--self-check-suite`(PYTHONUTF8=1) rc=0.

## Self-review

staged 변경에 self-reviewer를 한 번 돌렸다(Reviewer 판정 아님). minor 두 건과 처리:

1. task-model 7절 인용이 원문과 달랐다("팀 규칙에 따라"가 빠짐). 원문대로 고치고, 그 팀 규칙 문서가 없어 updated_at을 두는 것이 Manager 판단임을 구현 절에 적었다.
2. "task-0218 기록 조사 절에 같은 사실이 있다"가 넓었다(그 조사 절은 "백틱 4개"라 하고 109건은 QA 결과 절에 있다). 조사 절과 QA 결과 절을 함께 가리키고 4개와 2개의 차이를 적었다.

수정 뒤 사전 점검(`check_task_record.py --require-quotes`) 결과는 candidate 직전 실행과 같다(PASS, violations 0).

## Reviewer 결과 (candidate `de0b0b3353b000f37b05ba85e8bf6d7df15fdb42`)

verdict PASS, findings 없음, self_deviations 없음. Reviewer의 unverified 항목(파서·smoke·self-check 결과, preflight)은 QA에서 확인했다.

## QA 결과 (같은 candidate)

- scratchpad의 새 detached worktree(`core.autocrlf=true`)를 candidate에 두고 돌렸다. HEAD = candidate, 작업 트리 깨끗, `jarvis.bat` 트리에 없음.
- 변경 파일은 task-0214 기록과 이 기록 둘이고, task-0214는 summary 한 줄만 바뀌었다. `git diff --check` 통과, 사전 점검 PASS, SOP validator PASS.
- discord-intake smoke(PYTHONUTF8=1) rc=0, Discord `--self-check-suite`(PYTHONUTF8=1) rc=0, Console smoke rc=0. Console 파서가 task-0214를 `valid`로 읽는다. QA worktree는 지웠다.
- QA 판정: PASS. Docs는 `not_required`.

## Owner 결정 (원문, Complete)

```text
[Manager 질문]
task-0219: candidate de0b0b3에 Reviewer PASS(지적 0건)가 나왔고 QA도 PASS입니다. intake smoke와 Discord self-check가 다시 통과(rc=0)하고, Console smoke·validator·preflight도 통과했으며, task-0214는 Console에서 valid로 읽힙니다. Completion Evidence를 기록하고 Console Complete(DOING → DONE)를 실행한 뒤, DONE checkpoint와 master-plan 날짜 항목을 로컬에 커밋할까요? push는 하지 않습니다.

[Owner 답]
Complete 진행 (Recommended)
```

## Complete

Record Completion Evidence(Preview 확인 뒤 Confirm)로 completion_evidence를 남긴 뒤, Owner 결정에 따라 Console Complete Preview(DOING → DONE)를 확인하고 `Confirm Complete`로 DONE이 됐다(updated_at `2026-11-05 16:44 UTC`). Console은 끈 상태다. push는 하지 않았다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다. 오른쪽 칸에서 "Manager 해석"이라고 적은 부분은 승인 원문에 없는 내용이다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 질문]" | 질문의 표지 |
| A2 | Owner 결정 (원문) | "task-0214 summary 백틱을 고칠까요?" | A4 답의 질문. 범위는 summary의 백틱이다 |
| A3 | Owner 결정 (원문) | "[Owner 답]" | 답의 표지 |
| A4 | Owner 결정 (원문) | "고쳐줘" | 착수 승인. task-0214 summary의 백틱 두 개만 지웠다(구현 절). Manager 해석: 다른 문구와 updated_at은 질문 밖이라 그대로 두었다 |
| A5 | Owner 결정 (원문, Complete) | "[Manager 질문]" | 질문의 표지 |
| A6 | Owner 결정 (원문, Complete) | "task-0219: candidate de0b0b3에 Reviewer PASS(지적 0건)가 나왔고 QA도 PASS입니다." | A11 답의 질문 배경. Reviewer·QA 결과 절과 같다 |
| A7 | Owner 결정 (원문, Complete) | "intake smoke와 Discord self-check가 다시 통과(rc=0)하고, Console smoke·validator·preflight도 통과했으며, task-0214는 Console에서 valid로 읽힙니다." | A11 답의 질문 배경. QA 결과 절과 같다 |
| A8 | Owner 결정 (원문, Complete) | "Completion Evidence를 기록하고 Console Complete(DOING → DONE)를 실행한 뒤, DONE checkpoint와 master-plan 날짜 항목을 로컬에 커밋할까요?" | A11 답의 질문 |
| A9 | Owner 결정 (원문, Complete) | "push는 하지 않습니다." | A11 답의 질문 조건 |
| A10 | Owner 결정 (원문, Complete) | "[Owner 답]" | 답의 표지 |
| A11 | Owner 결정 (원문, Complete) | "Complete 진행 (Recommended)" | Console로 Completion Evidence를 남기고 Complete했다(Complete 절). checkpoint와 날짜 항목은 로컬 커밋만 하고 push하지 않는다 |
