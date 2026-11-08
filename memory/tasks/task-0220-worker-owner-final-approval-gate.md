# task-0220-worker-owner-final-approval-gate

- id: `task-0220-worker-owner-final-approval-gate`
- title: `Worker 결과의 Owner 최종 승인 뒤에만 main 반영 (1단위: 대기·accept·reject)`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-11-08 09:55 UTC`
- updated_at: `2026-11-08 09:55 UTC`
- summary: `Worker 파이프라인이 /go 실행 승인만으로 Reviewer와 QA 뒤 main에 반영하던 것을 바꾼다. 통과한 실행은 NEEDS_APPROVAL로 멈춰 candidate를 보존하고 main을 건드리지 않으며, Owner의 /go accept 때만 QA 재실행 뒤 ff-only 반영하고 /go reject는 main 불변으로 FAILED로 끝낸다. revise와 recheck는 2단위, Lead 종합 보고·Worker Backend·Gemma·push는 범위 밖이다.`
- source_command: `Owner 지시: 결과 확인 후 반영 구조 구현, 정책 4건 승인 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `a7a28dcd8e4a1af78f652866541f142eb3b9f96a` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문, 작업 지시)

```text
[Owner 지시]
첫 번째 작업 목표: 결과 확인 후 반영 구조 구현
Owner의 사전 실행 승인과 최종 반영 승인을 구분한다.
최종 승인 전에는 main이 절대 변경되지 않아야 한다.
승인 전 결과물은 candidate 또는 격리된 상태로 보존한다.
거절, 수정 요청, 재검토, 승인 흐름을 명확하게 구분한다.
기존 /go, /accept, resume, recover의 동작과 호환성을 확인한다.
기존 Reviewer, QA, 실패 복구 구조를 최대한 재사용한다.
jarvis.bat은 절대 수정하지 않는다.
```

## Owner 결정 (원문, 설계 승인)

```text
설계를 검토했다.
제안한 정책 결정 4건을 모두 승인한다.
NEEDS_APPROVAL 상태 재사용
main의 커밋 및 소스 파일은 최종 승인 전까지 불변.
읽기 전용 보고 기록은 기존 방식 유지
revise는 Owner가 승인한 새로운 실행으로 취급하며, 각 실행의 자동 repair는 최대 1회
Lead의 종합 보고는 이번 범위에서 제외하고 다음 작업으로 분리
봇 재시작 후에도 NEEDS_APPROVAL 상태와 candidate가 보존되어야 한다.
중복 accept 및 동시 승인으로 인한 중복 반영을 방지해야 한다.
Owner가 승인 전에 변경 파일, 변경 내용, Reviewer 결과, QA 결과를 확인할 수 있어야 한다.
승인 대기 중 main이 변경되면 기존 baseline 검증 규칙에 따라 안전하게 거절해야 한다.
이제 task를 등록하고 1단위부터 진행해라.
이번 작업에서는 Worker Backend 분리, Gemma 연결, push를 진행하지 않는다.
최종 목표는 Owner의 최종 승인 없이는 어떤 수정 작업도 main에 반영되지 않는 것이다.
```

두 블록은 Owner 메시지에서 조건 문장을 번호·글머리표 없이 옮긴 것이다.

## Owner 결정 (원문, 승인된 설계 제안)

```text
[Manager 제안]
통과한 실행은 NEEDS_APPROVAL로 대기하고 /go <id> accept 때만 main에 반영한다.
/go <id> reject는 main을 바꾸지 않고 FAILED로 끝낸다.
/go <id> revise <지시>는 수정 요청이고 /go <id> recheck는 재검토다.
결정 1: NEEDS_APPROVAL 재사용. 전이 DOING → NEEDS_APPROVAL 1쌍만 추가.
결정 2: main의 커밋과 소스 파일 불변. task 기록의 상태 변화는 작업 트리에만 있고 승인 때 커밋. 읽기 전용 보고는 지금처럼 기록만 커밋.
결정 3: revise 1회를 Owner가 승인한 새 실행으로 취급. 그 안의 자동 repair는 최대 1회.
결정 4: Lead 종합 보고는 이번에 제외.
진행 단위 1: 대기 + accept + reject.
진행 단위 2: revise + recheck.

[Owner 답]
제안한 정책 결정 4건을 모두 승인한다.
```

