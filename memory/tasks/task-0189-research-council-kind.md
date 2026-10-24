# task-0189-research-council-kind

- id: `task-0189-research-council-kind`
- title: `Worker 작업 종류: Research Council`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-23 09:51 UTC`
- updated_at: `2026-10-24 05:15 UTC`
- summary: `Worker 작업 종류 research_council을 더한다(허용 경로 apps/research-council/, 테스트 그 앱의 smoke test). 외부 LLM 호출 파일 openrouter_advisor.py, LIVE 모드 스위치와 검증 필터가 있는 llm_advisor.py, .env.example은 보호 경로로 막고, Worker 지시에 네트워크·외부 API·LLM·새 의존성 금지를 적는다. 더해 이 종류의 변경이 네트워크 모듈, openrouter, LIVE 모드 연결, 환경 변수·API 키 읽기 같은 금지 문구를 새 줄로 들여오면 scope 단계와 QA에서 자동으로 멈추는 코드 검사를 넣는다.`
- source_command: `Owner 지시: Research Council 작업 종류 추가, 보호 + 코드 검사 선택 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `27827adaeec9949575cdeffa5e4d13da437511bd` (등록 시점 main HEAD, task-0188까지 push 완료) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=1` (SOP §5 기본값, 사용 내역은 Repair 절) |

## Owner 결정 (원문)

```text
[Owner 지시]
다음은 Research Council 작업 종류 추가하자

[Manager 질문]
Research Council 작업 종류에서 외부 API(OpenRouter) 연결을 어디까지 막을까요? 조사 결과: 실제 호출 코드는 openrouter_advisor.py 한 곳뿐이지만, 그 호출을 켜는 스위치(LIVE 모드와 결과 검증 필터)는 llm_advisor.py에 있습니다. 지금은 어떤 실행 스크립트도 LIVE를 켜지 않고, 이 PC에는 OPENROUTER_API_KEY가 설정돼 있지 않아 켜져도 호출이 일어나지 않습니다. 앱 smoke test는 약 25초입니다.
- 두 파일 보호 + 지시 (권장): openrouter_advisor.py, llm_advisor.py, .env.example을 보호 경로로 막고, Worker 지시에 네트워크·외부 API·LLM·새 의존성 금지와 LIVE 모드 연결 금지를 적습니다. 판정 로직은 바꾸지 않습니다. 다른 실행 스크립트에 LIVE를 연결하는 변경은 Reviewer가 보는 지시 수준입니다.
- 보호 + 코드 검사 추가: 1번에 더해, Worker 변경에 네트워크 import나 openrouter·LIVE 연결이 새로 들어오면 QA에서 자동으로 실패시키는 검사를 claude_worker.py에 추가합니다. 더 안전하지만 Worker 판정 로직을 바꾸는 더 큰 작업입니다.
- 호출 파일만 보호: 처음 제안대로 openrouter_advisor.py만 보호하고 지시를 적습니다. 가장 작지만 LIVE 스위치(llm_advisor.py)는 Worker가 바꿀 수 있습니다.

