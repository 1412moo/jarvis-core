# task-0220-worker-owner-final-approval-gate

- id: `task-0220-worker-owner-final-approval-gate`
- title: `Worker 결과의 Owner 최종 승인 뒤에만 main 반영 (1단위: 대기·accept·reject)`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-11-08 09:55 UTC`
- updated_at: `2026-11-08 15:02 UTC`
- summary: `Worker 파이프라인이 /go 실행 승인만으로 Reviewer와 QA 뒤 main에 반영하던 것을 바꾼다. 통과한 실행은 NEEDS_APPROVAL로 멈춰 candidate를 보존하고 main을 건드리지 않으며, Owner의 /go accept 때만 QA 재실행 뒤 ff-only 반영하고 /go reject는 main 불변으로 FAILED로 끝낸다. 2단위는 /go revise로 수정한 새 candidate와 /go recheck로 Reviewer·QA만 재실행을 더한다. Lead 종합 보고·Worker Backend·Gemma·push는 범위 밖이다.`
- source_command: `Owner 지시: 결과 확인 후 반영 구조 구현, 정책 4건 승인 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `a7a28dcd8e4a1af78f652866541f142eb3b9f96a` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=1` (SOP §5 기본값, repair 1은 아래 절). retry는 Owner 증액으로 2회 사용(`retry_count=2`, 재검토 경과 절) |

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
| owned | `orchestrator/worker/claude_worker.py`, `orchestrator/worker/run_smoke_tests.py`, `adapters/discord/bot_minimal.py`, `orchestrator/discord-intake/task_file_writer.py`, `apps/jarvis-console/run_web_app.py`, `apps/jarvis-console/run_smoke_tests.py`, `docs/task-model.md`, `docs/jarvis-multi-agent-sop-v0.1.md`, `adapters/discord/README.md`, `apps/jarvis-console/README.md`, 이 task 기록(2단위에도 같은 파일) |
| deny | Lead 종합 보고, Worker Backend, Gemma, 다른 task 기록, validator, `jarvis.bat`, `.env`, push |

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

- repair 1 뒤 기준: Worker smoke total=664 failed=0, Console smoke PYTHONUTF8=1과 없음 rc=0, `run_web_app.py --self-test` 통과, Discord `--self-check-suite` 109건 ok, SOP validator PASS, `node --check app.js` 통과, discord-intake smoke rc=0, `git diff --check` 통과.

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

## Reviewer 결과 (candidate `341f59662914d3a7e1d352913f3ac04a47a0558b`)

verdict FINDINGS, `self_deviations` 1건(Reviewer가 git grep에 여러 패턴을 합침)이라 이 검토는 무효다. minor 두 건:

1. 대기 task의 Hold 안내 분기와 Hold→Resume 보존을 확인하는 테스트가 없다.
2. `_prepare_final_review`가 diff timeout을 잡지 않아 "실행에 영향 없음" 설명과 다르다(fail-closed이지만 FAILED로 끝남).

## Repair 1 (`repair_count=1`)

- Console smoke에 대기 task의 Hold Preview 안내와 Hold→Resume 뒤 상태·기록 보존 검사를 더했다.
- `_prepare_final_review`가 `subprocess.TimeoutExpired`도 잡게 하고 Worker smoke에 검사를 더했다.
- 이전 candidate의 Reviewer 결과는 무효이며 새 candidate에 fresh Reviewer와 QA를 돌린다.

## Reviewer 재검토 경과 (candidate `44e5adabb044d8355ccb04e9a07118390a075b0d`)

| 차례 | 판정 | self_deviations | 효력 |
| --- | --- | --- | --- |
| repair 뒤 1차 | FINDINGS minor 1(큰 테스트 diff를 다 읽지 못함) | `git grep`에 패턴 alternation | 무효 |
| retry 1 | PASS, 지적 0 | `git grep -F` | 무효 |
| retry 2 (Owner 증액) | PASS, 지적 0 | `git grep -c` | 무효, 아래 Owner 예외로 유효 인정 |

세 이탈 모두 읽기 전용 git 옵션이다. retry 1의 이탈은 Manager가 넘긴 검색어에 `|`가 들어 있어 유도됐다. 1차의 지적은 소스 변경이 필요 없어 retry로 처리했고, retry에 이 파일의 변경 위치를 찾는 검색어를 넘겼다.

## Owner 결정 (원문, retry 증액)

```text
[Manager 질문]
retry 예산 1회는 이미 썼고, 예산 증액은 Owner만 정할 수 있습니다. 어떻게 할까요?

