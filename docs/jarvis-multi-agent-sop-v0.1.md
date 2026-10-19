# Jarvis Multi-Agent SOP v0.1

## 1. 목적과 적용 범위

이 문서는 Jarvis-Core의 승인된 개발 milestone을 운영하는 기본 SOP다. Manual
Pilot v0.1A에서 검증한 역할 분리와 evidence 흐름을 반복 가능한 저장소 규칙으로
고정한다. 읽기 전용 질의나 단순 설명에는 Worker 조직을 강제하지 않지만, tracked
file을 바꾸는 개발 work package에는 이 SOP를 기본 적용한다.

이 SOP는 Codex SDK/app-server 연결, 자동 dispatcher, background worker, runtime
queue persistence, 외부 API/LLM, multi-project registry 또는 push/PR 권한을
만들지 않는다. 현재 운영은 Owner가 승인한 bounded work package와 로컬 Codex
task를 이용한 수동 조직 운영이다.

## 2. 공식 조직 구조

```text
Owner
  ↓
Director (primary Codex task)
  ↓
Manager
  ├─ Implementer
  ├─ Reviewer
  ├─ QA
  └─ Docs
```

기본 실행 흐름은 다음과 같다.

```text
Owner milestone approval
→ Director creates or engages Manager
→ Manager fixes work package, dependencies, file ownership and validation
→ Implementer produces a candidate local commit
→ Reviewer examines the exact candidate commit
→ finding이면 Manager가 Repair를 운영하고 새 candidate에 Reviewer를 다시 실행
→ QA validates the same exact candidate commit
→ 실패하면 Manager가 Repair를 운영하고 새 candidate에 Reviewer → QA를 다시 실행
→ optional Docs
→ Manager reconciles reports with Git evidence
→ Manager Report
→ Director Report
→ Owner
```

별도 Dispatcher는 조직 역할로 두지 않는다. Worker orchestration은 Manager의
책임이다.

## 3. 역할 계약

### Owner

- milestone과 권한 경계를 승인한다.
- 구현 세부사항이나 budget 안의 retry/repair에는 개입하지 않는다.
- budget 증액과 escalation gate를 넘는 결정만 내린다.

### Director

- Owner와 소통하는 primary Codex task다.
- 승인된 milestone을 Manager에게 전달하고 Manager의 계획과 최종 결과를 평가한다.
- Worker를 직접 운영하거나 assignment, 순서, retry, repair를 판단하지 않는다.
- 구현 세부사항을 중간 보고하지 않고 최종 Director Report 한 번을 제출한다.
- Manager가 escalation한 사안을 bounded Owner decision으로 정리한다.

현재 Codex 표면에서 Manager의 nested spawning이 지원되지 않거나 불명확하면
Director가 Manager의 확정된 assignment plan에 따라 Worker task를 기계적으로
생성할 수 있다. 이 fallback은 task 생성 위치에 관한 것으로, Worker 선택·순서,
repair·retry와 pass/fail 판단은 계속 Manager가 소유한다. nested spawning을
지원한다고 가정하거나 가장하지 않는다.

### Manager

- Worker orchestration의 유일한 논리적 책임자다.
- 시작 전에 branch, baseline HEAD와 exact `git status --short`를 확인한다.
- bounded work package, dependency, target/deny files, file ownership과 가장
  가벼운 충분한 validation profile을 확정한다.
- Implementer → Reviewer → QA → 필요 시 Docs 순서를 관리한다.
- retry 또는 repair 여부와 budget 사용을 결정한다.
- Worker 주장과 실제 branch, HEAD, status, diff, staged paths와 commit evidence를
  대조한다.
- scope 밖 변경, branch/HEAD drift, protected file 변경 또는 evidence 불일치는
  fail closed로 처리한다.
- 최종 Manager Report 또는 한 개의 bounded escalation을 Director에게 제출한다.
- tracked file을 직접 수정하지 않는다.
- Owner 승인 메시지의 포함·제외 조건을 task 기록에 요약 없이 원문 그대로
  인용한다. Manager의 해석은 원문 인용과 구분해 따로 적는다.
