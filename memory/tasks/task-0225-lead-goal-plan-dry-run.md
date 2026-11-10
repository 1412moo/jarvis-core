# task-0225-lead-goal-plan-dry-run

- id: `task-0225-lead-goal-plan-dry-run`
- title: `Lead 목표 계획 dry-run: 하위 작업 분해와 결정론적 Policy Gate 판정 (실행 없음)`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-11-10 07:39 UTC`
- updated_at: `2026-11-10 09:03 UTC`
- summary: `Owner가 /goal로 목표 하나를 주면 읽기 전용 Lead가 하위 작업(kind, 목적, 의존성, 완료 조건, 순서, 위험도, worker_request)으로 분해하고, 코드의 결정론적 Policy Gate가 작업마다 auto, needs_owner, forbidden을 판정해 Discord에 보여 준다. task 생성, Worker 실행, 배정, Dispatcher, 백그라운드 실행, main 통합은 하지 않는다. 판정 기준은 Owner 승인 전 제안이며 실행 권한이 아니다.`
- source_command: `Owner 지시: Lead Goal Plan Dry-run 1단계 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `c1946fb66763eeb7ab7f798b8840bf2165d304ab` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=1` (SOP §5 기본값, repair 1은 아래 절) |
| 작업 위치 | 저장소 밖 worktree `jarvis-core-worktrees/task-0225-lead-goal-plan`, 브랜치 `work/task-0225-lead-goal-plan`. main 체크아웃은 그대로 둔다 |

## Owner 결정 (원문, 작업 지시)

```text
Jarvis의 최종 목표는 Owner가 개별 작업마다 지시하고 승인하는 시스템이 아니라, Owner가 목표를 주면 Claude Lead가 계획·분해·배정·실행 조율·검증·결과 보고까지 담당하는 자율형 AI 팀이다.
이번 작업은 그 방향으로 가기 위한 1단계: Lead Goal Plan Dry-run이다.
목표
현재의 단일 작업 계획 기능을 확장하여, Owner가 하나의 목표를 입력하면 Lead가 다음 내용을 포함한 하위 작업 계획을 생성하도록 한다.
목표 전체 요약
하위 작업 목록
각 작업의 kind 및 목적
작업 간 선행 조건 및 의존성
각 작업의 완료 조건(acceptance criteria)
예상 작업 순서
작업별 위험도 및 Owner 승인 필요 여부
전체 목표의 예상 진행 흐름
핵심 요구사항
이번 단계에서는 계획만 생성한다. 실제 Worker 실행, 자동 배정, Dispatcher, 백그라운드 실행은 구현하거나 활성화하지 않는다.
기존 Worker의 단일 작업 파이프라인은 유지한다. 향후 하위 작업 실행에 재사용할 수 있도록 설계한다.
Lead가 생성한 작업별 `worker_request`가 실제 Worker에게 전달되어야 한다는 점을 설계에 반영한다. 현재 Owner 원문만 전달되는 구조를 개선할 방안을 제시한다.
작업별 정책 판정은 Lead의 주관적 위험도만으로 결정하지 않는다. 결정론적 Policy Gate를 통해 `auto`, `needs_owner`, `forbidden`으로 분류하는 구조를 제안한다.
보호 경로, 금지 작업, 외부 공개, 데이터 삭제, 비용 지출 등은 임의로 자동 실행 가능하다고 판단하지 않는다.
현재 master-plan 및 SOP에서 자동 실행을 제한하는 규칙을 확인하고, 이번 단계에서 허용되는 범위를 벗어나지 않는다.
기존 Discord 진입점과 Console 구조를 조사하고, `/goal` 명령을 추가할 경우의 구체적인 UX를 제안한다.
작업 방식
우선 현재 코드와 문서를 다시 확인한다.
기존 Lead, Worker, Reviewer, QA, task model의 실제 구조를 기준으로 설계한다.
기존 구현을 불필요하게 변경하지 않는다.
이번 단계는 Dry-run이므로 계획 생성 및 정책 판정 결과를 확인할 수 있는 수준까지만 구현한다.
실제 자동 실행이나 main 통합 자동화는 절대 추가하지 않는다.
테스트를 작성하고 실행하여 기존 기능에 영향이 없는지 검증한다.
Owner에게 제시할 결과
다음 내용을 실제 동작 결과로 확인할 수 있어야 한다.
Owner가 하나의 복합 목표를 입력한다.
Lead가 목표를 여러 하위 작업으로 분해한다.
각 작업의 의존성과 완료 조건을 제시한다.
각 작업에 `auto / needs_owner / forbidden` 정책을 판정한다.
전체 실행 계획을 Owner가 한눈에 검토할 수 있게 보여준다.
아직 실제 실행은 시작하지 않는다.
진행 원칙
이번 작업은 기존 SOP와 승인 경계를 준수한다. 자동 실행 권한이나 예산 한도를 임의로 확정하지 않는다. 필요한 정책 결정이 있다면 근거와 선택지를 보고한다.
작업 완료 시 다음을 보고한다.
구현한 기능
수정한 파일
실제 Dry-run 결과 예시
테스트 결과
현재 Lead가 할 수 있게 된 일과 아직 할 수 없는 일
다음 단계에서 필요한 Owner 결정
중요한 것은 단순히 작업 목록을 출력하는 것이 아니라, 실제 자율 실행 시스템으로 확장할 수 있는 Goal 단위의 계획 구조를 만드는 것이다.
```

번호와 글머리표만 뺀 Owner 메시지다.

## 조사 (baseline 기준)

- 자동 실행 제한: `docs/master-plan.md`의 잠긴 고위험 기능에 외부 API/LLM, 자동 실행, stage, commit, push/PR, Memory 저장, background worker, 모바일 원격 실행이 있다. SOP §9는 dispatcher subsystem, background execution, queue persistence를 별도 승인 전까지 금지하고 §10(Worker 파이프라인과 팀장 단계)만 예외다.
- 팀장(`orchestrator/worker/claude_lead.py`)은 §10의 팀장 단계다. 읽기 전용(Read·Grep·Glob, plan 모드, `--tools`, `--strict-mcp-config`)으로 HEAD의 임시 detached worktree에서 한 번 실행하고, 정해진 필드만 받아 형식이 어긋나면 실패한다. 계획 하나는 작업 종류 하나와 TODO task 하나만 만든다.
- Worker와 Reviewer는 Owner의 `/work` 원문만 받는다(`bot_minimal._worker_request_for`). 팀장의 `worker_request`는 Owner에게 보이기만 한다(SOP §10.1 팀장 문단).
- task 모델에는 목표, 상위 task, 의존성 필드가 없다(`docs/task-model.md`).
- Discord: `_run_command`는 `startswith`로 분기해 `/goal`이 지금은 `/go`로 간다. 권한 검사는 접두어도 특권으로 보므로 `/goal`은 이미 Owner 전용으로 분류된다.
- Console은 task 상태 화면과 Preview + Confirm 전이만 하고 팀장이나 Worker를 부르지 않는다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/worker/goal_plan.py`(새 파일), `orchestrator/worker/policy_gate.py`(새 파일), `orchestrator/worker/claude_lead.py`, `orchestrator/worker/run_smoke_tests.py`, `adapters/discord/bot_minimal.py`, `adapters/discord/README.md`, `docs/jarvis-multi-agent-sop-v0.1.md`, `docs/lead-goal-plan-design.md`(새 파일), 이 task 기록 |
| deny | `orchestrator/worker/claude_worker.py`, Console, `docs/task-model.md`, `docs/master-plan.md`, task 생성·Worker 실행·배정·Dispatcher·큐·백그라운드 실행·main 통합, 다른 task 기록, validator, `jarvis.bat`, `.env`, push, 봇 재시작 |

