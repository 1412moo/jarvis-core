# task-0205-console-read-only-report-view

- id: `task-0205-console-read-only-report-view`
- title: `Task View에서 읽기 전용 보고 전문 보기`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-28 12:36 UTC`
- updated_at: `2026-10-28 14:00 UTC`
- summary: `task-0201 읽기 전용 확인·보고 task의 Worker 답 전문은 저장소 밖 보고 파일에만 있고 Console Task View에는 글자 수만 보인다. Console이 그 task의 보고 파일을 길이 제한을 두고 읽기 전용으로 읽어 카드에서 펼쳐 볼 수 있게 하고, 검증 안 된 Worker 답(Reviewer·QA 없음)이라고 표시하며, 파일이 없거나 읽지 못하면 그 상태를 보인다. 새 route·쓰기·저장은 없다.`
- source_command: `Owner 지시: Console 다음 작업 A안 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `56b8038dd650345e993c517999d7281afa15ac13` (등록 시점 main HEAD, origin/main과 같음) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=3`, `repair_count=3` (SOP §5 기본값 1에서 Owner가 두 번 +1. repair 1~3은 아래 Reviewer·repair 절) |

## Owner 결정 (원문)

```text
[Manager 제안: Console 다음 작업 후보]
**A. Task View에서 읽기 전용 보고 전문 보기 (추천)**
- **문제:** task-0201 이후 읽기 전용 확인 작업의 실제 답은 저장소 밖 파일(`%LOCALAPPDATA%\jarvis-core\reports\<task-id>.md`)에만 있습니다. Console 카드에는 "read-only report of 1163 chars"라는 글자 수만 나옵니다. 예를 들어 task-0202는 DONE인데 결과를 Console에서 읽을 수 없습니다.
- **변경:** 그 task의 보고 파일을 길이 제한을 두고 읽기 전용으로 읽어 카드에 펼쳐 보이게 합니다. "검증 안 된 Worker 답(Reviewer·QA 없음)"이라는 표시를 붙이고, 파일이 없거나 읽지 못하면 그 상태를 그대로 보여 줍니다.
- **승인이 필요한 점:** Console이 처음으로 저장소 밖 파일을 읽게 됩니다. 쓰기는 하지 않습니다.
- **규모:** 작음~중간. `run_web_app.py`, `app.js`, smoke test, README/SOP 한 문단 정도입니다.
A나 B를 고르시면 저장소 밖 파일을 읽기 전용으로 여는 것에 대한 승인도 함께 받아야 합니다.

[Owner 답]
A로 진행
```

## Owner 결정 (원문, Reviewer 지적 뒤 bounded question)

```text
[Manager 질문 1]
Console이 저장소 밖 보고 폴더(%LOCALAPPDATA%\jarvis-core\reports)를 읽기 전용으로 읽는 것을 승인하시나요? (쓰기·삭제 없음, 저장소 안을 가리키면 읽지 않음)

[Owner 답 1]
승인 (Recommended)

[Manager 질문 2]
보고 표시 문구를 어떻게 할까요?

[Owner 답 2]
한국어로 변경
```

## Owner 결정 (원문, repair 예산 소진 뒤 escalation)

```text
[Manager 질문]
Reviewer minor 지적(보고 폴더가 JARVIS_REPORT_DIR·홈 폴더 대체 규칙으로 바뀔 수 있음)을 어떻게 처리할까요?

[Owner 답]
예산 +1, 폴더 고정
```

선택지 설명(Manager가 질문과 함께 보인 문구, Owner 원문 아님): "repair 예산을 1 늘리고 Console이 %LOCALAPPDATA%\jarvis-core\reports만 읽도록 고칩니다. 새 candidate에 Reviewer→QA를 다시 합니다."

## Owner 결정 (원문, 두 번째 escalation)

```text
[Manager 질문]
A3 행 문구(폴더 규칙 설명이 고정 뒤 내용과 어긋남) minor 지적을 어떻게 처리할까요?

