# task-0167-stalled-doing-detection-and-owner-recover

- id: `task-0167-stalled-doing-detection-and-owner-recover`
- title: `Worker 파이프라인 R2: 멈춘 DOING 판정을 Worker 실행 상태 기준으로 고치고 Owner 명시 복구 /go <id> recover 추가`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-18 16:42 UTC`
- updated_at: `2026-10-18 16:58 UTC`
- summary: `Worker 경로 task가 DOING인데 실행 중인 Worker가 없으면 이전 실행 기록과 관계없이 멈춤 후보로 판정하고(V3 결함), 고아 Worker까지 식별되는 실행 표지를 두며, Owner 전용 /go <id> recover가 감사 기록과 함께 DOING을 FAILED로만 바꾼다. 실행 표지가 없거나 불완전하면 복구를 거절하고, Worker 경로 task에 대한 /retry는 거절한다. 자동 재실행·큐·Scheduler는 만들지 않고 push는 하지 않는다.`
- source_command: `Owner 승인: R2 설계 결정(task-0165 실제 Discord 검증 V3 뒤)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `4416b04acfca38ca547004dd33bb056943186c08` (main HEAD = origin/main, fetch 뒤 확인) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat`, `memory/tasks/task-0166-studyroom-glossary-r1-1.md`(V2·V3 테스트 task, 보존) |
| 환경 | Windows ACP 949, Python 3.12.10 |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (기본값) |

## 조사 결과 (read-only, 등록 전 확인)

1. V3 결함: 시작 점검(`_stalled_doing_scan`)과 `/go`의 DOING 처리(`_run_go`)는 "실행 중인 Worker 없음 그리고 `executed` 없음"을 멈춤으로 본다. `/go` 재시도(FAILED→TODO→DOING)는 이전 실행 기록을 그대로 두므로, 재시도 중 봇이 죽으면 `recorded_doing`으로 분류되어 DM·`doing_without_execution_record`가 나오지 않는다. task-0166이 이 상태다(`status: DOING`, `updated_at` 16:27, 이전 기록 `worker:worker_timeout` 15:58).
2. 파이프라인은 끝날 때 실행 기록과 `DOING→DONE/FAILED`를 `_apply_execution_result`로 한 번에 쓴다. 그래서 Worker 경로 task가 정상적으로 "DOING인데 실행 중인 Worker 없음"에 머무를 수 없다. 예외는 기록 쓰기 자체의 실패(그것도 멈춤으로 보는 것이 맞다)와 Owner가 Console Start로 `/work` task를 수동 시작한 경우다.
3. 고아 Worker: V3에서 봇(PID 21188)이 종료된 뒤 Worker claude(PID 13996)가 부모 없이 계속 실행되어 `-r2` worktree의 `glossary.json`을 고쳤고, 그동안 파일 잠금은 풀려 있었다(`lock held: False`). 잠금만으로는 "실행 중 아님"을 보장할 수 없다. Worker는 `claude_worker._run`의 `subprocess.Popen`으로 시작되고, 시간 초과 때만 `taskkill /T`로 하위 트리를 끝낸다.
4. `DOING→FAILED`는 이미 허용된 전이다(`ALLOWED_STATUS_TRANSITIONS`, `docs/task-model.md` 5-1). recover는 새 전이가 아니라 5-2의 새 발생 경로다.
5. `/retry`(`_run_retry`)는 FAILED·DOING을 받고 Worker 잠금을 보지 않는다. 제목·요약의 단어(script·run·demo·test·검증)로 실행 후보를 만들며, Worker 경로 task에서 이 경로가 열리면 FAILED→TODO→DOING 뒤 `executed: false` 기록만 쓰고 DOING에 남거나, 실행 중인 task의 기록을 덮어쓸 수 있다(코드 판독, 실행하지 않음). 단어가 없으면 `retry_execution_candidate_missing`로 아무것도 바꾸지 않는다.

## Owner 결정 (원문)

```text
설계안은 전반적으로 타당합니다. 특히 V3 결함을 실행 기록의 시각 비교가 아니라 Worker 실행 상태를 기준으로 해결하자는 제안이 좋습니다. 다만 구현 승인 전에 고아 Worker 처리와 복구 명령의 안전성을 조금 더 명확히 정하는 게 좋겠습니다.

## 제가 권하는 결정

