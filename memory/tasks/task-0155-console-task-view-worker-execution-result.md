# task-0155-console-task-view-worker-execution-result

- id: `task-0155-console-task-view-worker-execution-result`
- title: `Console Task View에 Worker 실행 결과(Execution result·Execution summary) 읽기 전용 표시`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-13 08:23 UTC`
- updated_at: `2026-10-13 08:24 UTC`
- summary: `Task View가 task 기록의 실행 필드를 이미 읽고 검사하지만 화면 결과에서 빼서, Worker로 실행한 task(예: task-0143 FAILED)의 실제 결과와 실패 이유가 보이지 않는다. parse_task_view_text()에 execution(task-model 10절 규칙의 status와 execution_summary)을 더하고, 카드에 실행 결과가 있을 때만 두 줄을 읽기 전용으로 표시한다. task 기록, 데이터 모델, 상태, API 경로는 바꾸지 않고 push는 하지 않는다.`
- source_command: `Owner 승인: Task View의 Worker 실행 결과 표시 개선을 조사 결과에 따른 최소 변경 범위로 구현`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `9806a8b2b30849b01774e2a8b9bfb82bdcecfb63` (main HEAD, origin/main보다 1 commit 앞섬, push 전) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 계기 | 2026-10-11 Console 실사용 점검에서 task-0143(FAILED)의 실패 이유 `scope:repair_no_changes`와 task-0154(DONE)의 Worker 결과가 Task View에 보이지 않았다 |
| 보존 대상 | task-0143 r3 worktree/branch(`e05c69c`), task-0149 worktree/branch 2개(`8f0c58e`, r2 `bd1622e`), task-0154 worktree/branch(`80a61a8`) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` |

## 조사 결과 (read-only, 코드와 task 기록 기준)

1. 흐름: `GET /api/overview` → `project_task_view_items()` → `read_task_view_text()` → `parse_task_view_text()`
   (`apps/jarvis-console/run_web_app.py`) → 화면 `actionableTaskItemMarkup()`(`apps/jarvis-console/web/app.js`).
2. `parse_task_view_text()`는 실행 필드 8개를 허용 목록(`TASK_VIEW_OPTIONAL_*`)으로 받아 text(1–500자, 제어문자 없음),
   boolean(`true`/`false`), timestamp 형식을 검사하고, 어긋나면 metadata review로 보낸다. 그러나 반환 dict에는 실행 필드가 없다.
3. 카드 렌더러는 Status, Title, Task ID, Updated, Summary, Completion evidence, Next action, Path만 그린다.
4. task-model 10절(task 상태 영역 기준 문서): `execution_status`는 저장하지 않고 읽을 때 만든다. `executed`와 `success`가 모두
   `true`면 `success`, `executed`만 `true`면 `failed`, 그 밖에는 `not_executed`. 실행 metadata가 없는 task는 실행 구역을 보여주지 않는다.
   같은 규칙이 `adapters/discord/bot_minimal.py`의 파생 함수에도 있다.
5. 실행 필드가 있는 기록은 4건(task-0143, 0146, 0149, 0154)이고 모두 `executed`를 갖는다.
   - task-0143: `FAILED`, `executed=true`, `success=false`, `execution_summary`=`scope:repair_no_changes`
   - task-0154: `DONE`, `executed=true`, `success=true`, `execution_summary`=`worker candidate 2fe5262 passed Reviewer and QA after 0 repair(s)`
6. 관찰(이 task에서 고치지 않음): task-0143의 `execution_updated_at`(2026-09-24 16:41 UTC)은 첫 시도 시각인데 본문은 실행 metadata가
   마지막 시도(r3)의 결과라고 적는다. 그래서 `execution_updated_at`은 표시하지 않는다(Owner 승인 제외 범위).

## Owner 결정 (원문)

