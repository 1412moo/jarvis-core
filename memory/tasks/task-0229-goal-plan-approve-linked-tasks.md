# task-0229-goal-plan-approve-linked-tasks

- id: `task-0229-goal-plan-approve-linked-tasks`
- title: `/goal 계획 승인: auto 하위 작업을 연결된 TODO task로 만들고 팀장 지시를 Worker와 Reviewer에 전달`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-11-12 08:47 UTC`
- updated_at: `2026-11-12 08:48 UTC`
- summary: `Owner 전용 /goal <goal-id> approve가 저장소 밖 계획 파일을 hash로 다시 확인하고, 등록된 작업 종류이면서 Policy Gate가 auto로 판정한 하위 작업만 TODO task로 만든다. task에는 goal_id, goal_task, goal_plan_sha256, goal_depends_on을 두고, 목표 task의 Worker와 Reviewer는 Owner의 /goal 원문과 팀장의 하위 작업 지시와 완료 조건을 받는다. 선행 task가 DONE이 아니면 /go를 거절한다. 실행은 계속 /go, main 반영은 accept뿐이며 자동 실행, 병렬, 목표 브랜치, 작업 종류 추가는 범위 밖이다.`
- source_command: `Owner 지시: A안 진행 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `da6761cd7493b621fea8873786a6e157157c96a4` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=1` (SOP §5 기본값, repair 1은 아래 절) |
| 작업 위치 | 저장소 밖 worktree `jarvis-core-worktrees/task-0229-goal-approve`, 브랜치 `work/task-0229-goal-approve`. main 체크아웃은 그대로 둔다 |

## Owner 결정 (원문, 작업 지시)

```text
[Manager 질문]
다음 작업으로 어느 안을 진행할까요?

[Owner 답]
A안 진행
```

질문 앞의 Manager 조사 보고(Manager 문장, 승인 원문 아님)는 Owner의 읽기 전용 조사 지시에 대한 답이다. 후보 A(계획 승인 → 연결된 task + 지시 묶음), B(Console 작업 종류 등록), C(Console 목표 읽기 화면)를 비교하고 A를 추천했다. 보고가 적은 A안의 범위:

- 포함 1: `/goal <goal-id> approve`가 계획 파일을 읽어 hash를 확인하고, 등록된 종류이면서 `auto` 판정인 하위 작업만 TODO task로 만든다.
- 포함 2: task 메타데이터에 `goal_id`, `goal_task`(T번호), 계획 hash, 선행 task를 추가한다.
- 포함 3: 지시 묶음. Worker는 Owner 목표 원문과 팀장 지시·완료 조건을 받고, Reviewer는 Owner 원문과 승인된 계획을 기준으로 대조한다.
- 포함 4: 선행 task가 DONE이 아니면 `/go`를 거절한다.
- 제외: 자동 실행, 병렬, 목표 브랜치, `needs_owner`·`forbidden` 하위 작업의 task화, 작업 종류 추가, Console 변경, 재계획.
- 완료 기준: Studyroom·Radar 복합 목표 1건을 `approve`해 task가 생기고 `/go`로 순서대로 실행돼 Reviewer·QA·`accept`를 통과한다. 선행 미완료 `/go`, hash 불일치, 두 번째 `approve`, `needs_owner` 작업의 task화가 모두 거절되는 smoke가 있다. 기존 `/work`·`/go` smoke와 SOP validator가 그대로 통과한다.

## Owner 결정 (원문, 구현 전 질문 세 가지)

```text
[Manager 질문]
A안은 /goal <goal-id> approve가 저장소 밖 계획 파일을 다시 읽어 TODO task를 만듭니다. 지금 SOP §10.1은 '계획 파일을 다시 읽는 기능도 없다'고 적고 있어 이 문장을 고쳐야 합니다. 허용할까요?

[Owner 답]
허용 (Recommended)

[Manager 질문]
A안은 팀장의 Worker 지시와 완료 조건을 Worker와 Reviewer에게 전달합니다(지금은 Owner 원문만 전달). 승인 근거는 계속 Owner의 /goal 원문과 approve 메시지로 두고, Reviewer는 팀장 지시가 그 범위 밖이면 finding으로 냅니다. SOP §10과 .claude/agents/reviewer.md의 이 계약 변경을 허용할까요?

[Owner 답]
허용 (Recommended)

[Manager 질문]
approve가 task로 만들 하위 작업의 기준을 무엇으로 할까요? Policy Gate v0는 지금 '제안'이며 실행 권한이 아닙니다. 어느 쪽이든 실행은 Owner의 /go, main 반영은 accept로만 합니다.

