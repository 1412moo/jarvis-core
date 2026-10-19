# task-0166-studyroom-glossary-r1-1

- id: `task-0166-studyroom-glossary-r1-1`
- title: `Studyroom glossary에 R1 검증용 용어 1개 추가`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-10-18 15:57 UTC`
- updated_at: `2026-10-19 10:55 UTC`
- summary: `요청 사항(Studyroom glossary에 R1 검증용 용어 1개 추가)을 작업 초안으로 정리한다. 이번 단계는 draft object 생성 규칙 정의까지만 포함한다.`
- source_command: `/task`
- execution_candidate: `true`
- execution_request: `{"action":"claude_worker_pipeline","execution_type":"claude_worker","requested_at":"2026-10-19 10:55 UTC","result_type":"execution_request","source":"/go","target":"studyroom_content","task_id":"task-0166-studyroom-glossary-r1-1"}`
- execution_result: `{"action":"claude_worker_pipeline","error_reason":"","executed":true,"execution_type":"claude_worker","result_type":"execution_result","success":true,"task_id":"task-0166-studyroom-glossary-r1-1"}`
- executed: `true`
- success: `true`
- dry_run: `false`
- execution_updated_at: `2026-10-19 10:55 UTC`
- execution_summary: `worker candidate bfc3f6d accepted by the Owner after QA, Reviewer not called again`

## Owner 예외 승인: D2 한 번 예외로 DOING→FAILED (원문)

```text
[Owner 명시적 결정 — task-0166 한정 예외 승인]
task-0166에 한해, 실행 표지가 없는 과거 Worker 시도를 FAILED로 종결할 수 있도록 D2 정책의 예외를 한 번 승인한다.
승인 범위:

1. task-0166의 기존 `DOING` 상태와 실행 기록을 보존한다.
2. r2가 실행 결과를 기록하지 못하고 중단된 사실과 실행 표지가 없다는 사실을 기록한다.
3. 프로젝트의 정식 기록 함수와 감사 절차를 사용해 `DOING → FAILED` 전이를 수행한다. 임의로 task 파일을 직접 수정해 상태만 바꾸지 않는다.
4. 실패 원인은 실제 증거에 맞게 기록한다. 확인되지 않은 원인을 단정하지 않는다.
5. 이후 복구는 기존 정책에 따라 Owner가 Discord에서 명시적으로 `/go task-0166-studyroom-glossary-r1-1 resume`를 실행한 경우에만 진행한다.
6. resume 시 기존 r2의 `glossary.json` 변경 7줄을 보존하고 재사용한다. 이미 존재하는 변경을 중복 구현하지 않는다.
7. 이후 Reviewer, QA, main 반영, Console Complete 등 기존 공식 절차를 모두 따른다.

제한:

* 이번 예외는 task-0166에만 적용하며 일반적인 marker-missing 복구 정책을 변경하지 않는다.
* 다른 task의 상태나 기록을 변경하지 않는다.
* `git push` 및 무관한 worktree·smoke 임시 폴더 삭제는 하지 않는다.
* 기존 변경이 예상과 다르거나 정식 상태 전이 함수를 사용할 수 없다면 진행을 멈추고 보고한다.

