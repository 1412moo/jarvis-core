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

## 9. 현재 자동화 경계와 성숙도

이 SOP는 조직 계약과 project custom-agent 설정을 제공하지만 Hermes가 자동으로
Worker를 실행하는 runtime은 아니다. SDK/app-server, dispatcher subsystem,
background execution과 queue persistence는 별도 승인 전까지 금지다.

Manual Pilot v0.1A는 실제 Implementer candidate에서 Reviewer가 P2 finding을 찾고,
Manager가 repair 1회를 지시한 뒤 새 candidate에 Reviewer와 QA를 다시 실행해
완료했다. 이 SOP의 채택은 완료됐지만 운영 성숙도를 확정하려면 실제 기능
work package 1~2개에서 같은 흐름을 반복 성공해야 한다. 그 뒤에만 Hermes 자동
runtime 검토를 제안한다.