| 항목                   | 결정                                                                                              |
| -------------------- | ----------------------------------------------------------------------------------------------- |
| 멈춘 DOING 판정          | (c) 채택. Worker 경로 task가 DOING이고 실행 중인 Worker가 없으면, 과거 실행 기록과 무관하게 멈춤 후보로 판정                     |
| 복구 명령                | `/go <id> recover` 채택. Owner 승인과 감사 기록을 남기고 `FAILED`로만 전환                                       |
| 복구 후 실행              | 자동 재실행 금지. 기존 `/go`와 `resume`을 사용                                                               |
| 고아 Worker 대책         | ① PID 파일 방식을 우선 검토. PID만으로 프로세스를 식별하면 PID 재사용이나 다른 프로세스 오인 위험이 있으므로 프로세스 경로·시작 시각 등 추가 식별 기준 필요 |
| `/retry`             | Worker 경로 task에서 잠금 없이 실행되거나 `DOING` 상태를 덮어쓰는 경로는 거절하도록 수정                                      |
| task-0166 및 worktree | 현재 상태와 변경 사항 그대로 보존. R2 검증 대상으로 재사용                                                             |
| 테스트 흔적 정리            | R2 검증이 끝난 후 별도 결정                                                                               |

## 구현 전에 추가로 명확히 할 점

1\. `recover`는 잠금이 비어 있다는 것만으로 안전하다고 판단하면 안 됩니다. 고아 Worker가 계속 실행 중일 수 있기 때문입니다. PID 파일이 없거나 식별 정보가 불완전하면 복구를 거절하는 보수적인 동작이 필요합니다.

2\. 시작 DM과 복구 명령은 별개로 검증해야 합니다. 먼저 봇 재기동 시 `task-0166`이 멈춘 작업으로 DM에 포함되는지 확인하고, 그다음 명시적 `recover`로 `FAILED` 전환과 감사 기록을 검증하는 순서가 적절합니다.

3\. `/retry` 범위는 기존 동작을 확인한 뒤 최소한으로 바꿔야 합니다. Worker 경로 task에 대한 안전한 거절은 필요하지만, 무관한 수동 task의 동작까지 변경하지 않도록 회귀 테스트를 포함해야 합니다.

## 다음 단계

이제 설계 조사 자체는 충분합니다. 별도 조사나 새 테스트 task를 추가하기보다는, 이 결정을 반영해 `task-0167`에 R2를 등록하고 기존 SOP에 따라 진행하면 됩니다.

