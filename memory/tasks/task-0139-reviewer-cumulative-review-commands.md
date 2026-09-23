# task-0139-reviewer-cumulative-review-commands

- id: `task-0139-reviewer-cumulative-review-commands`
- title: `Reviewer 허용 명령에 baseline 누적 diff·commit 범위·candidate 시점 파일 읽기와 evidence path를 추가`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-09-23 17:20 UTC`
- updated_at: `2026-09-23 17:20 UTC`
- summary: `task-0135 후속. Reviewer가 candidate의 마지막 commit만 볼 수 있어 누적 범위와 근거 확인을 매번 QA로 넘기던 제한을 줄이기 위해, 두 Reviewer 정의에 baseline 전체 hash 기준 누적 diff와 commit 범위, candidate 시점 파일 읽기, Manager가 준 evidence path 읽기를 같은 문구로 추가하고 작업 트리 직접 읽기 금지를 명시한다. validator는 새 필수 문구를 검사하고 Skill 호출문에 baseline 전체 hash와 evidence path 칸을 둔다. DONE은 Reviewer/QA 후 Owner가 Console Complete로 결정한다.`
- source_command: `Owner 지시: task-0135 후속 Reviewer 허용 명령 개선을 read-only 조사의 최소 변경안으로 task-0139에서 진행`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `e7dfa1a9e3b293de33ec983ac560ad7e5d8f8be3` (`origin/main`과 같음) |
| 작업 전 상태 | tracked 수정 없음, untracked `jarvis.bat`만 |
| validator | `python -B scripts/validate_multi_agent_sop.py` → `negative_checks=72`, `negative_failures=0`, `status=PASS` |

## 문제 (read-only 조사 결과)

- 두 Reviewer 정의의 diff 형식은 `git diff <hash>^ <hash>`뿐이라 baseline부터 candidate까지의 누적 변경과
  commit 범위를 Reviewer가 확인할 수 없었다.
- `git show <hash>:<path>`가 없어 candidate 시점 파일 전체를 읽을 수 없었다(task-0135의 큰 diff 문제).
- `git grep`은 scope 파일에만 허용돼 task 기록 같은 근거 파일을 hash에 묶어 읽을 수 없었고, Reviewer는
  Read 도구로 작업 트리를 읽은 뒤 그 사실을 finding으로 밝혀 왔다.
- `jarvis-reviewer-call` Skill의 사전 확인은 `git diff --name-status <baseline> <hash>`로 전체 변경 범위를
  계산하지만 Reviewer는 그 명령을 재현할 수 없었다.
- 2026-09-23 Studyroom 작업(task-0138)에서 이 제한 때문에 누적 확인과 근거 대조가 반복적으로 QA로 넘어갔다.

## Owner 승인 원문

```text
task-0139로 진행해.

이번 범위는 방금 read-only 조사에서 제안한 최소 변경안으로 한정한다.

포함:
- .claude/agents/reviewer.md
- .codex/agents/reviewer.toml
- scripts/validate_multi_agent_sop.py
- .claude/skills/jarvis-reviewer-call/SKILL.md
- memory/tasks/task-0139-*.md

핵심 변경:
- baseline 전체 hash 기준 누적 diff 확인 허용
- baseline..candidate commit 범위 확인 허용
- candidate 시점 파일 읽기(git show) 허용
- Manager가 제공한 evidence path를 git show/git grep 대상으로 허용
- 작업 트리 직접 Read 금지 규칙 명시
- 기존 금지 규칙과 BLOCKED 규칙은 유지
- 두 Reviewer 정의의 규칙은 동일하게 유지

이번 task에서는 Claude Reviewer의 Read/Grep/Glob 도구 자체를 제거하지 않는다.

먼저 task-0139를 DOING으로 만들고 구현한 뒤,
validator + mutation negative check + git diff --check를 실행해.
Reviewer와 QA까지 진행하되, 각 단계 결과는 PASS/FINDINGS와 핵심 내용만 보고해.

