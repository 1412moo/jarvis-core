# task-0210-master-plan-baseline-refresh

- id: `task-0210-master-plan-baseline-refresh`
- title: `master-plan 기준점과 Owner Dashboard 현재 줄 갱신`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-30 13:56 UTC`
- updated_at: `2026-10-30 14:04 UTC`
- summary: `docs/master-plan.md §2 현재 기준점이 2026-07-23(Verified implementation HEAD 7d4394e)에 멈춰 Console Project Control 카드가 7~9월 상태를 보인다. §2의 설명 필드 일곱 개(Last verified, Verified implementation HEAD, Current workstream, Current milestone, Recommended next step, Next user-visible milestone, Recent completed)와 Owner Dashboard의 현재 줄 네 개를 2026-10-29(7b03f6f) 상태로 고친다. Approval state, Owner decision, Manager reporting 필드와 보류 결정은 바꾸지 않고 push는 하지 않는다.`
- source_command: `Owner 지시: 다음 단계 후보 1 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `7b03f6f0f39b23959e95925405f0e2e86248c2a1` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문)

```text
[Manager 제안: 다음 단계 후보]
| **1 (추천)** | **master-plan 기준점(§2)과 Owner Dashboard 갱신** | Console Project Control 카드와 Dashboard가 지금 상태(10월 작업, 다음 결정)를 보여 줍니다. | 중간. 문서만 바꾸지만 Console 파서와 validator가 §2 필드를 읽고, `Verified implementation HEAD`는 Git 이력 검사를 받습니다. 그래서 smoke와 validator로 확인해야 합니다. |

[Owner 답]
1 기준점 갱신
```

## Owner 결정 (원문, 착수 전 bounded question)

```text
[Manager 질문 1]
Verified implementation HEAD와 Last verified를 어느 시점으로 맞출까요?

[Owner 답 1]
7b03f6f, 2026-10-29 (Recommended)

[Manager 질문 2]
어느 부분까지 갱신할까요?

[Owner 답 2]
§2 설명 필드 + Dashboard 현재 줄 (Recommended)
```

선택지 설명(Manager가 질문과 함께 보인 문구, Owner 원문 아님):

- 답 1: "지금 main이자 origin/main입니다. task-0209 QA까지 끝난 상태로, 이번 task의 baseline입니다."
- 답 2: "§2의 Last verified, Verified HEAD, Current workstream/milestone, Recommended next step, Next user-visible milestone, Recent completed와 Dashboard의 '현재 다음 작업·현재 사용자 체감 결과·다음 사용자 체감 milestone·현재 결정 필요' 줄만 고칩니다. Approval state, Owner decision, Manager reporting 필드는 그대로 둡니다."

## 조사 (등록 전)