[Owner 답]
auto 판정만 (Recommended)
```

각 답의 선택지 설명(Manager 문장, 승인 원문 아님): 첫째 "approve 때 한 번만 읽고 hash가 일치할 때만 task를 만듭니다. 자동 실행·큐·백그라운드는 계속 금지이며 SOP §10.1 문단을 그에 맞게 갱신합니다." 둘째 "목표에서 만든 task에만 적용합니다. 기존 /work·/go task는 지금처럼 Owner 원문만 받습니다." 셋째 "등록된 작업 종류이고 Policy Gate가 auto로 판정한 하위 작업만 task로 만듭니다. needs_owner와 forbidden은 건너뛰고 목록으로 보입니다. Gate v0를 'task를 만들 자격'으로만 승인하는 것입니다."

## Owner 결정 (원문, 제안서 안의 충돌)

```text
[Manager 질문]
구현 전 조사에서 제안서 안의 충돌을 찾았습니다. A안은 'task 메타데이터에 goal_id 등 4개 필드 추가'와 'Console 변경 제외'를 함께 적었는데, Console이 허용 필드 목록을 따로 갖고 있어(run_web_app.py의 TASK_VIEW_ALLOWED_FIELDS, smoke가 일치를 검사) 필드를 더하면 Console도 고쳐야 합니다. 어떻게 할까요?

