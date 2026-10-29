# task-0208-console-uncommitted-task-record

- id: `task-0208-console-uncommitted-task-record`
- title: `커밋되지 않은 task 기록을 카드에 표시`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-29 15:47 UTC`
- updated_at: `2026-10-29 15:48 UTC`
- summary: `task-0200처럼 git에 들어가지 않은 task 기록은 Console 카드만 보고는 알 수 없다. Console이 이미 읽는 git status 결과(허용 목록 명령, 새 명령 없음)를 같은 요청의 Task View 투영에 넘겨, memory/tasks 기록이 미추적·커밋 안 된 수정·stage됨이면 카드에 한국어 Git 상태 한 줄을 보인다. 그룹·순위·counts, task 기록, 쓰기 흐름은 바꾸지 않고 push는 하지 않는다.`
- source_command: `Owner 지시: Console 다음 작업 후보 3 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `e7d7ae8a11e7d5f9414e3810f70579b424f105f8` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문)

```text
[Manager 제안: 다음 작업]
| 2 | Console 후보 3: 커밋되지 않은 task 기록을 카드에 표시 | task-0200처럼 미추적으로 남은 기록을 Console에서 바로 알아볼 수 있습니다. | 중간. Console이 `git status`를 실행해야 해서, 하위 프로세스를 실행하는 경계와 timeout을 정해야 합니다. |

[Owner 답]
console 후보 3 시작해
```

## Owner 결정 (원문, 착수 전 bounded question)

```text
[Manager 질문 1]
어떤 상태의 task 기록을 카드에 표시할까요?

[Owner 답 1]
미추적·수정 모두, 구분 표시 (Recommended)

[Manager 질문 2]
표시 문구는 어느 언어로 할까요?

[Owner 답 2]
한국어 (Recommended)

[Manager 질문 3]
카드 한 줄 외에 Task View 상단에 개수도 보일까요?

[Owner 답 3]
카드 한 줄만 (Recommended)
```

선택지 설명(Manager가 질문과 함께 보인 문구, Owner 원문 아님):

- 답 1: "미추적(git에 없음), 커밋 안 된 수정, stage됨을 각각 다른 문구로 보입니다. Console Start·Complete 뒤 checkpoint 전의 기록도 보입니다."
- 답 2: "task-0207의 실패 의미·가능한 조치처럼 항목 이름과 문구를 한국어로 씁니다(예: 'Git 상태: 미추적, 커밋 안 됨')."
- 답 3: "카드 Facts에 한 줄만 더합니다. 그룹·순위·counts는 그대로여서 변경이 가장 작습니다."

질문 전에 Manager가 Owner에게 알린 조사 결과(Owner 원문 아님): Console은 이미 허용 목록 명령 `git status --short --untracked-files=all`을 `run_read_only_git`(shell 없음, timeout 5초, `GIT_OPTIONAL_LOCKS=0`)으로 실행해 `repo.working_tree_status`에 담고 있으므로, 그 결과를 같은 요청의 task 투영에 넘기면 새 git 명령·하위 프로세스·허용 목록 변경이 필요 없다.

## 조사 (등록 전)

- `apps/jarvis-console/run_web_app.py` `overview_payload()`는 `repo_status_payload()`(위 git status 포함)를 먼저 부른 뒤 `project_task_view_items(task_candidates)`로 task 카드를 만든다. 두 결과는 같은 응답에 담기지만 카드에는 git 상태가 이어지지 않는다.
- `READ_ONLY_GIT_COMMANDS`, `validate_read_only_git_args`, `run_read_only_git`는 바꿀 필요가 없다. git 실패는 지금처럼 `repo_status_payload()`에서 `RegistryError`로 overview 전체가 실패한다(기존 동작).
- task 기록 파일 이름은 `TASK_FILE_PATTERN`(ASCII)이라 git이 경로를 따옴표로 감싸지 않는다. 카드 항목의 `path`는 저장소 상대 POSIX 경로(`memory/tasks/<name>.md`)로 git status 경로와 같은 형식이다.

## 설계

