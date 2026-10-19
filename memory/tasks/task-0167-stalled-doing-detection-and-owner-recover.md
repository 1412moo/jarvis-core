# task-0167-stalled-doing-detection-and-owner-recover

- id: `task-0167-stalled-doing-detection-and-owner-recover`
- title: `Worker 파이프라인 R2: 멈춘 DOING 판정을 Worker 실행 상태 기준으로 고치고 Owner 명시 복구 /go <id> recover 추가`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-18 16:42 UTC`
- updated_at: `2026-10-19 05:47 UTC`
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

아래 행은 Owner 결정 블록 셋("Owner 결정", "D1 결정", "D2 결정"), Start 승인, 진행 승인, repair 결정, 예산 증액 결정 두 건 원문의 조건 문장을 빠짐없이 인용한다.

| # | 승인 조건 (원문 인용) | Manager 해석과 충족 방법 |
| --- | --- | --- |
| O0 | "설계안은 전반적으로 타당합니다. 특히 V3 결함을 실행 기록의 시각 비교가 아니라 Worker 실행 상태를 기준으로 해결하자는 제안이 좋습니다. 다만 구현 승인 전에 고아 Worker 처리와 복구 명령의 안전성을 조금 더 명확히 정하는 게 좋겠습니다." | 판정을 Worker 실행 상태(잠금과 실행 표지)로 바꾸고, 고아 Worker 처리(D1)와 복구 안전성(K4·D2)을 Start 전에 확정했다 |
| O1 | 멈춘 DOING 판정: "(c) 채택. Worker 경로 task가 DOING이고 실행 중인 Worker가 없으면, 과거 실행 기록과 무관하게 멈춤 후보로 판정" | `_worker_task_state`(잠금 또는 살아 있는 표지면 `running`)로 시작 점검(`_stalled_doing_scan`)과 `/go`의 DOING 처리가 같은 기준을 쓴다. 이전 기록은 `_previous_record`로 참고 줄에만 쓴다 |
| O2 | 복구 명령: "`/go <id> recover` 채택. Owner 승인과 감사 기록을 남기고 `FAILED`로만 전환" | `_run_recover`: Owner 전용 `/go` 경로, `_apply_execution_result`로 실패 기록과 `DOING→FAILED`를 한 번에 쓰고 `_audit_owner_approval`(DOING→FAILED)과 `_audit_execution_result`(source `go`)를 남긴다 |
| O3 | 복구 후 실행: "자동 재실행 금지. 기존 `/go`와 `resume`을 사용" | recover는 실행하지 않고 답장에 `/go <id>`·`/go <id> resume` 선택지만 보인다. 이후 `/go`는 기존 FAILED 재시도 경로 그대로 |
| O4 | 고아 Worker 대책: "① PID 파일 방식을 우선 검토. PID만으로 프로세스를 식별하면 PID 재사용이나 다른 프로세스 오인 위험이 있으므로 프로세스 경로·시작 시각 등 추가 식별 기준 필요" | D1 (a) 확정. 아래 D1 행 |
| O5 | `/retry`: "Worker 경로 task에서 잠금 없이 실행되거나 `DOING` 상태를 덮어쓰는 경로는 거절하도록 수정" | `_run_retry`가 `source_command: /task` task를 상태 확인 직후, 아무것도 바꾸기 전에 `retry_worker_path_use_go`로 거절한다 |
| O6 | task-0166 및 worktree: "현재 상태와 변경 사항 그대로 보존. R2 검증 대상으로 재사용" / 테스트 흔적 정리: "R2 검증이 끝난 후 별도 결정" | task-0166 기록과 `-r1`·`-r2` worktree·브랜치를 건드리지 않았다. 검증은 임시 clone과 smoke 임시 저장소에서만 했다 |
| O7 | "1\. `recover`는 잠금이 비어 있다는 것만으로 안전하다고 판단하면 안 됩니다. 고아 Worker가 계속 실행 중일 수 있기 때문입니다. PID 파일이 없거나 식별 정보가 불완전하면 복구를 거절하는 보수적인 동작이 필요합니다." | recover는 잠금을 잡은 뒤 표지 상태가 `gone`일 때만 진행한다. `missing`·`invalid`(읽을 수 없음, 필드 누락·형식 오류, attempt 조회 실패, repair 1부터 표지가 가리키는 프로세스를 식별할 수 없음)·`alive`는 각각 거절 |
| O8 | "2\. 시작 DM과 복구 명령은 별개로 검증해야 합니다. 먼저 봇 재기동 시 `task-0166`이 멈춘 작업으로 DM에 포함되는지 확인하고, 그다음 명시적 `recover`로 `FAILED` 전환과 감사 기록을 검증하는 순서가 적절합니다." | K9 순서. 실제 Discord 검증은 이 task의 QA 뒤 별도 승인으로 한다 |
| O9 | "3\. `/retry` 범위는 기존 동작을 확인한 뒤 최소한으로 바꿔야 합니다. Worker 경로 task에 대한 안전한 거절은 필요하지만, 무관한 수동 task의 동작까지 변경하지 않도록 회귀 테스트를 포함해야 합니다." | 거절은 `source_command: /task`에만. self-check(수동 FAILED task가 기존 경로대로 `retry_result`)와 Worker smoke(수동 DOING task가 Worker 경로 거절을 받지 않음), 기존 `/retry` self-check 유지 |
| O10 | "이제 설계 조사 자체는 충분합니다. 별도 조사나 새 테스트 task를 추가하기보다는, 이 결정을 반영해 `task-0167`에 R2를 등록하고 기존 SOP에 따라 진행하면 됩니다." / "다만 이것은 구현 방향에 대한 승인안이지, 제가 저장소에서 실제 등록이나 구현을 완료했다는 뜻은 아닙니다. 실제 구현은 위 안전 조건을 task 범위에 명시한 뒤 진행하는 것이 좋겠습니다." | 이 기록에 K1~K10으로 범위를 적어 등록했고, Start 승인 뒤에 구현했다. 새 테스트 task는 만들지 않았다 |
| D1 | "저는 D1은 (a) PID 파일 방식으로 진행하는 것을 권합니다." / "(b) 실행 잠금 래퍼도 가능하지만, 기존 Worker 실행·시간 제한 처리를 래퍼로 옮기면 변경 범위가 커집니다. 지금 R2의 목적은 멈춘 작업을 안전하게 감지하고 복구하는 것이므로, 기존 실행 구조를 최대한 유지하는 편이 좋겠습니다." / "* PID뿐 아니라 실행 파일 경로와 프로세스 시작 시각까지 대조합니다." / "* 표지가 없거나 손상됐거나 식별 정보가 불완전하면 복구를 거절합니다." / "* 이전 시도의 표지가 새 시도에 잘못 적용되지 않도록 attempt별로 구분합니다." / "* Worker가 정상 종료되거나 실패할 때 표지를 정리합니다. 강제 종료 후 남은 표지는 프로세스 식별 결과로 판단합니다." / "* 기존 실행 제한과 잠금 구조는 불필요하게 변경하지 않습니다." | 표지 `WORKTREE_ROOT/<attempt>.worker.json`에 `task_id`·`attempt`·`pid`·`exe`·`started`. `_process_identity`(Windows `QueryFullProcessImageNameW`·`GetProcessTimes`, 그 밖 `/proc`)로 PID·경로·시작 시각이 모두 같을 때만 살아 있음. 식별 정보를 읽지 못하면 빈 값을 써 `invalid`가 된다. 마지막 attempt의 표지만 `missing`/`invalid`/`gone`을 정하고, 어느 attempt든 살아 있으면 `alive`. `_run_worker`가 `finally`에서 지운다(정상·실패·시간 초과; candidate 1 기준이며 repair 1부터 표지 범위·정리 시점은 R2 행, 식별 불가 처리는 R1 행). `_run`에는 시작 직후 PID를 알리는 선택 인자만 더했고(repair 2에서 되돌림, 이제 `_run`이 활성 표지에 자식을 직접 적는다, Q1 행) 시간 제한·`taskkill`·Worker 잠금은 그대로 |
| D1a | "그리고 승인은 두 단계로 나누겠습니다. D1 선택은 확정하되, `START TASK`와 구현 착수는 아직 승인하지 않습니다. Start Preview까지만 열린 현재 상태를 유지하면 됩니다." / "이렇게 하면 우선 실행 표지 설계를 고정하고, 실제 구현 시작은 별도로 결정할 수 있습니다." | D1 결정 뒤 Start Preview 상태를 유지했고 구현하지 않았다 |
| D2 | "저는 D2는 (a) 거절 유지를 권합니다." / "이유는 명확합니다. D1에서 실행 표지가 없거나 불완전하면 복구를 거절하기로 확정했는데, task-0166만 예외로 허용하면 그 안전 규칙에 별도 경로가 생깁니다. 특히 이번에는 봇이 죽은 뒤 Worker 프로세스가 독립적으로 실행될 수 있다는 사실도 확인했기 때문에, 표지가 없는 과거 작업을 프로세스 목록만으로 복구하는 것은 피하는 편이 낫습니다." / "* D2: (a) 거절 유지" / "* task-0166 시작 DM 검증: 진행 가능" / "* task-0166 recover 검증: `recover_worker_marker_missing` 거절이 예상되므로 실제 복구 성공 검증에는 사용하지 않음" / "* recover 성공 검증: R2 적용 이후 표지가 생성되는 새 시도나 별도의 테스트 fixture를 사용하되, 불필요한 테스트 task 증가는 최소화" | 표지 없는 시도에 예외 경로가 없다(`missing`이면 거절). recover 성공은 Worker smoke의 fixture(임시 clone 안의 `/work` task와 살아 있는·끝난 프로세스 표지)로 검증했고 새 실제 task는 만들지 않았다 |
| D2a | "현재 task-0167은 `TODO`, Console은 Start Preview 상태 그대로 두면 됩니다." / "그리고 지금은 D2만 확정한 것이며, `START TASK`와 구현 착수는 아직 승인하지 않은 상태입니다. 설계 기록을 갱신한 뒤 별도로 시작 승인을 받는 순서가 맞습니다." | D2 기록 뒤 TODO·Start Preview 상태를 유지하고 Start 승인을 따로 받았다 |
| P1 | 변형 검증 보고 뒤 진행 승인: "진행해. 승인된 범위대로 task-0167의 구현 및 검증 결과를 기록하고 candidate 커밋 → Reviewer → 필요 시 repair 1회 → QA → QA checkpoint까지 진행해." / "단, M9는 잠금 예외로 smoke가 중단됐으므로 개별 검사 결과가 남지 않았다는 사실을 그대로 기록해. 변형 검증 결과를 과장하지 말고, 필요한 경우 M9 검증의 한계를 QA 보고에 명시해." / "남은 smoke 임시 폴더 3개는 삭제하지 말고 보존해. task-0166 기록과 두 worktree, `jarvis.bat`은 건드리지 마. push, master-plan 갱신, 최종 DONE 처리는 하지 말고 QA checkpoint 후 보고하고 멈춰." | 아래 "구현"과 "Implementer 검증"에 결과를 적고 candidate → Reviewer → (repair 1회까지) → QA → QA 기록 checkpoint 순서로 진행한다. M9 행은 "smoke 중단, 개별 결과 없음"으로 적는다. smoke 임시 폴더 3개·task-0166·worktree·`jarvis.bat`은 그대로 두고, push·master-plan·DONE은 하지 않는다 |
| S0 | Start 승인: "task-0167 Start Confirm 승인합니다, 구현 시작해줘" | 2026-10-18 16:58 UTC Console Start Confirm으로 `TODO→DOING`, 그 뒤 구현. Complete·DONE checkpoint·master-plan·push·실제 Discord 검증은 하지 않았다 |
| R0 | Repair 진행 지시: "jarvis-core의 task-0167 작업을 이어서 진행한다." / 현재 상태: "task-0167은 DOING" / "candidate 5cff917은 로컬 커밋 상태이며 push하지 않음" / "Reviewer retry 예산 1/1 소진, repair 예산 0/1 사용" / "먼저 실제 저장소 상태와 기존 작업 기록을 확인해 현재 위치를 파악한 뒤, 위 승인 범위 안에서만 이어서 진행한다. 이미 완료된 검사를 불필요하게 반복하지 않는다." | 상태 서술이 실제와 같음을 확인했다: task-0167 `DOING`, 작업 전 `main`=`5cff917`(origin/main보다 1커밋 앞섬, push 안 됨), `retry_count=1`·`repair_count=0`, tracked 변경 없음, untracked `jarvis.bat`·task-0166 기록만 있음을 확인했다. 앞 세션의 Reviewer 두 보고를 이 기록의 "Reviewer 1·retry" 절에 옮겼다. 이미 끝난 검사는 다시 돌리지 않고, repair가 바꾼 동작의 검사와 바뀐 파일에 걸린 검사만 다시 실행했다 |
| R1 | Repair 결정: "F1: 프로세스 종료와 식별 정보 읽기 실패를 구분하도록 fail-closed 수정 필요" | `_probe_process`가 `alive`·`gone`·`unknown`을 나눈다. Windows는 `OpenProcess` 오류 87(그런 PID 없음)과 `STILL_ACTIVE`가 아닌 종료 코드만 `gone`, 그 밖의 실패(접근 거부 등)는 `unknown`. `/proc`은 `/proc` 자체가 없거나 읽기 실패면 `unknown`, `/proc/<pid>`가 없거나 Z·X 상태면 `gone`. 어느 attempt의 표지든 `unknown`이 있으면 `invalid`로 recover 거절 |
| R2 | "F2: PID 표지를 Worker 단계뿐 아니라 attempt의 run 전체로 확장하기로 결정" / "accept 경로도 동일한 원칙 적용" | 표지는 attempt 생성 직전(worktree 경로를 정한 뒤)부터 결과 기록(`record_result`) 뒤까지 있고, 봇(run) 프로세스의 PID·경로·시작 시각과 Worker가 도는 동안 Worker의 세 값(`worker`)을 담는다. Reviewer·QA·통합·resume 단계에서 봇이 죽어도 표지가 남아 recover가 된다(repair 1 기준. 그 단계의 자식 프로세스는 repair 2부터 표지에 적힌다, Q1 행). accept는 승인 전이 직전부터 결과 기록 뒤까지 같은 표지를 둔다. D1 조건(세 값 대조, attempt별 파일, fail closed, 끝나면 정리, 실행 제한·잠금 구조 유지)은 그대로 |
| R3 | "F1과 F2를 남은 repair 1회 안에서 구현·테스트·문서화한 뒤 새 candidate 생성" / "Reviewer가 다시 무효 판정을 받으면 SOP에 따라 중단하고 보고" | repair 1회(`repair_count=1`)로 코드·테스트·SOP·task-model·이 기록을 고친 새 candidate를 만들고 새 Reviewer → QA. retry 예산은 소진(1/1)이므로 새 Reviewer가 무효면 멈추고 보고한다 |
| R4 | "push, master-plan 갱신, 최종 DONE 처리는 별도 승인 전까지 금지" / "임시 폴더 3개, task-0166 기록 및 두 worktree, jarvis.bat은 보존" | push·master-plan·DONE 없음. smoke 임시 폴더(기존 보존분 포함)·task-0166 기록·`-r1`·`-r2` worktree·`jarvis.bat`을 건드리지 않는다 |
| Q0 | 예산 증액: "task-0167 repair 예산을 1에서 2로 증액한다. 이 증액은 task-0167에만 적용한다." / "bf87a66 위에서 repair 2로 다음을 수정한다." | `repair_budget=2`, 이 repair로 `repair_count=2`. `bf87a66` 위에 새 commit으로 만들고 `bf87a66`은 그대로 둔다 |
| Q1 | "A: Reviewer, 테스트, QA 및 관련 git 자식 프로세스의 생존 여부도 recover 판단에 반영한다. 식별 정보가 불완전한 경우 fail-closed 원칙을 유지한다." | `_run`이 시작한 모든 자식(Worker·Reviewer·테스트·QA·git)을 실행 중 표지 `children`에 적고 끝나면 뺀다. recover는 run과 모든 자식이 끝났을 때만 진행. 자식 식별 정보를 읽지 못하면 빈 값을 적어 `invalid`(거절). 같은 attempt의 이전 run 프로세스가 남아 있으면 이어 적는다. accept는 표지를 기록된 attempt를 찾은 직후(main 확인·QA 전)부터 두어 QA 프로세스도 적힌다(R2 행의 "승인 전이 직전부터"는 repair 1 기준). repair 1의 `worker` 키는 `children`으로 바뀌었다 |
| Q2 | "B: SOP §10.2 item 13과 task 기록의 preflight 관련 설명을 실제 코드 동작과 일치시킨다." | SOP 13항과 Repair 1 절의 서술을 고쳤다: 이전 attempt 표지가 없으면 `recover_worker_marker_missing`, 있으면 그 표지로 판정 |
| Q3 | "task 기록의 updated_at도 실제 수정 시점에 맞게 갱신한다." | `updated_at`을 이 repair 기록 시각으로 갱신(status는 `DOING` 그대로) |
| Q4 | "새 candidate 생성 후 Reviewer와 QA를 다시 진행한다." / "새 candidate에 한해 Reviewer 무효(self_deviations 등 자체 규칙 위반) 시 재검토 1회를 허용한다(retry_budget 1→2). 유효한 FINDINGS는 무효 처리하지 않고 그대로 보고한다." | 새 candidate에 새 Reviewer → QA. 무효 검토일 때만 같은 candidate로 재검토 1회(`retry_budget=2`). 유효한 FINDINGS는 그대로 보고하고 멈춘다(남은 repair 없음) |
| Q5 | "push, master-plan 갱신, 최종 DONE 처리는 별도 승인 전까지 하지 않는다." / "기존 candidate bf87a66과 모든 보존 대상 임시 폴더 및 worktree는 그대로 유지한다." | push·master-plan·DONE 없음. `bf87a66`은 새 candidate의 부모로 남고 고치지 않는다. smoke 임시 폴더·task-0166 기록·`-r1`·`-r2` worktree·`jarvis.bat`을 건드리지 않는다 |
| T0 | 예산 증액: "task-0167 repair 예산을 2에서 3으로 증액한다. 이 증액은 task-0167에만 적용한다." / "ad79cee 위에서 repair 3으로 다음을 수정한다." | `repair_budget=3`, 이 repair로 `repair_count=3`. `ad79cee` 위에 새 commit으로 만들고 `ad79cee`·`bf87a66`은 그대로 둔다 |
| T1 | "1. 옵션 (b)를 적용한다. 같은 attempt의 기존 표지가 존재하지만 읽을 수 없거나, 불완전하거나, 다른 task를 가리키는 경우 새 실행이 이를 덮어써서 안전성 정보를 잃지 않도록 한다. 해당 상태는 invalid로 유지하고, 실행 종료 후에도 자동 삭제하지 않는다. recover는 기존 fail-closed 원칙에 따라 거절되어야 한다." | 그런 표지의 텍스트를 새 run이 쓰는 모든 표지에 `earlier_unreadable`로 담아 run 동안·종료 뒤 모두 invalid, 종료 때 삭제하지 않음. recover는 `recover_worker_marker_invalid`로 거절 |
| T2 | "2. 빈 child identity 및 다른 task의 표지를 이용한 회귀 테스트를 추가한다. 새 실행 중과 종료 후에도 invalid 상태가 유지되고 recover가 거절되는지 확인한다. 기존 정상 표지 carry-over 테스트도 유지한다." | `marker_flow`(빈 child·다른 task·읽을 수 없는 텍스트, run 중·자식 실행 뒤·종료 뒤), `recover_flow`(두 경우 recover 거절), `accept_flow`(실제 accept), 기존 이어 적기 검사 유지 |
| T3 | "3. 이 동작을 SOP §10.2 item 13과 task-0167 기록에 정확하게 반영한다. Reviewer의 major finding과 이 Owner 결정을 기록하고 updated_at도 갱신한다." | SOP 13항 추가 문장, 이 기록의 Reviewer·Owner 원문·repair 3 절, Repair 2 한계 서술 정정, `updated_at` 갱신 |
| T4 | "4. 정상 검사와 변형 검증을 실행하고 새 candidate를 만든 뒤 Reviewer와 QA를 진행한다." | Worker smoke·self-check·SOP validator·discord-intake와 변형 검증, 새 candidate → Reviewer → QA |
| T5 | "5. 새 candidate에 대한 Reviewer가 자체 규칙 위반으로 무효가 되면 기존 승인 범위에 따라 재검토 1회를 허용한다. 유효한 FINDINGS 또는 major finding은 그대로 보고하고 임의로 수용 처리하지 않는다." | 무효 검토일 때만 같은 candidate 재검토 1회(`retry_budget=2`, `retry_count=1`). 유효한 FINDINGS는 수용하지 않고 보고 후 멈춘다 |
| T6 | "6. push, master-plan 갱신, 최종 DONE 처리는 별도 승인 전까지 하지 않는다." / "7. 기존 candidate ad79cee와 bf87a66, 47개 smoke 임시 폴더, task-0166 기록 및 두 worktree, jarvis.bat은 보존한다." / "승인 범위는 위 repair 3, 새 candidate의 Reviewer 및 QA까지다. 추가 repair가 필요하면 다시 멈추고 Owner에게 보고한다." | push·master-plan·DONE 없음. 보존 대상 모두 건드리지 않음. 범위는 repair 3·Reviewer·QA까지이고 추가 repair가 필요하면 멈추고 보고 |

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

## Candidate 1

`5cff917a32a13668c52989d2936833be8a46f5b4` (baseline `4416b04`의 자식, 로컬 커밋, push 안 함).

## Reviewer 1·retry (`5cff917`, 둘 다 무효)

| 검토 | verdict | findings | self_deviations | 판정 |
| --- | --- | --- | --- | --- |
| Reviewer 1 (2026-10-18 19:02 UTC 반환) | FINDINGS | minor 1건: 표지가 Worker·repair 프로세스가 도는 동안만 있어(`_run_worker`의 `finally`에서 삭제, resume은 `_run_worker`를 부르지 않음) Worker 시작 전·Reviewer·QA·통합·repair 없는 resume 중에 봇이 죽으면 마지막 attempt에 표지가 없고 recover가 항상 `recover_worker_marker_missing`. 시작 DM과 `stalled_doing` 답장은 recover를 안내하고 SOP 13항은 이 한계를 "표지 전 시도"로만 적음 | `git grep`에 정규식 OR(`\|`) 1건 | 무효(자기 명령 규칙 위반). `retry_count=1`로 같은 candidate 재검토 |
| Reviewer retry (2026-10-18 19:07 UTC 반환) | FINDINGS | minor 2건. F1: `_process_identity`가 `OpenProcess` 실패(접근 거부 포함)·`GetExitCodeProcess`·`QueryFullProcessImageNameW`·`GetProcessTimes` 실패·`/proc` 읽기 실패를 모두 `None`으로 돌려, 식별 정보를 못 읽은 살아 있는 Worker가 `gone`이 되고 recover가 진행됨(O7·D1 fail closed와 반대). F2: Reviewer 1과 같은 지적(Worker 단계 뒤 봇이 죽으면 recover 불가, `/retry`도 거절이라 Discord로 복구할 수단 없음) | `git grep -F` 1건, `git grep -i` 1건 | 무효. retry 예산 소진(1/1)으로 SOP대로 멈추고 Owner에게 보고 |

Manager가 코드를 직접 대조해 두 지적 모두 사실임을 확인했다. F1은 안전 결함, F2는 범위 결정(D1 확장 여부)이 필요해 Owner에게 (a) 표지를 run 전체로 확장, (b) 한계만 문서화를 물었다.

## Owner repair 결정 (원문)

```text
jarvis-core의 task-0167 작업을 이어서 진행한다.
현재 상태:

* task-0167은 DOING
* candidate 5cff917은 로컬 커밋 상태이며 push하지 않음
* Reviewer retry 예산 1/1 소진, repair 예산 0/1 사용
* F1: 프로세스 종료와 식별 정보 읽기 실패를 구분하도록 fail-closed 수정 필요
* F2: PID 표지를 Worker 단계뿐 아니라 attempt의 run 전체로 확장하기로 결정
* accept 경로도 동일한 원칙 적용
* F1과 F2를 남은 repair 1회 안에서 구현·테스트·문서화한 뒤 새 candidate 생성
* Reviewer가 다시 무효 판정을 받으면 SOP에 따라 중단하고 보고
* push, master-plan 갱신, 최종 DONE 처리는 별도 승인 전까지 금지
* 임시 폴더 3개, task-0166 기록 및 두 worktree, jarvis.bat은 보존

먼저 실제 저장소 상태와 기존 작업 기록을 확인해 현재 위치를 파악한 뒤, 위 승인 범위 안에서만 이어서 진행한다. 이미 완료된 검사를 불필요하게 반복하지 않는다.
```

F2는 (a) run 전체 확장으로 확정되었고 D1의 표지 범위가 "Worker 프로세스"에서 "attempt의 run 전체"로 넓어진다(D1의 나머지 조건은 유지). 위 D1 행의 "`_run_worker`가 `finally`에서 지운다"는 candidate 1 기준 기록이며, repair 1부터는 아래 표가 현재 동작이다. budget: `retry_count=1`(소진), `repair_count=1`(이 repair).

## Repair 1 (F1·F2)

| 파일 | 변경 |
| --- | --- |
| `orchestrator/worker/claude_worker.py` | F1: `_probe_process(pid)` → `alive`(경로·시작 시각)·`gone`·`unknown`. Windows `OpenProcess` 실패는 오류 87만 `gone`, 그 밖은 `unknown`. `GetExitCodeProcess` 실패 `unknown`, `STILL_ACTIVE`(259)가 아니면 `gone`, 경로·시각 조회 실패 `unknown`. 그 밖 OS는 `/proc` 없음 `unknown`, `/proc/<pid>` 없음·Z·X 상태 `gone`, 읽기 실패 `unknown`. `_process_identity`는 `alive`일 때만 값을 준다(표지 쓰기용). `_marker_process_state`: 표지의 프로세스 중 하나라도 세 값이 같은 채 살아 있으면 `alive`, 아니면 하나라도 `unknown`이면 `unknown`, 모두 끝났으면(또는 PID가 다른 프로세스로 재사용됐으면) `gone`. `worker_marker_state`: 어느 attempt의 표지든 `alive`면 `alive`, 읽을 수 없거나 불완전하거나 `unknown`인 표지가 하나라도 있으면 `invalid`(이전 attempt 표지 포함, 살아 있는 Worker를 가리킬 수 있으므로), 그 밖은 마지막 attempt(worktree·브랜치·표지 번호 중 가장 큰 번호; worktree 추가 전에 쓴 표지도 그 attempt로 셈)의 표지가 없으면 `missing`, 있으면 `gone`. F2: 표지 키 `task_id`·`attempt`·`pid`·`exe`·`started`(run 프로세스)·`worker`(`null` 또는 Worker의 `pid`·`exe`·`started`). `_start_run_marker`(현재 프로세스로 쓰기, 쓰기 실패는 무시해 나중의 recover만 거절되게 함)·`_end_run_marker`(삭제, 실패 무시). `_run_pipeline`은 worktree 경로를 정하고 저장소 밖임을 확인한 직후(resume 계획·`git worktree add` 전) 표지를 쓰고, 성공 경로는 `_integrate_and_checkpoint`(DONE 기록) 뒤, 실패 경로는 `record_result` 뒤에 지운다. `_run_worker`는 Worker 시작 직후 표지에 Worker를 더하고 끝나면(정상·실패·시간 초과) run만 남긴 표지로 되돌린다(삭제하지 않음). `_accept_candidate`는 `approve()` 직전에 표지를 쓰고, 승인 전이가 적용되지 않은 경우·성공·승인 뒤 실패 모두 결과 처리 뒤에 지운다. 시간 제한·`taskkill`·Worker 잠금은 그대로 |
| `adapters/discord/bot_minimal.py` | `_run_recover`·`_worker_task_state` docstring을 run 표지 기준으로 고침. `recover_worker_marker_missing`·`_invalid` 답장 문구를 "실행 표지가 없거나, 표지나 표지가 가리키는 프로세스를 확인할 수 없어 실행이 끝났는지 알 수 없습니다"로 고침(사유 문자열은 그대로) |
| `orchestrator/worker/run_smoke_tests.py` | 가짜 Worker가 표지 내용을 기록. `run_case`에 선택 인자 `on_record`. `marker_flow`: 정상·시간 초과·실패 run 모두 Worker 실행 중 표지가 run(이 프로세스)과 Worker를 가리키고 결과 기록 때 표지가 있으며 run 뒤 없음, 정상 run은 Reviewer·QA·통합 단계에도 run만 가리키는 표지가 있음, 거절된 resume은 표지를 남기지 않음, run이 끝나도 Worker가 살아 있으면 `alive`, run이 살아 있으면 `alive`, 둘 다 끝나면 `gone`, Worker 식별 정보 불완전·빈 경로 `invalid`, 식별 불가(`unknown`) `invalid`(F1), 끝난 PID가 실제 OS에서 `gone`, worktree 전에 쓴 표지가 마지막 attempt로 셈, 이전 attempt의 읽을 수 없는 표지 `invalid`. `recover_flow`: 식별 불가 프로세스면 recover가 `recover_worker_marker_invalid`(F1). `accept_flow`: 성공 accept는 승인 때와 기록 때 이 프로세스를 가리키는 표지가 있고 끝나면 없음, 승인 전이 거절도 표지를 남기지 않음, 승인 전 거절 모두 표지 없음 |
| `docs/jarvis-multi-agent-sop-v0.1.md` | §10.2 13항을 run 전체 표지·accept·식별 불가 거절·preflight 구간 한계로 고침. §10.1 진입 명령 행의 표지 설명 한 구절 |
| `docs/task-model.md` | 5-2 recover 행의 조건 문구("표지가 가리키는 프로세스가 모두 끝났을 때만") |

남는 한계(기록): Windows의 "접근 거부"로 `unknown`이 되는 실제 경로는 결정론적으로 재현하지 못해 `_probe_process`를 바꿔 끼운 테스트로만 확인했다(오류 87 → `gone`은 실제 OS에서 확인). `/proc` 경로는 이 PC(Windows)에서 실행되지 않았다. `_run_go`가 DOING으로 바꾼 뒤 pipeline이 표지를 쓰기 전(preflight의 읽기 전용 git 명령 몇 개 구간)에 봇이 죽으면 이번 실행의 표지는 없다. 이전 attempt가 남긴 표지가 없으면 recover는 `recover_worker_marker_missing`으로 거절되고, 있으면(recover는 표지를 지우지 않음) 그 표지가 마지막 attempt의 표지로 판정되어 가리키는 프로세스가 모두 끝났으면 recover가 된다. 그 구간에는 worktree와 Worker가 아직 없다(repair 2에서 이 서술을 코드에 맞게 고침, SOP 13항 동일). 식별 불가 표지가 있는 task는 시작 점검과 `/go`에서 지금처럼 `stalled`로 보이지만 recover는 거절된다.

## Repair 1 Implementer 검증 (작업 트리 기준, candidate 2 전)

`.env` 없는 임시 clone(scratchpad, `5cff917`의 `main`을 체크아웃하고 변경 파일 복사)에서 실행했다. 이제 `main`(`5cff917`)이 task-0166 브랜치들(`4416b04`)과 달라 candidate 1 때의 브랜치 선택 문제는 없지만, `.env`를 읽지 않도록 같은 방식을 썼다. 실제 봇·Discord·claude는 실행하지 않았다.

| # | 결과 |
| --- | --- |
| 정상 | Worker smoke 457/0(candidate 1의 439에서 +18: F1·F2·accept 검사), self-check 104/0(설정 없음·`PYTHONUTF8=1`, 이번 repair는 self-check 문자열을 바꾸지 않아 수 그대로), SOP validator PASS(음성 검사 133), discord-intake 141/0 |
| 변형 | 각각 전체 Worker smoke로 실행. M10 F1 되돌림(식별 불가를 `gone`으로) → 11건 실패(F1 표지 검사, F1 recover 거절, 그 뒤 recover 흐름 연쇄). M11 F2 되돌림(Worker가 끝나면 표지 삭제) → 4건(세 run의 Worker 중·기록 시 표지 검사, Reviewer·QA·통합 단계 표지 검사). M12 accept 표지 없음 → 2건(accept 승인·기록 시 표지, 승인 전이 거절 때 표지). M13 읽을 수 없는 표지 무시 → 19건(불완전·손상·다른 task 표지, 이전 attempt 손상 표지, recover 불완전 표지 거절과 연쇄). 네 변형 모두 검사가 잡았다 |
| 다시 돌리지 않은 것 | Console smoke: 이번 repair는 Console이 읽는 코드나 이 기록의 메타데이터(status·updated_at)를 바꾸지 않아 candidate 1의 PASS를 다시 확인하지 않았다. candidate 1의 M1~M9 변형도 다시 돌리지 않았다(M9 한계는 위 기록 그대로) |
| 남은 흔적 | smoke 임시 폴더 44→46. M10·M13 run이 Worker 잠금 파일을 연 채 끝나 지우지 못한 2개(`jarvis_worker_smoke_iluhmr2v`·`_5nbceqi6`). 정상 코드 run은 폴더를 남기지 않았다. Owner가 정하기 전까지 삭제하지 않고 보존 |

task-0166 기록, `-r1`·`-r2` worktree, `jarvis.bat`은 건드리지 않았다.

## Candidate 2

`bf87a66f7005f3ee85587858680c0edd2d8c0072` (repair 1, 부모 `5cff917`, 로컬 커밋, push 안 함).

## Reviewer (`bf87a66`, 유효, FINDINGS)

`self_deviations: []`로 유효한 검토였다. verdict FINDINGS, minor 2건.

| # | 지적 (요지) | Manager 대조 |
| --- | --- | --- |
| A | 표지는 run(봇)과 `_run_worker` 안의 Worker만 적는다. Reviewer claude(`_run_reviewer`, 시간 제한 900초)와 QA 하위 프로세스(`_qa_checks`, attempt worktree에서 실행)는 `started` 없이 `_run`을 거쳐 적히지 않으므로, 봇이 Reviewer·QA 단계에서 죽으면 그 자식이 아직 돌아도 `gone`이 되어 recover가 진행된다. R2 행과 "남는 한계"가 이 경우를 적지 않았다. 최소 수정: Reviewer·QA 자식을 표지에 더하거나, 한계로 적는다 | 맞다. tests 단계의 테스트와 QA·통합의 git 명령도 같다(모두 `_run`). 봇이 죽으면 이 자식들의 시간 제한도 사라진다. 다만 Reviewer는 읽기 도구만 쓰고, 두 작업 종류의 테스트는 worktree에 쓰지 않아 지금 설정에서 실제 피해 가능성은 낮다. 기록과 구현이 어긋난 실제 결함으로 분류 |
| B | SOP 13항은 "DOING 전환 뒤 표지를 쓰기 전(preflight)에 멈춘 실행도 표지가 없으므로 같은 거절"이라 하지만, 마지막 attempt를 attempt·표지 번호의 최댓값으로 정하고 recover는 표지를 지우지 않으므로, 이전 attempt가 표지를 남겼으면 preflight에서 멈춘 다음 실행은 `gone`이 되어 recover가 된다. 결과는 안전하지만 문서가 틀렸다 | 맞다. 그 구간에는 worktree·Worker가 없고(잠금이 있으면 `worker_busy`), 결과는 안전하다. 문서 결함으로 분류 |

repair 예산(1/1)이 소진되어 고치지 않고 Owner에게 보고했다. SOP §8 minor 수용 조항(수동 경로, 지적별 Owner 원문 수용, 그 candidate에만 효력, QA 전부 통과 필요)과 §5 증액(Owner만)을 함께 보고했다.

## Owner 결정: repair 예산 증액 (원문)

```text
task-0167 repair 예산을 1에서 2로 증액한다. 이 증액은 task-0167에만 적용한다.
bf87a66 위에서 repair 2로 다음을 수정한다.

