# task-0119-console-write-outcome-and-confirm-status-contracts

- id: `task-0119-console-write-outcome-and-confirm-status-contracts`
- title: `Task transition 쓰기 후 refresh 실패 안내와 confirm token 404 계약을 테스트로 고정`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-10 07:20 UTC`
- updated_at: `2026-09-10 07:20 UTC`
- summary: `task-0118 audit 이 찾은 TEST GAP 2 건을 test-only 로 닫았다. 쓰기는 성공했지만 직후 Overview refresh 가 실패했을 때 화면이 낡았다고 알리는 transition 분기가 검증되지 않아, 그 문구를 성공 문구로 바꿔도 suite 가 통과했다. 같은 분기가 evidence 쪽에는 이미 고정돼 있어 그 블록을 그대로 미러링했다. 두 번째로 confirm token 을 거부하는 6 개 지점 중 4 개가 status 또는 error code 한쪽만 고정돼 있어 양쪽을 모두 단언했다. mutation 8 종 전부 새 assertion 에서 잡힌다. production 코드 변경 0.`
- source_command: `task-0118 read-only audit 이 확정한 TEST GAP 1/2 의 test-only hardening 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`8a61887`** = `origin/main` |
| 직전 작업 | task-0116 (production selection scope 테스트 경로 전환) |
| 근거 | task-0118 read-only audit (BUG 0 / TEST GAP 2 / production change 불필요) |
| 변경 파일 | `run_smoke_tests.py` + 이 기록 |
| production 코드 변경 | **없음** |

## TEST GAP 1 — 쓰기 성공 직후 refresh 실패 분기

`confirmTaskTransition()` 은 write 가 성공한 뒤 `/api/overview` 를 한 번 부르고
결과를 세 갈래로 안내한다. `loadOverview()` 는 실패해도 마지막 성공 화면을
그대로 두므로(이미 `run_smoke_tests.py` 가 단언), **failed 분기의 문구가 화면이
낡았다는 것을 사용자에게 알리는 유일한 신호**다.

그런데 그 분기가 비어 있었다. 여섯 개 결과 문구 중 실제로 고정된 것은 두 개뿐이었다.

| 흐름 | succeeded | failed | superseded |
| --- | --- | --- | --- |
| completion evidence | 미고정 | **고정** | 미고정 |
| task transition | 미고정 | **비어 있음** | **고정** |

두 흐름이 서로 다른 갈래만 하나씩 고정하고 있었고, transition 의 failed 만
어느 쪽에도 걸리지 않았다. 그래서 문구를

```text
"Overview refresh failed. The receipt remains authoritative."
→ "Overview refresh succeeded."
```

로 바꿔도 suite 가 통과했다. 이 변형은 **write 는 성공했는데 화면은 낡은 상태
그대로인 상황에서 새로고침이 됐다고 말하는** 결과를 만든다.

### 어떻게 고정했나

evidence 쪽 블록(`run_smoke_tests.py`)을 그대로 미러링했다. 기존 node harness 가
이미 제어 가능한 `/api/overview` 를 갖고 있어 **새 harness 도 새 구조도 만들지
않았다.** transition confirm 을 한 번 더 수행하되 이번에는 post-write refresh 를
500 으로 실패시키고 다음을 확인한다.

| 검사 | 내용 |
| --- | --- |
| receipt 생존 | `taskTransitionLastReceipt` 가 새 receipt 이고 live target 에 렌더된다 |
| detached target | 교체 전 target 에는 렌더되지 않는다 |
| 화면 보존 | `tasksDetails.innerHTML` 이 refresh 이전 값 그대로다 |
| 안내 문구 | `statusText` 에 실패 문구가 정확히 포함된다 |
| 반복 경고 | `nextActionText` 가 write 를 다시 하지 않는다고 알린다 |
| 요청 계약 | confirm POST 1 회 + overview GET 1 회, body 는 token/confirmation 뿐 |

여기에 소스 텍스트 단언 2 개를 더했다. transition 의 failed 문구와 evidence 의
failed 문구가 각 함수 본문에 남아 있는지 확인한다.

## TEST GAP 2 — confirm token 을 거부하는 404 계약

