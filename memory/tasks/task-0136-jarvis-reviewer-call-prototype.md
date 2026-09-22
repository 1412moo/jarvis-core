# task-0136-jarvis-reviewer-call-prototype

- id: `task-0136-jarvis-reviewer-call-prototype`
- title: `Reviewer 호출 절차를 명시 호출 전용 Claude Skill prototype 으로 고정 (jarvis-reviewer-call)`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-09-21 12:08 UTC`
- updated_at: `2026-09-22 04:02 UTC`
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

승인 2 — prototype 검토 결과에 대한 수정 승인:

```text
수정 승인합니다.
다만 보고한 범위에서만 수정하세요. 새로운 파일, helper script, Codex/Gemini 사본, governance 변경은 추가하지 마세요.
수정 대상:

1. M1

* `SKILL.md`의 Inputs와 task 기록 읽기 절차에 baseline을 명시적으로 포함
* baseline은 task 기록의 `## 기준선`에서 읽도록 함
* baseline부터 candidate까지의 전체 변경 집합을 계산할 수 있도록 연결

2. M2

* scope 경로가 candidate의 단일 commit diff에 없다는 이유만으로 BLOCKED하지 않도록 수정
* scope 검증 기준을 baseline부터 candidate까지의 전체 변경 집합으로 통일

3. M3

* baseline부터 candidate까지의 전체 변경 집합에 있으면서 승인 범위/scope에 포함되지 않은 파일을 탐지하는 BLOCKED 조건 추가
* 승인된 scope보다 candidate 변경이 넓어지는 방향을 반드시 검사

4. m1

* 사용하지 않는 `Bash(git cat-file:*)` 제거

5. m2

* task-id가 선택인지 필수인지 한 가지로 통일
* 실제 절차와 Inputs 표가 일치하도록 수정

6. m3

* merge commit 및 root commit에서 parent 해석이 달라질 수 있다는 주의사항 추가
* parent를 임의로 하나 선택해서 전체 범위를 잘못 계산하지 않도록 명확히 함

7. m4

* `.claude/agents/reviewer.md`의 명령 형식을 SKILL.md에 다시 복제하지 않도록 수정
* Reviewer 정의의 해당 절을 기준으로 따르도록 축약
* 동일 문구의 drift 가능성을 제거

8. m5

* repair 여부를 Skill이 판단하는 표현 제거
* budget 상태와 count를 사실 그대로 보고하고, budget 소진 시 escalation이 필요하다는 사실만 알리도록 수정
* budget 증액 판단은 Owner 영역으로 유지

9. `task-0136` 기록

* 위 수정 내용과 기록의 설명이 일치하도록 필요한 부분만 수정
* BLOCKED 조건 개수 등 실제 SKILL.md와 불일치하는 부분만 맞춤

수정 후에는 바로 commit하지 마세요.
```

승인 3 — `Glob` 제거와 candidate commit 승인:

```text
`Glob`은 제거하고 진행하세요.
이유:

* 현재 SKILL.md 본문에서 Glob을 사용하지 않음
* task-0136 기록도 `Read`와 `Grep`이면 충분하다고 확인함
* 이번 prototype의 최소 권한 원칙에 맞춰 불필요한 도구를 남기지 않음

수정은 `.claude/skills/jarvis-reviewer-call/SKILL.md`의 `allowed-tools`에서 `Glob`을 제거하는 한 줄 변경만 허용합니다.

문제가 없으면 두 신규 파일만 candidate commit으로 만드세요.
candidate commit 시:

* `.claude/skills/jarvis-reviewer-call/SKILL.md`
* `memory/tasks/task-0136-jarvis-reviewer-call-prototype.md`

이 두 파일만 staging/commit합니다.
`jarvis.bat`은 절대 포함하지 마세요.
commit 후에는 hash와 포함 파일, parent, commit 구조를 보고하고 push하지 마세요.
그 다음 SOP에 따라 Reviewer → QA를 진행하세요.
중요:

* Reviewer 결과를 받기 전에는 PASS 처리하지 마세요.
* Reviewer 결과가 나오면 원문 그대로 보고하세요.
* minor가 나오더라도 임의로 수정하지 말고 먼저 결과를 보여주세요.
* repair가 필요하면 기존 repair budget과 Owner 권한 경계를 그대로 적용하세요.
```

승인 4 — candidate `770ed6e6…` Reviewer FINDINGS 뒤 repair 1 승인:

```text
repair 1회를 승인합니다. 기존 repair budget 안에서 처리하세요. 이번 repair 범위는 아래로 고정합니다.
A. `.claude/skills/jarvis-reviewer-call/SKILL.md`

1. `allowed-tools` 항목을 공백 구분에서 Claude Skill frontmatter에 맞는 쉼표 구분으로 수정합니다.
2. hash 관련 BLOCKED 조건 중:
   * 40자 여부
   * commit으로 resolve되는지 여부
