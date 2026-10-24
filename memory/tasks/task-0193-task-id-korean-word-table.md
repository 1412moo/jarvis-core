# task-0193-task-id-korean-word-table

- id: `task-0193-task-id-korean-word-table`
- title: `task ID 한영 단어표`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-24 07:43 UTC`
- updated_at: `2026-10-24 08:51 UTC`
- summary: `한글 제목으로 만든 task의 ID가 task-0192-1처럼 내용을 알 수 없게 되는 문제를 고친다. writer의 slug 생성에 한영 단어표를 더해 등록된 한글 낱말은 조사가 붙어도 표준 영문으로 바꾸고, 영문은 유지하고, 중복은 없애고, ID 전체를 60자 안으로 줄인다. 작업 종류 이름은 단어표에 들어 있어 남고, 결과가 비면 기존 예비값 task를 쓴다. 한글이 없는 제목은 기존과 같다. ID 형식과 제목·본문은 바꾸지 않는다.`
- source_command: `Owner 지시: task ID 이름 개선, 1안 기본 2안 예비 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `52eb55474525bb05faac0d91d8e095f24ac806e4` (등록 시점 main HEAD, task-0192까지 push 완료) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문)

```text
[Manager 질문]
방향을 정해 주세요.
1. (권장) 한영 단어표: "스터디룸→studyroom", "용어집→glossary", "추가→add"처럼 자주 쓰는 한글 낱말을 영문으로 바꿉니다. 예: `task-0192-studyroom-glossary-task-thread-term-1-add`. 표에 없는 한글은 빠지고, 길이 상한(약 60자)을 둡니다.
2. 작업 종류 이름 붙이기: 영문이 거의 안 남으면 작업 종류 이름을 붙입니다. 예: `task-0192-studyroom-1`. 가장 작은 변경이지만 무슨 작업인지는 여전히 잘 안 보입니다.
3. 팀장이 영문 이름 제안: 이름은 가장 좋습니다. 다만 "스터디룸"처럼 표지어가 있어 팀장을 거치지 않는 요청에는 적용되지 않고, 팀장 답 형식이 바뀌는 더 큰 작업입니다.

[Owner 답]
1안을 기본으로 하고, 2안을 예비 규칙으로 사용하는 방식을 추천합니다.
기준	1안: 한영 단어표	2안: 작업 종류	3안: 팀장 제안
변경 범위	작음	가장 작음	큼
ID만 보고 내용 파악	비교적 쉬움	어려움	가장 쉬울 수 있음
표지어 없는 요청 대응	가능	가능	팀장을 거치지 않으면 어려움
관리 부담	단어표 관리 필요	낮음	팀장 출력 형식 관리 필요

예를 들어 스터디룸 용어집에 Task Thread 용어 추가라는 작업이라면 다음처럼 만들 수 있습니다.

task-0192-studyroom-glossary-task-thread-term-add-1

이 방식의 장점은 ID만 봐도 작업 대상을 대략 이해할 수 있다는 것입니다.

다만 단어표에 없는 단어가 전부 빠지면 다시 식별력이 떨어질 수 있으므로, 다음 규칙을 함께 두는 게 좋겠습니다.
- 한글 단어와 조사까지 고려해 의미 있는 단어를 추출합니다.
- 등록된 단어는 표준 영문으로 변환합니다.
- 이미 영문인 단어는 유지합니다.
- 의미 없는 조사나 중복 단어는 제거합니다.
- ID 전체 길이는 약 60자로 제한합니다.
- 변환 결과가 비어 있으면 작업 종류 이름을 사용합니다.
- 기존 ID와 감사 기록 형식은 변경하지 않습니다.
중요한 점: 이번 개선은 ID 생성 규칙만 바꾸고, task 파일의 실제 제목과 본문은 그대로 유지해야 합니다.
3. 다음작업 어떻게하면 좋을지
우선 1안과 2안을 결합한 설계를 승인하고, writer의 변경 범위만 검토하는 작업으로 진행하는 것을 추천합니다.

구현 후에는 최소한 다음 사례를 검증해야 합니다.
- 한글 제목: 스터디룸 용어집 수정 → task-0193-studyroom-glossary-...
- 영문 제목: Update README → 기존 영문 ID 생성 동작 유지
- 한영 혼합 제목: Task Thread 용어 추가 → 영문 단어 보존 및 한글 변환
- 표에 없는 한글 제목: 빈 ID가 되지 않고 예비 규칙 적용
- 긴 제목: 60자 제한 준수
- 동일한 제목이 반복될 때: 기존처럼 고유한 ID 생성
이 변경은 task 파일을 생성하는 기준 코드에 영향을 주므로, writer 수정에 대한 Owner 승인을 받은 뒤 진행하는 것이 맞습니다.

제 판단으로는 팀장 출력 형식까지 바꾸는 3안은 지금 도입할 필요가 없습니다. 먼저 작은 변경으로 ID 가독성을 개선하고, 실제 사용에서 단어표가 부족하다는 근거가 생길 때 확장하는 편이 좋겠습니다.
```

