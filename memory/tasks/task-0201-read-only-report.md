# task-0201-read-only-report

- id: `task-0201-read-only-report`
- title: `읽기 전용 확인·보고 작업`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-10-27 10:55 UTC`
- updated_at: `2026-10-27 11:43 UTC`
- summary: `Discord /work 요청에 정해진 읽기 전용 문구(수정하지 마, 수정 금지, 보고만, 확인만, 읽기 전용 등)가 있으면 읽기 전용 확인·보고 작업으로 만든다. /go 뒤 Worker는 Read·Grep·Glob만으로 임시 worktree에서 답하고, 답을 검증 안 된 Worker 답으로 채널에 보고한다. 파일이 바뀌면 실패, 바뀐 파일이 없어도 성공이다. 긴 답은 잘라 보내고 전문은 저장소 밖 파일에 둔다. Reviewer·QA·main 반영은 없고 task 기록만 checkpoint한다. SOP 경량화 파일럿 측정 대상 3/3이다.`
- completion_evidence: `candidate c0626d978f6a9130918032d4d82537c6dbd88b20 (baseline f3bd53b, repair 1 after Reviewer minors 3). Reviewer PASS, findings 0, self_deviations 0. QA PASS 30/30 in a fresh worktree: 6 scope files, only the stated definitions; SOP edits inside 10.1; plan mode with Read,Grep,Glob only, edits and Bash disallowed, no MCP; replies fit one message, never ping, name the file; smoke 642/0 and self-check 109 leave the real reports and usage log untouched.`
- source_command: `Owner 지시: 읽기 전용 확인·보고 작업 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `f3bd53b55d24e4ee5921a36acf97297bb13680e7` (등록 시점 main HEAD, task-0199까지 push 완료) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=1` (SOP §5 기본값. Reviewer 1차 minor 3건 repair) |
| 파일럿 | SOP 경량화 파일럿(task-0197) 측정 대상 3/3. 요약 표는 `check_summary_quotes.py --emit-table`, candidate는 `commit_candidate.py --require-quotes`로 만든다 |

## Owner 결정 (원문)

```text
[Manager 추천]
1. 읽기 전용 "확인·보고" 작업 종류 추가 (추천, 파일럿 3/3)
   - "확인만 해줘, 수정 금지" 같은 요청을 이 종류로 받게 합니다.
   - Worker는 파일을 고치지 않고, Worker가 쓴 답을 그대로 Discord 보고에 담습니다.
   - 바뀐 파일이 없어도 no_changes 실패로 보지 않습니다. 반대로 파일을 바꾸면 범위 위반으로 막습니다.
   - 이 작업이 끝나면 파일럿 3건이 모두 모입니다. 그 뒤 task-0183~0196과 비교해 경량화를 계속할지 보고드리겠습니다.

[Owner 답]
1번 진행해

[Manager 질문과 Owner 답]
- 읽기 전용 작업을 어떻게 알아보게 할까요? = /work 문구로 구분 (추천)
  (지금처럼 /work를 쓰고, 요청에 '수정하지 마', '수정 금지', '보고만', '확인만', '읽기 전용' 같은 정해진 문구가 있으면 읽기 전용으로 돈다. 작업 준비 메시지에 '읽기 전용'이라고 표시해 /go 전에 확인할 수 있다. 문구를 빠뜨리면 지금처럼 수정 작업으로 돈다.)
- Worker의 답을 따로 검증할까요? = 검증 없이 보고 (추천)
  (Worker 1회만 부르고(이번 예로 약 $0.14), 보고에 '검증 안 된 Worker 답'이라고 표시한다. 파일이 바뀌면 실패 처리하는 검사는 그대로 한다. Reviewer·QA·main 반영은 없다.)