를 Skill 자체의 독립적인 Reviewer 검증 규칙처럼 다시 적지 말고, Reviewer 정의의 binding 절을 따르도록 참조하는 표현으로 축약합니다.
3. Owner approval verbatim block 관련 BLOCKED 조건도 동일하게 처리합니다.
   * Skill이 Reviewer의 fail-closed threshold를 재구현하지 않습니다.
   * 필요한 것은 Manager preflight에서 승인 원문이 호출에 전달될 수 있는지 확인하는 절차라는 점만 유지합니다.

B. `memory/tasks/task-0136-jarvis-reviewer-call-prototype.md`

4. `allowed-tools` 설명에서 `Glob`을 제거하여 실제 SKILL.md와 일치시킵니다.
5. 현재 `## Owner 승인 원문` 절에 승인 2와 승인 3을 원문 그대로 추가합니다.
   * 요약하거나 재작성하지 마세요.
   * 문장 순서와 조건을 임의로 바꾸지 마세요.
   * 승인 1과 동일하게 verbatim으로 기록합니다.
6. Manager summary에 승인 2·3에서 누락된 조건을 추가합니다.
특히 Reviewer가 지적한 다음 조건들을 빠뜨리지 마세요.
   * 승인 2: 수정 후 바로 commit하지 말 것
   * 승인 3: candidate commit 후 hash / 포함 파일 / parent / commit 구조 보고
   * Reviewer 결과 전 PASS 처리 금지
   * Reviewer 결과 원문 그대로 보고
   * minor 발견 시 임의 수정 금지, 먼저 보고
   * repair 시 기존 budget / Owner 권한 경계 적용
기존 summary를 불필요하게 다시 작성하지 말고 누락된 조건만 보강하세요.
7. V5의 SKILL.md 줄 수를 실제 committed file 기준 `195줄`로 수정합니다.
8. 위 수정 때문에 변경되는 설명이나 검증 수치가 있다면 실제 파일과 일치하도록 필요한 부분만 정합성을 맞춥니다.

이번 repair에서 금지

* 새로운 기능 추가 금지
* helper script 금지
* Codex/Gemini 사본 금지
* governance 변경 금지
* `.claude/skills/` 공식 경로 확정 금지
* scope/budget/approval 판단 자동화 추가 금지
* Reviewer 자체 검증 로직 재구현 금지
* `jarvis.bat` 수정 금지

절차
이번 repair에서는 수정만 하고 바로 commit하지 마세요.
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
| 12 | 검토 결과 수정은 보고한 범위(M1–M3, m1–m5, 기록 정합)에서만 한다. 새 파일·helper script·Codex/Gemini 사본·governance 변경 없음 | 승인 2 "보고한 범위에서만 수정하세요" |
| 13 | 수정 후 read-only 재검증 10 항목을 확인하고 결과를 먼저 보고한다 | 승인 2 "수정 후 read-only 재검증" 목록 |
| 14 | 수정 후 바로 commit 하지 않는다 | 승인 2 "수정 후에는 바로 commit하지 마세요" |
| 15 | `allowed-tools` 에서 `Glob` 을 제거하는 한 줄 변경만 추가로 허용한다 | 승인 3 "한 줄 변경만 허용합니다" |
| 16 | 두 신규 파일만 stage·commit 하고 `jarvis.bat` 은 포함하지 않으며 push 하지 않는다 | 승인 3 "이 두 파일만 staging/commit합니다", "`jarvis.bat`은 절대 포함하지 마세요", "push하지 마세요" |
| 17 | commit 후 hash·포함 파일·parent·commit 구조를 보고한다 | 승인 3 "commit 후에는 hash와 포함 파일, parent, commit 구조를 보고하고" |
| 18 | Reviewer 결과를 받기 전에는 PASS 처리하지 않는다 | 승인 3 "Reviewer 결과를 받기 전에는 PASS 처리하지 마세요" |
| 19 | Reviewer 결과는 원문 그대로 보고한다 | 승인 3 "Reviewer 결과가 나오면 원문 그대로 보고하세요" |
| 20 | minor 가 나와도 임의로 수정하지 않고 먼저 결과를 보여준다 | 승인 3 "minor가 나오더라도 임의로 수정하지 말고 먼저 결과를 보여주세요" |
| 21 | repair 가 필요하면 기존 repair budget 과 Owner 권한 경계를 그대로 적용한다 | 승인 3 "repair가 필요하면 기존 repair budget과 Owner 권한 경계를 그대로 적용하세요" |
| 22 | repair 1 의 수정은 승인 4 의 A 1–3, B 4–8 범위로 고정하고, 기존 budget 안에서 처리하며 commit 은 하지 않는다 | 승인 4 "이번 repair 범위는 아래로 고정합니다", "기존 repair budget 안에서 처리하세요", "수정만 하고 바로 commit하지 마세요" |
| 23 | repair 1 에서 새 기능·helper script·Codex/Gemini 사본·governance 변경·`.claude/skills/` 경로 확정·판단 자동화·Reviewer 검증 재구현·`jarvis.bat` 수정을 하지 않는다 | 승인 4 "이번 repair에서 금지" 목록 |

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
6. 4 단계 BLOCKED 조건 8 가지 (hash 미제공, baseline 부재, scope 경로가 전체 변경 집합에 없음, 전체 변경 집합이 승인 scope 밖으로 넓어짐, 전달할 승인 원문 없음, 요약 표 없음, 작업 트리 불일치, `jarvis.bat`). hash 와 승인 원문의 fail-closed 임계값은 적지 않고 Reviewer 정의의 binding 절을 가리킨다
7. 5 단계 고정 순서 호출문(marker 문구는 Reviewer 정의가 요구하는 그대로, 명령 형식은 Reviewer 정의의 해당 절을 가리키기만 한다)
8. 6 단계 Manager 보고 형식(budget 은 기록된 사실만 표시하고 소진 시 escalation 필요만 알린다)