- Console(`apps/jarvis-console/run_web_app.py`)은 `## 2. 현재 기준점`의 `- <필드>: <값>` 줄을 `MASTER_PLAN_FIELDS`로 읽는다. 값은 백틱·`**`를 뗀 뒤 비어 있지 않고 500자 이하여야 하며, 빠지거나 중복되면 Project Control이 실패한다.
- `Verified implementation HEAD`는 현재 branch의 조상이어야 한다(`commit_is_branch_ancestor`, task-0126). 아니면 Manager Report가 blocked가 된다. `7b03f6f`는 main HEAD라 조건을 만족한다.
- validator(`scripts/validate_multi_agent_sop.py` `_validate_master_plan`)는 문서 어딘가에 옛 HEAD 문자열 `7d4394eed584bc11ee25062a671952b2e4c38b31`이 남기를 요구한다. 이 값은 Dashboard의 "최근 검증 결과" 줄에도 있어 §2 값을 바꿔도 남는다.
- 2026-10-29 기준 task 기록: DONE 153, CLOSED 3, ON_HOLD 5(Team Manager 보류, task-0156/0176), 그 밖 열린 task 없음.
- 문서에 적은 "남은 작은 후보"(FAILED Next action 문구 정정, 비밀 정보 검사기 전체 검사의 자체 견본 제외)는 이 task 직전 Manager의 읽기 전용 조사(2026-10-29, Owner에게 후보 표로 보고, 이 task는 그 표의 후보 1)에서 나왔다. 근거: `apps/jarvis-console/run_web_app.py` `TASK_VIEW_STATUS_RULES["FAILED"]`의 Next action "Review the summary and decide the recovery outside Jarvis Console.", `python -B scripts/check_no_secrets.py` 전체 검사의 findings 7건이 모두 `scripts/check_no_secrets.py:242-248` 자체 검사 견본(task-0206 기록에도 같은 사실). main에 없는 attempt branch 3개가 실패한 이전 시도이고 task-0209가 그 branch를 남겼다는 사실은 task-0209 기록에 있다. 그 삭제 여부를 남은 Owner 결정으로 적은 것은 같은 조사에서 Manager가 판단한 것이다(task-0209의 Owner 답은 "worktree만 정리"이고 branch 삭제는 그 task의 범위 밖이었다).
- "현재 사용자 체감 결과" 문장의 근거: Discord `/work`·`/go`와 Worker → Reviewer → QA → main 반영(SOP §10, task-0142/0148), `자비스,` 호출(task-0184), Task View 실행 결과·FAILED 사유와 조치·커밋 안 된 기록(task-0155/0207/0208), Start·Complete·Hold·Resume·Close(task-0173/0180/0206), 수동 SOP의 사전 점검·self-review(task-0171/0172).

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `docs/master-plan.md`(§2의 일곱 필드 값, Owner Dashboard의 네 줄), `memory/tasks/task-0210-master-plan-baseline-refresh.md` |
| deny | §2의 Branch·Known protected untracked file·Current goal·Manager reporting 세 필드·Current reason·Owner outcome·Approval state·Approval note·Owner decision 네 필드, master-plan의 다른 절과 날짜 항목, 코드·validator·다른 문서·다른 task 기록, `jarvis.bat`, push |

## 계획

1. Console Start(TODO → DOING).
2. 문서 갱신(값 길이 검사 포함).
3. 검사: Console smoke(PYTHONUTF8 없이·있이), SOP validator, `git diff --check`, 실제 Console Project Control 카드.
4. 사전 점검 → self-review → candidate → Reviewer → QA → Evidence·Complete → checkpoint. push는 별도 지시.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다(status·updated_at 줄만 바뀜, updated_at `2026-10-30 13:57 UTC`).

## 구현

`docs/master-plan.md`만 바꿨다(11줄 교체).

- §2 일곱 필드: `Last verified` `2026-10-29`, `Verified implementation HEAD` `7b03f6f0f39b23959e95925405f0e2e86248c2a1`, `Current workstream`·`Current milestone`·`Recent completed`는 task-0130 이후 task-0209까지의 Console·Worker·팀장·SOP 작업으로, `Recommended next step`은 같은 결정(다음 bounded package 제안 뒤 Owner 승인)과 보류 문장(②/④/⑤ 보류, task-0042가 ④ 착수를 승인하지 않음)을 그대로 두고 2026-10-29 조사로 남은 작은 후보와 attempt branch 3개 결정을 더해, `Next user-visible milestone`은 Close(task-0180/0206)를 더해 고쳤다. `Recent completed`는 500자 상한 때문에 대표 이력만 남겼다: Buzz Phase 1·Bridge와 감사 해시체인은 남기고, Manual Pilot v0.1A·Reviewer 규칙(task-0133~0136/0139)·Studyroom(task-0137/0138/0140)·기준 지도(task-0147) 등 task-0130 무렵 항목은 빼고 task-0142 이후 항목을 넣었다(뺀 항목은 Owner Dashboard 날짜 항목에 그대로 있다). 값 길이(백틱·`**` 제외)는 각각 10, 40, 423, 415, 439, 212, 488자로 Console 상한 500자 안이다.
- Owner Dashboard 네 줄: "현재 다음 작업"의 첫 문장, "현재 사용자 체감 결과" 전체, "다음 사용자 체감 milestone"의 첫 문장과 Console 쓰기 목록(Close 추가), "현재 결정 필요"의 첫 문장 뒤 attempt branch 결정 한 문장. 각 줄의 보류·잠금 문장은 그대로다.
- Approval state·Approval note·Owner decision·Manager reporting 필드와 다른 절은 바꾸지 않았다(diff 기준).