[Owner 답]
retry 1회 증액 (Recommended)
```

## Owner 결정 (원문, Reviewer 무효 규칙 예외)

```text
이번 한 건에 한해 Owner 결정으로 현재 candidate `44e5ada`의 Reviewer PASS를 유효한 검토 결과로 인정한다.
동일 candidate에서 PASS, 지적 0건이 두 차례 확인되었고, 무효 사유는 모두 읽기 전용 git 옵션 사용이었다는 점을 고려한 예외 결정이다.
다음 조건으로 진행해라.
이번 예외 결정과 사유를 task-0220 기록에 정확히 남긴다.
candidate `44e5ada`의 코드는 변경하지 않는다.
기존 절차에 따라 QA를 진행한다.
QA PASS 후에도 NEEDS_APPROVAL 상태를 유지한다.
Owner의 최종 승인 전까지 main에 반영하지 않는다.
push는 하지 않는다.
이번 예외는 task-0220의 해당 Reviewer 검토에만 적용한다.
이후 작업부터는 기존 SOP의 Reviewer 무효 규칙을 그대로 적용한다.
```

이 예외는 위 retry 2의 검토에만 적용한다. Owner의 메시지에서 번호를 뺀 것 외에는 원문 그대로다.

## QA 결과 (candidate `44e5adabb044d8355ccb04e9a07118390a075b0d`)

- scratchpad의 새 detached worktree(`core.autocrlf=true`)를 candidate에 두고 돌렸다. HEAD = candidate, 작업 트리 깨끗(실행 뒤에도), 변경 파일 11개, `jarvis.bat` 트리에 없음. QA worktree는 지웠다.
- `git diff --check` 통과, SOP validator PASS, `run_web_app.py --self-test` 통과, Console smoke PYTHONUTF8=1과 없음 모두 rc=0, `node --check app.js` 통과, Worker smoke total=664 failed=0, discord-intake smoke rc=0, Discord `--self-check-suite` rc=0, Studyroom smoke 5/5, `check_no_secrets.py` findings 0.
- Reviewer의 unverified 항목: 감사 검증기 `validate_payload("owner_approval", ...)`가 `/go` reject(`NEEDS_APPROVAL → FAILED`)와 accept(`NEEDS_APPROVAL → DOING`) payload를 받는다. 저장소 밖 잠금 파일을 잡은 동안 별도 프로세스의 획득은 실패하고 해제 뒤 성공한다. `_run_pipeline` 안에 `_integrate_and_checkpoint` 호출이 없고 `merge` 호출은 파일 전체에 하나다. `accept_candidate`와 `run_pipeline`을 부르는 곳은 봇의 `_run_worker_job`뿐이다.
- QA 판정: PASS. Docs는 `not_required`(문서 변경이 candidate에 포함됨).
- 확인하지 못한 것: 실제 봇 프로세스 재시작과 Discord 실전 실행. 실행 중인 봇은 이 코드를 아직 읽지 않았고 이 PC의 `claude` CLI는 로그아웃 상태다.

## Manager 메모 (candidate 절차)

첫 candidate 커밋 때 Manager의 명령이 Console smoke 실패를 확인하지 않아, 실패한 상태로 커밋이 만들어졌다. Reviewer에 넘기기 전에 `git reset --soft`로 되돌려 고친 뒤 다시 커밋했다(`341f596`). 이 task의 status는 DOING이며 Owner 최종 승인 전이라 Complete하지 않았다. 이 기록의 Reviewer 경과·예외·QA 절은 작업 트리에만 있고 커밋하지 않았다.

## Owner 결정 (원문, 브랜치 분리)

```text
브랜치로 분리하는 방향을 선택한다.
이번 task-0220의 목적은 Owner 최종 승인 전까지 main을 변경하지 않는 구조를 만드는 것이다.
현재 두 커밋이 로컬 main에 들어간 것은 최초 승인 조건과 맞지 않으므로 다음과 같이 처리해라.
`341f596`, `44e5ada`를 별도 작업 브랜치에 안전하게 보존한다.
로컬 main을 기존 기준점 `a7a28dc`로 복구한다.
origin/main과 로컬 main이 다시 일치하는지 확인한다.
`jarvis.bat`은 절대 건드리지 않는다.
push는 하지 않는다.
task-0220은 이 단계에서 DONE 처리하지 않는다.
2단위 revise/recheck는 분리한 작업 브랜치에서 진행할 수 있도록 상태와 절차를 정리한다.
특히 브랜치 분리 전에 현재 작업물과 task 기록, 예외 결정 기록이 모두 보존되는지 확인해라.
Git reset이나 branch 이동은 먼저 복구 가능한 백업과 참조점을 확보한 뒤 실행해라.
작업이 끝나면 main, origin/main, 작업 브랜치의 HEAD와 task 상태를 각각 보고해라.
이번 단계에서는 봇 재시작이나 push를 하지 말고 먼저 보고해라.
```

번호만 뺀 Owner 메시지다.

## 브랜치 분리 실행

순서: 백업 ref `refs/backup/task-0220/main-before-split`(`44e5ada`)와 bundle, 기록 사본 생성 → 저장소 밖 worktree에 `work/task-0220-final-approval` 생성 → 커밋되지 않았던 기록(재검토 경과, 예외 결정, QA)을 그대로 복사해 `aaff7c2`로 커밋 → 기록 blob이 원본과 같고 두 candidate가 조상임을 확인 → main의 기록 변경 복원 → `git reset --keep a7a28dc`. main 체크아웃은 main을 떠나지 않았다.

결과: 로컬 main, origin/main, 원격 조회가 `a7a28dc`로 일치한다. `jarvis.bat`의 크기와 수정 시각은 전후로 같다. push와 봇 재시작은 하지 않았다. 이 task는 DOING이며 기록은 이 브랜치에만 있다.

## 2단위 절차

- 작업 위치: worktree `jarvis-core-worktrees/task-0220-final-approval`(브랜치 `work/task-0220-final-approval`). 봇이 쓰는 main 체크아웃은 `main_not_checked_out`을 피하려고 main에 둔다.
- Reviewer와 QA를 통과한 candidate는 `44e5ada`까지다. 2단위 baseline은 이 브랜치의 HEAD다.
- 도구: `scripts/commit_candidate.py`, `check_task_record.py`, Console은 각자 자기 체크아웃을 기준으로 동작하므로 worktree 안에서 실행한다.
- 최종 반영: Owner 승인 뒤에만 main을 이 브랜치로 ff-only 한다. 그 전에 main이 움직이면 브랜치를 새 main 위로 옮기고 Reviewer와 QA를 다시 한다.
- 주의: main이 `a7a28dc`인 동안 봇 코드에는 최종 승인 대기가 없어 `/go`는 이전처럼 자동 반영한다. main에서 새 task를 만들면 이 task의 번호 0220을 다시 쓸 수 있다.

## Owner 결정 (원문, 2단위)

```text
브랜치 분리 결과를 확인했다.
현재 상태를 유지하고 task-0220의 2단위를 진행해라.
`/go <id> revise <지시>` 구현
`/go <id> recheck` 구현
revise 후 새 candidate 생성 및 Reviewer·QA 재실행
recheck는 Worker를 호출하지 않고 기존 candidate에 Reviewer·QA만 재실행
검증 통과 후에도 NEEDS_APPROVAL 유지
Owner 최종 승인 전 main 반영 금지
main 체크아웃은 그대로 유지한다.
모든 변경과 검증은 지정된 worktree에서 진행한다.
baseline은 현재 작업 브랜치 HEAD인 `8b40732`다.
기존 1단위 기능과 테스트를 훼손하지 않는다.
`jarvis.bat`은 절대 수정하지 않는다.
Reviewer 및 QA 절차를 준수한다.
self-review를 포함한 모든 검증 방식의 차이는 기록한다.
push하지 않는다.
2단위 구현과 검증이 끝나면 중간 보고해라.
아직 DONE 처리하거나 main에 반영하지 마라.
최종적으로 1·2단위 전체 기능과 테스트 결과를 확인한 뒤 Owner에게 최종 승인 여부를 요청해라.
```

번호와 글머리표만 뺀 Owner 메시지다.

## 2단위 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `8b407323fb4ebc5391ec59ab2c84d571e8ba0a3f` (작업 브랜치 HEAD) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=2`(Owner 증액), `repair_count=2`(아래 Repair 절들). Manager 해석: 새 작업 단위라 SOP 기본값으로 시작한다. 1단위의 Reviewer 예외는 적용하지 않는다 |