- Worker 답이 Discord 한 메시지(2000자)보다 길면 어떻게 할까요? = 잘라서 보고 + 전문은 로컬 파일 (추천)
  (Discord에는 앞부분만 보내고, 전문은 저장소 밖 %LOCALAPPDATA%\jarvis-core\reports\<task-id>.md에 저장해 경로를 알려 준다.)
```

## 조사 (등록 전)

- 계기: task-0200(Discord, 기록은 main에 추적되지 않은 채 FAILED)은 "보고만 해줘. 파일은 수정하지 마."라는 요청이 `studyroom_content` 수정 작업으로 돌아 Worker가 아무것도 고치지 않자 `scope:no_changes`로 실패했고, Worker의 답은 버려졌다(Worker 1회, API 환산 약 $0.14).
- `/work`는 작업 종류 표지어(앱 이름)가 있으면 TODO task를 만들고, 없으면 팀장 단계로 간다(`_run_work`). `/go`는 task 제목으로 종류를 정한다(`_go_work_kind`). task 제목은 `/work` 원문이며 120자를 넘으면 task가 만들어지지 않는다(`task_file_writer.MAX_TITLE_CHARS`). 그래서 제목으로 읽기 전용을 판정하면 작업 준비 표시와 `/go`가 같은 판정을 한다.
- 팀장(`claude_lead.py`)은 이미 HEAD의 임시 detached worktree에서 Read·Grep·Glob, plan 권한 모드로 claude를 부르고 끝나면 worktree를 지운다. 읽기 전용 Worker도 같은 도구 제한을 쓴다.
- Worker 경로는 SOP §10이 정한 승인된 예외다. 새 실행 경로이므로 §10.1 표와 규칙을 갱신해야 한다(§10.1 "범위를 넓히거나 바꾸려면 새 Owner 승인과 이 표의 갱신이 필요").

## 설계

1. `orchestrator/worker/claude_worker.py`
   - 읽기 전용 문구 목록 `READ_ONLY_MARKERS`와 `is_read_only_request(text)`(공백을 하나로 줄이고 소문자로 본다): 수정하지 마, 수정하지 말, 수정 금지, 고치지 마, 고치지 말, 변경하지 마, 변경하지 말, 변경 금지, 보고만, 확인만, 읽기 전용, read-only, read only, readonly.
   - `run_report()`: main이 checkout돼 있고 tracked 변경이 없을 때(task 자신의 기록 제외, 기존 preflight와 같음) baseline(HEAD)으로 attempt 이름의 detached worktree(브랜치 없음)를 저장소 밖에 만들고, 실행 표지(task-0167)를 둔다. Worker를 Read·Grep·Glob만, plan 권한 모드, `--tools`·`--strict-mcp-config`로 한 번 부른다(사용량은 task-0199 기록에 남음). 답이 비면 실패, worktree에 바뀐 파일이 있으면 `report_changed_files`로 실패(worktree 보존). 성공하면 답 전문을 저장소 밖 보고 파일(`%LOCALAPPDATA%\jarvis-core\reports\<attempt>.md`, `JARVIS_REPORT_DIR`로 변경)에 쓰고(실패해도 실행은 계속), DOING→DONE과 task 기록만 담는 checkpoint commit을 한다. 끝나면 worktree를 지운다. Reviewer·QA·ff-only 반영은 없다.
   - `WorkerRunResult`에 `read_only`, `report`, `report_path`를 더한다.
2. `adapters/discord/bot_minimal.py`
   - `/work`: 요청에 읽기 전용 문구가 있으면 작업 종류 표지어와 관계없이 팀장을 거치지 않고 TODO task를 만들고, 만든 task 제목으로 다시 판정한 결과를 작업 준비 메시지에 "읽기 전용 확인·보고"로 보인다. 제목이 읽기 전용이 아니게 되면(제목은 `/work` 원문이라 보통 일어나지 않음) 작업 준비 메시지 대신 `read_only_title_mismatch:<task-id>`로 거절한다. 이때 이미 만든 TODO task는 남고, 그 task에 `/go`하면 수정 작업으로 돈다(사유 코드에 task ID를 넣어 Owner가 알 수 있게 함, repair 1).
   - `/go`: 제목이 읽기 전용이면 읽기 전용 실행을 시작한다. `resume`은 거절(`resume_not_for_read_only`), `accept`는 기존 기록 검사대로 거절된다. `recover`는 그대로다.
   - 결과 보고: 성공이면 답(멘션 무력화, 한 메시지에 맞게 잘라냄)과 "검증 안 된 Worker 답(Reviewer·QA 없음)", 잘렸으면 전문 파일 경로, 사용량, checkpoint, push 없음. 실패면 기존 실패 보고에서 resume 선택지를 빼고 재시도·상태 확인만 보인다.
3. 판정·repair·QA·반영, 기존 작업 종류, 팀장, task 기록 형식은 바꾸지 않는다.
4. 문서: SOP §10.1(범위 문장, 표의 지원 작업 행과 새 읽기 전용 행, 팀장 문단의 예외 한 구절, 읽기 전용 문단), Discord README.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/worker/claude_worker.py`, `orchestrator/worker/run_smoke_tests.py`, `adapters/discord/bot_minimal.py`, `adapters/discord/README.md`, `docs/jarvis-multi-agent-sop-v0.1.md`(§10.1만), `memory/tasks/task-0201-read-only-report.md` |
| deny | `jarvis.bat`, `apps/`, 팀장 코드, writer·Console, task 기록 스키마, 감사 기록, AGENTS·agent 정의, validator, 다른 task 기록(task-0200 포함), 외부 API·credential, 보호 worktree, 작업 스케줄러 |

