# task-0185-studyroom-app-kind

- id: `task-0185-studyroom-app-kind`
- title: `Worker 작업 종류: Studyroom 앱 전체`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-22 17:09 UTC`
- updated_at: `2026-10-23 05:26 UTC`
- summary: `Worker 작업 종류 studyroom_content의 허용 경로를 apps/studyroom/content/에서 Studyroom 앱 전체 apps/studyroom/으로 넓힌다. 앱 실행 스크립트 apps/studyroom/studyroom.bat은 보호 경로에 더해 Worker가 바꾸지 못하게 하고, Worker 지시에 네트워크·외부 API·새 의존성 금지와 로컬 서버 127.0.0.1 유지를 적는다. 종류 이름·표지어·테스트는 그대로다.`
- source_command: `Owner 지시: 작업 종류 늘리기, Studyroom 앱 전체 선택 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `d8a341f408cccab15c9c969959be4715de058b57` (등록 시점 main HEAD, task-0184 push 완료) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=1` (SOP §5 기본값, 사용 내역은 Repair 절) |

## Owner 결정 (원문)

```text
[Manager 제안]
남은 결정
1. task-0184 커밋 3개를 push할지
2. 다음 단계: (b) 작업 종류 늘리기, 또는 (c) 낮은 위험 작업 자동 시작과 일일 보고. (c)는 무인 실행 잠금(master-plan §6)을 푸는 결정이 필요합니다.

[Owner 답]
push하고 작업 종류 늘리기 진행해

[Manager 질문]
Worker가 새로 작업할 수 있게 할 앱을 골라 주세요. (Jarvis Console은 task 상태와 승인을 다루는 코드라 후보에서 뺐습니다)
- Studyroom 앱 전체 (권장): 지금은 apps/studyroom/content/만 됩니다. 앱 코드까지 넓힙니다. 테스트 1초, 외부 연결 없음, 위험 낮음.
- Research Council (권장): apps/research-council/. 테스트 25초. 단 OpenRouter API 호출 코드(openrouter_advisor.py)가 있어, 그 파일은 Worker가 못 바꾸게 막고 네트워크·API 추가 금지 규칙을 넣습니다.
- Hermes Manager Pilot: apps/hermes-manager-pilot/. 테스트 64초. 승인 바인딩·증거 수집 같은 관리용 코드가 있어 위험이 중간입니다.

[Owner 답]
Studyroom 앱 전체 (권장)
```

## Owner 결정 2: validator 음성 테스트 한 줄 (원문)

```text
[Manager 질문]
결정이 필요한 것: validator 한 줄 (범위 밖)
- validator scripts/validate_multi_agent_sop.py의 음성 테스트 하나가 SOP 표의 옛 문구 `apps/studyroom/content/`(studyroom_content)를 그대로 찾습니다.
- 고치는 방법은 테스트가 찾는 문구 한 줄을 `apps/studyroom/`(studyroom_content)로 바꾸는 것입니다. 검사의 의미(경로를 바꾸면 잡아내는지)는 그대로입니다.
1. (권장) validator의 그 한 줄을 이번 범위에 넣어 고치고, self-review → candidate → Reviewer → QA → 완료까지 진행합니다.
2. 범위를 넓히지 않고 task-0185를 멈춥니다.