## 설계 결정과 근거

| 결정 | 이유 |
| --- | --- |
| `disable-model-invocation: true` | 조건 4. Manager 가 `/jarvis-reviewer-call` 로만 호출한다 |
| `allowed-tools` 를 읽기 전용 git 으로 제한 | `allowed-tools` 는 그 턴의 도구를 미리 승인하므로 본문에서 실제 쓰는 명령만 둔다(`status`, `rev-parse`, `log`, `diff`, `ls-tree` + `Read`/`Grep`). 쉼표로 구분한다. 쓰기·push 형식은 없다 |
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
| V5 | frontmatter 필드 | `name`, `description`, `argument-hint`, `disable-model-invocation`, `allowed-tools` 5 개로 파싱됨. `=== OWNER APPROVAL (verbatim) ===` marker 포함. `!`cmd`` 주입은 `git status --short --branch` 와 `git log -5` 2 개뿐. repair 1 뒤 205 줄, 9.4KB (candidate `770ed6e6…` 시점에는 195 줄) |
| V6 | `allowed-tools` 와 본문 명령 일치 | 본문이 쓰는 git 은 `status`, `rev-parse`, `log`, `diff`, `ls-tree` 5 종이고 `allowed-tools` 도 같은 5 종이다. `cat-file` 은 제거했다 |
| V7 | scope 양방향 검사 실측 | task-0135 repair candidate `f0af74fe…` 기준. 단일 commit diff 는 기록 1 파일뿐이지만 `97c775f..f0af74f` 전체 변경 집합은 4 파일이고, `scope − 변경집합` 과 `변경집합 − scope` 가 모두 비어 있다. 수정 전 규칙이었다면 정상 호출이 BLOCKED 됐다 |

## 바꾸지 않은 것

- `.claude/agents/reviewer.md`, `.codex/` 전체, `scripts/validate_multi_agent_sop.py`
- `docs/jarvis-multi-agent-sop-v0.1.md`, master-plan, handoff, 기존 task 기록
- `skills/repo-bootstrap.md`, `skills/report-writer.md`
- Console 코드, `jarvis.bat`

## Repair 이력

retry_budget=1, retry_count=0, repair_budget=1, repair_count=1

| # | 원인 | 조치 |
| --- | --- | --- |
| 1 | Reviewer FINDINGS (candidate `770ed6e6d8953bbebaa1d07fca0bbcdd4b7a0ae7`, major 2 / minor 5): 기록의 `allowed-tools` 설명에 `Glob` 이 남아 SKILL.md 와 어긋남, Manager 요약이 승인 2·3 조건을 빠뜨림, 승인 2·3 이 기록의 승인 원문 절에 없음, V5 줄 수 196 (실제 195), `allowed-tools` 가 공백 구분, hash·승인 원문 BLOCKED 조건이 Reviewer 정의의 임계값을 다시 적음 | 승인 4 범위대로 `allowed-tools` 를 쉼표 구분으로 고치고, hash·승인 원문 BLOCKED 조건을 Reviewer 정의 binding 절 참조로 축약했다. 기록에는 승인 2·3·4 원문을 추가하고 요약 12–23 행을 보강했으며 `Glob` 문구와 V5 수치를 실제 파일에 맞췄다. 새 기능·script·사본·governance 변경은 없다. 새 candidate 에 fresh Reviewer → QA |

## 후속으로 남긴 것

- `.claude/skills/` 를 Jarvis 공식 skill 경로로 확정할지 (조건 10, Owner 결정)
- validator 가 skill 파일을 검사할지 (현재 검사 없음)
- 저장소의 산문 `skills/*.md` 와 Claude Skill 형식의 관계 정리
- Codex·Gemini 사본과 공통 본문 배선 (필요해질 때)
- skill-creator 의 표준 필드 검사(`quick_validate.py`)를 Jarvis 검증에 넣을지