- 승인 원문의 조건끼리, 또는 승인 원문과 제안서가 충돌하면 구현을 시작하지
  않고 충돌한 조건을 인용한 bounded question을 Director에게 escalation해 Owner
  결정을 받는다. 그 질문과 답도 원문 그대로 task 기록에 남긴다.
- Reviewer assignment에는 Manager 요약과 함께 Owner 승인 원문을 전달한다.
- candidate(repair candidate 포함)를 커밋하기 전에 변경 파일과 task 기록을 stage한 상태로
  `python -B scripts/check_task_record.py memory/tasks/<task-id>.md --baseline <baseline>`을
  실행하고, 종료 코드가 0이 아니면 candidate를 만들지 않고 출력된 위반(파서·Console 읽기,
  `owned` 행과 staged 파일, `updated_at`, 파일 끝 줄바꿈)을 먼저 고친다(task-0171). 같은 출력의
  승인 원문 인용 목록(task-0169)은 Manager의 참고 자료이며 종료 코드에 영향을 주지 않고,
  이 검사는 Reviewer의 조건 대조나 판정을 대신하지 않는다.

### Implementer

- 한 assignment에서 유일한 source writer다. 병렬 source writer는 허용하지 않는다.
- 승인된 file ownership 안에서만 구현하고 테스트한다.
- self-review와 결정론적 validation 뒤 명시된 파일만 stage한다.
- `git add .`과 `git add -A`를 사용하지 않는다.
- 안전한 candidate local commit과 Worker Report를 만든다.
- push/PR, 외부 호출, credential과 protected `jarvis.bat`를 다루지 않는다.

### Reviewer

- Manager가 지정한 exact candidate commit에 고정된다.
- strict read-only로 diff와 관련 contract를 검토한다.
- actionable finding만 severity, evidence와 최소 correction 조건으로 보고한다.
- 허용 명령으로 확인할 수 없는 요구와 주장은 finding이 아니라 `unverified`로,
  자기 명령의 허용 형식 이탈은 `self_deviations`로 보고한다. 판정은 findings로만
  정한다.
- findings가 없으면 Reviewer 단계는 PASS가 될 수 있다. 이 PASS는 task 전체의 PASS나
  DONE이 아니다. `unverified` 항목은 반드시 QA로 넘기고, 최종 acceptance는 QA
  검증 뒤에 결정한다.
- Manager 요약과 Owner 승인 원문을 함께 받고, diff의 범위는 승인 원문을 기준으로
  대조한다. Manager 요약이 승인 원문과 다르면 그 차이를 finding으로 보고한다.
- tracked/untracked file을 수정하거나 stage/commit하지 않는다.
- pass는 QA pass나 release 권한을 뜻하지 않는다.

### QA

- Reviewer pass 후 같은 exact candidate commit을 검증한다.
- tracked source를 수정하지 않는다. workspace write 권한이 필요하면 test temp,
  cache와 runtime artifact에만 사용하고 종료 전에 정리한다.
- unit/deterministic test부터 가장 가벼운 충분한 QA를 선택한다.
- 서버가 꼭 필요할 때만 background로 시작하고 readiness timeout을 적용한다.
- 성공·실패와 무관하게 소유 PID, temp artifact와 대상 listener를 정리하고
  cleanup evidence를 보고한다.
- docs/config-only 단계에는 서버와 브라우저를 실행하지 않는다.

### Docs

- 변경 성격에 따라 QA 뒤에 순차 실행하거나 `not_required`와 이유를 기록한다.
- 실행할 때는 Manager가 지정한 documentation file ownership만 수정한다.
- 제품 source, runtime 또는 다른 Worker의 파일을 수정하지 않는다.
- Docs 변경으로 candidate commit이 바뀌면 이전 Reviewer/QA evidence는 전부
  무효가 되며 새 candidate에 Reviewer → QA를 다시 실행한다.

