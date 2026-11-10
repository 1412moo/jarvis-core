# task-0226-goal-task-owner-needs

- id: `task-0226-goal-task-owner-needs`
- title: `/goal: 작업 종류 없는 하위 작업의 사유 누락을 거절 대신 needs_owner로, 실패 이유 설명과 실패 기록`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-11-10 11:34 UTC`
- updated_at: `2026-11-10 14:03 UTC`
- summary: `첫 실제 /goal이 goal_answer_malformed:task_reason:T1로 실패했다. 등록된 작업 종류가 없는 하위 작업이 Owner 결정 사유를 빠뜨려도 계획 전체를 거절하지 않고, Policy Gate가 그런 하위 작업을 방식과 관계없이 needs_owner로 판정해 사유 누락을 근거로 남긴다. 팀장 안내 문구를 분명히 하고, 실패 메시지에 등록된 사유 코드의 한국어 설명을 더하고, 팀장 답 원문 없는 실패 기록 파일을 쓴다. task 생성, Worker 실행, 자동 실행은 범위 밖이다.`
- source_command: `Owner 지시: task-0226으로 고쳐 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `5d55d1175ab2f3bc31a4472df6f99ca33f032c2e` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=2`, `repair_count=2` (SOP §5 기본값 1회에 Owner가 1회 증액, repair 1·2는 아래 절) |
| 작업 위치 | 저장소 밖 worktree `jarvis-core-worktrees/task-0226-goal-kind-none`, 브랜치 `work/task-0226-goal-kind-none-reason`. main 체크아웃은 그대로 둔다 |

## Owner 제보 (원문, 실제 /goal 실패)

```text
/goal Jarvis Console에 최근 완료된 작업과 현재 진행 상태를 한눈에 볼 수 있는 대시보드를 추가하고, 필요한 하위 작업을 계획해 줘.
jarvis-bot앱 — 오후 8:27
 목표 계획 시작 (dry-run): Jarvis Console에 최근 완료된 작업과 현재 진행 상태를 한눈에 볼 수 있는 대시보드를 추가하고, 필요한 하위 작업을 계획해 줘.
팀장이 읽기 전용으로 저장소를 살펴 하위 작업으로 나누고, 작업마다 정책 판정을 붙입니다.
task 생성과 실행은 하지 않습니다. 끝나면 이 메시지에 여는 스레드에 올립니다(스레드를 열 수 없으면 이 채널).
목표 계획 실패: 아무것도 만들거나 실행하지 않았습니다.
reason: `goal_answer_malformed:task_reason:T1`
팀장 사용량 추정: $0.18
```

번호와 글머리표만 뺀 Owner 메시지다.

## Owner 결정 (원문, 작업 지시)

```text
[Manager 질문]
새 task-0226으로 이 실패를 고칠까요?

[Owner 답]
task-0226으로 고쳐
```

질문 앞의 Manager 보고가 제안한 고칠 방향(Manager 문장, 승인 원문 아님): 1) 종류가 `none`인데 사유가 없으면 계획을 거절하지 않고 needs_owner로 판정하고, 읽기 전용이면서 종류가 `none`인 작업도 needs_owner로 바꾼다. 2) 팀장 안내 문구에 "kind none이면 읽기 전용이어도 사유를 적는다"를 넣는다. 3) 실패 진단: 거절된 팀장 답을 저장소 밖 계획 폴더에 남기고 실패 메시지 이유를 한국어로 풀어 쓴다.

## 조사 (baseline 기준)

- `goal_plan._parse_task`는 `kind == "none"`이고 `owner_decision`이 `none`이면 `task_reason:<id>`로 계획 전체를 거절했다. 팀장 안내는 "otherwise kind none, and say why in owner_decision"이었다.
- 등록된 Worker 작업 종류는 `studyroom_content`, `daily_ai_radar`, `research_council`뿐이라 Console 목표의 하위 작업은 모두 `none`이 된다.
- Policy Gate v0는 `none`인 수정 작업에만 `no_registered_kind`를 붙였다. 읽기 전용이고 `none`이며 사유가 없는 작업은 다른 신호가 없으면 auto였다.
- 실패한 팀장 답은 어디에도 남지 않는다. 팀장 답 원문은 파싱된 계획으로만 밖에 나간다(`claude_lead.run_lead` 문서 문자열, task-0183 repair 2, master-plan의 task-0183 항목이 "원문 노출"을 Reviewer 보안 지적으로 기록).

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/worker/goal_plan.py`, `orchestrator/worker/policy_gate.py`, `adapters/discord/bot_minimal.py`, `orchestrator/worker/run_smoke_tests.py`, `adapters/discord/README.md`, `docs/jarvis-multi-agent-sop-v0.1.md`, 이 task 기록 |
| deny | `orchestrator/worker/claude_worker.py`, `orchestrator/worker/claude_lead.py`, Console, `docs/lead-goal-plan-design.md`(History), `docs/master-plan.md`(DONE 전), 작업 종류 추가, task 생성·Worker 실행·자동 실행, 다른 task 기록, validator, `jarvis.bat`, `.env`, push, 봇 재시작 |