## Start

Console(worktree에서 띄움) Voice Inbox의 Create Local Task Preview를 확인하고 Confirm해 TODO 기록을 만들었다. Project Control의 Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다. Console은 수정 전에 껐다. 그 뒤 title·summary·source_command를 이 task 내용으로 고쳤다.

## 구현

- `orchestrator/worker/goal_plan.py`(새 파일): 목표 계획 v1의 데이터 구조(`GoalPlan`, `GoalTask`), 팀장 프롬프트, 엄격한 JSON 파서. 필드 집합이 정확히 같아야 하고 길이·개수 제한, id 형식, 등록된 kind, 방식, 위험도, 선행 작업의 존재·자기 참조·순환, `order`가 모든 id를 선행 작업 먼저 담는지 검사한다. 어긋나면 `goal_answer_malformed:<사유>`. 답 전체를 감싼 코드 fence 하나만 벗긴다. 선행 작업으로 단계를 계산하고 계획의 sha256(`plan_digest`)을 만든다.
- `orchestrator/worker/policy_gate.py`(새 파일): 결정론적 판정 v0(`policy-gate-v0-dry-run`). 보호 경로, 모든 `jarvis.bat`, `.env` 계열, `.git` 내부, 저장소 밖 경로는 forbidden. kind 없는 수정, 경로 없는 수정, kind 허용 경로 밖, 와일드카드, 일곱 범주의 신호 문구(외부 공개·전송, 삭제, 비용, 외부 서비스, 보안·권한, 설치·의존성, 자동·백그라운드 실행), 팀장의 Owner 결정 사유, 팀장 위험도 high, auto가 아닌 선행 작업은 needs_owner. 나머지는 auto. 팀장의 말은 판정을 엄격하게만 만든다. 영어 낱말은 ASCII 단어 경계로 찾는다.
- `orchestrator/worker/claude_lead.py`: `run_lead`의 실행 단계(잠금, 임시 worktree, 호출, 정리, 종료 코드)를 `_consult`로 옮기고 `run_lead`와 새 `run_goal_plan`이 함께 쓴다. `run_lead`의 동작은 바꾸지 않았다(기존 팀장 smoke 그대로 통과). `run_goal_plan`은 계획, 판정, hash, CLI 사용량 추정을 돌려준다.
- `adapters/discord/bot_minimal.py`: Owner 전용 `/goal <목표>`(1500자 이하). `_run_command`에서 `/go`보다 먼저 첫 낱말이 정확히 `/goal`일 때만 받는다. on_message가 스레드를 열고 `_run_goal_job`을 백그라운드로 돌려 `_goal_reply_messages`의 메시지들을 보낸다. job은 task 기록과 Worker를 건드리지 않고, git은 기존 `/work` 팀장과 같은 임시 팀장 worktree의 추가·제거 말고는 바꾸지 않으며, 저장소 밖 계획 파일 하나만 쓴다(`JARVIS_GOAL_PLAN_DIR`, 저장소 안이면 쓰지 않음). `/help`와 지원 명령 안내에 `/goal`을 더했다.
- `orchestrator/worker/run_smoke_tests.py`: `goal_flow`(파서 정상·fence·hash, 형식 오류 27종, 판정 규칙과 단방향성, 선행 작업 전파, 팀장 잠금 공유, 실패 시 모델 문구 미노출, `/goal` 권한·사용법·길이, job이 task·commit·파일을 바꾸지 않음, 계획 파일 내용, 2000자 메시지 분할, 멘션 무력화, 저장소 안 폴더 거절, 처리기 소스 검사).
- 문서: SOP §10.1 진입 명령 행과 목표 계획 dry-run 문단, Discord README `/goal` 절, 설계 기록 `docs/lead-goal-plan-design.md`(목표 계획 구조, Policy Gate, `worker_request` 전달 방안, `/goal`·Console UX 제안, 다음 Owner 결정).
- Manager 해석: 계획 파일은 실행 보고 파일과 같은 성격의 검토 자료로 두었다. 아무 코드도 다시 읽지 않으므로 SOP §9의 queue persistence가 아니다. 승인 원문에는 계획 파일 언급이 없다.
- Manager 해석: 팀장 시간 제한은 기존 300초를 그대로 쓴다. 판정 신호 목록과 forbidden 기준은 제안이며 승인 원문의 "확정하지 않는다"에 따라 실행 권한과 연결하지 않았다.