## 4. File ownership과 candidate 규칙

1. Manager는 assignment마다 owned files와 deny files를 exact path로 기록한다.
2. Implementer 한 명만 product source를 쓴다.
3. Reviewer와 QA는 candidate commit hash를 받기 전 시작하지 않는다.
4. Reviewer와 QA report에는 검증한 full commit hash를 기록한다.
5. tracked file이 바뀌는 repair 또는 Docs sync는 새 candidate commit을 만든다.
6. **candidate commit 변경 시 기존 Reviewer/QA 결과는 전부 무효**다.
7. 새 candidate는 반드시 fresh Reviewer → fresh QA 순서를 다시 통과한다.
8. Manager는 final HEAD, candidate hash와 report hash가 모두 같은지 대조한다.

## 5. Retry와 Repair budget

모든 package의 초기값은 다음과 같다.

```text
retry_budget=1
retry_count=0
repair_budget=1
repair_count=0
```

- Retry는 source 변경이 없는 test 재실행, 일시적 환경 복구 또는 동일 candidate의
  evidence 재수집이다. retry를 실행할 때 `retry_count += 1`이다.
- Reviewer 보고의 `self_deviations`로 무효가 된 검토의 재검토와, Manager 요약·승인
  원문 전달 누락(호출 결함)을 고친 같은 candidate의 재검토는 candidate를 바꾸지
  않으므로 retry이며 repair 예산을 쓰지 않는다. `self_deviations`에 따른 재검토는
  한 candidate에 1회까지이고, 재검토에서도 다시 나오면 그 검토는 실패로 보고
  Manager가 Director에게 escalation한다.
- Repair는 Reviewer finding 또는 QA 실패를 해결하기 위해 tracked source를 바꾸는
  correction이다. source-changing repair마다 `repair_count += 1`이다.
- budget 1은 Manager가 Owner 개입 없이 해당 동작을 한 번 실행할 수 있다는 뜻이다.
- 다음 retry/repair가 필요한 시점에 count가 budget과 같으면 budget이 소진된
  것이므로 실행하지 않고 Manager → Director로 escalation한다.
- budget 안의 retry/repair는 Manager가 결정하며 Owner에게 중간 승인 요청을 하지
  않는다.
- budget 증액은 Owner만 결정할 수 있다.
- repair가 candidate를 바꾸면 모든 이전 Reviewer/QA evidence를 무효화하고 새
  Reviewer → QA를 실행한다.

## 6. Budget과 무관한 즉시 escalation

다음 조건은 남은 budget과 관계없이 작업을 멈추고 Manager → Director로
escalation한다.

- 승인된 scope 또는 권한 확대
- `jarvis.bat` 접근·수정·stage·commit 필요
- 외부 API/LLM, credential 또는 secret 필요
- destructive action이나 복구하기 어려운 변경 필요
- push 또는 PR 필요
- 기존 안전 계약과 승인된 요구의 충돌
- baseline 이후 예상하지 못한 저장소 변경, branch/HEAD drift 또는 file ownership 충돌

Owner 승인 원문의 조건끼리 또는 승인 원문과 제안서가 충돌하는 경우는 위 목록의
안전 계약·승인 요구 충돌 gate(`gate_safety_conflict`)에 해당한다. 별도 gate를 두지
않고 구현 전에 §3 Manager의 bounded question을 위와 같이 Manager → Director로
escalation해 처리한다.

Director는 필요한 Owner 결정 한 가지만 명확히 보고한다. 안전하게 좁힐 수 없는
상태를 추정으로 통과시키지 않는다.

## 7. Evidence와 보고 흐름

Worker의 보고는 주장이며 Git evidence를 대신하지 않는다. Manager는 최소한 다음을
직접 대조한다.