## Start

Console(worktree에서 띄움) Voice Inbox의 Create Local Task Preview를 확인하고 Confirm해 TODO 기록을 만들었다. Project Control의 Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다. Console은 수정 전에 껐다. 그 뒤 title·summary·source_command를 이 task 내용으로 고쳤다.

## 구현

- `orchestrator/worker/goal_plan.py`: `task_reason` 거절을 없앴다. 사유가 `none`이면 `owner_decision`은 지금처럼 없음(None)으로 받는다. 팀장 안내에 "This holds for read_only sub-tasks too: a kind none sub-task never has owner_decision none."을 더했다.
- `orchestrator/worker/policy_gate.py`: 등록된 kind가 없으면 방식과 관계없이 `no_registered_kind`(needs_owner)를 붙이고, 팀장 사유도 없으면 `lead_reason_missing`("팀장이 Owner 결정 사유를 적지 않음")을 더한다. 판정이 엄격해지기만 한다(읽기 전용 `none` 작업이 auto에서 needs_owner로). 정책 버전 문자열은 바꾸지 않았다(Manager 해석: v0는 Owner 승인 전 제안이라 기준 변경 이력은 이 기록에 둔다).
- `adapters/discord/bot_minimal.py`: 실패 메시지 첫 줄을 "task를 만들거나 실행하지 않았습니다"로 바꾸고, 사유 코드 아래 `- 이유:` 한국어 설명(`GOAL_FAILURE_LABELS`, `GOAL_MALFORMED_LABELS`, `_goal_failure_label`; 등록된 코드에만 붙고 `lead_failed:`로 시작하는 그 밖의 코드는 공통 설명, 그 밖의 모르는 코드는 설명 없음), 사용량, 실패 기록 경로를 붙인다. 실패하면 계획 파일과 같은 폴더에 팀장 답 원문 없이 `goal_id`, `created_at`, `goal`, `dry_run`, `executed: false`, `ok: false`, `reason`, `usage`를 담은 실패 기록을 쓴다.
- 제안 3의 "거절된 팀장 답을 남긴다"는 하지 않았다. 팀장 답 원문은 파싱된 계획으로만 밖에 나간다는 기존 규칙(조사 절)과 부딪히고, 팀장이 읽은 내용이 답에 섞이면 그대로 파일에 남기 때문이다. 대신 원문 없는 실패 기록과 한국어 설명으로 진단을 돕는다. self-review 지적 3에 따라 candidate 전에 Owner에게 물었고, Owner가 이 축소를 수용했다(아래 Owner 결정 절).
- 문서: Discord README `/goal` 절(실패 설명, 실패 기록, `none` 작업 판정), SOP §10.1 목표 계획 문단(같은 두 내용). 설계 기록 `docs/lead-goal-plan-design.md`는 History라 고치지 않았다.
- `orchestrator/worker/run_smoke_tests.py`: 형식 오류 목록에서 사유 없는 `none` 사례를 빼고, 그 계획이 받아들여져 세 작업 모두 needs_owner(읽기 전용 포함, 사유 누락 근거, 사유가 있으면 누락 근거 없음)인지, 라벨, 팀장 안내 문구, 실패 기록 파일(저장소 밖, 원문 없음), 실패 메시지의 한국어 설명과 기록 경로, 라벨 함수(작업 id, 모르는 코드), 첫 실제 실패와 같은 Console 목표가 계획을 보이는지 확인한다.

## Implementer 검증 (작업 트리, candidate 전)

