# task-0184-nl-lead-call-v02

- id: `task-0184-nl-lead-call-v02`
- title: `팀장 자연어 호출 v0.2`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-22 16:32 UTC`
- updated_at: `2026-10-22 16:41 UTC`
- summary: `Discord 일반 메시지로 팀장을 부르는 v0.2 자연어 연결이다. 메시지가 호출어(자비스, 또는 jarvis, 같은 호출어와 쉼표·콜론, 또는 봇 멘션)로 시작할 때만 호출어를 뗀 본문을 /work 본문으로 바꿔 기존 경로(Owner 권한 검사, 팀장, 원문 보존, 작업 스레드)에 넣는다. 호출어가 없는 대화는 지금처럼 기존 자연어 해석으로 간다. 자연어 해석기 호출 위치 계약은 그대로 지킨다.`
- source_command: `Owner 지시: v0.2 자연어 연결 진행 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `8616f02ad182e561f60d9c1a6b0751aa616dc90a` (등록 시점 main HEAD, push 완료) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |
| 근거 | task-0183 기록의 "후속 작업 (v0.2 후보, Owner 결정 3)" 절(호출 규칙, 원문 보존, 테스트 계약, 비용·안전) |

## Owner 결정 (원문)

```text
[Manager 제안]
남은 결정
1. push: 로컬 커밋 9개(task-0183)를 push할지
2. 다음 단계 (권장 순서)
- (a) v0.2 자연어 지시 연결: task 기록의 "후속 작업" 절에 호출 규칙과 테스트 계약을 정리해 두었습니다.
- (b) 작업 종류 늘리기
- (c) 낮은 위험 작업 자동 시작과 일일 보고: 무인 실행 잠금(master-plan §6)을 해제하는 결정이 필요합니다.

[Owner 답]
push하고 v0.2 자연어 연결 진행해
```

## 설계

1. 호출 규칙: Discord 메시지가 호출어로 시작할 때만 팀장 요청이다. 호출어는 `자비스` 또는 `jarvis`(대소문자 무시) 뒤에 쉼표나 콜론, 또는 이 봇에 대한 멘션이다. 일반 대화는 팀장을 부르지 않는다.
2. 처리: 호출어를 뗀 본문을 `/work <본문>`으로 바꿔 기존 처리에 넣는다. 그 뒤는 `/work`와 같다(Owner 전용 권한 검사, 표지어 있으면 기존 작업 준비, 없으면 팀장, Owner 원문 보존, 작업 스레드). 새 실행 경로를 만들지 않는다. 본문이 비면 `/work` 사용법 오류가 나온다.
3. 우선순위: 호출어가 있으면 기존 자연어 해석(`/status`·`/report`)보다 먼저 판정한다. 호출어가 없으면 기존 해석이 그대로 돈다.
4. 테스트 계약: `orchestrator/discord-nl-intent/run_smoke_tests.py`가 고정한 자연어 해석기 호출 위치(봇 안에서 각 1번, 슬래시 없는 분기 안, 규칙이 못 맞혔을 때만 폴백)를 바꾸지 않는다.
5. 비용·안전: 팀장 실행은 이미 한 번에 하나다. 호출 빈도 제한은 이번에 더하지 않는다(필요하면 별도 결정).

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `adapters/discord/bot_minimal.py`(호출어 판정과 `on_message`의 슬래시 없는 분기, self-check), `orchestrator/worker/run_smoke_tests.py`(필요할 때 검사), `adapters/discord/README.md`, `docs/jarvis-multi-agent-sop-v0.1.md`(§10.1 진입 명령 행과 팀장 문단 앞의 자연어 호출 문단), `memory/tasks/task-0184-nl-lead-call-v02.md` |
| deny | `jarvis.bat`, `orchestrator/discord-nl-intent/`(해석기와 그 테스트는 바꾸지 않음), Worker·팀장 실행 코드, writer·Console, AGENTS·agent 정의, 다른 task 기록, 외부 API·credential, 보호 worktree |

## 계획