```text
Owner가 Task View의 Worker 실행 결과 표시 개선을 승인한다.
조사 결과에 따른 최소 변경 범위로 구현하라.
승인 범위

1. `apps/jarvis-console/run_web_app.py`
   * `parse_task_view_text()` 반환값에 `execution` 정보를 추가한다.
   * task-model §10의 규칙에 따라 `status`를 계산한다.
   * `execution` 필드가 없는 일반 task는 `null`로 처리한다.
   * 기존 검증을 통과한 데이터만 사용한다.
2. `apps/jarvis-console/web/app.js`
   * Task View 카드에서 실행 결과가 존재할 때만 `Execution result`와 `Execution summary`를 읽기 전용으로 표시한다.
   * `escapeHtml`을 사용한다.
   * 기존 버튼, 그룹, 정렬, 상태 전이, 쓰기 흐름은 변경하지 않는다.
3. `apps/jarvis-console/run_smoke_tests.py`
   * 기존 반환 키 검사와 조사 단계에서 정리한 회귀 테스트를 추가한다.
   * 일반 task, 성공, 실패, 미실행, summary 누락, 잘못된 boolean 값을 검증한다.
   * 기존 미리보기 응답 구조와 상태 전이 관련 테스트도 유지한다.
4. `apps/jarvis-console/README.md`
   * Task View에서 Worker 실행 결과를 읽기 전용으로 확인할 수 있다는 설명을 짧게 추가한다.

제외 범위

* `execution_updated_at`은 표시하지 않는다.
* task 기록, `execution_result` JSON, 데이터 모델, Discord, 새 상태, API 경로는 변경하지 않는다.
* `jarvis.bat` 및 `.git/info/exclude`는 건드리지 않는다.
* 10건 표시 제한, 탭 기본 선택, 다른 UI 불편 사항은 이번 작업에 포함하지 않는다.
* 승인되지 않은 추가 개선은 하지 않는다.

작업 절차

1. 저장소 지침과 SOP를 준수한다.
2. 정식 task 생성 및 프로젝트의 Implementer → Reviewer → QA 절차를 따른다.
3. 변경 전후 diff를 검토하고 지정한 회귀 테스트와 전체 Console smoke test, `scripts/validate_multi_agent_sop.py`, `git diff --check`를 실행한다.
4. 검증 실패가 있으면 임의로 범위를 넓히지 말고 원인과 결과를 보고한다.
5. 작업 완료 시 변경 파일, 테스트 결과, candidate/checkpoint 커밋, task 상태를 보고한다.
6. push는 하지 않는다. 완료 후 멈추고 Owner의 다음 지시를 기다린다.
```

## Manager 요약

승인 원문의 조건을 하나씩 옮긴 Manager의 해석이다. 원문과 다르면 원문이 우선한다.

| # | 승인 조건 | Manager 해석과 충족 방법 |
| --- | --- | --- |
| A1 | run_web_app.py: `parse_task_view_text()` 반환값에 `execution` 추가 | valid 반환 dict에 키 `execution` 하나를 더한다. invalid 반환(`invalid_task_view`)은 바꾸지 않는다 |
| A2 | task-model §10 규칙으로 `status` 계산 | `executed=true`·`success=true` → `success`, `executed=true`만 → `failed`, 그 밖 → `not_executed` |
| A3 | `execution` 필드가 없는 일반 task는 `null` | `executed` 줄이 없으면 `execution: None`(JSON `null`). 실행 필드가 있는 4건 모두 `executed`를 가지며 writer가 함께 기록한다 |
| A4 | 기존 검증을 통과한 데이터만 사용 | 기존 boolean·text 검사가 모두 끝난 뒤의 값만 쓴다. `execution_summary`는 기존 정규화 결과(`normalized_optional_text`)를 쓰고, 없으면 `summary: None`. `execution_result` JSON은 읽지 않는다. 새 검사나 새 실패 사유는 없다 |
| B1 | app.js: 실행 결과가 있을 때만 `Execution result`·`Execution summary`를 읽기 전용 표시 | `actionableTaskItemMarkup()`에서 `view.execution`이 있을 때만 `<dt>/<dd>` 두 줄. summary가 없으면 `Not recorded` |
| B2 | `escapeHtml` 사용 | 두 값 모두 `escapeHtml`로 출력 |
| B3 | 버튼, 그룹, 정렬, 상태 전이, 쓰기 흐름 불변 | 위 두 줄 외 렌더러·핸들러 변경 없음. 서버의 그룹·순위·next_action·전이 코드도 그대로 |
| C1 | smoke: 기존 반환 키 검사 갱신과 조사 단계 회귀 테스트 추가 | 반환 키 정확 비교 검사에 `execution` 추가. 일반 task는 `None` |
| C2 | 일반 task, 성공, 실패, 미실행, summary 누락, 잘못된 boolean 검증 | 각 경우를 `parse_task_view_text()`로 검사: 일반 → `None`, 성공 → `success`, 실패 → `failed`(task-0143 형태), 미실행(`executed=false`, dry_run) → `not_executed`, `executed`만 있고 summary 없음 → `summary None`, 잘못된 boolean(`executed`·`success`) → metadata review(`invalid_text`) |
| C3 | 미리보기 응답 구조·상태 전이 테스트 유지 | 기존 미리보기 키 검사와 전이 테스트를 바꾸지 않고 그대로 통과시킨다 |
| D1 | README: Task View에서 Worker 실행 결과를 읽기 전용으로 확인 가능하다는 짧은 설명 | Tasks / Reports 절에 짧은 문단 1개 |
| X1 | `execution_updated_at` 미표시 | 반환·화면 어디에도 넣지 않는다 |
| X2 | task 기록, `execution_result` JSON, 데이터 모델, Discord, 새 상태, API 경로 불변 | 기존 task 기록은 바꾸지 않는다(이 task 기록 추가는 정식 task 생성 절차). 새 route·상태·저장 없음 |
| X3 | `jarvis.bat`, `.git/info/exclude` 불변 | 접근하지 않는다 |
| X4 | 10건 제한, 탭 기본 선택, 다른 UI 불편 사항 제외 | 손대지 않는다 |
| X5 | 승인되지 않은 추가 개선 금지 | 위 4개 파일과 이 기록 외 변경 없음 |
| P1 | 정식 task 생성, Implementer → Reviewer → QA | 이 기록 생성 → Console Start(`TODO→DOING`) → candidate commit → Reviewer → QA |
| P2 | diff 검토, 지정 회귀 테스트, Console smoke 전체, SOP validator, `git diff --check` | 검증 계획 V1–V6 |
| P3 | 검증 실패 시 범위를 넓히지 않고 보고 | 실패하면 멈추고 보고한다. budget 안의 repair도 승인 범위 4개 파일 안에서만 |
| P4 | 완료 시 변경 파일, 테스트 결과, candidate/checkpoint commit, task 상태 보고 | 최종 보고에 포함 |
| P5 | push 금지, 완료 후 멈춤 | push하지 않는다. DONE은 SOP §8대로 Owner의 Console Complete 결정으로 남긴다 |