[Owner 답]
1번으로 진행해
```

## 설계

1. `studyroom_content`의 `allowed_prefix`를 `apps/studyroom/`으로 바꾼다. 종류 이름·표지어(studyroom·스터디룸)·테스트(`apps/studyroom/run_smoke_tests.py`)·기본 종류 지위는 그대로라 기존 기록·감사·`/go` 판정과 맞는다.
2. `PROTECTED_PATHS`에 `apps/studyroom/studyroom.bat`(앱 실행 스크립트)을 더해, 허용 경로 안이어도 Worker 변경을 범위 위반으로 막고 Reviewer 증거에서도 뺀다.
3. Worker 지시(`prompt_note`): 기존 JSON 형식 규칙에 더해, 앱 구조와 코드 스타일 유지, smoke test 통과, 네트워크·외부 API·LLM·새 의존성 금지, 로컬 서버는 127.0.0.1에만 묶어 둔다.
4. 다른 종류(Daily AI Radar)와 팀장·`/go`·QA 로직은 바꾸지 않는다. 팀장 프롬프트는 등록된 종류 목록을 그대로 읽으므로 새 경로가 자동 반영된다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/worker/claude_worker.py`(`WORK_KINDS`의 studyroom 항목과 `PROTECTED_PATHS`만), `orchestrator/worker/run_smoke_tests.py`, `adapters/discord/bot_minimal.py`(self-check의 기대값만), `adapters/discord/README.md`, `docs/jarvis-multi-agent-sop-v0.1.md`(§10.1 표), `scripts/validate_multi_agent_sop.py`(Owner 결정 2: 음성 테스트 `pipeline_scope_prefix_changed`가 찾는 SOP 문구 한 줄만), `memory/tasks/task-0185-studyroom-app-kind.md` |
| deny | `jarvis.bat`, `apps/`(앱 자체는 바꾸지 않음), Worker의 판정·repair·QA·반영 로직, 팀장 코드, writer·Console, AGENTS·agent 정의, 다른 task 기록, 외부 API·credential, 보호 worktree |

## 계획

1. 레지스트리와 보호 경로 변경.
2. 검사: 앱 코드(예: `apps/studyroom/web/app.js`) 변경은 허용되고, `studyroom.bat` 변경과 앱 밖 변경은 범위 위반, 지시에 새 금지 규칙이 있음. 기존 기대값(허용 경로) 갱신.
3. 문서: SOP §10.1 표(validator가 코드와 맞춰 봄), Discord README.
4. 사전 점검 → self-review → candidate → Reviewer → QA → Evidence·Complete(Manager, G3와 같게) → checkpoint. push는 별도 승인.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-22 17:09 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다.

## 구현

- `orchestrator/worker/claude_worker.py`: `WORK_KINDS`의 `studyroom_content` 항목 `allowed_prefix`를 `apps/studyroom/`으로 바꾸고, `prompt_note`에 앱 코드 규칙(기존 구조·스타일 유지, smoke test 통과, 네트워크·외부 API·LLM·새 의존성 금지, 로컬 서버 127.0.0.1 유지, `apps/studyroom/studyroom.bat` 변경 금지)을 더했다. `PROTECTED_PATHS`에 `apps/studyroom/studyroom.bat`을 더했다. 다른 로직은 바꾸지 않았다. Reviewer 호출문의 파이프라인 한계 문장("none is jarvis.bat")과 `source_evidence_paths` docstring은 범위 밖이라 `jarvis.bat`만 적힌 채로 두었다. `studyroom.bat` 변경은 그보다 앞선 scope 단계에서 막힌다(검사로 확인).
- `orchestrator/worker/run_smoke_tests.py`: 가짜 Worker 모드 두 개(`studyroombat`: 실행 스크립트 수정, `appcode`: `apps/studyroom/web/app.js` 수정)와 검사를 더했다. 실행 스크립트 수정은 scope 단계 `scope_violation`으로 멈추고 그 파일 이름이 사유에 나오며, 앱 코드 수정은 Reviewer·QA·main 반영까지 DONE이고, Worker 지시에 새 규칙이 있다. 팀장 계획의 허용 경로 표시 기대값을 새 경로로 바꿨다.
- `adapters/discord/bot_minimal.py`: self-check의 작업 종류 레지스트리 기대값만 새 경로로 바꿨다.
- `scripts/validate_multi_agent_sop.py`(Owner 결정 2): 음성 테스트 `pipeline_scope_prefix_changed`가 찾는 SOP 문구를 새 표 문구로 바꿨다. 변조 문구(`apps/other/`)와 기대 오류 코드는 그대로다.
- 문서: SOP §10.1 표의 지원 작업·허용 경로·보호 경로 행, Discord README의 `/work`·`/go` 절 머리말.

## Implementer 검증 (작업 트리)

- Worker smoke total=556 failed=0(이전 545에 11개), Discord self-check ok 109, SOP validator PASS(negative_checks 172, 실패 0).
- 사전 점검(`check_task_record`, baseline `d8a341f`): status=PASS, staged_files 7, violations 0.

## Self-review