Codex Reviewer의 실제 동작 검증은 환경상 불가능하므로 억지로 시도하지 말고 한계로 기록해.
```

## Manager 요약 (승인 원문 조건별)

| # | 승인 원문 조건 | 이 task에서의 처리 |
| --- | --- | --- |
| 1 | "task-0139로 진행해." | 이 기록 |
| 2 | "이번 범위는 방금 read-only 조사에서 제안한 최소 변경안으로 한정한다." | 조사 보고의 3절(최소 변경안) 1~5만 구현. 선택안(도구 제거)은 제외 |
| 3 | "포함:" 파일 5개 | 아래 5개 파일만 변경 |
| 4 | "baseline 전체 hash 기준 누적 diff 확인 허용" | `git diff --name-status <baseline> <hash>`, `git diff <baseline> <hash> -- <path>` 형식 추가. `<baseline>`은 Manager가 준 40자 전체 hash만 |
| 5 | "baseline..candidate commit 범위 확인 허용" | `git log --format=<format> <baseline>..<hash>` 형식 추가 |
| 6 | "candidate 시점 파일 읽기(git show) 허용" | `git show <hash>:<path>` 형식 추가. `<path>`는 scope 파일 또는 evidence path |
| 7 | "Manager가 제공한 evidence path를 git show/git grep 대상으로 허용" | evidence path 정의 문단 추가, `git grep` 경로 조건에 evidence path 포함 |
| 8 | "작업 트리 직접 Read 금지 규칙 명시" | scope 파일과 evidence path는 candidate hash에 묶인 git 형식으로만 읽고 작업 트리를 파일 읽기 도구로 직접 읽지 않는다는 문단 추가 |
| 9 | "기존 금지 규칙과 BLOCKED 규칙은 유지" | 기존 형식·금지 문구·BLOCKED 절 무변경 |
| 10 | "두 Reviewer 정의의 규칙은 동일하게 유지" | 두 파일에 같은 문구로 추가. 본문 차이는 기존 실행 방식 한 문장뿐 |
| 11 | "이번 task에서는 Claude Reviewer의 Read/Grep/Glob 도구 자체를 제거하지 않는다." | `.claude/agents/reviewer.md`의 `tools:` 줄 무변경 |
| 12 | "먼저 task-0139를 DOING으로 만들고 구현한 뒤," | status `DOING` |
| 13 | "validator + mutation negative check + git diff --check를 실행해." | 검증 절에 기록 |
| 14 | "Reviewer와 QA까지 진행하되, 각 단계 결과는 PASS/FINDINGS와 핵심 내용만 보고해." | Owner 보고 형식 |
| 15 | "Codex Reviewer의 실제 동작 검증은 환경상 불가능하므로 억지로 시도하지 말고 한계로 기록해." | 한계 절에 기록 |

## 변경

| 파일 | 변경 |
| --- | --- |
| `.claude/agents/reviewer.md` | Allowed commands 절에 형식 4개, baseline 문단, evidence path 문단, 작업 트리 직접 읽기 금지 문단 추가. `git grep` 경로 조건에 evidence path 포함 |
| `.codex/agents/reviewer.toml` | 같은 문구를 같은 위치에 추가 |
| `scripts/validate_multi_agent_sop.py` | `REVIEWER_ROLE_CLAUSES`에 새 필수 문구 추가. 기존 negative 루프가 새 문구마다 두 파일 삭제 사본을 만든다 |
| `.claude/skills/jarvis-reviewer-call/SKILL.md` | 입력 표에 evidence path 행, 호출문 템플릿에 baseline 전체 hash 표기와 evidence path 목록 추가 |
| 이 기록 | 신규 |

## 검증 (Implementer 실행, QA 재현 대상)

| # | 항목 | 결과 |
| --- | --- | --- |
| V1 | `python -B scripts/validate_multi_agent_sop.py` | `negative_checks=80`, `negative_failures=0`, `status=PASS` (새 필수 문구 4개 × 두 파일 = negative 8개 증가) |
| V2 | 외부 mutation: 추적 파일 임시 사본에서 새 문구 4개를 두 파일에서 하나씩 지우기 | 8/8 검출, 무변형 사본 PASS |
| V3 | 두 정의 본문 대조 | 차이는 기존 실행 방식 한 줄뿐 ("each through the Bash tool" 대 "each as a shell command in the read-only sandbox") |
| V4 | `git diff --check` | exit 0 |
| V5 | `.codex/agents/reviewer.toml` TOML 파싱 | 정상 |

## 한계

- Codex Reviewer(`.codex/agents/reviewer.toml`)의 실제 동작은 이 환경에 Codex agent 호출 수단이 없어 검증하지
  않는다. 정의 문구와 validator 검사로만 확인한다.
- Claude Reviewer의 Read/Grep/Glob 도구는 남아 있으므로 작업 트리 직접 읽기 금지는 정의 문구로만 강제된다.
  실행 단계 강제는 이번 범위 밖이다.

## Repair 이력

retry_budget=1, retry_count=0, repair_budget=1, repair_count=0