## Implementer 검증 (작업 트리, candidate 전)

- Worker smoke total=748 failed=0(새 goal·gate 검사 40건 포함, 기존 팀장 검사 그대로 통과), SOP validator PASS, Discord `--self-check-suite` rc=0, Console `--self-test`와 smoke rc=0, discord-intake smoke rc=0, `git diff --check` 통과.
- 첫 smoke 실행에서 6건이 실패해 고쳤다: 한글이 붙은 "PR이"에서 단어 경계가 잡히지 않음(`re.ASCII`로 고침), 테스트 자료의 Worker 지시가 300자 제한을 넘음, 처리기 소스 검사의 위치 문자열. 그 뒤 깊게 중첩된 답이 파서를 예외로 끝내지 않게 `run_goal_plan`에 실패 처리를 더하고 smoke를 다시 돌렸다(위 수치).

## Self-review

SOP §3대로 staged 변경에 `claude -p --agent self-reviewer --tools Read,Grep,Glob`을 한 번 돌렸다(Reviewer 판정 아님). minor 세 건과 처리:

1. 기록이 job은 git을 건드리지 않는다고 적었는데 팀장은 임시 worktree를 추가·제거하고, 소스 검사는 job 함수 본문만 본다. 구현 절, A13, A28을 고치고 smoke의 상태 비교에 `git worktree list --porcelain`을 더했다.
2. SOP 진입 명령 행에서 `/goal`이 Worker 잠금 문장 앞에 있어 `worker_busy`를 쓰는 것처럼 읽히고, "아무것도 만들거나"가 계획 파일 쓰기와 어긋났다. 행 안 설명을 팀장 잠금·`lead_busy`와 "task를 만들거나 실행하지 않고"로 고쳤다.
3. A26에 `PRIVILEGED_COMMANDS`와 지원 명령 안내 문구 변경이 빠졌다. 더했다.

