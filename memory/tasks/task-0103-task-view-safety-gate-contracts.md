# task-0103-task-view-safety-gate-contracts

- id: `task-0103-task-view-safety-gate-contracts`
- title: `Task View 선택 범위 · ON_HOLD 렌더링 · evidence DOING 게이트 고정`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-09 11:31 UTC`
- updated_at: `2026-09-09 11:31 UTC`
- summary: `task-0102 가 찾은 3 개 gap 을 test-only 로 닫았다. Actionable Task View 선택 범위 밖 Task 가 Start Complete Record Evidence 에서 404 로 거부되는지, ON_HOLD 가 렌더러에서 read-only 로 그려지는지, evidence 게이트가 비-DOING 6 개 status 전부를 409 로 거부하는지다. 셋 다 동작은 원래 옳았고 검증만 없었다. 11 개 fixture 하나로 1 번과 3 번을 함께 덮었고 렌더러 status 리스트에는 drift guard 를 붙였다. 각 mutation 이 HEAD suite 에서는 통과하고 새 suite 에서는 실패하는 것을 전후 비교로 확인했다. production 코드 변경 0.`
- source_command: `task-0102 audit 이 확정한 3 개 TEST_GAP 의 test-only hardening 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`d163069`** = `origin/main` |
| 직전 작업 | task-0101 (writer 전이 positive contract) |
| 변경 파일 | `run_smoke_tests.py` + 이 기록 |
| production 코드 변경 | **없음** |

## 무엇을 닫았나

task-0102 가 찾은 4 개 gap 중 3 개다. 네 번째(disclosure 미결속 · 죽은 상수
`TASK_VIEW_DISCLOSURE`)는 production 판단이 필요해 이번 범위에서 제외했다.

세 gap 모두 **동작은 원래 옳았고 검증만 없었다.** 새 동작을 만들지 않았다.

### 1. Actionable Task View 선택 범위 게이트

Actionable Task View 는 backlog 전체가 아니라 `OVERVIEW_MAX_ITEMS_PER_DIRECTORY`
로 잘린 선택이고, 쓰기 표면은 그 선택에 한정된다. 그런데
`task_not_found_in_actionable_view` 와
`completion_evidence_task_not_found_in_actionable_view` 는 smoke 에서 **0 회**
단언되고 있었다. 선택을 **넓히는** 변형은 기존 단언을 깨뜨릴 수 없다 — 넓히면
선택 가능한 Task 가 늘어날 뿐이라 성공 단언도, 404 아닌 error code 단언도 모두
그대로 통과한다.

### 2. ON_HOLD 렌더링

렌더러 테스트가 status 를 두 하드코딩 리스트로 돌리는데 task-0098 이 어휘를
넓힐 때 `ON_HOLD` 가 어느 쪽에도 들어가지 않았다. **7 개 중 6 개만** 렌더된 것이다.

다만 `action` 삼항식은 기존 exact-text 단언이 이미 고정하고 있어, Start/Complete
오분류는 전부터 잡혔다. 실제로 비어 있던 곳은 **`recordEligible`** 이다. 이 쪽은
source-pinned 가 아니고, 기존 read-only 루프는 evidence 버튼을 검사하지 않았다.

### 3. Completion evidence DOING 전용 게이트

`completion_evidence_task_not_doing` 이 **TODO 픽스처 하나로만** 검증되고 있었다.
게이트를 `not in {"DOING", "BLOCKED"}` 로 완화해도 TODO 테스트는 통과한다.

## 어떻게 고정했나

### fixture 하나로 1 번과 3 번

`fixture_root / "selection-scope"` 에 **11 개** Task 를 만든다. 기존
`task_bytes` 헬퍼와 기존 fixture 수명주기(`finally` 의 `rmtree`)를 재사용했고
새 헬퍼는 만들지 않았다.

- 상위 10 개는 `os.utime` 으로 내림차순 mtime 을 명시해 in-view 로 고정한다.
  파일시스템 타임스탬프 해상도에 의존하지 않는다.
- 11 번째는 가장 오래된 mtime 이라 선택 밖이며, **status 는 TODO** 다.

11 번째를 TODO 로 둔 것이 핵심이다. Start 가 status 상 합법인 Task 이므로,
404 가 status 오류나 경로 오류가 아니라 **선택 게이트** 때문임이 드러난다. 같은
status 의 in-view TODO 가 Start preview 에서 200 을 받는 대조 단언도 함께 둔다.