## 계획

1. 구현.
2. 검사: 문구 판정(있음, 없음, 공백·대소문자), 읽기 전용 실행 성공(답, 보고 파일, DONE 기록, checkpoint는 기록 한 파일만, worktree 정리, main에 다른 변경 없음), 바뀐 파일이 있으면 실패, 빈 답 실패, main이 더러우면 실패, 보고 파일 쓰기 실패에도 성공, 사용량 기록, 봇의 `/work`·`/go`·보고(잘림과 경로, 멘션 무력화, resume 거절, 실패 선택지). Worker smoke 전체, self-check, validator.
3. 사전 점검 → self-review → candidate(`commit_candidate.py --require-quotes`) → Reviewer → QA → Evidence·Complete → checkpoint. 기록 끝에 파일럿 측정값과 3건 비교. push와 봇 재시작은 별도 지시.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-27 10:56 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다. 등록 기록은 한때 별도 커밋(`973d3b5`)으로 만들었다가 push 전에 `git reset --soft`로 되돌려 candidate에 함께 담았다(task-0199와 같은 방식).

## 구현

- `orchestrator/worker/claude_worker.py`: `READ_ONLY_MARKERS`와 `is_read_only_request`, 상수 `REPORT_TOOLS`(Read·Grep·Glob)·`REPORT_DISALLOWED_TOOLS`·`REPORT_DIR`(기본 `%LOCALAPPDATA%` 아래 `jarvis-core/reports`, `JARVIS_REPORT_DIR`로 변경), `WorkerRunResult`의 `read_only`·`report`·`report_path`, `report_prompt`, `_run_report_worker`(plan 권한 모드, `--tools`·`--strict-mcp-config`, 사용량 기록, JSON의 `result`를 답으로), `run_report`·`_run_report`(설계 1의 순서. 보고 파일 이름은 attempt 이름이라 첫 시도는 `<task-id>.md`). 모듈 docstring에 한 문단.
- `adapters/discord/bot_minimal.py`: `_run_work`의 읽기 전용 분기(만든 task 제목으로 다시 판정, 어긋나면 `read_only_title_mismatch`), `_run_go`의 `read_only`와 `resume_not_for_read_only`, `_run_worker_job`의 `read_only` 인자와 `run_report` 호출, `on_message`가 그 값을 넘김, `_format_work_reply`의 읽기 전용 작업 준비·시작·성공(`_report_reply`, `REPORT_CUT_NOTE`. 보고 파일을 쓰지 못했으면 답 길이와 관계없이 그 사실을 적음)·실패 문구(기록 단계 실패 문구, 선택지).
- `orchestrator/worker/run_smoke_tests.py`: 가짜 claude의 `report`·`reportedit`·`reportempty` 모드(읽기 전용 인자가 아니면 종료 코드 5), `report_flow`(12개)와 `report_bot_flow`(12개).
- `docs/jarvis-multi-agent-sop-v0.1.md` §10.1: 범위 문장에 task-0201, 지원 작업 행과 팀장 문단에 읽기 전용 예외 한 구절, 표에 읽기 전용 행, 읽기 전용 문단(실패 기록은 11항, worktree는 `report_changed_files`일 때만 남김).
- `adapters/discord/README.md`: `/work` 절에 읽기 전용 항목.

