# task-0135-reviewer-definition-parity

- id: `task-0135-reviewer-definition-parity`
- title: `Claude Reviewer 정의(.claude/agents/reviewer.md)와 Codex Reviewer 정의(.codex/agents/reviewer.toml)의 핵심 계약 정합성 점검·강화`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-09-18 03:04 UTC`
- updated_at: `2026-09-18 07:35 UTC`
- summary: `task-0134 Owner 결정 1 이 별도 과제로 남긴 두 Reviewer 정의의 장기적 정합성과 validator 대상 확장을 다룬다. read-only 대조 결과 approval binding 은 양쪽에 있지만 marker 문구, candidate hash fail-closed, file scope, 금지 목록, 출력 형식이 reviewer.toml 에 없거나 다르고 validator 는 reviewer.md 를 전혀 검사하지 않는다. Owner 가 Q1–Q3 와 H1/H2 에 답하고 구현을 승인했다(역할 규칙 전부 동일, 호출자 명칭 Manager (the caller), validator 양쪽 검사, task-0134 작은 Reviewer 문제 포함). DONE 은 Reviewer/QA 후 Owner 가 Console Complete 로 결정한다.`
- source_command: `Owner 지시: origin/main 97c775f 기준으로 Reviewer 정의 정합성 강화 과제의 task record 만 작성`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `97c775ff2ed9be623faec9daecddc26070ddb7e2` (`origin/main` 과 같음) |
| 작업 전 상태 | tracked 수정 없음, untracked `jarvis.bat` 만 |
| validator | `python -B scripts/validate_multi_agent_sop.py` → `negative_checks=34`, `negative_failures=0`, `status=PASS` (task-0134 최종 확인 기준) |

## 문제와 배경

task-0134 Owner 승인 원문 결정 1 은 이렇게 적었다.

```text
1. `.claude/agents/reviewer.md`는 이번 validator 검사 대상에 포함하지 않습니다.
   - validator는 기존 구조대로 `.codex/agents/reviewer.toml`의 필수 문구를 검사합니다.
   - `.claude/agents/reviewer.md`와 `.codex/agents/reviewer.toml`의 장기적 정합성/validator 대상 확장은 별도 과제로 남깁니다.