- 첫 실행: Worker smoke total=759 failed=0(baseline 751에 새 검사 8건, 기존 목표 계획·팀장 검사 그대로 통과), SOP validator PASS, Discord `--self-check-suite` rc=0, `git diff --check` 통과.
- self-review 수정 뒤 다시 돌린 결과는 아래 Self-review 절에 적는다.

## Self-review

SOP §3대로 staged 변경에 `claude -p --agent self-reviewer --tools Read,Grep,Glob`을 한 번 돌렸다(Reviewer 판정 아님, 사용량 추정 $0.50). 지적 네 건과 처리:

1. major: SOP 목표 계획 문단 끝의 "실패하면 사유 코드만 보낸다"가 새 실패 메시지(설명, 사용량, 기록 경로)와 어긋났다. 그 문장을 실제 메시지 항목으로 고쳤다.
2. minor: README 4·5항, SOP, 이 기록 구현 절이 메시지와 실패 기록에 실리는 항목을 서로 다르게 "만"으로 나열했다. 세 곳을 "팀장 답 원문 없이"와 실제 항목으로 맞췄다.
3. minor: 제안 3의 원문 저장을 Manager 판단만으로 뺐다. candidate 전에 Owner에게 물어 수용 답을 받았다(아래 Owner 결정 절).
4. minor: `lead_failed:<예외 이름>` 같은 코드에는 설명이 없는데 summary와 README는 모든 실패에 설명이 붙는 것처럼 읽혔다. `lead_failed:`로 시작하는 그 밖의 코드에 공통 설명 "팀장 실행이 실패했습니다"를 두고 smoke에 확인을 더했으며, README와 구현 절에 설명이 붙는 범위를 적었다.

수정 뒤 다시 돌린 결과: Worker smoke total=759 failed=0(공통 설명 확인은 기존 라벨 검사 안에 더해 검사 수는 같음), SOP validator PASS, Discord `--self-check-suite` rc=0, `git diff --check` 통과, 사전 점검은 candidate 직전에 다시 돌린다.

## Owner 결정 (원문, self-review 지적 질문)

```text
[Manager 질문]
task-0226 self-review 지적: 승인하신 제안 3의 '거절된 팀장 답 원문을 저장소 밖에 저장'을 빼고, 원문 없는 실패 기록(목표·사유 코드·사용량)과 한국어 이유 설명만 넣었습니다. 기존 규칙(task-0183 repair 2)이 팀장 답 원문을 파싱된 계획으로만 밖에 내보내고, 팀장이 읽은 내용이 답에 섞이면 그대로 파일에 남기 때문입니다. 어떻게 할까요?

[Owner 답]
원문 저장 빼는 것 수용 (Recommended)
```

## Reviewer 결과 (candidate `5bd1c70465c442678af119ca366f1d5b60f5db05`)

verdict FINDINGS, `self_deviations` 없음. minor 3건:

1. `task_text` 설명이 제목의 백틱 때문에 같은 코드가 나는 경우를 말하지 않는다.
2. `task_depends_on` 설명이 선행 작업 목록이 문자열 목록이 아니거나 같은 id가 되풀이되는 경우를 말하지 않는다.
3. Manager 요약 A6이 Owner 수용 행을 A11로 가리키는데 수용 답은 A12다.

Reviewer unverified: candidate에서의 검사 실행 결과, 저장소 안 계획 폴더에서 실패한 계획이 실패 기록을 쓰지 않는지(smoke 없음), 실제 봇의 `/goal`.

## Repair 1 (`repair_count=1`)

- 지적 1·2를 고치면서 설명 전체를 `goal_plan`의 실패 조건과 대조했다. `json`, `fields`, `text`, `tasks`, `task_fields`, `task_paths`, `task_acceptance` 설명도 원인 일부만 말하고 있어, 각 설명이 그 코드를 내는 모든 경우를 말하도록 고쳤다.
- 지적 3: A6의 참조를 A12로 고쳤다.
- smoke: 형식 오류 목록의 모든 사유에 설명이 있는지, 백틱 제목과 되풀이된 선행 작업의 설명이 그 경우를 말하는지, 저장소 안 계획 폴더에서 실패한 계획이 실패 기록을 쓰지 않고 답에 기록 경로도 없는지 확인을 더했다(Reviewer unverified 항목).
- repair 뒤 검증(작업 트리): Worker smoke total=761 failed=0(새 검사 2건), SOP validator, Discord self-check, `git diff --check`, 사전 점검.
- 이전 candidate의 Reviewer 결과는 무효이며 새 candidate에 fresh Reviewer와 QA를 돌린다.