## Implementer 검증 (작업 트리)

- Worker smoke total=641 failed=0(이전 617에 24개), Discord self-check ok 109, SOP validator PASS.
- 만드는 중 실패 두 번: 봇 문구를 넣는 패치 스크립트(bash heredoc 안의 Python 문자열)에서 줄바꿈 표기가 실제 줄바꿈으로 바뀌어 문법 오류가 났고 직접 고쳤다. 같은 방식으로 SOP 문단의 보고 파일 경로에서 역슬래시와 r이 줄바꿈으로 바뀌어 고쳤다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 추천]" | 추천의 표지. 해석할 조건이 아니다 |
| A2 | Owner 결정 (원문) | "읽기 전용 "확인·보고" 작업 종류 추가 (추천, 파일럿 3/3)" | Manager 해석: 작업 종류 레지스트리(`WORK_KINDS`)의 새 항목이 아니라 종류와 따로 판정하는 실행 방식으로 만들었다. 종류 항목은 허용 경로·테스트·QA를 전제로 하고 표지어가 앱 이름이라, 같은 앱에 대한 수정과 확인을 나눌 수 없기 때문이다. 파일럿 3/3이다 |
| A3 | Owner 결정 (원문) | ""확인만 해줘, 수정 금지" 같은 요청을 이 종류로 받게 합니다." | `is_read_only_request`가 이 두 문구를 포함한 정해진 목록으로 판정한다(검사) |
| A4 | Owner 결정 (원문) | "Worker는 파일을 고치지 않고, Worker가 쓴 답을 그대로 Discord 보고에 담습니다." | Worker는 Read·Grep·Glob만 보이는 plan 모드로 돈다. 답은 그대로 보내되 멘션만 무력화하고, 길면 A23대로 자른다 |
| A5 | Owner 결정 (원문) | "바뀐 파일이 없어도 no_changes 실패로 보지 않습니다." | 바뀐 파일이 없으면 성공이다(검사) |
| A6 | Owner 결정 (원문) | "반대로 파일을 바꾸면 범위 위반으로 막습니다." | scope 단계에서 `report_changed_files`로 실패하고 worktree를 남긴다. 이름은 기존 `scope_violation`과 구분했다(검사) |
| A7 | Owner 결정 (원문) | "이 작업이 끝나면 파일럿 3건이 모두 모입니다." | 기록 끝 파일럿 측정 절에 3/3 값을 남긴다 |
| A8 | Owner 결정 (원문) | "그 뒤 task-0183~0196과 비교해 경량화를 계속할지 보고드리겠습니다." | DONE 뒤 Owner 보고에서 비교한다. 이 task의 코드 범위가 아니다 |
| A9 | Owner 결정 (원문) | "[Owner 답]" | Owner 답의 표지. 해석할 조건이 아니다 |
| A10 | Owner 결정 (원문) | "1번 진행해" | 그대로 진행했다 |
| A11 | Owner 결정 (원문) | "[Manager 질문과 Owner 답]" | 질문과 답의 표지. 해석할 조건이 아니다 |
| A12 | Owner 결정 (원문) | "읽기 전용 작업을 어떻게 알아보게 할까요?" | 질문 원문. 답은 A13 |
| A13 | Owner 결정 (원문) | "= /work 문구로 구분 (추천)" | `/work` 문구로 구분한다. 새 명령은 만들지 않았다 |
| A14 | Owner 결정 (원문) | "(지금처럼 /work를 쓰고, 요청에 '수정하지 마', '수정 금지', '보고만', '확인만', '읽기 전용' 같은 정해진 문구가 있으면 읽기 전용으로 돈다." | 다섯 문구에 같은 뜻의 변형(수정하지 말, 고치지 마·말, 변경하지 마·말, 변경 금지, read-only, read only, readonly)을 더했다. 표지어가 없어도 읽기 전용이면 팀장을 거치지 않는다 |
| A15 | Owner 결정 (원문) | "작업 준비 메시지에 '읽기 전용'이라고 표시해 /go 전에 확인할 수 있다." | "작업 준비됨 (읽기 전용)"과 작업 종류 "읽기 전용 확인·보고"로 보인다. `/go`와 같은 task 제목으로 판정해 둘이 어긋나지 않는다(검사) |
| A16 | Owner 결정 (원문) | "문구를 빠뜨리면 지금처럼 수정 작업으로 돈다.)" | 기존 경로는 바꾸지 않았다(기존 검사 통과) |
| A17 | Owner 결정 (원문) | "Worker의 답을 따로 검증할까요?" | 질문 원문. 답은 A18 |
| A18 | Owner 결정 (원문) | "= 검증 없이 보고 (추천)" | Reviewer·QA 없이 보고한다 |
| A19 | Owner 결정 (원문) | "(Worker 1회만 부르고(이번 예로 약 $0.14), 보고에 '검증 안 된 Worker 답'이라고 표시한다." | Worker 한 번, 보고에 "검증 안 된 Worker 답입니다(Reviewer·QA 없음)."(검사) |
| A20 | Owner 결정 (원문) | "파일이 바뀌면 실패 처리하는 검사는 그대로 한다." | A6과 같다 |
| A21 | Owner 결정 (원문) | "Reviewer·QA·main 반영은 없다.)" | candidate·Reviewer·QA·ff-only가 없고 main에는 task 기록 한 파일의 checkpoint commit만 생긴다(검사) |
| A22 | Owner 결정 (원문) | "Worker 답이 Discord 한 메시지(2000자)보다 길면 어떻게 할까요?" | 질문 원문. 답은 A23 |
| A23 | Owner 결정 (원문) | "= 잘라서 보고 + 전문은 로컬 파일 (추천)" | 한 메시지에 맞게 자르고 잘림 표시를 붙인다(검사) |
| A24 | Owner 결정 (원문) | "(Discord에는 앞부분만 보내고, 전문은 저장소 밖 %LOCALAPPDATA%\jarvis-core\reports\<task-id>.md에 저장해 경로를 알려 준다.)" | 전문은 저장소 밖 보고 폴더에 쓰고, 잘렸을 때 경로를 적는다. 파일 이름은 attempt 이름이라 첫 시도는 `<task-id>.md`이고 앞선 시도가 남아 있으면 `-r<N>`이 붙는다(Manager 해석, README에 적음). 쓰기에 실패하면 답 길이와 관계없이 그 사실을 보고한다(검사) |