* A: Reviewer, 테스트, QA 및 관련 git 자식 프로세스의 생존 여부도 recover 판단에 반영한다. 식별 정보가 불완전한 경우 fail-closed 원칙을 유지한다.
* B: SOP §10.2 item 13과 task 기록의 preflight 관련 설명을 실제 코드 동작과 일치시킨다.
* task 기록의 updated_at도 실제 수정 시점에 맞게 갱신한다.
* 새 candidate 생성 후 Reviewer와 QA를 다시 진행한다.
* 새 candidate에 한해 Reviewer 무효(self_deviations 등 자체 규칙 위반) 시 재검토 1회를 허용한다(retry_budget 1→2). 유효한 FINDINGS는 무효 처리하지 않고 그대로 보고한다.
* push, master-plan 갱신, 최종 DONE 처리는 별도 승인 전까지 하지 않는다.
* 기존 candidate bf87a66과 모든 보존 대상 임시 폴더 및 worktree는 그대로 유지한다.
```

이 증액은 task-0167에만 효력이 있다. budget: `retry_budget=2`(새 candidate의 무효 검토 재검토 1회 한정), `retry_count=1`, `repair_budget=2`, `repair_count=2`(이 repair).

## Repair 2 (A·B)

| 파일 | 변경 |
| --- | --- |
| `orchestrator/worker/claude_worker.py` | A: 표지 키를 `task_id`·`attempt`·`pid`·`exe`·`started`(run 프로세스)·`children`(실행 중인 자식 프로세스마다 `pid`·`exe`·`started`)로 바꿨다(repair 1의 `worker` 키 대체). `_RunMarker`가 이 스레드의 run 표지를 들고, `_run`이 표지가 활성일 때 시작한 프로세스를 시작 직후 `children`에 더하고 끝나면(정상·실패·시간 초과) 뺀다. Worker·Reviewer·테스트·QA·git이 모두 `_run`을 거치므로 단계와 관계없이 적힌다. 더할 때 식별 정보를 읽을 수 없으면 빈 값을 적어 표지가 `invalid`가 되고(fail closed), 이미 끝난 자식은 적지 않는다. `_marker_process_state`는 run과 모든 자식을 본다. 같은 attempt의 이전 run이 남긴 표지(봇이 죽은 뒤 다시 accept)가 아직 실행 중이거나 식별할 수 없는 프로세스를 적고 있으면 새 표지에 이어 적고, run이 끝날 때 그 프로세스가 남아 있으면 이전 run 정보로 표지를 남긴다(지우지 않음). accept는 표지를 기록된 attempt를 찾은 직후(main 확인·QA 전)부터 둔다. repair 1의 `_run(started=)` 인자와 `_run_worker(task_id)` 인자는 쓰임이 없어져 되돌렸다. 시간 제한·`taskkill`·Worker 잠금은 그대로 |
| `orchestrator/worker/run_smoke_tests.py` | 가짜 claude가 Worker·Reviewer로 실행될 때 자신(또는 `.cmd` shim)이 표지 `children`에 있는지 기록. `write_marker` fixture. `marker_flow`: Worker 실행 중 표지, Reviewer 실행 중 표지(repair 2), 단계 사이에는 run만 남음(끝난 자식은 빠짐), `_run`으로 시작한 임의 자식이 실행 중 표지에 있고 끝나면 빠짐, run 밖의 `_run`은 표지를 쓰지 않음, run이 끝나도 자식이 살아 있으면 `alive`, 자식 식별 정보 불완전·빈 경로·목록이 아님 `invalid`, 같은 attempt의 새 run이 이전 run의 살아 있는 자식을 이어 적고 끝날 때 남김, 이어 적을 프로세스가 모두 끝났으면 끝날 때 지움. `recover_flow`: 봇은 끝났고 run의 자식이 살아 있으면 `recover_worker_alive`. `accept_flow`: QA 단계에도 표지 있음 |
| `docs/jarvis-multi-agent-sop-v0.1.md` | §10.2 13항: 자식 프로세스 표지, 이전 run 프로세스 이어 적기, accept 표지 시작 시점(QA 전), B의 preflight 서술을 코드와 맞춤 |
| 이 기록 | 위 Reviewer 결과와 Owner 원문, repair 2, 검증, `updated_at` 갱신(Owner 지시, task-model 7절). Repair 1 절의 preflight 서술을 고침 |

남는 한계: 표지는 `_run`이 직접 시작한 프로세스를 적는다. 그 프로세스가 다시 띄운 손자(예: `claude.cmd`가 띄운 node)는 따로 적지 않으며, 직접 자식이 살아 있는 동안만 그 실행이 이어지는 것으로 본다. 이전 run의 표지가 읽을 수 없는 상태면 이어 적지 못하고 새 표지로 바뀐다(표지는 원자적으로 쓰므로 직접 고친 경우만 해당). [repair 3에서 정정: 이 서술은 틀렸다. 이 코드 자신이 식별하지 못한 프로세스를 빈 값으로 적어 표지를 invalid로 만들 수 있고, repair 2는 그런 표지를 덮어써 지웠다(`ad79cee` Reviewer major). repair 3부터는 아래 "Repair 3" 절대로 invalid를 유지한다.] Windows 접근 거부로 `unknown`이 되는 실제 경로와 `/proc` 경로는 repair 1과 같이 실제로 재현하지 않았다.

## Repair 2 Implementer 검증 (작업 트리 기준, candidate 3 전)

repair 1과 같은 `.env` 없는 임시 clone(scratchpad, `bf87a66`을 체크아웃하고 변경 파일 복사)에서 실행했다. 실제 봇·Discord·claude는 실행하지 않았다.

| # | 결과 |
| --- | --- |
| 정상 | Worker smoke 464/0(repair 1의 457에서 +7, `worker` 키 검사를 `children` 검사로 바꾸고 자식 프로세스·이어 적기 검사 추가), self-check 104/0, SOP validator PASS(음성 검사 133), discord-intake 141/0 |
| 변형 | 각각 전체 Worker smoke. M14 `_run`이 자식을 적지 않음 → 6건(Worker·Reviewer·임의 자식 표지 검사). M15 끝난 자식을 빼지 않음 → 3건(단계 사이 표지, 임의 자식 제거, accept 표지). M16 판정이 자식을 보지 않음 → 12건(살아 있는 자식 `alive`, 이어 적기, recover 거절과 그 뒤 연쇄). M17 이전 run 프로세스를 이어 적지 않음 → 1건(이어 적기 검사). 네 변형 모두 검사가 잡았다 |
| 다시 돌리지 않은 것 | Console smoke(Console이 읽는 코드와 이 기록의 status는 그대로. `updated_at`만 바뀜). repair 1의 M10~M13과 candidate 1의 M1~M9 |
| 남은 흔적 | smoke 임시 폴더 46→47. M16 run이 Worker 잠금 파일을 연 채 끝나 지우지 못한 1개(`jarvis_worker_smoke_c226gbw_`). 정상 코드 run은 폴더를 남기지 않았다. Owner가 정하기 전까지 보존 |

`bf87a66`, task-0166 기록, `-r1`·`-r2` worktree, `jarvis.bat`은 건드리지 않았다. `updated_at`은 이 기록 시각(`2026-10-19 04:37 UTC`)이다.

## Candidate 3

`ad79cee3f1e37c7e7788378c73a5f948eac4ace3` (repair 2, 부모 `bf87a66`, 로컬 커밋, push 안 함).

## Reviewer (`ad79cee`, 유효, FINDINGS major)

`self_deviations: []`로 유효한 검토였다. verdict FINDINGS, major 1건.

| 지적 (요지) | Manager 대조 |
| --- | --- |
| `_RunMarker.__init__`은 `_read_worker_marker`가 값을 돌려줄 때만 이전 run의 프로세스를 이어 적는다. 그런데 이 코드 자신이 식별하지 못한 자식·run을 빈 값(`exe` 빈 문자열, `started` 0)으로 적어 표지를 invalid로 만들므로, 같은 attempt의 두 번째 run(봇이 accept QA 중 죽은 뒤 다시 accept)은 그 표지를 이어 적지 못하고 덮어쓰며, `_end_run_marker`가 지운다. 기록의 한계("직접 고친 경우만 해당")와 SOP 13항("식별할 수 없는 프로세스가 있으면 새 표지에 이어 적고")이 코드와 어긋나고, 그 경우의 smoke 검사가 없다. 영향: 식별하지 못한, 아직 돌 수 있는 첫 run의 QA·git 자식이 표지에서 사라져 나중의 recover가 `gone`에 이를 수 있다(fail open) | 맞다. 재현 조건은 (1) 첫 accept에서 자식이나 봇 식별 실패로 표지가 invalid, (2) 승인 전이 전에 봇 종료(FAILED 유지), (3) 같은 기록으로 accept 다시 실행해 덮어씀, (4) 두 번째 run이 승인 뒤 멈춰 recover하거나 정상 종료로 표지 삭제. accept 경로에서만 생긴다(pipeline은 attempt 번호가 새로 정해지고, 같은 번호 표지가 남는 경우는 DOING이라 새 run이 시작되지 않음). Windows에서 자기 자식 식별이 실패할 가능성은 매우 낮지만 Owner 조건 A의 fail closed를 깨므로 major 판단은 타당. 회귀가 아니다: `bf87a66`도 같은 attempt 표지를 조건 없이 덮어썼지만 그때는 자식을 적지 않았고 accept 표지는 승인 전이 직전에 시작해 잃을 정보가 없었다. repair 2가 자식 기록·QA 전 표지·이어 적기를 더하면서 읽을 수 없는 이전 표지 경우를 빠뜨렸고 문서 두 곳을 틀리게 적은 새 결함이다 |

Reviewer가 미확인으로 남긴 "봇 작업 스레드로의 ContextVar 전달"은 Manager가 확인했다: 봇은 `asyncio.to_thread(_run_worker_job, …)`로 실행하고, 표지 ContextVar는 그 스레드 안의 `run_pipeline`·`accept_candidate`가 직접 설정·해제하므로 스레드 사이 전달이 필요 없다.

repair 예산(2/2)이 소진되었고 major는 §8 수용 대상이 아니어서 고치지 않고 Owner에게 보고했다. 수정안으로 (b) invalid 유지(권장)와 (a) accept 거절을 제시했다.

## Owner 결정: repair 예산 증액 2→3 (원문)

```text
task-0167 repair 예산을 2에서 3으로 증액한다. 이 증액은 task-0167에만 적용한다.
ad79cee 위에서 repair 3으로 다음을 수정한다.