다만 이것은 구현 방향에 대한 승인안이지, 제가 저장소에서 실제 등록이나 구현을 완료했다는 뜻은 아닙니다. 실제 구현은 위 안전 조건을 task 범위에 명시한 뒤 진행하는 것이 좋겠습니다.
```

## Manager 요약

아래 행은 Owner 결정 블록 셋("Owner 결정", "D1 결정", "D2 결정"), Start 승인, 진행 승인 원문의 조건 문장을 빠짐없이 인용한다.

| # | 승인 조건 (원문 인용) | Manager 해석과 충족 방법 |
| --- | --- | --- |
| O0 | "설계안은 전반적으로 타당합니다. 특히 V3 결함을 실행 기록의 시각 비교가 아니라 Worker 실행 상태를 기준으로 해결하자는 제안이 좋습니다. 다만 구현 승인 전에 고아 Worker 처리와 복구 명령의 안전성을 조금 더 명확히 정하는 게 좋겠습니다." | 판정을 Worker 실행 상태(잠금과 실행 표지)로 바꾸고, 고아 Worker 처리(D1)와 복구 안전성(K4·D2)을 Start 전에 확정했다 |
| O1 | 멈춘 DOING 판정: "(c) 채택. Worker 경로 task가 DOING이고 실행 중인 Worker가 없으면, 과거 실행 기록과 무관하게 멈춤 후보로 판정" | `_worker_task_state`(잠금 또는 살아 있는 표지면 `running`)로 시작 점검(`_stalled_doing_scan`)과 `/go`의 DOING 처리가 같은 기준을 쓴다. 이전 기록은 `_previous_record`로 참고 줄에만 쓴다 |
| O2 | 복구 명령: "`/go <id> recover` 채택. Owner 승인과 감사 기록을 남기고 `FAILED`로만 전환" | `_run_recover`: Owner 전용 `/go` 경로, `_apply_execution_result`로 실패 기록과 `DOING→FAILED`를 한 번에 쓰고 `_audit_owner_approval`(DOING→FAILED)과 `_audit_execution_result`(source `go`)를 남긴다 |
| O3 | 복구 후 실행: "자동 재실행 금지. 기존 `/go`와 `resume`을 사용" | recover는 실행하지 않고 답장에 `/go <id>`·`/go <id> resume` 선택지만 보인다. 이후 `/go`는 기존 FAILED 재시도 경로 그대로 |
| O4 | 고아 Worker 대책: "① PID 파일 방식을 우선 검토. PID만으로 프로세스를 식별하면 PID 재사용이나 다른 프로세스 오인 위험이 있으므로 프로세스 경로·시작 시각 등 추가 식별 기준 필요" | D1 (a) 확정. 아래 D1 행 |
| O5 | `/retry`: "Worker 경로 task에서 잠금 없이 실행되거나 `DOING` 상태를 덮어쓰는 경로는 거절하도록 수정" | `_run_retry`가 `source_command: /task` task를 상태 확인 직후, 아무것도 바꾸기 전에 `retry_worker_path_use_go`로 거절한다 |
| O6 | task-0166 및 worktree: "현재 상태와 변경 사항 그대로 보존. R2 검증 대상으로 재사용" / 테스트 흔적 정리: "R2 검증이 끝난 후 별도 결정" | task-0166 기록과 `-r1`·`-r2` worktree·브랜치를 건드리지 않았다. 검증은 임시 clone과 smoke 임시 저장소에서만 했다 |
| O7 | "1\. `recover`는 잠금이 비어 있다는 것만으로 안전하다고 판단하면 안 됩니다. 고아 Worker가 계속 실행 중일 수 있기 때문입니다. PID 파일이 없거나 식별 정보가 불완전하면 복구를 거절하는 보수적인 동작이 필요합니다." | recover는 잠금을 잡은 뒤 표지 상태가 `gone`일 때만 진행한다. `missing`·`invalid`(읽을 수 없음, 필드 누락·형식 오류, attempt 조회 실패)·`alive`는 각각 거절 |
| O8 | "2\. 시작 DM과 복구 명령은 별개로 검증해야 합니다. 먼저 봇 재기동 시 `task-0166`이 멈춘 작업으로 DM에 포함되는지 확인하고, 그다음 명시적 `recover`로 `FAILED` 전환과 감사 기록을 검증하는 순서가 적절합니다." | K9 순서. 실제 Discord 검증은 이 task의 QA 뒤 별도 승인으로 한다 |
| O9 | "3\. `/retry` 범위는 기존 동작을 확인한 뒤 최소한으로 바꿔야 합니다. Worker 경로 task에 대한 안전한 거절은 필요하지만, 무관한 수동 task의 동작까지 변경하지 않도록 회귀 테스트를 포함해야 합니다." | 거절은 `source_command: /task`에만. self-check(수동 FAILED task가 기존 경로대로 `retry_result`)와 Worker smoke(수동 DOING task가 Worker 경로 거절을 받지 않음), 기존 `/retry` self-check 유지 |
| O10 | "이제 설계 조사 자체는 충분합니다. 별도 조사나 새 테스트 task를 추가하기보다는, 이 결정을 반영해 `task-0167`에 R2를 등록하고 기존 SOP에 따라 진행하면 됩니다." / "다만 이것은 구현 방향에 대한 승인안이지, 제가 저장소에서 실제 등록이나 구현을 완료했다는 뜻은 아닙니다. 실제 구현은 위 안전 조건을 task 범위에 명시한 뒤 진행하는 것이 좋겠습니다." | 이 기록에 K1~K10으로 범위를 적어 등록했고, Start 승인 뒤에 구현했다. 새 테스트 task는 만들지 않았다 |
| D1 | "저는 D1은 (a) PID 파일 방식으로 진행하는 것을 권합니다." / "(b) 실행 잠금 래퍼도 가능하지만, 기존 Worker 실행·시간 제한 처리를 래퍼로 옮기면 변경 범위가 커집니다. 지금 R2의 목적은 멈춘 작업을 안전하게 감지하고 복구하는 것이므로, 기존 실행 구조를 최대한 유지하는 편이 좋겠습니다." / "* PID뿐 아니라 실행 파일 경로와 프로세스 시작 시각까지 대조합니다." / "* 표지가 없거나 손상됐거나 식별 정보가 불완전하면 복구를 거절합니다." / "* 이전 시도의 표지가 새 시도에 잘못 적용되지 않도록 attempt별로 구분합니다." / "* Worker가 정상 종료되거나 실패할 때 표지를 정리합니다. 강제 종료 후 남은 표지는 프로세스 식별 결과로 판단합니다." / "* 기존 실행 제한과 잠금 구조는 불필요하게 변경하지 않습니다." | 표지 `WORKTREE_ROOT/<attempt>.worker.json`에 `task_id`·`attempt`·`pid`·`exe`·`started`. `_process_identity`(Windows `QueryFullProcessImageNameW`·`GetProcessTimes`, 그 밖 `/proc`)로 PID·경로·시작 시각이 모두 같을 때만 살아 있음. 식별 정보를 읽지 못하면 빈 값을 써 `invalid`가 된다. 마지막 attempt의 표지만 `missing`/`invalid`/`gone`을 정하고, 어느 attempt든 살아 있으면 `alive`. `_run_worker`가 `finally`에서 지운다(정상·실패·시간 초과). `_run`에는 시작 직후 PID를 알리는 선택 인자만 더했고 시간 제한·`taskkill`·Worker 잠금은 그대로 |
| D1a | "그리고 승인은 두 단계로 나누겠습니다. D1 선택은 확정하되, `START TASK`와 구현 착수는 아직 승인하지 않습니다. Start Preview까지만 열린 현재 상태를 유지하면 됩니다." / "이렇게 하면 우선 실행 표지 설계를 고정하고, 실제 구현 시작은 별도로 결정할 수 있습니다." | D1 결정 뒤 Start Preview 상태를 유지했고 구현하지 않았다 |
| D2 | "저는 D2는 (a) 거절 유지를 권합니다." / "이유는 명확합니다. D1에서 실행 표지가 없거나 불완전하면 복구를 거절하기로 확정했는데, task-0166만 예외로 허용하면 그 안전 규칙에 별도 경로가 생깁니다. 특히 이번에는 봇이 죽은 뒤 Worker 프로세스가 독립적으로 실행될 수 있다는 사실도 확인했기 때문에, 표지가 없는 과거 작업을 프로세스 목록만으로 복구하는 것은 피하는 편이 낫습니다." / "* D2: (a) 거절 유지" / "* task-0166 시작 DM 검증: 진행 가능" / "* task-0166 recover 검증: `recover_worker_marker_missing` 거절이 예상되므로 실제 복구 성공 검증에는 사용하지 않음" / "* recover 성공 검증: R2 적용 이후 표지가 생성되는 새 시도나 별도의 테스트 fixture를 사용하되, 불필요한 테스트 task 증가는 최소화" | 표지 없는 시도에 예외 경로가 없다(`missing`이면 거절). recover 성공은 Worker smoke의 fixture(임시 clone 안의 `/work` task와 살아 있는·끝난 프로세스 표지)로 검증했고 새 실제 task는 만들지 않았다 |
| D2a | "현재 task-0167은 `TODO`, Console은 Start Preview 상태 그대로 두면 됩니다." / "그리고 지금은 D2만 확정한 것이며, `START TASK`와 구현 착수는 아직 승인하지 않은 상태입니다. 설계 기록을 갱신한 뒤 별도로 시작 승인을 받는 순서가 맞습니다." | D2 기록 뒤 TODO·Start Preview 상태를 유지하고 Start 승인을 따로 받았다 |
| P1 | 변형 검증 보고 뒤 진행 승인: "진행해. 승인된 범위대로 task-0167의 구현 및 검증 결과를 기록하고 candidate 커밋 → Reviewer → 필요 시 repair 1회 → QA → QA checkpoint까지 진행해." / "단, M9는 잠금 예외로 smoke가 중단됐으므로 개별 검사 결과가 남지 않았다는 사실을 그대로 기록해. 변형 검증 결과를 과장하지 말고, 필요한 경우 M9 검증의 한계를 QA 보고에 명시해." / "남은 smoke 임시 폴더 3개는 삭제하지 말고 보존해. task-0166 기록과 두 worktree, `jarvis.bat`은 건드리지 마. push, master-plan 갱신, 최종 DONE 처리는 하지 말고 QA checkpoint 후 보고하고 멈춰." | 아래 "구현"과 "Implementer 검증"에 결과를 적고 candidate → Reviewer → (repair 1회까지) → QA → QA 기록 checkpoint 순서로 진행한다. M9 행은 "smoke 중단, 개별 결과 없음"으로 적는다. smoke 임시 폴더 3개·task-0166·worktree·`jarvis.bat`은 그대로 두고, push·master-plan·DONE은 하지 않는다 |
| S0 | Start 승인: "task-0167 Start Confirm 승인합니다, 구현 시작해줘" | 2026-10-18 16:58 UTC Console Start Confirm으로 `TODO→DOING`, 그 뒤 구현. Complete·DONE checkpoint·master-plan·push·실제 Discord 검증은 하지 않았다 |

## 범위와 안전 조건

| # | 조건 |
| --- | --- |
| K1 | 멈춤 판정: Worker 경로 task(`source_command: /task`)가 DOING이고 실행 중인 Worker가 없으면(아래 K3 기준) 이전 실행 기록과 관계없이 멈춤 후보. 시작 점검과 `/go`의 DOING 처리가 같은 판정 함수를 쓴다. 이전 기록은 참고로만 표시한다 |
| K2 | 수동 task(그 밖의 `source_command`)는 지금처럼 건수만 세고 판정·복구 대상이 아니다 |
| K3 | 실행 중 판단: 프로세스 안 잠금, 파일 잠금, 그리고 Worker 실행 표지(D1) 셋 중 하나라도 실행 중을 가리키면 실행 중이다 |
| K4 | `recover`는 실행 표지가 없거나 읽을 수 없거나 식별 정보가 불완전하면 거절한다(fail closed). 표지가 가리키는 프로세스가 살아 있으면 거절한다 |
| K5 | `/go <id> recover`: Owner 전용(기존 `/go` 권한 검사). Worker 잠금 두 개를 잡은 채 `_apply_execution_result`로 실패 기록과 `DOING→FAILED`를 한 번에 쓰고 감사 기록을 남긴다. 거절 사유: `not_found`, `recover_requires_doing:<상태>`, `recover_not_worker_path`, `worker_busy`, `recover_worker_marker_missing`·`recover_worker_marker_invalid`, `recover_worker_alive`, 쓰기 실패 |
| K6 | 복구 뒤 자동 재실행 없음. 답장에 `/go <id>`·`/go <id> resume` 선택지와, resume이 마지막 attempt worktree의 변경(고아 Worker 편집 포함 가능)을 가져온다는 안내 |
| K7 | `/retry`: Worker 경로 task는 상태를 바꾸기 전에 거절하고 `/go` 사용을 안내한다. 수동 task의 기존 동작은 그대로(회귀 테스트) |
| K8 | task-0166, `-r1`·`-r2` worktree와 변경 파일을 그대로 보존한다. 새 테스트 task를 만들지 않는다 |
| K9 | 실제 Discord 검증 순서: 봇 재기동 → task-0166이 시작 DM에 실리는지 → `/go task-0166-… recover`가 `recover_worker_marker_missing`으로 거절되고 상태가 그대로인지(D2). recover 성공은 결정론적 테스트 fixture로 검증하고, 실제 Discord 성공 검증은 표지가 생기는 새 시도로 최소한만(별도 승인). 각 단계 별도 승인 |
| K10 | 자동 재실행·큐·Scheduler·Console 제어·push 없음. `jarvis.bat` 접근 금지 |

## Start 전에 정할 항목

| # | 질문 | 선택지 | Manager 권고 |
| --- | --- | --- | --- |
| D1 | Worker 실행 표지 방식 | (a) PID 파일: Worker 시작 직후 저장소 밖 `WORKTREE_ROOT/<attempt>.worker.json`에 PID·실행 파일 경로·프로세스 시작 시각(Windows `GetProcessTimes`, 그 밖 `/proc` 또는 `ps`)을 쓰고, 판정 때 같은 PID의 경로와 시작 시각이 모두 같을 때만 "살아 있음". 정상 종료 시 파일 삭제 / (b) 실행 잠금 래퍼: Worker를 작은 Python 래퍼로 시작하고, 래퍼가 attempt 전용 잠금 파일을 claude가 끝날 때까지 잡는다(시간 초과도 래퍼가 처리). 판정은 잠금 탐지로 하므로 PID 재사용 문제가 없다 | (b). 기존 OS 잠금 기능을 그대로 쓰고 PID 재사용·식별 정보 비교가 필요 없다. 단 래퍼가 claude 하위 트리를 확실히 끝내야 하므로 시간 초과 처리를 래퍼로 옮긴다. Owner가 (a)를 원하면 (a)로 하고 식별 정보 셋 중 하나라도 없으면 거절한다 |

### D1 결정 (원문)

```text
저는 D1은 (a) PID 파일 방식으로 진행하는 것을 권합니다.
(b) 실행 잠금 래퍼도 가능하지만, 기존 Worker 실행·시간 제한 처리를 래퍼로 옮기면 변경 범위가 커집니다. 지금 R2의 목적은 멈춘 작업을 안전하게 감지하고 복구하는 것이므로, 기존 실행 구조를 최대한 유지하는 편이 좋겠습니다.
다만 (a)는 다음 조건을 반드시 지켜야 합니다.