## Reviewer 결과 (repair 1 candidate `3b5d3c33142782a4b9a89c1e5ff78fca9d744329`)

verdict FINDINGS, `self_deviations` 없음. minor 2건: `task_paths`와 `task_acceptance` 설명이 목록 안에 문자열이 아닌 항목이 있는 경우를 말하지 않아, Repair 1 절의 "모든 경우를 말하도록 고쳤다"가 이 두 코드에서 맞지 않는다. Reviewer unverified: candidate에서의 검사 실행 결과, 실제 봇의 `/goal`, 팀장이 읽은 내용이 섞인 다른 형식 오류 답에서도 실패 기록에 원문이 없는지. repair 예산이 소진돼 Owner에게 물었다.

## Owner 결정 (원문, repair 2 증액)

```text
[Manager 질문]
task-0226 repair candidate 3b5d3c3의 Reviewer minor 2건: /goal 실패 시 보이는 한국어 설명 중 task_paths와 task_acceptance 두 개가 '목록 안에 문자열이 아닌 항목'인 경우를 말하지 않습니다(사유 코드는 그대로 보이고, 판정·실행에는 영향 없음). repair 예산 1회는 소진됐습니다. 어떻게 할까요?

[Owner 답]
repair 1회 증액해 고침 (Recommended)
```

## Repair 2 (`repair_count=2`, Owner 증액)