1. `_lead_call_body(text, bot_user_id)`: 호출어로 시작하면 본문을, 아니면 None을 돌려준다.
2. `on_message`의 슬래시 없는 분기에서 이 판정을 먼저 하고, 맞으면 `content = "/work " + 본문`, 아니면 기존 자연어 해석을 그대로 탄다.
3. 검사: 호출어 형태별 판정, 일반 대화는 None, 호출어 문장이 `/work`와 같은 결과(팀장 시작과 원문 보존), Owner가 아니면 거부, discord-nl-intent smoke 그대로 통과.
4. 문서: README와 SOP §10.1 팀장 문단.
5. 사전 점검 → self-review → candidate → Reviewer → QA → Evidence·Complete(Manager, G3와 같게) → checkpoint. push는 별도 승인.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-22 16:32 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다.

## 구현

- `adapters/discord/bot_minimal.py`: `LEAD_CALL_PATTERN`과 `_lead_call_body(text, bot_user_id)`를 더했다. 메시지 맨 앞의 `자비스` 또는 `jarvis`(대소문자 무시) 뒤 쉼표·콜론(전각 포함), 또는 이 봇의 멘션(`<@id>`, `<@!id>`)이면 나머지 본문(입력한 `/work`처럼 앞뒤 공백만 정리)을, 아니면 None을 돌려준다. `on_message`의 슬래시 없는 분기에서 이 판정을 먼저 하고, 호출이면 `content = "/work <본문>"`으로 바꿔 기존 권한 검사와 `/work` 경로로 보낸다. 호출이 아니면 기존 `resolve_intent` → `resolve_llm_fallback` 흐름을 그대로 탄다(각 호출은 그 분기 안에 한 번씩). `/help`에 호출 방법 한 줄을 더했다.
- `orchestrator/worker/run_smoke_tests.py`: `call_flow` 검사 6개(호출 형태 14가지 판정, 봇 id 없을 때 멘션 무시, 호출이 `/work`와 같은 결과(팀장 시작과 Owner 원문, 생성 없음), 빈 호출의 사용법 오류, Owner가 아니면 거부, `on_message`에서 호출 판정이 자연어 해석보다 먼저이고 `/work`로 바뀜).
- 문서: SOP §10.1 진입 명령 행과 팀장 문단 앞의 자연어 호출 문단, Discord README `/work` 절.
- 바꾸지 않은 것: `orchestrator/discord-nl-intent/`(해석기와 그 테스트), 팀장·Worker 실행 코드.

## Implementer 검증 (작업 트리)

- Worker smoke total=545 failed=0(이전 539에 6개), Discord self-check ok 109, discord-nl-intent smoke 통과(해석기 호출 위치 구조 검사 포함), Console smoke 통과, SOP validator PASS.
- 사전 점검(`check_task_record`, baseline `8616f02`): status=PASS, violations 0.

## Self-review

candidate 전 1회. minor 2건을 candidate 전에 고쳤다: 호출 본문의 안쪽 공백을 접던 것을 입력한 `/work`처럼 앞뒤만 정리하도록 바꿨고(검사도 맞춤), SOP §10.1 진입 명령 행에 호출 방식을 적고 기록의 범위 표현을 실제 변경 위치에 맞췄다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 제안]" / "남은 결정" / "1. push: 로컬 커밋 9개(task-0183)를 push할지" | task-0183 커밋 9개를 이 task 등록 전에 push했다(`e069fa0..8616f02`). 이 task의 baseline이 그 결과다 |
| A2 | Owner 결정 (원문) | "2. 다음 단계 (권장 순서)" / "- (a) v0.2 자연어 지시 연결: task 기록의 "후속 작업" 절에 호출 규칙과 테스트 계약을 정리해 두었습니다." | task-0183 후속 작업 절의 1~3항(호출어나 봇 멘션만, 원문 보존, 해석기 테스트 계약 유지)을 구현했다. 4항(호출 빈도 제한)은 설계 5항대로 이번에 더하지 않았다(팀장은 이미 한 번에 하나) |
| A3 | Owner 결정 (원문) | "- (b) 작업 종류 늘리기" / "- (c) 낮은 위험 작업 자동 시작과 일일 보고: 무인 실행 잠금(master-plan §6)을 해제하는 결정이 필요합니다." | (b)·(c)는 이번 지시 밖이라 하지 않았다 |
| A4 | Owner 결정 (원문) | "[Owner 답]" / "push하고 v0.2 자연어 연결 진행해" | push 뒤 이 task를 등록하고 Console로 Start했다. 이 task의 push는 별도 승인으로 남긴다 |