## 2단위 구현

- `/go <id> revise <지시>`: 지시 원문을 받아(Manager 해석: 1000자 상한은 승인 문구에 없고 commit과 Reviewer 호출 길이를 위해 정했다) 대기 기록을 대조하고 `revise_candidate`를 돌린다. `_run_pipeline`에 Owner 수정 분기(`_OwnerRevision`)를 더해, 기존 범위 검사·테스트·candidate·Reviewer·repair·QA·대기 단계를 그대로 쓴다. 기록 식별과 main baseline 확인은 accept와 같은 함수이며, 그 거절은 상태를 바꾸지 않는다.
- 지시 원문은 revision commit의 `Owner-Revision:` 줄에 JSON으로 남고 `owner_revisions`가 읽는다. 뒤의 Worker와 Reviewer는 요청과 모든 지시를 받는다.
- 감사 명령은 200자 상한 때문에 `/go <id> revise`로 기록한다. 지시 원문은 commit에 있다.
- `/go <id> recheck`: `recheck_candidate`가 Reviewer와 QA만 돌린다. Worker를 부르지 않는다. 통과면 task 파일을 쓰지 않고 대기를 유지하며 검토 파일을 새로 쓴다. Reviewer가 판정하지 못한 경우는 아무것도 바꾸지 않는다. FINDINGS와 미확인 항목은 `NEEDS_APPROVAL → FAILED`, QA 실패는 대기 유지다(Owner 결정, repair 증액과 recheck 정책 절).
- `_candidate_chain`은 수정 commit과 실행마다의 repair를 허용하는 순서 검사로 바꿨고 수정 commit마다 지시가 정확히 하나 있어야 한다. 자동 repair 수는 commit 제목으로 센다.
- resume은 이전 시도의 지시를 새 시도의 첫 commit에 옮겨 적고 Reviewer에게 넘긴다.
- Worker가 바꾼 것이 없으면 `revise_no_changes`, 변경이 모두 사라지면 `revise_empty_change_set`으로 실패한다.
- Manager 해석: 승인 전이 뒤 Worker가 실패한 revise는 일반 실행 실패(`FAILED`, attempt 보존)로 두었다. 이전 candidate는 사슬과 브랜치에 남고 `resume`으로 이어갈 수 있다.
- 보고에 네 가지 결정 명령을 모두 적었다. Console Next action과 Hold 안내도 맞췄다.
- 테스트 환경: Worker smoke의 임시 clone이 실행 체크아웃의 브랜치를 따라가 작업 브랜치에서 `main_not_checked_out`으로 실패했다. clone을 `main`으로 맞추는 한 줄을 더했다.

