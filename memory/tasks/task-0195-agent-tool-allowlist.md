# task-0195-agent-tool-allowlist

- id: `task-0195-agent-tool-allowlist`
- title: `에이전트 호출 도구 명시 목록`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-24 14:16 UTC`
- updated_at: `2026-10-24 14:26 UTC`
- summary: `Worker, Reviewer, 팀장의 claude 호출이 쓸 수 있는 도구를 명시 목록으로 줄인다. 지금은 --allowedTools가 묻지 않고 허용할 도구만 정하고 다른 도구를 숨기지 않아, 실험에서 Worker에게 33개 도구(Task, CronCreate, RemoteTrigger, PushNotification, claude.ai Docs MCP 등)가 보였다. 호출마다 --tools로 기본 도구를 정하고 --strict-mcp-config로 MCP 서버를 빼서 Worker 5개, Reviewer 4개, 팀장 3개만 보이게 한다.`
- source_command: `Owner 지시: Worker 도구 범위 보강 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `ac912fb02d42deb7ef05c47a5712d9f5ab45ba17` (등록 시점 main HEAD, task-0194까지 push 완료) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문)

```text
[Manager 보고: stream-json 실험의 안전 관련 발견]
실험 1에서 `--allowedTools Read,Glob`만 줬는데도 시작 이벤트의 도구 목록에는 23개가 보였습니다. 이 PC의 Claude 환경에 연결된 `Task`, `CronCreate`, `RemoteTrigger`, `PushNotification`, `Artifact` 같은 도구입니다.
이유는 이렇습니다. `--allowedTools`는 "묻지 않고 허용할 도구" 목록이고, 다른 도구를 숨기지는 않습니다. 도구를 빼는 것은 `--disallowedTools`입니다.
지금 Worker는 `--allowedTools Read,Edit,Write,Glob,Grep`에 `--disallowedTools Bash,NotebookEdit,WebFetch,WebSearch`만 씁니다. 그래서 Worker에게도 이 도구들이 보일 가능성이 큽니다.
비대화형 실행에서는 허용 목록 밖 도구가 승인 없이 거절될 것으로 보이지만, 실제로 확인하지는 않았습니다.
권장하는 보강은 Worker·팀장·Reviewer 호출에 쓸 도구만 명시하는 것입니다. self-review가 이미 `--tools Read,Grep,Glob`로 그렇게 하고 있습니다. 작은 별도 task로 하는 것이 좋겠습니다.

다음 권장 순서
1. Worker 도구 범위 확인과 보강 (작은 task): 지금 Worker에게 보이는 도구를 확인하고, 호출을 명시 목록으로 바꿉니다. 안전 문제라 먼저 하길 권합니다.

[Owner 답]
1번 Worker 도구 범위 보강 진행해
```

## 조사 (등록 전, 저장소 밖 임시 폴더)

- 지금 Worker 호출(`--permission-mode acceptEdits --allowedTools Read,Edit,Write,Glob,Grep --disallowedTools Bash,NotebookEdit,WebFetch,WebSearch`)의 시작 이벤트 도구 목록은 33개였다: 허용한 5개 외에 Task, Artifact, ArtifactComments, ArtifactData, CronCreate, CronDelete, CronList, DesignSync, EnterWorktree, ExitWorktree, ListAgents, Monitor, PushNotification, RemoteTrigger, ReportFindings, ScheduleWakeup, SendMessage, Skill, TaskStop, ToolSearch와 claude.ai Claude Docs MCP 도구 8개.
- `--tools Read,Edit,Write,Glob,Grep`만 더하면 13개(기본 도구는 5개로 줄지만 MCP 도구 8개가 남음), `--strict-mcp-config`까지 더하면 정확히 5개였고 답은 정상이었다.
- 같은 방식으로 Reviewer(`--agent reviewer --tools Read,Grep,Glob,Bash --strict-mcp-config`)는 4개, 팀장(`--permission-mode plan --tools Read,Grep,Glob --strict-mcp-config`)은 3개였고 둘 다 정상 응답했다.
- 이 실험은 허용 목록 밖 도구를 실제로 부르게 하지는 않았다. 지금 설정에서 그 도구들이 비대화형 실행에서 거절되는지는 확인하지 않았고, 이 task는 그 확인 대신 도구를 아예 보이지 않게 한다.

## 설계

