# task-0203-fix-pilot-tools

- id: `task-0203-fix-pilot-tools`
- title: `파일럿 도구 A1·A4 정식 절차 고정`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-27 13:25 UTC`
- updated_at: `2026-10-27 13:28 UTC`
- summary: `SOP 경량화 파일럿(task-0197) 3건 뒤 Owner 결정에 따라 A1(요약 표 생성)과 A4(커밋 보호)를 정식 절차로 고정한다. SOP Manager 절의 사전 점검을 미인용 0 필수(--require-quotes)로, candidate와 repair candidate 커밋을 commit_candidate.py로만 하도록, Manager 요약 표는 --emit-table 뼈대로 만들도록 바꾸고 파일럿 측정 의무는 끝낸다. self-review와 Reviewer 호출 skill의 사전 점검 명령도 같은 옵션으로 맞춘다. 코드는 바꾸지 않는다.`
- source_command: `Owner 지시: A1·A4 정식 절차 고정 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `d1987222e81dd9278583c33b505f73508e0d961a` (등록 시점 main HEAD, task-0202 checkpoint까지 push 완료) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문)

```text
[Manager 보고: task-0201 완료 뒤]
2. 파일럿 두 도구(요약 표 자동 생성, 점검 통과 때만 커밋하는 커밋 보호)를 정식 절차로 고정할지 정해 주세요.

[Owner 답]
d198722 push를 승인하고, A1·A4도 정식 절차로 고정한다
```

## 조사 (등록 전)

- 파일럿 규칙은 SOP Manager 절의 "파일럿(task-0197)" 항목 하나에만 있다. 그 위 사전 점검 항목은 `check_task_record.py`를 옵션 없이 필수로 두고, 승인 원문 인용 목록은 종료 코드에 영향을 주지 않는다고 적는다.
- 파일럿 3건(task-0198, 0199, 0201)의 측정과 비교는 task-0201 기록의 "파일럿 3건 비교" 절에 있다.
- `.claude/skills/jarvis-self-review/SKILL.md`와 `.claude/skills/jarvis-reviewer-call/SKILL.md`의 사전 점검 명령은 `--require-quotes` 없이 `check_task_record.py`를 부른다. validator는 이 명령 문자열을 검사하지 않는다(`scripts/validate_multi_agent_sop.py`에 해당 문자열 없음).
- 두 도구의 코드(`scripts/commit_candidate.py`, `check_summary_quotes.py --emit-table`, `check_task_record.py --require-quotes`)는 task-0197·0198에서 이미 검사와 함께 들어와 있다.

## 설계

1. SOP Manager 절:
   - 사전 점검 항목: 명령을 `python -B scripts/check_task_record.py memory/tasks/<task-id>.md --baseline <baseline> --require-quotes`로 바꾸고, Owner 원문 문장이 Manager 요약에 그대로 인용되지 않으면 위반(종료 코드 0이 아님)이라고 적는다(task-0203). 이 검사가 Reviewer의 조건 대조를 대신하지 않는다는 문장은 둔다.
   - 파일럿 항목을 정식 항목으로 바꾼다: Manager 요약 표는 `check_summary_quotes.py --emit-table <기록>`의 뼈대로 만들고 해석 칸만 채운다(A1). candidate와 repair candidate는 `commit_candidate.py --record <기록> --baseline <baseline> --message-file <파일> --require-quotes`로만 커밋하고, 직접 `git commit`으로 candidate를 만들지 않는다(A4). 파일럿 측정 의무는 끝났다고 적고, 측정 결과 위치(task-0201 기록)를 남긴다.
2. 두 skill의 사전 점검 명령에 `--require-quotes`를 더한다. Reviewer 호출 skill에는 그 점검이 PASS면 인용 목록이 비어 있다는 구절을 더한다(self-review 4). 그 밖의 skill 내용은 바꾸지 않는다.
3. 코드, validator, agent 정의, Reviewer 판정 기준은 바꾸지 않는다. `check_task_record.py`의 docstring과 주석에 남은 "task-0197 pilot"·"advice only unless --require-quotes" 표기는 코드가 deny 범위라 그대로 두며, 옵션 동작은 같다. DONE checkpoint와 master-plan 커밋은 이번 규칙의 대상(candidate)이 아니므로 그대로 둔다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `docs/jarvis-multi-agent-sop-v0.1.md`(Manager 절의 사전 점검·파일럿 항목만), `.claude/skills/jarvis-self-review/SKILL.md`(사전 점검 명령만), `.claude/skills/jarvis-reviewer-call/SKILL.md`(사전 점검 명령과 그 바로 뒤 인용 목록 문장만), `memory/tasks/task-0203-fix-pilot-tools.md` |
| deny | `jarvis.bat`, 코드 전부(`scripts/`, `orchestrator/`, `adapters/`, `apps/`), validator, AGENTS, agent 정의(`.claude/agents/`, `.codex/agents/`), 다른 task 기록, 외부 API·credential, 봇·작업 스케줄러 |