1. 서버: 함수 `task_record_git_states(working_tree_status)`가 `git status --short` 줄을 읽어 `memory/tasks/` 아래 경로만 `미추적`(`??`), `커밋 안 된 수정`(작업 트리 쪽 Y가 공백이 아님), `stage됨`(index 쪽 X만 있음)으로 나눈다. rename(`old -> new`)은 새 경로를, 따옴표로 시작하는 경로와 `clean`·빈 결과는 무시한다. `project_task_view_items()`에 선택 인자 `git_states`를 더해, 상태가 있는 항목에만 `git_state = {"kind", "label"}`을 붙인다. `overview_payload()`만 이미 가진 `repo["working_tree_status"]`로 이 인자를 채운다. 새 git 호출은 없다.
2. 화면: `item.git_state`가 있으면 카드 Facts에 `Git 상태` 한 줄(escape)을 보인다. 버튼·fetch 없음. 그룹·순위·counts·`next_action`은 그대로다.
3. 테스트: 파서의 세 종류·rename·따옴표·다른 경로·clean, 투영에 키가 붙는 항목과 안 붙는 항목, `overview_payload()`가 새 git 명령 없이 기존 결과를 넘기는지, 화면 harness.
4. 문서: `apps/jarvis-console/README.md`.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `apps/jarvis-console/run_web_app.py`, `apps/jarvis-console/web/app.js`, `apps/jarvis-console/run_smoke_tests.py`, `apps/jarvis-console/README.md`, `memory/tasks/task-0208-console-uncommitted-task-record.md` |
| deny | `jarvis.bat`, `READ_ONLY_GIT_COMMANDS`·`run_read_only_git`·`validate_read_only_git_args`의 변경, Discord 봇·Worker·writer 코드, 상태 계약 문서, 다른 task 기록, AGENTS·agent 정의·validator, 외부 API·credential, push |

## 계획

1. Console Start(TODO → DOING).
2. 구현: 서버, 화면, smoke test, README.
3. 검사: Console smoke(PYTHONUTF8 없이·있이), SOP validator, `git diff --check`, `node --check app.js`, 실제 브라우저(이 task 기록 자신이 미추적이라 그 카드로 확인).
4. 사전 점검 → self-review → candidate → Reviewer → QA → Evidence·Complete → checkpoint → master-plan. push는 별도 지시.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다(status·updated_at 줄만 바뀜, updated_at `2026-10-29 15:48 UTC`). Console은 구현 전에 껐다.

## 구현

- `apps/jarvis-console/run_web_app.py`: 상수 `TASK_RECORD_GIT_DIRECTORY`(`memory/tasks/`), `TASK_RECORD_GIT_LABELS`(세 종류의 한국어 문구). 함수 `task_record_git_states(working_tree_status)`는 `git status --short` 줄의 XY와 경로를 읽어 `memory/tasks/`로 시작하는 경로만 `untracked`(`??`), `modified`(작업 트리 쪽 Y가 공백이 아님, 일부 stage 포함), `staged`(index 쪽 X만)로 나눈다. rename은 새 경로, 따옴표로 시작하는 경로·형식이 다른 줄·`clean`은 무시한다. `project_task_view_items()`에 선택 인자 `git_states`를 더해 상태가 있는 항목에만 `git_state = {"kind", "label"}`을 붙인다. `overview_payload()`는 이미 가진 `repo["working_tree_status"]`로 이 인자를 채운다. `READ_ONLY_GIT_COMMANDS`, `run_read_only_git`, `validate_read_only_git_args`는 바꾸지 않았고 새 git 호출은 없다.
- `apps/jarvis-console/web/app.js`: 카드 Facts의 Path 뒤에 `item.git_state`가 있을 때만 `Git 상태` 한 줄(escape). 버튼·fetch 없음.
- `apps/jarvis-console/run_smoke_tests.py`: `_test_task_record_git_state`(파서의 세 종류·rename·따옴표·다른 경로·형식이 다른 줄·clean, 투영에서 키가 붙는 항목과 나머지가 그대로인지, `overview_payload()`가 status 명령을 한 번만 부르고 모든 git 호출이 허용 목록 안인지, 넘긴 status로 카드에 키가 붙는지, node 렌더 harness).
- `apps/jarvis-console/README.md`: task-0207 실패 의미·가능한 조치 문단 뒤에 `Git 상태` 문단을 더했다.

## Implementer 검증 (작업 트리)