[Owner 답]
보호 + 코드 검사 추가
```

## 설계

1. `WORK_KINDS`에 세 번째 항목 `research_council`을 더한다. 표지어는 앱 이름(research council, research-council, research_council, 리서치 카운슬)만, 허용 경로 `apps/research-council/`, 테스트 `apps/research-council/run_smoke_tests.py`, 커밋 범위 `research-council`. Studyroom이 계속 첫 항목이자 기본 종류다.
2. `PROTECTED_PATHS`에 `apps/research-council/research_council/openrouter_advisor.py`, `apps/research-council/research_council/llm_advisor.py`, `apps/research-council/.env.example`을 더한다. 허용 경로 안이어도 변경은 `scope_violation`이고 Reviewer 증거에서도 빠진다.
3. 코드 검사: `WorkKind`에 `forbidden_additions`(기본 빈 값)를 더하고, research_council에만 금지 문구 목록을 둔다(네트워크 모듈 urllib·http.client·socket·requests·httpx·aiohttp·websocket, subprocess, openrouter, LIVE 모드 연결, candidate_generator, 환경 변수·API 키 읽기). 변경 파일에서 기준선에 없던 새 줄이 금지 문구를 담으면(대소문자 무시), scope 단계에서 `forbidden_addition`으로 멈추고(사유에 파일과 문구), QA의 `change_set_matches`도 거짓이 된다. accept도 QA를 다시 돌리므로 같은 검사를 받는다. 기존 줄과 지운 줄은 보지 않는다. 다른 종류는 목록이 비어 있어 동작이 그대로다.
4. Worker 지시(`prompt_note`): 앱 구조·스타일 유지, smoke test 통과, 결정론 유지, 네트워크·외부 API·LLM·환경 변수·subprocess·새 의존성 금지, LIVE 모드·candidate_generator 연결 금지, 보호 파일 3개 변경 금지, 금지 문구가 든 새 줄은 파이프라인이 거절한다는 안내.
5. 팀장은 등록된 종류 목록을 그대로 읽으므로 새 종류가 자동으로 보인다. 다른 종류, `/go`·repair·Reviewer·반영 로직은 바꾸지 않는다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/worker/claude_worker.py`(`WorkKind`, `WORK_KINDS`, `PROTECTED_PATHS`, 새 금지 문구 검사 함수, 그 검사를 부르는 scope 단계와 `_qa_checks`, QA 의미 문장만), `orchestrator/worker/run_smoke_tests.py`, `adapters/discord/bot_minimal.py`(self-check의 기대값만), `adapters/discord/README.md`, `docs/jarvis-multi-agent-sop-v0.1.md`(§10.1 표와 금지 문구 설명), `memory/tasks/task-0189-research-council-kind.md` |
| deny | `jarvis.bat`, `apps/`(앱 자체는 바꾸지 않음), 팀장 코드, writer·Console, AGENTS·agent 정의, validator(표 형식이 그대로라 변경 불필요할 때), 다른 task 기록, 외부 API·credential, 보호 worktree |

## 계획

1. 레지스트리·보호 경로·금지 문구 검사 구현.
2. 검사: 앱 README 수정이 Reviewer·QA·main 반영까지 DONE(실제 Research Council smoke 실행), 보호 파일 변경은 scope_violation, 금지 문구가 든 새 줄은 forbidden_addition, 기존 줄·지운 줄은 걸리지 않음, 다른 종류는 그대로, QA에서도 같은 판정, 표지어 선택, Worker 지시.
3. 문서: SOP §10.1 표(validator가 코드와 맞춰 봄), Discord README.
4. 사전 점검 → self-review → candidate → Reviewer → QA → Evidence·Complete(Manager, G3와 같게) → checkpoint. push는 별도 승인.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-23 09:51 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다.

## 구현