수정 뒤 Worker smoke, SOP validator, 사전 점검을 다시 돌렸다(아래 Implementer 검증 절의 수치는 수정 뒤 실행).

## 실제 dry-run (2026-11-10, 작업 트리 코드)

- 방법: 봇 재시작은 승인 밖이라, worktree의 `bot_minimal._run_goal_job`과 `_goal_reply_messages`를 실제 `claude` CLI로 직접 실행했다. Discord 전송만 빠졌고 팀장 호출, 판정, 계획 파일, 메시지 내용은 `/goal`과 같다.
- 목표(입력 원문): "Studyroom 용어집에 RAG와 임베딩 용어를 추가하고, Daily AI Radar 보고서 머리말 문구를 더 읽기 쉽게 다듬은 뒤, 두 변경을 각 앱 README의 변경 기록에 적고, 마지막으로 결과를 GitHub에 push해 줘."
- 결과: 62초, 팀장 사용량 추정 $0.45, `goal-20261110-080023-693`, 계획 hash `8ba066b1411b…`, 메시지 3개(1035·1541·1822자).
- 하위 작업 5개, 판정 auto 4 · needs_owner 1 · forbidden 0, 3단계:
  - 1단계 T1(Studyroom 용어집에 RAG·임베딩 추가, auto), T2(Radar 보고서 머리말 문구, auto)
  - 2단계 T3(Studyroom README 변경 기록, T1 뒤, auto), T4(Radar README Change Log, T2 뒤, auto)
  - 3단계 T5(GitHub push, T1~T4 뒤, needs_owner: 등록된 작업 종류 밖, 변경 경로 없음, 외부 공개·전송, 팀장이 Owner 결정 필요로 표시)