```

같은 Reviewer 역할이 두 정의로 존재한다. `.claude/agents/reviewer.md` 는 Claude Code subagent 이고
(`ff165e2` 에서 추적 시작, task-0134 에서 approval binding 추가), `.codex/agents/reviewer.toml` 은
Codex agent 이며 SOP validator 가 검사하는 쪽이다. 두 정의는 따로 고쳐져 와서 핵심 계약이 어긋나 있다.

### 두 정의 대조 (baseline `97c775f`, read-only)

| # | 계약 항목 | `.claude/agents/reviewer.md` | `.codex/agents/reviewer.toml` | 상태 |
| --- | --- | --- | --- | --- |
| 1 | strict read-only, 파일 수정·stage·commit·repair 금지 | 있음 | 있음 (`sandbox_mode = "read-only"` 포함) | 일치 |
| 2 | exact candidate, full hash 존재 확인, moving branch 금지 | 있음 | 있음 | 일치 |
| 3 | candidate hash 누락·40 자 미만·모호 시 `BLOCKED` + 고정 blocking finding | 있음 (Candidate binding 절) | 없음. "verify that exact full hash exists" 만 | **불일치** |
| 4 | `HEAD`, `@`, branch, tag, short hash, working tree 를 검토 대상으로 쓰지 않음 | 있음 | 없음 | **불일치** |
| 5 | 호출자가 준 file scope 로 제한, scope 밖 파일은 보고만 | 있음 | 없음 | **불일치** |
| 6 | Owner 승인 원문 필수, 없으면 `BLOCKED`, 요약은 대체 불가, 원문 기준 scope 판단, 요약 차이 finding | 있음 | 있음 | 일치 (문구 차이는 7 행) |
| 7 | 승인 원문 marker 문구 | `=== OWNER APPROVAL (verbatim) ===` (정확한 줄) | `OWNER APPROVAL (verbatim)` (`===` 없음) | **불일치** |
| 8 | 호출자 명칭 | caller | Manager | 표현 차이 (플랫폼 차이로 의도적일 수 있음) |
| 9 | 허용 명령 목록 (read-only git 형식, pipeline·redirection 금지) | 있음 | 없음 (sandbox 에 의존) | **불일치** |
| 10 | `jarvis.bat`, `.env` 읽기·인용·stage 금지, 건드리면 finding | 있음 | 없음 | **불일치** |
| 11 | 서버·브라우저·외부 호출·다른 agent 호출 금지 | 있음 | 없음 | **불일치** |
| 12 | 결정 금지 범위 | retry, repair, approval, release, push, PR | retry/repair 만 | **불일치** |
| 13 | finding 필드 (severity, evidence, impact, correction) | 있음 | 있음 | 일치 |
| 14 | severity 값 `blocking` / `major` / `minor`, verdict 값 `PASS` / `FINDINGS` / `BLOCKED` | 있음 | 없음 | **불일치** |
| 15 | 고정 출력 template 과 note 문구 | 있음 | 없음 | **불일치** |
| 16 | PASS 는 QA PASS·승인·release 권한이 아님, candidate 변경 시 이전 결과 무효 | 있음 | 있음 | 일치 |
| 17 | `description` 에 hash·scope·승인 원문 필요 명시 | 있음 | 없음 ("Performs a strict read-only review of one exact Jarvis-Core candidate commit.") | **불일치** |

### validator 현황

| 대상 | 검사 |
| --- | --- |
| `.codex/agents/reviewer.toml` | `reviewer_read_only` 4 문구, `reviewer_approval_binding` 3 문구, `reviewer_write_contradiction` 패턴과 각 negative self-test |
| `.claude/agents/reviewer.md` | 없음. validator 가 파일을 읽지 않는다. 한쪽만 바뀌어도 검출되지 않는다 |

### task-0134 에서 관찰된 Reviewer 동작 (이 task 의 범위 판단 참고)

- 허용 명령 형식 이탈: 첫 사전 확인 B 에서 `git -C <path>` 접두어와 반복 `-e` 사용. 다른 호출에서는 `\|` 로 여러 패턴을 한 grep 에 묶음. `reviewer.md` 는 형식을 열거하지만 regex alternation 금지는 적혀 있지 않다.
- 요약 대조 결과가 호출마다 달랐다. 같은 입력에서 원문 조건 누락 4 개를 보고하기도 하고 보고하지 않기도 했다.
- `BLOCKED` 결과에서도 `files_reviewed` 에 scope 경로를 그대로 적었다 (실제로 읽은 파일 없음).

이 세 가지는 정합성 문제가 아니라 Claude Reviewer 동작 문제다. 포함 여부는 Q3 로 묻는다.

## 목표

1. 두 Reviewer 정의가 같은 핵심 계약을 갖는다. 핵심 계약의 경계는 Q1 의 답으로 정한다.
2. 한쪽 정의에서 핵심 계약 문구가 빠지거나 두 정의가 어긋나면 validator 가 FAIL 한다 (Q2 가 "예" 인 경우).
3. 플랫폼 차이(도구 선언, 호출자 명칭, sandbox)는 의도된 차이로 기록하고 정합성 요구에서 제외한다.

## 승인이 필요한 범위 (제안)

아래는 제안이다. Owner 승인 원문과 bounded question 답을 받기 전에는 구현하지 않는다.

| # | 파일 | 제안 변경 | 관련 질문 |
| --- | --- | --- | --- |
| S1 | `.codex/agents/reviewer.toml` | 대조표 불일치 행을 모두 해소해 `reviewer.md` 와 같은 역할 규칙을 `developer_instructions` 에 둔다 (candidate binding, 검토 대상 제한, file scope, marker `=== OWNER APPROVAL (verbatim) ===`, 허용 명령 형식, 금지 목록, 결정 금지 범위, verdict·severity 값, 출력 template). `description` 에 hash·scope·승인 원문 필요 명시. Manager 요약 6 행 보강도 같이. 기존 validator 필수 문구 7 개는 그대로 유지 | Q1, Q3 |
| S2 | `.claude/agents/reviewer.md` | Manager 요약 6 행의 작은 문제 수정(허용 형식 밖 변형 금지, `BLOCKED` 시 `files_reviewed` 비움, 조건별 요약 대조 절차). 두 파일에서 같은 문장이 되도록 필요한 문구 조정. frontmatter 형식은 유지 | Q1, Q3 |
| S3 | `scripts/validate_multi_agent_sop.py` | `.claude/agents/reviewer.md` 를 읽고, 공통 핵심 규칙 문구를 두 파일 모두에 요구하는 검사와 파일·문구마다 negative self-test 추가. 기존 검사·self-test 는 삭제하거나 약화하지 않음 | Q2 |
| S4 | `memory/tasks/task-0135-reviewer-definition-parity.md` | 이 기록. 승인 원문, 질문과 답, 검증 결과 반영 | — |

## 명시적 비범위

- `docs/jarvis-multi-agent-sop-v0.1.md`, `AGENTS.md`, `docs/master-plan.md`, `docs/chatgpt-handoff.md`, Roadmap
- `.codex/agents/manager.toml`, `implementer.toml`, `qa.toml`, `docs.toml`
- 기존 task 기록 (task-0134 포함)
- Console 코드와 문서
- 새 gate, repair/retry budget, candidate 무효화 규칙 변경
- task-0131·task-0134 결과 기록 commit 취급의 SOP 일반화
- Codex 와 Claude 의 플랫폼 차이 자체를 없애는 것 (도구 선언, sandbox, 호출자 명칭)
- Reviewer 요약 대조 결과의 비결정성 해소 (모델 동작 문제로, 정의 문구만으로 보장할 수 없음. Q3 답에 따라 절차 문구 보강은 범위에 포함)
- push, merge, PR
- `jarvis.bat` (접근·수정·stage 금지)

## 검증 계획 (구현 승인 후)

| # | 검증 | 기대 |
| --- | --- | --- |
| V1 | `python -B scripts/validate_multi_agent_sop.py` | `status=PASS`, `negative_failures=0`, `negative_checks` 가 34 보다 증가 (Q2 "예" 인 경우) |
| V2 | 새 필수 문구를 두 파일에서 각각 하나씩 지운 외부 mutation (candidate 사본에서) | 각 case 가 exit 1, 기대 오류 코드 하나 |
| V3 | 대조표 재작성 | 핵심 계약 행 전부 "일치", 남은 차이는 의도된 플랫폼 차이로만 표시 |
| V4 | Claude Reviewer 동작: hash 없음 → `BLOCKED`, 승인 원문 없음 → `BLOCKED`, 둘 다 있음 → 정상 review | task-0134 A/B 와 같은 결과 |
| V5 | Codex Reviewer 동작 | 이 환경에서 Codex agent 를 호출할 수단이 확인되지 않았다. 문구·validator 검증으로 대신하거나 Owner 가 Codex 세션에서 수행 (Q2 답과 함께 결정) |
| V6 | `git diff --check` | exit 0 |
| V7 | `python -B apps/jarvis-console/run_smoke_tests.py` | exit 0 |
| V8 | diff scope | 승인된 파일만. `jarvis.bat` 미포함 |

참고: `.claude/agents/reviewer.md` 를 고치면 같은 세션의 다음 Reviewer 호출부터 바뀐 정의가 적용된다
(task-0134 Q1 근거). 이 task 의 Reviewer 도 바뀐 정의로 동작한다.

## Owner bounded question

```text
Q1. `.codex/agents/reviewer.toml`이 `.claude/agents/reviewer.md`의 어디까지를 같은 핵심 계약으로 가져야 할까요?
  A. 핵심 계약만 (Recommended): read-only, candidate hash fail-closed(BLOCKED), 검토 대상 제한(HEAD/branch/short hash 금지), file scope, 승인 원문 binding과 동일 marker `=== OWNER APPROVAL (verbatim) ===`, `jarvis.bat`/`.env` 금지, 결정 금지 범위, verdict 3값과 severity 3값. 허용 명령 목록과 고정 출력 template은 Claude 전용으로 남김(Codex는 sandbox로 쓰기 차단).
  B. 전체 복제: 허용 명령 목록과 고정 출력 template까지 toml에 그대로 옮김.
  C. marker 문구 통일만.