[Owner 답]
필드 추가 + Console 허용 목록만 (Recommended)
```

선택지 설명(Manager 문장, 승인 원문 아님): "goal_id, goal_task, goal_plan_sha256, goal_depends_on을 정식 필드로 더하고, Console은 이 필드가 있는 task를 읽을 수 있게 허용 목록과 그 smoke만 고칩니다. 화면·API·동작은 바꾸지 않습니다."

## 조사 (baseline 기준)

- `/goal`의 계획 파일은 쓰기만 했다. `GOAL_PLAN_DIR`을 읽는 코드는 없었고(`bot_minimal._write_goal_plan_file`만 사용), SOP §10.1은 "계획 파일을 다시 읽는 기능도 없다"고 적었다.
- Worker와 Reviewer는 Owner의 `/work` 원문만 받았다(`bot_minimal._worker_request_for`, `claude_worker.worker_prompt`, `reviewer_call`).
- task 메타데이터 허용 목록은 `task_file_writer.TASK_ALLOWED_METADATA` 한 곳이고, Console은 같은 내용의 `TASK_VIEW_ALLOWED_FIELDS`를 따로 두며 Console smoke가 둘이 같은지 검사한다.
- `/go`는 작업 종류와 읽기 전용 여부를 task 제목에서 정한다(`_go_work_kind`, `claude_worker.is_read_only_request`).
- 저장소 밖에 남은 실제 계획 파일 6건을 새 읽기 함수로 읽어 보니 모두 파일의 hash와 같은 계획으로 되돌아왔다. Studyroom·Radar 목표 2건에서 auto 하위 작업 4개씩이 task 제목을 얻었고, Console 목표 4건은 모든 하위 작업이 종류 없음이라 만들 task가 없다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `adapters/discord/bot_minimal.py`, `adapters/discord/README.md`, `orchestrator/discord-intake/task_file_writer.py`, `orchestrator/worker/claude_worker.py`, `orchestrator/worker/goal_plan.py`, `orchestrator/worker/run_smoke_tests.py`, `apps/jarvis-console/run_web_app.py`, `apps/jarvis-console/run_smoke_tests.py`, `docs/jarvis-multi-agent-sop-v0.1.md`, `docs/task-model.md`, `.claude/agents/reviewer.md`, 이 task 기록 |
| deny | `orchestrator/worker/policy_gate.py`, `orchestrator/worker/claude_lead.py`, Console의 화면·API·동작, `docs/lead-goal-plan-design.md`(History), `docs/master-plan.md`와 `docs/master-plan-history.md`(DONE 전), `.codex/agents/*.toml`, 작업 종류 추가, 자동 실행·병렬·목표 브랜치·재계획, 다른 task 기록, validator, `jarvis.bat`, `.env`, push, 봇 재시작 |

## Start

Console(worktree에서 띄움) Voice Inbox의 Create Local Task Preview를 확인하고 Confirm해 TODO 기록을 만들었다. Project Control의 Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다. Console은 수정 전에 껐고(시작한 PID를 종료, 8790 포트 listener 없음 확인) 그 뒤 title·summary·source_command를 이 task 내용으로 고쳤다.

## 구현

- `orchestrator/discord-intake/task_file_writer.py`: 선택 필드 `goal_id`, `goal_task`, `goal_plan_sha256`, `goal_depends_on`을 허용 목록에 더했다. `goal_fields_error`가 앞의 세 필드는 함께 있거나 모두 없고, `goal_depends_on`은 그 셋과 함께만 있으며, 값마다 정해진 형식(goal id, `T1`~`T99`, 소문자 64자리 hex, 쉼표로 이은 task id, 되풀이 없음)인지 본다. `write_task_file`은 draft에 이 필드가 있으면 검사한 뒤 `source_command` 다음에 쓰고, 기록을 읽을 때도 같은 검사를 한다. draft의 `goal_body`(목표 지시 묶음 절)는 링크 필드와 함께일 때만, `## ` 제목으로 시작하고 줄바꿈 말고는 제어 문자가 없고 20,000자 이하일 때만 머리말 아래에 쓴다(`goal_body_error`).
- `apps/jarvis-console/run_web_app.py`: 허용 목록 `TASK_VIEW_ALLOWED_FIELDS`에 `task_file_writer.TASK_GOAL_FIELDS`를 더하고, 파서가 작성기의 `goal_fields_error`로 같은 규칙을 본다(어긋나면 `invalid_text`, `goal_id`로 metadata review). Console은 이 필드가 있는 기록을 읽을 수 있게만 되고 화면·API·쓰기는 그대로다. `apps/jarvis-console/run_smoke_tests.py`에 네 이름이 허용 목록에 있고, 온전한 링크는 읽히며 일부만 있는 링크는 metadata review로 간다는 확인을 더했다.
- Console 파서의 형식 검사는 Owner 답 "허용 목록만"보다 넓어 self-review 지적 1로 Owner에게 물었고 유지 답을 받았다(아래 Owner 결정 절). 허용만 하면 작성기가 거절하는 기록을 Console이 정상으로 보이게 되어 `hold_from`·`closed_reason`과 달리 두 파서의 규칙이 갈린다. 처음에는 네 이름을 `TASK_VIEW_OPTIONAL_TEXT_FIELDS`에 넣었는데 Console smoke의 실행 필드 집합 검사(`TASK_VIEW_EXECUTION_FIELDS`)가 실패해 별도 집합으로 옮겼다.
- `orchestrator/worker/goal_plan.py`: `plan_from_record`가 계획 파일에 저장된 계획을 팀장 답 모양으로 되돌려 `parse_goal_answer`로 다시 전부 검사한다.
- `orchestrator/worker/claude_worker.py`: `GoalBrief`(goal id, 하위 작업 id, 계획 hash, 승인 명령, 팀장 제목·목적·지시·완료 조건·경로)와 실행 중인 brief를 담는 context 변수를 더했다. `run_pipeline`, `revise_candidate`, `recheck_candidate`, `run_report`가 `goal_brief`를 받아 설정한다. brief가 있으면 `worker_prompt`와 `report_prompt`는 "Owner goal (verbatim)"과 이 하위 작업만 하라는 안내, 팀장의 말로 표시한 지시·목적·경로·완료 조건을 넣고, `reviewer_call`은 Manager 요약에 Owner 목표와 하위 작업·팀장 항목을 넣으며 승인 원문을 `/goal <목표>`, `/goal <goal-id> approve`, `/go` 명령으로 만든다. brief가 없으면 세 프롬프트는 이전과 같다.
- `adapters/discord/bot_minimal.py`: `/goal <goal-id> approve`(`_run_goal_approve`). goal id로 시작하는 `/goal`은 목표로 계획하지 않고 `approve`만 받는다. `_load_goal_plan`이 계획 파일을 읽어 goal id, 실패 기록 여부, 목표 원문, 계획 전체, hash를 검사하고, 현재 코드의 Policy Gate로 다시 판정해 auto이고 등록된 종류인 하위 작업마다 `write_task_file`로 TODO task를 만든다. 제목이 다른 종류나 다른 방식을 고르게 되는 하위 작업과, 만들어지지 않은 하위 작업에 의존하는 하위 작업은 만들지 않는다. 같은 goal id의 task가 있으면 `goal_already_approved`다. 승인은 task마다 머리말 아래에 "목표 지시 묶음" 절(Owner의 `/goal` 원문, 팀장 제목·목적·지시·완료 조건·경로, 계획 hash, 승인 명령, 이 내용의 `brief_sha256`을 담은 JSON 블록)을 함께 쓰고, 첫 task를 쓰기 전에 모든 draft를 `preview_task_file_write`로 검사한다. `_run_go`는 목표 task면 그 기록의 지시 묶음 절만 읽어(`_goal_brief_for`, `_parse_goal_brief`) brief를 만들고 요청 원문을 Owner의 `/goal` 원문으로 하며, 절이 없거나 형식이 어긋나거나 `brief_sha256`·머리말 필드와 맞지 않거나 선행 task가 DONE이 아니면 잠금과 전이 전에 거절한다(`accept`, `reject`, `recover`는 제외). 계획 파일은 승인 때만 읽는다(self-review 지적 2에 대한 Owner 답). `_run_worker_job`은 받은 brief를 파이프라인에 넘긴다. `/help`와 계획 개요에 승인 명령을 더하고, 개요의 "이 계획을 실행하는 기능은 아직 없고" 문구를 뺐다.
- 문서: SOP §10.1 진입 명령 행과 목표 계획 문단(계획 파일을 다시 읽는 곳), 새 목표 계획 승인 문단, §10.2 2항. `.claude/agents/reviewer.md`의 Goal plan sub-task 절. `docs/task-model.md` 14절. Discord README의 `/goal <goal-id> approve` 절.
- `orchestrator/worker/run_smoke_tests.py`: `goal_approve_flow`. 필드 형식, 계획 파일 되읽기, 승인 거절(없는 id, 실패 기록, 바뀐 계획, 다른 goal id, 읽을 수 없는 파일, 저장소 안 폴더, 사용법, Owner 아님), 만든 task와 건너뛴 하위 작업, 두 번째 승인 거절, 만들 것이 없는 계획(종류 없음, task 기록으로 쓸 수 없는 제목, 만들어지지 않은 선행 작업), task 기록의 지시 묶음 내용, 계획 파일 없이 실행되는지, 고치거나 지우거나 되풀이하거나 다른 task 것으로 바꾼 지시 묶음과 선행 미완료의 `/go` 거절, Worker·Reviewer 프롬프트 내용, accept 뒤 선행 조건 해소, 읽기 전용 하위 작업 실행, 링크 없는 task와 brief 없는 프롬프트가 이전과 같은지, 승인 함수가 Worker·팀장·git·잠금을 부르지 않는지 확인한다.
- Manager 해석: 승인 명령에 hash를 따로 입력받지 않았다. goal id가 계획 파일 하나를 가리키고, 승인 때 계획이 파일의 hash와 같은지 본다. 실행 때는 task 기록의 지시 묶음이 자신의 `brief_sha256`과 머리말의 goal id·하위 작업·계획 hash에 맞는지 본다. `brief_sha256`은 실수로 바뀐 기록을 거르는 장치이고 저장소에 쓸 수 있는 사람의 의도적 수정을 막지는 못한다(SOP 문단과 `docs/task-model.md` 14절에 적음).
- Manager 해석: 지시 묶음 절은 task 기록 본문에 있지만 실행 입력이다. AGENTS.md 기준 지도는 task 기록 본문을 History로 분류하는데, 이 절은 규칙의 근거가 아니라 승인 때 봇이 쓴 데이터이고 Owner가 고른 선택지 설명이 "task 기록 본문이 실행 입력이 됩니다"였다. `docs/task-model.md` 14절에 이 예외를 적었고 AGENTS.md는 범위 밖이라 고치지 않았다. AGENTS.md History 목록에 한 줄을 더할지는 Owner 보고에 결정 사항으로 올린다.
- Manager 해석: 읽기 전용이면서 등록된 종류이고 auto인 하위 작업도 task로 만든다(Owner 답 "auto 판정만"의 기준에 방식 제한이 없음). 기존 읽기 전용 확인·보고로 실행된다.
- Manager 해석: 승인은 task 상태 전이가 아니라 TODO 생성이므로 `/work`와 같이 승인 감사 기록을 쓰지 않는다. `/go`와 accept의 감사는 그대로다.
- Manager 해석: `.codex/agents/reviewer.toml`은 Owner 답이 `.claude/agents/reviewer.md`만 적어 고치지 않았다. SOP validator는 그대로 PASS다.

## Implementer 검증 (작업 트리, candidate 전)

- self-review 전 작업 트리: Worker smoke total=807 failed=0, Discord `--self-check-suite` rc=0, SOP validator PASS, Console `--self-test` rc=0, Console smoke rc=0(PYTHONUTF8=1과 없음 둘 다), `node --check apps/jarvis-console/web/app.js` 통과, discord-intake smoke rc=0, Studyroom smoke rc=0, `check_no_secrets.py` PASS, `git diff --check` 통과.
- 고친 실패: 첫 Worker smoke 실행에서 4건이 실패했다. (1)(2) 계획 개요의 마지막 줄을 바꿔 기존 검사 두 건(마지막 문구, 최대 길이에서 2000자 안)이 실패해, 승인 안내를 별도 줄로 옮기고 마지막 줄 "auto 판정도 실행 권한이 아닙니다."를 되살렸다. (3) 새 검사가 accept 응답에 brief가 있다고 잘못 기대했다(accept는 brief를 받지 않음). (4) 새 검사가 `/go`만 하고 실행하지 않은 DOING task를 남겨 뒤의 시작 점검 검사가 실패해, 그 task를 시작하지 않고 링크 없음만 확인하게 고쳤다.
- 첫 Console smoke 실행에서 1건이 실패했다(`TASK_VIEW_EXECUTION_FIELDS` 집합 검사). 구현 절의 Console 항목대로 네 이름을 별도 집합으로 옮겼다.
- 실제 계획 파일 6건(저장소 밖, 읽기만): `_load_goal_plan`이 모두 파일의 hash와 같은 계획으로 읽었다. 승인은 실행하지 않았다(main의 task 기록을 만들게 되므로).
- 하지 않은 것: 실제 `claude` CLI로 목표 task를 실행해 보는 것과 실제 봇에서의 `/goal <goal-id> approve`(봇 재시작은 승인 밖). Worker·Reviewer 프롬프트는 가짜 claude가 받은 내용으로 확인했다.
- self-review 수정 뒤의 결과는 아래 Self-review 절에 적는다.

## Self-review

SOP §3대로 staged 변경에 `claude -p --agent self-reviewer --tools Read,Grep,Glob`을 한 번 돌렸다(Reviewer 판정 아님, 사용량 추정 $0.68). 지적 다섯 건과 처리:

1. major: 요약 A18이 Console 변경을 "`TASK_VIEW_OPTIONAL_TEXT_FIELDS`와 smoke 확인 한 건"이라고 적었는데 실제 코드는 별도 집합과 파서의 형식 검사였고, 형식 검사는 Owner 답 "허용 목록만"보다 넓다. candidate 전에 Owner에게 물어 유지 답을 받았고(아래 Owner 결정 절) 요약 행을 실제 코드에 맞게 고쳤다.
2. major: Owner가 고른 선택지 설명은 "approve 때 한 번만 읽고"였는데 구현은 목표 task의 `/go`마다 계획 파일을 다시 읽었다. Owner에게 물었고 답은 "approve 때만 읽기"였다(아래 Owner 결정 절). 승인이 지시 묶음을 task 기록에 옮겨 쓰고 `/go`는 그 기록만 읽게 다시 구현했다(구현 절의 봇·작성기 항목, SOP 문단, README, `docs/task-model.md` 14절, smoke).
3. minor: 요약 A14가 auto인데도 만들지 않는 하위 작업 가운데 제목 충돌만 적었다. 만들어지지 않은 하위 작업에 의존하는 것과 task 기록으로 쓸 수 없는 제목·요약도 요약 행에 적었다.
4. minor: 요약 A3a가 완료 기준의 충족 방법과 확인하지 못한 부분을 적지 않았다. 가짜 claude smoke로 확인한 것과 실제 봇·실제 CLI로 확인하지 못한 것을 그 행에 적었다.
5. minor: task를 쓰다가 실패하면 이미 쓴 task가 남고 다시 승인할 수 없다는 동작이 SOP와 README에 없었다. 두 문서에 한 문장씩 더했다.

수정 뒤 다시 돌린 결과: Worker smoke total=812 failed=0(baseline 767에 새 검사 45건, 기존 검사는 그대로 통과), Console `--self-test` rc=0, Console smoke rc=0(PYTHONUTF8=1과 없음 둘 다), `node --check apps/jarvis-console/web/app.js` 통과, discord-intake smoke rc=0, Discord `--self-check-suite` rc=0, Studyroom smoke rc=0, `check_no_secrets.py` PASS, SOP validator PASS, `git diff --check` 통과. 사전 점검은 candidate 직전에 다시 돌린다.

## Owner 결정 (원문, self-review 지적 질문)

```text
[Manager 질문]
task-0229 self-review 지적(major): 승인하신 선택지 설명은 'approve 때 한 번만 읽고'였는데, 구현은 목표 task의 /go(resume·revise·recheck 포함) 때마다 계획 파일을 다시 읽습니다. 팀장 지시와 완료 조건을 Worker·Reviewer에게 전달하려면 그 내용이 필요하고, task 기록에는 hash만 두었기 때문입니다(파일이 없거나 hash가 다르면 실행 거절). 어떻게 할까요?

[Owner 답]
approve 때만 읽기

[Manager 질문]
task-0229 self-review 지적(major): Owner 답은 '필드 추가 + Console 허용 목록만'이었는데, Console 파서에 형식 검사 한 줄(작성기의 goal_fields_error 호출)도 넣었습니다. 허용만 하면 작성기가 거절하는 기록(링크 일부만 있는 기록)을 Console이 정상으로 보이게 됩니다. 어떻게 할까요?

[Owner 답]
형식 검사 유지 (Recommended)
```

선택지 설명(Manager 문장, 승인 원문 아님): 첫째 답 "승인 때 팀장 지시·완료 조건을 task 기록 본문에 옮겨 적고 /go는 그 기록만 읽게 다시 구현합니다. 작업이 늘고 task 기록 본문이 실행 입력이 됩니다." 둘째 답 "Console과 작성기가 같은 규칙으로 기록을 봅니다(hold_from, closed_reason과 같은 방식). 화면·API·쓰기는 그대로입니다."

## Reviewer 결과 (candidate `bfb5aa31bfe2b1220e7e283bc607e81adaf54a91`)

verdict FINDINGS, `self_deviations` 없음, 사용량 추정 $0.96. 이 절은 candidate 뒤에 쓴 기록이며 repair 1 candidate에 함께 커밋한다. minor 1건:

1. 커밋 메시지 본문의 "/go refuses it while a prerequisite task is not DONE, or when the plan file is gone or no longer matches the recorded hash."가 실제 동작과 다르다. `/go`는 task 기록만 읽고 계획 파일을 읽지 않는다(`_goal_brief_for`, SOP §10.1, smoke). 메시지를 self-review 전에 써 두고 재구현 뒤 고치지 않았다.

Reviewer unverified: 기록의 검사 실행 결과, 완료 기준(가짜 claude smoke로만 확인, 실제 CLI와 실제 봇은 승인 밖), Console의 화면·API·쓰기 동작이 그대로라는 것(diff로만 판단). 모두 QA에서 확인한다.

## Repair 1 (`repair_count=1`)

- 고친 것: 커밋 메시지의 그 문장을 "지시 묶음 절이 없거나 형식이 어긋나거나 `brief_sha256`·링크 필드와 맞지 않으면 거절하고 계획 파일은 읽지 않는다"는 내용으로 바꿨다. 소스 파일은 바꾸지 않았고 이 기록에 Reviewer 결과와 이 절만 더했다.
- 방법: 커밋 메시지는 새 commit으로 고칠 수 없으므로 작업 브랜치에서 `git reset --soft <baseline>`으로 첫 candidate를 풀어 같은 변경을 stage한 상태로 되돌리고, 고친 메시지로 `scripts/commit_candidate.py`를 다시 실행했다. 작업 브랜치는 push하지 않았고 main에 없으므로 다른 기록은 바뀌지 않는다. 첫 candidate `bfb5aa3`는 어느 브랜치에도 없고 reflog에만 남는다.
- candidate가 바뀌었으므로 위 Reviewer 결과는 무효이고 새 candidate에 Reviewer와 QA를 다시 실행한다.
- 소스가 바뀌지 않아 smoke는 다시 돌리지 않았다(QA가 새 candidate에서 전부 돌린다). 사전 점검은 commit 직전에 다시 돌린다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문, 작업 지시) | "[Manager 질문]" | bounded question의 표지 |
| A2 | Owner 결정 (원문, 작업 지시) | "다음 작업으로 어느 안을 진행할까요?" | A3a 답의 질문. 선택지 A·B·C는 질문 앞 Manager 조사 보고의 후보다 |
| A3 | Owner 결정 (원문, 작업 지시) | "[Owner 답]" | 답의 표지 |
| A3a | Owner 결정 (원문, 작업 지시) | "A안 진행" | 이 task의 승인. 범위는 질문 앞 Manager 조사 보고의 A안(위 작업 지시 절의 포함 1~4, 제외, 완료 기준)이다. 자동 실행, 병렬, 목표 브랜치, 작업 종류 추가, 재계획은 하지 않았다. 제외 항목 "Console 변경"은 A18·A24의 Owner 답으로 허용 목록과 형식 검사까지 바뀌었다. 완료 기준의 충족: 복합 목표를 approve해 task가 생기고 `/go`로 실행돼 Reviewer·QA·accept를 통과하는 흐름, 선행 미완료 `/go`, 바뀐 계획(hash 불일치), 두 번째 approve, needs_owner 하위 작업을 task로 만들지 않는 것은 가짜 claude를 쓰는 Worker smoke(`goal_approve_flow`)로 확인했고, 기존 `/work`·`/go` smoke와 SOP validator는 그대로 통과한다. 확인하지 못한 것: 실제 `claude` CLI와 실제 봇에서의 같은 흐름(봇 재시작은 승인 밖) |
| A4 | Owner 결정 (원문, 구현 전 질문 세 가지) | "A안은 /goal <goal-id> approve가 저장소 밖 계획 파일을 다시 읽어 TODO task를 만듭니다." | `_run_goal_approve`와 `_load_goal_plan`. 계획 파일은 승인 때 한 번만 읽는다(A21) |
| A5 | Owner 결정 (원문, 구현 전 질문 세 가지) | "지금 SOP §10.1은 '계획 파일을 다시 읽는 기능도 없다'고 적고 있어 이 문장을 고쳐야 합니다." | SOP §10.1 목표 계획 문단의 그 문장을 "계획 파일을 다시 읽는 것은 아래 목표 계획 승인 한 번뿐이다"로 고치고 목표 계획 승인 문단을 더했다 |
| A6 | Owner 결정 (원문, 구현 전 질문 세 가지) | "허용할까요?" | 답은 A7 |
| A7 | Owner 결정 (원문, 구현 전 질문 세 가지) | "허용 (Recommended)" | 계획 파일 읽기와 SOP §10.1 문장 수정을 허용. 처음 구현은 `/go`도 같은 파일을 다시 읽었는데 self-review 지적 뒤 Owner 답 A21에 따라 승인 때만 읽게 고쳤다. 이 답은 이 task에만 효력이 있고 계속 적용되는 규칙은 SOP §10.1 문단으로 옮겼다 |
| A8 | Owner 결정 (원문, 구현 전 질문 세 가지) | "A안은 팀장의 Worker 지시와 완료 조건을 Worker와 Reviewer에게 전달합니다(지금은 Owner 원문만 전달)." | `claude_worker.GoalBrief`와 `worker_prompt`, `report_prompt`, `reviewer_call`. 목표에서 만든 task에만 적용하고 그 밖의 task는 이전과 같다 |
| A9 | Owner 결정 (원문, 구현 전 질문 세 가지) | "승인 근거는 계속 Owner의 /goal 원문과 approve 메시지로 두고, Reviewer는 팀장 지시가 그 범위 밖이면 finding으로 냅니다." | Reviewer 호출의 승인 원문은 `/goal <목표>`, `/goal <goal-id> approve`, `/go` 세 줄이고 팀장의 말은 Manager 요약에 팀장의 말로 표시한다. 범위 밖 지시를 finding으로 내는 규칙은 `.claude/agents/reviewer.md`의 Goal plan sub-task 절 |
| A10 | Owner 결정 (원문, 구현 전 질문 세 가지) | "SOP §10과 .claude/agents/reviewer.md의 이 계약 변경을 허용할까요?" | 답은 A7과 같은 문장(이 블록의 둘째 답). SOP §10.1·§10.2 2항과 `.claude/agents/reviewer.md`를 고쳤다. `.codex/agents/reviewer.toml`은 질문에 없어 고치지 않았다 |
| A11 | Owner 결정 (원문, 구현 전 질문 세 가지) | "approve가 task로 만들 하위 작업의 기준을 무엇으로 할까요?" | 답은 A14 |
| A12 | Owner 결정 (원문, 구현 전 질문 세 가지) | "Policy Gate v0는 지금 '제안'이며 실행 권한이 아닙니다." | 승인 뒤에도 auto는 실행 권한이 아니다. SOP 문단에 "task를 만들 자격"이라고 적었다 |
| A13 | Owner 결정 (원문, 구현 전 질문 세 가지) | "어느 쪽이든 실행은 Owner의 /go, main 반영은 accept로만 합니다." | 승인은 아무것도 실행하지 않고, 실행은 `/go`, 반영은 accept다. smoke가 승인 뒤 HEAD·worktree·잠금 불변과 승인 함수가 Worker·팀장·git·잠금을 부르지 않음을 확인한다 |
| A14 | Owner 결정 (원문, 구현 전 질문 세 가지) | "auto 판정만 (Recommended)" | auto이고 등록된 작업 종류인 하위 작업만 task로 만든다. needs_owner·forbidden은 만들지 않고 사유와 함께 보인다. Manager 해석: auto인데도 만들지 않는 경우가 세 가지 있다. 제목이 다른 종류·방식을 고르게 되는 하위 작업(`title_kind_conflict`, `title_mode_conflict`. 만들면 `/go`가 계획과 다른 종류나 방식으로 실행함), 만들어지지 않은 하위 작업에 의존하는 하위 작업(`depends_on_skipped`. 선행 조건을 채울 task가 없음), 제목이나 요약을 task 기록으로 쓸 수 없는 하위 작업(`task_draft_invalid`. 쓰다가 실패해 일부만 만들어지는 것을 막음) |
| A15 | Owner 결정 (원문, 제안서 안의 충돌) | "구현 전 조사에서 제안서 안의 충돌을 찾았습니다." | Manager가 구현 전에 찾은 충돌의 보고(SOP §3의 bounded question) |
| A16 | Owner 결정 (원문, 제안서 안의 충돌) | "A안은 'task 메타데이터에 goal_id 등 4개 필드 추가'와 'Console 변경 제외'를 함께 적었는데, Console이 허용 필드 목록을 따로 갖고 있어(run_web_app.py의 TASK_VIEW_ALLOWED_FIELDS, smoke가 일치를 검사) 필드를 더하면 Console도 고쳐야 합니다." | 충돌 내용. `TASK_VIEW_ALLOWED_FIELDS`와 Console smoke의 일치 검사는 조사 절에 적었다 |
| A17 | Owner 결정 (원문, 제안서 안의 충돌) | "어떻게 할까요?" | 답은 A18(이 블록)과 A21·A24(self-review 지적 질문 블록) |
| A18 | Owner 결정 (원문, 제안서 안의 충돌) | "필드 추가 + Console 허용 목록만 (Recommended)" | 네 필드를 `task_file_writer`에 더했다. Console은 허용 목록 `TASK_VIEW_ALLOWED_FIELDS`에 `TASK_GOAL_FIELDS`를 별도 집합으로 더하고, 파서에 작성기의 `goal_fields_error` 형식 검사를 넣었으며(이 검사는 "허용 목록만"보다 넓어 Owner에게 다시 물었다, A22~A24), Console smoke에 허용 목록·온전한 링크·일부만 있는 링크 확인을 더했다. Console의 화면·API·쓰기 동작은 바꾸지 않았다 |
| A19 | Owner 결정 (원문, self-review 지적 질문) | "task-0229 self-review 지적(major): 승인하신 선택지 설명은 'approve 때 한 번만 읽고'였는데, 구현은 목표 task의 /go(resume·revise·recheck 포함) 때마다 계획 파일을 다시 읽습니다." | self-review 지적 2의 질문. 처음 구현의 동작을 그대로 적었다 |
| A20 | Owner 결정 (원문, self-review 지적 질문) | "팀장 지시와 완료 조건을 Worker·Reviewer에게 전달하려면 그 내용이 필요하고, task 기록에는 hash만 두었기 때문입니다(파일이 없거나 hash가 다르면 실행 거절)." | 처음 구현이 `/go`에서 계획 파일을 읽은 이유 |
| A21 | Owner 결정 (원문, self-review 지적 질문) | "approve 때만 읽기" | 계획 파일은 승인 때만 읽는다. 승인이 Owner 목표 원문과 팀장 지시·완료 조건을 task 기록의 "목표 지시 묶음" 절에 옮겨 쓰고 `/go`는 그 기록만 읽는다. smoke가 계획 파일을 지운 채 실행·accept·읽기 전용 실행이 되는 것과, 고친·지운·되풀이한·바꿔 넣은 지시 묶음의 `/go` 거절을 확인한다. 이 답은 이 task에만 효력이 있고 규칙은 SOP §10.1과 `docs/task-model.md` 14절로 옮겼다 |
| A22 | Owner 결정 (원문, self-review 지적 질문) | "task-0229 self-review 지적(major): Owner 답은 '필드 추가 + Console 허용 목록만'이었는데, Console 파서에 형식 검사 한 줄(작성기의 goal_fields_error 호출)도 넣었습니다." | self-review 지적 1의 질문 |
| A23 | Owner 결정 (원문, self-review 지적 질문) | "허용만 하면 작성기가 거절하는 기록(링크 일부만 있는 기록)을 Console이 정상으로 보이게 됩니다." | 형식 검사를 넣은 이유 |
| A24 | Owner 결정 (원문, self-review 지적 질문) | "형식 검사 유지 (Recommended)" | Console 파서의 `goal_fields_error` 검사를 유지한다. 이 답은 이 task에만 효력이 있다 |