- 목표 문장의 주의 신호: 외부 공개·전송. 실행 뒤 main과 worktree의 git 상태는 그대로였고 임시 팀장 worktree는 남지 않았다. 계획 파일은 `%LOCALAPPDATA%\jarvis-core\goal-plans\`에 하나 생겼다.

## Reviewer 결과 (candidate `6576e61e561041179f8c85e45ae40a1b4fdae439`)

verdict FINDINGS, `self_deviations` 없음(유효). major 2건, minor 2건:

1. major: 보호 경로와 `.git` 비교가 대소문자를 구분해 `apps/studyroom/Studyroom.BAT`, `OpenRouter_Advisor.py`, `.GIT/config` 같은 변형이 auto가 된다.
2. minor: 최대 길이 입력에서 개요 끝의 실행 안 함 안내·계획 hash와 작업 블록의 판정 근거가 2000자 자르기로 잘린다.
3. major: 요약 A14의 "백그라운드 Worker 실행이 아니다"가 승인 원문의 "백그라운드 실행"을 좁혔다. `/goal`은 팀장 계획을 이벤트 루프 밖에서 돌린다.
4. minor: 요약 A27이 계획 파일을 승인 원문이 뒷받침하는 것처럼 적었다(Manager 해석).

Reviewer unverified: 검사 실행 결과, 실제 dry-run, `run_lead` 동작 불변(읽기로만 확인), `usage_of`가 예외 처리 밖에 있음, SOP 변경과 master-plan 잠금의 일관성. 3·4는 소스 수정이 아니라 Owner 결정이 필요해 아래와 같이 물었다.

## Owner 결정 (원문, Reviewer 지적 질문)

```text
[Manager 질문]
Reviewer 지적(major): 승인 원문은 '백그라운드 실행은 구현하거나 활성화하지 않는다'입니다. /goal은 기존 /work 팀장과 똑같이, 읽기 전용 팀장 계획 1회를 봇 이벤트 루프 밖 스레드에서 돌리고 끝나면 결과를 스레드에 올립니다(Worker·큐·상시 실행 없음). 이것을 금지된 '백그라운드 실행'으로 볼까요?
Reviewer 지적(minor): /goal은 계획 전체를 저장소 밖 %LOCALAPPDATA%\jarvis-core\goal-plans\<goal-id>.json에 검토 자료로 남깁니다(아무 코드도 다시 읽지 않음). 승인 원문에 없는 Manager 해석입니다. 유지할까요?

