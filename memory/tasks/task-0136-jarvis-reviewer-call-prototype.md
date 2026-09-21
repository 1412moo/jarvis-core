# task-0136-jarvis-reviewer-call-prototype

- id: `task-0136-jarvis-reviewer-call-prototype`
- title: `Reviewer 호출 절차를 명시 호출 전용 Claude Skill prototype 으로 고정 (jarvis-reviewer-call)`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-09-21 12:08 UTC`
- updated_at: `2026-09-21 12:17 UTC`
- summary: `task-0134·0135 에서 Reviewer 를 13 회 호출하며 같은 5 개 블록(candidate·scope·명령 형식·Manager 요약·Owner 승인 원문)을 매번 손으로 조립했고, 요약이 승인 원문 조건을 빠뜨려 repair 2 회가 발생했다. 이 절차를 명시 호출 전용 Claude Skill prototype 1 개로 고정한다. Owner 가 승인한 범위는 SKILL.md 1 개와 이 기록 1 개뿐이며 helper script, Codex·Gemini 사본, 자동 호출, governance 변경, Reviewer 검증 로직 재구현, commit/push 자동화, 승인·budget·scope 판단 자동화는 제외한다. .claude/skills 를 공식 경로로 확정하는 결정은 하지 않는다.`
- source_command: `Owner 가 승인한 jarvis-reviewer-call prototype 최소 범위 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `b5229c2b38333a02211ab08e14adcf524d778cbb` |
| 작업 전 상태 | tracked 수정 없음, untracked `jarvis.bat` 만 |
| validator | `python -B scripts/validate_multi_agent_sop.py` → `negative_checks=72`, `negative_failures=0`, `status=PASS` |
| 선행 | task-0135 QA PASS 기록 commit (`b5229c2`) |

## 왜 만드는가

task-0134 와 task-0135 에서 Reviewer 를 13 회 호출했다 (사전 확인 3, candidate 리뷰 4, QA 동작 확인 6).
매번 아래 5 개 블록을 손으로 다시 조립했고 문구가 호출마다 조금씩 달라졌다.

| 반복 항목 | 근거 |
| --- | --- |
| candidate hash·parent·commit 구조 | SOP §4 규칙 3·4, task-0135 는 3 commit 에 걸침 |
| file scope | SOP §4 규칙 1 |
| 명령 형식 요구 | task-0134 `git -C`·반복 `-e`, task-0135 `\|` alternation |
| Manager 요약 | SOP §3 Manager "Reviewer assignment 에는 Manager 요약과 함께 Owner 승인 원문을 전달한다" |
| Owner 승인 원문 | 같은 조항, `=== OWNER APPROVAL (verbatim) ===` |

요약이 승인 원문의 조건을 빠뜨린 것이 task-0135 repair 1·2 의 직접 원인이었다.

## Owner 승인 원문

```text
2. `jarvis-reviewer-call` prototype 승인

제안한 prototype 작업을 승인합니다.
다만 범위는 최소화합니다.
이번 prototype에서는:

* `.claude/skills/jarvis-reviewer-call/SKILL.md`
* 필요한 task 기록 1개

만 작성합니다.
이번 범위에서 제외:

* helper script
* Codex/Gemini 사본
* 자동 호출
* governance 변경
* Reviewer 자체 검증 로직 재구현
* commit/push/merge 자동화
* approval/budget/scope 판단 자동화

`SKILL.md`는 명시 호출 전용으로 만들고, 기존 Claude Skill 표준 구조/frontmatter와 `!`cmd` 기반 git 정보 주입을 재사용하세요.
그리고 `.claude/skills/`를 Jarvis의 공식/영구 skill 경로로 확정하는 결정은 아직 하지 않습니다. 이번에는 prototype을 만드는 단계로만 취급하세요.
구현 전에 기존 저장소의 관련 skill 구조와 prototype task 기록 위치를 다시 read-only로 확인하고, 실제 변경에 들어가기 전에 정확한 파일 목록과 변경 범위를 먼저 보고하세요.
계속 진행해주세요.
```

## Manager 요약 (원문 해석)

| # | 조건 | 원문 근거 |
| --- | --- | --- |
| 1 | 만드는 파일은 `.claude/skills/jarvis-reviewer-call/SKILL.md` 와 이 기록 2 개뿐 | "이번 prototype에서는 … 만 작성합니다" |
| 2 | helper script 를 만들지 않는다 | 제외 목록 |
| 3 | Codex·Gemini 사본을 만들지 않는다 | 제외 목록 |
| 4 | 자동 호출을 만들지 않는다. 명시 호출 전용 | 제외 목록, "명시 호출 전용으로 만들고" |
| 5 | governance 를 바꾸지 않는다 | 제외 목록 |
| 6 | Reviewer 의 자체 검증 로직(hash·승인 원문 fail-closed)을 skill 에서 다시 구현하지 않는다 | 제외 목록 |
| 7 | commit·push·merge 자동화를 넣지 않는다 | 제외 목록 |
| 8 | 승인·budget·scope 판단을 자동화하지 않는다 | 제외 목록 |
| 9 | Claude Skill 표준 구조·frontmatter 와 `!`cmd`` git 주입을 재사용한다 | "기존 Claude Skill 표준 구조/frontmatter와 `!`cmd` 기반 git 정보 주입을 재사용하세요" |
| 10 | `.claude/skills/` 를 공식·영구 경로로 확정하지 않는다. prototype 단계로만 취급 | "결정은 아직 하지 않습니다" |
| 11 | 구현 전에 기존 skill 구조와 기록 위치를 read-only 로 확인하고 파일 목록·범위를 먼저 보고한다 | "구현 전에 … 먼저 보고하세요" |

