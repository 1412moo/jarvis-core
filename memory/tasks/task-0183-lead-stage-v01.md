# task-0183-lead-stage-v01

- id: `task-0183-lead-stage-v01`
- title: `팀장(Lead) 단계 v0.1`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-22 05:30 UTC`
- updated_at: `2026-10-22 07:06 UTC`
- summary: `Worker 파이프라인 앞에 팀장(Lead) 단계를 더한다. 작업 종류 표지어가 없는 /work 요청이면 읽기 전용 Claude 팀장이 저장소를 살펴 계획(작업 종류, 단계, 위험도, Owner 결정 필요 여부)을 세워 Discord에 올리고, 기존 작업 종류에 맞으면 그 종류의 TODO task를 만들어 /go를 안내하며 맞지 않으면 이유만 보고한다. 실행은 지금처럼 Owner의 /go로만 시작하고 새 비용·외부 연결은 없다.`
- source_command: `Owner 지시: 팀장 단계 v0.1 시작 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `e069fa07b2febe80bc9de973404843713d70cbe0` (등록 시점 main HEAD) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |
| 배경 | Owner의 최종 목표(Discord 지시 → AI 팀장 계획·배분 → 실무·검토·수정 → 보고) 대비 현황 조사에서 가장 큰 병목이 팀장 단계 부재로 확인됨 |

## Owner 결정 (원문)

```text
[Manager 제안]
첫 번째로 실행할 작업: "팀장(Lead) 단계 v0.1"
- 내용: Discord에 자연어로 지시하면(또는 마커 없는 /work) Claude 팀장이 읽기 전용으로 저장소를 조사해 계획을 만들고, 그 계획을 Discord에 올립니다.
  - 계획에 담는 것: 무엇을 할지, 어느 작업 종류와 경로인지, 위험도, 승인이 필요한지
  - 기존 작업 종류에 맞으면 그 종류로 배정하고, 맞지 않으면 이유와 함께 "새 작업 종류 필요"로 보고합니다.
  - Owner가 /go 한 번만 누르면 기존 Worker → Reviewer → 수정 → QA → 반영이 이어집니다.
  - 각 단계의 의견(팀장 계획, Reviewer 지적, Worker 수정)을 Discord 스레드에 그대로 보여 줍니다.
- 필요한 승인: SOP §10.1(Worker 파이프라인의 실행 범위)을 넓히는 일이라, 시작하려면 이 task를 승인해 주셔야 합니다. 외부 연결과 비용은 없습니다.
팀장 단계 v0.1 task를 등록하고 시작할까요? 승인하시면 이 세션에서 등록, 구현, 검토까지 진행하겠습니다.

[Owner 답]
시작해
```

## Owner 결정 2: 진행 표시와 스레드 (원문)

```text
[Manager 질문]
처음 제안에는 "각 단계의 의견(팀장 계획, Reviewer 지적, Worker 수정)을 Discord 스레드에 그대로 보여 줍니다"가 있었는데, 지금 구현은 팀장 계획만 보여 줍니다. Reviewer 지적과 수정 과정을 보이려면 승인 범위 밖(deny)인 Worker 실행 코드 claude_worker.py를 조금 고쳐야 합니다.
1. (권장) claude_worker.py의 최소 변경을 이번 범위에 넣습니다.
2. 이번에는 팀장 계획만 보이도록 범위를 줄이고, 지적·수정 표시와 스레드는 다음 task(v0.2)로 넘깁니다.

[Owner 답]
1번으로 진행해 줘.
이번 task에 `claude_worker.py`의 최소 변경을 포함해서 Reviewer의 지적 요지, Worker의 수정 진행, 재검토 결과가 Discord에 표시되도록 해 줘. 작업별 Discord 스레드에 팀장 계획부터 최종 결과까지 모으는 것도 포함해 줘.
다만 범위를 불필요하게 넓히지는 마.

* 기존 Worker → Reviewer → 수정 → QA → DONE 파이프라인과 승인 정책은 최대한 그대로 유지할 것.
* Reviewer 지적과 수정 결과는 기존 실행 결과에서 확인 가능한 내용을 전달하고, 새로운 판단이나 결과를 만들어 내지 말 것.
* Discord 알림 실패가 작업 자체의 성공·실패 판정을 부당하게 바꾸지 않도록 처리할 것.
* 민감한 정보나 불필요한 전체 프롬프트를 Discord에 노출하지 말고, 지적 요지와 수정 결과만 표시할 것.
* 기존 테스트와 종단 테스트를 갱신해 정상 흐름, Reviewer 지적 후 수정, 재검토, 알림 실패를 검증할 것.
* 변경 파일과 승인 범위를 확인하고, 추가 범위가 필요하면 먼저 보고할 것.

구현 후 candidate를 만들고 Reviewer → QA → 완료 절차를 진행해 줘. 중간에 유효한 지적이 나오면 무조건 중단하기보다 현재 승인된 수정 범위와 남은 repair 예산 안에서 해결을 시도해 줘. Owner 결정이 반드시 필요한 경우에만 멈추고 이유를 설명해 줘.
```