* PID뿐 아니라 실행 파일 경로와 프로세스 시작 시각까지 대조합니다.
* 표지가 없거나 손상됐거나 식별 정보가 불완전하면 복구를 거절합니다.
* 이전 시도의 표지가 새 시도에 잘못 적용되지 않도록 attempt별로 구분합니다.
* Worker가 정상 종료되거나 실패할 때 표지를 정리합니다. 강제 종료 후 남은 표지는 프로세스 식별 결과로 판단합니다.
* 기존 실행 제한과 잠금 구조는 불필요하게 변경하지 않습니다.

그리고 승인은 두 단계로 나누겠습니다. D1 선택은 확정하되, `START TASK`와 구현 착수는 아직 승인하지 않습니다. Start Preview까지만 열린 현재 상태를 유지하면 됩니다.
이렇게 하면 우선 실행 표지 설계를 고정하고, 실제 구현 시작은 별도로 결정할 수 있습니다.
```

D1은 (a) PID 파일로 확정. 표지 조건: PID·실행 파일 경로·프로세스 시작 시각을 모두 대조, attempt별 파일(`WORKTREE_ROOT/<attempt 이름>.worker.json`), Worker가 끝나면(정상·실패·시간 초과) `_run_worker` 쪽에서 정리, 강제 종료 뒤 남은 표지는 프로세스 식별 결과로 판단, `_run`의 시간 제한과 Worker 잠금 구조는 그대로. Start와 구현 착수는 아직 승인되지 않았다(Start Preview만 연 상태 유지).

D2(R2 이전 시도의 복구): task-0166의 `-r2` 시도는 R2 이전에 시작되어 표지 파일이 없다. K4대로라면 시작 DM에는 실리지만(K1은 표지가 없어도 잠금이 비고 표지가 실행 중을 가리키지 않으면 멈춤 후보) `/go task-0166-… recover`는 `recover_worker_marker_missing`으로 거절된다.

### D2 결정 (원문)

```text
저는 D2는 (a) 거절 유지를 권합니다.
이유는 명확합니다. D1에서 실행 표지가 없거나 불완전하면 복구를 거절하기로 확정했는데, task-0166만 예외로 허용하면 그 안전 규칙에 별도 경로가 생깁니다. 특히 이번에는 봇이 죽은 뒤 Worker 프로세스가 독립적으로 실행될 수 있다는 사실도 확인했기 때문에, 표지가 없는 과거 작업을 프로세스 목록만으로 복구하는 것은 피하는 편이 낫습니다.
결정은 이렇게 정리하면 됩니다.