## 2단위 검증 (작업 트리, 지정 worktree)

- Self-review 수정 뒤에 돌렸고, repair 뒤에는 candidate 커밋 직전마다 다시 돌렸다(마지막 기준은 Repair 2 뒤 QA). Worker smoke, Console smoke PYTHONUTF8=1과 없음, `run_web_app.py --self-test`, Discord `--self-check-suite`, discord-intake smoke, SOP validator, `node --check`, `git diff --check`를 다시 돌렸다. 수치는 candidate 직전 실행의 결과로 Owner 보고에 적는다.

## Self-review (2단위)

절차 차이: `claude` CLI가 여전히 로그아웃(`loggedIn: false`)이라 SOP §3의 `claude -p --agent self-reviewer` 대신 같은 정의를 세션 subagent로 돌렸다. Reviewer 판정이 아니다. 지적과 처리:

1. major: resume이 Owner 지시를 잃음. 이전 시도의 지시를 새 첫 commit에 옮겨 적고 Reviewer에 넘기게 했다.
2. major: recheck FINDINGS의 FAILED 전환과 1000자 상한의 근거 표시 없음. 구현 절에 출처와 Manager 해석을 적고 도움말·시작 답에 경고를 넣었다.
3. major: 검증 절이 없는데 있다고 적음. 이 절과 검증 절을 더했다.
4. minor: recheck 기록 실패를 무시함. `recheck_transition_failed`로 보고하고 대기를 유지한다.
5. minor: 지시 없는 수정 commit 통과, 음성 테스트 없음. 지시 하나를 요구하고 smoke를 더했다.
6. minor: 지시 판독을 승인 뒤에 하고 `splitlines`를 씀. 승인 전에 읽고 줄바꿈만 나눈다.
7. minor: 변경 없는 revise가 repair 실패로 보임. `revise_no_changes`와 Console 설명을 더했다.
8. minor: 변경이 모두 사라져도 대기로 감. `revise_empty_change_set`으로 실패한다.
9. minor: recheck 보고의 테스트 줄이 비어 있음. 채웠다.
10. minor: 기록 요약과 A15·A27·A30·A33이 2단위 전 표현. 고쳤다.
11. minor: task-model의 recheck 행에 미확인 항목 누락. 더했다.
12. minor: SOP 항 번호 인용 오류. 고쳤다.

self-review subagent는 저장소 worktree 전체를 grep했으나 이 worktree에는 `jarvis.bat`이 없고 `.env`도 추적되지 않는다.

## 2단위 Reviewer 결과 (candidate `4c0d27520b4159ea80c6b6baf51f62badea008fd`)

verdict FINDINGS, self_deviations 없음(유효). 첫 호출은 사용량 한도로 끊겨 같은 Reviewer를 이어서 끝냈다. major 3건, minor 3건:

1. major: commit 전에 실패한 revise의 지시가 resume에 안 넘어감. 2. major: `_cumulative_paths` 합집합 때문에 `revise_empty_change_set`이 도달 불가, 일부 되돌리기는 항상 qa_failed. 3. major: SOP가 미확인 항목의 candidate도 accept 불가라고 적음. 4. minor: recheck의 실패 종결이 승인 원문에 없음. 5. minor: Console의 `reviewer_findings` 설명이 recheck에 맞지 않음. 6. minor: Owner 수정 commit에 repair 진행 표시가 나감.

## 2단위 Repair (`repair_count=1`)