Q2. validator가 `.claude/agents/reviewer.md`도 검사하도록 확장할까요?
  A. 예 (Recommended): Q1에서 정한 핵심 계약 문구를 두 파일 모두에 필수로 요구하고 문구마다 negative self-test 추가.
  B. 아니오: toml만 강화하고 validator 대상은 그대로.

Q3. task-0134에서 관찰된 Claude Reviewer 동작 문제(regex alternation으로 패턴 묶기, BLOCKED 시 files_reviewed 기재)를 이 task에 포함할까요?
  A. 제외하고 별도 task로 (Recommended): 이 task는 두 정의의 정합성만 다룸.
  B. 포함: reviewer.md에 해당 규칙을 추가.
```

## Owner 승인 원문

구현 승인 메시지 (H1/H2 답 포함, 원문):

```text
H1: 예.
허용 git 명령 목록과 고정 출력 형식도 Reviewer의 역할 규칙으로 봅니다. Claude/Codex 양쪽 Reviewer 정의에 동일하게 적용하세요. 단, 실제 명령 실행 방식처럼 Claude/Codex 플랫폼에서 불가피하게 다른 부분은 플랫폼별 차이로 유지합니다.
H2: 예.
호출자 명칭은 **`Manager (the caller)`**로 통일하세요. Claude 쪽의 `caller`, Codex 쪽의 `Manager`처럼 의미가 같은 표현을 플랫폼별로 다르게 유지하지 않습니다.
구현 승인: 예.
위 H1/H2 결정을 Owner 승인 원문으로 task-0135 기록에 먼저 기록한 뒤 구현하세요.
승인된 범위:

* S1 `reviewer.toml`을 `reviewer.md`와 동일한 Reviewer 역할 규칙에 맞게 정합성 수정
* S2 `reviewer.md`의 task-0134에서 확인된 작은 문제와 문구 정합성 수정
* S3 validator가 양쪽 Reviewer 정의의 공통 핵심 규칙을 검사하도록 확장하고 negative self-test 추가
* task-0134에서 확인된 작은 문제 3건도 이번 task 범위에서 수정

구현 시:

* 플랫폼별 문법/도구 사용법 차이는 유지
* SOP, master-plan, handoff, 다른 agent 정의, 기존 task는 수정하지 않음
* `jarvis.bat` 절대 접근/수정/stage 금지
* 먼저 task record의 Owner 승인 원문과 범위를 확정한 뒤 구현
* 구현 후 바로 push하지 말 것
* 작업 단위 checkpoint 전까지 Reviewer/QA 절차를 기존 SOP에 따라 진행

우선 승인 원문 기록과 구현 계획을 확인한 뒤 구현을 진행하세요.
```

위 bounded question Q1–Q3 에 대한 Owner 답 (원문):

```text
Q1: 핵심 규칙뿐 아니라 Reviewer 역할의 규칙은 양쪽에서 동일하게 적용되도록 맞춘다. 플랫폼별 문법/도구 사용법 차이만 예외로 둔다.
Q2: validator가 Claude와 Codex 양쪽 Reviewer 정의의 공통 핵심 규칙을 모두 검사하도록 한다.
Q3: task-0134에서 발견한 작은 Reviewer 문제도 이번 task에서 함께 수정한다.
```

Q1 답은 제시한 A·B·C 중 어느 것과도 같지 않다. 가장 가까운 것은 B(전체 복제)이며, 예외를 "플랫폼별 문법/도구 사용법 차이" 로 한정한다.

candidate `28125a7742d63f4e514d23291ab33cfd2405f2b2` Reviewer FINDINGS (major 1, minor 4) 뒤 read-only 재검토에서 Owner 에게 올린 질문 (요지):

```text
질문 1. `Manager` 문구 처리
  A (권장): 호출 주체를 가리키는 문장 하나("Require the Owner's approval verbatim from Manager under the marker line ...")만 `Manager (the caller)`로 수정하고 그 문장에 의존하는 validator 문자열 3곳도 같이 바꾼다. `Manager summary` 같은 용어는 유지. repair 1회.
  B: 문구 유지, Manager 요약 4행만 "task-0134 필수 문구 때문에 예외 1곳"으로 정정. repair 1회.