## 설계 (v0.1)

1. 진입: `/work <요청>`에 작업 종류 표지어가 있으면 지금과 같다. 없으면(지금은 `unsupported_work_kind` hold) 팀장 단계로 간다. 자연어 일반 메시지의 팀장 연결은 v0.1에서 하지 않는다(자연어 처리 경로와 그 테스트 계약을 따로 바꿔야 함).
2. 팀장 실행: 새 모듈 `orchestrator/worker/claude_lead.py`. 기존 Worker와 같은 `claude` CLI(현재 로그인, 새 비용 없음)를 `-p`로 저장소 루트에서 읽기 전용으로 부른다(Read·Grep·Glob만 허용, 편집·Bash·웹 도구 금지, plan 권한 모드, 시간 제한). 한 번에 하나만 돌고, Worker 잠금은 잡지 않는다(파일을 바꾸지 않음).
3. 팀장 출력: 정해진 필드(작업 종류 또는 none, 제목, 단계, 위험도, Owner 결정 필요 여부, Worker 지시)만 받고, 형식이 하나라도 어긋나면 실패로 본다(fail closed).
4. 결과 처리: 작업 종류가 등록된 종류면 그 종류의 표지어를 붙인 제목으로 기존 `/task` 경로의 TODO task를 만들고 계획과 `/go <task-id>`를 Discord에 올린다. none이거나 실패면 task를 만들지 않고 이유를 보고한다. Owner 결정 필요로 표시되면 그 사유를 함께 보인다. 실행은 Owner의 `/go`로만 시작한다.
5. (Owner 결정 2로 바뀜) 작업별 Discord 스레드에 팀장 계획, 진행, Reviewer 판정·지적 요지, Worker 수정 결과, 최종 결과를 모은다. 지적 요지와 수정 결과는 파이프라인이 이미 가진 값(Reviewer 보고의 findings 발췌, 수정 candidate의 변경 파일과 테스트 요약)만 쓰고, 알림 실패는 판정에 영향을 주지 않는다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/worker/claude_lead.py`(새 파일), `orchestrator/worker/claude_worker.py`(Owner 결정 2: 진행 알림에 Reviewer 판정·지적 요지와 수정 결과를 싣는 최소 변경), `orchestrator/worker/run_smoke_tests.py`, `adapters/discord/bot_minimal.py`, `adapters/discord/README.md`, `docs/jarvis-multi-agent-sop-v0.1.md`(§10.1 표의 지원 작업 행과 팀장 단계 문단, 진행 알림·스레드 문장 포함), `memory/tasks/task-0183-lead-stage-v01.md` |
| deny | `jarvis.bat`, `claude_worker.py`의 진행 알림 밖(판정·repair·QA·반영 로직), writer·Console, AGENTS·agent 정의, 다른 task 기록, 외부 API·credential·새 의존성, 보호 worktree |

## 계획

1. `claude_lead.py`: 프롬프트(등록된 작업 종류 목록 포함), 읽기 전용 실행, 출력 파서, 결과 형식. 실행기는 테스트에서 바꿔 끼울 수 있게 한다.
2. 봇: 표지어 없는 `/work` → 팀장 시작 응답 → 백그라운드 실행 → 계획 게시와 task 생성. 오류·시간 초과·형식 오류는 task 없이 보고.
3. 테스트: 가짜 실행기로 정상·none·형식 오류·시간 초과·동시 실행 거부, 표지어 있는 `/work`는 그대로임을 고정. QA에서 실제 `claude`로 팀장을 1회 읽기 전용 실행해 형식을 확인한다(파일 변경 없음).
4. 문서: SOP §10·§10.1, Discord README.
5. 사전 점검 → self-review → candidate → Reviewer → QA → Evidence·Complete(Manager, G3와 같게) → checkpoint. push는 별도 승인.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-22 05:30 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다.

## 구현

- `orchestrator/worker/claude_lead.py`(새 파일): 팀장 프롬프트(등록된 작업 종류와 허용 경로·테스트를 나열, 아무것도 바꾸지 않음, `jarvis.bat`·`.env` 금지, worker_request는 Owner 참고용 제안), 읽기 전용 실행(`claude -p --permission-mode plan --allowedTools Read,Grep,Glob --disallowedTools Edit,Write,NotebookEdit,Bash,WebFetch,WebSearch`, 저장소 루트, 300초), 한 번에 하나(`lead_busy`), 출력 파서(필드 6개만, 종류는 등록된 이름 또는 none, none이면 이유 필수, 위험도 low·medium·high, 단계 1~7개, 한 줄·백틱 금지, 어긋나면 `lead_answer_malformed:*`), 시간 초과·비정상 종료·예외도 실패로 돌려준다. task 제목은 "종류 표지어: 팀장 제목"이고 그 제목이 다른 종류를 고르면 만들지 않는다.
- `orchestrator/worker/claude_worker.py`(Owner 결정 2의 최소 변경): `_report_progress`가 선택적 detail을 받아 `progress(stage, detail)`로 부를 수 있게 했고(`PROGRESS_DETAIL_STAGES`), 알림 두 곳을 더했다. Reviewer 판정 직후 `review`(PASS, 또는 판정과 이미 계산된 `reviewer_excerpt` 300자), 수정 candidate를 만든 직후 `repaired`(그 단계에서 이미 구한 변경 파일과 테스트 요약, 300자). 판정·repair·QA·반영 로직과 기존 단계 알림은 그대로이고, 알림 예외는 지금처럼 무시된다.
- `adapters/discord/bot_minimal.py`:
  - 표지어 없는 `/work`는 hold 대신 `lead_started`를 돌려주고, `on_message`가 이벤트 루프 밖에서 `_run_lead_job`을 돌린다.
  - `_run_lead_job`은 등록된 종류면 제목 "표지어: 팀장 제목", summary "Owner 요청: <Owner의 /work 원문>", `source_command` `/task`인 TODO task를 기존 writer로 만든다. none·실패·`lead_busy`·`lead_task_kind_conflict`·`lead_request_too_long`(원문이 summary에 그대로 들어가지 않음)이면 아무것도 만들지 않는다.
  - `/go`(accept 포함)는 팀장 task일 때 Worker와 Reviewer에게 summary의 Owner 원문만 넘기고, 종류는 제목에서 정해 `_run_worker_job(..., work_kind=)`로 넘긴다. Reviewer의 원문 승인 칸은 Owner가 입력한 `/work` 문장과 같다. 팀장의 계획·제안 지시는 Owner에게만 보인다.
  - 진행 줄: Reviewer 판정 PASS 줄, 지적이면 판정과 "지적 요지", 수정 뒤 "repair N회차 수정을 마침"과 변경 파일·테스트. 모델이 쓴 문장은 `@`를 무력화한다(`_discord_safe`).
  - 작업 스레드: `/work` 메시지에 스레드를 열어 팀장 계획을 올리고, `/go`는 스레드 안이면 그 스레드, 아니면 새 스레드에 진행과 결과를 올린다(`_task_thread`). 스레드를 못 열거나 스레드 전송이 실패하면 원래 채널로 보내고 예외를 내지 않는다(`_send_safely`). 팀장 계획에 수정 허용 경로와 스레드 안내를 보인다. `/help` 줄을 고쳤다.
- `orchestrator/worker/run_smoke_tests.py`: 표지어 없는 `/work`의 기대값을 `lead_started`(파일 생성 없음)로 바꿨다. `lead_flow`(팀장 답 파서와 실패 경우, task 생성 규칙, 종단 검사 두 개: Studyroom 팀장 task → `/go` → Worker → Reviewer → QA → DONE에서 Reviewer 원문 승인이 Owner 문장과 같고 팀장 문장이 넘어가지 않음, Radar 팀장 task가 Owner 문장에 표지어가 없어도 Radar로 DONE), `discussion_flow`(봇 경유로 지적 → 수정 → 재검토 → PASS 줄 순서와 내용, 프롬프트·멘션 미노출, 멘션 무력화, 모든 알림 실패에도 수정된 실행 DONE, 스레드 재사용·생성·실패 시 채널, 전송 실패 대체와 무예외). `progress_flow`는 detail 알림을 따로 기록해 정상 흐름(PASS)과 수정 흐름(지적 요지, 수정 결과, 재검토 PASS)을 고정하고, 실패하는 알림이 수정된 실행을 바꾸지 않는지 더했다. 성공 실행의 진행 줄 기대값에 PASS 줄을 넣었다.
- `adapters/discord/bot_minimal.py` self-check: 표지어 없는 `/work`의 기대값만 `lead_started`로 바꿨다.
- 문서: SOP §10.1 표의 지원 작업 행(`hold` → 팀장 단계)과 팀장 문단(진행 알림·스레드 문장 포함), Discord README `/work` 절.

## Implementer 검증 (작업 트리)

- 실제 `claude`로 팀장을 1회 실행했다(읽기 전용, 25초, 저장소 변경 없음): 요청 "Studyroom 용어집에 RAG 용어를 하나 추가해 줘"에 형식에 맞는 계획(studyroom_content, 단계 5개, risk low)을 냈다.
- Worker smoke total=528 failed=0(이전 494에 34개), Discord self-check ok 109, discord-nl-intent smoke 통과, Console smoke 통과, SOP validator PASS.
- 사전 점검(`check_task_record`, baseline `e069fa0`): status=PASS, staged_files 7, violations 0.

## Self-review

candidate 전 1회(읽기 전용 self-reviewer, Owner 결정 2 전). major 3·minor 5건이었고 모두 candidate 전에 처리했다: Reviewer 원문 승인 칸에 팀장 문장이 들어가던 구조를 Owner 원문만 넘기도록 바꿨고(종단 검사로 고정), SOP §10.1 표의 `hold` 문구를 고쳤고, 승인 조건에서 빠졌던 Reviewer 지적·수정 표시와 스레드는 Owner 결정 2를 받아 구현했고, none의 이유 필수·계획의 허용 경로 표시·문서의 실패 경우·기록 정리·사전 점검 기록을 반영했다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 제안]" / "첫 번째로 실행할 작업: "팀장(Lead) 단계 v0.1"" / "- 내용: Discord에 자연어로 지시하면(또는 마커 없는 /work) Claude 팀장이 읽기 전용으로 저장소를 조사해 계획을 만들고, 그 계획을 Discord에 올립니다." | 마커 없는 `/work`로 구현했다. 일반 자연어 메시지 연결은 하지 않았다(설계 1항, 자연어 처리 경로 계약 변경 필요, v0.2 후보). 팀장은 읽기 전용이고 계획을 작업 스레드에 올린다 |
| A2 | Owner 결정 (원문) | "  - 계획에 담는 것: 무엇을 할지, 어느 작업 종류와 경로인지, 위험도, 승인이 필요한지" / "  - 기존 작업 종류에 맞으면 그 종류로 배정하고, 맞지 않으면 이유와 함께 "새 작업 종류 필요"로 보고합니다." | 계획에 제목·단계·작업 종류·수정 허용 경로·위험도·Owner 결정 필요·제안 지시를 보인다. 맞으면 TODO task를 만들고, 맞지 않으면 팀장이 반드시 이유를 적어야 하며(없으면 형식 오류로 실패) task를 만들지 않는다 |
| A3 | Owner 결정 (원문) | "  - Owner가 /go 한 번만 누르면 기존 Worker → Reviewer → 수정 → QA → 반영이 이어집니다." | 종단 검사로 고정했다. 이때 Worker와 Reviewer는 Owner의 `/work` 원문만 받고, 판정·repair·QA·반영 로직은 바꾸지 않았다 |
| A4 | Owner 결정 (원문) | "  - 각 단계의 의견(팀장 계획, Reviewer 지적, Worker 수정)을 Discord 스레드에 그대로 보여 줍니다." | Owner 결정 2(B1~B4)로 구현했다: 작업 스레드에 팀장 계획, Reviewer 판정과 지적 요지, Worker 수정 결과, 재검토 판정, 최종 결과 |
| A5 | Owner 결정 (원문) | "- 필요한 승인: SOP §10.1(Worker 파이프라인의 실행 범위)을 넓히는 일이라, 시작하려면 이 task를 승인해 주셔야 합니다. 외부 연결과 비용은 없습니다." / "팀장 단계 v0.1 task를 등록하고 시작할까요? 승인하시면 이 세션에서 등록, 구현, 검토까지 진행하겠습니다." / "[Owner 답]" / "시작해" | SOP §10.1에 팀장 단계를 적었다. 작업 종류·허용 경로·보호 경로·테스트는 넓히지 않았다. 이미 쓰던 `claude` CLI만 쓰며 새 외부 연결·비용·의존성은 없다 |
| B1 | Owner 결정 2: 진행 표시와 스레드 (원문) | "[Manager 질문]" / "처음 제안에는 "각 단계의 의견(팀장 계획, Reviewer 지적, Worker 수정)을 Discord 스레드에 그대로 보여 줍니다"가 있었는데, 지금 구현은 팀장 계획만 보여 줍니다. Reviewer 지적과 수정 과정을 보이려면 승인 범위 밖(deny)인 Worker 실행 코드 claude_worker.py를 조금 고쳐야 합니다." / "1. (권장) claude_worker.py의 최소 변경을 이번 범위에 넣습니다." / "2. 이번에는 팀장 계획만 보이도록 범위를 줄이고, 지적·수정 표시와 스레드는 다음 task(v0.2)로 넘깁니다." / "[Owner 답]" / "1번으로 진행해 줘." | 선택지 1에 따라 `claude_worker.py`를 범위에 넣었다. 바꾼 것은 진행 알림 함수와 알림 두 곳뿐이다(구현 절) |
| B2 | Owner 결정 2: 진행 표시와 스레드 (원문) | "이번 task에 `claude_worker.py`의 최소 변경을 포함해서 Reviewer의 지적 요지, Worker의 수정 진행, 재검토 결과가 Discord에 표시되도록 해 줘. 작업별 Discord 스레드에 팀장 계획부터 최종 결과까지 모으는 것도 포함해 줘." / "다만 범위를 불필요하게 넓히지는 마." / "* 기존 Worker → Reviewer → 수정 → QA → DONE 파이프라인과 승인 정책은 최대한 그대로 유지할 것." | 지적 요지·수정 진행과 결과·재검토 판정 줄과 작업 스레드를 구현했다. 판정·repair 예산·QA·반영·승인 정책(`/go`, Owner 전용)은 바꾸지 않았다. 범위는 승인된 7개 파일이다 |
| B3 | Owner 결정 2: 진행 표시와 스레드 (원문) | "* Reviewer 지적과 수정 결과는 기존 실행 결과에서 확인 가능한 내용을 전달하고, 새로운 판단이나 결과를 만들어 내지 말 것." / "* Discord 알림 실패가 작업 자체의 성공·실패 판정을 부당하게 바꾸지 않도록 처리할 것." / "* 민감한 정보나 불필요한 전체 프롬프트를 Discord에 노출하지 말고, 지적 요지와 수정 결과만 표시할 것." | 지적 요지는 기존 `reviewer_excerpt`, 수정 결과는 그 단계의 변경 파일과 테스트 요약만 쓴다. 알림·스레드 실패는 무시되거나 채널로 대체되며 판정을 바꾸지 않는다(모든 알림 실패 검사). 프롬프트 전문은 보내지 않고 멘션은 무력화한다 |
| B4 | Owner 결정 2: 진행 표시와 스레드 (원문) | "* 기존 테스트와 종단 테스트를 갱신해 정상 흐름, Reviewer 지적 후 수정, 재검토, 알림 실패를 검증할 것." / "* 변경 파일과 승인 범위를 확인하고, 추가 범위가 필요하면 먼저 보고할 것." / "구현 후 candidate를 만들고 Reviewer → QA → 완료 절차를 진행해 줘. 중간에 유효한 지적이 나오면 무조건 중단하기보다 현재 승인된 수정 범위와 남은 repair 예산 안에서 해결을 시도해 줘. Owner 결정이 반드시 필요한 경우에만 멈추고 이유를 설명해 줘." | `progress_flow`·`discussion_flow`·`lead_flow`로 정상 흐름, 지적 뒤 수정, 재검토, 알림 실패, 스레드를 검증한다. 추가 범위는 필요하지 않았다. 이후 절차는 candidate → Reviewer → QA → 완료로 진행한다 |