1. `orchestrator/worker/claude_worker.py`: Worker 호출에 `--tools`(Read, Edit, Write, Glob, Grep)와 `--strict-mcp-config`를, Reviewer 호출에 `--tools`(Read, Grep, Glob, Bash)와 `--strict-mcp-config`를 더한다. 기존 `--allowedTools`·`--disallowedTools`·권한 모드는 그대로 둔다(Reviewer의 Bash는 지금처럼 git 읽기 명령 패턴만 묻지 않고 허용된다). 목록은 상수로 둔다.
2. `orchestrator/worker/claude_lead.py`: 팀장 호출에 `--tools`(Read, Grep, Glob)와 `--strict-mcp-config`를 더한다.
3. 판정·repair·QA·반영 로직, 프롬프트, 다른 호출은 바꾸지 않는다.
4. 문서: SOP §10.1이나 README에 세 호출의 도구 목록과 MCP 제외를 적는다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/worker/claude_worker.py`(Worker·Reviewer 호출 인자와 그 상수만), `orchestrator/worker/claude_lead.py`(팀장 호출 인자와 그 상수만), `orchestrator/worker/run_smoke_tests.py`, `adapters/discord/README.md`, `docs/jarvis-multi-agent-sop-v0.1.md`(§10의 해당 문장), `memory/tasks/task-0195-agent-tool-allowlist.md` |
| deny | `jarvis.bat`, `apps/`, 봇 코드, writer·Console, AGENTS·agent 정의(`.claude/agents`, `.codex/agents`), self-review skill, validator(필요하면 보고), 다른 task 기록, 외부 API·credential, 보호 worktree, 작업 스케줄러 |

## 계획

1. 세 호출 변경.
2. 검사: 가짜 claude가 받은 인자에서 세 호출 각각의 `--tools` 목록과 `--strict-mcp-config` 확인, 기존 인자 유지, 기존 파이프라인 검사 전부 통과. 실제 claude로 세 호출 형태의 시작 이벤트 도구 목록 재확인(저장소 밖).
3. 사전 점검 → self-review → candidate → Reviewer → QA → Evidence·Complete(Manager, G3와 같게) → checkpoint. push와 봇 재시작은 별도 지시(봇은 작업 스케줄러 감시 루프로 돌고 있어 `-Stop`·`-Start`로 재시작).

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-24 14:16 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다.

## 구현

- `orchestrator/worker/claude_worker.py`: 상수 `WORKER_TOOLS`(Read,Edit,Write,Glob,Grep)와 `REVIEWER_TOOLS`(Read,Grep,Glob,Bash)를 더했다. Worker 호출 인자 끝에 `--tools WORKER_TOOLS --strict-mcp-config`, Reviewer 호출에 `--tools REVIEWER_TOOLS --strict-mcp-config`를 넣었다(Reviewer는 `--allowedTools` 앞에 두어, 여러 값을 받는 그 인자가 마지막에 오는 기존 모양을 지킴). 다른 인자, 판정·repair·QA·반영 로직은 바꾸지 않았다.
- `orchestrator/worker/claude_lead.py`: 상수 `LEAD_TOOLS`(Read,Grep,Glob)를 더하고 팀장 호출 인자 끝에 `--tools LEAD_TOOLS --strict-mcp-config`를 넣었다.
- `orchestrator/worker/run_smoke_tests.py`: `tool_allowlist_checks` 검사 5개. `_run`을 가로채 세 호출의 인자를 받아, 각 호출의 `--tools` 목록과 `--strict-mcp-config`(그리고 `--mcp-config` 없음), 기존 권한 인자 유지, 묻지 않고 허용하는 도구가 모두 보이는 도구 안에 있는지 본다.
- 문서: SOP §10.1 팀장 문단과 Discord README의 Worker·Reviewer 설명에 도구 목록과 MCP 제외를 적었다.

## Implementer 검증 (작업 트리)

- Worker smoke total=600 failed=0(이전 595에 5개), Discord self-check ok 109, SOP validator PASS.
- 실제 claude(저장소 밖, 읽기만): 코드가 만든 세 호출 인자 그대로(출력 형식만 `stream-json --verbose`로 바꿈) 실행해 시작 이벤트를 봤다. Worker는 Edit·Glob·Grep·Read·Write, Reviewer는 Bash·Glob·Grep·Read, 팀장은 Glob·Grep·Read만 보였고 MCP 서버는 셋 다 0개, 응답은 셋 다 정상이었다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "1. Worker 도구 범위 확인과 보강 (작은 task): 지금 Worker에게 보이는 도구를 확인하고, 호출을 명시 목록으로 바꿉니다. 안전 문제라 먼저 하길 권합니다." / "[Owner 답]" / "1번 Worker 도구 범위 보강 진행해" | 확인: 지금 Worker에게 33개 도구가 보였다(조사 절). 보강: Worker 호출을 명시 목록 5개로 바꿨고 MCP 서버를 뺐다. "작은 별도 task"와 "먼저": task-0194 바로 다음에 따로 등록한 task이고(baseline `ac912fb`), 변경은 호출 인자·상수·smoke 검사·문서 두 문장으로 한정했다 |
| A2 | Owner 결정 (원문) | "권장하는 보강은 Worker·팀장·Reviewer 호출에 쓸 도구만 명시하는 것입니다. self-review가 이미 `--tools Read,Grep,Glob`로 그렇게 하고 있습니다." | 팀장과 Reviewer 호출도 같은 방식으로 바꿨다. self-review skill은 이미 그렇게 하고 있어 바꾸지 않았다 |
| A3 | Owner 결정 (원문) | "비대화형 실행에서는 허용 목록 밖 도구가 승인 없이 거절될 것으로 보이지만, 실제로 확인하지는 않았습니다." | 이 task도 그 거절을 확인하지 않았다. 대신 그 도구들이 아예 보이지 않게 해, 거절에 기대지 않게 했다 |

## Self-review

candidate 전 1회. minor 1건(A1이 "작은 별도 task"와 "먼저" 조건을 해석하지 않음)을 반영해 A1에 한 문장을 더했다. 코드와 문서에는 지적이 없었다. 사전 점검(`check_task_record`, baseline `ac912fb`): status=PASS, staged_files 6, violations 0.