## 계획

1. 문서 수정.
2. 검사: validator PASS, 세 스크립트 `--self-test` PASS, 이 기록에 `--require-quotes` 사전 점검 PASS, 두 skill의 명령이 실제로 실행 가능(옵션 인식).
3. 사전 점검 → self-review → candidate(`commit_candidate.py --require-quotes`) → Reviewer → QA → Evidence·Complete → checkpoint → master-plan. push는 별도 지시.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-27 13:25 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다.

## 구현

- `docs/jarvis-multi-agent-sop-v0.1.md` Manager 절: 사전 점검 항목의 명령에 `--require-quotes`를 더하고 미인용 Owner 원문 문장을 위반 목록에 넣었다("종료 코드에 영향을 주지 않는다" 문장을 뺌). 파일럿 항목을 두 정식 항목으로 바꿨다: 요약 표는 `--emit-table` 뼈대(A1), candidate와 repair candidate는 `commit_candidate.py --require-quotes`로만 커밋하고 직접 `git commit`으로 만들지 않음(A4). 파일럿 측정 의무가 끝났다는 것과 측정 결과 위치(task-0201 기록)를 적었다.
- `.claude/skills/jarvis-self-review/SKILL.md`, `.claude/skills/jarvis-reviewer-call/SKILL.md`: 사전 점검 명령에 `--require-quotes`. Reviewer 호출 skill에는 PASS면 인용 목록이 비어 있다는 구절.
- SOP의 근거 표시는 "task-0197 파일럿의 A1 요약 표 생성", "task-0197 파일럿의 A4 커밋 보호"로 풀어 썼다. 기록 요약 표의 행 번호 A1~A4와는 다른 이름이다.

## Implementer 검증 (작업 트리)

- SOP validator PASS. `check_task_record.py`, `commit_candidate.py`, `check_summary_quotes.py`의 `--self-test` 모두 PASS(코드는 바꾸지 않음).
- 이 기록의 사전 점검을 두 skill과 같은 명령 `python -B scripts/check_task_record.py memory/tasks/task-0203-fix-pilot-tools.md --baseline d1987222e81dd9278583c33b505f73508e0d961a --require-quotes`로 실행해 staged 4, violations 0, 미인용 0, status=PASS(종료 코드 0). 옵션은 인식되며, 미인용 문장이 있으면 위반이 되는 것은 `check_task_record.py --self-test`의 해당 검사가 확인한다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 보고: task-0201 완료 뒤]" | 보고의 표지. 해석할 조건이 아니다 |
| A2 | Owner 결정 (원문) | "파일럿 두 도구(요약 표 자동 생성, 점검 통과 때만 커밋하는 커밋 보호)를 정식 절차로 고정할지 정해 주세요." | 질문 원문. 답은 A4 |
| A3 | Owner 결정 (원문) | "[Owner 답]" | Owner 답의 표지. 해석할 조건이 아니다 |
| A4 | Owner 결정 (원문) | "d198722 push를 승인하고, A1·A4도 정식 절차로 고정한다" | d198722 push는 이 task 전에 했다(`a31762c..d198722`). 도구 A1(요약 표 뼈대)과 A4(커밋 보호)(task-0197 파일럿 명칭)를 SOP Manager 절의 정식 항목으로 바꿨다. 다음은 Manager 해석이다: A4가 미인용 0일 때만 커밋하므로 그 앞 사전 점검(`check_task_record.py`)도 같은 기준(`--require-quotes`)으로 올렸고, 같은 사전 점검을 쓰는 두 skill의 명령도 맞춰 SOP와 skill이 갈리지 않게 했다 |

## Self-review

candidate 전 1회(사전 점검 `--require-quotes` PASS 뒤). 지적 5건(모두 minor)을 반영했다.

1. SOP의 "(task-0203, A1)", "(task-0203, A4)"가 무엇을 가리키는지 SOP 안에서 알 수 없었고, 기록 요약 표의 행 번호와 헷갈렸다. 도구 이름으로 풀어 쓰고 요약 행에 "task-0197 파일럿 명칭"을 밝혔다.
2. 계획 2의 `--require-quotes` 사전 점검 결과가 검증 절에 없었다. 명령 전체와 결과를 적었다.
3. 사전 점검 기준을 올린 것도 Manager 해석인데 해석 표시가 skill 변경에만 붙어 있었다. 요약 행 A4를 고쳤다.
4. Reviewer 호출 skill의 인용 목록 설명이 `--require-quotes` 뒤에는 늘 빈 목록이 된다는 점과 맞지 않았다. 한 구절을 더하고 owned 범위를 그 문장까지 넓혔다.
5. `check_task_record.py`의 "pilot" 주석이 SOP와 어긋난다. 코드가 deny 범위라 그대로 둔다고 설계 3에 적었다.

- 고친 뒤: SOP validator PASS, 세 스크립트 `--self-test` PASS.
- self-review 사용량(API 환산 추정): 약 $0.32, 63초.