- `orchestrator/worker/claude_worker.py`: `WorkKind`에 `forbidden_additions`(기본 빈 값)를 더했다. `WORK_KINDS`에 세 번째 항목 `research_council`(표지어 앱 이름 4개, 허용 경로 `apps/research-council/`, 테스트 그 앱의 `run_smoke_tests.py`, 커밋 범위 `research-council`, Worker 지시, 금지 문구 18개)을 더했다. `PROTECTED_PATHS`에 `openrouter_advisor.py`, `llm_advisor.py`, `.env.example`(모두 `apps/research-council/` 아래)을 더했다. 새 함수 `_forbidden_additions`는 변경 파일마다 기준선 파일보다 많아진 줄만 새 줄로 세어(남은 줄·옮긴 줄·지운 줄은 제외) 금지 문구를 대소문자 무시로 찾는다. scope 단계는 범위 검사 뒤 이 검사에 걸리면 `forbidden_addition`으로 멈추고(사유에 파일과 문구), `_qa_checks`의 `change_set_matches`도 이 검사를 함께 본다(accept도 QA를 다시 돌리므로 같다). QA 의미 문장은 금지 문구가 있는 종류에만 그 부분을 덧붙인다. 다른 종류는 목록이 비어 동작이 그대로다.
- `orchestrator/worker/run_smoke_tests.py`: `run_case`에 `work_kind` 인자를 더했고, 가짜 Worker 모드 5개(`rcreadme`, `rcadvisor`, `rcnet`, `rclive`, `rcnewfile`)와 `research_council_flow` 검사를 더했다. 종류 등록·표지어, 보호 파일 3개, 금지 문구(네트워크 import, 대문자 LIVE, 새 파일), 실제 Research Council smoke로 README 수정이 DONE, Worker 지시, QA 의미, 작은 임시 저장소에서 새 줄 판정(남은·옮긴·지운 줄 제외, 늘어난 사본은 셈, 삭제 파일, QA의 `change_set_matches`, 목록 없는 종류)을 본다.
- `adapters/discord/bot_minimal.py`: self-check의 작업 종류 레지스트리 기대값만 세 종류로 바꿨다.
- `docs/jarvis-multi-agent-sop-v0.1.md`: §10.1 머리말, 지원 작업·허용 경로·보호 경로·테스트 명령 행, 새 "추가 금지 문구" 행.
- `adapters/discord/README.md`: `/work`·`/go` 절 머리말에 새 종류와 보호 파일을 적었다. 같은 문장에 있던 "Worker는 네트워크·외부 API·새 의존성을 더하지 않는다"는 task-0185 Reviewer가 지적하고 Owner가 수용했던 문구로, 이번에 이 줄을 고치면서 무엇이 지시이고 무엇이 코드 검사인지 나눠 적었다.
- validator는 바꾸지 않았다. 표 형식이 그대로라 새 종류도 기존 대조 검사가 본다.

## Implementer 검증 (작업 트리)

- Worker smoke total=589 failed=0(이전 559에 30개), Discord self-check ok 109, SOP validator PASS(negative_checks 172, 실패 0).
- 사전 점검(`check_task_record`, baseline `27827ad`): status=PASS, staged_files 6, violations 0.
- 실제 앱 smoke(`apps/research-council/run_smoke_tests.py`)는 약 25초이고, 위 Worker smoke 안에서 README 수정 사례가 테스트 단계와 QA에서 두 번 돌려 통과했다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "다음은 Research Council 작업 종류 추가하자" | `research_council` 종류를 세 번째 항목으로 더했다. 다른 종류와 기본 종류는 그대로다 |
| A2 | Owner 결정 (원문) | "- 보호 + 코드 검사 추가: 1번에 더해, Worker 변경에 네트워크 import나 openrouter·LIVE 연결이 새로 들어오면 QA에서 자동으로 실패시키는 검사를 claude_worker.py에 추가합니다. 더 안전하지만 Worker 판정 로직을 바꾸는 더 큰 작업입니다." / "[Owner 답]" / "보호 + 코드 검사 추가" | 1번 내용(보호 파일 3개, Worker 지시)을 모두 넣었다. 검사는 QA에서 실패시키고, 같은 검사를 더 이른 scope 단계에도 걸어 테스트·Reviewer 전에 멈추게 했다. 금지 문구 가운데 Owner 원문에 이름이 없는 것은 Manager의 추가이고 근거는 이렇다. candidate_generator는 LIVE 모드가 호출 함수를 받는 자리(`llm_advisor.py`의 `LLMAdvisorConfig.candidate_generator`)라 LIVE 연결의 일부다. os.environ·getenv·api_key는 `openrouter_advisor.py`가 API 키를 환경 변수에서 읽는 방식이라 키를 끌어오는 경로다. subprocess는 외부 명령(curl 등)으로 네트워크를 우회하는 경로다. requests는 다른 이름(`evidence_requests` 등)과 문장(evidence requests)에 흔히 들어 있어 import가 있는 줄과 `requests.get` 같은 호출만 막는다(repair 1에서 정규식으로 바꿨다). 모두 더 좁히는 쪽이며 Worker 권한을 넓히지 않는다 |
| A3 | Owner 결정 (원문) | "- 두 파일 보호 + 지시 (권장): openrouter_advisor.py, llm_advisor.py, .env.example을 보호 경로로 막고, Worker 지시에 네트워크·외부 API·LLM·새 의존성 금지와 LIVE 모드 연결 금지를 적습니다." | 세 파일을 `PROTECTED_PATHS`에 넣었고 Worker 지시에 금지와 보호 파일을 적었다 |
| A4 | Owner 결정 (원문) | "판정 로직은 바꾸지 않습니다." / "다른 실행 스크립트에 LIVE를 연결하는 변경은 Reviewer가 보는 지시 수준입니다." / "[Owner 답]" / "보호 + 코드 검사 추가" | 이 두 문장은 1번 선택지의 설명이다. Owner가 고른 2번은 "1번에 더해" 판정 로직을 바꾸는 검사를 넣는 선택이므로, 이 두 조건은 2번으로 대체됐다고 본다. 그래서 scope 단계와 QA 판정을 바꿨고, 다른 실행 스크립트에 LIVE를 연결하는 새 줄도 지시가 아니라 코드 검사로 막는다 |