1. 지시를 승인 전이 전에 attempt worktree 옆 `.owner-revision.json`에 저장하고 수정 commit이 끝나면 지운다. resume이 읽어 새 첫 commit에 옮긴다.
2. revise는 commit될 내용과 baseline의 차이(`_net_changed_paths`)를 change set으로 쓴다.
3. SOP 문장을 고쳤다. 미확인 항목은 accept 가능하다.
4. recheck의 실패 종결은 Owner에게 보고해 결정을 받는다(코드 변경 없음).
5. `recheck_findings` 사유와 Console 설명을 따로 두었다.
6. repair 진행 표시는 repair commit에만 나간다.

이전 candidate의 Reviewer 결과는 무효이며 새 candidate에 fresh Reviewer와 QA를 돌린다.

## 2단위 Reviewer 결과 (repair candidate `768ff908fe5c5350f80fa330889deee1d2c1716a`)

verdict FINDINGS, self_deviations 없음(유효). major 1건(resume이 commit 전에 실패한 뒤 다시 resume하면 지시 유실), minor 5건(recheck 종결이 승인 원문에 없음, 검증 절이 repair 전 기준, revise 범위 검사의 rename, 새 resume 사유의 Console 설명, 비워진 candidate에 resume 안내). repair 예산이 소진돼 Owner에게 보고했다.

## Owner 결정 (원문, repair 증액과 recheck 정책)

```text
[Manager 제안]
repair 예산 1회 증액 (권장)
위 지적은 소스 수정이 필요하고, 예산 증액은 Owner만 정할 수 있습니다.
recheck가 문제를 찾았을 때의 동작
Reviewer 지적: 대기 종료, FAILED, accept 불가 유지
QA 미확인 항목: 대기 종료, FAILED, 확인 후 accept 가능 유지
QA 실패: 대기 유지로 변경

[Owner 답]
권장안으로 진행
```

## 2단위 Repair 2 (`repair_count=2`, Owner 증액)

