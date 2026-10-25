# task-0199-worker-usage-record

- id: `task-0199-worker-usage-record`
- title: `Worker 경로 사용량 기록`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-25 16:53 UTC`
- updated_at: `2026-10-25 17:26 UTC`
- summary: `Discord Worker 경로에서 Worker와 Reviewer의 claude 실행 결과에 이미 있는 사용량(API 환산 비용, 토큰, 시간, 턴 수)을 버리지 않고 남긴다. 실행마다 저장소 밖 사용량 로그(JSON 한 줄)에 쓰고, 실행 결과에 담아 Discord 완료·실패 보고에 한 줄로 보인다. 프롬프트와 답 내용은 남기지 않는다. 판정·repair·QA·반영 로직과 task 기록 형식은 바꾸지 않는다. SOP 경량화 파일럿 측정 대상 2/3이다.`
- source_command: `Owner 지시: Worker 비용 기록 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `e50b59aec597f3fe24427b9e539483e399679bf3` (등록 시점 main HEAD, task-0198까지 push 완료) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |
| 파일럿 | SOP 경량화 파일럿(task-0197) 측정 대상 2/3. 요약 표는 `check_summary_quotes.py --emit-table`, candidate는 `commit_candidate.py --require-quotes`로 만든다 |

## Owner 결정 (원문)

```text
[Manager 추천]
1. Worker 경로 비용 기록 (파일럿 2/3로 추천)
   - Discord Worker 경로의 Worker와 Reviewer 실행 결과에는 이미 비용·토큰·시간이 들어 있는데, 파이프라인이 버리고 있습니다.
   - 이 값을 task 실행 기록에 남기면, 앞으로 비용 절감 효과를 숫자로 볼 수 있습니다. 비용 조사 때 "측정 불가"였던 항목을 채우는 일입니다.
   - 작고, 파이프라인 판정은 바꾸지 않습니다.

[Owner 답]
1번 Worker 비용 기록 task로 진행해
```

## 조사 (등록 전)

- Worker는 `claude -p --output-format json`의 표준 출력을 읽지 않고 버린다(`_run_worker`). Reviewer는 `result`만 읽는다(`_run_reviewer`). 이 JSON에는 `total_cost_usd`(API 요금 환산, 구독 사용에서는 실제 청구액이 아님), `duration_ms`, `num_turns`, `usage`(입력·출력·캐시 토큰), `is_error`가 있다(task-0195 stream-json 실험과 self-review 결과 JSON으로 확인).
- task 기록의 실행 필드는 정해진 스키마이고 새 필드를 금지하며(`bot_minimal.py` `_execution_metadata_values`, task-0053 결정 2), `execution_result` JSON은 500자 예산이 있다. 그래서 사용량은 task 기록 메타데이터에 넣지 않는다.

## 설계

1. `orchestrator/worker/claude_worker.py`:
   - 실행 중 사용량 목록을 담는 contextvar를 두고 `run_pipeline`이 실행마다 새 목록으로 설정한다(작업 종류 contextvar와 같은 방식).
   - `_run_worker`와 `_run_reviewer`가 claude 출력 JSON에서 비용·시간·턴·토큰·오류 여부만 꺼내(`_note_usage`) 그 목록에 더하고 사용량 로그에 한 줄로 덧붙인다. JSON이 아니거나 필드가 없으면 그 값은 비워 둔다. 로그 쓰기 실패는 실행에 영향을 주지 않는다.
   - 사용량 로그: 기본 `%LOCALAPPDATA%\jarvis-core\logs\agent-usage.jsonl`(저장소 밖), 환경 변수 `JARVIS_USAGE_LOG`로 바꿀 수 있다. 한 줄에 시각, task ID, 단계(worker, reviewer), 비용, 시간, 턴, 토큰 네 가지, 오류 여부, 종료 코드. 프롬프트·답·파일 내용은 넣지 않는다.
   - `WorkerRunResult`에 `usage` 목록을 더한다.