- `task_paths`, `task_acceptance` 설명에 문자열이 아닌 항목을 더했다. Repair 1의 대조가 이 두 경우를 놓쳤으므로 설명 전부를 `goal_plan`의 실패 경로와 다시 하나씩 대조했고, `task_id` 설명도 id가 문자열이 아닌 경우와 실제 형식(T1~T99)을 말하도록 고쳤다. 나머지 설명은 그 코드를 내는 경우를 모두 말한다(`task_kind`, `task_mode`, `task_risk`는 어떤 값이든 정해진 값이 아니면 같은 설명이 맞다).
- smoke: 경로, 완료 조건, id에 문자열이 아닌 값을 넣은 답의 사유 코드와 그 설명이 "문자열이 아니"를 말하는지 확인을 기존 설명 검사에 더했다.
- 실패 기록은 `_run_goal_job`이 파싱 결과의 `reason`과 `usage`만 넣어 쓰므로 팀장 답의 형식 오류 종류와 관계없이 원문이 들어가지 않는다(코드 읽기, Reviewer unverified 셋째 항목에 대한 Manager 해석).
- repair 뒤 검증(작업 트리): Worker smoke total=761 failed=0(기존 설명 검사에 조건만 더해 검사 수는 같음), SOP validator, Discord self-check, `git diff --check`, 사전 점검.
- 이전 candidate의 Reviewer 결과는 무효이며 새 candidate에 fresh Reviewer와 QA를 돌린다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A0a | Owner 제보 (원문, 실제 /goal 실패) | "/goal Jarvis Console에 최근 완료된 작업과 현재 진행 상태를 한눈에 볼 수 있는 대시보드를 추가하고, 필요한 하위 작업을 계획해 줘." | 실패한 목표. smoke의 Console 목표 사례와 QA의 실제 dry-run에 쓴다 |
| A0b | Owner 제보 (원문, 실제 /goal 실패) | "jarvis-bot앱 — 오후 8:27" | 봇 답의 표지(재시작한 봇, main `5d55d11`) |
| A0c | Owner 제보 (원문, 실제 /goal 실패) | "목표 계획 시작 (dry-run): Jarvis Console에 최근 완료된 작업과 현재 진행 상태를 한눈에 볼 수 있는 대시보드를 추가하고, 필요한 하위 작업을 계획해 줘." | 시작 안내는 정상이었다. 바꾸지 않는다 |
| A0d | Owner 제보 (원문, 실제 /goal 실패) | "팀장이 읽기 전용으로 저장소를 살펴 하위 작업으로 나누고, 작업마다 정책 판정을 붙입니다." | 시작 안내. 바꾸지 않는다 |
| A0e | Owner 제보 (원문, 실제 /goal 실패) | "task 생성과 실행은 하지 않습니다." | 시작 안내. 실패해도 task는 생기지 않았다 |
| A0f | Owner 제보 (원문, 실제 /goal 실패) | "끝나면 이 메시지에 여는 스레드에 올립니다(스레드를 열 수 없으면 이 채널)." | 시작 안내. 바꾸지 않는다 |
| A0g | Owner 제보 (원문, 실제 /goal 실패) | "목표 계획 실패: 아무것도 만들거나 실행하지 않았습니다." | 실패 기록 파일을 쓰게 되므로 "task를 만들거나 실행하지 않았습니다"로 바꿨다 |
| A1 | Owner 제보 (원문, 실제 /goal 실패) | "reason: `goal_answer_malformed:task_reason:T1`" | 고칠 실패. 조사 절의 거절 규칙이 원인이다 |
| A2 | Owner 제보 (원문, 실제 /goal 실패) | "팀장 사용량 추정: $0.18" | 실패에도 비용이 들었다. 실패 기록에 사용량을 남긴다 |
| A3 | Owner 결정 (원문, 작업 지시) | "[Manager 질문]" | 질문의 표지 |
| A4 | Owner 결정 (원문, 작업 지시) | "새 task-0226으로 이 실패를 고칠까요?" | A6 답의 질문. 고칠 방향은 질문 앞 Manager 보고의 제안 1~3이다 |
| A5 | Owner 결정 (원문, 작업 지시) | "[Owner 답]" | 답의 표지 |
| A6 | Owner 결정 (원문, 작업 지시) | "task-0226으로 고쳐" | 제안 1·2를 구현했다. 제안 3은 한국어 설명과 원문 없는 실패 기록으로 구현하고, 팀장 답 원문 저장은 기존 규칙 때문에 하지 않았고 Owner가 A12에서 수용했다 |
| A7 | Owner 결정 (원문, self-review 지적 질문) | "[Manager 질문]" | 질문의 표지 |
| A8 | Owner 결정 (원문, self-review 지적 질문) | "task-0226 self-review 지적: 승인하신 제안 3의 '거절된 팀장 답 원문을 저장소 밖에 저장'을 빼고, 원문 없는 실패 기록(목표·사유 코드·사용량)과 한국어 이유 설명만 넣었습니다." | self-review 지적 3 |
| A9 | Owner 결정 (원문, self-review 지적 질문) | "기존 규칙(task-0183 repair 2)이 팀장 답 원문을 파싱된 계획으로만 밖에 내보내고, 팀장이 읽은 내용이 답에 섞이면 그대로 파일에 남기 때문입니다." | 축소의 근거 |
| A10 | Owner 결정 (원문, self-review 지적 질문) | "어떻게 할까요?" | 답은 A12 |
| A11 | Owner 결정 (원문, self-review 지적 질문) | "[Owner 답]" | 답의 표지 |
| A12 | Owner 결정 (원문, self-review 지적 질문) | "원문 저장 빼는 것 수용 (Recommended)" | 원문 저장 없이 진행한다. 이 답은 이 task에만 효력이 있다 |
| A13 | Owner 결정 (원문, repair 2 증액) | "[Manager 질문]" | 질문의 표지 |
| A14 | Owner 결정 (원문, repair 2 증액) | "task-0226 repair candidate 3b5d3c3의 Reviewer minor 2건: /goal 실패 시 보이는 한국어 설명 중 task_paths와 task_acceptance 두 개가 '목록 안에 문자열이 아닌 항목'인 경우를 말하지 않습니다(사유 코드는 그대로 보이고, 판정·실행에는 영향 없음)." | repair 1 candidate의 Reviewer 지적 |
| A15 | Owner 결정 (원문, repair 2 증액) | "repair 예산 1회는 소진됐습니다." | 증액 전 `repair_count=1`, `repair_budget=1` |
| A16 | Owner 결정 (원문, repair 2 증액) | "어떻게 할까요?" | 답은 A18 |
| A17 | Owner 결정 (원문, repair 2 증액) | "[Owner 답]" | 답의 표지 |
| A18 | Owner 결정 (원문, repair 2 증액) | "repair 1회 증액해 고침 (Recommended)" | `repair_budget=2`. Repair 2 절에서 두 설명을 고쳤다. 증액은 이 task에만 효력이 있다 |
