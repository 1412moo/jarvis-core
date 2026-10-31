# task-0214-console-name-rule-hidden-count

- id: `task-0214-console-name-rule-hidden-count`
- title: `Console이 이름 규칙으로 뺀 task 기록 수 표시`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-31 09:12 UTC`
- updated_at: `2026-10-31 14:27 UTC`
- summary: `Console 탐색은 파일 이름에 secret·token·credential·password·.env가 든 파일을 아무 표시 없이 뺀다. 그래서 task-0043-no-secrets-enforcement.md가 Task View 집계와 화면에서 빠지고, 같은 단어가 든 task는 Console에서 상태를 바꿀 수도 없다. 제외 규칙은 그대로 두고, 이 규칙으로 뺀 task 기록의 수를 Task View에 보이게 한다(파일 이름과 내용은 보이지 않는다). Owner 답(Start as recommended) 뒤 구현했고 candidate 검토 단계다. push는 하지 않는다.`
- source_command: `Owner 지시: N1 등록과 조사 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `ed47f6fed897713e313a8d115c77e4e3ca49efca` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문)

```text
N1을 다음 bounded work package로 등록하고 조사
```

N1은 task-0213 기록 조사 절의 후보 표에 있는 행이다(Owner에게 완료 보고로 보인 표).

## Owner 결정 (원문, 착수 전 bounded question)

```text
[Manager 질문]
Start task-0214 with the recommended answers?

[Owner 답]
Start as recommended
```

추천안(Manager가 등록·조사 보고 4절에 질문과 함께 보인 문구, Owner 원문 아님):

- 표시 범위: "Task View(`memory/tasks`)만 (추천). Recent와 History까지 넓히는 안도 있습니다."
- 표시 내용: "수와 규칙 설명만 (추천). 예: \"1 task record is not listed because its file name contains a word such as secret or token.\" 파일 이름은 보이지 않습니다."
- 언어: "영어 (추천). 바로 위 \"Not shown\" 줄이 영어라 맞춥니다."

같은 보고의 3절(설계 초안)은 Owner에게 아래 "설계 방향"과 같은 내용을 보였다. 수만 세고 파일 이름·경로·내용은 넣지 않는다, 0보다 크면 한 줄을 더한다, 규칙·Recent·History·상태 전이·slug는 바꾸지 않는다, 예상 변경 파일은 `run_web_app.py`·`app.js`·`run_smoke_tests.py`·README·이 기록이다. 5절(비범위)은 slug 대책과 task-0043 이름 변경을 범위 밖으로 보였다. 질문은 이 보고 바로 뒤에 했다.

## 조사 (등록 전)

### 제외 규칙이 있는 곳

- `apps/jarvis-console/run_web_app.py` `SECRET_LIKE_NAME_PARTS = ("secret", "token", "credential", "password", ".env")`. `is_overview_candidate_path()`가 파일 이름(소문자)에 이 중 하나라도 들어 있으면 거짓을 돌려준다. 같은 함수가 확장자(`.json`·`.md`·`.txt`만), 숨김 경로(`.`로 시작), `.git`, `__pycache__`, 허용 폴더 밖 경로도 거른다.
- 이 함수를 쓰는 곳은 세 군데다: `discover_recent_items()`(Recent Tasks·Reports·Checkpoints·Docs/Examples), `discover_history_items()`(Checkpoints/History), 그리고 task 상태 전이용 목록(`selected_task_transition_items()`, `tasks_dir.rglob` 뒤 같은 함수). Task View(`overview_payload()["tasks"]`)와 집계(`task_view_counts`)는 Recent Tasks와 같은 탐색 결과로 만든다.
- `overview_payload()["discovery"]["excluded"]`가 `"secrets-like file names"`를 적지만, `web/app.js`와 README는 이 값을 화면에 보이지 않는다(`app.js`에 `excluded`·`secrets-like` 사용 없음). 제외가 있었는지 화면으로는 알 수 없다.