1. 옵션 (b)를 적용한다. 같은 attempt의 기존 표지가 존재하지만 읽을 수 없거나, 불완전하거나, 다른 task를 가리키는 경우 새 실행이 이를 덮어써서 안전성 정보를 잃지 않도록 한다. 해당 상태는 invalid로 유지하고, 실행 종료 후에도 자동 삭제하지 않는다. recover는 기존 fail-closed 원칙에 따라 거절되어야 한다.
2. 빈 child identity 및 다른 task의 표지를 이용한 회귀 테스트를 추가한다. 새 실행 중과 종료 후에도 invalid 상태가 유지되고 recover가 거절되는지 확인한다. 기존 정상 표지 carry-over 테스트도 유지한다.
3. 이 동작을 SOP §10.2 item 13과 task-0167 기록에 정확하게 반영한다. Reviewer의 major finding과 이 Owner 결정을 기록하고 updated_at도 갱신한다.
4. 정상 검사와 변형 검증을 실행하고 새 candidate를 만든 뒤 Reviewer와 QA를 진행한다.
5. 새 candidate에 대한 Reviewer가 자체 규칙 위반으로 무효가 되면 기존 승인 범위에 따라 재검토 1회를 허용한다. 유효한 FINDINGS 또는 major finding은 그대로 보고하고 임의로 수용 처리하지 않는다.
6. push, master-plan 갱신, 최종 DONE 처리는 별도 승인 전까지 하지 않는다.
7. 기존 candidate ad79cee와 bf87a66, 47개 smoke 임시 폴더, task-0166 기록 및 두 worktree, jarvis.bat은 보존한다.