candidate 전 1회. minor 3건을 반영했다: 사전 점검 결과를 적었고, A2에 Manager의 추가 안전 제한과 그 근거를 밝혔고, 범위 밖이라 `jarvis.bat`만 적힌 채 남은 두 문구와 그래도 scope 단계에서 막힌다는 점을 구현 절에 적었다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 제안]" / "남은 결정" / "1. task-0184 커밋 3개를 push할지" / "2. 다음 단계: (b) 작업 종류 늘리기, 또는 (c) 낮은 위험 작업 자동 시작과 일일 보고. (c)는 무인 실행 잠금(master-plan §6)을 푸는 결정이 필요합니다." / "[Owner 답]" / "push하고 작업 종류 늘리기 진행해" | task-0184 커밋 3개를 이 task 등록 전에 push했다(`8616f02..d8a341f`). (b)를 진행했고 (c)는 하지 않았다 |
| A2 | Owner 결정 (원문) | "[Manager 질문]" / "Worker가 새로 작업할 수 있게 할 앱을 골라 주세요. (Jarvis Console은 task 상태와 승인을 다루는 코드라 후보에서 뺐습니다)" / "- Studyroom 앱 전체 (권장): 지금은 apps/studyroom/content/만 됩니다. 앱 코드까지 넓힙니다. 테스트 1초, 외부 연결 없음, 위험 낮음." / "[Owner 답]" / "Studyroom 앱 전체 (권장)" | 기존 `studyroom_content`의 허용 경로를 `apps/studyroom/`으로 넓혔다. 실행 스크립트 보호, 127.0.0.1 고정, 네트워크·외부 API·LLM·새 의존성 금지는 Owner 원문에 없는 Manager의 추가 안전 제한이다. `studyroom.bat`은 `jarvis.bat`과 같은 이유(실행 스크립트)로 막았고, 나머지는 원문의 "외부 연결 없음"이 넓힌 뒤에도 유지되게 하려는 것이다 |
| A3 | Owner 결정 (원문) | "- Research Council (권장): apps/research-council/. 테스트 25초. 단 OpenRouter API 호출 코드(openrouter_advisor.py)가 있어, 그 파일은 Worker가 못 바꾸게 막고 네트워크·API 추가 금지 규칙을 넣습니다." / "- Hermes Manager Pilot: apps/hermes-manager-pilot/. 테스트 64초. 승인 바인딩·증거 수집 같은 관리용 코드가 있어 위험이 중간입니다." | Owner가 고르지 않았으므로 두 앱은 열지 않았다 |
| A4 | Owner 결정 2: validator 음성 테스트 한 줄 (원문) | "[Manager 질문]" / "결정이 필요한 것: validator 한 줄 (범위 밖)" / "- validator scripts/validate_multi_agent_sop.py의 음성 테스트 하나가 SOP 표의 옛 문구 `apps/studyroom/content/`(studyroom_content)를 그대로 찾습니다." / "- 고치는 방법은 테스트가 찾는 문구 한 줄을 `apps/studyroom/`(studyroom_content)로 바꾸는 것입니다. 검사의 의미(경로를 바꾸면 잡아내는지)는 그대로입니다." / "1. (권장) validator의 그 한 줄을 이번 범위에 넣어 고치고, self-review → candidate → Reviewer → QA → 완료까지 진행합니다." / "2. 범위를 넓히지 않고 task-0185를 멈춥니다." / "[Owner 답]" / "1번으로 진행해" | validator에서는 그 한 줄만 바꿨다. 변조 문구와 기대 오류는 그대로이고 음성 테스트 172개가 모두 오류를 잡는다 |

## Repair

- candidate `b71250f134f871600d668572ffe219465933d599`: Reviewer FINDINGS(유효, self_deviations 0), minor 1건: Daily AI Radar Worker 지시에 Studyroom 경로가 섞이지 않는지 보는 기존 검사(`orchestrator/worker/run_smoke_tests.py`)가 옛 경로 `apps/studyroom/content/`를 찾고 있어 새 경로가 섞여도 잡지 못했다. 구현 절은 허용 경로 기대값을 새 경로로 바꿨다고 했는데 이 한 곳이 빠졌다.
- repair 1(`repair_count=1`, 기본 예산 안): 그 검사가 `apps/studyroom/`을 찾도록 바꿨다. 다른 것은 바꾸지 않았다.