### 지금 빠지는 파일

baseline에서 `OVERVIEW_DIRECTORIES` 일곱 폴더를 모두 훑어, 허용 확장자이면서 이름 규칙에 걸리는 파일을 셌다. **`memory/tasks/task-0043-no-secrets-enforcement.md` 하나뿐**이다. reports·docs·examples·`apps/jarvis-console`에는 없다.

- 그 결과 Task View 집계 total은 task 파일 수(`task-template.md` 제외)보다 하나 적다. 이 기록을 더한 baseline 작업 트리에서 165 대 166.
- task-0043은 DONE이라 Task View에서는 원래 숨겨지는 쪽이다(Not shown 집계 안). 지금 실제로 잃는 것은 "Not shown: … DONE 150" 같은 수가 하나 적게 나오는 것이다.

### 앞으로 생길 수 있는 경우

- Discord intake의 `orchestrator/discord-intake/task_file_writer.py` `_slugify()`는 제목의 단어를 그대로 slug로 쓴다. 예: "Rotate the bot token" → `rotate-the-bot-token`, "Remove password field" → `remove-password-field`, "secret scanner" → `secret-scanner`(baseline에서 실행해 확인).
- 그런 task 파일은 Console Task View에 나타나지 않는다. 또한 `preview_task_transition()`은 대상이 actionable 목록에 있어야 해서(`task_not_found_in_actionable_view`), Console로 Start·Hold·Complete·Close를 할 수 없다. 수동 task도 같다. task-0212가 처음 id에 `secret`을 넣었다가 Console에 안 보여 id를 바꿨다(task-0212 기록 조사 절).
- 이 task는 그 경우를 "보이게" 할 뿐 이름 규칙이나 slug 규칙을 바꾸지 않는다. slug 쪽 대책은 범위 밖 후보다.

### 기존 화면

- Task View 아래 `taskViewHiddenCountsMarkup()`(task-0162)가 "Not shown: N of M Tasks (상태별 수). Read-only count; …" 한 줄을 영어로 보인다. 새 표시를 둘 자연스러운 자리다.
- smoke(`apps/jarvis-console/run_smoke_tests.py`)는 `task_view_counts`의 `displayed + hidden == total`과 상태별 합을 검사한다. 새 수는 이 합과 별개로 두어야 기존 검사가 그대로 맞다.

### 설계 방향 (Owner 답 전 초안)

1. `memory/tasks` 탐색에서 이름 규칙 때문에만 빠진 파일의 **수**를 센다(확장자·숨김 경로로 빠진 것은 세지 않는다). 파일 이름·경로·내용은 payload에 넣지 않는다.
2. 그 수를 `task_view_counts`에 별도 필드로 붙이고, 0보다 크면 Task View 아래에 한 줄을 더한다.
3. `SECRET_LIKE_NAME_PARTS`, `is_overview_candidate_path()`의 판정, Recent·History 탐색, 상태 전이 규칙은 바꾸지 않는다.

## 범위 (초안, Owner 답으로 확정)

| 구분 | 경로 |
| --- | --- |
| owned | `apps/jarvis-console/run_web_app.py`(수 세기와 payload 필드), `apps/jarvis-console/web/app.js`(한 줄 표시), `apps/jarvis-console/run_smoke_tests.py`(새 검사), `apps/jarvis-console/README.md`(설명 한 문단), 이 task 기록 |
| deny | 제외 규칙 자체, 파일 이름·내용 노출, Recent·History 화면, 상태 전이, Discord slug 규칙, task-0043 파일 이름 변경, 다른 task 기록, `jarvis.bat`, `.env`, push |

Owner 답 "Start as recommended"로 이 범위 초안과 설계 방향, 추천안 세 개(Task View만, 수와 규칙 설명만, 영어)를 그대로 쓴다.

## 계획