## Self-review

candidate 전 1회(사전 점검 `--require-quotes` PASS, staged 6, 위반 0, 미인용 0 뒤). 지적 6건을 모두 반영했다.

1. major: SOP 읽기 전용 문단이 실패를 11항("실패한 시도는 보존한다")으로 보냈는데 코드는 `report_changed_files`일 때만 worktree를 남긴다. 실패 기록은 11항, worktree는 그 경우만 남긴다고 고쳤다.
2. 설계 4는 지원 작업 행을 고친다고 했지만 새 행만 더했고, 지원 작업 행과 팀장 문단은 표지어가 없으면 팀장으로 간다고만 읽혔다. 두 곳에 읽기 전용 예외 한 구절을 넣고 설계 4를 실제대로 고쳤다.
3. `_run_work`의 제목이 읽기 전용이 아닐 때 기본 종류의 수정 계획으로 넘어가는 분기가 설계에 없었다. 수정 작업으로 넘기지 않고 `read_only_title_mismatch`로 거절하게 바꾸고 검사 1개를 더했다.
4. A24는 쓰기 실패를 늘 보고한다고 했지만 코드는 잘린 경우에만 적었다. 짧은 답에도 적게 바꾸고 검사 1개를 더했다.
5. README의 "공백 차이 무시"와 "넘으면 전문 파일" 문구를 코드대로(연속 공백은 하나로, 전문은 성공 때마다 저장) 고쳤다.
6. 기록에 사전 점검과 self-review 단계가 없었다. 이 절을 더했다.