Manager가 채팅으로 보인 설계 제안의 핵심 문장을 표 형식 없이 옮겼다.

## 조사 (baseline 기준)

- `_run_pipeline`은 Reviewer PASS와 QA 6개 통과 뒤 바로 `_integrate_and_checkpoint`로 ff-only 반영했다. `/go`가 실행 승인과 반영 승인을 겸했다.
- `/go <id> accept`(`accept_candidate`)는 candidate 대조, main baseline 확인, QA 재실행, 승인 전이, 반영을 이미 한다. 별도 `/accept` 명령은 없다.
- 상태 `NEEDS_APPROVAL`에서 나가는 전이(`DOING`, `FAILED`)는 이미 있고, 들어오는 전이 `DOING → NEEDS_APPROVAL`만 없었다.
- `/approve`는 `NEEDS_APPROVAL`을 받아 옛 실행 경로로 보내므로, 대기 task에는 막아야 한다.
- task 기록은 `/work`로 만든 뒤 checkpoint까지 커밋되지 않으며 `_main_tracked_changes`는 task 자신의 기록을 뺀다. 승인 전 상태 변화는 작업 트리에만 있다(요약 A13의 main 불변 범위).

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/worker/claude_worker.py`, `orchestrator/worker/run_smoke_tests.py`, `adapters/discord/bot_minimal.py`, `orchestrator/discord-intake/task_file_writer.py`, `apps/jarvis-console/run_web_app.py`, `apps/jarvis-console/run_smoke_tests.py`, `docs/task-model.md`, `docs/jarvis-multi-agent-sop-v0.1.md`, `adapters/discord/README.md`, `apps/jarvis-console/README.md`, 이 task 기록 |
| deny | revise·recheck(2단위), Lead 종합 보고, Worker Backend, Gemma, 다른 task 기록, validator, `jarvis.bat`, `.env`, push |

## Start

Console Create Local Task Preview를 확인하고 Confirm해 TODO 기록을 만들었다. Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다. Console은 수정 전에 껐다. 그 뒤 title·summary·source_command를 이 task 내용으로 고쳤다.

## 구현

- 상태 전이: `DOING → NEEDS_APPROVAL`을 더했다(14쌍). 봇의 `ALLOWED_STATUS_TRANSITIONS`도 맞췄다.
- `_run_pipeline`: QA 뒤 반영하지 않고 `owner_review` 단계로 간다. 검토 자료를 만들고 `qa:owner_final_review candidate=.. baseline=.. attempt=..` 기록을 `record_awaiting`으로 쓴 뒤 `awaiting_owner`로 끝난다. 기록을 못 쓰면 `awaiting_not_recorded`로 실패한다. 파이프라인에서 main을 바꾸는 호출을 없앴고 이를 켜는 인자나 환경 변수는 두지 않았다.
- 검토 자료: 변경 파일(`git diff --stat`), diff 앞부분, 저장소 밖 `<attempt>-final-review.md`(전체 diff, Reviewer 보고, QA, 테스트). 쓰기 실패는 실행을 바꾸지 않는다.
- `/go <id> accept`: `NEEDS_APPROVAL`이면 `_final_review_record`를, `FAILED`면 기존 `_owner_review_record`를 받아 같은 `accept_candidate`로 간다. 승인 전이는 `NEEDS_APPROVAL → DOING`이다.
- `/go <id> reject`: `_run_reject`가 잠금을 잡고 `NEEDS_APPROVAL → FAILED`와 `owner:owner_rejected ...` 기록을 한 번에 쓰고 감사를 남긴다. 거절된 candidate는 accept 기록이 아니다.
- `/approve`는 대기 task를 `approve_not_for_final_review`로 거절한다.
- 보고: `_final_review_reply`가 변경 파일(길면 잘라 총 개수 표시), Reviewer, QA, 테스트, diff 앞부분, 검토 파일 경로, 두 명령을 한 메시지(2000자)에 담는다. accept가 거절됐을 때는 다시 승인·거절과 `resume` 길을 안내한다. `/work` 계획 문구와 `/help`도 고쳤다.
- 일반 전이 writer는 `DOING → NEEDS_APPROVAL`을 거부한다(기록 없는 대기 방지).
- Console: 대기 task의 Next action과 Hold Preview 안내에 두 명령을 적고, `owner_rejected`·`awaiting_not_recorded` 실패 설명을 더했다.
- 문서: task-model §5-1·§5-2, SOP §10.1 진입 명령, §10.2 9·10·11·12항, Discord·Console README.

## Owner 추가 조건의 충족

| 조건 | 구현과 테스트 |
| --- | --- |
| 봇 재시작 후 보존 | 상태와 기록은 task 파일, candidate는 git·worktree에만 있다. smoke가 잠금 없음, 파일 기록 재판독, `find_owner_review_attempt`로 candidate 재식별, 멈춘 작업 목록에 없음을 확인한다. 실제 프로세스 재시작은 하지 않았다 |
| 중복·동시 승인 방지 | 실행 중 두 번째 accept는 `worker_busy`, DONE 뒤는 `accept_requires_failed:DONE`, 상태 검사를 지난 늦은 accept는 job에서 다시 읽어 `accept_record_invalid`로 끝나고 main이 움직이지 않는다 |
| 승인 전 확인 | 보고와 검토 파일. smoke가 보고 내용과 2000자 이내, 검토 파일의 네 절을 확인한다 |
| 대기 중 main 변경 | `accept_baseline_moved`로 거절하고 상태·기록·worktree를 유지한다. 답에 재승인·거절·resume 길을 보인다 |

## Implementer 검증 (작업 트리)

- Worker smoke total=663 failed=0, Console smoke PYTHONUTF8=1과 없음 rc=0, `run_web_app.py --self-test` 통과, Discord `--self-check-suite` 109건 ok, SOP validator PASS, `node --check app.js` 통과, discord-intake smoke rc=0, `git diff --check` 통과.

## Self-review

SOP §3의 `claude -p --agent self-reviewer`는 이 PC의 Claude CLI 로그인이 풀려(`loggedIn: false`, OAuth session expired) 실행할 수 없었다. 로그인은 Owner만 할 수 있어, 같은 `.claude/agents/self-reviewer.md` 정의(Read·Grep·Glob)를 이 세션의 subagent로 한 번 돌렸다(절차 차이). Reviewer 판정이 아니다. 지적과 처리:

1. major: Hold 안내와 task-model·Console README가 `/approve`만 승인 경로라고 적음. Hold Preview 안내를 대기 기록이면 `/go accept`·`reject`로 바꾸고 문서에 예외를 적었다.
2. major: 승인된 설계 제안이 기록에 없고 A1·A6·A13이 원문 없는 내용을 적음. 제안의 핵심 문장을 원문 블록으로 옮기고 해당 행을 고쳤다.
3. minor: "유일한 경로" 표현이 읽기 전용 보고의 기록 커밋을 빠뜨림, 대기 중 main 이동 상호작용 미기재. 주석·A23·SOP 9항을 고쳤다.
4. minor: accept 상태 읽기 실패 시 잠금 미해제. try로 감싸 빈 값이면 accept가 거절되고 잠금이 풀리게 했다.
5. minor: 승인 전이 실패 시 안내가 대기 task에 맞지 않음. 별도 안내를 더했다.
6. minor: 긴 파일 목록이면 명령이 잘림. 목록과 테스트 요약의 길이를 제한하고 긴 목록 smoke를 더했다.
7. minor: accept 중 DOING + success가 docstring과 어긋남. docstring과 task-model 10절을 고쳤다.
8. minor: 일반 writer가 대기 전이를 통과시킴. 거부하게 하고 smoke를 더했다.
9. minor: SOP의 resume 우회 금지와 봇 안내가 충돌해 보임. SOP와 봇 문구에 새 실행임을 적었다.
10. minor: 실행 표지 종료 시점, 대기 기록 위치, reject의 `worker_busy`, `/approve` 거절 사유 미기재. 각 문서에 더했다.
11. minor: accept 관련 주석이 FAILED 전용. 고쳤다.
12. minor: 기록의 "Owner 결정 2" 표현. A13으로 고쳤다.

수정 뒤 전체 검사를 다시 돌렸고 사전 점검(`check_task_record.py --require-quotes`)은 candidate 직전 실행과 같다(PASS).

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다. 오른쪽 칸에서 "Manager 해석"이라고 적은 부분은 승인 원문에 없는 내용이다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문, 작업 지시) | "[Owner 지시]" | 지시의 표지. Manager 해석: 이 task는 Owner 지시 흐름 중 대기·승인·거절 부분이다 |
| A2 | Owner 결정 (원문, 작업 지시) | "첫 번째 작업 목표: 결과 확인 후 반영 구조 구현" | 이 task와 2단위 task의 목표다 |
| A3 | Owner 결정 (원문, 작업 지시) | "Owner의 사전 실행 승인과 최종 반영 승인을 구분한다." | `/go`는 실행 승인, `/go <id> accept`는 반영 승인이다. SOP 9항에 적었다 |
| A4 | Owner 결정 (원문, 작업 지시) | "최종 승인 전에는 main이 절대 변경되지 않아야 한다." | `_run_pipeline`에서 반영 호출을 없앴고 smoke가 HEAD 불변을 확인한다 |
| A5 | Owner 결정 (원문, 작업 지시) | "승인 전 결과물은 candidate 또는 격리된 상태로 보존한다." | attempt 브랜치와 worktree에 남긴다 |
| A6 | Owner 결정 (원문, 작업 지시) | "거절, 수정 요청, 재검토, 승인 흐름을 명확하게 구분한다." | 승인과 거절은 이 task, 수정 요청과 재검토는 A33의 진행 단위 2다 |
| A7 | Owner 결정 (원문, 작업 지시) | "기존 /go, /accept, resume, recover의 동작과 호환성을 확인한다." | Manager 해석: /accept는 실제 명령 /go <id> accept다. smoke가 네 경로를 확인한다. FAILED accept는 기존 그대로다 |
| A8 | Owner 결정 (원문, 작업 지시) | "기존 Reviewer, QA, 실패 복구 구조를 최대한 재사용한다." | Reviewer·QA·repair는 바꾸지 않았고 `accept_candidate`를 재사용했다 |
| A9 | Owner 결정 (원문, 작업 지시) | "jarvis.bat은 절대 수정하지 않는다." | 건드리지 않았다 |
| A10 | Owner 결정 (원문, 설계 승인) | "설계를 검토했다." | 설계 승인의 배경 |
| A11 | Owner 결정 (원문, 설계 승인) | "제안한 정책 결정 4건을 모두 승인한다." | 구현 착수 승인 |
| A12 | Owner 결정 (원문, 설계 승인) | "NEEDS_APPROVAL 상태 재사용" | `DOING → NEEDS_APPROVAL` 1쌍만 더했다 |
| A13 | Owner 결정 (원문, 설계 승인) | "main의 커밋 및 소스 파일은 최종 승인 전까지 불변." | main 커밋과 소스 파일은 accept 전까지 바뀌지 않는다. task 기록의 상태는 작업 트리에서만 바뀐다(A29 결정 2) |
| A14 | Owner 결정 (원문, 설계 승인) | "읽기 전용 보고 기록은 기존 방식 유지" | `run_report`는 바꾸지 않았다 |
| A15 | Owner 결정 (원문, 설계 승인) | "revise는 Owner가 승인한 새로운 실행으로 취급하며, 각 실행의 자동 repair는 최대 1회" | 2단위에서 구현한다 |
| A16 | Owner 결정 (원문, 설계 승인) | "Lead의 종합 보고는 이번 범위에서 제외하고 다음 작업으로 분리" | 포함하지 않았다 |
| A17 | Owner 결정 (원문, 설계 승인) | "봇 재시작 후에도 NEEDS_APPROVAL 상태와 candidate가 보존되어야 한다." | Owner 추가 조건 표 참고. 실제 프로세스 재시작은 하지 않았고 파일·git 재판독으로 확인했다 |
| A18 | Owner 결정 (원문, 설계 승인) | "중복 accept 및 동시 승인으로 인한 중복 반영을 방지해야 한다." | Owner 추가 조건 표 참고 |
| A19 | Owner 결정 (원문, 설계 승인) | "Owner가 승인 전에 변경 파일, 변경 내용, Reviewer 결과, QA 결과를 확인할 수 있어야 한다." | Discord 보고와 저장소 밖 검토 파일. Owner 추가 조건 표 참고 |
| A20 | Owner 결정 (원문, 설계 승인) | "승인 대기 중 main이 변경되면 기존 baseline 검증 규칙에 따라 안전하게 거절해야 한다." | `accept_baseline_moved`로 거절하고 대기를 유지한다 |
| A21 | Owner 결정 (원문, 설계 승인) | "이제 task를 등록하고 1단위부터 진행해라." | 이 task가 1단위다 |
| A22 | Owner 결정 (원문, 설계 승인) | "이번 작업에서는 Worker Backend 분리, Gemma 연결, push를 진행하지 않는다." | 하지 않았다 |
| A23 | Owner 결정 (원문, 설계 승인) | "최종 목표는 Owner의 최종 승인 없이는 어떤 수정 작업도 main에 반영되지 않는 것이다." | Worker 변경이 main에 들어가는 경로는 `accept_candidate`뿐이다. 읽기 전용 보고의 task 기록 커밋은 A14 예외다. 실행 중인 봇은 재시작 전까지 이전 코드라는 점을 Owner에게 보고한다 |
| A24 | Owner 결정 (원문, 승인된 설계 제안) | "[Manager 제안]" | 제안의 표지 |
| A25 | Owner 결정 (원문, 승인된 설계 제안) | "통과한 실행은 NEEDS_APPROVAL로 대기하고 /go <id> accept 때만 main에 반영한다." | NEEDS_APPROVAL 대기와 accept를 구현했다 |
| A26 | Owner 결정 (원문, 승인된 설계 제안) | "/go <id> reject는 main을 바꾸지 않고 FAILED로 끝낸다." | reject를 구현했다 |
| A27 | Owner 결정 (원문, 승인된 설계 제안) | "/go <id> revise <지시>는 수정 요청이고 /go <id> recheck는 재검토다." | Manager 해석: 수정 요청과 재검토는 진행 단위 2에서 구현한다 |
| A28 | Owner 결정 (원문, 승인된 설계 제안) | "결정 1: NEEDS_APPROVAL 재사용. 전이 DOING → NEEDS_APPROVAL 1쌍만 추가." | `DOING → NEEDS_APPROVAL`만 더했다 |
| A29 | Owner 결정 (원문, 승인된 설계 제안) | "결정 2: main의 커밋과 소스 파일 불변. task 기록의 상태 변화는 작업 트리에만 있고 승인 때 커밋. 읽기 전용 보고는 지금처럼 기록만 커밋." | A13·A14와 같다 |
| A30 | Owner 결정 (원문, 승인된 설계 제안) | "결정 3: revise 1회를 Owner가 승인한 새 실행으로 취급. 그 안의 자동 repair는 최대 1회." | 진행 단위 2에서 구현한다 |
| A31 | Owner 결정 (원문, 승인된 설계 제안) | "결정 4: Lead 종합 보고는 이번에 제외." | 포함하지 않았다 |
| A32 | Owner 결정 (원문, 승인된 설계 제안) | "진행 단위 1: 대기 + accept + reject." | 이 task의 범위다 |
| A33 | Owner 결정 (원문, 승인된 설계 제안) | "진행 단위 2: revise + recheck." | 다음 task의 범위다 |
| A34 | Owner 결정 (원문, 승인된 설계 제안) | "[Owner 답]" | 답의 표지 |
| A35 | Owner 결정 (원문, 승인된 설계 제안) | "제안한 정책 결정 4건을 모두 승인한다." | A11과 같은 문장이다 |
