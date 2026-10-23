# task-0188-accept-test-line

- id: `task-0188-accept-test-line`
- title: `accept 완료 보고의 테스트 줄`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-23 08:25 UTC`
- updated_at: `2026-10-23 08:32 UTC`
- summary: `Discord /go accept 완료 보고의 테스트 줄이 비어 나오는 표시 문제를 고친다. accept 경로는 Worker 단계 테스트 요약이 없고 QA가 작업 종류의 smoke test를 다시 돌리므로, 그 결과를 테스트 줄에 적는다. 판정·반영 로직은 바꾸지 않는다.`
- source_command: `Owner 지시: accept 완료 보고 테스트 줄 수정 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `f5f1158ab7040ecafb9f1b5046bb60fb79c19dec` (등록 시점 main HEAD, task-0186·task-0187 결과 포함, push 전) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문)

```text
[Manager 보고]
완료 보고에서 "테스트:" 줄이 비어 있었는데, 실패가 아닙니다. accept 경로는 Worker 단계의 테스트를 다시 돌리지 않아 테스트 요약 값이 비어 있고, 봇이 그 줄을 빈 채로 출력했기 때문입니다(bot_minimal.py:2582). 대신 accept 때 QA 6개를 다시 확인했고 모두 통과했습니다. accept일 때 "테스트: accept 때 재실행 없음 (QA 6개로 확인)"처럼 표시되게 고치는 것은 작은 별도 task 후보입니다.

다음으로 할 수 있는 것은 셋입니다.
1. 커밋 4개 push. 말씀하시면 올리겠습니다.
2. 보호 장치 테스트. Discord에 `자비스, 스터디룸 studyroom.bat에 포트 번호를 바꾸는 옵션을 추가해줘.`를 보내면, Worker가 고쳐도 `scope_violation`으로 멈춰야 정상입니다.
3. 위의 "테스트:" 빈 줄 표시 수정.

[Owner 답]
3번
```

## 설계

1. `adapters/discord/bot_minimal.py`의 `_format_work_reply` 성공 분기만 바꾼다. Worker 단계 테스트 요약이 있으면 지금처럼 그대로 쓴다.
2. 요약이 비어 있고 Owner accept 결과이면, QA의 smoke test 재실행 결과(`qa_checks`의 `tests_rerun`)로 테스트 줄을 채운다. 통과면 "QA에서 다시 실행해 통과 (Owner accept, Worker 단계 요약 없음)"로 적는다. 성공 보고는 QA 전체 통과 뒤에만 나오지만, 값이 없으면 통과라고 쓰지 않는다.
3. 판정·반영·QA 로직과 다른 보고 문구는 바꾸지 않는다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `adapters/discord/bot_minimal.py`(`_format_work_reply` 성공 분기의 테스트 줄만), `orchestrator/worker/run_smoke_tests.py`(accept 성공 보고 검사), `memory/tasks/task-0188-accept-test-line.md` |
| deny | `jarvis.bat`, `apps/`, `orchestrator/worker/claude_worker.py`, Worker의 판정·repair·QA·반영 로직, 팀장 코드, writer·Console, AGENTS·agent 정의, SOP 문서, 다른 task 기록, 외부 API·credential, 보호 worktree |

## 계획

1. 성공 분기의 테스트 줄 변경.
2. 검사: accept 성공 보고의 테스트 줄이 비어 있지 않고 QA 재실행 통과를 말함. 일반 성공 보고는 Worker 요약을 그대로 보임.
3. 사전 점검 → self-review → candidate → Reviewer → QA → Evidence·Complete(Manager, G3와 같게) → checkpoint. push는 별도 승인.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-23 08:25 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다.

## 구현

- `adapters/discord/bot_minimal.py`: `_format_work_reply` 성공 분기에서 테스트 줄 값을 변수로 뺐다. Worker 단계 요약이 비어 있고, Owner accept 결과이고, `qa_checks`의 `tests_rerun`이 참일 때만 "QA에서 다시 실행해 통과 (Owner accept, Worker 단계 요약 없음)"을 쓴다. 그 밖에는 지금처럼 요약을 그대로 쓴다. 다른 줄과 분기는 바꾸지 않았다.
- `orchestrator/worker/run_smoke_tests.py`: 검사 3개를 더했다. 실제 accept 흐름의 성공 보고 테스트 줄이 비어 있지 않고 QA 재실행 통과를 말함, 일반 성공 보고는 Worker 요약을 그대로 보임, QA 재실행 값이 없는 accept 보고는 통과라고 쓰지 않음.

## Implementer 검증 (작업 트리)

- Worker smoke total=559 failed=0(이전 556에 3개), Discord self-check ok 109, SOP validator PASS.
- 사전 점검(`check_task_record`, baseline `f5f1158`): status=PASS, staged_files 3, violations 0, quote_check_unquoted 8(참고용).

## Self-review

candidate 전 1회. minor 3건을 모두 반영했다: A2에 "(QA 6개로 확인)"을 테스트 줄에 넣지 않은 이유를 적었고, QA가 테스트를 다시 돌린다는 근거 위치(`claude_worker.py`의 `_qa_checks`)를 적었고, 사전 점검 결과를 적었다. 코드는 바꾸지 않았다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "3. 위의 "테스트:" 빈 줄 표시 수정." / "[Owner 답]" / "3번" | accept 완료 보고의 테스트 줄만 고쳤다. 1(push)과 2(보호 장치 테스트)는 하지 않았다 |
| A2 | Owner 결정 (원문) | "accept일 때 "테스트: accept 때 재실행 없음 (QA 6개로 확인)"처럼 표시되게 고치는 것은 작은 별도 task 후보입니다." | 문구는 예시였다. 코드를 보니 QA가 smoke test를 실제로 다시 돌리므로(`tests_rerun`) "재실행 없음" 대신 "QA에서 다시 실행해 통과"로 사실에 맞게 적었다. 근거는 `orchestrator/worker/claude_worker.py`의 `_qa_checks`가 `qa["tests_rerun"] = _run_tests(worktree)[0]`로 작업 종류의 테스트를 다시 돌리는 것이다. 예시의 "(QA 6개로 확인)"은 바로 아래 기존 QA 줄(`- QA: PASS (N개 검사)`)이 이미 보이므로 테스트 줄에서 되풀이하지 않았다 |
