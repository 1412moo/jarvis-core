# task-0126-historical-evidence-ancestry-implementation

- id: `task-0126-historical-evidence-ancestry-implementation`
- title: `D1 구현 — historical evidence 를 branch ancestry 로 검증`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-11 05:30 UTC`
- updated_at: `2026-09-11 05:30 UTC`
- summary: `task-0125 설계를 Owner 승인에 따라 구현했다. 기존 검증은 commit 의 존재를 확인한 적이 없고 최근 5 개 목록 포함 여부만 봤다. 이제 merge-base --is-ancestor 로 이 branch 역사의 일부인지 묻는다. 답이 만료되지 않으므로 window 숫자도 TTL 도 schema 변경도 없다. Manager/Director 가 blocked 에서 milestone_complete 로 바뀌고 git evidence conflict 3 건이 사라졌으며 카드는 approval_state 때문에 attention 을 유지한다. mutation 9 종 전부 새 assertion 이 잡는다. historical hash 와 MAX_COMMITS 는 무변경.`
- source_command: `Owner 의 Option C 및 git allowlist 확장 승인에 따른 D1 구현 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`a1016f2`** = `origin/main` |
| 설계 | task-0125 (Option C) |
| Owner 결정 | task-0124 (Decision A/B, D1 승인) |
| 승인 범위 | **Option C 채택** + **git allowlist 확장** |

Owner 는 두 항목을 명시적으로 승인했고, task-0125 §16 의 나머지 세 항목(TTL
미도입 · schema 변경 0 · D2/D3/D4 미포함)은 Option C 채택의 직접 귀결이므로 함께
적용했다. **D2/D3/D4 는 채택하지 않았다.**

## 무엇이 문제였나

기존 검증은 **commit 의 존재를 확인한 적이 없다.**

`READ_ONLY_GIT_COMMANDS` 는 고정 7 개였고 임의 commit 을 물을 수 있는 명령이
하나도 없었다. 그래서 `"absent from Git evidence"` 는 실제로는 **"최근 5 개 안에
없다"** 를 뜻했고, 다음 두 경우가 같은 메시지를 냈다.

| 경우 | 기존 판정 | 실제 |
| --- | --- | --- |
| 실재하는 2026-07-23 commit 이 창 밖으로 밀림 | absent | **정상적인 historical fact** |
| 존재한 적 없는 40-hex 문자열 | absent | **조작 또는 오류** |

실측하면 표에 박힌 세 hash 는 전부 실재하며 HEAD 의 조상이다(118~122 커밋 뒤).
**historical evidence 는 참이었고 시스템만 그것을 볼 수 없었다.**

## 무엇을 바꿨나

질문을 바꿨다. `commit_hash in recent_set` → **`이 commit 이 이 branch 역사의
일부인가`**. history 는 자라기만 하므로 한 번 조상이면 영원히 조상이고, 답이
만료되지 않는다.

### `run_web_app.py`

| 추가 | 내용 |
| --- | --- |
| `ANCESTRY_GIT_COMMAND_PREFIX` · `HISTORICAL_COMMIT_PATTERN` | `merge-base --is-ancestor` 와 `[0-9a-f]{7,40}` |
| `validate_read_only_git_args` 확장 | **인자를 받는 유일한 allowlist 항목.** 형태가 고정(`4-tuple`, prefix 고정, `args[3] == "HEAD"`)이고 변수는 hash 하나뿐 |
| `commit_is_branch_ancestor` | exit 0 → True, **1·128 → False**, 그 외 → `RegistryError` |
| `historical_commit_ancestry` | 기록된 commit 별로 한 번씩 답을 만든다 |
| `project_control_payload` 배선 | 표시용 목록 옆에 답을 함께 전달 |

축약 hash 를 허용한 이유는 `verified_implementation_head` 가 원래 prefix 매칭을
허용했고 실제 픽스처가 7 자·16 자를 쓰기 때문이다.

### `manager_reporting_data.py`

| 변경 | 내용 |
| --- | --- |
| `_LIVE_GIT_FIELDS` | `historical_commit_ancestry` 추가 |
| `_historical_commit_ancestry` | mapping · 비어 있지 않은 str 키 · **bool 값**을 강제 |
| `_commit_is_historical_evidence` | `ancestry.get(commit) is True` — **답이 없으면 unverified** |
| 적용 지점 3 곳 | verified HEAD · checkpoint package · **worker report**(현재 미사용이나 같은 결함) |
| 제거 | `recent_set` — historical 판정에 더는 쓰지 않는다 |

adapter 는 여전히 Git 도 파일시스템도 건드리지 않는다. **조회는 Console 이 하고
답만 전달한다.**

## 결과

| | 이전 | 이후 |
| --- | --- | --- |
| Manager Report | `blocked` | **`milestone_complete`** |
| Director Report | `blocked` | **`milestone_complete`** |
| source_conflicts | 3 | **0** |
| project card | `attention` | `attention` |
| attention 사유 | git evidence 3 건 | **`Approval state: required` 1 건** |