## Self-review

candidate 전 1회. minor 3건을 모두 반영했다.

1. 1번 선택지의 "판정 로직은 바꾸지 않습니다."와 "Reviewer가 보는 지시 수준" 문장이 요약에 없었다. A4 행을 더해 원문을 인용하고, 2번 선택으로 대체됐다는 해석을 적었다.
2. Owner 원문에 없는 금지 문구(candidate_generator, 환경 변수·API 키 읽기, subprocess)와 scope 단계 정지의 근거가 없었다. A2 해석 칸에 항목마다 근거를 적었다.
3. SOP 행과 Worker 지시는 socket·requests를 담은 줄이면 다 거절한다고 읽혔지만, 코드는 `import`·`from` 형태만 막는다. 코드는 그대로 두고 SOP 행과 Worker 지시를 코드에 맞게 고쳤다.

고친 뒤 다시 돌린 결과: Worker smoke total=589 failed=0, Discord self-check ok 109, validator PASS(negative_checks 172, 실패 0). 사전 점검도 다시 PASS(staged_files 6, violations 0).

## Repair

- candidate `b1951c7adc86abf54235828c0dcfe72127dfd975`: Reviewer 보고가 금지된 명령 옵션(`git grep -i`)을 self_deviations에 적어 SOP상 무효 검토다. 그 보고의 minor 지적 1건은 Manager가 직접 확인해 사실이었다: 금지 문구를 단순 문자열로 비교해 `import os, socket`, `import json, requests`, `from http import client`, 여러 줄로 나눈 import가 통과했다. Owner 원문의 "네트워크 import나 openrouter·LIVE 연결이 새로 들어오면 QA에서 자동으로 실패"와 맞지 않으므로 무효 검토의 재실행(retry) 대신 repair로 고쳤다.
- repair 1(`repair_count=1`, 기본 예산 안): `forbidden_additions`를 (이름, 정규식) 쌍으로 바꿔 소문자로 바꾼 줄에서 찾는다. 낱말 socket, import가 있는 줄의 requests, `from http`·`from requests` 같은 네트워크 모듈 import, `requests.get` 같은 호출, `__import__`·importlib을 더해 19개다. 보고 사유에는 항목 이름이 나온다. Worker 지시와 SOP §10.1 행을 같은 규칙으로 고쳤고, 위 형태들이 잡히고 흔한 낱말은 통과하는 검사 1개를 더했다. 구현 절의 "금지 문구 18개"는 첫 candidate 기준 기록이다.
- 다시 돌린 결과: Worker smoke total=590 failed=0, Discord self-check ok 109, validator PASS(negative_checks 172, 실패 0).