먼저 예외 승인과 FAILED 전이만 처리하고 결과를 보고해. Discord resume은 Owner가 직접 실행하기 전까지 시작하지 마.
```

이 예외는 task-0166 한 건에만 적용된다. task-0167 D2 (a)(표지 없는 시도는 `recover_worker_marker_missing`으로 거절)와 SOP §10.2-13, `_run_recover`의 동작은 바뀌지 않는다.

## 전이 전 기록 보존 (2026-10-19 10:25 UTC 기준, 원래 메타데이터 값 그대로)

아래 실행 필드는 r1 시도의 결과다. 전이 함수가 실행 필드를 새 실패 기록으로 바꾸므로 원래 값을 여기에 남긴다.
전이 전 이 파일의 SHA-256은 `b870bd9b8499f7f2723eba4bc31f1738be43ec760fc7b91bc3420fc5a4772ff9`(본문 없음, 메타데이터만)이다.

| 필드 | 원래 값 |
| --- | --- |
| `status` | DOING |
| `updated_at` | 2026-10-18 16:27 UTC |
| `execution_request` | {"action":"claude_worker_pipeline","execution_type":"claude_worker","requested_at":"2026-10-18 15:58 UTC","result_type":"execution_request","source":"/go","target":"studyroom_content","task_id":"task-0166-studyroom-glossary-r1-1"} |
| `execution_result` | {"action":"claude_worker_pipeline","error_reason":"worker:worker_timeout","executed":true,"execution_type":"claude_worker","result_type":"execution_result","success":false,"task_id":"task-0166-studyroom-glossary-r1-1"} |
| `executed` | true |
| `success` | false |
| `dry_run` | false |
| `execution_updated_at` | 2026-10-18 15:58 UTC |
| `execution_summary` | worker:worker_timeout |

## 증거 (확인된 사실과 미확인 사항)

| 항목 | 내용 |
| --- | --- |
| r1 | 감사 seq 10(`/go`, TODO→DOING, 2026-10-18T15:57:53Z) → seq 11(실행 결과 failure, 15:58:15Z). 22초 만의 `worker:worker_timeout`이며 worktree `-r1`에는 변경이 없다. 이 길이의 timeout을 정한 설정은 저장소·`adapters/discord/.env` 키 이름에서 찾지 못했다(`jarvis.bat`은 열지 않았다) |
| r2 시작 | 감사 seq 12(`/go`, TODO→DOING, 2026-10-18T16:27:20Z). worktree·브랜치 `jarvis/task-0166-studyroom-glossary-r1-1-r2`가 같은 시각에 생겼다 |
| r2 결과 없음 | seq 12 뒤에 이 task의 실행 결과 감사가 없고, 실행 기록은 r1 값 그대로이며 상태는 DOING이다. r2 브랜치에 candidate commit이 없다(main 조상 `4416b04`) |
| r2 변경 | worktree에 미커밋 `apps/studyroom/content/glossary.json` +7줄(용어 `cache-control` 1개). diff SHA-256 `ea049678f686991af57efe1c155fcff90097b30a12d4299505e5fa9786da9c6a`. main의 같은 파일에 용어 1개를 더한 것과 정확히 같고 JSON 유효·id 중복 없음. r2 기준 이후 main에서 이 파일은 바뀌지 않았다 |
| 실행 표지 | 없음. r2는 실행 표지(task-0167, R2) 도입 전에 시작됐다. 2026-10-19 Discord `/go … recover`는 `recover_worker_marker_missing`으로 거절됐다(task-0167 K9) |
| 프로세스 | 2026-10-19 10:2x UTC에 명령줄에 `acceptEdits`·`task-0166`·`bot_minimal`이 있는 프로세스 없음(참고 사실. D2에 따라 이것만으로 종료를 판정하지 않았고 이번 전이는 위 Owner 예외에 근거한다) |
| 미확인 | r2가 어느 단계에서 왜 멈췄는지(봇 종료, 프로세스 중단 등)는 기록이 없어 확인하지 못했다. Worker가 끝났는지, scope·tests 단계에 들어갔는지도 알 수 없다 |

## DOING→FAILED 전이 결과 (Owner 예외, 2026-10-19 10:26 UTC)

| 항목 | 결과 |
| --- | --- |
| 방법 | `bot_minimal._run_recover`와 같은 순서와 함수를 쓴 일회성 로컬 스크립트(저장소 밖). DOING·`/work` 경로 확인 → Worker 잠금 2개 획득 → `worker_marker_state`가 정확히 `missing`(`task-0166-studyroom-glossary-r1-1-r2.worker.json` 없음)일 때만 진행 → `_apply_execution_result`(실패 기록과 `DOING→FAILED`를 한 번의 원자적 쓰기) → `_audit_owner_approval` → `_audit_execution_result` → 잠금 해제. 표지 확인을 거절 사유로 쓰지 않은 것만 승인된 예외다 |
| 실패 기록 | `recover:owner_exception_no_marker_no_result`(결과와 표지가 없다는 사실만 적고 원인은 단정하지 않음). 이전 기록 `worker:worker_timeout (2026-10-18 15:58 UTC)`은 위 보존 표에 있다 |
| 적용 | applied=true, 상태 `FAILED`, `updated_at` 10:26 UTC |
| 감사 | seq 13 `owner_approval`(DOING→FAILED, applied, command에 Owner 예외·로컬 CLI 명시), seq 14 `execution_result`(failure). `verify-chain` valid, length 14 |
| 보존 | `-r2` worktree diff SHA-256 전과 같음(`ea049678…`), `-r1`·`-r2` worktree·브랜치 그대로, 다른 task 기록·main tracked 파일 변경 없음 |
| resume 사전 확인(읽기 전용) | 파이프라인의 `_plan_resume`가 다음 시도 `-r3`, 원본 `jarvis/task-0166-studyroom-glossary-r1-1-r2`, 복사 경로 `apps/studyroom/content/glossary.json` 하나로 판정(충돌·범위 위반 없음). main의 tracked 변경 없음 |

다음 단계는 Owner가 Discord에서 `/go task-0166-studyroom-glossary-r1-1 resume`을 보낼 때만 진행한다. 그 뒤 Reviewer → QA → main 반영 → DONE은 파이프라인 공식 절차를 따른다.