1. Owner bounded question(표시 범위, 문구, 언어)에 답을 받는다.
2. Console Start(TODO → DOING).
3. 구현과 검사: Console smoke(PYTHONUTF8 유무), self-test, 실제 저장소에서 수가 1인지, 임시 fixture에서 0·여러 개일 때, payload에 파일 이름이 없는지, SOP validator, `git diff --check`, 비밀 정보 검사기.
4. 사전 점검 → self-review → candidate → Reviewer → QA → Evidence·Complete → checkpoint. push는 별도 지시.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다(status·updated_at 줄만 바뀜, updated_at `2026-10-31 14:27 UTC`). Console은 구현 전에 껐다.

## 구현

- `apps/jarvis-console/run_web_app.py`
  - 새 함수 `name_rule_excluded_count(directory_key)`: 한 탐색 폴더에서 `is_overview_candidate_path()`가 거른 파일 가운데, 이름의 `SECRET_LIKE_NAME_PARTS` 단어를 `x`로 바꾼 같은 경로가 통과하는 것만 센다. 이름 맨 앞의 `.`는 바꾸기 전에 떼어 두었다가 다시 붙이므로 `.env…`로 시작하는 숨김 이름도 숨김으로 남는다. 그래서 확장자·숨김 경로·허용 폴더 판정은 기존 함수가 그대로 정한다. 수만 돌려주고 이름·경로·내용은 돌려주지 않는다.
  - `task_view_counts()`에 키워드 인자 `name_rule_excluded`(기본 0)를 더하고, 결과에 `"name_rule_excluded"` 필드 하나를 더했다. `total`·`displayed`·`hidden`·`hidden_by_status`는 그대로다.
  - `overview_payload()`가 `name_rule_excluded_count("memory_tasks")`를 넘긴다.
  - `SECRET_LIKE_NAME_PARTS`, `is_overview_candidate_path()`, `discover_recent_items()`, `discover_history_items()`, 상태 전이 코드는 바꾸지 않았다.
- `apps/jarvis-console/web/app.js`: 새 함수 `taskViewNameRuleExcludedMarkup(counts)`가 수가 0보다 큰 숫자일 때만 영어 한 줄을 만든다. 1일 때 "Name rule: 1 task record is not listed because its file name contains a word such as secret or token. Discovery skips such names, so it is not in the counts above and cannot be changed here.", 2 이상이면 복수형이다. `renderActionableTaskView()`가 기존 "Not shown" 줄 바로 아래에 이 줄을 넣는다. 버튼이나 요청은 없다.
- `apps/jarvis-console/run_smoke_tests.py`: 새 검사 `_test_task_view_name_rule_excluded_count()`를 더하고 `main` 목록에서 task-0162 검사 다음에 부른다.
- `apps/jarvis-console/README.md`: 기능 목록에 한 항목을 더했다.

## Implementer 검증 (작업 트리)

- 새 smoke 검사의 내용:
  - 임시 fixture(저장소 안 `name-rule-fixture/`, `finally`에서 지움)에서 이름 규칙 파일이 없으면 0이다.
  - 이름 규칙 파일 두 개(`…-rotate-the-bot-token.md`, `…-remove-password-field.md`)에 다른 이유로 빠지는 파일 네 개(`.py` 확장자, `.hidden/` 아래, `.`로 시작하는 이름, `.env`로 시작하는 이름)를 더하면 2다.
  - `total`·`displayed + hidden`·Task View 목록·`selected_task_transition_items()`는 이름 규칙 파일이 없을 때와 같다.
  - payload에서 `repo`·`project_control`을 뺀 탐색 부분에 빠진 파일 이름이 없다.
  - 실제 `memory/tasks`의 수가 독립 계산과 같다.
  - node harness로 1·2일 때 문구, 0·없음·문자열일 때 빈 문자열, 버튼·`fetch(` 없음을 본다.
  - 렌더러가 이 함수를 부르는지도 본다.