- branch와 baseline/final HEAD
- 시작·candidate·final `git status --short`
- candidate commit의 exact changed paths와 diff
- staged paths가 승인된 ownership과 같은지
- Reviewer/QA가 기록한 full hash가 candidate와 같은지
- protected file, scope 밖 파일, secret, external call, push/PR 부재
- QA temp/process/listener cleanup

Worker Report는 역할, assignment, candidate hash, changed paths, 실행한 validation,
finding/결과와 cleanup을 포함한다. Manager Report는 milestone result, budget 사용,
역할별 결과, evidence reconciliation, risk, escalation 또는 다음 추천을 포함한다.
Director Report는 Owner outcome, milestone result, bounded risk, Owner decision과
다음 추천만 보여주며 상세 Manager evidence는 펼쳐보는 증거로 남긴다.

## 8. Fail-closed 완료 조건

다음 조건을 모두 만족해야 Manager가 완료를 보고할 수 있다.

- exact candidate에 Reviewer pass
- 같은 exact candidate에 QA pass
- 필요한 Docs가 완료됐거나 `not_required` 이유가 있음
- candidate 변경 뒤 stale Reviewer/QA evidence가 사용되지 않음
- 실제 Git evidence와 Worker Report가 일치함
- scope 밖 변경과 동시 source writer가 없음
- `jarvis.bat`가 untouched/untracked 상태임
- push/PR, 외부 호출과 escalation gate 위반이 없음
- runtime artifact와 listener가 남지 않음

조건 하나라도 증명할 수 없으면 완료로 추정하지 않고 blocked 또는 escalation으로
보고한다.

DONE 경로는 두 가지다. 수동 SOP 작업의 DONE은 위 조건을 만족한 뒤 Owner가 Jarvis
Console Complete(Preview + Confirm)로 결정한다. §10 Worker 파이프라인의 자동
DONE은 §10.2의 적용 조건을 만족할 때만 파이프라인이 기록한다.

Owner의 minor finding 수용(수동 경로 한정). Reviewer FINDINGS의 지적이 모두
minor이면 Owner는 지적별로 수용할 수 있고, 그때 같은 candidate로 QA를 진행한다.

- blocking과 major는 수용할 수 없다.
- 지적마다 Owner의 수용 원문을 task 기록에 남긴다.
- 수용은 그 candidate에만 효력이 있고 candidate가 바뀌면 무효다.
- QA는 그대로 전부 통과해야 하며 수용이 QA를 대신하지 않는다.
- Manager는 finding을 수용할 수 없다.
- §10 Worker 파이프라인에는 적용하지 않는다.

## 9. 현재 자동화 경계와 성숙도

이 SOP는 조직 계약과 project custom-agent 설정을 제공하지만 Hermes가 자동으로
Worker를 실행하는 runtime은 아니다. SDK/app-server, dispatcher subsystem,
background execution과 queue persistence는 별도 승인 전까지 금지다. §10의 승인된
예외는 이 금지에서 제외되며 그 범위와 규칙은 §10을 따른다.

Manual Pilot v0.1A는 실제 Implementer candidate에서 Reviewer가 P2 finding을 찾고,
Manager가 repair 1회를 지시한 뒤 새 candidate에 Reviewer와 QA를 다시 실행해
완료했다. 이 SOP의 채택은 완료됐지만 운영 성숙도를 확정하려면 실제 기능
work package 1~2개에서 같은 흐름을 반복 성공해야 한다. 그 뒤에만 Hermes 자동
runtime 검토를 제안한다.

## 10. 승인된 예외: Worker 파이프라인

Owner 승인(task-0142, 보완 task-0144·task-0145)에 따라 Discord 봇이 Worker
파이프라인 `orchestrator/worker/claude_worker.py`를 실행한다. 이 절은 §9 금지의
예외이며 두 부분으로 나뉜다. §10.1은 현재 실행 범위이고, §10.2는 범위 값과 무관한
파이프라인 규칙이다.

### 10.1 현재 실행 범위 (v0.2, 일반 규칙 아님)