## Implementer 검증 (작업 트리)

- Console smoke(PYTHONUTF8 없이·있이) 통과, SOP validator PASS(옛 HEAD 문자열은 Dashboard "최근 검증 결과" 줄에 남음), `git diff --check` 통과.
- `read_master_plan_snapshot()`이 새 값을 읽고 `commit_is_branch_ancestor(7b03f6f…)`는 참이다. Manager Report는 `milestone_complete`, `source_conflicts` 없음.
- Project Control 카드 상태는 `attention`이며 이유는 Approval note 한 줄이다. 변경 전 문서로 계산해도 똑같아(같은 상태, 같은 이유) 이번 변경과 무관하다(Approval state `required`는 범위 밖).
- 실제 Console(127.0.0.1:8790): Project Control이 `HEAD 7b03f6f`와 새 Current milestone·Recommended next step을 보이고, 옛 HEAD `7d4394e`는 이 task 카드 summary에만 나온다. 콘솔 오류 없음. 서버는 껐다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다. 오른쪽 칸에서 "Manager 해석"이라고 적은 부분은 승인 원문에 없는 내용이며, 근거가 선택지 설명(Manager 문구, Owner 원문 아님)이거나 Manager 판단이다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 제안: 다음 단계 후보]" | 제안의 표지 |
| A2 | Owner 결정 (원문) | "\| **1 (추천)** \| **master-plan 기준점(§2)과 Owner Dashboard 갱신** \| Console Project Control 카드와 Dashboard가 지금 상태(10월 작업, 다음 결정)를 보여 줍니다." | §2 일곱 필드와 Dashboard 네 줄을 2026-10-29 상태로 고쳤고, Project Control 카드가 새 값을 보인다(Implementer 검증) |
| A3 | Owner 결정 (원문) | "\| 중간." | 제안이 적은 위험 등급. 조건이 아니다 |
| A4 | Owner 결정 (원문) | "문서만 바꾸지만 Console 파서와 validator가 §2 필드를 읽고, `Verified implementation HEAD`는 Git 이력 검사를 받습니다." | `docs/master-plan.md` 한 문서만 바꿨다(이 task 기록 제외). 값 길이 500자 상한, branch 조상 검사, validator의 옛 HEAD 문자열 요구를 모두 확인했다 |
| A5 | Owner 결정 (원문) | "그래서 smoke와 validator로 확인해야 합니다. \|" | Console smoke 두 방식과 SOP validator가 통과했다. Manager 해석: 실제 Console 화면 확인도 더했다 |
| A6 | Owner 결정 (원문) | "[Owner 답]" | 답의 표지 |
| A7 | Owner 결정 (원문) | "1 기준점 갱신" | 후보 1 착수 승인. 세부는 A11·A15의 답으로 정했다. Manager 해석: 범위 표 owned의 이 task 기록은 승인 원문에 이름이 없고, SOP 기록으로 Manager가 넣었다 |
| A8 | Owner 결정 (원문, 착수 전 bounded question) | "[Manager 질문 1]" | 질문의 표지 |
| A9 | Owner 결정 (원문, 착수 전 bounded question) | "Verified implementation HEAD와 Last verified를 어느 시점으로 맞출까요?" | A11의 질문 |
| A10 | Owner 결정 (원문, 착수 전 bounded question) | "[Owner 답 1]" | 답의 표지 |
| A11 | Owner 결정 (원문, 착수 전 bounded question) | "7b03f6f, 2026-10-29 (Recommended)" | `Verified implementation HEAD`를 `7b03f6f`의 40자 hash로, `Last verified`를 `2026-10-29`로 썼다. Manager 해석: 40자로 쓴 것은 기존 값 형식을 따른 것이다 |
| A12 | Owner 결정 (원문, 착수 전 bounded question) | "[Manager 질문 2]" | 질문의 표지 |
| A13 | Owner 결정 (원문, 착수 전 bounded question) | "어느 부분까지 갱신할까요?" | A15의 질문 |
| A14 | Owner 결정 (원문, 착수 전 bounded question) | "[Owner 답 2]" | 답의 표지 |
| A15 | Owner 결정 (원문, 착수 전 bounded question) | "§2 설명 필드 + Dashboard 현재 줄 (Recommended)" | Manager 해석(선택지 설명 근거): "§2 설명 필드"는 Last verified, Verified implementation HEAD, Current workstream, Current milestone, Recommended next step, Next user-visible milestone, Recent completed 일곱 개이고, "Dashboard 현재 줄"은 현재 다음 작업·현재 사용자 체감 결과·다음 사용자 체감 milestone·현재 결정 필요 네 줄이다. Approval state, Owner decision, Manager reporting 필드는 그대로다. §2 필드와 Dashboard 네 줄 모두 오래된 문장만 고치고 보류·잠금 문장은 남겼다 |