* D2: (a) 거절 유지
* task-0166 시작 DM 검증: 진행 가능
* task-0166 recover 검증: `recover_worker_marker_missing` 거절이 예상되므로 실제 복구 성공 검증에는 사용하지 않음
* recover 성공 검증: R2 적용 이후 표지가 생성되는 새 시도나 별도의 테스트 fixture를 사용하되, 불필요한 테스트 task 증가는 최소화

현재 task-0167은 `TODO`, Console은 Start Preview 상태 그대로 두면 됩니다.
그리고 지금은 D2만 확정한 것이며, `START TASK`와 구현 착수는 아직 승인하지 않은 상태입니다. 설계 기록을 갱신한 뒤 별도로 시작 승인을 받는 순서가 맞습니다.
```

D2는 (a) 거절 유지로 확정. 표지 없는 시도에 예외 경로를 두지 않는다. 이에 따라 K9를 다음과 같이 고친다: task-0166은 시작 DM 검증에 쓰고, `recover`에는 `recover_worker_marker_missing` 거절 확인에만 쓴다. recover 성공 검증은 결정론적 테스트(self-check·Worker smoke의 fixture)로 하고, 실제 Discord에서의 성공 검증이 필요하면 R2 적용 뒤 표지가 생기는 새 시도를 쓰며 테스트 task는 최소로 늘린다(실행 전 별도 승인). Start와 구현 착수는 여전히 승인되지 않았다.

### Start 승인 (원문)

```text
task-0167 Start Confirm 승인합니다, 구현 시작해줘
```

## 구현 계획

| # | 내용 |
| --- | --- |
| I1 | `claude_worker`: D1 방식의 Worker 실행 표지와 판정 함수(`worker_marker_state(task_id)` → `alive`/`gone`/`missing`/`invalid`). 기존 Worker·repair 호출 경로에만 적용, Reviewer 호출은 그대로 |
| I2 | `bot_minimal`: 멈춤 판정 함수 하나(`_stalled_worker_task`)를 시작 점검과 `_run_go`가 함께 쓴다(K1·K2·K3). 시작 DM과 `/go` 답장에 이전 기록 참고 줄 |
| I3 | `/go <id> recover`(K5·K6), 도움말, 답장 문구 |
| I4 | `/retry` Worker 경로 거절(K7) |
| I5 | `docs/task-model.md` 5-2에 recover 경로 한 줄, SOP §10.1 진입 행과 §10.2 한 항목(`recover_*` 사유), validator 대조가 통과하는지 확인 |
| I6 | 테스트: self-check와 Worker smoke에 V3 재현(재시도 기록이 남은 DOING이 멈춤으로 잡힘), 실행 표지(살아 있음·끝남·없음·손상), recover 거절 각각과 성공(원자적 쓰기·감사·잠금 해제), recover 뒤 `/go`·`resume`, `/retry` Worker 경로 거절과 수동 task 회귀, 기존 task-0164·0165 검사 유지, 변형 검증 |

## 변경 예정 파일

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/worker/claude_worker.py`, `adapters/discord/bot_minimal.py`, `orchestrator/worker/run_smoke_tests.py`, `docs/task-model.md`(5-2 한 줄), `docs/jarvis-multi-agent-sop-v0.1.md`(§10.1·§10.2), 이 기록 |
| 조건부 | `scripts/validate_multi_agent_sop.py`(§10.2 사유 대조가 새 사유를 받지 못할 때만, 사유 패턴 추가) |
| deny | `jarvis.bat`, `.env`, `apps/`, `docs/master-plan.md`(Complete 뒤 별도 승인), task-0166 기록과 그 worktree, 다른 task 기록, 그 밖의 모든 파일 |