## File ownership

| 구분 | 경로 |
| --- | --- |
| owned (Implementer) | `apps/jarvis-console/run_web_app.py`, `apps/jarvis-console/web/app.js`, `apps/jarvis-console/run_smoke_tests.py`, `apps/jarvis-console/README.md`, 이 기록 |
| deny | `jarvis.bat`, `.git/info/exclude`, 다른 `memory/tasks/*.md`, `docs/task-model.md`, `adapters/`, `orchestrator/`, 그 밖 모든 파일 |

Docs 판정: `not_required`. README 설명은 Owner 승인 범위 4번으로 candidate에 함께 들어가 Reviewer·QA를 받으므로 QA 뒤 별도 Docs
단계가 없다.

## 검증 계획

| # | 항목 |
| --- | --- |
| V1 | 새 회귀 테스트(C2의 6가지)와 갱신한 반환 키 검사 |
| V2 | Console smoke 전체(`python -B apps/jarvis-console/run_smoke_tests.py`), self-test(`run_web_app.py --self-test`) |
| V3 | 실제 저장소 기준 overview: 실행 결과가 있는 task가 4건(0143 failed, 0146·0149·0154 success), metadata review 0건 |
| V4 | `python -B scripts/validate_multi_agent_sop.py` PASS |
| V5 | `git diff --check` exit 0, 변경 범위가 owned 파일과 같음 |
| V6 | 서버·listener·임시 파일 없음, `jarvis.bat` untracked |

## 범위 밖

- task-0143 `execution_updated_at` 불일치 원인 조사
- Worker task의 초안 summary 문구, 10건 표시 제한, 기본 탭 선택
- Discord 파생 함수와의 공통화
- commit 외 DONE 처리, push, `jarvis.bat`

## 구현 착수

2026-10-13 08:24 UTC에 Jarvis Console Start(Preview + Confirm, `START TASK`)로 `TODO→DOING`을 적용했다(Console 결과
`result_type: updated`, `TODO → DOING`, `no_execution: true`). 서버는 `--no-browser`로 띄운 뒤 소유 PID만 종료했다.

## 구현 (Implementer)

baseline `9806a8b2b30849b01774e2a8b9bfb82bdcecfb63`. 이 기록과 함께 candidate commit에 넣는다.