- 처음 구현은 중립 이름을 `name-rule-probe.md`로 만들어 앞의 `.`가 사라졌다. 그래서 `.task-9107-token.md`도 세어 fixture 값이 3이 되었고, 새 검사가 이를 잡았다. 단어만 바꾸는 방식으로 고친 뒤 2가 됐다.
- `repo.working_tree_status`와 `project_control`의 git 상태 문자열은 원래 미추적 파일 경로를 하나씩 보인다. fixture 이름도 그 문자열에 나타났다. 이것은 기존 동작이고 이 task 범위 밖이라 바꾸지 않았다. 대신 검사 대상을 탐색 부분으로 좁혔다.
- 결과:
  - 실제 저장소: `task_view_counts`는 `total 165, displayed 10, hidden 155, hidden_by_status {DONE 152, CLOSED 3}, name_rule_excluded 1`이다.
  - Console 화면: "Not shown" 줄 아래에 위 1건 문구가 보였다. 확인 뒤 Console은 껐다.
  - Console smoke: PYTHONUTF8=1과 없음 모두 rc=0, "Jarvis Console smoke tests passed".
  - 그 밖의 검사: `run_web_app.py --self-test` 통과, SOP validator PASS, `scripts/check_no_secrets.py` findings=0 PASS, `git diff --check` 통과. fixture 폴더는 남지 않았다.

## Self-review

staged 변경에 self-reviewer를 한 번 돌렸다(Reviewer 판정 아님). minor 세 건이 나왔고 candidate 전에 모두 고쳤다.

1. 메타데이터 summary가 아직 "등록과 조사 단계"였다 → 지금 단계로 고쳤다.
2. `.env`로 시작하는 숨김 이름은 `.env`가 통째로 바뀌어 앞의 `.`가 사라져 세어질 수 있었다 → 맨 앞 `.`를 떼어 두고 바꾸도록 고쳤고, fixture에 `.env-task-9108-notes.md`를 더했다.
3. 범위 초안·설계 방향을 그대로 쓴다는 문장의 근거가 기록에 없었다 → 등록·조사 보고 3·5절이 무엇을 보였는지 추천안 아래에 적고 A5에 Manager 해석을 더했다.

고친 뒤 위 Implementer 검증 결과를 다시 확인했다(smoke 두 방식, self-test, validator, 비밀 정보 검사기, `git diff --check`, 실제 수 1).

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다. 오른쪽 칸에서 "Manager 해석"이라고 적은 부분은 승인 원문에 없는 내용이며, 근거가 추천안(Manager 문구, Owner 원문 아님)이거나 Manager 판단이다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "N1을 다음 bounded work package로 등록하고 조사" | 이 기록으로 등록했고 조사 절에 결과를 적었다. 구현 승인은 A5다 |
| A2 | Owner 결정 (원문, 착수 전 bounded question) | "[Manager 질문]" | 질문의 표지 |
| A3 | Owner 결정 (원문, 착수 전 bounded question) | "Start task-0214 with the recommended answers?" | A5의 질문. 추천안 세 개는 원문 블록 아래에 Manager 문구로 적었다 |
| A4 | Owner 결정 (원문, 착수 전 bounded question) | "[Owner 답]" | 답의 표지 |
| A5 | Owner 결정 (원문, 착수 전 bounded question) | "Start as recommended" | Console Start 뒤 구현했다. Manager 해석(추천안 근거): `memory/tasks` 수만 Task View에 보이고, 수와 규칙 설명만 적고 파일 이름은 보이지 않으며, 문구는 영어다. Manager 해석(보고 3·5절 근거): 같은 보고에 보인 설계 초안·변경 파일·비범위를 범위 표와 설계 방향으로 그대로 쓴다. 범위 표 owned의 이 task 기록은 SOP 기록으로 Manager가 넣었다 |