검증기 대조: `scripts/validate_multi_agent_sop.py`의 실패 사유 대조(`pipeline_reason_parity`)는 `claude_worker.py`의 문자열만 읽는다. `recover_*` 사유는 `bot_minimal.py`에 있어 대조 대상이 아니므로 검증기는 바꾸지 않았다(조건부 파일 미변경). 따라서 `recover_*`와 SOP §10.2 13항의 일치는 검증기가 아니라 Worker smoke와 self-check가 확인한다.

## 구현 착수

2026-10-18 16:58 UTC에 Console Project Control 화면에서 Start(Preview → Confirm Start)로 `TODO→DOING`을 적용했다(파일의 status·updated_at만 바뀜).

## 구현

| 파일 | 변경 |
| --- | --- |
| `orchestrator/worker/claude_worker.py` | 실행 표지: `WORKER_MARKER_SUFFIX`, `worker_marker_path`, `_process_identity`(Windows `OpenProcess`·`GetExitCodeProcess`·`QueryFullProcessImageNameW`·`GetProcessTimes`, 그 밖 `/proc`), `_write_worker_marker`(임시 파일 뒤 `os.replace`), `_read_worker_marker`(키 집합과 형식, 파일 이름과 `attempt` 일치), `_marker_alive`(PID·경로·시작 시각 모두 일치), `worker_marker_state`(어느 attempt든 살아 있으면 `alive`, 아니면 마지막 attempt 표지로 `missing`/`invalid`/`gone`, attempt 조회 실패는 `invalid`). `_run`에 선택 인자 `started`(시작 직후 PID 전달, 실패 무시). `_run_worker`에 선택 인자 `task_id`(표지 쓰기, `finally`에서 삭제). Worker·repair 호출만 `task_id`를 넘긴다. 시간 제한·`taskkill`·Worker 잠금은 그대로 |
| `adapters/discord/bot_minimal.py` | `_worker_task_state`, `_previous_record`, `_stalled_doing_scan`(Worker 경로 DOING은 실행 중이 아니면 `stalled`, 표지가 살아 있으면 `orphaned`, 그 밖은 건수), `_format_startup_report`(두 목록, 이전 기록 참고 줄, recover 안내), `_run_go`의 Worker 경로 DOING 처리(`worker_busy`·`doing_worker_process_alive`·`stalled_doing`, 수동 task는 기존 그대로), `_run_recover`와 `RECOVER_SUMMARY`, `/retry` Worker 경로 거절, 도움말과 답장 문구, self-check 2건 추가와 task-0165 시작 점검 self-check 기대값 갱신(기록 있는 Worker 경로 DOING이 이제 `stalled`) |
| `orchestrator/worker/run_smoke_tests.py` | 가짜 Worker가 실행 중 표지 존재를 기록(`FAKE_MARKER_LOG`). `marker_flow`(정상·시간 초과·실패 run의 표지 생성과 삭제, 표지 상태 검사 13건), `recover_flow`(recover 거절: 표지 없음·DOING 아님·수동 task·살아 있는 Worker·불완전한 표지·잠금 보유·두 번째 recover, 그리고 성공, recover 뒤 `/go`로 DONE, V3 재현, 시작 DM 참고 줄, `/retry` Worker 경로 거절과 수동 task 비거절). 기존 검사 2건의 기대값을 실제 동작에 맞춤: 멈춘 `/work` task의 `/go` 사유(`doing_without_execution_record`→`stalled_doing`), `/go` 사용법 문구(`[resume|accept|recover]`). 잠금 보유 단계의 `acquire`에 5초 제한(아래 M3 참고) |
| `docs/jarvis-multi-agent-sop-v0.1.md` | §10.1 진입 명령 행(`recover`, 판정 기준, `/retry` 안내, 시작 점검 문구), §10.2에 13항 Recover |
| `docs/task-model.md` | 5-2에 recover 경로 한 줄 추가, `/retry` 행에 "`/work`로 만든 task 제외" 표기(두 곳) |