질문 2. `git -C` 처리
  A (권장): task-0135에서는 현재 금지 문구를 유지하고, 실제 실행 단계 강제(또는 완화 여부)는 별도 후속 task로 넘긴다.
  B: task-0135 안에서 "저장소 루트 `-C` 허용"으로 규칙 완화.
```

Owner 답 (원문):

```text
Q1 A, Q2 A로 결정. 원문 기록 후 repair 진행
```

candidate `4d095b31557626bc7784f1c145f6d92b189cc456` fresh Reviewer FINDINGS (minor 4) 뒤 repair budget 1/1 소진으로 Owner 에게 올린 질문 (요지):

```text
A. repair budget을 2로 늘린다. minor 1–2(Manager 요약에 repair 질문 1 A 조건 2개와 "구현 계획을 확인한 뒤" 추가, task 기록만 수정)를 반영하고 새 candidate에 fresh Reviewer → QA.
B. budget을 늘리지 않는다. minor 1–2를 기록 요약 누락으로 받아들이고 현재 candidate로 QA 진행(SOP 순서 예외).
```

Owner 답 (원문):

```text
A로 결정. budget 2로 증액하고 repair 진행
```

## Manager 요약 (원문 해석)

| # | 조건 | 원문 근거 |
| --- | --- | --- |
| 1 | Reviewer 역할 규칙은 두 정의에서 전부 같게 적용한다. 대조표 3–5, 7, 9–12, 14, 15, 17 행의 불일치를 모두 해소한다 | Q1 |
| 2 | 예외는 플랫폼 문법·도구 사용법만: 정의 파일 형식(YAML frontmatter + Markdown 대 TOML), `tools:`·`model:` 선언 대 `sandbox_mode`, Claude 의 Bash 도구 호출 방식 대 Codex 셸 실행 방식 | Q1 "플랫폼별 문법/도구 사용법 차이만 예외" |
| 3 | 허용 git 명령 형식 목록과 고정 출력 template 은 역할 규칙으로 보고 양쪽에 같게 둔다. 명령 실행 방식(Claude Bash 도구 대 Codex 셸)만 플랫폼 차이로 남긴다 | Q1, H1 |
| 4 | 호출 주체(Reviewer 를 호출한 쪽)를 가리킬 때는 두 정의 모두 `Manager (the caller)` 로 쓴다. 단독 `caller` 로 호출자를 가리키지 않는다. `Manager summary` 처럼 `Manager` 가 문서·역할 용어로 쓰이는 곳은 그대로 둔다. 호출 주체 문장을 바꿀 때 그 문장에 의존하는 validator 문자열 3 곳도 같이 바꾸며, 이 수정은 repair 1 회로 한다 | Q1, H2, repair 질문 1 A "그 문장에 의존하는 validator 문자열 3곳도 같이 바꾼다", "repair 1회" |
| 5 | validator 는 `.claude/agents/reviewer.md` 도 읽고, 공통 핵심 규칙 문구를 두 파일 모두에 필수로 요구하며 문구마다 negative self-test 를 둔다. 기존 검사·self-test 는 삭제·약화하지 않는다 | Q2 |
| 6 | task-0134 에서 관찰한 작은 Reviewer 문제를 두 정의에 함께 고친다: (a) 허용 형식 밖 변형 금지를 명시(`git -C` 같은 추가 옵션·접두어, 반복 `-e`, `\|` 같은 regex alternation 으로 패턴 묶기 금지, grep 당 패턴 하나), (b) `BLOCKED` 일 때 `files_reviewed` 는 비움, (c) 요약 대조를 승인 원문 조건별로 수행하고 요약에 없는 조건을 모두 finding 으로 보고하도록 절차를 명시 | Q3 |
| 7 | 6(c) 는 결과가 호출마다 달라지는 문제를 줄이려는 문구 보강이며, 모델 동작이라 결정적 보장은 하지 않는다 | Q3, 명시적 비범위의 비결정성 항목 |
| 8 | 비범위는 앞 절 그대로 유지. SOP·다른 toml·기존 task·Console·gate·budget·push/merge/PR·`jarvis.bat` 무변경 | 명시적 비범위 |
| 9 | task record 의 Owner 승인 원문과 범위를 먼저 확정하고 구현 계획을 확인한 뒤 구현한다 | 구현 승인 "먼저 task record의 Owner 승인 원문과 범위를 확정한 뒤 구현", "우선 승인 원문 기록과 구현 계획을 확인한 뒤 구현을 진행하세요" |
| 10 | 작업 단위 checkpoint 전까지 Reviewer → QA 를 기존 SOP 대로 진행한다. 구현 후 바로 push 하지 않는다 | 구현 승인 "작업 단위 checkpoint 전까지 Reviewer/QA 절차를 기존 SOP에 따라 진행", "구현 후 바로 push하지 말 것" |
| 11 | `git -C` 금지 문구는 두 정의에 그대로 둔다. 실행 단계 강제 방법(또는 완화 여부)은 별도 후속 task 로 넘긴다 | repair 질문 2 A |

### 해석 확인 2 건 (Owner 답으로 확정)

- H1. 허용 git 명령 목록과 고정 출력 template 을 "역할 규칙" 으로 보고 Codex 정의에도 같게 넣는다. → 예 (위 원문).
- H2. 호출자 명칭을 `Manager (the caller)` 로 통일한다. → 예 (위 원문).

### 구현 계획

1. 두 정의의 본문을 같은 문장으로 맞춘다. `reviewer.md` 는 frontmatter 뒤 본문, `reviewer.toml` 은 `developer_instructions` 가 같은 본문을 갖는다. 문단·항목은 한 줄로 써서 raw 문자열 비교가 가능하게 한다.
2. 플랫폼 차이로 남기는 것: 파일 형식, `tools:`·`model:` 대 `sandbox_mode`, 허용 명령 절의 실행 방식 한 문장(Claude "through the Bash tool", Codex "as shell commands").
3. `description` 은 두 파일에서 같은 문장으로 맞춘다.
4. 기존 `reviewer.toml` 필수 문구 7 개와 기존 negative self-test 의 raw 문자열을 그대로 유지한다.
5. 작은 문제 3 건: 허용 형식 밖 변형 금지(추가 옵션·접두어, 반복 `-e`, regex alternation), `BLOCKED` 시 `files_reviewed` 비움, 조건별 요약 대조 절차.
6. validator: `.claude/agents/reviewer.md` 를 source 로 읽고, 공통 역할 규칙 문구 목록을 두 파일 모두에 요구(`reviewer_role_parity`), 호출자 명칭 통일 검사(`reviewer_caller_name`), 파일·문구마다 negative self-test 추가. 기존 검사는 삭제·약화하지 않고 `documents=3` 집계는 바꾸지 않는다.
7. 검증 V1–V8 뒤 candidate local commit → Reviewer → QA. push 하지 않는다.

## Manager assignment (승인 후 확정)

| 역할 | assignment |
| --- | --- |
| Implementer | 승인된 파일만. V1–V3, V6–V8. candidate local commit 1 개 |
| Reviewer | candidate full hash 에 고정, 승인된 파일 scope, strict read-only. Manager 요약과 Owner 승인 원문을 표시 구역으로 받는다. 바뀐 정의로 동작 |
| QA | Reviewer PASS 후 같은 candidate 에서 V1–V8 재현 |
| Docs | 별도 Docs 실행 `not_required` (변경 자체가 정의·검사 문서) |
| 완료 | Reviewer/QA PASS 후에도 `DOING`. `DOING → DONE` 은 Owner 가 Console 에서 결정 |

## 무엇을 바꿨나

| 파일 | 변경 |
| --- | --- |
| `.claude/agents/reviewer.md` | 본문을 공통 Reviewer 본문으로 교체. 문단·항목을 한 줄로 씀. 호출자 명칭 `Manager (the caller)`. 승인 marker 문장 명시. 조건별 요약 대조 절차, 허용 형식 밖 변형 금지(추가 옵션·접두어, 반복 `-e`, regex alternation), `BLOCKED` 시 `files_reviewed` `[]` 추가. findings 대상에 요약 누락·모순 추가. frontmatter 의 `tools:`·`model:` 유지 |
| `.codex/agents/reviewer.toml` | `developer_instructions` 를 같은 공통 본문으로 교체하고 `description` 을 `reviewer.md` 와 같은 문장으로 맞춤. `sandbox_mode = "read-only"` 유지. 기존 필수 문구 7 개 유지 |
| `scripts/validate_multi_agent_sop.py` | `.claude/agents/reviewer.md` 를 source 로 읽음. 공통 역할 규칙 문구 18 개를 두 정의 모두에 요구(`reviewer_role_parity`), 단독 `caller` 금지(`reviewer_caller_name`). negative self-test 38 개 추가(문구 18 × 2 파일, 호출자 명칭 2). 기존 검사·self-test 무변경, `documents=3` 유지 |

두 정의 본문의 차이는 허용 명령 절 첫 문장 하나다 (Claude "each through the Bash tool", Codex "each as a shell command in the read-only sandbox"). `description` 은 두 파일에서 같다.

repair 1 에서 호출 주체 문장을 "Require the Owner's approval verbatim from Manager (the caller) under the marker line OWNER APPROVAL (verbatim)." 로 바꿨다. 이 문장에 의존하던 validator 문자열 3 곳(task-0134 `reviewer_approval_binding` 필수 문구, 같은 문구의 negative self-test, task-0135 공통 문구 목록)도 같은 문장으로 바꿨다. 검사 수와 self-test 수는 그대로다. 남은 단독 `Manager` 는 `Manager summary` 3 곳뿐이며 문서 용어다. `reviewer_caller_name` 은 단독 `caller` 만 금지한다.

## 검증 (Implementer 보고, QA 재현 대상)

| # | 항목 | 결과 |
| --- | --- | --- |
| V1 | `python -B scripts/validate_multi_agent_sop.py` | `negative_checks=72`, `negative_failures=0`, `status=PASS` (34 에서 38 증가) |
| V2 | 작업 트리 사본에서 문구 18 개를 파일마다 하나씩 지우기 + 단독 `caller` 추가 | 38/38 exit 1, 기대 코드 검출. 무변형 사본 PASS |
| V3 | 두 본문 대조 | 차이는 허용 명령 절 첫 문장 하나. `description` 동일. 문구 18 개가 두 파일에 각각 raw 로 정확히 1 회 |
| V4 | Claude Reviewer 동작 | candidate 뒤 QA 에서 재현 |
| V5 | Codex Reviewer 동작 | 이 환경에서 Codex agent 호출 수단 없음. V1–V3 로 대신 |
| V6 | `git diff --check` | exit 0 |
| V7 | `python -B apps/jarvis-console/run_smoke_tests.py` | self-test passed, smoke tests passed, exit 0 |
| V8 | diff scope | `.claude/agents/reviewer.md`, `.codex/agents/reviewer.toml`, `scripts/validate_multi_agent_sop.py`, 이 기록. `jarvis.bat` 미포함 |

`.claude/agents/reviewer.md` 를 고쳤으므로 이 세션의 다음 Reviewer 호출부터 바뀐 정의가 적용된다.

위 V1–V3, V6–V8 은 repair 1 뒤 다시 실행해 같은 결과였다 (`negative_checks=72`, `negative_failures=0`, 외부 mutation 38/38, 본문 차이 1 줄, 문구 18 개 각 1 회, diff-check exit 0, smoke exit 0). 두 정의에 남은 단독 `Manager` 는 `Manager summary` 3 곳뿐이다.

## Repair 이력

retry_budget=1, retry_count=0, repair_budget=2 (Owner 가 1 에서 2 로 증액), repair_count=2

| # | 원인 | 조치 |
| --- | --- | --- |
| 1 | Reviewer FINDINGS (candidate `28125a7742d63f4e514d23291ab33cfd2405f2b2`): major 1 — 호출 주체 문장 "Require the Owner's approval verbatim from Manager under the marker line …" 에 단독 `Manager` 가 남아 Manager 요약 4 행·H2 와 어긋나고 그 예외가 Owner 결정이 아니었음. minor 1–2 — 구현 승인 조건 "먼저 task record의 Owner 승인 원문과 범위를 확정한 뒤 구현", "작업 단위 checkpoint 전까지 Reviewer/QA 절차를 기존 SOP에 따라 진행" 이 Manager 요약에 없음. minor 3 — validator·mutation·diff-check·smoke 는 QA handoff. minor 4 — Reviewer 가 `git -C /c/work/jarvis-core rev-parse …` 로 허용 형식을 어긴 것을 스스로 보고 | Owner 결정(질문 1 A, 질문 2 A)에 따라 호출 주체 문장만 `from Manager (the caller)` 로 바꾸고 의존 validator 문자열 3 곳을 같이 바꿈(검사 수·self-test 수 불변). Manager 요약 4 행 정정, 9–11 행 추가. `git -C` 금지 문구는 유지하고 실행 단계 강제는 후속 task 로 이관(요약 11 행). 새 candidate 에 fresh Reviewer → QA |
| 2 | Reviewer FINDINGS (candidate `4d095b31557626bc7784f1c145f6d92b189cc456`): minor 1 — Manager 요약에 repair 질문 1 A 의 조건 "그 문장에 의존하는 validator 문자열 3곳도 같이 바꾼다", "repair 1회" 가 없음. minor 2 — 요약 9 행에 "구현 계획을 확인한 뒤" 가 없음. minor 3 — Reviewer 가 도구가 파일로 저장한 긴 diff 출력을 Read 도구로 읽어 허용 git 형식 밖으로 읽었음을 스스로 보고 (후속 task 의 허용 형식 강제 주제). minor 4 — validator·mutation·diff-check·smoke 는 QA handoff. repair budget 1 소진으로 Owner 에게 escalation, Owner 가 budget 을 2 로 증액하고 repair 를 결정 | Manager 요약 4 행과 9 행에 빠진 조건을 원문 인용과 함께 추가. task 기록만 수정, 정의·validator 무변경. 새 candidate 에 fresh Reviewer → QA |

## 후속 task 로 넘긴 것

- Reviewer 허용 명령 형식을 문서가 아니라 실행 단계에서 강제하는 방법(Claude Code 권한 규칙·hook 등) 조사·적용, 또는 저장소 루트 `git -C` 허용으로 완화할지 결정. 근거: task-0134 의 `git -C`·반복 `-e`·regex alternation, task-0135 candidate `28125a7…` Reviewer 의 `git -C` 사용, candidate `4d095b3…` Reviewer 가 도구가 저장한 긴 diff 출력을 Read 도구로 읽은 일.