in-view 10 개의 status 집합은 공식 7 개 전부를 덮고, 그것을
`set(TASK_VIEW_STATUS_RULES)` 와 대조한다. 8 번째 status 가 생기면 여기서 깨진다.
그 10 개 중 DOING 이 아닌 것 전부에 evidence preview 를 걸어 409 를 확인한다 —
3 번 gap 이 같은 fixture 로 닫힌다.

### 렌더러 drift guard

두 status 리스트를 Python 쪽 이름으로 빼고 JSON 으로 harness 에 주입한 뒤,
합집합이 `TASK_VIEW_STATUS_RULES` 와 같은지, 교집합이 비었는지 단언한다.
`"ON_HOLD"` 한 단어를 read-only 리스트에 넣는 것보다 이쪽이 다음 확장까지 막는다.
read-only 루프에는 두 가지를 더 넣었다 — 자기 status 배지가 실제로 그려지는지,
그리고 **evidence 버튼이 없는지**. 후자가 없어서 2 번 gap 이 비어 있었다.

## mutation probe — 전후 비교

각 변형을 **HEAD suite** 와 **새 suite** 양쪽에 걸었다. HEAD 에서 통과하고
새 suite 에서 실패해야 gap 이 실재했고 닫혔다는 뜻이다.

| 변형 | HEAD suite | 새 suite |
| --- | --- | --- |
| 선택 상한 제거 (`discovered[:N]` → `discovered`) | **exit=0** | **exit=1** |
| `recordEligible` 이 ON_HOLD 를 허용 | **exit=0** | **exit=1** |
| evidence 게이트가 BLOCKED 를 허용 | **exit=0** | **exit=1** |

실패 지점도 의도한 곳이다.

| 변형 | 새 suite 실패 지점 |
| --- | --- |
| 선택 상한 제거 | 선택 밖 Task 의 404 단언 |
| ON_HOLD evidence 허용 | node harness `ON_HOLD did not render the read-only badge exactly` |
| evidence 게이트 완화 | `assert not_doing_result[0] == HTTPStatus.CONFLICT` → `AssertionError: BLOCKED` |

추가로 테스트 쪽 변형도 확인했다. read-only 리스트에서 `ON_HOLD` 를 빼면
drift guard 가 즉시 실패한다.

정직하게 남기는 결과 하나. `action` 삼항식에 ON_HOLD 를 끼워 넣는 변형은
**기존** exact-text 단언이 먼저 잡는다. 그 변형은 이번 작업의 성과가 아니다.

모든 probe 뒤 `run_web_app.py` · `app.js` · `run_smoke_tests.py` 를 byte-identical
로 복원했다.

## 테스트 결과

| 항목 | 결과 |
| --- | --- |
| Console self-test | PASS |
| Console smoke | PASS |
| 전체 regression 9 종 sequential | 전부 exit=0 |
| `git diff --check` | clean |
| fixture 잔여물 | 없음 |

## 규모

| 항목 | 값 |
| --- | --- |
| fixture 파일 | 11 개 (기존 `task_bytes` · 기존 fixture_root 재사용) |
| 새 Python assertion | 17 개 |
| 새 JS 검사 | 2 개 (status 배지, evidence 버튼) |
| 삭제된 assertion | **0 개** |
| diff | +151 / −2 |

`−2` 는 JS status 리스트 두 줄이 이름 있는 상수 참조로 바뀐 것뿐이다. 리스트
내용은 유지 + `ON_HOLD` 추가이고, 루프 본문은 검사가 늘었을 뿐 줄지 않았다.

## 바꾸지 않은 것

| 대상 | 상태 |
| --- | --- |
| `run_web_app.py` · `web/app.js` · `task_file_writer.py` · `bot_minimal.py` | 무변경 |
| `docs/*` | 무변경 |
| 기존 43 개 transition rejection · 6 개 positive transition (task-0101) | 무변경 |
| task-0099 secret-like filename 정책 | 무변경 |
| `TASK_VIEW_DISCLOSURE` 죽은 상수 | 이번 범위 밖 — 별도 판단으로 남김 |
| task-0097 ~ task-0102 기록 | 무변경 |