## 구현 전 read-only 확인 (조건 11)

| 확인 | 결과 |
| --- | --- |
| `.gitignore` 의 `.claude` 제외 여부 | 항목 없음. `.claude/agents/reviewer.md` 는 이미 추적 중 |
| validator 의 skill 검사 여부 | 없음. validator 는 `.claude/agents/reviewer.md` 와 `.codex/agents/*.toml`, 문서 3 개만 읽는다 |
| 기존 `skills/*.md` | `repo-bootstrap`, `report-writer` 는 frontmatter 없는 산문 절차 문서. Claude Skill 형식과 다르며 이번에 무변경 |
| task 기록 위치·번호 | `memory/tasks/task-####-slug.md`, 마지막이 task-0135 이므로 task-0136 |
| Console 영향 | Console 은 `memory/tasks` 를 읽으므로 이 기록이 목록에 나타난다. 코드 변경은 없다 |

## 무엇을 만들었나

| 파일 | 내용 |
| --- | --- |
| `.claude/skills/jarvis-reviewer-call/SKILL.md` | frontmatter(`name`, `description`, `argument-hint`, `disable-model-invocation: true`, 읽기 전용 git 만 담은 `allowed-tools`) + 6 단계 절차 |
| `memory/tasks/task-0136-jarvis-reviewer-call-prototype.md` | 이 기록 |

SKILL.md 의 구조:

1. 역할 경계 — Reviewer 도 Owner 도 아니며, 승인·판정·scope·budget·commit 을 건드리지 않는다
2. `!`cmd`` 주입은 **항상 성공하는 두 가지**(`git status --short --branch`, `git log -5`)만 사용한다. hash 에 의존하는 조회는 1 단계에서 실행한다. 잘못된 hash 가 skill 자체를 중단시키지 않고 BLOCKED 보고로 이어지게 하기 위해서다
3. 1 단계 candidate 사실 수집(읽기 전용 git 형식만, `jarvis.bat` 은 tree 목록으로만 확인하고 열지 않는다). 기준 집합은 `<baseline>..<hash>` 이고 candidate 단일 commit diff 는 참고용이다. merge·root commit 에서는 `^` 로 부모를 임의 선택하지 않는다
4. 2 단계 task 기록 읽기(`## 기준선` 의 baseline, 승인된 scope, 승인 원문·요약·budget·repair 이력을 구분해 보관)
5. 3 단계 승인 원문 조건별 대조 — 누락·미지원·축소 표현을 보고만 한다
6. 4 단계 BLOCKED 조건 8 가지 (hash, baseline 부재, scope 경로가 전체 변경 집합에 없음, 전체 변경 집합이 승인 scope 밖으로 넓어짐, 승인 원문 없음, 요약 표 없음, 작업 트리 불일치, `jarvis.bat`)
7. 5 단계 고정 순서 호출문(marker 문구는 Reviewer 정의가 요구하는 그대로, 명령 형식은 Reviewer 정의의 해당 절을 가리키기만 한다)
8. 6 단계 Manager 보고 형식(budget 은 기록된 사실만 표시하고 소진 시 escalation 필요만 알린다)

## 설계 결정과 근거

