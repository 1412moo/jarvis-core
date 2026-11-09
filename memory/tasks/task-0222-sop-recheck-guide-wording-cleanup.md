# task-0222-sop-recheck-guide-wording-cleanup

- id: `task-0222-sop-recheck-guide-wording-cleanup`
- title: `SOP recheck 표지 안내 문구 정리와 task-0220 minor 정정 기록`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-11-09 06:48 UTC`
- updated_at: `2026-11-09 08:49 UTC`
- summary: `task-0220에서 Owner가 수용한 Reviewer minor 5건을 정리한다. 현재 규칙인 SOP의 recheck 표지 안내 문구만 실제 동작에 맞게 고치고, task-0220 DONE 기록의 요약 세 행은 History라 고치지 않고 이 기록에 정정을 남기며, smoke diff 보기 한도 건은 변경이 없다. 코드 변경과 push는 범위 밖이다.`
- source_command: `Owner 지시: 진행해 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `dd0efa205ec08646412f862bee8fc16aceeaec51` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=1` (SOP §5 기본값, repair 1은 아래 절) |

## Owner 결정 (원문)

```text
[Manager 질문]
수용한 minor 5건의 문구 정리를 다음 task로 진행할까요?

[Owner 답]
진행해
```

직전 Manager 보고(Owner 원문 아님): task-0220 candidate `ecb820c`의 Reviewer minor 5건을 Owner가 그 candidate에 한해 수용했고, 그 문구 정리를 작은 후속 task로 권했다. push는 이 승인에 포함되지 않는다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `docs/jarvis-multi-agent-sop-v0.1.md`(§10 recheck 항목의 문장 하나), 이 task 기록 |
| deny | task-0220 기록, 코드, 검사기, 다른 문서, `jarvis.bat`, `.env`, push, 봇 재시작 |

## 5건 처리

task-0220 기록의 "2단위 Reviewer 결과" 절 번호를 따른다.

| # | 지적 | 위치의 성격 | 처리 |
| --- | --- | --- | --- |
| 1 | 요약 A89의 "유지했다" | History(DONE task 본문) | task-0220을 고치지 않고 아래 정정 절에 남긴다 |
| 2 | SOP의 "안내하지 않으며" | 현재 규칙 | 문장을 실제 동작에 맞게 고친다(구현 절) |
| 3 | 요약 A8의 "Reviewer·QA·repair는 바꾸지 않았고" | History(DONE task 본문) | 정정 절에 남긴다 |
| 4 | 요약 A73의 "main을 바꾸는 호출은 accept의 ff-only뿐" | History(DONE task 본문) | 정정 절에 남긴다 |
| 5 | smoke diff가 도구 한도를 넘어 Reviewer가 삭제 줄을 못 봄 | 문구 문제가 아니라 검토 범위 기록 | 변경 없음. task-0220의 2단위 Reviewer 결과 절(repair 4 candidate) 5번 항목에 Manager와 QA의 확인이 적혀 있다 |

Manager 해석: 질문의 "문구 정리"를 위 표로 나눴다. AGENTS.md 기준 지도는 task 본문을 작성 당시의 기록으로 두고, task-0220의 Owner 최종 승인과 completion_evidence가 그 기록 위에 있으므로 뒤늦게 바꾸지 않는다.

## task-0220 요약 행 정정 (task-0220 기록은 그대로)

- A89 "유지했다": task 기록을 쓰지 못해도 `.recheck-findings` 표지로 accept 거절을 유지한다. 기록과 표지 쓰기가 함께 실패하면 표지가 없어 accept가 막히지 않고 답장으로만 알린다. SOP 해당 문장의 끝에 이 한계가 적혀 있다.
- A8 "Reviewer·QA·repair는 바꾸지 않았고": 1단위까지의 설명이다. 2단위는 QA 비교의 `--no-renames`와 Reviewer 호출의 recheck·revision 분기를 더했다.
- A73 "main을 바꾸는 호출은 accept의 ff-only뿐": candidate의 소스를 main에 넣는 경로에 대한 설명이다. 읽기 전용 보고의 기록 commit과 accept 뒤 checkpoint commit도 main을 움직인다.

## 구현

`docs/jarvis-multi-agent-sop-v0.1.md`의 recheck 항목에서 "거절하고 안내하지 않으며"를 네 부분으로 나눴다: accept는 `accept_recheck_findings`로 거절한다, 이 거절을 판정한 답장(`accept_blocked`)은 accept를 안내하지 않는다, 그 판정을 거치지 않는 안내(예: Console Next action, `/approve` 거절 답장, 깨진 표지가 남은 뒤의 revise 성공이나 미확인 항목 답장, candidate를 찾지 못한 실패 답장)는 accept를 안내할 수 있다, 그래도 실제 accept는 표지 확인(candidate 식별이 계속 실패하면 그 식별 단계)에서 거절된다. 목록은 예시이며 전부가 아니다.

확인한 코드(baseline 기준):
- `orchestrator/worker/claude_worker.py`의 `_recheck_findings_hold`는 깨진 표지면 candidate와 무관하게 True를 돌려준다.
- `adapters/discord/bot_minimal.py`의 `accept_blocked` 분기는 accept 선택지를 빼고, accept 재시도 표시는 `accept_blocked`면 꺼진다.
- `apps/jarvis-console/run_web_app.py`에는 표지를 읽는 코드가 없고 Next action이 accept를 적는다. `/approve` 거절 답장과 최종 승인 대기 보고의 accept 안내는 표지를 읽지 않는 고정 문구다.
- 승인 전이 뒤의 revise가 `qa_unverified_owner_review`로 끝나면 `accept_blocked`가 계산되지 않고, candidate를 찾지 못하면 표지를 읽지 않아 `accept_retryable`이 참이 될 수 있다(self-review 지적 1, 2).

코드는 바꾸지 않았다. 안내를 표지에 맞추려면 코드 변경이라 이 task 밖이다.

## Self-review

staged 변경에 self-reviewer를 한 번 돌렸다(Reviewer 판정 아님). minor 세 건과 처리:

1. SOP 문장이 revise 실패 답장은 accept를 안내하지 않는다고 단정했는데, 승인 전이 뒤 revise가 미확인 항목으로 끝나면 안내한다. 고쳤다: 안내하지 않는 쪽을 `accept_blocked` 판정 답장으로 한정하고, 깨진 표지의 예에 미확인 항목 답장을 더했다.
2. 표지를 읽지 않는 안내의 목록이 전부처럼 읽혔고, candidate 식별 실패 답장이 빠졌다. 고쳤다: 그 답장을 더하고 "예:"로 예시임을 밝혔다.
3. 5번 처리의 근거가 QA 결과 절을 가리켰는데 확인은 2단위 Reviewer 결과 절 5번 항목에만 있다. 고쳤다.

수정 뒤 사전 점검(`check_task_record.py --require-quotes`)은 candidate 직전 실행 결과와 같다(PASS, violations 0).

## Reviewer 결과 (candidate `7cfbc222722735da6f9fb888559db01304195b87`)

verdict FINDINGS, minor 2건.

1. SOP 문장의 "표지 확인에서 거절된다"가 candidate 식별 실패까지 덮었다. 식별이 계속 실패하면 표지를 읽기 전에 식별 단계에서 거절된다.
2. 5건을 SOP 수정 1건, 정정 기록 3건, 변경 없음 1건으로 나눈 것이 승인 원문에 없는 Manager 해석이었다.

`self_deviations` 4건: `git grep`에 허용 형식 밖의 `-i`를 한 번 썼고, 표 행을 찾는 패턴 세 개에 파이프 문자를 썼다. 모두 읽기 전용이고 결과는 판정의 근거 중 일부다. 새 candidate의 Reviewer는 다시 돈다.

Reviewer unverified: 사전 점검 결과, validator 통과 여부, self-review 실행 사실, baseline과 origin/main의 관계, 직전 Manager 보고의 맥락. 앞의 둘은 QA에서 확인한다.

## Owner 결정 (원문, 5건 처리)

```text
[Manager 질문]
task-0222에서 task-0220의 minor 5건을 이렇게 처리할까요?
SOP 문장 1건만 수정하고, task-0220 DONE 기록의 요약 3행(A8, A73, A89)은 그대로 둔 채 task-0222 기록에 정정을 남기며, smoke diff 보기 한도 1건은 변경하지 않습니다.