## Owner 결정 2: Console 테스트 기대 ID 6줄 (원문)

```text
[Manager 질문]
결정이 필요한 것
1. (권장) `apps/jarvis-console/run_smoke_tests.py`의 기대 ID 6줄만 이번 범위에 넣어 고칩니다. Console 코드는 바꾸지 않습니다. 이어서 self-review → candidate → Reviewer → QA → 완료까지 진행합니다.
2. 범위를 넓히지 않고 task-0193을 멈춥니다.

[Owner 답]
1번으로 진행해
```

## Owner 결정 3: 작업 종류 예비 규칙의 차이 수용 (원문)

```text
[Manager 질문]
결정이 필요한 것
1. (권장) 지금 방식을 받아들입니다. Worker task는 종류 이름이 늘 남고, 종류가 없는 task는 `task`가 됩니다. 이 차이는 작업 기록에 그대로 적어 두었습니다. 바로 candidate → Reviewer → QA → 완료로 갑니다.
2. 규칙을 글자 그대로 지키도록 범위를 넓힙니다. writer가 봇에서 작업 종류를 넘겨받게 하고, 봇의 task 생성 두 곳도 고칩니다. 그만큼 변경과 검토가 커집니다.

[Owner 답]
1번으로 진행해
```

## 설계

1. `orchestrator/discord-intake/task_file_writer.py`의 `_slugify`와 새 도우미 `_korean_slug`·`_cap_slug`, 단어표·상수만 바꾼다. 한글이 없는 제목은 지금 결과를 그대로 쓰고, 길이만 줄인다(아래 4).
2. 한글이 있는 제목: 소문자로 바꾼 뒤 여러 낱말 표현(예: 리서치 카운슬, 다크 모드)을 먼저 영문으로 바꾸고, 공백·기호로 나눈 토막마다 앞에서부터 단어표의 가장 긴 표제어를 찾아 표준 영문으로 바꾼다. 표제어 뒤에 붙은 조사·어미(에, 를, 해줘 등)와 표에 없는 한글은 버리고, 영문·숫자는 그대로 둔다. 같은 단어는 처음 한 번만 남긴다.
3. 단어표에는 작업 종류 이름(스터디룸→studyroom, 리서치 카운슬→research-council, 데일리 ai 레이더→daily-ai-radar)이 들어 있다. 봇이 만드는 Worker task 제목에는 늘 작업 종류 표지어가 있으므로 다른 낱말이 표에 없어도 종류 이름이 남는다(2안의 예비 규칙). writer는 작업 종류를 모르므로 결과가 비면 기존 예비값 `task`를 쓴다.
4. ID 전체는 60자 이하: slug를 50자 이하로 줄인다. 한글 제목은 단어표 낱말 단위로 담아 `research-council` 같은 하이픈 낱말이 중간에서 잘리지 않고, 한글이 없는 제목은 마지막 하이픈에서 자른다(첫 토막이 50자를 넘으면 글자에서 자름).
5. ID 형식(`task-####-<a-z0-9 하이픈>`), 번호 배정, 충돌 회피, 파일 내용(제목·본문)은 바꾸지 않는다. 이미 있는 task의 ID도 바꾸지 않는다. preview와 write가 같은 함수를 쓰므로 Console 미리보기와 실제 생성 ID가 같다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/discord-intake/task_file_writer.py`(`_slugify`, 새 도우미 `_korean_slug`·`_cap_slug`, 단어표·상수만), `orchestrator/discord-intake/run_smoke_tests.py`, `docs/task-model.md`(1절 slug 규칙 한 줄), `apps/jarvis-console/run_smoke_tests.py`(Owner 결정 2: 기대 ID 6줄만), `memory/tasks/task-0193-task-id-korean-word-table.md` |
| deny | `jarvis.bat`, `apps/`(위 Console 테스트 6줄 밖), 이미 있는 task 파일 이름과 ID, 감사 기록 형식, `TASK_ID_PATTERN`들, Worker·팀장·봇 로직, Console, AGENTS·agent 정의, validator, 다른 task 기록, 외부 API·credential, 보호 worktree |

## 계획

1. `_slugify`와 단어표 구현.
2. 검사: 한글 제목, 영문 제목(기존과 같음), 한영 혼합, 표에 없는 한글(빈 값 아님), 긴 제목(60자), 같은 제목 반복(고유 ID), 조사, 중복, 모든 결과가 ID 형식에 맞음, 실제 writer로 만든 파일의 제목이 원문 그대로.
3. 사전 점검 → self-review → candidate → Reviewer → QA → Evidence·Complete(Manager, G3와 같게) → checkpoint. push와 봇 재시작은 별도 지시.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-24 07:43 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다.

## 구현

- `orchestrator/discord-intake/task_file_writer.py`: 상수 `MAX_TASK_ID_CHARS`(60), `MAX_SLUG_CHARS`(50), `HANGUL_PATTERN`, 여러 낱말 표현 4개(`KOREAN_PHRASES`), 단어표 71개(`KOREAN_WORDS`, 작업 종류 이름 포함. 여러 낱말 표현은 붙여 쓴 표제어로 먼저 합쳐 하이픈 낱말이 한 단어로 남는다)를 더했다. `_slugify`는 한글이 없으면 기존 식 그대로, 한글이 있으면 새 `_korean_slug`로 만들고, 둘 다 새 `_cap_slug`로 50자 안에서 단어 경계에 맞춰 자른 뒤 비면 `task`를 쓴다. 번호 배정·충돌 회피·파일 내용·ID 형식은 바꾸지 않았다.
- `orchestrator/discord-intake/run_smoke_tests.py`: `_slug_cases` 14개. Owner가 든 사례(한글 제목, 영문 제목은 기존 식과 같음, 한영 혼합, 표에 없는 한글은 `task`, 긴 제목 60자, 같은 제목 반복은 고유 ID)와 조사·중복·모든 결과의 파일 이름 형식, 실제 writer로 만든 파일에 제목이 원문 그대로 있는지.
- `apps/jarvis-console/run_smoke_tests.py`(Owner 결정 2): Console 로컬 task 만들기 검사가 한글 제목의 옛 ID(`task-0001-task`, `task-0002-task`)를 기대하던 6줄을 새 ID(`task-0001-list-cleanup`, `task-0002-cleanup`)로 바꿨다. Console 코드는 바꾸지 않았다.
- `docs/task-model.md`: 1절 slug 규칙에 한 줄.
- Console 충돌 검사: Console 검사의 두 번째 제목("내일 일정 정리")은 예전에 첫 제목과 같은 slug `task`가 되어 번호 충돌 회피를 보였다. 이제 slug가 달라(`cleanup`) 그 검사는 번호가 이어지는 것만 본다. 같은 slug의 충돌 회피는 discord-intake `_slug_cases`의 같은 제목 반복 사례가 확인한다.
- 작업 종류 예비 규칙(2안): writer의 입력(title, repo, summary, source_command)에는 작업 종류가 없다. 대신 Worker task 제목에는 늘 종류 표지어가 들어 있다: `/work` 표지어 경로는 Owner 요청에 표지어가 있어야 그 종류의 task를 만들고 그 요청이 제목이 되며(`orchestrator/discord-intake/task_draft_builder.py`의 `"title": request`), 팀장 경로의 제목은 `orchestrator/worker/claude_lead.py`의 `task_title_for`가 종류의 첫 표지어로 시작하게 만든다. 표지어는 영문이거나 단어표에 있는 한글(스터디룸, 리서치 카운슬, 데일리 ai 레이더)이므로 Worker task의 slug에는 종류 이름이 늘 남는다(검사: "스터디룸 안녕하세요" → `studyroom`, "데일리 AI 레이더 안녕하세요" → `daily-ai-radar`, "리서치 카운슬 반가워요" → `research-council`). Worker task가 아닌 제목(Console 로컬 task, 수동 `/task`)에는 작업 종류가 없어서, 표의 낱말이 하나도 없으면 기존 예비값 `task`가 된다. 한계: 표지어가 제목 끝에 있고 앞 낱말만으로 50자가 차면 종류 이름이 잘릴 수 있다.

## Implementer 검증 (작업 트리)

- discord-intake smoke total=182 failed=0(새 검사 14개), Worker smoke total=595 failed=0, Discord self-check ok 109, Console smoke passed, discord-nl-intent smoke failed 0, SOP validator PASS.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "1안을 기본으로 하고, 2안을 예비 규칙으로 사용하는 방식을 추천합니다." | 한영 단어표를 기본으로 넣었다. 예비 규칙은 작업 종류 이름을 단어표에 넣는 방식이다(writer가 종류를 모르기 때문). 종류 표지어가 있는 제목은 늘 종류 이름이 남고, 아무 낱말도 없으면 기존 `task`가 된다 |
| A2 | Owner 결정 (원문) | "- 한글 단어와 조사까지 고려해 의미 있는 단어를 추출합니다." / "- 등록된 단어는 표준 영문으로 변환합니다." / "- 이미 영문인 단어는 유지합니다." / "- 의미 없는 조사나 중복 단어는 제거합니다." / "- ID 전체 길이는 약 60자로 제한합니다." | 토막 앞에서부터 가장 긴 표제어를 찾아 바꾸고 뒤의 조사·어미는 버린다. 영문·숫자는 유지하고, 같은 단어는 처음 한 번만 남기며, ID 전체를 60자 이하로 단어 경계에서 자른다 |
| A3 | Owner 결정 (원문) | "- 변환 결과가 비어 있으면 작업 종류 이름을 사용합니다." / "- 기존 ID와 감사 기록 형식은 변경하지 않습니다." / "중요한 점: 이번 개선은 ID 생성 규칙만 바꾸고, task 파일의 실제 제목과 본문은 그대로 유지해야 합니다." | 원문과 다른 점이 있다: writer는 작업 종류를 입력으로 받지 않으므로 "결과가 비면 종류 이름"을 그대로 구현하지 않았다. 대신 작업 종류가 있는 task(Worker task)의 제목에는 늘 종류 표지어가 있고 그 표지어가 단어표에 있어, 종류 이름이 결과에 늘 들어간다(구현 절의 근거와 검사). 작업 종류가 없는 task는 표의 낱말이 없으면 `task`가 된다. writer 입력에 종류를 더하는 방식은 봇 코드까지 바뀌어 이번 범위에 넣지 않았다. 이미 있는 ID, `TASK_ID_PATTERN`들, 감사 기록 형식은 바꾸지 않았다. 파일 제목·본문은 그대로이며 검사로 확인했다 |
| A4 | Owner 결정 (원문) | "- 한글 제목: 스터디룸 용어집 수정 → task-0193-studyroom-glossary-..." / "- 영문 제목: Update README → 기존 영문 ID 생성 동작 유지" / "- 한영 혼합 제목: Task Thread 용어 추가 → 영문 단어 보존 및 한글 변환" / "- 표에 없는 한글 제목: 빈 ID가 되지 않고 예비 규칙 적용" / "- 긴 제목: 60자 제한 준수" / "- 동일한 제목이 반복될 때: 기존처럼 고유한 ID 생성" | 여섯 사례를 모두 `_slug_cases`에 넣었다. 영문 제목은 기존 식과 같은 결과다. 다만 50자를 넘는 영문 slug는 60자 제한으로 이제 잘린다 |
| A5 | Owner 결정 (원문) | "제 판단으로는 팀장 출력 형식까지 바꾸는 3안은 지금 도입할 필요가 없습니다." | 팀장 코드와 답 형식은 바꾸지 않았다 |
| A6 | Owner 결정 2: Console 테스트 기대 ID 6줄 (원문) | "1. (권장) `apps/jarvis-console/run_smoke_tests.py`의 기대 ID 6줄만 이번 범위에 넣어 고칩니다. Console 코드는 바꾸지 않습니다." / "[Owner 답]" / "1번으로 진행해" | 그 테스트 파일의 기대 ID 6줄만 바꿨고 Console 코드는 그대로다. Console smoke가 통과한다 |
| A7 | Owner 결정 (원문) | "task-0192-studyroom-glossary-task-thread-term-add-1" | 숫자는 제목에 나온 순서대로 남아 실제 결과는 `studyroom-glossary-task-thread-term-1-add`다(Manager 질문의 예시와 같음). Owner의 예시는 모양을 보여 준 것으로 보고 순서를 바꾸지 않았다 |
| A8 | Owner 결정 3: 작업 종류 예비 규칙의 차이 수용 (원문) | "1. (권장) 지금 방식을 받아들입니다. Worker task는 종류 이름이 늘 남고, 종류가 없는 task는 `task`가 됩니다." / "[Owner 답]" / "1번으로 진행해" | A3의 차이를 Owner가 받아들였다. writer 입력과 봇 코드는 바꾸지 않았다 |

## Self-review

candidate 전 1회. major 1건, minor 5건.

1. (major) Owner 원문 "변환 결과가 비어 있으면 작업 종류 이름을 사용합니다"와 구현(종류 이름을 단어표에 넣고, 종류 없는 제목은 `task`)이 다르다는 지적. writer는 종류를 입력으로 받지 않는다. 그래서 Worker task 제목에 늘 표지어가 있다는 근거 파일을 구현 절에 적었고, A3에 차이를 그대로 적었다. 이 차이는 Owner에게 올렸고 Owner가 받아들였다(Owner 결정 3).
2. 예비 규칙의 근거 파일과 검사가 없었다. 근거(`task_draft_builder.py`, `claude_lead.py`의 `task_title_for`)를 적고 검사 3개(스터디룸·데일리 AI 레이더·리서치 카운슬 + 표에 없는 낱말)를 더했다.
3. 범위·설계가 `_slugify`만 바꾼다고 적었다. 새 도우미 두 개를 범위와 설계에 적었다.
4. 하이픈 낱말이 자르는 지점에서 중간에 잘릴 수 있었다. 한글 제목은 단어표 낱말 단위로 담도록 코드를 고쳤다. 이 검사를 더하다가, 여러 낱말 표현이 `research-council`로 바뀐 뒤 하이픈에서 다시 나뉘는 결함을 찾아 함께 고쳤다(붙여 쓴 표제어로 먼저 합침).
5. Console 충돌 검사의 의미가 바뀐 점을 구현 절에 적었다.
6. Owner 예시의 숫자 위치와 실제 결과가 다른 점을 A7에 적었다.
