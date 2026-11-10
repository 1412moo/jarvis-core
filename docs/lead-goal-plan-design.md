# Lead 목표 계획 dry-run 설계 (task-0225)

이 문서는 작성 당시의 설계 기록이다(AGENTS.md 기준 지도의 History). 현재 동작은 코드와 smoke가,
현재 규칙은 SOP §10.1의 목표 계획 문단이 정한다.

## 1. 목적과 이번 단계의 경계

최종 방향은 Owner가 목표를 주면 팀장(Lead)이 계획·분해·배정·실행 조율·검증·보고를 맡는 팀이다.
이번 단계는 그 첫 층인 **목표 단위 계획**만 만든다.

| 한다 | 하지 않는다 |
| --- | --- |
| `/goal <목표>`로 읽기 전용 팀장이 목표를 하위 작업으로 나눈다 | task 생성, Worker 실행, 배정 |
| 하위 작업마다 kind, 방식, 목적, 경로, 선행 작업, 완료 조건, 위험도, Owner 결정, Worker 지시를 받는다 | Dispatcher, 큐, 백그라운드 Worker |
| 의존성으로 실행 단계를 계산하고 순서를 검증한다 | main 통합, commit, push |
| 결정론적 Policy Gate가 작업마다 `auto`, `needs_owner`, `forbidden`을 판정한다 | 판정을 실행 권한으로 쓰는 것 |
| Discord에 계획 전체를 보이고 저장소 밖에 계획 파일을 남긴다 | 계획 파일을 다시 읽어 무엇인가를 하는 것 |

근거: `docs/master-plan.md`의 잠긴 고위험 기능(자동 실행, background worker 등)과 SOP §9의
금지(dispatcher subsystem, background execution, queue persistence)는 그대로다. 팀장은 SOP §10의
팀장 단계와 같은 방식(같은 잠금, HEAD의 임시 detached worktree, Read·Grep·Glob, plan 모드)으로
한 번 실행된다. 계획 파일은 실행 보고 파일과 같은 성격의 검토 자료이며 큐가 아니다.

## 2. 목표 계획 구조 v1 (`orchestrator/worker/goal_plan.py`)

팀장은 JSON 객체 하나로 답한다. 형식이 어긋나면 실패로 보고(fail closed) 사유 코드만 남긴다.

| 필드 | 내용 | 제한 |
| --- | --- | --- |
| `goal_summary` | 목표 전체 요약 | 한 줄, 300자 |
| `tasks[]` | 하위 작업 | 1~8개 |
| `tasks[].id` | `T1`…`T99` 형식 | 중복 금지 |
| `tasks[].title` | 제목 | 한 줄, 100자, backtick 금지(뒤에 task 제목이 될 수 있음) |
| `tasks[].kind` | 등록된 작업 종류 이름 또는 `none` | `none`이면 `owner_decision`에 이유 필수 |
| `tasks[].mode` | `edit` 또는 `read_only` | |
| `tasks[].purpose` | 목적 | 한 줄, 300자 |
| `tasks[].paths[]` | 바꿀(읽기 전용이면 읽을) 저장소 상대 경로 | 0~10개, 공백 없음 |
| `tasks[].depends_on[]` | 먼저 끝나야 할 id | 존재하는 id, 자기 자신·순환 금지 |
| `tasks[].acceptance[]` | 완료 조건 | 1~5개, 각 200자 |
| `tasks[].risk` | 팀장 위험도 `low`/`medium`/`high` | |
| `tasks[].owner_decision` | `none` 또는 Owner가 정할 이유 | 300자 |
| `tasks[].worker_request` | Worker에게 줄 한 줄 지시 | 300자 |
| `order[]` | 예상 실행 순서 | 모든 id 한 번씩, 선행 작업이 먼저 |
| `flow` | 전체 진행 흐름 | 한 줄, 500자 |

- 단계(stage): 선행 작업이 없으면 1단계, 있으면 선행 작업 중 가장 늦은 단계 + 1. 같은 단계의 작업은 서로
  의존하지 않는다(나중에 병렬 실행 후보가 되지만 지금은 표시만 한다).
- `plan_digest`: 검증된 계획을 고정 JSON 형태로 만든 sha256. 뒤의 승인이 "어느 계획을 승인했는지"를
  정확히 가리킬 수 있게 한다(5절).
- 계획 파일: `%LOCALAPPDATA%\jarvis-core\goal-plans\<goal-id>.json`(환경 변수 `JARVIS_GOAL_PLAN_DIR`로 바꿀 수 있음).
  저장소 안을 가리키면 쓰지 않는다. `dry_run: true`, `executed: false`, 계획, 단계, 판정, hash, 팀장 사용량을 담는다.

## 3. Policy Gate v0 (`orchestrator/worker/policy_gate.py`)

판정은 코드가 한다. 팀장의 말은 판정을 **엄격하게만** 만들 수 있고 느슨하게 만들 수 없다.