[Owner 답]
허용: 계획 1회는 금지 대상 아님
유지
```

## Repair 1 (`repair_count=1`)

- 지적 1: `policy_gate._is_protected`가 경로와 `PROTECTED_PATHS`를 소문자로 맞춰 비교하고 `.git`도 대소문자 무시로 본다. smoke에 `JARVIS.BAT`, `apps/studyroom/Studyroom.BAT`, `.GIT/config`, `apps/studyroom/.ENV`, `OpenRouter_Advisor.py` 변형을 더했다.
- 지적 2: `_fit_head_tail`이 개요의 끝(주의 신호, 계획 파일, hash, 사용량, 실행 안 함 안내)과 작업 블록의 판정 근거를 온전히 두고 앞쪽 자유 문장만 자른다(끝 줄은 줄마다 500자 상한). smoke에 파서 최대 길이 계획을 더했다.
- 지적 3·4: Owner 답에 따라 동작은 그대로 두고 요약 A14·A27의 근거를 Owner 답으로 고쳤다.
- unverified 중 `usage_of`: 같은 stdout을 읽으므로 `run_goal_plan`의 예외 처리 안으로 옮기고, 최상위 stdout이 너무 깊은 경우의 smoke를 더했다.
- 이전 candidate의 Reviewer 결과는 무효이며 새 candidate에 fresh Reviewer와 QA를 돌린다.
- repair 뒤 검증(작업 트리): Worker smoke total=750 failed=0, SOP validator, Discord self-check, `git diff --check`, 사전 점검.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문, 작업 지시) | "Jarvis의 최종 목표는 Owner가 개별 작업마다 지시하고 승인하는 시스템이 아니라, Owner가 목표를 주면 Claude Lead가 계획·분해·배정·실행 조율·검증·결과 보고까지 담당하는 자율형 AI 팀이다." | 방향 설명. 이번 task는 그중 계획·분해만 구현한다 |
| A2 | Owner 결정 (원문, 작업 지시) | "이번 작업은 그 방향으로 가기 위한 1단계: Lead Goal Plan Dry-run이다." | 이 task의 범위 |
| A3 | Owner 결정 (원문, 작업 지시) | "현재의 단일 작업 계획 기능을 확장하여, Owner가 하나의 목표를 입력하면 Lead가 다음 내용을 포함한 하위 작업 계획을 생성하도록 한다." | 기존 팀장 실행 단계를 공유하는 `run_goal_plan`과 `/goal`. `/work` 팀장은 그대로다 |
| A4 | Owner 결정 (원문, 작업 지시) | "목표 전체 요약" | `goal_summary` |
| A5 | Owner 결정 (원문, 작업 지시) | "하위 작업 목록" | `tasks` 1~8개 |
| A6 | Owner 결정 (원문, 작업 지시) | "각 작업의 kind 및 목적" | `kind`(등록 종류 또는 none), `purpose`. Manager 해석: 방식(`mode`)과 경로(`paths`)도 판정에 필요해 더했다 |
| A7 | Owner 결정 (원문, 작업 지시) | "작업 간 선행 조건 및 의존성" | `depends_on`, 순환·없는 id 거절, 단계 계산 |
| A8 | Owner 결정 (원문, 작업 지시) | "각 작업의 완료 조건(acceptance criteria)" | `acceptance` 1~5개 |
| A9 | Owner 결정 (원문, 작업 지시) | "예상 작업 순서" | `order`, 선행 작업이 먼저인지 검사. 개요에 단계별 순서로 보인다 |
| A10 | Owner 결정 (원문, 작업 지시) | "작업별 위험도 및 Owner 승인 필요 여부" | 팀장 `risk`·`owner_decision`과 Policy Gate 판정 |
| A11 | Owner 결정 (원문, 작업 지시) | "전체 목표의 예상 진행 흐름" | `flow`와 단계 |
| A12 | Owner 결정 (원문, 작업 지시) | "핵심 요구사항" | 아래 행들의 표제 |
| A13 | Owner 결정 (원문, 작업 지시) | "이번 단계에서는 계획만 생성한다." | job은 task 기록과 Worker를 건드리지 않고, git은 임시 팀장 worktree(기존 `/work` 팀장과 같음)의 추가·제거만 한다. smoke가 job 뒤 task 목록, HEAD, status, 브랜치, worktree 목록 불변을 확인한다 |
| A14 | Owner 결정 (원문, 작업 지시) | "실제 Worker 실행, 자동 배정, Dispatcher, 백그라운드 실행은 구현하거나 활성화하지 않는다." | 구현하지 않았다. 팀장 계획 1회는 기존 `/work` 팀장처럼 봇의 이벤트 루프 밖 스레드에서 돈다. 이것이 금지된 백그라운드 실행이 아니라는 것은 질문 A50~A52에 대한 Owner 답 A57이다 |
| A15 | Owner 결정 (원문, 작업 지시) | "기존 Worker의 단일 작업 파이프라인은 유지한다." | `claude_worker.py`를 바꾸지 않았다 |
| A16 | Owner 결정 (원문, 작업 지시) | "향후 하위 작업 실행에 재사용할 수 있도록 설계한다." | 하위 작업 하나 = 실행 한 번(kind, paths, mode, acceptance). 설계 기록 4절 |
| A17 | Owner 결정 (원문, 작업 지시) | "Lead가 생성한 작업별 `worker_request`가 실제 Worker에게 전달되어야 한다는 점을 설계에 반영한다." | 작업마다 `worker_request`를 받고 계획 hash를 둔다. 전달 방식은 설계 기록 5절 |
| A18 | Owner 결정 (원문, 작업 지시) | "현재 Owner 원문만 전달되는 구조를 개선할 방안을 제시한다." | 설계 기록 5절의 지시 묶음. 구현은 하지 않았다 |
| A19 | Owner 결정 (원문, 작업 지시) | "작업별 정책 판정은 Lead의 주관적 위험도만으로 결정하지 않는다." | 판정은 코드 규칙이고 팀장 위험도는 high일 때 엄격하게만 쓴다 |
| A20 | Owner 결정 (원문, 작업 지시) | "결정론적 Policy Gate를 통해 `auto`, `needs_owner`, `forbidden`으로 분류하는 구조를 제안한다." | `policy_gate.py` v0와 설계 기록 3절 |
| A21 | Owner 결정 (원문, 작업 지시) | "보호 경로, 금지 작업, 외부 공개, 데이터 삭제, 비용 지출 등은 임의로 자동 실행 가능하다고 판단하지 않는다." | 보호 경로는 forbidden, 외부 공개·삭제·비용 등 일곱 범주는 needs_owner. smoke가 범주마다 확인한다 |
| A22 | Owner 결정 (원문, 작업 지시) | "현재 master-plan 및 SOP에서 자동 실행을 제한하는 규칙을 확인하고, 이번 단계에서 허용되는 범위를 벗어나지 않는다." | 조사 절. SOP 문단에 §9 예외를 넓히지 않는다고 적었다 |
| A23 | Owner 결정 (원문, 작업 지시) | "기존 Discord 진입점과 Console 구조를 조사하고, `/goal` 명령을 추가할 경우의 구체적인 UX를 제안한다." | `/goal` 구현과 설계 기록 6·7절의 다음 단계 UX 제안. Console은 바꾸지 않았다 |
| A24 | Owner 결정 (원문, 작업 지시) | "우선 현재 코드와 문서를 다시 확인한다." | 조사 절 |
| A25 | Owner 결정 (원문, 작업 지시) | "기존 Lead, Worker, Reviewer, QA, task model의 실제 구조를 기준으로 설계한다." | 조사 절과 설계 기록 4·5절 |
| A26 | Owner 결정 (원문, 작업 지시) | "기존 구현을 불필요하게 변경하지 않는다." | 기존 코드 변경은 `run_lead`의 실행 단계를 공유 함수로 옮긴 것, `/goal` 분기·도움말, 지원 명령 안내 문구, `PRIVILEGED_COMMANDS`에 `/goal`을 명시한 것(접두어 판정에 기대지 않으려고)뿐이다 |
| A27 | Owner 결정 (원문, 작업 지시) | "이번 단계는 Dry-run이므로 계획 생성 및 정책 판정 결과를 확인할 수 있는 수준까지만 구현한다." | 계획과 판정을 보인다. 계획 파일은 승인 원문에 없는 Manager 해석이었고 질문 A53~A55에 대한 Owner 답 "유지"로 남긴다 |
| A28 | Owner 결정 (원문, 작업 지시) | "실제 자동 실행이나 main 통합 자동화는 절대 추가하지 않는다." | 추가하지 않았다. smoke의 소스 검사가 `_run_goal_job` 본문(그 함수만)에 task writer, Worker, pipeline, git 호출이 없음을 확인하고, 실행 검사가 job 전후 저장소 상태 불변을 확인한다 |
| A29 | Owner 결정 (원문, 작업 지시) | "테스트를 작성하고 실행하여 기존 기능에 영향이 없는지 검증한다." | `goal_flow`와 기존 smoke 전부. 검증 절 |
| A30 | Owner 결정 (원문, 작업 지시) | "Owner에게 제시할 결과" | 아래 행들의 표제 |
| A31 | Owner 결정 (원문, 작업 지시) | "다음 내용을 실제 동작 결과로 확인할 수 있어야 한다." | 실제 dry-run 절. Manager 해석: 봇 재시작은 승인 밖이라 같은 job과 메시지 함수를 실제 `claude` CLI로 직접 실행했다 |
| A32 | Owner 결정 (원문, 작업 지시) | "Owner가 하나의 복합 목표를 입력한다." | 실제 dry-run 절의 목표 |
| A33 | Owner 결정 (원문, 작업 지시) | "Lead가 목표를 여러 하위 작업으로 분해한다." | 실제 dry-run 절 |
| A34 | Owner 결정 (원문, 작업 지시) | "각 작업의 의존성과 완료 조건을 제시한다." | 작업 블록의 선행 작업과 완료 조건 |
| A35 | Owner 결정 (원문, 작업 지시) | "각 작업에 `auto / needs_owner / forbidden` 정책을 판정한다." | 작업 블록의 판정과 근거 |
| A36 | Owner 결정 (원문, 작업 지시) | "전체 실행 계획을 Owner가 한눈에 검토할 수 있게 보여준다." | 개요 메시지(판정 집계와 단계별 순서) |
| A37 | Owner 결정 (원문, 작업 지시) | "아직 실제 실행은 시작하지 않는다." | 개요의 마지막 줄이 실행하지 않았음을 밝힌다 |
| A38 | Owner 결정 (원문, 작업 지시) | "이번 작업은 기존 SOP와 승인 경계를 준수한다." | SOP 수동 절차(worktree, Reviewer, QA, Owner 최종 승인 전 main 불변)를 따른다 |
| A39 | Owner 결정 (원문, 작업 지시) | "자동 실행 권한이나 예산 한도를 임의로 확정하지 않는다." | 판정 기준을 제안으로 표시했고 예산 값은 정하지 않았다 |
| A40 | Owner 결정 (원문, 작업 지시) | "필요한 정책 결정이 있다면 근거와 선택지를 보고한다." | 설계 기록 8절과 Owner 보고 |
| A41 | Owner 결정 (원문, 작업 지시) | "작업 완료 시 다음을 보고한다." | Owner 보고의 형식 |
| A42 | Owner 결정 (원문, 작업 지시) | "구현한 기능" | 구현 절 |
| A43 | Owner 결정 (원문, 작업 지시) | "수정한 파일" | 범위 절 owned 행 |
| A44 | Owner 결정 (원문, 작업 지시) | "실제 Dry-run 결과 예시" | 실제 dry-run 절 |
| A45 | Owner 결정 (원문, 작업 지시) | "테스트 결과" | 검증 절 |
| A46 | Owner 결정 (원문, 작업 지시) | "현재 Lead가 할 수 있게 된 일과 아직 할 수 없는 일" | Owner 보고 |
| A47 | Owner 결정 (원문, 작업 지시) | "다음 단계에서 필요한 Owner 결정" | 설계 기록 8절과 Owner 보고 |
| A48 | Owner 결정 (원문, 작업 지시) | "중요한 것은 단순히 작업 목록을 출력하는 것이 아니라, 실제 자율 실행 시스템으로 확장할 수 있는 Goal 단위의 계획 구조를 만드는 것이다." | 검증된 구조(단계, hash, 판정 버전)와 저장소 밖 계획 파일. 다음 단계의 Goal Store·Dispatcher·지시 묶음의 입력 형식이다 |
| A49 | Owner 결정 (원문, Reviewer 지적 질문) | "[Manager 질문]" | Reviewer 지적 3·4에 대한 bounded question의 표지 |
| A50 | Owner 결정 (원문, Reviewer 지적 질문) | "Reviewer 지적(major): 승인 원문은 '백그라운드 실행은 구현하거나 활성화하지 않는다'입니다." | Reviewer 지적 3 |
| A51 | Owner 결정 (원문, Reviewer 지적 질문) | "/goal은 기존 /work 팀장과 똑같이, 읽기 전용 팀장 계획 1회를 봇 이벤트 루프 밖 스레드에서 돌리고 끝나면 결과를 스레드에 올립니다(Worker·큐·상시 실행 없음)." | 실제 동작 설명. 코드와 같다 |
| A52 | Owner 결정 (원문, Reviewer 지적 질문) | "이것을 금지된 '백그라운드 실행'으로 볼까요?" | 답은 A57 |
| A53 | Owner 결정 (원문, Reviewer 지적 질문) | "Reviewer 지적(minor): /goal은 계획 전체를 저장소 밖 %LOCALAPPDATA%\jarvis-core\goal-plans\<goal-id>.json에 검토 자료로 남깁니다(아무 코드도 다시 읽지 않음)." | Reviewer 지적 4 |
| A54 | Owner 결정 (원문, Reviewer 지적 질문) | "승인 원문에 없는 Manager 해석입니다." | A27 행에 그렇게 적었다 |
| A55 | Owner 결정 (원문, Reviewer 지적 질문) | "유지할까요?" | Owner 답은 "유지". 계획 파일 쓰기를 그대로 둔다 |
| A56 | Owner 결정 (원문, Reviewer 지적 질문) | "[Owner 답]" | 답의 표지 |
| A57 | Owner 결정 (원문, Reviewer 지적 질문) | "허용: 계획 1회는 금지 대상 아님" | 팀장 계획 1회를 이벤트 루프 밖에서 돌리는 현재 방식을 유지한다. 이 답은 이 task에만 효력이 있다 |