승인 범위는 위 repair 3, 새 candidate의 Reviewer 및 QA까지다. 추가 repair가 필요하면 다시 멈추고 Owner에게 보고한다.
```

이 증액은 task-0167에만 효력이 있다. budget: `retry_budget=2`(새 candidate의 무효 검토 재검토 1회 한정, `ad79cee` 검토는 유효해 쓰지 않음), `retry_count=1`, `repair_budget=3`, `repair_count=3`(이 repair).

## Repair 3 (major: 읽을 수 없는 이전 표지)

| 파일 | 변경 |
| --- | --- |
| `orchestrator/worker/claude_worker.py` | `_RunMarker.__init__`: 같은 attempt의 표지가 있지만 `_read_worker_marker`가 읽지 못하거나(손상·불완전, 빈 식별 값 포함) 다른 task를 가리키면, 그 파일 내용(최대 4000자)을 `earlier_unreadable`로 보관한다. `_write_marker_file`은 이 값을 `earlier_unreadable` 키로 함께 쓰고, 키 집합이 달라 그 표지는 항상 invalid로 읽힌다. run 동안의 모든 쓰기(`write`)와 끝(`_end_run_marker`)에서 이 키를 유지하며, 끝날 때 지우지 않는다. 읽을 수 있는 이전 표지의 이어 적기(repair 2)는 그대로 |
| `orchestrator/worker/run_smoke_tests.py` | `marker_flow`: 빈 child identity·다른 task·읽을 수 없는 텍스트 세 경우 각각, 새 run 시작 뒤·자식 실행 뒤·run 종료 뒤 모두 `invalid`이고 원래 텍스트가 보관됨. `recover_flow`: 빈 child identity·다른 task 표지 위에서 run이 한 번 돈 뒤에도 recover가 `recover_worker_marker_invalid`로 거절되고 아무것도 바뀌지 않음. `accept_flow`: 빈 child identity 표지가 있는 attempt를 실제 accept하면 QA·승인·기록 시점 표지가 그 텍스트를 담고, 끝난 뒤에도 표지가 남아 `invalid`. 기존 정상 표지 이어 적기 검사는 그대로 |
| `docs/jarvis-multi-agent-sop-v0.1.md` | §10.2 13항에 읽을 수 없는 이전 표지의 처리와 그 뒤 recover 거절(Owner 확인 뒤 수동 삭제 전까지) |
| 이 기록 | 위 Reviewer 결과·Manager 대조·Owner 원문, repair 3, 검증, Repair 2 절 한계 서술 정정, `updated_at` 갱신 |

운영상 결과: 이런 표지가 남은 task는 이후 어느 attempt의 recover도 `recover_worker_marker_invalid`로 거절된다(모든 attempt 표지를 보는 판정). Owner가 해당 프로세스가 없음을 확인하고 그 표지 파일을 직접 지워야 recover를 다시 쓸 수 있다.

> 정정(2026-10-19, task-0168): 위 마지막 문장은 일부 경우에만 맞다. 보존된 표지가 마지막 attempt 자신의 것이면, 지운 뒤 그 attempt에 표지가 없어 `worker_marker_state`가 `missing`을 돌려주고 `_run_recover`가 `recover_worker_marker_missing`으로 거절한다(거절 사유만 바뀜). 수동 삭제 뒤 recover가 진행될 수 있는 것은 그 표지가 더 이전 attempt의 것이고, 더 새 attempt가 자기 표지를 남긴 채 멈췄으며 그 표지가 가리키는 프로세스가 모두 끝난 경우뿐이다. 원문은 기록으로 남긴다.

## Repair 3 Implementer 검증 (작업 트리 기준, candidate 4 전)

같은 `.env` 없는 임시 clone(scratchpad, `ad79cee`를 체크아웃하고 변경 파일 복사)에서 실행했다. 실제 봇·Discord·claude는 실행하지 않았다.

| # | 결과 |
| --- | --- |
| 정상 | Worker smoke 470/0(repair 2의 464에서 +6: `marker_flow` 3, `recover_flow` 2, `accept_flow` 1), self-check 104/0, SOP validator PASS(음성 검사 133), discord-intake 141/0 |
| 변형 | 각각 전체 Worker smoke. M18 읽을 수 없는 이전 표지를 보관하지 않음(repair 2 동작) → 6건(새 검사 6건 모두). M19 종료 때 그 표지를 지움 → 6건. M20 run 동안의 쓰기에 보관 값을 넣지 않음 → 4건(run 중 상태 검사 3, accept 1). 세 변형 모두 검사가 잡았다 |
| 다시 돌리지 않은 것 | Console smoke(Console이 읽는 코드와 이 기록의 status는 그대로). 이전 repair의 M1~M17 |
| 남은 흔적 | smoke 임시 폴더 47개 그대로(이번 정상·변형 run은 폴더를 남기지 않았다) |

`ad79cee`·`bf87a66`, task-0166 기록, `-r1`·`-r2` worktree, `jarvis.bat`은 건드리지 않았다. `updated_at`은 이 기록 시각(`2026-10-19 05:02 UTC`)이다.

## Candidate 4

`429d5c8646d4fff66815e6690ee4110e6553a375` (repair 3, 부모 `ad79cee`, 로컬 커밋, push 안 함).

## Reviewer (`429d5c8`, 유효, FINDINGS minor)

`self_deviations: []`로 유효한 검토였다. verdict FINDINGS, minor 1건.

| 지적 (요지) | Manager 대조 |
| --- | --- |
| 이 기록의 "운영상 결과"(Owner가 표지를 직접 지우면 recover를 다시 쓸 수 있다), `claude_worker.py`의 `EARLIER_UNREADABLE_KEY` 주석("until the Owner has checked and removed it by hand"), SOP 13항("직접 지울 때까지 `recover_worker_marker_invalid`로 거절")은 수동 삭제 뒤 recover가 된다고 읽힌다. 그러나 보존된 표지가 마지막 attempt 자신의 표지(이번 repair가 다루는 같은 attempt accept 경우)이면, 지운 뒤 `worker_marker_state`가 `missing`을 돌려주고 `_run_recover`가 `recover_worker_marker_missing`으로 거절해 거절 사유만 바뀐다. fail closed는 유지되어 안전성 영향은 없고, 승인 3항("정확하게 반영")에 미치지 못한다 | 맞다(`worker_marker_state`의 `latest not in markers` → `missing`, `_run_recover`의 `missing` → `recover_worker_marker_missing`). 서술은 그 표지가 더 이전 attempt의 것이고 새 attempt가 멈춘 경우에만 맞다. 문서·주석의 부정확성이며 동작 결함이 아니다 |

repair 예산(3/3)이 소진되어 고치지 않고 Owner에게 보고했다(§8 minor 수용 또는 예산 증액).

## Owner 결정: minor finding 수용 (SOP §8, 원문)

```text
task-0167의 candidate `429d5c8`에 대해 Reviewer의 유효한 minor finding 1건을 SOP §8에 따라 수용한다.
수용 사유: 지적된 내용은 invalid marker를 수동 삭제했을 때의 복구 결과를 설명하는 문서와 코드 주석의 부정확성이다. 현재 확인된 동작에서는 fail-closed 원칙이 유지되므로, 이 후보의 동작 안전성을 막는 결함으로 보지는 않는다. 다만 문서 설명은 정확하지 않으므로 별도 후속 작업에서 정정해야 한다.
위 수용 사유를 task-0167 기록에 이 문구 그대로 남기고, 이 수용은 candidate `429d5c8`에만 적용한다. 관련 문서와 코드 주석은 이번 후보에서 수정하지 않는다.
이후 다음을 진행한다.

