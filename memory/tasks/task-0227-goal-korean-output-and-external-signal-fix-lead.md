# task-0227-goal-korean-output-and-external-signal-fix-lead

- id: `task-0227-goal-korean-output-and-external-signal-fix-lead`
- title: `/goal: 팀장 출력 한국어 일관성과 외부 서비스·네트워크 신호 오판 수정`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-11-11 03:57 UTC`
- updated_at: `2026-11-11 04:59 UTC`
- summary: `재시작한 봇의 실제 /goal 계획에서 팀장 설명이 영어와 한국어로 섞였고, /api/ 경로만 적은 하위 작업에 외부 서비스·네트워크 신호가 붙었다. 팀장 안내에 Owner가 읽는 모든 설명을 한국어로 쓰라는 규칙을 넣고, Policy Gate가 경로·파일 이름 속 api와 URL만으로는 외부 서비스 신호를 붙이지 않되 실제 호출과 외부 서비스 의존은 그대로 잡게 한다. 스레드 동작, 대시보드, Console 역할, task 생성·Worker 실행 권한은 범위 밖이다.`
- source_command: `Owner 지시: task-0227을 진행하자 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `913a347d10f578f7251d324f1539de7a3b79e6b6` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=3`, `repair_count=3` (SOP §5 기본값 1회에 Owner가 두 번 1회씩 증액, repair 1·2·3은 아래 절) |
| 작업 위치 | 저장소 밖 worktree `jarvis-core-worktrees/task-0227-goal-korean-signal`, 브랜치 `work/task-0227-goal-korean-signal`. main 체크아웃은 그대로 둔다 |

## Owner 결정 (원문, 작업 지시)

```text
[Manager 질문]
영어 혼용과 외부 서비스 오판을 task-0227로 고칠까요?

[Owner 답]
task-0227을 진행하자.
이번 작업은 `/goal` 실사용 테스트에서 발견한 문제 중 **1번(한국어 출력 혼용)과 2번(외부 서비스·네트워크 오판)**만 수정한다.
1. 한국어 출력 일관성

* `goal_plan.py`의 팀장 프롬프트에 사용자에게 표시되는 모든 설명을 자연스러운 한국어로 작성하도록 명시한다.
* 목표 요약, 하위 작업 제목, 목적, 진행 흐름, 완료 조건, Worker 지시, Owner 결정 필요 사유, 정책 판정 근거를 모두 포함한다.
* 코드 식별자, 파일 경로, API 경로, 고유 명칭은 필요한 경우 원문을 유지해도 된다.
* 실제 출력 검증 테스트를 추가한다.

2. 외부 서비스·네트워크 오판 수정

* `/api/`, `GET route`, URL 문자열 등 단순 경로·문서 표현만으로 외부 서비스 호출 신호가 발생하지 않도록 한다.
* 실제 외부 네트워크 요청이나 외부 서비스 의존성이 있는 경우에는 기존처럼 탐지해야 한다.
* 실제 호출 여부와 단순 API 경로 표현을 구분하는 테스트를 추가한다.
* 기존 정상 탐지 사례가 회귀하지 않는지 확인한다.

3. 스레드 생성 문제

* 이번 `/goal`은 DM에서 실행했다.
* DM에는 서버(Guild) 정보가 없으므로 메시지 스레드를 만들 수 없는 것이 정상적인 플랫폼 차이다.
* 현재의 `using the channel` fallback은 정상 동작으로 취급한다.
* 이번 task에서는 스레드 관련 코드를 수정하지 않는다. 서버 채널에서 발생하는 스레드 생성 실패까지 임의로 해결하려 하지 않는다.

작업 범위 및 절차