| 판정 | 조건 |
| --- | --- |
| `forbidden` | 경로가 파이프라인 보호 경로(`PROTECTED_PATHS`), 모든 `jarvis.bat`, `.env`로 시작하는 파일, `.git` 내부, 저장소 밖(절대 경로, 드라이브, `~`, `..`) |
| `needs_owner` | 등록된 kind가 없는 수정, 경로 없는 수정, kind 허용 경로 밖 경로, 와일드카드 경로, 아래 신호 문구, 팀장의 `owner_decision`, 팀장 위험도 `high`, `auto`가 아닌 선행 작업 |
| `auto` | 위 어느 것에도 해당하지 않음 |

신호 문구(제목, 목적, Worker 지시, 완료 조건에서 대소문자 무시로 찾음):

| 범주 | 예 |
| --- | --- |
| 외부 공개·전송 | push, PR, deploy, publish, release, 배포, 공개, 게시, 업로드, 이메일 |
| 삭제·제거 | delete, remove, drop, purge, 삭제, 제거, 지우, 폐기, 초기화 |
| 비용 | cost, billing, paid, 결제, 비용, 유료, 구매, 구독, 요금 |
| 외부 서비스·네트워크 | api, http, network, webhook, crawl, LLM, OpenRouter, Gemini, GPT, Ollama, 외부 API, 네트워크 |
| 보안·권한·자격 증명 | permission, credential, password, token, secret, api key, allowlist, 권한, 보안, 토큰, 인증 |
| 설치·의존성 | install, pip, npm, dependency, download, 설치, 의존성, 다운로드 |
| 자동·백그라운드 실행 | schedule, cron, background, daemon, dispatcher, queue, 스케줄, 백그라운드, 자동 실행 |

- 목록은 일부러 넓다. 잘못 붙은 `needs_owner`는 Owner가 한 번 보면 되지만, 잘못 붙은 `auto`는 Owner를 건너뛴다.
- 신호 목록은 안전 경계가 아니다. 문구를 피해 쓴 계획을 막지 못한다. 실제 실행에서는 지금처럼 파이프라인의 범위 검사, 보호 경로,
  금지 문구, Reviewer, QA가 경계이고, 판정은 그 앞의 첫 거름망이다.
- 읽기 전용 작업은 경로가 kind 밖이어도 `auto`일 수 있다(바뀌는 파일이 없으므로). 보호 경로와 `.env`는 읽기 전용이어도 `forbidden`이다.
- 보호 파일을 담은 폴더(`apps/studyroom/`처럼)는 그 자체로 `forbidden`이 아니다. 그 파일 하나의 변경은 실행 때 범위 검사가 거절한다.
- 판정 버전 `policy-gate-v0-dry-run`은 Owner 승인 전 제안이다. `auto`는 "이 기준이면 Owner 없이 갈 후보"라는 뜻일 뿐 실행 권한이 아니다.

## 4. 기존 단일 작업 파이프라인의 재사용

하위 작업 하나는 지금의 Worker 실행 한 번과 같은 단위로 설계했다.

- `kind`와 `paths`는 `WORK_KINDS`의 허용 경로와 같은 언어다. 실행 단계가 오면 하위 작업 하나가 `run_pipeline(work_kind=...)` 한 번이 된다.
- `mode: read_only`는 지금의 읽기 전용 확인·보고(`run_report`)에 대응한다.
- `acceptance`는 Reviewer가 대조할 완료 조건이 된다.
- 순차 실행이면 하위 작업의 baseline을 목표 전용 브랜치의 끝으로 잡아, 지금의 ff-only 반영 규칙을 그대로 쓸 수 있다(병렬은 그 뒤).

## 5. 팀장의 `worker_request`를 Worker에게 전달하는 방안

현재: Worker와 Reviewer는 Owner의 `/work` 원문만 받는다(`bot_minimal._worker_request_for`). 팀장의 지시는
Owner에게 보이기만 한다. 이유는 Reviewer가 diff를 **Owner 승인 원문**에 대조하기 때문이다. 팀장의 말이
승인 원문 자리에 들어가면 팀장이 승인 범위를 스스로 넓힐 수 있다.

제안: 지시 묶음(instruction bundle). 승인의 근거는 계속 Owner 원문이고, 팀장의 지시는 그 아래의 구체화로 함께 전달한다.

| 묶음 항목 | 출처 | Worker | Reviewer |
| --- | --- | --- | --- |
| Owner 목표 원문 | `/goal` 원문 | 받음(최상위 목표) | 승인 원문으로 대조 |
| 목표 계획 승인 원문 | Owner의 계획 승인 메시지(계획 hash 포함) | — | 승인 원문으로 대조 |
| 하위 작업 지시 | 팀장 `worker_request`, `purpose` | 받음(팀장 지시로 표시) | 목표 원문과 승인된 계획 안인지 검사 |
| 완료 조건 | 팀장 `acceptance` | 받음 | candidate가 충족하는지 검사 |
| 범위 | kind, paths, 판정과 정책 버전 | 받음 | 범위 검사와 함께 대조 |