| 파일 | 변경 |
| --- | --- |
| `apps/jarvis-console/run_web_app.py` | `parse_task_view_text()`: 기존 boolean·text·timestamp 검사가 끝난 뒤 `executed` 줄이 있으면 `execution = {"status", "summary"}`를 만든다(A2 규칙, summary는 `normalized_optional_text`의 `execution_summary` 또는 `None`). 없으면 `None`. valid 반환 dict에 `"execution"` 키 1개 추가. invalid 반환, 그룹·순위·next_action, 전이 코드는 그대로 |
| `apps/jarvis-console/web/app.js` | `actionableTaskItemMarkup()`: `valid && view.execution`일 때만 `Execution result`(`escapeHtml(view.execution.status \|\| "")`)와 `Execution summary`(`escapeHtml(view.execution.summary \|\| "Not recorded")`) 두 줄. 그 밖 변경 없음 |
| `apps/jarvis-console/run_smoke_tests.py` | (1) 반환 키 정확 비교에 `execution` 추가, 일반 task `execution is None`. (2) 실행 사례 7개: 성공, 실패(task-0143 형태), 미실행(`executed=false`+dry_run), 미실행+`success=true`, `executed`만 있음, summary 누락, `executed` 없이 summary만 있음(`None`). 각 사례에서 그룹·순위 불변과 `execution_updated_at` 미노출 확인. (3) 잘못된 boolean 4개(`executed`=`True`·`1`·빈 값, `success`=`yes`)는 metadata review `invalid_text`이고 `execution` 키 없음. (4) node 렌더러 harness: 실행 정보가 없으면 두 줄 없음, 있으면 escape된 두 줄만 추가되고 badge·버튼 등 나머지 markup 동일, summary `null`은 `Not recorded`, metadata review는 실행 줄 없음. escape 계약 목록에 두 표현 추가, 렌더러에 `execution_updated_at` 없음 확인. (5) 기존 검사 하나 조정: 실행 metadata를 넣은 view가 일반 view와 완전히 같다는 `optional_view == plain_view`는 이 task가 바꾸려는 이전 동작 그 자체라, `execution` 키를 뺀 나머지가 같고 `execution`이 `{"status": "failed", "summary": "summary"}`인지로 바꿨다. 원시 실행 필드 이름이 view에 없다는 바로 아래 검사, `execution_candidate`만 있는 view·`execution_updated_at`만 있는 view가 일반 view와 같다는 검사는 그대로다 |
| `apps/jarvis-console/README.md` | Tasks / Reports 절에 실행 결과 읽기 전용 표시 문단 1개 |

규모: 4개 파일 207 추가, 2 삭제(이 기록 제외). 미리보기 응답 키 검사와 상태 전이 테스트는 바꾸지 않았다.

## 검증 (Implementer 실행)

| # | 항목 | 결과 |
| --- | --- | --- |
| V1 | 새 회귀 테스트와 반환 키 검사 | Console smoke 안에서 PASS |
| V2 | Console smoke 전체, `run_web_app.py --self-test` | 둘 다 PASS |
| V3 | 실제 저장소 기준 | task 기록 107개 모두 valid(metadata review 0). 실행 결과: task-0143 `failed`/`scope:repair_no_changes`, task-0146·0149·0154 `success`. `/api/overview` 200, 표시 10건 중 task-0143 `failed`, task-0154 `success`, 나머지 `null` |
| V4 | SOP validator | PASS, negative_checks=129, negative_failures=0 |
| V5 | `git diff --check`, 범위 | exit 0. 변경은 owned 4개 파일과 이 기록 |
| V6 | 강도 확인(임시 worktree에서 변경을 하나씩 넣어 Console smoke 실행) | 변경 없는 사본 PASS. `executed`만일 때 `not_executed`로 계산, 일반 task에 non-null execution, summary escape 제거, metadata review에도 실행 줄 표시, 실행 줄 옆에 다른 markup 추가는 모두 FAIL. 임시 worktree 삭제 |
| V7 | 정리 | 서버·listener 없음, 보존 worktree 4개 그대로, `jarvis.bat` untracked |

정리 메모: V6 스크립트의 잘못된 복사 한 줄이 `C:\Program Files\Git\tmp_rw.py`(수정한 `run_web_app.py` 사본)를 저장소 밖에 만들었다.
삭제 명령은 Claude Code 안전 검사에 막혀 실행하지 않았고 Owner에게 보고한다.