2. `adapters/discord/bot_minimal.py`: Worker 실행 결과 보고(완료, 실패, Owner 판단 필요)에 사용량이 있으면 한 줄("사용량(API 환산 추정): Worker n회 $x, Reviewer m회 $y, 합계 t초")을 더한다. 사용량이 없으면(예: accept) 보고는 지금과 같다.
3. 판정·repair·QA·반영, task 기록 형식, 팀장 호출은 바꾸지 않는다. 팀장 사용량은 후속 후보로 남긴다.
4. 문서: Discord README의 Worker 절에 사용량 줄과 로그 위치를 적는다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/worker/claude_worker.py`(사용량 contextvar·기록 함수, `_run_worker`·`_run_reviewer`의 기록 호출, `run_pipeline`의 설정, WorkerRunResult의 usage 필드만), `orchestrator/worker/run_smoke_tests.py`, `adapters/discord/bot_minimal.py`(Worker 결과 보고의 사용량 줄만), `adapters/discord/README.md`, `memory/tasks/task-0199-worker-usage-record.md` |
| deny | `jarvis.bat`, `apps/`, 팀장 코드, writer·Console, task 기록 스키마, 감사 기록, AGENTS·agent 정의, SOP, validator, 다른 task 기록, 외부 API·credential, 보호 worktree, 작업 스케줄러 |

## 계획

1. 구현.
2. 검사: 사용량 추출(실제 출력 모양의 JSON, JSON 아님, 필드 없음), 로그 한 줄의 필드와 내용 없음(프롬프트 문자열이 들어가지 않음), 로그 쓰기 실패가 실행을 바꾸지 않음, 파이프라인 한 번에 worker·reviewer 줄이 task ID와 함께 남음, 보고의 사용량 줄(있을 때만), 기존 보고 문자열 불변 검사 통과. Worker smoke 전체, self-check, validator.
3. 사전 점검 → self-review → candidate(`commit_candidate.py --require-quotes`) → Reviewer → QA → Evidence·Complete → checkpoint. 기록 끝에 파일럿 측정값. push와 봇 재시작은 별도 지시.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-25 16:53 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다.

## 구현

- `orchestrator/worker/claude_worker.py`: contextvar `_ACTIVE_USAGE`, 상수 `USAGE_LOG`(기본 `%LOCALAPPDATA%\jarvis-core\logs\agent-usage.jsonl`, `JARVIS_USAGE_LOG`로 변경, LOCALAPPDATA가 없으면 홈 폴더 아래), `USAGE_TOKEN_FIELDS`, 함수 `usage_of`(출력 JSON에서 단계·비용·시간·턴·오류 여부·종료 코드·토큰 네 가지만 꺼냄, 타입이 맞지 않으면 None)와 `_note_usage`(실행 중일 때만 목록에 더하고 로그에 한 줄 덧붙임, 쓰기 실패는 표준 오류에 한 줄만 남기고 실행은 그대로). `_run_worker`와 `_run_reviewer`가 결과를 받은 직후 `_note_usage`를 부른다(Worker는 실패 판정보다 먼저). `run_pipeline`이 실행마다 새 목록을 설정하고 끝나면 `WorkerRunResult.usage`에 담는다. accept는 claude를 부르지 않아 사용량이 없다. `datetime` import를 더했다.
- `adapters/discord/bot_minimal.py`: `_usage_line`을 더해 Worker 결과 보고의 성공 보고(push 줄 앞)와 실패·Owner 판단 필요 보고(main 변경 여부 줄, 곧 "main은 변경되지 않았고" 또는 checkpoint 실패 줄 뒤)에 사용량이 있을 때만 한 줄을 넣는다. 비용이 없는 호출은 "비용 정보 없음"으로, 시간 값이 하나도 없으면 "합계 시간 정보 없음"으로 적는다(0초로 보이지 않게).
- `orchestrator/worker/run_smoke_tests.py`: `usage_checks` 검사 17개(직접 13개와 `run_case` 두 번이 더하는 기본 검사 4개. 실제 모양 JSON의 값, 답 내용 없음, JSON 아님, 잘못된 타입, 실행 밖 호출은 기록 없음, 한 번 실행의 worker·reviewer 두 줄과 task ID 순서, 로그에 프롬프트·답 없음, 로그 쓰기 실패가 실행을 바꾸지 않음, 보고의 사용량 줄과 위치, 사용량이 없으면 줄 없음, 실패 보고의 사용량 줄, 비용 없는 호출, 시간 정보 없음). smoke는 `USAGE_LOG`를 임시 폴더로 바꿔 실제 로그를 쓰지 않는다.
- `adapters/discord/README.md`: Worker 절 4항에 사용량 줄과 로그 위치.

## Implementer 검증 (작업 트리)

- Worker smoke total=617 failed=0(이전 600에 17개), Discord self-check ok 109, SOP validator PASS.
- smoke를 돌린 뒤에도 실제 `%LOCALAPPDATA%\jarvis-core\logs`에 `agent-usage.jsonl`이 생기지 않았다.
- 만드는 중 실패 세 번: 패치 스크립트의 줄바꿈 처리로 검사 문자열 하나가 깨져 직접 고쳤고, 보고 줄 검사의 기대 합계 시간을 잘못 계산(16초, 실제 30초)해 고쳤다(검사 쪽 실수). README에 넣은 로그 경로의 역슬래시 하나가 패치 문자열에서 제어 문자(벨)로 바뀌어 고쳤다(README의 제어 문자 0개 확인).

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 추천]" | 추천의 표지. 해석할 조건이 아니다 |
| A2 | Owner 결정 (원문) | "Worker 경로 비용 기록 (파일럿 2/3로 추천)" | 이 task로 진행했다. 측정 대상 2/3이다(기준선 표의 파일럿 행) |
| A3 | Owner 결정 (원문) | "Discord Worker 경로의 Worker와 Reviewer 실행 결과에는 이미 비용·토큰·시간이 들어 있는데, 파이프라인이 버리고 있습니다." | 버리던 claude 출력 JSON에서 비용·토큰·시간·턴을 꺼낸다(`usage_of`) |
| A4 | Owner 결정 (원문) | "이 값을 task 실행 기록에 남기면, 앞으로 비용 절감 효과를 숫자로 볼 수 있습니다." | "task 실행 기록"을 task ID가 붙은 실행별 사용량 기록으로 읽은 것은 Manager의 해석이다. task 기록 메타데이터의 실행 필드는 새 필드를 금지하는 스키마라(조사 절) 그곳에는 넣지 않고, 같은 실행의 결과(`WorkerRunResult.usage`), 그 task의 Discord 완료·실패 보고 한 줄, task ID가 붙은 저장소 밖 사용량 로그에 남긴다. 원문의 목적("비용 절감 효과를 숫자로 볼 수 있습니다")은 task별로 모을 수 있는 이 로그로 채워지므로 원문 범위 안이라고 봤다. task 기록 파일 안에 남기길 원하시면 Owner 확인이 필요하다 |
| A5 | Owner 결정 (원문) | "비용 조사 때 "측정 불가"였던 항목을 채우는 일입니다." | 그 항목(Worker 경로의 Worker·Reviewer 비용)을 이제 잰다. 팀장 호출은 아직 아니다(후속 후보) |
| A6 | Owner 결정 (원문) | "작고, 파이프라인 판정은 바꾸지 않습니다." | 판정·repair·QA·반영과 task 기록 형식은 바꾸지 않았다. 기록 실패도 실행을 바꾸지 않는다(검사) |
| A7 | Owner 결정 (원문) | "[Owner 답]" | Owner 답의 표지. 해석할 조건이 아니다 |
| A8 | Owner 결정 (원문) | "1번 Worker 비용 기록 task로 진행해" | 그대로 진행했다 |

## Self-review

candidate 전 1회. minor 6건을 모두 반영했다.

1. A4: "task 실행 기록"을 task 기록 밖의 사용량 로그로 옮긴 것이 Manager의 해석이라는 점과 그 근거를 적었다.
2. 시간 값이 없으면 "합계 0초"로 보였다. "합계 시간 정보 없음"으로 바꾸고 검사 1개를 더했다.
3. 실패 보고의 사용량 줄 위치(checkpoint 실패 줄 뒤도 포함)를 정확히 적었다.
4. 설계의 로그 필드에 종료 코드를 더했다.
5. "실패 두 번" 뒤에 세 건이 있었다. 세 번으로 고쳤다.
6. 검사 개수의 내역(직접 13개, `run_case` 기본 4개)을 적었다.

- 고친 뒤: Worker smoke total=617 failed=0, Discord self-check ok 109, validator PASS. 사전 점검(`--require-quotes`, baseline `e50b59a`): status=PASS, staged_files 5, violations 0, 미인용 0.