## Self-review

`self-reviewer`(`claude -p --agent self-reviewer --tools Read,Grep,Glob`, 첫 사전 점검 PASS 뒤 1회, API 환산 약 $0.49)의 지적 4건(major 1, minor 3)을 모두 고쳤다.

1. (major) `Recommended next step`에서 기준선 값 끝 문장 "task-0042가 ④의 선행조건인 것은 사실이지만 그 사실이 ④ 착수를 승인하지는 않는다"가 빠짐 → 되살렸다(값 418자). 구현 절과 A15에 보류 문장을 그대로 두었다고 적었다.
2. "남은 작은 후보"와 "현재 사용자 체감 결과" 문장의 근거가 기록에 없음 → 조사 절에 출처(코드 위치, 검사 결과, task id)를 적었다.
3. `Recent completed`에서 남긴 옛 항목·뺀 항목과 기준이 기록에 없음 → 구현 절에 적었다.
4. 사전 점검 결과가 기록에 없음 → 아래에 적었다.

수정 뒤 Console smoke 통과, SOP validator PASS. 수정 뒤 사전 점검(`python -B scripts/check_task_record.py memory/tasks/task-0210-master-plan-baseline-refresh.md --baseline 7b03f6f0f39b23959e95925405f0e2e86248c2a1 --require-quotes`)은 `staged_files=2`, `violations=0`, `status=PASS`였고, 그 뒤 `commit_candidate.py`로 candidate를 만들었다.

## Reviewer 결과 (첫 candidate)

- candidate `42544d6f2b7585cd6aabef80950d10957ef75c86`: Reviewer FINDINGS, 지적 1건(minor), self_deviations 0. master-plan 두 곳(Recommended next step, 현재 결정 필요)과 조사 절이 attempt branch 3개 삭제를 "남은 Owner 결정"으로 적으며 task-0209를 출처로 달았지만, task-0209 기록에는 그 branch들이 main 조상이 아닌 실패 시도라는 사실과 Owner가 branch를 남기기로 한 결정만 있고 열린 결정은 없다.
- Repair 1(`repair_count=1`, 예산 안, Manager 결정): 두 master-plan 문장을 "task-0209가 남긴 … branch 3개"를 2026-10-29 조사가 Owner 결정 대상으로 본 것으로 고쳐 task-0209는 사실의 출처로만 남겼고, 조사 절에 판단 주체를 적었다. `Recommended next step` 값은 439자다. 새 candidate에 Reviewer → QA를 다시 한다.
