# task-0124-historical-evidence-current-state-separation-design

- id: `task-0124-historical-evidence-current-state-separation-design`
- title: `Historical milestone evidence 와 current-state validation 분리 (D1) 설계 승인`
- status: `TODO`
- repo: `jarvis-core`
- created_at: `2026-09-11 03:05 UTC`
- updated_at: `2026-09-11 03:05 UTC`
- summary: `rolling-window audit 이 확정한 구조적 문제에 대한 Owner 결정 2 건을 기록하고 D1 방향을 설계 대상으로 승인한다. 완료된 milestone 의 evidence 가 5 커밋 뒤 창 밖으로 밀렸다는 이유만으로 Manager Report 가 영구 blocked 되는 것은 의도한 장기 운영 모델이 아니다. 4 절 package 표는 현재 작업 목록이 아니라 historical evidence 로 정의하고 과거 hash 는 보존한다. 표시용 recent-5 계약과 검증용 evidence 를 분리하는 설계만 승인하며 window 숫자 TTL 새 schema validator 구현은 이번에 정하지 않는다. production 변경 0.`
- source_command: `rolling-window READ-ONLY audit 결과에 대한 Owner 결정 기록 및 D1 설계 승인 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`1b51a6c`** = `origin/main` |
| 직전 작업 | task-0123 (README 범위 서술 정정) |
| 근거 | rolling-window READ-ONLY audit (VERDICT **C** — 혼합) |
| 이 task 의 성격 | **DESIGN / DECISION 기록.** production 변경 없음 |
| status | `TODO` — 설계와 구현이 후속 task 로 남아 있다 |

## Owner Decision A — 완료된 milestone 의 5 커밋 이후 상태

완료된 milestone 의 historical evidence 가 5 커밋 뒤 창 밖으로 밀려났다는
이유만으로 Manager Report 가 **영구적으로 blocked 되는 것은 의도한 장기 운영
모델로 보지 않는다.**

다음 두 가지를 동일시하지 않는다.

| | |
| --- | --- |
| historical evidence 의 시간적 유효성 상실 | 과거 사실이 최근 커밋 목록에 더는 없다는 것 |
| current operational blockage | 현재 운영 상태가 실제로 막혀 있다는 것 |

**fail-closed 자체를 뒤집는 결정이 아니다.** mismatch 를 Owner 결정 요청으로
올리는 것은 `docs/manager-reporting-workflow-v0.1.md` 가 명시한 설계이고 그대로
유지한다. 이 결정이 부정하는 것은 "완료된 과거를 현재 장애로 취급하는 것"뿐이다.

## Owner Decision B — §4 package table 의 의미

`docs/master-plan.md` §4 의 package 표는 **"현재 milestone 의 작업 목록"이 아니라
"완료·검증된 milestone 에 대한 historical evidence"** 로 정의한다.

따라서 다음이 확정된다.

| 규칙 | 내용 |
| --- | --- |
| 보존 | 기존 package commit hash 는 **historical fact 로 보존**한다 |
| 금지 | 최신 HEAD 로 hash 를 갱신하지 않는다 |
| 금지 | 현재 상태를 맞추려고 과거 commit hash 를 rewrite 하지 않는다 |

현재 표에 있는 두 행은 이 정의에 따라 그대로 둔다.

```text
manager-reporting-v0.1a  325fe500a0cf3938eba2a7627fc8d8978cf0e2c3
manager-reporting-v0.1b  a11c95365020fd39d928a75f1970cf59fd0c2b37
```

## audit 핵심 발견

### window 정의

`window = {live_head} ∪ (git log -n 5 의 hash 5 개)`. 두 판정이 같은 집합을 쓴다.

| 대상 | 조건 | 매칭 |
| --- | --- | --- |
| `verified_implementation_head` | `any(c.startswith(vh) for c in (live_head, *recent))` | prefix |
| package `commit_hash` | `commit_hash in recent_set` | exact 40 자 |

### 현재 behavior

실제 history 로 재현했다. milestone 을 commit X 에 기록하면 **정확히 5 커밋 동안
유효하고 6 번째 커밋에서 두 조건이 동시에 무효화된다.**

```text
N+0 ~ N+4   verified_head VALID   package_hash VALID
N+5 이후    verified_head ABSENT  package_hash ABSENT
```

회복 경로를 막는 것은 세 제약의 결합이다.

| # | 제약 | 위치 |
| --- | --- | --- |
| 1 | package 표 **최소 1 행 필수** — 비울 수 없다 | `run_web_app.py` `_parse_master_plan_manager_packages` |
| 2 | 모든 행의 commit 이 창 안이어야 한다 | `manager_reporting_data.py` `_checkpoint_source_conflicts` |
| 3 | **conflict 가 있으면 선언된 status 를 무조건 `blocked` 로 덮어쓴다** | `manager_reporting_data.py` `build_manager_report_from_checkpoint_sources` |

3 번이 핵심이다. §2 가 이미 `Manager reporting status: milestone_complete` 를
선언하고 있는데도 **면제되지 않는다.** `milestone_complete` 는 conflict 가 빈
경우에만 읽힌다. 여기에 `package_id.startswith(milestone_id)` 가 더해져,
"완료된 milestone 이 창 밖으로 밀려난 상태"를 표현할 스키마상 방법이 없다.

### fail-closed 는 의도, 창 재사용은 구조적 귀결

두 문제를 분리해야 한다.

| 질문 | 답 | 근거 |
| --- | --- | --- |
| 오래된 evidence 를 invalid 로 보는 것이 의도인가 | **의도다** | `docs/manager-reporting-workflow-v0.1.md` — verified-HEAD / package-commit mismatch 는 blocked Manager Report 와 Owner decision request 를 만든다고 명시 |
| 새 evidence 를 기록해야만 정상으로 돌아가는 구조가 의도인가 | **명시된 근거를 찾지 못했다** | 어떤 설계문서도 "회복하려면 새 milestone 을 선언하라"고 말하지 않는다 |

5 커밋 경계는 원래 **표시 계약의 bound** 로 설계됐다.
`docs/project-control-recent-milestone-evidence-v0.1.md` 는 five commits 를
256KB · 160 자 subject · 20 파일과 같은 목록에 나열하고, Attention 유발 조건으로
명시한 것은 **HEAD 불일치와 protected `jarvis.bat`** 뿐이다. verified-HEAD absent
나 package-commit absent 는 그 문서에 없다.
`docs/jarvis-console-v0.1-checkpoint.md` 도 같다 — "owner 가 최근 5 개 커밋을
본다"는 표시 목적이고, Attention 은 "mismatch 와 protected jarvis.bat history".

그 표시용 5 개 리스트를 검증 집합으로 넘기는 것은 `run_web_app.py` 의 배선이며,
이 결합을 설명하는 설계문서는 없다. 이 정책을 도입·고정한 task record 도 **0 건**
이다 — v0.1D/v0.1E 시기로 task record 체계 이전이다.

## 왜 historical hash rewrite 가 금지되는가

두 가지 이유이며 서로 독립이다.

1. **사실 위조다.** `manager-reporting-v0.1a/b` 는 2026-07-23 커밋에서 나왔다.
   hash 를 최신 HEAD 로 바꾸면 "이 package 가 그 커밋에서 검증됐다"는 진술
   자체가 거짓이 된다. Decision B 가 이 표를 historical evidence 로 정의한 이상
   rewrite 는 정의와 정면으로 충돌한다.
2. **이미 기록된 정책이다.** `docs/chatgpt-handoff.md` 의 Technical Debt 행이
   *"do not rewrite hashes or enlarge evidence windows to hide the conflict"* 를
   명시한다. 이 문구는 **유지한다.** 삭제하거나 약화시키지 않는다.

같은 이유로 window 를 단순히 키우는 방식도 이번 설계 대상에서 제외한다. 그것은
충돌을 해결하는 것이 아니라 가리는 것이다.

## 왜 표시 계약과 validation 계약을 분리해야 하는가

하나의 bound 가 두 개의 서로 다른 목적을 동시에 지고 있다.

| 목적 | 무엇이 필요한가 | 현재 |
| --- | --- | --- |
| 표시 | Owner 가 한 화면에서 볼 수 있는 **작은** 목록 | `git log -n 5` |
| 검증 | milestone evidence 가 실재하는지 판단할 **정확한** 근거 | **같은 5 개 목록을 재사용** |

표시 목적은 작을수록 좋고 검증 목적은 그럴 이유가 없다. 두 요구가 반대 방향
인데 하나의 상수에 묶여 있어서, 표시를 위해 고른 5 라는 숫자가 검증 유효기간이
돼 버렸다. 분리하면 각 계약이 자기 목적에 맞는 근거를 갖는다.

## D1 승인 — 설계 방향만

다음 개념 분리를 **설계 대상으로 승인한다.** 구현은 이번 작업에서 하지 않는다.

| 개념 | 역할 |
| --- | --- |
| **Historical Evidence** | 과거 milestone/package 가 실제로 어느 commit 에서 검증됐는지 보존한다. hash 를 rewrite 하지 않는다 |
| **Current State Evidence** | 현재 milestone 과 운영 상태가 정상인지 판단한다. 표시용 recent-5 계약에 종속시키지 않는다 |

## 이번 task 에서 결정하지 않은 것

| 항목 | 상태 |
| --- | --- |
| window 숫자 | **결정하지 않음** |
| TTL | **결정하지 않음** |
| 새 schema field | **결정하지 않음** |
| validator 구현 방식 | **결정하지 않음** |
| D2 (`milestone_complete` 면제) · D3 (표 최소 행 완화) · D4 (attestation) | **선택하지 않음** — D1 만 승인됐다 |

D1 설계 과정에서 D2~D4 중 일부가 함께 필요하다고 밝혀질 수 있다. 그 판단은
설계 task 의 결과물이며 지금 미리 정하지 않는다.

## Acceptance criteria

이 task 는 다음이 모두 성립하면 완료로 본다.

1. Owner Decision A 와 B 가 canonical record 로 남는다.
2. D1 이 설계 방향으로 승인됐다는 사실이 기록된다.
3. historical hash rewrite 금지 근거가 문서화된다.
4. `docs/chatgpt-handoff.md` 의 *"do not rewrite hashes or enlarge evidence
   windows"* 문구가 **그대로 유지된다.**
5. master-plan §4 의 package commit hash 2 건이 **변경되지 않는다.**
6. production 코드 · 테스트 · schema 변경이 **0 건**이다.
7. 기존 smoke suite 가 통과한다.
8. 후속 implementation task 가 필요하다는 사실이 명시된다.

## 후속

**production 구현은 이 task 의 범위가 아니다.** 별도 task 가 필요하다.

| 후속 | 범위 | 승인 |
| --- | --- | --- |
| **D1 설계** | Historical / Current State evidence 분리 설계. window·TTL·schema·validator 를 여기서 결정 | 설계 산출물에 대한 Owner 승인 필요 |
| **D1 구현** | 설계 확정 후 production 변경 | 별도 승인 |

그때까지 Project Control 카드가 `attention` 이고 Manager/Director 가 `blocked`
인 것은 **현재 구조의 정상 귀결이며 결함이 아니다.** 그 상태를 감추기 위해
hash 나 window 를 건드리지 않는다.