- 고친 뒤: Worker smoke total=641 failed=0, Discord self-check ok 109, validator PASS.
- self-review 사용량(API 환산 추정): 약 $0.67, 97초.

## Reviewer 1차와 repair 1

- candidate `88b0df3aa0295efca1f45073e745aee49427302b`: Reviewer FINDINGS, minor 3건, self_deviations 0. 모두 candidate 파일을 가리켜 repair 예산 안에서 고쳤다(`repair_count=1`).
  1. SOP 읽기 전용 문단이 10.2의 1~9항·12항만 제외해, 10항(9가 성공한 경우에만 자동 DONE과 checkpoint)과 읽기 전용 DONE이 맞부딪쳤다. 제외 범위를 1~10항·12항으로 넓히고 DONE과 기록 checkpoint는 그 문단을 따른다고 적었다.
  2. `JARVIS_REPORT_DIR`가 저장소 안을 가리키면 답이 작업 트리에 쓰일 수 있었다. 보고 폴더에 `_ensure_outside_repo`를 적용해 저장소 안이면 쓰지 않은 것으로 본다(검사 1개, SOP 문단에도 적음).
  3. `read_only_title_mismatch` 때 만든 TODO task가 남아 `/go`하면 수정 작업으로 도는데, 기록은 그런 task가 생기지 않는다고 적었다. 기록 설계 2와 코드 주석을 실제대로 고치고, 사유 코드에 task ID를 붙였다(검사에 TODO로 남는 것까지 확인).
- Reviewer 미확인 가운데 읽기 전용 호출의 `--disallowedTools`·`--strict-mcp-config`는 가짜 claude가 함께 확인하게 했다(아니면 종료 코드 5).
- 고친 뒤: Worker smoke total=642 failed=0, Discord self-check ok 109, validator PASS.

## Reviewer·QA 결과