[Owner 답]
예산 +1, A3 수정 (Recommended)
```

선택지 설명(Manager가 질문과 함께 보인 문구, Owner 원문 아님): "repair 예산을 1 늘려 기록의 A3 문구만 고치고, 새 candidate에 Reviewer→QA를 다시 합니다. 코드는 그대로입니다."

## 조사 (등록 전)

- Worker(`orchestrator/worker/claude_worker.py`)는 읽기 전용 실행이 성공 경로에 들어설 때만 답 전문을 `REPORT_DIR / f"{name}.md"`에 쓴다. `REPORT_DIR`은 `JARVIS_REPORT_DIR`, 없으면 `%LOCALAPPDATA%`(없으면 홈) 아래 `jarvis-core/reports`이고, `name`은 attempt 이름(첫 시도 `<task-id>`, 그다음 `<task-id>-r<N>`)이다. 같은 실행의 task 결과 기록은 `execution_summary`를 `read-only report of <N> chars, no files changed`로 남긴다.
- Console `parse_task_view_text()`는 파일을 읽지 않는 순수 함수이고, `project_task_view_items()`가 task 기록을 읽어 투영한다. 카드의 실행 결과 두 줄은 task-0155가 더했다.
- 현재 보고 폴더에는 `task-0202-studyroom-glossary-owner-accept-term-task-0154.md` 하나가 있다(task-0202 DONE).
- Console 잠금 목록(`owner_decision_data.py`)의 jarvis-console 항목은 "New route or persistence"를 잠근다. 이 task는 route와 저장을 더하지 않고 기존 `/api/overview` 응답의 task 항목에 읽기 전용 필드를 더한다(task-0155·0162와 같은 방식).

## 설계

1. 대상: Task View 투영의 유효한 task 중 실행 결과가 `success`이고 `execution_summary`가 Worker가 쓰는 형식 `read-only report of <N> chars, no files changed`와 정확히 같은 task만. 그 밖의 task에는 새 필드가 없다.
2. 보고 폴더: Owner가 승인한 `%LOCALAPPDATA%\jarvis-core\reports` 하나만 읽는다(repair 2). Worker의 `JARVIS_REPORT_DIR` 변경과 홈 폴더 대체는 따르지 않으므로 그곳에 쓴 보고는 `missing`으로 보인다. `LOCALAPPDATA`가 없거나 비어 있으면 어떤 폴더도 읽지 않고 `unavailable`이다. 해석한 폴더가 저장소 안이면 읽지 않고 `unavailable`로 본다(fail closed).
3. 파일 선택: 폴더에서 이름이 정확히 `<task-id>.md` 또는 `<task-id>-r<N>.md`(N ≥ 2, 앞자리 0 없음)인 일반 파일만 후보로 본다. 심볼릭 링크, 폴더, 다른 task 기록과 이름이 같은 파일은 후보가 아니다. attempt 번호만으로는 어느 실행의 파일인지 알 수 없으므로(self-review 1), 후보 중 기록된 `<N> chars`에 맞는 파일 하나만 보인다. Worker는 답과 줄바꿈 하나를 쓰고(Windows에서는 CRLF) 답의 길이를 기록하므로, CRLF를 LF로 바꾼 본문이 N+1자이고 줄바꿈으로 끝나면 맞는다. 잘린 파일은 앞부분만 읽으므로 읽은 길이가 N+1보다 짧을 때만 맞는다. 맞는 파일이 없으면 `mismatch`, 둘 이상이면 `ambiguous`다.
4. 읽기: 후보마다 앞에서부터 정해진 바이트 수까지만 읽고, 엄격한 UTF-8로 해독한다(잘린 끝의 덜 끝난 문자만 버림). 보이는 본문은 줄끝을 LF로 바꾸고 NFC로 정규화하며, 줄바꿈·탭 밖의 제어·형식 문자(Cc·Cf·Cs)를 지우고 Zl·Zp는 줄바꿈으로 바꾼다. 잘렸으면 그 사실을 표시한다. 목록·열기·해독 실패는 `unreadable`, 후보가 없으면 `missing`이다.
5. 응답: task 항목에 `worker_report`(상태, 파일 이름, 본문, 잘림 여부, "검증 안 된 Worker 답" 표지, `read_only: true`)를 더한다. 파일의 전체 경로는 응답에 넣지 않는다.
6. 화면: 카드에 "Read-only report" 줄을 더하고, 본문은 기본으로 접힌 `<details>`에 escape해 `<pre>`로 보인다. "검증 안 된 Worker 답(Reviewer·QA 없음)" 표지(repair 1부터, Owner 결정)를 늘 함께 보인다. `missing`·`unreadable`·`unavailable`·`mismatch`·`ambiguous`는 그 상태 문구만 보인다. 버튼·상태 전이·정렬·그룹·쓰기 흐름은 바꾸지 않는다.
7. 문서: Console README에 한 문단. SOP는 바꾸지 않는다(Manager 해석: 제안의 "README/SOP 한 문단"은 문서 한 문단의 규모를 말한 것으로 보고, Console 화면 설명이 있는 README에 둔다. SOP §10.1의 보고 파일 설명은 이 변경 뒤에도 사실이다).

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `apps/jarvis-console/run_web_app.py`, `apps/jarvis-console/web/app.js`, `apps/jarvis-console/web/styles.css`, `apps/jarvis-console/run_smoke_tests.py`, `apps/jarvis-console/README.md`, `memory/tasks/task-0205-console-read-only-report-view.md` |
| deny | `jarvis.bat`, 보고 폴더와 그 안 파일에 쓰기·지우기, Worker·Discord 코드(`orchestrator/`), task 기록 스키마·writer, 새 route·저장, SOP·AGENTS·agent 정의·validator, 다른 task 기록(task-0200 포함), 외부 API·credential, push |

## 계획

1. Console Start(TODO → DOING).
2. 구현: 서버 보고 읽기와 투영 필드, 카드 표시, smoke test, README.
3. 검사: Console smoke 전체, 새 경우(대상 아님·있음·r2 우선·없음·읽기 실패·UTF-8 깨짐·잘림·제어 문자·저장소 안 폴더·심볼릭 링크·이름 불일치)와 escape된 화면, SOP validator, 실제 브라우저에서 task-0202 카드.
4. 사전 점검 → self-review → candidate(`commit_candidate.py --require-quotes`) → Reviewer → QA → Owner Complete 결정 → checkpoint → master-plan. push는 별도 지시.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다(status 줄만 바뀜, updated_at `2026-10-28 12:36 UTC`). Console은 Start 뒤 껐다.

## 구현

- `apps/jarvis-console/run_web_app.py`: `codecs` import. 상수 `TASK_REPORT_SUMMARY_PATTERN`(Worker가 남기는 `execution_summary` 형식 그대로), `TASK_REPORT_MAX_BYTES`(64 KiB), `TASK_REPORT_LABEL`("검증 안 된 Worker 답(Reviewer·QA 없음)", repair 1에서 영어 문구를 바꿈), `TASK_REPORT_DROPPED_CATEGORIES`. 함수 `task_report_dir()`(`%LOCALAPPDATA%\jarvis-core\reports`만, `LOCALAPPDATA`가 없으면 None. 호출 때 환경 변수를 읽음. repair 2), `task_report_chars()`(유효한 task, 실행 결과 success, summary가 형식과 정확히 같으면 기록된 글자 수, 아니면 None), `clean_task_report_text()`(설계 4의 본문 정리), `read_task_report(task_id, expected_chars)`(설계 2~5. 폴더가 저장소 안이면 `unavailable`, 폴더·후보가 없으면 `missing`, 목록·열기·해독 실패는 `unreadable`, 후보마다 64 KiB까지 읽고 기록된 길이에 맞는 파일 하나만 `available`, 없으면 `mismatch`, 둘 이상이면 `ambiguous`). `project_task_view_items()`에 선택 인자 `report_reader`를 더하고 대상 task 항목에만 `worker_report`를 붙인다. `parse_task_view_text()`와 정렬·그룹·counts·쓰기 흐름은 그대로다.
- `apps/jarvis-console/web/app.js`: `workerReportStateText`(상태 문구 다섯)와 `workerReportMarkup()`. 카드의 실행 결과 두 줄 뒤에 `item.worker_report`가 있을 때만 "Read-only report" 줄을 더한다. `available`이면 접힌 `<details class="worker-report">`(summary에 표지와 파일 이름, 잘렸으면 안내 한 줄, 본문은 escape한 `<pre>`), 그 밖의 상태는 상태 문구 한 줄. fetch·버튼은 더하지 않았다.
- `apps/jarvis-console/web/styles.css`: `.worker-report pre` 한 규칙(줄바꿈 유지, 긴 줄 감싸기, 최대 높이 360px와 스크롤). Manager 해석: 제안의 파일 목록은 "정도"로 적은 규모이고, 카드 안에서 긴 답을 읽을 수 있게 하는 표시 규칙 하나라 같은 화면 변경으로 보고 owned에 더했다.
- `apps/jarvis-console/run_smoke_tests.py`: `_test_task_report_view()`를 `main()` 맨 앞에 더했다.
- `apps/jarvis-console/README.md`: Task View 실행 결과 문단 뒤에 한 문단.

## Implementer 검증 (작업 트리)

- `python -B apps/jarvis-console/run_smoke_tests.py`(PYTHONUTF8 없이) 통과. 새 테스트가 확인하는 것: 대상 판정 8경우와 기록된 글자 수, 폴더 규칙 3단계, 없음(빈 폴더·없는 폴더), Worker가 Windows에서 쓰는 모양(CRLF)의 파일과 본문 정리(BEL·U+202E 제거, 탭 유지, 한국어), 응답에 전체 경로 없음, 길이가 하나라도 다르거나 끝 줄바꿈이 없으면 `mismatch`(본문·파일 이름 없음), LF 파일도 맞음, 후보 선택(맞는 파일 하나만, 같은 길이 둘이면 `ambiguous`, `-r1`·`-r02`·다른 확장자·폴더는 길이가 맞아도 무시, 다른 task 기록과 같은 이름 건너뜀, 심볼릭 링크는 만들 수 있을 때만), 읽은 뒤 폴더의 파일 이름·크기·mtime 그대로, 깨진 UTF-8은 `unreadable`(본문 없음), 64 KiB 경계의 잘림(덜 끝난 한글 한 글자만 빠짐, 기록 길이가 읽은 것보다 짧으면 `mismatch`)과 정확히 64 KiB는 안 잘림, 목록 실패는 `unreadable`, 저장소 루트와 그 아래 폴더는 `unavailable`, 투영에서 성공한 보고 task만 `worker_report`를 받고 reader가 그 task와 기록된 글자 수로만 불림, 화면 harness(escape, 접힘, 표지와 파일 이름, 잘림 안내, 다섯 상태 문구, 일반 task·metadata review에는 줄 없음, 보고 줄 밖 카드 마크업 그대로).
- self-review 반영 뒤 실제 보고 폴더에서 `read_task_report`를 직접 불렀다: task-0202를 기록된 1163으로 읽으면 `available`(본문 1164자, 안 잘림), 1162로 읽으면 `mismatch`.
- SOP validator PASS, `git diff --check` 통과.
- 실제 브라우저(Console 127.0.0.1:8790, 실제 보고 폴더): task-0202 카드에 "Read-only report" 줄과 "Unverified Worker answer (no Reviewer or QA): task-0202-studyroom-glossary-owner-accept-term-task-0154.md"(candidate `ab1d0e3`의 영어 표지, repair 1에서 바뀜)가 보이고, 펼치면 답 전문(1164자, 파일 끝 줄바꿈 포함)이 보였다. `/api/overview`에서 `worker_report`가 있는 task는 task-0202 하나(`available`)였고, 응답 JSON과 페이지 HTML에 `AppData`가 없었다. 콘솔 오류 없음. 서버는 확인 뒤 껐다.
- Manager 확인(A8 관련): `apps/jarvis-console/run_web_app.py`에서 `LOCALAPPDATA`·홈 폴더를 쓰는 다른 읽기 경로는 찾지 못했다(grep). 같은 저장소의 Hermes 앱(`apps/hermes-manager-pilot`)은 자체 저장소 밖 상태 폴더를 쓰지만 Console이 아니다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 제안: Console 다음 작업 후보]" | 제안의 표지. 해석할 조건이 아니다 |
| A2 | Owner 결정 (원문) | "Task View에서 읽기 전용 보고 전문 보기 (추천)**" | 이 task의 범위. Task View 카드에 보고 전문을 보인다 |
| A3 | Owner 결정 (원문) | "**문제:** task-0201 이후 읽기 전용 확인 작업의 실제 답은 저장소 밖 파일(`%LOCALAPPDATA%\jarvis-core\reports\<task-id>.md`)에만 있습니다." | 읽는 곳은 Owner가 승인한 `%LOCALAPPDATA%\jarvis-core\reports` 하나다(B4·C4, repair 3에서 고침). Worker의 폴더 규칙(`JARVIS_REPORT_DIR`, 홈 대체)은 따르지 않는다. 파일 이름은 Worker의 attempt 이름(`<task-id>.md`, `<task-id>-r<N>.md`)이다. Manager 해석: "그 task의 보고 파일"은 task에 기록된 실행의 답이므로, attempt 번호가 아니라 기록된 글자 수에 맞는 파일 하나만 보인다(설계 3) |
| A4 | Owner 결정 (원문) | "Console 카드에는 "read-only report of 1163 chars"라는 글자 수만 나옵니다." | 대상 판정은 이 `execution_summary` 형식과 정확히 같고 실행 결과가 success인 유효한 task다. 기존 두 줄은 그대로 둔다 |
| A5 | Owner 결정 (원문) | "예를 들어 task-0202는 DONE인데 결과를 Console에서 읽을 수 없습니다." | 실제 브라우저에서 task-0202 카드로 확인했다(Implementer 검증) |
| A6 | Owner 결정 (원문) | "**변경:** 그 task의 보고 파일을 길이 제한을 두고 읽기 전용으로 읽어 카드에 펼쳐 보이게 합니다." | 64 KiB까지 읽고 잘렸으면 안내한다. 카드에서 접힌 `<details>`로 펼쳐 본다. 읽기만 하고 폴더는 그대로다(테스트) |
| A7 | Owner 결정 (원문) | ""검증 안 된 Worker 답(Reviewer·QA 없음)"이라는 표시를 붙이고, 파일이 없거나 읽지 못하면 그 상태를 그대로 보여 줍니다." | 화면 표지는 원문 그대로 "검증 안 된 Worker 답(Reviewer·QA 없음)"이다(repair 1, 아래 B8). 없음·읽기 실패는 "Report file not found"·"Report file could not be read", 저장소 안 폴더는 "Report folder unavailable", 기록된 실행과 맞는 파일이 없거나 여럿이면 "No report file matches the recorded run"·"Several report files match the recorded run"으로 보인다. 본문에서 제어·형식 문자를 지우고 정규화하는 것은 화면 안전을 위한 Manager 판단이다(설계 4) |
| A8 | Owner 결정 (원문) | "**승인이 필요한 점:** Console이 처음으로 저장소 밖 파일을 읽게 됩니다." | 저장소 밖 읽기는 이 보고 폴더 하나로 한정했다. 해석한 폴더가 저장소 안이면 읽지 않는다(fail closed). 응답과 화면에 전체 경로를 넣지 않는다 |
| A9 | Owner 결정 (원문) | "쓰기는 하지 않습니다." | 보고 폴더에 쓰기·만들기·지우기가 없다. 새 route·저장도 없다 |
| A10 | Owner 결정 (원문) | "**규모:** 작음~중간." | 변경 파일 5개와 이 기록 |
| A11 | Owner 결정 (원문) | "`run_web_app.py`, `app.js`, smoke test, README/SOP 한 문단 정도입니다." | 네 곳을 바꿨고 문서는 README 한 문단이다(SOP는 그대로, 설계 7). `styles.css` 한 규칙을 더한 것은 구현 절의 Manager 해석이다 |
| A12 | Owner 결정 (원문) | "A나 B를 고르시면 저장소 밖 파일을 읽기 전용으로 여는 것에 대한 승인도 함께 받아야 합니다." | 이 승인은 Reviewer 지적(major) 뒤 따로 받았다. 아래 B2의 질문에 대한 B4의 Owner 답이 그 승인이다 |
| A13 | Owner 결정 (원문) | "[Owner 답]" | Owner 답의 표지. 해석할 조건이 아니다 |
| A14 | Owner 결정 (원문) | "A로 진행" | A안으로 이 task를 등록하고 SOP 흐름으로 진행한다 |
| B1 | Owner 결정 (원문, Reviewer 지적 뒤 bounded question) | "[Manager 질문 1]" | 질문의 표지. 해석할 조건이 아니다 |
| B2 | Owner 결정 (원문, Reviewer 지적 뒤 bounded question) | "Console이 저장소 밖 보고 폴더(%LOCALAPPDATA%\jarvis-core\reports)를 읽기 전용으로 읽는 것을 승인하시나요? (쓰기·삭제 없음, 저장소 안을 가리키면 읽지 않음)" | 아래 답으로 승인됐다. repair 2부터 Console은 질문에 적은 그 폴더 하나만 읽는다(C3·C4). 읽기만 하고(A9), 저장소 안이면 읽지 않는다(A8) |
| B3 | Owner 결정 (원문, Reviewer 지적 뒤 bounded question) | "[Owner 답 1]" | 답의 표지 |
| B4 | Owner 결정 (원문, Reviewer 지적 뒤 bounded question) | "승인 (Recommended)" | 보고 폴더 읽기 전용 접근 승인. A12의 조건을 채운다 |
| B5 | Owner 결정 (원문, Reviewer 지적 뒤 bounded question) | "[Manager 질문 2]" | 질문의 표지 |
| B6 | Owner 결정 (원문, Reviewer 지적 뒤 bounded question) | "보고 표시 문구를 어떻게 할까요?" | 선택지는 영어 유지와 한국어 변경이었다 |
| B7 | Owner 결정 (원문, Reviewer 지적 뒤 bounded question) | "[Owner 답 2]" | 답의 표지 |
| B8 | Owner 결정 (원문, Reviewer 지적 뒤 bounded question) | "한국어로 변경" | `TASK_REPORT_LABEL`을 "검증 안 된 Worker 답(Reviewer·QA 없음)"으로 바꿨다(repair 1). 상태 문구 다섯과 "Read-only report" 줄 이름은 질문 대상이 아니어서 영어 그대로다(Manager 해석) |
| C1 | Owner 결정 (원문, repair 예산 소진 뒤 escalation) | "[Manager 질문]" | 질문의 표지 |
| C2 | Owner 결정 (원문, repair 예산 소진 뒤 escalation) | "Reviewer minor 지적(보고 폴더가 JARVIS_REPORT_DIR·홈 폴더 대체 규칙으로 바뀔 수 있음)을 어떻게 처리할까요?" | 두 번째 Reviewer의 minor 지적. 선택지는 §8 수용과 예산 +1·폴더 고정이었다 |
| C3 | Owner 결정 (원문, repair 예산 소진 뒤 escalation) | "[Owner 답]" | 답의 표지 |
| C4 | Owner 결정 (원문, repair 예산 소진 뒤 escalation) | "예산 +1, 폴더 고정" | `repair_budget` 1→2. repair 2로 `task_report_dir()`을 `%LOCALAPPDATA%\jarvis-core\reports`만으로 고정했다(`JARVIS_REPORT_DIR`·홈 대체 없음, `LOCALAPPDATA`가 없으면 `unavailable`). 테스트와 README, 설계 2, 구현 절, B2를 고쳤다 |
| D1 | Owner 결정 (원문, 두 번째 escalation) | "[Manager 질문]" | 질문의 표지 |
| D2 | Owner 결정 (원문, 두 번째 escalation) | "A3 행 문구(폴더 규칙 설명이 고정 뒤 내용과 어긋남) minor 지적을 어떻게 처리할까요?" | 세 번째 Reviewer의 minor 지적. 선택지는 예산 +1·A3 수정과 §8 수용이었다 |
| D3 | Owner 결정 (원문, 두 번째 escalation) | "[Owner 답]" | 답의 표지 |
| D4 | Owner 결정 (원문, 두 번째 escalation) | "예산 +1, A3 수정 (Recommended)" | `repair_budget` 2→3. repair 3으로 A3의 해석 칸만 고쳤다. 코드·테스트·README는 그대로다 |

## Self-review

candidate 전 1회(사전 점검 `--require-quotes` PASS, staged 6, 위반 0, 미인용 0 뒤). 지적 2건을 반영했다.

1. major: 코드·README·설계 3·A3가 "가장 큰 attempt 번호의 파일이 마지막 실행의 답"이라고 적었지만 Worker는 이를 보장하지 않는다(보고 파일 쓰기에 실패해도 실행은 성공하고, worktree가 지워지면 번호가 다시 시작할 수 있음). 지적의 첫 번째 교정을 택해, 후보마다 기록된 `<N> chars`와 길이를 비교하고 맞는 파일 하나만 보이게 고쳤다(없으면 `mismatch`, 둘 이상이면 `ambiguous`, 상태 문구 둘 추가, 테스트 추가). 설계 3·4·6, 구현 절, A3, README를 같이 고쳤다.
2. minor: 설계 4와 README가 본문 정리를 제어 문자 삭제만으로 적었다. 코드대로(줄끝 LF, NFC, Cc·Cf·Cs 삭제, Zl·Zp는 줄바꿈) 설계 4와 README에 적었다.

- 처음 고칠 때 스크립트로 `run_web_app.py`를 한 번에 바꾸다 이스케이프가 깨져, 그 파일을 staged 판으로 되돌린 뒤 Edit로 다시 고쳤다(candidate 전, 결과는 위와 같음).
- self-review 사용량(API 환산 추정): 약 $0.52, 73초.

## Reviewer·repair

- candidate `ab1d0e34b0c5043bb8b41b5ec8235e6c6cf2fe19`: Reviewer FINDINGS(self_deviations 0).
  1. major: 승인 원문은 저장소 밖 읽기 승인을 "함께 받아야 합니다"라고 적었는데 Owner 답은 "A로 진행"뿐이고 A12는 Manager 해석이었다(권한 확대는 즉시 escalation gate). 교정: Owner 승인을 원문으로 받아 A12에 인용.
  2. minor: 원문이 인용한 표지 "검증 안 된 Worker 답(Reviewer·QA 없음)" 대신 영어 문구를 썼다. 교정: 원문 문구로 보이거나 Owner 수용을 기록.
  - unverified(QA로 넘김): smoke 통과, validator PASS, 실제 브라우저의 task-0202 카드와 경로 없음, 실제 폴더를 읽은 뒤 그대로, Console의 다른 저장소 밖 읽기 경로 없음.
- Manager → Owner bounded question 두 개를 묻고 답을 위 "Owner 결정 (원문, Reviewer 지적 뒤 bounded question)"에 원문 그대로 남겼다(B1~B8). Owner는 보고 폴더 읽기 전용 접근을 승인했고 표지를 한국어로 바꾸기로 했다.
- repair 1(`repair_count` 0→1, 예산 안, 커밋 두 개: `b371d1c`와 A12 행 번호를 바로잡은 다음 커밋. 새 Reviewer는 마지막 커밋에 한 번): `TASK_REPORT_LABEL`을 원문 문구로 바꾸고, smoke의 세 기대값(Python 결과 사전, JS harness 입력과 summary)과 README 문단을 맞췄다. 설계 6, 구현 절, A7, A12를 고쳤다. smoke(PYTHONUTF8 없이) 통과. 이 repair로 앞 Reviewer 결과는 무효이며 새 candidate에 Reviewer → QA를 다시 한다.
- candidate `0a4baee0e906b5a18d5222b49230f451afa7bc63`: Reviewer FINDINGS(minor 1, self_deviations 0). 승인 질문은 `%LOCALAPPDATA%\jarvis-core\reports` 하나를 적었는데 `task_report_dir()`은 `JARVIS_REPORT_DIR`와 홈 폴더 대체를 따르고, B2는 이를 "질문에 적은 대로"라고 적었다. unverified(QA로 넘김): smoke, validator, repair 1 뒤 실제 브라우저(한국어 표지), 실제 폴더를 읽은 뒤 그대로, 다른 저장소 밖 읽기 경로 없음.
- repair 예산(1)이 소진돼 Manager → Owner로 escalation했고, Owner가 "예산 +1, 폴더 고정"을 골랐다(C1~C4).
- repair 2(`repair_count` 1→2, `repair_budget` 2): `task_report_dir()`을 승인된 폴더 하나로 고정하고 `LOCALAPPDATA`가 없으면 `read_task_report`가 `unavailable`을 돌려주게 했다. smoke의 폴더 규칙 검사를 바꾸고(`JARVIS_REPORT_DIR`가 있어도 무시, `LOCALAPPDATA`가 없거나 비면 None·`unavailable`), README·설계 2·구현 절·B2를 고쳤다. smoke(PYTHONUTF8 없이) 통과. 이 repair로 앞 Reviewer 결과는 무효이며 새 candidate에 Reviewer → QA를 다시 한다. 예산은 다시 소진됐다.
- candidate `b10b208595543d725abd0d9ad3edfd341d96f5bc`: Reviewer FINDINGS(minor 1). A3의 해석이 아직 "Worker와 같은 규칙의 보고 폴더"라고 적어 B2·C4와 어긋났다. 같은 보고에 self_deviations 1건(첫 명령에 `cd`·리디렉션·명령 연결을 붙임)이 있어 그 검토는 SOP §5에 따라 무효다. retry로 재검토하는 대신, 지적 자체가 사실이라 repair 예산 소진으로 Manager → Owner escalation을 했다. Owner가 "예산 +1, A3 수정 (Recommended)"을 골랐다(D1~D4).
- repair 3(`repair_count` 2→3, `repair_budget` 3): A3의 해석 칸을 승인된 폴더 하나로 고쳤다. 같은 옛 설명이 남은 곳을 기록·README·코드·테스트에서 찾았고 A3 밖에는 없었다. 이 repair로 앞 Reviewer 결과는 무효이며 새 candidate에 Reviewer → QA를 다시 한다. 예산은 다시 소진됐다. `retry_count`는 0 그대로다(무효 검토를 retry로 재실행하지 않음).