- `python -B apps/jarvis-console/run_smoke_tests.py`(PYTHONUTF8 없이) 통과, `PYTHONUTF8=1`로도 통과.
- SOP validator PASS, `git diff --check` 통과, `node --check app.js` 통과.
- 실제 Console(127.0.0.1:8790, 실제 기록): 미추적인 이 task 기록 카드에만 `Git 상태: 미추적…` 줄이 보였고 다른 카드에는 없었다. 콘솔 오류 없음. 서버는 껐다.
- Worker·봇·writer 코드는 바꾸지 않았으므로 Worker smoke와 Discord self-check는 QA에서 돌린다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다. 오른쪽 칸에서 "Manager 해석"이라고 적은 부분은 승인 원문에 없는 내용이며, 근거가 선택지 설명(Manager 문구, Owner 원문 아님)이거나 Manager 판단이다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 제안: 다음 작업]" | 제안의 표지. 해석할 조건이 아니다 |
| A2 | Owner 결정 (원문) | "\| 2 \| Console 후보 3: 커밋되지 않은 task 기록을 카드에 표시 \| task-0200처럼 미추적으로 남은 기록을 Console에서 바로 알아볼 수 있습니다." | 커밋되지 않은 `memory/tasks` 기록 카드에 `Git 상태` 한 줄을 보인다. 미추적 기록은 `미추적` 문구다 |
| A3 | Owner 결정 (원문) | "\| 중간." | 제안이 적은 위험 등급. 조건이 아니다 |
| A4 | Owner 결정 (원문) | "Console이 `git status`를 실행해야 해서, 하위 프로세스를 실행하는 경계와 timeout을 정해야 합니다. \|" | Manager 해석: 조사에서 Console이 이미 허용 목록 명령 `git status --short --untracked-files=all`을 `run_read_only_git`(shell 없음, timeout 5초, `GIT_OPTIONAL_LOCKS=0`)으로 실행함을 확인해 Owner에게 질문 전에 알렸다. 그래서 경계와 timeout은 기존 것을 그대로 쓰고 새 명령·하위 프로세스·허용 목록 변경을 만들지 않았다(smoke: status 호출 1회, 모든 호출이 허용 목록 안). 제안이 말한 "정해야" 할 새 경계는 없다 |
| A5 | Owner 결정 (원문) | "[Owner 답]" | 답의 표지 |
| A6 | Owner 결정 (원문) | "console 후보 3 시작해" | 후보 3 착수 승인. 세부는 A10·A14·A18의 답으로 정했다. Manager 해석: 범위 표 owned의 smoke test, README, 이 task 기록은 승인 원문에 이름이 없고, 제품 코드 변경을 검사·문서화·기록하려는 Manager 판단으로 넣었다 |
| A7 | Owner 결정 (원문, 착수 전 bounded question) | "[Manager 질문 1]" | 질문의 표지 |
| A8 | Owner 결정 (원문, 착수 전 bounded question) | "어떤 상태의 task 기록을 카드에 표시할까요?" | A10의 질문 |
| A9 | Owner 결정 (원문, 착수 전 bounded question) | "[Owner 답 1]" | 답의 표지 |
| A10 | Owner 결정 (원문, 착수 전 bounded question) | "미추적·수정 모두, 구분 표시 (Recommended)" | 미추적과 수정을 모두 보이고 문구로 구분한다. Manager 해석(선택지 설명 근거): 세 번째 종류 `stage됨`을 따로 두었고, 작업 트리 변경이 있으면 일부가 stage됐어도 `커밋 안 된 수정`으로 보인다 |
| A11 | Owner 결정 (원문, 착수 전 bounded question) | "[Manager 질문 2]" | 질문의 표지 |
| A12 | Owner 결정 (원문, 착수 전 bounded question) | "표시 문구는 어느 언어로 할까요?" | A14의 질문 |
| A13 | Owner 결정 (원문, 착수 전 bounded question) | "[Owner 답 2]" | 답의 표지 |
| A14 | Owner 결정 (원문, 착수 전 bounded question) | "한국어 (Recommended)" | 줄 이름 `Git 상태`와 세 문구를 한국어로 썼다(`git`, `index`, `stage`는 도구 용어라 그대로). Manager 해석(선택지 설명 근거): 줄 이름도 한국어로 했다 |
| A15 | Owner 결정 (원문, 착수 전 bounded question) | "[Manager 질문 3]" | 질문의 표지 |
| A16 | Owner 결정 (원문, 착수 전 bounded question) | "카드 한 줄 외에 Task View 상단에 개수도 보일까요?" | A18의 질문 |
| A17 | Owner 결정 (원문, 착수 전 bounded question) | "[Owner 답 3]" | 답의 표지 |
| A18 | Owner 결정 (원문, 착수 전 bounded question) | "카드 한 줄만 (Recommended)" | 카드 Facts에 한 줄만 더했다. 상단 개수, `task_view_counts`, 그룹·순위·`next_action`은 바꾸지 않았다(diff 기준) |

## Self-review

`self-reviewer`(`claude -p --agent self-reviewer --tools Read,Grep,Glob`, 첫 사전 점검 PASS 뒤 1회, API 환산 약 $0.40)의 지적 1건(minor)을 고쳤다.

1. 구현 절의 README 위치("실행 결과 절 뒤")가 실제(task-0207 문단 뒤)와 다름 → 실제 위치로 고쳤다.

Owner 원문과 Manager 요약(A1–A18)의 조건 대조, 설계·README·코드 일치, 금지한 git helper 무변경은 지적이 없었다. 사전 점검 결과는 아래 candidate 직전 실행이다.