| 결정 | 이유 |
| --- | --- |
| `disable-model-invocation: true` | 조건 4. Manager 가 `/jarvis-reviewer-call` 로만 호출한다 |
| `allowed-tools` 를 읽기 전용 git 으로 제한 | `allowed-tools` 는 그 턴의 도구를 미리 승인하므로 본문에서 실제 쓰는 명령만 둔다(`status`, `rev-parse`, `log`, `diff`, `ls-tree` + `Read`/`Grep`/`Glob`). 쓰기·push 형식은 없다 |
| scope 검증을 양방향으로 | 단방향(scope ⊆ diff)만 보면 repair candidate 처럼 마지막 commit 이 한 파일만 바꾼 경우 오탐이 난다(실측: `f0af74fe…`). 또 승인 밖 파일이 들어온 방향(task-0132 의 실제 사고 유형)을 놓친다 |
| 명령 형식은 Reviewer 정의를 가리킴 | 같은 문구를 두 곳에 두면 drift 한다. task-0135 가 그 문제를 다룬 task 다 |
| budget 은 사실 보고만 | 승인 범위 제외 항목 8. repair 여부 판단과 증액은 Manager·Owner 영역이다 |
| helper script 없음 | 조건 2. git 조회는 허용 형식으로 충분하고, 스크립트를 넣으면 검증·유지 대상이 하나 늘어난다 |
| Reviewer 의 fail-closed 검증을 재구현하지 않음 | 조건 6. Reviewer 정의가 이미 hash·승인 원문이 없으면 BLOCKED 다. skill 의 preflight 는 Manager 쪽 누락을 먼저 알리는 용도다 |
| Claude 전용 필드 사용 | `disable-model-invocation` 은 Agent Skills 표준 밖의 Claude 확장이다. 이 파일을 그대로 Codex·Gemini 로 옮기면 packaging 검증에서 거부될 수 있다. 사본을 만들지 않는 이번 범위에서는 문제되지 않으며, 옮길 때는 Codex `agents/openai.yaml` 의 `allow_implicit_invocation: false` 로 대응한다 |

## 검증

| # | 항목 | 결과 |
| --- | --- | --- |
| V1 | `python -B scripts/validate_multi_agent_sop.py` | `negative_checks=72`, `negative_failures=0`, `status=PASS` — 기준선과 같다 (validator 는 skill 을 검사하지 않는다) |
| V2 | `git diff --check` | exit 0. 두 파일 모두 신규라 tracked diff 는 비어 있다 |
| V3 | `python -B apps/jarvis-console/run_smoke_tests.py` | self-test passed, smoke tests passed, exit 0 |
| V4 | 변경 범위 | `?? .claude/skills/jarvis-reviewer-call/SKILL.md`, `?? memory/tasks/task-0136-jarvis-reviewer-call-prototype.md` 2 개뿐. tracked 파일 수정 0. `?? jarvis.bat` 는 그대로 |
| V5 | frontmatter 필드 | `name`, `description`, `argument-hint`, `disable-model-invocation`, `allowed-tools` 5 개로 파싱됨. `=== OWNER APPROVAL (verbatim) ===` marker 포함. `!`cmd`` 주입은 `git status --short --branch` 와 `git log -5` 2 개뿐 (196 줄, 8.7KB) |
| V6 | `allowed-tools` 와 본문 명령 일치 | 본문이 쓰는 git 은 `status`, `rev-parse`, `log`, `diff`, `ls-tree` 5 종이고 `allowed-tools` 도 같은 5 종이다. `cat-file` 은 제거했다 |
| V7 | scope 양방향 검사 실측 | task-0135 repair candidate `f0af74fe…` 기준. 단일 commit diff 는 기록 1 파일뿐이지만 `97c775f..f0af74f` 전체 변경 집합은 4 파일이고, `scope − 변경집합` 과 `변경집합 − scope` 가 모두 비어 있다. 수정 전 규칙이었다면 정상 호출이 BLOCKED 됐다 |

## 바꾸지 않은 것

- `.claude/agents/reviewer.md`, `.codex/` 전체, `scripts/validate_multi_agent_sop.py`
- `docs/jarvis-multi-agent-sop-v0.1.md`, master-plan, handoff, 기존 task 기록
- `skills/repo-bootstrap.md`, `skills/report-writer.md`
- Console 코드, `jarvis.bat`

## 후속으로 남긴 것

- `.claude/skills/` 를 Jarvis 공식 skill 경로로 확정할지 (조건 10, Owner 결정)
- validator 가 skill 파일을 검사할지 (현재 검사 없음)
- 저장소의 산문 `skills/*.md` 와 Claude Skill 형식의 관계 정리
- Codex·Gemini 사본과 공통 본문 배선 (필요해질 때)
- skill-creator 의 표준 필드 검사(`quick_validate.py`)를 Jarvis 검증에 넣을지