[Owner 답]
이대로 승인 (Recommended)
```

## Repair 1

Reviewer minor 2건을 budget 안에서 고쳤다(`repair_count=1`). 지적 1은 SOP 문장과 구현 절에 식별 단계를 구분해 넣었고, 지적 2는 위 Owner 결정으로 분할을 승인받아 기록했다. 코드는 바꾸지 않았다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다. 오른쪽 칸에서 "Manager 해석"이라고 적은 부분은 승인 원문에 없는 내용이다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 질문]" | 질문의 표지 |
| A2 | Owner 결정 (원문) | "수용한 minor 5건의 문구 정리를 다음 task로 진행할까요?" | A4 답의 질문. 5건의 처리는 "5건 처리" 절이다 |
| A3 | Owner 결정 (원문) | "[Owner 답]" | 답의 표지 |
| A4 | Owner 결정 (원문) | "진행해" | 착수 승인. 5건의 처리 분할은 A9에서 Owner가 정했다. Manager 해석: 코드 변경과 push는 포함하지 않는다 |
| A5 | Owner 결정 (원문, 5건 처리) | "[Manager 질문]" | 질문의 표지 |
| A6 | Owner 결정 (원문, 5건 처리) | "task-0222에서 task-0220의 minor 5건을 이렇게 처리할까요?" | A9 답의 질문 |
| A7 | Owner 결정 (원문, 5건 처리) | "SOP 문장 1건만 수정하고, task-0220 DONE 기록의 요약 3행(A8, A73, A89)은 그대로 둔 채 task-0222 기록에 정정을 남기며, smoke diff 보기 한도 1건은 변경하지 않습니다." | A9 답의 질문 내용. "5건 처리" 절과 같다 |
| A8 | Owner 결정 (원문, 5건 처리) | "[Owner 답]" | 답의 표지 |
| A9 | Owner 결정 (원문, 5건 처리) | "이대로 승인 (Recommended)" | 5건 처리 분할 승인. SOP 문장만 고치고 task-0220 기록은 그대로 두었으며 smoke 건은 변경하지 않았다 |