아래 값은 task-0142 Owner 승인이 정하고 task-0164 Owner 승인이 Daily AI Radar 작업 종류와 프로세스 간
잠금으로 넓힌 현재 실행 범위다. 범위를 넓히거나 바꾸려면
새 Owner 승인과 이 표의 갱신이 필요하며, 다른 작업이나 저장소 전체의 규칙으로
해석하지 않는다.

| 항목 | 현재 값 | 코드 위치 |
| --- | --- | --- |
| 지원 작업 | `studyroom_content`(Studyroom 콘텐츠 수정, 표지어 studyroom·스터디룸), `daily_ai_radar`(Daily AI Radar 수정, 표지어는 앱 이름 daily ai radar·daily-ai-radar·daily_ai_radar·데일리 ai 레이더이고 radar·레이더 같은 일반 단어만으로는 고르지 않음). 표지어가 함께 있으면 표의 앞 항목(Studyroom)이 우선한다. `/work`는 표지어가 없으면 hold. `/go`는 task 제목으로 종류를 정하며 표지어가 없으면 기존처럼 studyroom_content | `WORK_KINDS` |
| Worker 변경 허용 경로 | `apps/studyroom/content/`(studyroom_content), `apps/daily-ai-radar/`(daily_ai_radar) | `allowed_prefix` |
| 파이프라인 보호 경로 | `jarvis.bat` | `PROTECTED_PATHS` |
| 테스트 명령 | `apps/studyroom/run_smoke_tests.py`(studyroom_content), `apps/daily-ai-radar/run_smoke_tests.py`(daily_ai_radar) | `test_script` |
| worktree 위치 | 저장소 밖 `C:\work\jarvis-core-worktrees\` | `WORKTREE_ROOT` |
| 진입 명령 | Owner 전용 `/work`, `/go`(`resume`, `accept`, `recover` 포함), 동시 실행 1개. 프로세스 안 잠금과 저장소 밖 파일 잠금을 함께 잡아 다른 봇 프로세스의 실행도 `worker_busy`로 거절. `/work`로 만든 DOING task는 실행 중인 Worker(두 잠금, 그리고 살아 있는 프로세스를 가리키는 실행 표지)가 없으면 이전 실행 기록과 관계없이 멈춤으로 보고, `/go`는 `stalled_doing`으로 알리기만 하고 상태는 바꾸지 않음(task-0167). 그 밖의 DOING task는 기존처럼 실행 기록이 없을 때 `doing_without_execution_record`. `/work`로 만든 task에 대한 `/retry`는 거절하고 `/go`로 안내. 실행 중에는 실제로 들어간 단계(Worker·Reviewer·repair·QA·통합)마다 같은 채널에 한 줄씩 보고하고(멘션 없음, 보고 실패는 실행에 영향 없음), 실패와 Owner 판단 필요 결과는 설정된 Owner를 멘션해 구분한다. 봇 시작 시 `/work`로 만든 task 중 멈춘 DOING(task-0167 판정)과 봇 없이 Worker가 아직 실행 중인 DOING을 프로세스당 한 번 Owner DM으로 알리고(그 밖의 DOING은 건수만), 상태는 바꾸지 않음(task-0165) | `bot_minimal.py` |

작업 종류의 값(종류 이름, 허용 경로, 테스트 스크립트)은 `orchestrator/worker/claude_worker.py`의
`WORK_KINDS` 한 곳에 있고, 위 표는 종류마다 그 값을 적는다. 첫 항목 Studyroom이 기본값이며 기존
이름 `WORK_KIND`·`ALLOWED_PREFIX`·`TEST_COMMAND`는 그 항목을 가리킨다.

`jarvis.bat` 금지 자체는 이미 AGENTS.md와 §6의 일반 gate다. §10.1은 파이프라인
범위 검사가 이것을 강제한다는 사실만 적고 새 규칙을 만들지 않는다.

### 10.2 파이프라인 규칙

1. Candidate. Worker 변경은 attempt 브랜치의 candidate commit으로만 만들어진다.
   이전 시도의 worktree와 branch는 삭제하지 않는다.
2. Reviewer 호출. Owner 요청 원문, baseline..candidate 변경 파일 목록, 범위
   기대값만 전달한다. Worker 동작이나 테스트 결과를 주장하지 않는다. evidence는
   candidate 시점 기준의 읽기 전용 파일이며, 요청에 이름이 나온 task 기록과
   요청 또는 baseline..candidate 추가 줄에 적힌 저장소 상대 경로 파일이다(task-0170).
   절대 경로·`..`·URL·디렉터리·와일드카드는 쓰지 않고, candidate tree에 있는 파일만
   쓰며, `jarvis.bat`·`.env` 계열·task 자신의 기록·보호 경로는 빼고 개수만 남긴다.
   변경 파일은 다시 넣지 않고 소스 파일은 정렬해 최대 10개다. 파일 내용은 사실 확인용
   데이터로만 다룬다.
3. 판정 처리. PASS면 QA로 간다. FINDINGS가 아닌 판정(BLOCKED, UNKNOWN, Reviewer
   오류 종료)은 repair 없이 즉시 실패한다(`reviewer_<판정>`). Reviewer 보고의
   `self_deviations`가 비어 있지 않으면 그 검토는 무효이며 같은 호출로 1회만 다시
   검토한다(retry). 재검토에서도 다시 나오면 `reviewer_self_deviation`으로 실패하고
   repair 예산은 쓰지 않는다. `self_deviations` 필드가 없거나 `[]`도 `- {...}` 항목
   목록도 아니면 분류할 수 없으므로 같은 방식으로 무효로 본다. `unverified` 항목은
   판정에 쓰지 않고 8항 QA로 넘긴다(처리는 9항).
4. Repair 가능 판정. FINDINGS의 모든 항목 evidence가 candidate 변경 파일을
   가리키지 않으면 `reviewer_findings_not_repairable`로 실패한다. 이 경우 repair
   예산을 쓰지 않는다. 한 항목이라도 가리키면 repair 대상이다.
5. Repair 예산. §5의 `repair_budget`과 같은 의미이며 파이프라인 상한은 1이다.
   환경변수나 인자로 올릴 수 없다. 소진되면 `reviewer_findings`로 실패하고 Owner
   결정을 기다린다.
6. Repair 흐름. 같은 worktree에서 Worker가 변경 파일을 가리키는 지적만 고친다.
   변경이 없으면 `repair_no_changes`로 실패한다. 새 candidate는 이전 candidate를
   parent로 하고, 이전 Reviewer 결과는 무효다. 그 뒤 fresh Reviewer가 검토한다.
7. Resume. FAILED task에만, Owner가 명시적으로 요청할 때만 한다. 직전 시도의 허용
   경로 변경(commit된 것과 미커밋 포함)을 현재 main을 baseline으로 한 새 시도에
   복사한다. 모든 검사는 새 worktree를 만들기 전에 하고, 거절 사유는
   `resume_no_previous_attempt`, `resume_no_changes`, `resume_scope_violation`,
   `resume_conflict`다.
8. QA. 같은 candidate에서 `head_is_candidate`, `change_set_matches`,
   `diff_check`, `jarvis_bat_absent`, `json_valid`, `tests_rerun` 6개가 모두
   통과해야 한다.
9. 반영. 파이프라인은 Reviewer 호출에 8항의 6개 검사 목록을 주고, Reviewer는 각
   `unverified` 항목에 그 항목을 혼자서 확인하는 검사 이름이나 `none`을 `qa`로
   적는다. 모든 `unverified` 항목의 `qa`가 6개 검사 중 하나이면 QA 통과로 확인된
   것으로 본다. `qa`가 `none`이거나 없거나 목록 밖이면 QA가 통과해도 반영하지 않고
   `qa_unverified_owner_review`로 실패해 Owner 확인 대상으로 남긴다(candidate 보존,
   새 상태 없음). 이때 실패 기록은
   `qa:qa_unverified_owner_review candidate=<40hex> baseline=<40hex> attempt=<N>`이다(12항).
   `unverified` 필드가 없거나 `[]`도 `- {...}` 항목 목록도 아니면
   분류할 수 없는 항목이 있는 것으로 보고 같이 멈춘다. 그다음 main HEAD가 baseline과 같을 때만 ff-only로 반영한다. main이
   움직였으면 반영하지 않고 실패한다. 실행 전, accept 승인 전, 반영 직전에 main의 tracked 변경이 있으면
   멈추되, `/go`의 상태 전이와 실행 결과 기록이 쓰는 실행 대상 task 자신의 기록(`memory/tasks/<task-id>.md`)
   한 파일만 예외다(task-0157).
10. 자동 DONE. 9가 성공한 경우에만 실행 결과 기록과 함께 `DOING→DONE`을 한 번의
    원자적 쓰기로 적용하고 task 파일을 checkpoint commit한다. 이것은 파이프라인
    경로에만 적용되는 예외이며 수동 SOP 작업의 DONE 경로(§8)를 바꾸지 않는다.
11. 실패 처리. DONE 기록 전의 실패는 `DOING→FAILED`로 기록한다. DONE 기록 뒤의
    실패는 task가 DONE으로 남으므로 Owner 확인 대상이다. 9 이전의 실패는 main에
    반영되지 않는다. 9 뒤의 기록·checkpoint 단계에서 실패하면 candidate는 이미
    main에 있으므로 Owner 확인 대상이다. 실패한 시도는 보존한다.
12. Accept. `/go <id> accept`는 9항의 실패 기록이 있는 FAILED task에만, Owner가 확인 대기
    항목을 확인한 뒤 명시적으로 요청할 때만 한다. 순서는 candidate 식별 → main baseline 확인 →
    8항 QA 6개 재실행 → 승인 전이(`FAILED→TODO→DOING`, `/go`와 같은 Owner 승인 감사) → baseline
    재확인 → ff-only → `DOING→DONE` → checkpoint이며 Reviewer는 다시 호출하지 않는다. 식별은
    기록된 candidate·baseline·attempt를 git 상태와 대조한다. 기록 형식이 다르면
    `accept_record_invalid`, attempt 이름이 다른 task와 겹치면 `accept_attempt_ambiguous`, 기록보다
    높은 번호의 attempt가 있으면 `accept_newer_attempt`, attempt branch나 worktree가 없으면
    `accept_branch_missing`·`accept_worktree_missing`, worktree가 그 branch로 등록돼 있지 않으면
    `accept_worktree_mismatch`, branch tip·worktree HEAD·기록 candidate가 다르면
    `accept_candidate_mismatch`, worktree에 변경이 있으면(QA 재실행 뒤 포함) `accept_worktree_dirty`,
    baseline에서 candidate까지가 Worker candidate commit 사슬이 아니면 `accept_chain_mismatch`,
    변경이 허용 경로를 벗어나면 `accept_scope_violation`, main이 checkout돼 있지 않거나 baseline과
    다르거나 tracked 변경이 있으면 `accept_main_not_checked_out`·`accept_baseline_moved`·
    `accept_main_dirty`, QA가 실패하면 `accept_qa_failed`로 거절한다. 이 거절들은 승인 전이 전이라
    상태·실패 기록·main·attempt를 바꾸지 않고 감사도 남기지 않으므로 다시 accept할 수 있다. 승인
    전이가 적용되지 않으면 `accept_transition_failed`다. 승인 전이 뒤의 실패는 9~11항과 같이
    처리하며 다시 accept하지 않는다. main이 baseline과 다르면 rebase·merge·resume으로 우회하지 않는다.
13. Recover. `/go <id> recover`는 `/work`로 만든 DOING task에만, Owner가 명시적으로 요청할 때만
    한다(task-0167). 실행은 attempt를 만들 때부터 결과(DONE·FAILED와 실행 기록)를 쓸 때까지
    attempt worktree 옆(저장소 밖)에 실행 표지를 두고 그 뒤 지운다(repair 1, run 전체). accept는
    기록된 attempt를 찾은 뒤(QA 전)부터 결과를 쓸 때까지 같은 표지를 둔다. 표지는 run을 실행하는
    봇 프로세스와, run이 시작해 아직 실행 중인 자식 프로세스(Worker·Reviewer·테스트·QA·git, 모두
    같은 실행 함수로 시작) 각각을 PID·실행 파일 경로·프로세스 시작 시각으로 적고, 자식이 끝나면
    그 항목을 지운다(repair 2). 같은 attempt의 이전 run이 남긴 표지에 아직 실행 중이거나 식별할 수
    없는 프로세스가 있으면 새 표지에 이어 적고, run이 끝날 때도 그 프로세스를 적은 표지를 남긴다.
    같은 attempt의 이전 표지가 있지만 읽을 수 없거나 불완전하거나(식별하지 못한 프로세스를 빈 값으로
    적은 표지 포함) 다른 task를 가리키면, 새 run은 그 내용을 버리지 않고 자기가 쓰는 표지마다 담아
    run 동안과 끝난 뒤 모두 invalid로 두며, 끝나도 지우지 않는다(repair 3). 그 표지가 남아 있는
    동안 그 task의 recover는 `recover_worker_marker_invalid`로 거절된다. Owner가 확인하고 그 표지를
    직접 지워도, 그것이 마지막 attempt의 표지였다면 그 attempt에 표지가 없으므로
    `recover_worker_marker_missing`으로 거절되고 거절 사유만 바뀐다. 지운 뒤 recover가 진행될 수
    있는 것은 그 표지가 더 이전 attempt의 것이고, 더 새 attempt가 자기 표지를 남긴 채 멈췄으며 그
    표지가 가리키는 프로세스가 모두 끝난 경우뿐이다(task-0168).
    recover는 Worker 잠금 둘을 잡은 채 마지막 attempt의 표지가 가리키는 프로세스가 모두 끝났을
    때만(세 값이 모두 같은 프로세스가 없을 때) 실패 기록과 `DOING→FAILED`를 한 번의 원자적 쓰기로
    적용하고, `/go`와 같은 Owner 승인 감사와 실행 결과 감사를 남긴다. 다시 실행하지 않으며 재실행은
    `/go`나 `/go <id> resume`이다. 상태가 DOING이 아니면 `recover_requires_doing:<상태>`, `/work`로
    만든 task가 아니면 `recover_not_worker_path`, 잠금이 잡혀 있으면 `worker_busy`, 어느 attempt의
    표지든 살아 있는 프로세스를 가리키면 `recover_worker_alive`, 마지막 attempt에 표지가 없으면
    `recover_worker_marker_missing`, 어느 attempt의 표지든 읽을 수 없거나 식별 정보가 불완전하거나
    표지가 가리키는 프로세스를 식별할 수 없으면(접근 거부 등, 끝난 것으로 보지 않는다)
    `recover_worker_marker_invalid`로 거절하고 아무것도 바꾸지 않는다(fail closed). 마지막 attempt는
    worktree·브랜치·표지 파일 번호 중 가장 큰 번호이고, recover는 표지를 지우지 않는다. 표지가
    생기기 전에 시작된 시도는 표지가 없으므로 `recover_worker_marker_missing`이다. DOING 전환 뒤
    이번 실행의 표지를 쓰기 전(preflight)에 멈춘 실행은, 이전 attempt가 남긴 표지가 없으면 같은
    거절이고, 있으면 그 표지가 마지막 attempt의 표지로 판정한다(가리키는 프로세스가 모두 끝났으면
    recover가 된다). 이 구간에는 worktree와 Worker가 아직 없고, 읽기 전용 git 명령만 표지 없이
    실행된다.