- candidate `c0626d978f6a9130918032d4d82537c6dbd88b20`(repair 1 뒤): fresh Reviewer PASS(findings 0, self_deviations 0). Reviewer 미확인 가운데 실제 claude의 plan 모드 동작과 Discord 실제 표시는 이번에 확인하지 않았다(가짜 claude로만 검사). 읽기 전용 DOING task의 recover는 기존 13항 경로를 그대로 쓰며 따로 실행해 보지 않았다.
- QA: 새 detached worktree에서 PASS 30/30(변경 파일 6개, 바뀐 정의가 적은 것뿐이고 파이프라인·accept·팀장·Worker 호출은 그대로, SOP 변경이 모두 10.1 안, 읽기 전용 호출 인자, 답 추출과 빈 답 실패, 보고 문구가 어떤 길이에서도 한 메시지 안이고 멘션 없음·잘림 표시·전문 경로·저장 실패 표시, 실패 선택지, Worker smoke 642/0과 self-check 109가 실제 보고 폴더·사용량 로그를 건드리지 않음, `--require-quotes` 기록 점검, validator, check_no_secrets, diff --check, 제어 문자 없음, jarvis.bat·task-0200 기록 미추적). 첫 실행은 QA 스크립트의 출력 인코딩(cp949) 오류로 중간에 멈춰, 스크립트만 고쳐 같은 candidate에서 다시 실행했다(retry, source 변경 없음). worktree는 지웠다.
- Console Evidence 기록 후 Complete(DOING → DONE)로 닫았다. Console은 끝난 뒤 껐다. push와 봇 재시작은 하지 않았다(읽기 전용 실행은 봇을 다시 켜야 Discord에서 쓸 수 있다).

## 파일럿 측정 (3/3)

| 항목 | 값 |
| --- | --- |
| 요약 표 | `--emit-table`로 생성, 24행, 미인용 0 |
| 커밋 | candidate 두 커밋(첫 candidate, repair 1) 모두 `commit_candidate.py --require-quotes`(점검 PASS 뒤 커밋) |
| self-review | 1회, 지적 6건(major 1: SOP 안의 실패 시 worktree 보존 모순, minor 5: 설계와 SOP 행, 제목 불일치 분기, 저장 실패 표시, README 문구, 기록 단계 누락). 모두 candidate 전에 반영 |
| Reviewer 실행 | 2회(FINDINGS minor 3 → repair 1 → PASS) |
| 지적 유형 | Reviewer: SOP 규칙 충돌 1, 실제 결함 1(보고 폴더가 저장소 안일 수 있음), 기록·주석이 코드보다 넓음 1. self-review: 실제 결함 2(제목 불일치 분기, 저장 실패 표시), SOP·문서 문구 3, 기록 1 |
| Owner 원문 누락 지적 | 0건 |
| repair | 1회 |
| QA 실행 | 2회(첫 실행은 QA 스크립트 인코딩 오류, 같은 candidate 재실행) |
| 사고 | 패치 스크립트의 줄바꿈 표기 손상 2건(구현 절). 등록 기록을 따로 커밋했다가 push 전 되돌림 |
| self-review 사용량(API 환산 추정) | 약 $0.67, 97초 |

## 파일럿 3건 비교 (task-0183~0196 수동 task와)

기준 기간의 수동 SOP task 10건(task-0183, 0184, 0185, 0188, 0189, 0191, 0193, 0194, 0195, 0196. Discord Worker task는 뺌)의 기록에서 마지막 `repair_count`를 읽었다. Reviewer 실행 수는 그 기간 기록에 일정한 칸이 없어 repair 수 + 1로 어림했다(무효 검토 재실행은 빠짐).

| 구분 | task 수 | repair 합(평균) | Reviewer 실행 어림 합(평균) | 첫 Reviewer PASS |
| --- | --- | --- | --- | --- |
| 기준 기간 | 10 | 14(1.4) | 24(2.4) | 4건(0184, 0188, 0191, 0195) |
| 파일럿(0198, 0199, 0201) | 3 | 1(0.33) | 4(1.33) | 2건(0198, 0199) |

- 파일럿 3건 모두 Owner 원문을 요약이 빠뜨렸다는 지적이 0건이었고, 커밋 보호를 거치지 않은 커밋은 없었다(task-0198의 `;` 사고는 보호를 거쳤지만 보완 전 기록이 커밋된 것).
- 한계: 표본이 3건이고 task 크기와 종류가 기준 기간과 다르다. 기준 기간의 지적 유형은 기록마다 분류가 달라 유형별 비교는 하지 않았다. Reviewer 실행 수는 어림이다.