* task-0227로 진행한다.
* 먼저 관련 코드, 기존 테스트, SOP를 읽고 수정 계획을 세운다.
* 승인된 두 문제만 최소 변경으로 수정한다.
* 대시보드 구현이나 Console 역할 변경은 절대 포함하지 않는다.
* 실제 Task 생성·Worker 실행 권한을 확대하지 않는다.
* `jarvis.bat`, `.env` 및 보호 경로는 열거나 수정하지 않는다.
* 테스트, Reviewer, QA를 기존 SOP에 따라 진행한다.
* 실패하거나 추가 Owner 결정이 필요한 사항은 임의로 범위를 확대하지 말고 보고한다.
* push와 봇 재시작은 하지 않는다. 최종 결과를 보고하고 Owner 승인을 기다린다.
```

질문 앞 Manager 보고(Manager 문장, 승인 원문 아님)는 재시작한 봇의 실제 `/goal` 결과에서 세 가지를 짚었다. 1) 진행 흐름, 완료 조건, Worker 지시, Owner 결정 필요 설명이 대부분 영어였다. 2) T1·T2·T3에 실제 외부 호출 없이 "외부 서비스·네트워크" 근거가 붙었다. 3) 스레드를 만들지 못하고 채널에 올렸다.

## 조사 (baseline 기준)

- Owner가 붙여 넣은 봇 답(`goal-20261111-034857-999`, 계획 hash `4d0a6b2a887b`, 하위 작업 6개 모두 needs_owner)에서 진행 흐름은 "No registered kind covers apps/jarvis-console/ or docs/, …"처럼 영어였고, T1의 Worker 지시와 Owner 결정 필요, T2~T6의 완료 조건 대부분이 영어였다. 목표 요약, 대부분의 목적, 판정 근거(코드가 붙이는 라벨)는 한국어였다.
- `goal_plan.goal_prompt`는 영어로 쓰였고 출력 언어를 정하는 문장이 없다. task-0226 QA의 실제 실행이 한국어로 나온 것은 프롬프트가 정한 결과가 아니었다.
- `policy_gate.OWNER_SIGNALS`의 `external_service`에 `\bapi\b`와 `\bhttp`가 있다. 앞의 것은 `/api/overview`, `GET /api/overview`의 `api`에, 뒤의 것은 모든 `http://`·`https://` URL과 `http.server`에 걸린다. T1(목적의 `/api/history`), T2(완료 조건의 `GET /api/overview`), T3(완료 조건의 `GET /api/overview`)이 이 때문에 근거를 받았다. "GET route"라는 말 자체는 어느 신호에도 걸리지 않는다.
- 판정 근거 라벨(`policy_gate.REASON_LABELS`)은 모두 한국어이고, 모르는 코드만 그대로 보인다. 봇의 고정 문구(`bot_minimal._goal_reply_messages`, `_goal_task_block`)도 한국어다.
- 봇 출력 `discord-bot.out.log`의 `[thread] create failed (ValueError); using the channel`은 DM에서 `/goal`을 실행한 결과다(Owner 답 3번). 이 task에서는 다루지 않는다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/worker/goal_plan.py`, `orchestrator/worker/policy_gate.py`, `orchestrator/worker/run_smoke_tests.py`, `adapters/discord/README.md`, 이 task 기록 |
| deny | `adapters/discord/bot_minimal.py`(스레드 포함), `orchestrator/worker/claude_worker.py`, `orchestrator/worker/claude_lead.py`, Console 전체(대시보드·역할 변경), `docs/jarvis-multi-agent-sop-v0.1.md`, `docs/lead-goal-plan-design.md`(History), `docs/master-plan.md`(DONE 전), 작업 종류 추가, task 생성·Worker 실행 권한, 다른 task 기록, validator, `jarvis.bat`, `.env`, 보호 경로, push, 봇 재시작 |

## Start

Console(worktree에서 띄움) Voice Inbox의 Create Local Task Preview를 확인하고 Confirm해 TODO 기록을 만들었다. Project Control의 Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다. Console은 수정 전에 껐다. 그 뒤 title·summary·source_command를 이 task 내용으로 고쳤다.

## 구현

- `orchestrator/worker/goal_plan.py`: 팀장 안내 규칙에 한 줄을 더했다. Owner가 읽는 설명(`goal_summary`, `flow`, 하위 작업의 `title`, `purpose`, `acceptance`, `owner_decision`, `worker_request`)을 자연스러운 한국어로 쓰고, 코드 식별자, 파일 경로, API 경로, 고유 명칭은 필요하면 원문대로 두며, `id`, `kind`, `mode`, `risk`, `paths`는 정해진 형식 그대로라는 내용이다. 파서는 바꾸지 않았다. 답의 언어를 코드로 검사해 거절하면 새 실패 경로가 생기므로 넣지 않았다(Manager 해석, 아래 A 행).
- 정책 판정 근거는 팀장이 아니라 Policy Gate가 붙이는 한국어 라벨이라 프롬프트로 바꿀 것이 없다. 모든 라벨이 한국어이고 답에 그대로 보이는지를 smoke로 확인한다.
- `orchestrator/worker/policy_gate.py`의 `external_service` 신호:
  - `\bapi\b`를 `(?<![/.])\bapi\b(?!/|\.\w)`로 바꿨다. 경로나 파일 이름의 일부인 `api`(`/api/overview`, `api/overview`, `api.py`, `x/api`)는 신호가 아니고, 단어 `api`("the API returns", "외부 API로", "REST-API")는 그대로 신호다.
  - `\bhttp`를 `\bhttp(?!s?://|\.server\b)`로 바꿨다. URL scheme `http://`·`https://`와 모듈 이름 `http.server`만 빠지고, `http`로 시작하는 나머지 단어("HTTP request", "HTTP 요청", `httpx`, `http_client`, `http.client`)는 그대로 신호다.
  - 이 PC가 아닌 주소의 URL은 같은 문장 안에서 가져오거나 호출하거나 연결하거나 보낸다는 말과 함께 있을 때만 신호다(repair 1: 그 말이 URL 앞이든 뒤든, 영어든 한국어든). 이 PC는 호스트 이름이 정확히 `localhost`·`127.0.0.1`(`localhost.example.com`은 밖)이거나 `[::1]`인 경우다. 그 말은 fetch·request·call·query·get·post·send·poll·crawl·scrap·download·upload·load·connect·access·sync·stream으로 시작하는 영어 단어와 가져·호출·요청·받아·받는·수집·접속·전송·보내·보낸·다운로드·업로드·연결·동기화·불러다. repair 2: 외부 서비스 신호를 볼 때만 URL을 통째로 표지 단어(`externalurl`, 이 PC 주소는 `localurl`)로 바꾸고 `GET /api/overview` 같은 HTTP 메서드와 route를 `route`로 바꾼 글을 읽는다. repair 3: 경로 없이 route를 가리키는 말 앞의 메서드("GET route", "GET or POST endpoint", "GET/POST route", "GET 경로")도 `route`가 된다. "GET 요청"처럼 요청을 말하면 메서드가 호출하는 말로 남는다. URL 안의 글자와 route의 메서드는 그 말로 세지 않는다. 다른 신호 범주는 바뀌지 않은 원래 글을 읽는다.
  - 나머지 `external_service` 신호(network, webhook, crawl, scrap, llm, 외부 서비스 이름, 외부 서비스, 외부 api, 네트워크, 크롤, 스크래핑)와 다른 범주는 바꾸지 않았다. 판정을 느슨하게만 만드는 변경이며 대상은 경로·파일 이름 속 `api`, URL, 모듈 이름 `http.server`뿐이다.
- `orchestrator/worker/run_smoke_tests.py`(새 검사 5건):
  - 팀장 안내에 한국어 규칙이 있고 설명 필드 일곱 개와 원문 유지 예외를 모두 말하는지
  - 경로·route·URL만 있는 문장 21개(Owner가 붙여 넣은 실제 계획의 T1 목적, T2·T3 완료 조건 문장, repair 2·3 Reviewer 지적의 URL 안 동사, route·문서 링크, 경로 없는 "GET route"·문서 링크 문장 포함)에 외부 서비스 신호가 없는지
  - 실제 호출·외부 서비스 문장 31개(기존 검사의 "외부 API로 번역한다", self-review 지적의 `httpx`, `http_client`, `REST-API`, `localhost.example.com`, `upload`, Reviewer 지적의 URL 뒤 동사·다운로드·업로드·연결·connect·access 포함)에 신호가 그대로 붙는지
  - `/api/` 경로만 적은 하위 작업에는 근거가 없고 외부 URL을 가져오는 하위 작업에는 근거가 붙는지
  - Console 목표 사례의 봇 답에 팀장의 한국어 설명 전부와 판정 근거의 한국어 라벨이 그대로 보이고, 모든 라벨이 한국어인지
- `adapters/discord/README.md` `/goal` 2·3항: 한국어 안내(코드 검사는 아님)와 외부 서비스 신호가 붙는 경우와 붙지 않는 경우를 적었다. SOP §10.1 문단은 신호 목록을 말하지 않아 고치지 않았다.

## Implementer 검증 (작업 트리, candidate 전)

- 첫 실행: Worker smoke total=766 failed=0(baseline 761에 새 검사 5건, 기존 신호·목표 계획 검사 그대로 통과), SOP validator PASS, Discord `--self-check-suite` rc=0, `git diff --check` 통과, 사전 점검 PASS.
- self-review 수정 뒤 다시 돌린 결과는 아래 Self-review 절에 적는다.

## Self-review

SOP §3대로 staged 변경에 `claude -p --agent self-reviewer --tools Read,Grep,Glob`을 한 번 돌렸다(Reviewer 판정 아님, 사용량 추정 $0.38). 지적 세 건과 처리:

1. major: 처음 쓴 `\bhttps?\b(?!://|\.\w)`는 baseline `\bhttp`가 잡던 HTTP 클라이언트 단어(`httpx`, `http_client`, `httplib`)를 놓쳐 A13과 어긋났다. `\bhttp(?!s?://|\.server\b)`로 바꿔 URL scheme과 `http.server`만 빼고, `httpx`와 `http_client` 문장을 smoke에 더했다.
2. minor: `api` 앞뒤의 하이픈 제외 때문에 "REST-API" 같은 단어도 빠졌다. 하이픈 제외를 없애 경로·파일 이름 형태만 빼고, "REST-API로 보낸다"를 smoke에 더했다.
3. minor: `localhost\b`가 `localhost.example.com`도 이 PC로 봤고, 동사 목록에 `upload`가 없어 "upload to https://…"를 놓쳤다. 호스트 이름이 정확히 `localhost`·`127.0.0.1`일 때만 이 PC로 보고 `upload`를 더했으며, 두 문장을 smoke에 더했다.

구현 절, Manager 요약 A13·A14, 코드 주석, README 3항을 바뀐 규칙에 맞췄다.

수정 뒤 다시 돌린 결과: Worker smoke total=766 failed=0(새 문장은 기존 신호 검사 안에 더해 검사 수는 같음), SOP validator PASS, Discord `--self-check-suite` rc=0, `git diff --check` 통과, 사전 점검 PASS.

## Reviewer 결과 (candidate `e92063b92ced20aa45c7c8b7064d131d2520e6e3`)

verdict FINDINGS, `self_deviations` 없음, 사용량 추정 $0.54. major 1건: 외부 URL은 URL 앞의 영어 동사나 URL 뒤의 한국어 동사가 있을 때만 신호가 되어, baseline `\bhttp`가 잡던 실제 요청 문장("https://example.com/data.zip 을 다운로드한다", "… 에 업로드한다", "… 에 연결한다", "connect to https://…", "access https://…", "https://example.com/feed is fetched daily")이 신호를 잃는다. A13과 Manager 요약 A13의 충족 주장이 맞지 않는다. Reviewer unverified: candidate에서의 검사 실행 결과, 실제 팀장 답의 한국어(A10, QA 몫), `jarvis.bat` 등을 열지 않았는지(A28), Console Start와 종료.

## Repair 1 (`repair_count=1`)

- 동사 목록을 하나로 합쳐 URL 앞이든 뒤든 같은 문장(마침표·세미콜론 전, 60자 안)에 있으면 신호로 보게 했다. 영어에 connect·access·sync·stream을, 한국어에 다운로드·업로드·연결·동기화·불러를 더했다.
- smoke `calls`에 Reviewer가 든 여섯 문장을 더했다. 경로·URL만 있는 13문장은 그대로 신호가 없다("http://localhost:8790/api/overview 에 연결한다"처럼 이 PC 주소는 여전히 신호가 아니다).
- 구현 절, Manager 요약 A13·A14, 코드 주석, README 3항을 고쳤다.
- repair 뒤 검증(작업 트리): Worker smoke total=766 failed=0(새 문장은 기존 신호 검사 안에 더해 검사 수는 같음), SOP validator PASS, Discord `--self-check-suite` rc=0, `git diff --check`, 사전 점검.
- 이전 candidate의 Reviewer 결과는 무효이며 새 candidate에 fresh Reviewer와 QA를 돌린다.

## Reviewer 결과 (repair 1 candidate `5bfaa06a03f52176693aefe7a8bbddc15aa1a7c1`)

verdict FINDINGS, `self_deviations` 없음, 사용량 추정 $0.42. 이 절은 candidate 뒤의 기록이라 작업 트리에만 둔다. major 1건: URL 뒤를 보는 규칙의 `\S*?`가 URL 자체로 이어져 URL 경로 안의 동사도 센다("문서에 https://example.com/download 링크를 적는다", ".../docs/getting-started"). URL 앞을 보는 규칙은 route의 `GET`도 동사로 센다("GET /api/overview 형식은 https://example.com/docs 를 따른다"). 그래서 URL 하나나 GET route와 문서 링크만으로 신호가 붙어 승인 2-1과 Manager 요약 A12, README 3항이 맞지 않는다. smoke `not_calls`에 이런 문장이 없다. Reviewer unverified: candidate에서의 검사 실행 결과, 실제 팀장 답의 한국어(A10), `jarvis.bat`·push·봇 재시작(A28, A31), Console Start와 종료. repair 예산이 소진돼 Owner에게 묻는다.

## Owner 결정 (원문, repair 2 증액)

```text
[Manager 질문]
task-0227 repair candidate 5bfaa06에 Reviewer major 1건이 나왔습니다. 외부 URL 판정이 URL 자체의 경로 글자(…/download, …/getting-started)와 route의 GET을 동사로 세서, 'https://example.com/download 링크를 적는다'나 'GET /api/overview 형식은 https://example.com/docs 를 따른다'처럼 URL·route만 있는 문장에도 외부 서비스 신호가 붙습니다(승인 2-1과 어긋남, 판정이 더 엄격해지는 쪽이라 실행 위험은 없음). repair 예산 1회는 소진됐습니다. 어떻게 할까요?

[Owner 답]
repair 1회 증액해 고침 (Recommended)
```

## Repair 2 (`repair_count=2`, Owner 증액)

- `policy_gate.text_signals`가 외부 서비스 범주를 볼 때만 `_mask_urls_and_routes`를 거친 글을 읽는다. 이 PC 주소의 URL은 `localurl`, 그 밖의 URL은 `externalurl`, HTTP 메서드와 바로 뒤의 `/`로 시작하는 route(`GET /api/overview`, `POST /api/tasks`)는 `route`가 된다. URL 호출 규칙 두 개는 `externalurl` 앞뒤의 호출하는 말을 본다. "GET https://…"는 URL이 먼저 표지가 되므로 `get`이 호출하는 말로 그대로 남는다.
- 다른 신호 범주(외부 공개, 삭제, 비용, 보안, 설치, 자동 실행)는 원래 글을 읽어 바뀌지 않았다. URL 경로 속 `push` 같은 단어가 외부 공개 신호를 내는 것은 baseline과 같고 이 task의 범위 밖이다(Manager 해석, 판정을 엄격하게 하는 쪽).
- smoke `not_calls`에 Reviewer가 든 세 문장과 POST route 문장을, `calls`에 "post results to https://hooks.example.com/x"를 더했다.
- 구현 절, Manager 요약 A12·A13·A14, 코드 주석, README 3항을 고쳤다.
- repair 뒤 검증(작업 트리): Worker smoke total=766 failed=0(새 문장은 기존 신호 검사 안에 더해 검사 수는 같음), SOP validator PASS, Discord `--self-check-suite` rc=0, `git diff --check`, 사전 점검.
- 이전 candidate의 Reviewer 결과는 무효이며 새 candidate에 fresh Reviewer와 QA를 돌린다.

## Reviewer 결과 (repair 2 candidate `7ec87d653f5c10308a48c0e9aa38a57bccc3f199`)

verdict FINDINGS, `self_deviations` 없음, 사용량 추정 $0.52. 이 절은 candidate 뒤의 기록이라 작업 트리에만 둔다. major 1건: route 가림은 메서드 바로 뒤에 `/`가 올 때만 동작해, 승인 2-1이 이름을 든 "GET route"(슬래시 없음)의 `get`이 여전히 호출하는 말로 세진다. "새 GET route는 https://example.com/docs 를 따른다"에 외부 서비스 신호가 붙는다(Manager가 재현). 판정 근거는 title·purpose·worker_request·acceptance를 이어 읽으므로 다른 필드의 문서 URL과도 걸린다. Manager 요약 A12·A13, Repair 2 절, README 3항이 이 경우를 덮는다. smoke `not_calls`에 이 문장이 없다. 판정이 더 엄격해지는 쪽이다. Reviewer unverified: candidate에서의 검사 실행 결과, 실제 팀장 답의 한국어(A10), `jarvis.bat`·push·봇 재시작(A28, A31), Console Start와 종료. repair 예산 2회가 소진돼 Owner에게 묻는다.

## Owner 결정 (원문, repair 3 증액)

```text
[Manager 질문]
task-0227 repair 2 candidate 7ec87d6에 Reviewer major 1건이 또 나왔습니다. route 가림이 'GET /경로'처럼 슬래시가 있을 때만 동작해, '새 GET route는 https://example.com/docs 를 따른다'처럼 슬래시 없는 'GET route'와 문서 URL이 함께 있으면 외부 서비스 신호가 붙습니다(재현함, 판정이 더 엄격해지는 쪽이라 실행 위험은 없음). URL 없는 'GET route'만으로는 신호가 없습니다. repair 예산 2회는 소진됐습니다. 어떻게 할까요?

[Owner 답]
repair 1회 더 증액해 고침 (Recommended)
```

## Repair 3 (`repair_count=3`, Owner 증액)

- `_METHOD_ROUTE`가 메서드 뒤의 `/` 경로뿐 아니라 경로 없이 route를 가리키는 말(route, endpoint, path, handler, method, 경로, 엔드포인트, 라우트, 메서드, 핸들러)도 받는다. 메서드가 `/`, 쉼표, or, and, 또는, 이나, 나로 이어진 경우("GET or POST endpoint", "GET/POST route")도 함께 가린다.
- "GET 요청을 https://… 에 보낸다", "get the list from https://…"처럼 요청을 말하는 문장은 그대로 신호다(smoke `calls`에 더함).
- smoke `not_calls`에 Reviewer가 든 문장과 같은 종류 세 문장을 더했다.
- 구현 절, Manager 요약 A12·A14, 코드 주석, README 3항을 고쳤다.
- repair 뒤 검증(작업 트리): Worker smoke total=766 failed=0(새 문장은 기존 신호 검사 안에 더해 검사 수는 같음), SOP validator PASS, Discord `--self-check-suite` rc=0, `git diff --check`, 사전 점검.
- 이전 candidate의 Reviewer 결과는 무효이며 새 candidate에 fresh Reviewer와 QA를 돌린다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문, 작업 지시) | "[Manager 질문]" | 질문의 표지 |
| A2 | Owner 결정 (원문, 작업 지시) | "영어 혼용과 외부 서비스 오판을 task-0227로 고칠까요?" | A4 이하 답의 질문. 짚은 문제는 질문 뒤 문단의 1)·2)이다 |
| A3 | Owner 결정 (원문, 작업 지시) | "[Owner 답]" | 답의 표지 |
| A4 | Owner 결정 (원문, 작업 지시) | "task-0227을 진행하자." | 이 task로 진행한다 |
| A5 | Owner 결정 (원문, 작업 지시) | "이번 작업은 `/goal` 실사용 테스트에서 발견한 문제 중 **1번(한국어 출력 혼용)과 2번(외부 서비스·네트워크 오판)**만 수정한다." | 구현은 이 두 문제뿐이다. 범위 owned 행 |
| A6 | Owner 결정 (원문, 작업 지시) | "한국어 출력 일관성" | 1번 문제의 표제 |
| A7 | Owner 결정 (원문, 작업 지시) | "`goal_plan.py`의 팀장 프롬프트에 사용자에게 표시되는 모든 설명을 자연스러운 한국어로 작성하도록 명시한다." | `goal_prompt` 규칙에 한국어 규칙 한 줄을 더했다(구현 절) |
| A8 | Owner 결정 (원문, 작업 지시) | "목표 요약, 하위 작업 제목, 목적, 진행 흐름, 완료 조건, Worker 지시, Owner 결정 필요 사유, 정책 판정 근거를 모두 포함한다." | 팀장이 쓰는 일곱 필드를 규칙에 이름으로 적었다. 정책 판정 근거는 Policy Gate의 한국어 라벨이라 프롬프트 대상이 아니며, 모든 라벨이 한국어로 보이는지 smoke로 확인한다(Manager 해석) |
| A9 | Owner 결정 (원문, 작업 지시) | "코드 식별자, 파일 경로, API 경로, 고유 명칭은 필요한 경우 원문을 유지해도 된다." | 같은 네 가지 예외를 규칙에 적었고 smoke가 확인한다 |
| A10 | Owner 결정 (원문, 작업 지시) | "실제 출력 검증 테스트를 추가한다." | smoke: Console 목표 사례의 봇 답에 팀장의 한국어 설명과 한국어 판정 라벨이 그대로 보이는지. 실제 팀장의 답은 QA의 실제 dry-run에서 필드별로 확인한다. 답의 언어를 코드로 거절하는 검사는 넣지 않았다(Manager 해석: 새 실패 경로와 범위 확대가 되므로) |
| A11 | Owner 결정 (원문, 작업 지시) | "외부 서비스·네트워크 오판 수정" | 2번 문제의 표제 |
| A12 | Owner 결정 (원문, 작업 지시) | "`/api/`, `GET route`, URL 문자열 등 단순 경로·문서 표현만으로 외부 서비스 호출 신호가 발생하지 않도록 한다." | 경로·파일 이름 속 `api`, URL scheme, `http.server`는 신호가 아니고, URL 안의 글자와 route의 메서드는 호출하는 말로 세지 않는다(repair 2). "GET route"는 URL 없이는 baseline에서도 신호가 아니었고, 외부 문서 URL과 함께여도 repair 3부터 신호가 아니다. smoke가 둘 다 확인한다. 문장 속 단어 `api`("Console API" 같은 내부 API 언급 포함)는 여전히 신호로 남긴다(Manager 해석: 외부 API일 수 있어 넓게 둔다) |
| A13 | Owner 결정 (원문, 작업 지시) | "실제 외부 네트워크 요청이나 외부 서비스 의존성이 있는 경우에는 기존처럼 탐지해야 한다." | 단어 `api`, `http`로 시작하는 단어(`httpx`, `http_client` 포함), network, webhook, 외부 서비스 이름, 한국어 표현은 그대로이고, 외부 URL은 가져오거나 호출하거나 연결하거나 보낸다는 말과 같은 문장에 있으면(앞뒤 순서 무관) 신호다. Reviewer 지적으로 repair 1에서 넓혔다. repair 2에서 URL 안의 글자와 route의 메서드를 그 말에서 뺐다(A12 쪽) |
| A14 | Owner 결정 (원문, 작업 지시) | "실제 호출 여부와 단순 API 경로 표현을 구분하는 테스트를 추가한다." | smoke: 경로·route·URL 문장 21개와 실제 호출 문장 31개, 하위 작업 판정 한 쌍 |
| A15 | Owner 결정 (원문, 작업 지시) | "기존 정상 탐지 사례가 회귀하지 않는지 확인한다." | 기존 신호 검사가 그대로 통과하고, 실제 호출 목록에 기존 사례 "외부 API로 번역한다"를 넣었다 |
| A16 | Owner 결정 (원문, 작업 지시) | "스레드 생성 문제" | 3번 표제. 이 task에서 다루지 않는다 |
| A17 | Owner 결정 (원문, 작업 지시) | "이번 `/goal`은 DM에서 실행했다." | 로그의 `create failed (ValueError)` 원인 |
| A18 | Owner 결정 (원문, 작업 지시) | "DM에는 서버(Guild) 정보가 없으므로 메시지 스레드를 만들 수 없는 것이 정상적인 플랫폼 차이다." | 조사 절 마지막 항목 |
| A19 | Owner 결정 (원문, 작업 지시) | "현재의 `using the channel` fallback은 정상 동작으로 취급한다." | 정상 동작으로 기록한다 |
| A20 | Owner 결정 (원문, 작업 지시) | "이번 task에서는 스레드 관련 코드를 수정하지 않는다." | `bot_minimal.py`를 deny에 두었다 |
| A21 | Owner 결정 (원문, 작업 지시) | "서버 채널에서 발생하는 스레드 생성 실패까지 임의로 해결하려 하지 않는다." | 다루지 않는다 |
| A22 | Owner 결정 (원문, 작업 지시) | "작업 범위 및 절차" | 절차 항목의 표제 |
| A23 | Owner 결정 (원문, 작업 지시) | "task-0227로 진행한다." | A4와 같다 |
| A24 | Owner 결정 (원문, 작업 지시) | "먼저 관련 코드, 기존 테스트, SOP를 읽고 수정 계획을 세운다." | 조사 절. `goal_plan.py`, `policy_gate.py`, 봇 출력 함수, smoke의 목표 계획 검사, SOP §10.1, Discord README를 읽은 뒤 고쳤다 |
| A25 | Owner 결정 (원문, 작업 지시) | "승인된 두 문제만 최소 변경으로 수정한다." | 프롬프트 한 줄, 신호 두 개 교체와 두 개 추가, smoke 5건, README 두 항목 |
| A26 | Owner 결정 (원문, 작업 지시) | "대시보드 구현이나 Console 역할 변경은 절대 포함하지 않는다." | Console은 deny. task 상태 전이에만 썼다 |
| A27 | Owner 결정 (원문, 작업 지시) | "실제 Task 생성·Worker 실행 권한을 확대하지 않는다." | `/goal`은 여전히 계획만 보이고, 신호 변경은 판정 라벨뿐이며 실행 권한이 아니다 |
| A28 | Owner 결정 (원문, 작업 지시) | "`jarvis.bat`, `.env` 및 보호 경로는 열거나 수정하지 않는다." | 열지 않았다. QA가 크기와 수정 시각만 확인한다 |
| A29 | Owner 결정 (원문, 작업 지시) | "테스트, Reviewer, QA를 기존 SOP에 따라 진행한다." | self-review, candidate, Reviewer, QA 순서 |
| A30 | Owner 결정 (원문, 작업 지시) | "실패하거나 추가 Owner 결정이 필요한 사항은 임의로 범위를 확대하지 말고 보고한다." | 실패나 결정 필요 사항은 Owner에게 묻는다 |
| A31 | Owner 결정 (원문, 작업 지시) | "push와 봇 재시작은 하지 않는다." | 하지 않는다 |
| A32 | Owner 결정 (원문, 작업 지시) | "최종 결과를 보고하고 Owner 승인을 기다린다." | QA 뒤 최종 보고를 하고 승인 전에는 main을 바꾸지 않는다 |
| A33 | Owner 결정 (원문, repair 2 증액) | "[Manager 질문]" | 질문의 표지 |
| A34 | Owner 결정 (원문, repair 2 증액) | "task-0227 repair candidate 5bfaa06에 Reviewer major 1건이 나왔습니다." | repair 1 candidate의 Reviewer 지적(위 Reviewer 결과 절) |
| A35 | Owner 결정 (원문, repair 2 증액) | "외부 URL 판정이 URL 자체의 경로 글자(…/download, …/getting-started)와 route의 GET을 동사로 세서, 'https://example.com/download 링크를 적는다'나 'GET /api/overview 형식은 https://example.com/docs 를 따른다'처럼 URL·route만 있는 문장에도 외부 서비스 신호가 붙습니다(승인 2-1과 어긋남, 판정이 더 엄격해지는 쪽이라 실행 위험은 없음)." | Repair 2 절에서 고쳤고 두 문장을 smoke `not_calls`에 넣었다 |
| A36 | Owner 결정 (원문, repair 2 증액) | "repair 예산 1회는 소진됐습니다." | 증액 전 `repair_count=1`, `repair_budget=1` |
| A37 | Owner 결정 (원문, repair 2 증액) | "어떻게 할까요?" | 답은 A39 |
| A38 | Owner 결정 (원문, repair 2 증액) | "[Owner 답]" | 답의 표지 |
| A39 | Owner 결정 (원문, repair 2 증액) | "repair 1회 증액해 고침 (Recommended)" | `repair_budget=2`. Repair 2 절. 증액은 이 task에만 효력이 있다 |
| A40 | Owner 결정 (원문, repair 3 증액) | "[Manager 질문]" | 질문의 표지 |
| A41 | Owner 결정 (원문, repair 3 증액) | "task-0227 repair 2 candidate 7ec87d6에 Reviewer major 1건이 또 나왔습니다." | repair 2 candidate의 Reviewer 지적(위 Reviewer 결과 절) |
| A42 | Owner 결정 (원문, repair 3 증액) | "route 가림이 'GET /경로'처럼 슬래시가 있을 때만 동작해, '새 GET route는 https://example.com/docs 를 따른다'처럼 슬래시 없는 'GET route'와 문서 URL이 함께 있으면 외부 서비스 신호가 붙습니다(재현함, 판정이 더 엄격해지는 쪽이라 실행 위험은 없음)." | Repair 3 절에서 고쳤고 그 문장을 smoke `not_calls`에 넣었다 |
| A43 | Owner 결정 (원문, repair 3 증액) | "URL 없는 'GET route'만으로는 신호가 없습니다." | baseline부터 그렇고 smoke가 확인한다 |
| A44 | Owner 결정 (원문, repair 3 증액) | "repair 예산 2회는 소진됐습니다." | 증액 전 `repair_count=2`, `repair_budget=2` |
| A45 | Owner 결정 (원문, repair 3 증액) | "어떻게 할까요?" | 답은 A47 |
| A46 | Owner 결정 (원문, repair 3 증액) | "[Owner 답]" | 답의 표지 |
| A47 | Owner 결정 (원문, repair 3 증액) | "repair 1회 더 증액해 고침 (Recommended)" | `repair_budget=3`. Repair 3 절. 증액은 이 task에만 효력이 있다 |