- resume은 지시 전체를 새 시도 옆에 저장해, 첫 commit 전에 실패해도 다시 resume할 때 이어진다.
- recheck의 QA 실패는 대기를 유지한다(Owner 결정). Reviewer 지적과 미확인 항목의 종결은 유지한다.
- revise 범위 검사에 `--no-renames`를 넣었다. 새 resume 사유의 Console 설명을 더했다. 비워진 candidate의 답에서 resume을 뺐다.
- 아래 2단위 검증 절의 수치는 Owner 보고와 QA 결과가 기준이다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다. 오른쪽 칸에서 "Manager 해석"이라고 적은 부분은 승인 원문에 없는 내용이다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문, 작업 지시) | "[Owner 지시]" | 지시의 표지. Manager 해석: 이 task는 Owner 지시 흐름 중 대기·승인·거절 부분이다 |
| A2 | Owner 결정 (원문, 작업 지시) | "첫 번째 작업 목표: 결과 확인 후 반영 구조 구현" | 이 task와 2단위 task의 목표다 |
| A3 | Owner 결정 (원문, 작업 지시) | "Owner의 사전 실행 승인과 최종 반영 승인을 구분한다." | `/go`는 실행 승인, `/go <id> accept`는 반영 승인이다. SOP 9항에 적었다 |
| A4 | Owner 결정 (원문, 작업 지시) | "최종 승인 전에는 main이 절대 변경되지 않아야 한다." | `_run_pipeline`에서 반영 호출을 없앴고 smoke가 HEAD 불변을 확인한다 |
| A5 | Owner 결정 (원문, 작업 지시) | "승인 전 결과물은 candidate 또는 격리된 상태로 보존한다." | attempt 브랜치와 worktree에 남긴다 |
| A6 | Owner 결정 (원문, 작업 지시) | "거절, 수정 요청, 재검토, 승인 흐름을 명확하게 구분한다." | 승인과 거절은 이 task, 수정 요청과 재검토는 A33의 진행 단위 2에서 구현했다 |
| A7 | Owner 결정 (원문, 작업 지시) | "기존 /go, /accept, resume, recover의 동작과 호환성을 확인한다." | Manager 해석: /accept는 실제 명령 /go <id> accept다. smoke가 네 경로를 확인한다. FAILED accept는 기존 그대로다 |
| A8 | Owner 결정 (원문, 작업 지시) | "기존 Reviewer, QA, 실패 복구 구조를 최대한 재사용한다." | Reviewer·QA·repair는 바꾸지 않았고 `accept_candidate`를 재사용했다 |
| A9 | Owner 결정 (원문, 작업 지시) | "jarvis.bat은 절대 수정하지 않는다." | 건드리지 않았다 |
| A10 | Owner 결정 (원문, 설계 승인) | "설계를 검토했다." | 설계 승인의 배경 |
| A11 | Owner 결정 (원문, 설계 승인) | "제안한 정책 결정 4건을 모두 승인한다." | 구현 착수 승인 |
| A12 | Owner 결정 (원문, 설계 승인) | "NEEDS_APPROVAL 상태 재사용" | `DOING → NEEDS_APPROVAL` 1쌍만 더했다 |
| A13 | Owner 결정 (원문, 설계 승인) | "main의 커밋 및 소스 파일은 최종 승인 전까지 불변." | main 커밋과 소스 파일은 accept 전까지 바뀌지 않는다. task 기록의 상태는 작업 트리에서만 바뀐다(A29 결정 2) |
| A14 | Owner 결정 (원문, 설계 승인) | "읽기 전용 보고 기록은 기존 방식 유지" | `run_report`는 바꾸지 않았다 |
| A15 | Owner 결정 (원문, 설계 승인) | "revise는 Owner가 승인한 새로운 실행으로 취급하며, 각 실행의 자동 repair는 최대 1회" | 2단위에서 구현했다. revise마다 repair 상한 1을 새로 쓴다 |
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
| A27 | Owner 결정 (원문, 승인된 설계 제안) | "/go <id> revise <지시>는 수정 요청이고 /go <id> recheck는 재검토다." | Manager 해석: 수정 요청과 재검토는 진행 단위 2에서 구현했다 |
| A28 | Owner 결정 (원문, 승인된 설계 제안) | "결정 1: NEEDS_APPROVAL 재사용. 전이 DOING → NEEDS_APPROVAL 1쌍만 추가." | `DOING → NEEDS_APPROVAL`만 더했다 |
| A29 | Owner 결정 (원문, 승인된 설계 제안) | "결정 2: main의 커밋과 소스 파일 불변. task 기록의 상태 변화는 작업 트리에만 있고 승인 때 커밋. 읽기 전용 보고는 지금처럼 기록만 커밋." | A13·A14와 같다 |
| A30 | Owner 결정 (원문, 승인된 설계 제안) | "결정 3: revise 1회를 Owner가 승인한 새 실행으로 취급. 그 안의 자동 repair는 최대 1회." | 진행 단위 2에서 구현했다 |
| A31 | Owner 결정 (원문, 승인된 설계 제안) | "결정 4: Lead 종합 보고는 이번에 제외." | 포함하지 않았다 |
| A32 | Owner 결정 (원문, 승인된 설계 제안) | "진행 단위 1: 대기 + accept + reject." | 이 task의 범위다 |
| A33 | Owner 결정 (원문, 승인된 설계 제안) | "진행 단위 2: revise + recheck." | 이 task의 2단위로 진행했다 |
| A34 | Owner 결정 (원문, 승인된 설계 제안) | "[Owner 답]" | 답의 표지 |
| A35 | Owner 결정 (원문, 승인된 설계 제안) | "제안한 정책 결정 4건을 모두 승인한다." | A11과 같은 문장이다 |
| A36 | Owner 결정 (원문, retry 증액) | "[Manager 질문]" | 질문의 표지 |
| A37 | Owner 결정 (원문, retry 증액) | "retry 예산 1회는 이미 썼고, 예산 증액은 Owner만 정할 수 있습니다." | A40 답의 질문 배경 |
| A38 | Owner 결정 (원문, retry 증액) | "어떻게 할까요?" | A40 답의 질문 |
| A39 | Owner 결정 (원문, retry 증액) | "[Owner 답]" | 답의 표지 |
| A40 | Owner 결정 (원문, retry 증액) | "retry 1회 증액 (Recommended)" | Owner가 retry 예산을 1 늘렸다. retry 2를 돌렸다 |
| A41 | Owner 결정 (원문, Reviewer 무효 규칙 예외) | "이번 한 건에 한해 Owner 결정으로 현재 candidate `44e5ada`의 Reviewer PASS를 유효한 검토 결과로 인정한다." | 이 결정으로 44e5ada의 Reviewer PASS를 유효로 본다. SOP 무효 규칙의 예외다 |
| A42 | Owner 결정 (원문, Reviewer 무효 규칙 예외) | "동일 candidate에서 PASS, 지적 0건이 두 차례 확인되었고, 무효 사유는 모두 읽기 전용 git 옵션 사용이었다는 점을 고려한 예외 결정이다." | 아래 Reviewer 재검토 경과 절의 사실과 같다 |
| A43 | Owner 결정 (원문, Reviewer 무효 규칙 예외) | "다음 조건으로 진행해라." | 조건의 표지 |
| A44 | Owner 결정 (원문, Reviewer 무효 규칙 예외) | "이번 예외 결정과 사유를 task-0220 기록에 정확히 남긴다." | 이 절과 재검토 경과 절이다 |
| A45 | Owner 결정 (원문, Reviewer 무효 규칙 예외) | "candidate `44e5ada`의 코드는 변경하지 않는다." | `44e5ada` 뒤로 코드를 바꾸지 않았다 |
| A46 | Owner 결정 (원문, Reviewer 무효 규칙 예외) | "기존 절차에 따라 QA를 진행한다." | QA 결과 절이다 |
| A47 | Owner 결정 (원문, Reviewer 무효 규칙 예외) | "QA PASS 후에도 NEEDS_APPROVAL 상태를 유지한다." | Manager 해석이 필요해 Owner에게 보고한다: task-0220 자체는 수동 task라 DOING이고 NEEDS_APPROVAL로 옮기는 경로가 없다. Worker 경로의 대기 동작은 candidate가 구현했다 |
| A48 | Owner 결정 (원문, Reviewer 무효 규칙 예외) | "Owner의 최종 승인 전까지 main에 반영하지 않는다." | Manager 해석이 필요해 Owner에게 보고한다: 수동 SOP candidate는 commit_candidate로 main에 커밋되므로 `341f596`·`44e5ada`는 이미 로컬 main에 있다. push는 하지 않았다 |
| A49 | Owner 결정 (원문, Reviewer 무효 규칙 예외) | "push는 하지 않는다." | 하지 않았다 |
| A50 | Owner 결정 (원문, Reviewer 무효 규칙 예외) | "이번 예외는 task-0220의 해당 Reviewer 검토에만 적용한다." | task-0220의 이 검토에만 적용한다 |
| A51 | Owner 결정 (원문, Reviewer 무효 규칙 예외) | "이후 작업부터는 기존 SOP의 Reviewer 무효 규칙을 그대로 적용한다." | 이 예외를 다른 task의 근거로 쓰지 않는다 |
| A52 | Owner 결정 (원문, 브랜치 분리) | "브랜치로 분리하는 방향을 선택한다." | 이 절의 실행 근거다 |
| A53 | Owner 결정 (원문, 브랜치 분리) | "이번 task-0220의 목적은 Owner 최종 승인 전까지 main을 변경하지 않는 구조를 만드는 것이다." | Manager 해석: 이 task의 수동 candidate 커밋도 Owner 최종 승인 전에는 main에 두지 않는다 |
| A54 | Owner 결정 (원문, 브랜치 분리) | "현재 두 커밋이 로컬 main에 들어간 것은 최초 승인 조건과 맞지 않으므로 다음과 같이 처리해라." | 조건의 표지 |
| A55 | Owner 결정 (원문, 브랜치 분리) | "`341f596`, `44e5ada`를 별도 작업 브랜치에 안전하게 보존한다." | `work/task-0220-final-approval`에 두 커밋이 조상으로 있다 |
| A56 | Owner 결정 (원문, 브랜치 분리) | "로컬 main을 기존 기준점 `a7a28dc`로 복구한다." | `git reset --keep`으로 복구했다 |
| A57 | Owner 결정 (원문, 브랜치 분리) | "origin/main과 로컬 main이 다시 일치하는지 확인한다." | main, origin/main, 원격 조회가 모두 `a7a28dc`다 |
| A58 | Owner 결정 (원문, 브랜치 분리) | "`jarvis.bat`은 절대 건드리지 않는다." | 크기와 수정 시각이 전후로 같다 |
| A59 | Owner 결정 (원문, 브랜치 분리) | "push는 하지 않는다." | 하지 않았다 |
| A60 | Owner 결정 (원문, 브랜치 분리) | "task-0220은 이 단계에서 DONE 처리하지 않는다." | status는 DOING이다 |
| A61 | Owner 결정 (원문, 브랜치 분리) | "2단위 revise/recheck는 분리한 작업 브랜치에서 진행할 수 있도록 상태와 절차를 정리한다." | 아래 2단위 절차 절이다 |
| A62 | Owner 결정 (원문, 브랜치 분리) | "특히 브랜치 분리 전에 현재 작업물과 task 기록, 예외 결정 기록이 모두 보존되는지 확인해라." | 복구 전에 기록 blob과 두 candidate가 브랜치에 있음을 확인했다 |
| A63 | Owner 결정 (원문, 브랜치 분리) | "Git reset이나 branch 이동은 먼저 복구 가능한 백업과 참조점을 확보한 뒤 실행해라." | 복구 전에 백업 ref, bundle, 기록 사본을 만들었다 |
| A64 | Owner 결정 (원문, 브랜치 분리) | "작업이 끝나면 main, origin/main, 작업 브랜치의 HEAD와 task 상태를 각각 보고해라." | Owner 보고에 적었다 |
| A65 | Owner 결정 (원문, 브랜치 분리) | "이번 단계에서는 봇 재시작이나 push를 하지 말고 먼저 보고해라." | 둘 다 하지 않았다 |
| A66 | Owner 결정 (원문, 2단위) | "브랜치 분리 결과를 확인했다." | 지시의 배경 |
| A67 | Owner 결정 (원문, 2단위) | "현재 상태를 유지하고 task-0220의 2단위를 진행해라." | 이 절이 2단위다 |
| A68 | Owner 결정 (원문, 2단위) | "`/go <id> revise <지시>` 구현" | `_run_go`의 revise 분기와 `revise_candidate` |
| A69 | Owner 결정 (원문, 2단위) | "`/go <id> recheck` 구현" | `_run_go`의 recheck 분기와 `recheck_candidate` |
| A70 | Owner 결정 (원문, 2단위) | "revise 후 새 candidate 생성 및 Reviewer·QA 재실행" | 같은 attempt에 새 candidate를 만들고 fresh Reviewer와 QA를 돌린다 |
| A71 | Owner 결정 (원문, 2단위) | "recheck는 Worker를 호출하지 않고 기존 candidate에 Reviewer·QA만 재실행" | smoke가 Worker 호출 0회와 Reviewer 1회를 확인한다 |
| A72 | Owner 결정 (원문, 2단위) | "검증 통과 후에도 NEEDS_APPROVAL 유지" | revise와 recheck가 통과해도 NEEDS_APPROVAL로 끝난다 |
| A73 | Owner 결정 (원문, 2단위) | "Owner 최종 승인 전 main 반영 금지" | main을 바꾸는 호출은 accept의 ff-only뿐이다 |
| A74 | Owner 결정 (원문, 2단위) | "main 체크아웃은 그대로 유지한다." | main 체크아웃과 그 작업 트리를 바꾸지 않았다 |
| A75 | Owner 결정 (원문, 2단위) | "모든 변경과 검증은 지정된 worktree에서 진행한다." | 지정 worktree에서만 변경하고 검증했다(2단위 검증 절) |
| A76 | Owner 결정 (원문, 2단위) | "baseline은 현재 작업 브랜치 HEAD인 `8b40732`다." | 2단위 preflight와 Reviewer baseline은 `8b407323fb4ebc5391ec59ab2c84d571e8ba0a3f`다 |
| A77 | Owner 결정 (원문, 2단위) | "기존 1단위 기능과 테스트를 훼손하지 않는다." | 1단위 smoke를 유지하고 전체를 다시 돌렸다(2단위 검증 절) |
| A78 | Owner 결정 (원문, 2단위) | "`jarvis.bat`은 절대 수정하지 않는다." | 건드리지 않았다 |
| A79 | Owner 결정 (원문, 2단위) | "Reviewer 및 QA 절차를 준수한다." | candidate 뒤의 절차로 진행한다 |
| A80 | Owner 결정 (원문, 2단위) | "self-review를 포함한 모든 검증 방식의 차이는 기록한다." | Self-review (2단위) 절에 적었다 |
| A81 | Owner 결정 (원문, 2단위) | "push하지 않는다." | 하지 않았다 |
| A82 | Owner 결정 (원문, 2단위) | "2단위 구현과 검증이 끝나면 중간 보고해라." | Owner 보고로 한다 |
| A83 | Owner 결정 (원문, 2단위) | "아직 DONE 처리하거나 main에 반영하지 마라." | DOING이고 main에 반영하지 않았다 |
| A84 | Owner 결정 (원문, 2단위) | "최종적으로 1·2단위 전체 기능과 테스트 결과를 확인한 뒤 Owner에게 최종 승인 여부를 요청해라." | QA 뒤 Owner에게 요청한다 |
| A85 | Owner 결정 (원문, repair 증액과 recheck 정책) | "[Manager 제안]" | 제안의 표지 |
| A86 | Owner 결정 (원문, repair 증액과 recheck 정책) | "repair 예산 1회 증액 (권장)" | Owner가 승인해 repair 2를 했다 |
| A87 | Owner 결정 (원문, repair 증액과 recheck 정책) | "위 지적은 소스 수정이 필요하고, 예산 증액은 Owner만 정할 수 있습니다." | A92 답의 배경 |
| A88 | Owner 결정 (원문, repair 증액과 recheck 정책) | "recheck가 문제를 찾았을 때의 동작" | 아래 세 줄의 주제 |
| A89 | Owner 결정 (원문, repair 증액과 recheck 정책) | "Reviewer 지적: 대기 종료, FAILED, accept 불가 유지" | 유지했다 |
| A90 | Owner 결정 (원문, repair 증액과 recheck 정책) | "QA 미확인 항목: 대기 종료, FAILED, 확인 후 accept 가능 유지" | 유지했다 |
| A91 | Owner 결정 (원문, repair 증액과 recheck 정책) | "QA 실패: 대기 유지로 변경" | 대기 유지로 바꿨다 |
| A92 | Owner 결정 (원문, repair 증액과 recheck 정책) | "[Owner 답]" | 답의 표지 |
| A93 | Owner 결정 (원문, repair 증액과 recheck 정책) | "권장안으로 진행" | 위 두 결정의 승인 |