카드가 `attention` 을 유지하는 것은 옳다. §2 가 선언한 승인 대기는 실제로 참이며,
이번 변경이 지운 것은 **거짓이던 3 건**뿐이다.

## mutation probe — 9/9

각 변형을 적용하고 두 suite 를 돌린 뒤 byte 단위로 복원했다(SHA-256 확인).

| 변형 | 결과 | 잡은 곳 |
| --- | --- | --- |
| M1 historical 검사가 항상 통과 | **CAUGHT** | console + hermes |
| M2 답 없는 commit 을 valid 로 기본값 | **CAUGHT** | console |
| M3 ancestry 가 recency 로 되돌아감 | **CAUGHT** | console |
| M4 bool 아닌 답을 허용 | **CAUGHT** | console |
| M5 probe 가 exit 1 을 조상으로 취급 | **CAUGHT** | console |
| M6 allowlist 가 hash 형태 검사 중단 | **CAUGHT** | console |
| M7 allowlist 가 `HEAD` 인자 고정 해제 | **CAUGHT** | console |
| M8 잘못된 commit 이 probe 를 통과 | **CAUGHT** | console |
| M9 Console 이 package commit 답을 안 만듦 | **CAUGHT** | console |

첫 실행에서 **M5 와 M9 는 MISSED 였다.** 그대로 두지 않고 원인을 조사했다.

- **M5** — 이 저장소는 **모든 commit 이 HEAD 의 조상**이라(`rev-list --all --not
  HEAD` = 0) exit 1 을 픽스처로 만들 수 없었다. 그래서 `commit_is_branch_ancestor`
  에 runner seam 을 추가했다. 이 저장소가 writer·registry 에서 이미 쓰는 패턴이며
  (`_open_temp_file`, `token_factory`, `clock`, `writer=`), 테스트 전용으로 새로
  만든 구조가 아니다. 이제 0/1/128 과 그 외를 직접 단언한다.
- **M9** — 기존 단언이 live 상태를 재계산하는데 `approval_state != "none"` 이면
  어느 분기도 단언하지 않는 구멍이 있었다. live payload 의 conflict 에
  `"is absent"` 가 없어야 한다는 단언을 추가해 배선을 고정했다.

## 테스트

`_test_historical_evidence_uses_branch_ancestry` 를 추가했다. task-0125 가 정의한
9 개 case 를 **고정 픽스처**로 덮는다 — 기존 단언은 live 상태를 재계산해서
카드가 `attention` 이든 `observed` 이든 통과하므로 어느 방향도 고정하지 못했다.

| Case | 내용 |
| --- | --- |
| 1·2 | 최근 목록에 없는 historical evidence 가 conflict 0 |
| 3·4 | branch drift 와 protected-path 위반은 여전히 blocked |
| 5·6 | 조작·비조상 evidence 는 거부 |
| 7 | display 목록만 바꿔도 판정 불변 |
| 8 | 답 없는 commit 은 fail-closed |
| 추가 | bool 아닌 답 거부, exit code 매핑, allowlist 인접 6 종 거부, live payload 배선 |

## 무결성

| 위험 | 결과 |
| --- | --- |
| historical hash rewrite | **없음.** 오히려 rewrite 할 이유가 사라졌다 |
| false freshness | **없음.** 신선하다고 주장하지 않고 "역사에 있다"고만 주장한다 |
| silent validation bypass | **없음.** conflict 를 무시한 것이 아니라 참인 evidence 가 conflict 를 만들지 않게 했다. `reconcile_project_control_reporting_state` 의 "conflict ⇒ blocked" 불변식은 그대로다 |
| evidence 위조 | **어려워졌다.** 실재하지 않거나 조상이 아닌 hash 가 명시적으로 거부된다 |
| window 확대 | **하지 않았다.** `MAX_COMMITS = 5` 는 display 계약으로 유지 |
| fail-closed 약화 | **없다.** 조회 실패·형식 위반·미응답 전부 거부 |

`docs/chatgpt-handoff.md` 의 *"do not rewrite hashes or enlarge evidence windows
to hide the conflict"* 문구는 **그대로 유지**된다.

## 바꾸지 않은 것

| 대상 | 상태 |
| --- | --- |
| master-plan §4 historical hash 2 건 | **무변경** — `325fe500`, `a11c9536` |
| §2 `verified_implementation_head` | **무변경** |
| `MAX_COMMITS = 5` | **무변경** |
| master-plan schema · `MASTER_PLAN_FIELDS` · workstream 6 행 | **무변경** |
| `README.md` | **무변경** |
| `jarvis.bat` | **접근하지 않음** |
| D2 · D3 · D4 | **채택하지 않음** |

## 남은 것

| 항목 | 상태 |
| --- | --- |
| §2 `Last verified` · `verified_implementation_head` 값이 2026-07-23 | 문서 신선도 문제로 남는다. **이제 blocked 를 만들지 않는다** |
| D3 "milestone 사이" 상태 표현 | 필요해지면 독립 주제 |
| D4 attestation — "당시 validation 이 통과했다"는 별개 주장 | 필요해지면 별도 task |
| T3 Console selected-state 표현 | **별도 Owner 승인 대기** (task-0121) |