## Implementer 검증 (작업 트리 기준, candidate 전)

`.env` 없는 임시 clone(`4416b04`에서 `main`을 체크아웃하고 변경 파일 복사)에서 실행했다. Owner ID는 가짜 값만 썼다.

| # | 결과 |
| --- | --- |
| 정상 | Worker smoke 439/0(기존 402 + 새 37), self-check 104/0(102 + 새 2, 설정 없음·`PYTHONUTF8=1`), SOP validator PASS(음성 검사 133), discord-intake 141/0(이 기록 1건 증가), Console smoke PASS |
| 검증 환경 | 처음에는 detached worktree를 썼으나, V2·V3 테스트 브랜치 `jarvis/task-0166-…` 두 개가 `main`과 같은 `4416b04`를 가리켜 Worker smoke 자신의 clone이 `main`이 아닌 브랜치를 골랐고 모든 run이 `preflight:main_not_checked_out`으로 실패했다. 코드 결함이 아니어서 `main`을 체크아웃한 임시 clone으로 바꿔 다시 실행했다 |
| 변형 | M1 시작 점검이 이전 기록 있는 task를 건너뜀 → Worker smoke 2·self-check 1. M2 `/go`가 기록으로 판정 → Worker smoke 1. M3 recover가 표지 없음·손상 허용 → Worker smoke 14. M4 이전 attempt의 살아 있는 Worker 무시 → Worker smoke 14. M5 PID만으로 식별 → Worker smoke 2. M6 표지를 지우지 않음 → Worker smoke 3. M7 `/retry` 거절 제거 → Worker smoke 1·self-check 1. M8 가장 오래된 attempt 표지로 판정 → Worker smoke 1. M9 recover가 잠금 없이 진행 → Worker smoke가 잡지 않은 잠금을 풀다 예외로 중단(종료 코드 1). M9는 실패로 드러났지만 개별 검사 결과가 남지 않았고, 어느 검사가 이 변형을 잡는지는 확인하지 못했다. self-check는 M1·M7만 잡는다 |
| M3 처음 실행 | 처음 M3 실행에서 Worker smoke가 잠금을 무한정 기다려 검증 스크립트의 30분 제한에 걸렸다(앞 단계가 잠금을 잡은 채 남은 상태에서 `_WORKER_LOCK.acquire()`). 그 대기에 5초 제한을 둔 뒤 M3~M9를 다시 실행했다 |
| 남은 흔적 | smoke 임시 폴더 41→44. 처음 M3 실행 중단 1개, M3·M4·M9가 Worker 잠금 파일을 연 채 끝나 지우지 못한 2개(각 폴더에 `worktrees/.jarvis-worker.lock`). 정상 코드 run은 폴더를 남기지 않았다. Owner 지시로 삭제하지 않고 보존 |

검증에서 실제 봇·Discord·claude를 실행하지 않았다. task-0166 기록과 `-r1`·`-r2` worktree는 건드리지 않았다.

## Owner 진행 승인 (변형 검증 보고 뒤, 원문)

```text
진행해. 승인된 범위대로 task-0167의 구현 및 검증 결과를 기록하고 candidate 커밋 → Reviewer → 필요 시 repair 1회 → QA → QA checkpoint까지 진행해.

단, M9는 잠금 예외로 smoke가 중단됐으므로 개별 검사 결과가 남지 않았다는 사실을 그대로 기록해. 변형 검증 결과를 과장하지 말고, 필요한 경우 M9 검증의 한계를 QA 보고에 명시해.

남은 smoke 임시 폴더 3개는 삭제하지 말고 보존해. task-0166 기록과 두 worktree, `jarvis.bat`은 건드리지 마. push, master-plan 갱신, 최종 DONE 처리는 하지 말고 QA checkpoint 후 보고하고 멈춰.
```