- Reviewer 계약에 두 검사를 더한다. (1) 팀장 지시가 Owner 목표 원문과 승인된 계획(hash 일치) 밖으로 나가면 finding.
  (2) 완료 조건을 충족하지 못하면 finding. 승인 원문이 Owner의 말이라는 규칙은 바꾸지 않는다.
- 구현 지점: task 기록에 `goal_id`, `goal_task`(T번호), 계획 hash를 두고, `_worker_request_for`가 묶음을 만들며,
  Worker 프롬프트와 Reviewer 호출(`approval_command`, Manager 요약 자리)이 묶음을 받는다. Reviewer 정의
  `.claude/agents/reviewer.md`와 SOP §10.2에 검사를 적는다.
- 이번 단계에서는 구현하지 않는다. 계획 hash와 하위 작업 필드는 이 연결을 위해 미리 만들었다.

## 6. Discord `/goal` UX

이번 단계에 구현한 것:

1. Owner가 `/goal <목표>`를 보낸다(Owner 전용, 1500자 이하). 다른 사용자는 `unauthorized`다.
2. 봇이 바로 "목표 계획 시작 (dry-run)"으로 답하고 그 메시지에 스레드를 연다.
3. 팀장이 끝나면 스레드에 올린다:
   - 개요: goal id, 목표 요약, 하위 작업 수와 판정 집계, 단계별 실행 순서(작업마다 판정 표시), 진행 흐름, 목표 문장의 주의 신호,
     계획 파일 경로, 계획 hash, 팀장 사용량 추정, "실행하지 않았습니다 … auto 판정도 실행 권한이 아닙니다".
   - 하위 작업 블록(순서대로, 메시지마다 2000자 이하): 판정 표지(✅ auto, 🟡 needs_owner, ⛔ forbidden), 종류와 허용 경로,
     방식, 팀장 위험도, 목적, 선행 작업, 경로, 완료 조건, Worker 지시(제안), 팀장의 Owner 결정 사유, 판정 근거.
4. 실패하면 사유 코드만 보인다(모델 답이나 오류 출력은 보내지 않음). 다른 팀장이 실행 중이면 `lead_busy`다.

다음 단계 제안(구현 안 함):

| 명령 | 뜻 | 선행 조건 |
| --- | --- | --- |
| `/goal <goal-id> show` | 계획 파일을 다시 보인다 | 계획 파일을 읽는 기능 |
| `/goal <goal-id> replan <지시>` | 같은 목표를 Owner 지시와 함께 다시 계획 | — |
| `/goal <goal-id> approve` | 계획 hash를 묶어 Owner가 계획을 승인(5절의 승인 원문) | Owner 정책 결정 |
| `/goal <goal-id> stop` | 진행 중인 목표를 멈춘다 | Dispatcher가 생긴 뒤 |
| `/goal <goal-id> accept`·`reject` | 목표 전체 결과를 한 번에 최종 승인·거절 | 목표 브랜치 통합이 생긴 뒤 |

## 7. Console UX 제안 (구현 안 함)

- Console은 지금 task 상태 화면과 Preview + Confirm 전이만 한다. 목표 화면은 그 원칙대로 **읽기 전용**으로 시작한다.
- Project Control에 "Goals" 영역: 계획 파일 목록(goal id, 생성 시각, 하위 작업 수, 판정 집계).
- 목표 상세: 단계별 표(작업, 판정 배지, 선행 작업, 완료 조건, 경로), 판정 근거, 계획 hash. 실행·승인 버튼은 두지 않는다.
- 하위 작업이 task가 되는 단계부터 각 행에 연결된 task id와 상태를 보인다.

## 8. 다음 단계에 필요한 Owner 결정

| 결정 | 선택지 | 근거 |
| --- | --- | --- |
| 자동 실행 허용 범위 | (a) 계속 dry-run만 (b) `auto` 중 읽기 전용만 Owner 승인 없이 (c) `auto` 수정 작업까지 목표 브랜치 안에서 | master-plan 잠금과 SOP §9를 바꾸는 결정 |
| 승인 단위 | (a) 하위 작업마다 지금처럼 `/go`·`accept` (b) 계획 승인 1회 + 목표 결과 최종 승인 1회 | task-0220의 "Owner 최종 승인 없이 main 불변" 유지 여부 |
| Policy Gate 기준 | v0 규칙을 그대로 승인 / 범주 추가·제거 / 경로 규칙 조정 | `auto` 기준은 코드와 승인 문서가 함께 정해야 함 |
| 지시 묶음 | 5절 방식 채택 여부, Reviewer 계약 변경 | 승인 원문 결속 규칙의 변경 |
| 예산 | 목표당 비용 상한과 시도 횟수 상한의 값, 넘으면 멈춤 | 팀장 사용량 추정은 이미 보임 |
| 계획 저장 | 계획 파일을 Goal Store로 승격할지(SOP §9 queue persistence와의 관계) | 지금은 검토 자료일 뿐 |