1. Reviewer 결과와 Owner의 수용 결정을 task-0167 기록에 반영한다.
2. 후보 `429d5c8`에 대해 QA 전체 검증을 수행한다.
3. QA 실패 또는 추가 결함이 발견되면 멈추고 결과를 보고한다. 추가 repair는 승인 없이 진행하지 않는다.
4. QA 통과 시에도 push, master-plan 갱신, 최종 DONE 처리는 별도 승인 전까지 하지 않는다.
5. `ad79cee`, `bf87a66`, 47개 smoke 임시 폴더, task-0166 기록과 `-r1`/`-r2` worktree, `jarvis.bat`은 기존 보존 지침대로 유지한다.
```

수용 사유(원문 그대로): 지적된 내용은 invalid marker를 수동 삭제했을 때의 복구 결과를 설명하는 문서와 코드 주석의 부정확성이다. 현재 확인된 동작에서는 fail-closed 원칙이 유지되므로, 이 후보의 동작 안전성을 막는 결함으로 보지는 않는다. 다만 문서 설명은 정확하지 않으므로 별도 후속 작업에서 정정해야 한다.

이 수용은 candidate `429d5c8`에만 효력이 있다. 위 "Repair 3" 절의 "운영상 결과" 서술, `claude_worker.py`의 `EARLIER_UNREADABLE_KEY` 주석, SOP §10.2 13항의 해당 문장은 이 candidate에서 고치지 않았으며, 같은 attempt의 표지가 보존된 경우 수동 삭제 뒤에는 `recover_worker_marker_missing`으로 거절된다는 정정은 후속 작업으로 남는다. 이 기록 갱신은 candidate를 바꾸지 않는 checkpoint commit으로 남긴다(task-0164 `42c126c`와 같은 방식).

## QA (candidate `429d5c8646d4fff66815e6690ee4110e6553a375`)

2026-10-19, `.env`·`jarvis.bat`이 없는 새 local clone(scratchpad)에서 `main`을 체크아웃해 HEAD가 candidate 그대로(`429d5c8`, 작업 트리 변경 0)임을 확인한 뒤 실행했다. 비교 기준은 `4416b04`. 실제 봇·Discord·claude는 실행하지 않았다.

| 검사 | 결과 |
| --- | --- |
| Worker smoke | 470/0. V3 재현, 표지(run 전체·자식 프로세스·이어 적기·읽을 수 없는 이전 표지 보존), F1 식별 불가 거절, recover 거절 각각과 성공, recover 뒤 `/go`, `/retry` Worker 경로 거절과 수동 task 회귀, accept 표지, 기존 task-0164·0165 검사 포함 |
| Discord self-check | 104/0, 설정 없음(`PYTHONUTF8` 없음)과 `PYTHONUTF8=1` 두 환경 |
| SOP validator | PASS, 음성 검사 133/0 |
| discord-intake smoke | 141/0 |
| Console smoke | PASS(browser shell self-test 포함) |
| `git diff --check` | `4416b04..429d5c8` 통과 |
| 변경 범위 | `bot_minimal.py`, SOP 문서, `task-model.md`, 이 기록, `claude_worker.py`, Worker smoke. owned 목록과 같고 조건부 파일(`validate_multi_agent_sop.py`)은 바뀌지 않음. `jarvis.bat` 트리에 없음 |
| 변형 | QA clone 복사본에서 다시 실행: `_run`이 자식을 적지 않음 6건, 이전 run 프로세스를 이어 적지 않음 1건, 읽을 수 없는 이전 표지를 보관하지 않음 6건, 종료 때 그 표지를 지움 6건 검출. F1 되돌림(M10)과 판정이 자식을 보지 않음(M16)은 Implementer 단계에서 검출을 확인했고, 그 두 변형이 smoke 임시 폴더를 남겼던 이력 때문에 QA에서는 다시 돌리지 않았다 |
| 실행 뒤 | QA clone 작업 트리 변경 0, HEAD 그대로. smoke 임시 폴더 47개 그대로. 남은 python 프로세스·listener 없음. 메인 checkout은 이 기록 외 변경 없음 |

판정: PASS. Reviewer minor 1건은 위 Owner 결정으로 이 candidate에 한해 수용됐다(문서·주석 정정은 후속 작업). 검증하지 않은 것: Windows 접근 거부로 `unknown`이 되는 실제 경로와 `/proc` 경로(바꿔 끼운 probe로만 확인), 실제 Discord에서의 시작 DM·recover(K9, 별도 승인), 실제 고아 Worker·Reviewer 프로세스. push·master-plan·Console Complete·DONE은 별도 승인 대기.