세 흐름 모두 confirm token 을 두 지점에서 거부한다. token 패턴 불일치(outer)와
보유하지 않은 token(inner)이며 **둘 다 같은 status·같은 error code** 로 답한다.
호출자가 두 경우를 구분하지 못하게 하려는 설계다.

task-0118 은 이 계약이 "세 흐름 모두 status 미고정"이라고 적었는데, 지점별로
확인해 보니 더 정확한 상태는 다음과 같았다. **이 정정을 여기 남긴다.**

| 지점 | status | error code |
| --- | --- | --- |
| create · outer | 미고정 | 미고정 |
| create · inner | 고정 | 고정 |
| transition · outer | 미고정 | 미고정 |
| transition · inner | **미고정** | 고정 |
| evidence · outer | 미고정 | 미고정 |
| evidence · inner | 고정 | **미고정** |

즉 여섯 지점 중 양쪽이 모두 고정된 곳은 create · inner 하나뿐이었다. 나머지
네 지점에 대해 status 와 error code 를 **둘 다** 단언하도록 보강했다. outer 는
패턴이 거부하는 token(`short/token`) 을 confirm 에 넣어 도달시켰고, 그때도 대상
Task 파일이 바뀌지 않는지 함께 확인한다.

기존 registry·fixture·헬퍼를 그대로 썼고 새 테스트 함수는 만들지 않았다.

## mutation probe

여덟 개 변형 전부가 **이번에 추가한 assertion 에서** 잡힌다.

| 변형 | 결과 | 잡은 위치 |
| --- | --- | --- |
| failed 문구를 성공 문구로 교체 | exit=1 | 소스 텍스트 단언 |
| failed 분기를 도달 불가로 변경(문구는 유지) | exit=1 | node harness |
| failed 분기가 낡은 화면을 덮어쓰게 변경 | exit=1 | node harness |
| create · outer 404 → 400 | exit=1 | 신규 malformed token 단언 |
| transition · outer 404 → 400 | exit=1 | 신규 malformed token 단언 |
| evidence · outer 404 → 400 | exit=1 | 신규 malformed token 단언 |
| transition · inner 404 → 400 | exit=1 | 신규 status 단언 |
| evidence · inner error code 변경 | exit=1 | 신규 error code 단언 |

두 번째와 세 번째 변형이 중요하다. 문구를 소스에 그대로 둔 채 **동작만** 깨뜨리는
변형이라 소스 텍스트 단언으로는 잡히지 않고, node harness 가 실제로 검증하고
있다는 것을 보여준다. 텍스트 단언 하나로 때운 것이 아니다.

모든 probe 뒤 `run_web_app.py` 와 `app.js` 를 byte-identical 로 복원했고 SHA-256
으로 확인했다.

## 테스트 결과

| 항목 | 결과 |
| --- | --- |
| Console self-test | PASS |
| Console smoke | PASS (exit=0) |
| `run_smoke_tests.py` assertion | 917 → **929** |
| `run_web_app.py` self-test assertion | 430 (무변경) |
| `git diff --check` | clean |
| diff | +101 / −2 |

`−2` 는 transition expired token 단언을 tuple 로 받도록 두 줄로 나눈 것뿐이다.
**삭제되거나 완화된 assertion 은 0 개**이고, 기존 error code 단언은 그대로 남아
있으며 status 단언이 추가됐다.

## 바꾸지 않은 것

| 대상 | 상태 |
| --- | --- |
| `run_web_app.py` · `web/app.js` · `task_file_writer.py` | 무변경 |
| `docs/*` | 무변경 |
| 테스트 구조 · 네이밍 · harness | 기존 것 재사용, 신규 프레임워크 없음 |
| task-0118 이 NOT A BUG 로 분류한 6 건 | 손대지 않음 |
| evidence · superseded, transition · succeeded 등 나머지 미고정 문구 | 이번 범위 밖 |

## 남은 것

task-0118 이 정리한 여섯 개 결과 문구 중 이번에 고정한 것은 transition 의 failed
하나다. 나머지 네 개(evidence succeeded/superseded, transition succeeded)는 여전히
미고정이지만, 그 변형은 사용자에게 **불필요한 재시도를 유도하는** 수준이지
낡은 화면을 최신이라고 말하지는 않는다. 필요하다고 판단되면 별도 task 로 다룬다.
