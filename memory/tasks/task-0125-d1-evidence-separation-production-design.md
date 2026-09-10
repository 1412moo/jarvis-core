# task-0125-d1-evidence-separation-production-design

- id: `task-0125-d1-evidence-separation-production-design`
- title: `D1 production 설계 — historical evidence 를 ancestry 로 검증하고 current-state 와 분리`
- status: `TODO`
- repo: `jarvis-core`
- created_at: `2026-09-11 04:15 UTC`
- updated_at: `2026-09-11 04:15 UTC`
- summary: `task-0124 가 승인한 D1 을 구현 착수 가능한 수준으로 설계했다. 조사 중 핵심 사실을 찾았다 — 현재 검증은 commit 존재를 확인하지 않고 최근 5 개 목록 포함 여부만 본다. 즉 실재하는 오래된 commit 과 조작된 hash 를 구분하지 못하고 같은 메시지를 낸다. 따라서 historical evidence 는 recency 가 아니라 ancestry 로 검증해야 하며 그 경우 window 숫자도 TTL 도 필요 없다. 9 개 conflict 중 문제는 2 개뿐이고 나머지는 current-state 로 이미 정확하다. schema 변경 0 을 목표로 하는 안을 추천한다. production 변경 0.`
- source_command: `task-0124 D1 승인에 따른 production 설계 지시`

## 1. 기준선과 참조

| 항목 | 값 |
| --- | --- |
| baseline | **`56810d4`** = `origin/main` |
| 직전 작업 | task-0124 (Owner Decision A/B, D1 승인) |
| 이 task 의 성격 | **설계 전용.** production · test 변경 0 |
| status | `TODO` — Owner 승인과 구현이 남아 있다 |

**Owner Decision A** (task-0124) — 완료된 milestone 의 evidence 가 recent-5 창
밖으로 밀렸다는 이유만으로 Manager Report 가 영구 blocked 되는 것은 의도한 장기
운영 모델이 아니다. historical evidence 의 시간적 범위와 current operational
blockage 를 동일시하지 않는다.

**Owner Decision B** (task-0124) — §4 package 표는 완료·검증된 milestone 의
historical evidence 이며 commit hash 는 historical fact 로 보존한다.

**D1 승인** (task-0124) — 표시용 recent-5 와 검증용 evidence 를 분리하는 방향.
window 숫자 · TTL · schema · validator 는 미결정 상태로 남았고, 이 task 가 그것을
근거와 함께 제시한다.

## 2. 조사 결과 — 설계를 바꾼 핵심 사실

### 2.1 현재 검증은 존재 확인이 아니다

`READ_ONLY_GIT_COMMANDS` (`run_web_app.py`) 는 **7 개 명령만** 허용한다.

```text
rev-parse --show-toplevel / --abbrev-ref HEAD / HEAD
status --short  /  status --short --untracked-files=all
log --oneline -n 10
log -n 5 --format=<sep>%H<sep>%s --name-only
```

**임의 commit 의 존재를 확인할 수 있는 명령이 하나도 없다.** `cat-file` 도
`merge-base` 도 `rev-list` 도 없다. 그래서 현재 package hash 검증은

```python
if commit_hash not in recent_set:      # recent_set = {live_head} ∪ recent-5
    conflicts.append(f"Checkpoint package {package_id} commit is absent from Git evidence")
```

**"Git evidence 에서 없어졌다"고 말하지만 실제로 하는 일은 "최근 5 개 안에 없다"** 다.
결과적으로 다음 두 경우가 **구분되지 않고 같은 메시지**를 낸다.

| 경우 | 현재 판정 | 실제 의미 |
| --- | --- | --- |
| 실재하는 2026-07-23 commit 이 창 밖으로 밀림 | absent | **정상적인 historical fact** |
| 존재한 적 없는 40-hex 문자열 | absent | **조작 또는 오류** |

이것이 D1 의 진짜 근거다. 창 크기 문제가 아니라 **검증 질문 자체가 틀렸다.**

### 2.2 실측 — historical commit 은 전부 실재하고 ancestor 다

```text
325fe500a0cf  exists  ancestor-of-HEAD   (HEAD 로부터 122 커밋 뒤)
a11c95365020  exists  ancestor-of-HEAD   (121 커밋 뒤)
7d4394eed584  exists  ancestor-of-HEAD   (118 커밋 뒤)   ← verified_implementation_head
```

전체 596 커밋. 세 hash 모두 실재하며 현재 branch 조상이다. 즉 **historical
evidence 는 지금도 참이고, 시스템만 그것을 확인할 방법이 없다.**

### 2.3 conflict 9 개 중 문제는 2 개다

Console 경로(`build_manager_report_from_checkpoint_sources`, worker_reports 는 비어
있음)에서 실제로 평가되는 조건이다.

| # | 조건 | 성격 | 현재 정확한가 |
| --- | --- | --- | --- |
| 1 | `source != docs/master-plan.md` | 문서 무결성 | 정확 |
| 2 | `known_protected_untracked_file != jarvis.bat` | 문서 무결성 | 정확 |
| 3 | `snapshot_branch != live_branch` | **current-state** | 정확 |
| 4 | **`verified_head` 가 창 밖** | **historical** | **부정확 — D1 대상** |
| 5 | live status 에 `?? jarvis.bat` 없음 | **current-state** | 정확 |
| 6 | `_protected_path_changed` | **current-state** | 정확 |
| 7 | `package_id.startswith(milestone_id)` 실패 | 결합 | 아래 §7 |
| 8 | package `result_type == "blocked"` | historical fact | 정확 |
| 9 | **package `commit_hash` 가 창 밖** | **historical** | **부정확 — D1 대상** |

**9 개 중 2 개(#4, #9)만 잘못됐다.** 나머지 7 개는 이미 올바른 질문을 하고 있다.
D1 의 범위가 매우 좁다는 뜻이다.

여기에 `run_web_app.py` 가 별도로 계산하는 base attention 3 종이 더 있다.

| 조건 | 성격 |
| --- | --- |
| `live_branch != expected_branch` | current-state |
| `not head_matches_latest_commit` | current-state |
| recent commit 에 `jarvis.bat` 포함 | **display 목록에서 파생** |

세 번째가 recent-5 의 **세 번째 소비자**다. 이것은 "최근에 무슨 일이 있었나"를
묻는 것이므로 display 계약에 종속되는 것이 **의미상 옳다.** D1 대상이 아니다.

### 2.4 "conflict ⇒ blocked" 는 두 곳에서 강제된다

| 위치 | 내용 |
| --- | --- |
| `manager_reporting_data.py` | `if conflicts: status = "blocked"` — 선언된 `milestone_complete` 를 덮어쓴다 |
| `run_web_app.py` `reconcile_project_control_reporting_state` | `source_conflicts` 가 비어 있지 않은데 `blocked`/`decision_required` 가 아니면 **`RegistryError`** |

**설계 제약이 여기서 나온다.** conflict 의 결과를 약화시키는 방향은 불가능하다 —
reconciler 가 즉시 500 을 낸다. D1 은 **참인 evidence 가 애초에 conflict 를 만들지
않게** 해야 하며, conflict 를 만든 뒤 무시하는 방식이어서는 안 된다. 이것은
fail-closed 를 보존하는 방향이기도 하다.

## 3. 세 관심사의 정의

현재 하나의 `git log -n 5` 결과가 세 가지 목적을 동시에 지고 있다.

```text
                     git log -n 5
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
     UI 표시          verified_head      package hash
   (의미상 옳음)        (틀림)             (틀림)
```

D1 이후 분리해야 할 세 계약이다.

| 계약 | 질문 | 시간에 따라 변하는가 | 현재 위치 |
| --- | --- | --- | --- |
| **Display Recent Commits** | 최근에 무엇이 일어났나 | **변한다** — 그것이 목적 | `recent_milestone_evidence.py`, `MAX_COMMITS = 5` |
| **Historical Evidence** | 이 milestone/package 가 **당시** 어느 commit 에서 검증됐나 | **변하지 않는다** — 과거는 고정 | master-plan §4, §2 `verified_implementation_head` |
| **Current-State Evidence** | **지금** repository 가 정상인가 | 변한다 | live HEAD/branch/status |

**Historical Evidence 는 시간이 지나도 참이다.** 이것이 D1 의 중심 명제이며
Decision A 의 코드적 표현이다.

## 4. Q1 — Historical Evidence 의 source of truth

| 후보 | 역할 | authoritative 인가 |
| --- | --- | --- |
| **master-plan §4 표** | package_id → commit_hash 주장 | **주장의 source** — 무엇을 검증할지 선언 |
| **git history** | 그 commit 이 실재하고 이 branch 조상인지 | **사실의 source** — 주장의 진위 |
| task records | 서술적 provenance | 보조. 기계 검증 대상 아님 |

**둘은 역할이 다르며 둘 다 필요하다.** §4 는 "무엇을 주장하는가", git 은 "그
주장이 참인가". 현재 구현은 후자를 확인할 수단이 없어 전자를 recency 로 대신
검사하고 있다.

### 현재 구현이 보장하는 것과 보장하지 않는 것

| 항목 | 현재 |
| --- | --- |
| hash 형식이 40-hex 소문자인가 | **보장** (`_required_hash`) |
| package_id 형식과 중복 없음 | **보장** |
| `result_type` 이 허용 enum 인가 | **보장** |
| **그 commit 이 실재하는가** | **보장하지 않음** |
| **그 commit 이 이 branch 조상인가** | **보장하지 않음** |
| 그 commit 의 내용/변경 파일 | **보장하지 않음** |
| 당시 protected-path 상태 | **보장하지 않음** |
| 당시 validation 결과 | **보장하지 않음** |
| 최근 5 개 안에 있는가 | 보장 — **그러나 이것은 historical 질문이 아니다** |

설계 판단: **존재와 조상 여부까지만 검증한다.** 당시 내용·validation 결과의
재검증은 별개 관심사(D4 attestation 영역)이며 이번 범위가 아니다. 과다 설계를
피한다.

## 5. Q2 — Current-State Evidence 의 정의

"최근 commit 이 있는가"를 current-state health 와 동일시하지 않는다. 현재 상태가
정상인지 판단하는 데 실제로 필요한 것은 다음이며, **대부분 이미 구현돼 있다.**

| evidence | 질문 | 현재 상태 |
| --- | --- | --- |
| live branch == 선언 branch | 다른 branch 에서 보고하고 있지 않은가 | **이미 있음** (#3) |
| live HEAD | 관찰 시점 고정 | **이미 있음** |
| `head_matches_latest_commit` | 로그와 HEAD 가 어긋나지 않는가 | **이미 있음** (base) |
| protected untracked `jarvis.bat` 존재 | 보호 파일이 사라지지 않았는가 | **이미 있음** (#5) |
| `jarvis.bat` tracked 변경 없음 | 보호 경계가 깨지지 않았는가 | **이미 있음** (#6) |
| 최근 commit 이 보호 경로를 건드림 | 최근에 위험한 일이 있었나 | **이미 있음** (base, display 파생 — 의미상 옳음) |
| current milestone 진행 상태 | 선언된 status 와 실제가 맞는가 | 부분 — §7 참조 |

**결론: current-state evidence 는 이미 충분하다.** D1 은 여기에 무언가를 더하는
작업이 아니라, **historical 질문이 current-state 판정에 섞여 들어온 것을 빼내는**
작업이다.

## 6. Q3 — `MAX_COMMITS = 5` 가 실제로 정의하는 계약

| | 계약 | 문서에 명시됐는가 |
| --- | --- | --- |
| **A** | **UI display contract** | **명시됨.** `project-control-recent-milestone-evidence-v0.1.md` 가 five commits 를 256KB · subject 160 자 · 20 파일과 같은 bound 목록에 나열한다. `jarvis-console-v0.1-checkpoint.md` 는 "owner 가 최근 5 개 커밋을 본다"고 적는다 |
| **B** | **validation evidence contract** | **명시되지 않음.** 두 설계문서가 Attention 유발 조건으로 적은 것은 **HEAD 불일치와 protected `jarvis.bat`** 뿐이다. verified-HEAD absent 나 package-commit absent 는 어느 문서에도 없다 |
| **C** | **historical evidence retention contract** | **존재하지 않음.** 어떤 문서도 historical evidence 의 보존 기간을 정의하지 않는다 |

**A 는 설계된 계약이고, B 는 `run_web_app.py` 배선에서 생긴 우연한 결합이며,
C 는 아예 없다.** 이 정책을 도입·고정한 task record 도 0 건이다(v0.1D/v0.1E 시기).

## 7. Proposed D1 architecture

```text
현재
    git log -n 5 ──┬── UI 표시
                   ├── verified_head 검증      ← 틀린 질문
                   └── package hash 검증       ← 틀린 질문

D1 이후
    git log -n 5 ────── UI 표시 + 최근 보호경로 확인   (변경 없음)

    git ancestry ──┬── verified_head 검증
                   └── package hash 검증
                        "실재하며 이 branch 조상인가"

    live HEAD/branch/status ── current-state 검증      (변경 없음)
```

핵심은 **검증 질문의 교체**다. `commit_hash in recent_set` 을
`commit_hash 가 실재하고 HEAD 의 조상인가` 로 바꾼다.

이 질문은 **시간이 지나도 답이 바뀌지 않는다.** history 는 자라기만 하므로 한 번
조상이면 영원히 조상이다. 그래서 **window 숫자도 TTL 도 필요 없어진다.**

## 8. Validation window 후보 비교

**5 라는 숫자를 답으로 가정하지 않았고, 어떤 숫자도 채택하지 않았다.**

### Option A — live HEAD 자체를 anchor 로

`recent_set` 을 `{live_head}` 로 축소.

| 축 | 평가 |
| --- | --- |
| 정확성 | **나쁨** — milestone commit 이 HEAD 인 순간만 통과. 1 커밋 뒤 다시 blocked |
| historical 보존 | 해결 안 됨 |
| fail-closed | 유지 |
| schema | 0 |
| 판정 | **문제를 악화시킨다. 기각** |

### Option B — 별도 validation evidence query (더 큰 창)

검증용으로 `git log -n N` 을 별도 실행, N > 5.

| 축 | 평가 |
| --- | --- |
| 정확성 | 나쁨 — N 커밋 뒤 같은 문제 재발. 문제를 **미루기만** 한다 |
| historical 보존 | 해결 안 됨 |
| 위조 가능성 | 여전히 존재 여부를 확인 못 함 |
| 정책 충돌 | **handoff 의 "do not enlarge evidence windows to hide the conflict" 와 정면 충돌** |
| 판정 | **기각.** 숫자를 정해야 한다는 것 자체가 잘못된 질문의 징후다 |

### Option C — ancestry 검증 (**추천**)

historical hash 를 `git merge-base --is-ancestor <hash> HEAD` 로 검증.

| 축 | 평가 |
| --- | --- |
| 정확성 | **높음** — "이 commit 이 이 branch 역사의 일부인가"라는 정확한 질문 |
| historical 보존 | **완전** — hash 를 건드리지 않는다. 과거는 영원히 조상 |
| fail-closed | **강화됨** — 존재하지 않거나 조상이 아닌 hash 는 **거부된다.** 현재는 오래된 진짜와 조작된 가짜를 구분 못 하지만 이 안은 구분한다 |
| 운영 복잡도 | 낮음 — Owner 가 관리할 숫자가 사라진다 |
| schema 변경 | **0** — §4 표도 §2 필드도 그대로 |
| 기존 코드 영향 | 좁음 — 아래 §11 |
| 테스트 영향 | 낮음 — 기존 계약 대부분 유지 |
| 장기 유지보수 | **가장 좋음** — 시간이 지나도 재검토가 필요 없다 |
| 위조 가능성 | **낮아짐** — 40-hex 를 지어내도 통과 못 함 |
| 비용 | `--is-ancestor` 는 boolean 종료코드. 출력 없음. package 당 1 회, 현재 2~3 회 |

### Option D — current milestone commit 을 별도 evidence 로 관리

completed milestone 과 in-progress milestone 을 각각 다른 evidence 로.

| 축 | 평가 |
| --- | --- |
| 정확성 | 높지만 **C 가 이미 해결하는 문제를 다시 푼다** |
| schema 변경 | **큼** — 새 필드·표·writer 필요 |
| 판정 | C 로 충분하면 불필요. **보류** |

### 추천

**Option C.** 숫자를 정하는 대신 **숫자가 필요 없는 질문으로 바꾼다.** 이것이
"window 숫자를 임의로 정하지 않는다"는 제약을 회피가 아니라 정면으로 만족시키는
유일한 안이다. 그리고 fail-closed 를 **약화가 아니라 강화**한다.

> `--is-ancestor` 를 쓰려면 `READ_ONLY_GIT_COMMANDS` 에 항목이 추가돼야 한다.
> 현재 allowlist 는 **고정 인자 tuple 집합**이라 hash 를 인자로 받는 형태를
> 표현할 수 없다. allowlist 구조를 어떻게 확장할지는 구현 단계 결정 사항이며,
> "고정 prefix + 검증된 40-hex 인자" 형태를 강하게 권한다. 임의 인자 전달은
> 허용하지 않는다.

## 9. TTL 판단 — **불필요하다**

두 개념을 분리한다.

| 개념 | 시간에 따라 | TTL 이 말이 되는가 |
| --- | --- | --- |
| commit recency | 반드시 변한다 | 해당 없음 — 그 자체가 recency |
| **historical evidence validity** | **변하지 않는다** | **아니다** |

`325fe500` 이 `manager-reporting-v0.1a` 를 검증한 commit 이라는 사실은 1 년 뒤에도
참이다. **오래됐다고 거짓이 되지 않는다.** historical evidence 에 TTL 을 두는 것은
"과거가 만료된다"고 말하는 것과 같다.

Option C 를 채택하면 TTL 을 둘 자리가 아예 없다 — ancestry 는 시간 함수가 아니다.

**단, "review/refresh signal" 은 TTL 과 구분된다.** "이 milestone 은 오래됐으니
한 번 돌아보라"는 알림이 유용할 수는 있다. 그것은
**blocked 를 만들지 않는 정보성 신호**여야 하고, historical evidence 를 invalid
로 만들어서는 안 된다. 이 신호가 필요한지는 **D4 attestation 영역이며 이번 범위가
아니다.** 이번 설계는 TTL 을 도입하지 않는다.

## 10. Schema 변경 검토 — **0 을 목표로 한다**

Option C 는 **기존 schema 를 그대로 쓴다.**

| 계약 | 변경 |
| --- | --- |
| master-plan §4 표 (`Work package`/`Result type`/`Summary`/`Commit`) | **없음** |
| `package_id` · `commit_hash` 형식 규칙 | **없음** |
| §2 `verified_implementation_head` | **없음** |
| `manager_reporting_status` enum | **없음** |
| `MASTER_PLAN_FIELDS` 19 개 | **없음** |
| `MASTER_PLAN_WORKSTREAMS` 6 행 | **없음** |
| `MAX_COMMITS = 5` | **없음** (display 계약으로 유지) |

`recent_commit_hashes` 는 adapter 입력 계약으로 남지만 **historical 판정에는 쓰지
않는다.** adapter 가 ancestry 결과를 어떤 형태로 받을지 — 새 입력 필드인지
callable 인지 — 는 구현 결정 사항이다. 어느 쪽이든 **master-plan 문서 schema 는
바뀌지 않는다.**

**새 field 를 도입하지 않는 것이 이 설계의 강점이다.** migration 도
backward compatibility 문제도 발생하지 않는다. 기존 master-plan 문서는 수정 없이
그대로 통과한다.

## 11. Implementation scope (예상, 구현하지 않음)

| 파일 | 변경 성격 |
| --- | --- |
| `apps/jarvis-console/run_web_app.py` | allowlist 확장(고정 prefix + 검증된 hash 인자), ancestry 조회 헬퍼, adapter 배선에서 historical 판정 입력 교체 |
| `apps/hermes-manager-pilot/.../manager_reporting_data.py` | #4 · #9 의 판정을 recency 에서 ancestry 결과로 교체. **worker report 경로(#`commit_hash not in recent_set`)도 같은 결합을 갖고 있어 함께 다뤄야 한다** |
| `apps/jarvis-console/run_smoke_tests.py` | §13 테스트 계약 추가 |
| docs | 계약 분리 반영 |

**`MAX_COMMITS` 는 건드리지 않는다.** display 계약은 그대로다.

## 12. D1 과 D2/D3/D4 의 경계

| | 내용 | D1 과의 관계 | 근거 |
| --- | --- | --- | --- |
| **D2** | `milestone_complete` 를 current-state gate 에서 면제 | **D1 만으로 해결 가능 — 불필요해진다** | #4·#9 가 참인 evidence 에 conflict 를 만들지 않게 되면, `milestone_complete` 선언이 덮어써질 이유가 사라진다. 면제 규칙을 따로 만들 필요가 없고, 만들면 오히려 fail-closed 에 구멍이 생긴다 |
| **D3** | package 표 최소 1 행 제약 완화 | **D1 만으로 해결 가능 — 단 조건부** | 최소 1 행이 문제였던 이유는 "그 행이 반드시 창 안이어야" 했기 때문이다. ancestry 로 바꾸면 오래된 행을 그대로 두는 것이 정상이 되므로 완화가 필요 없다. **다만 "milestone 사이" 상태를 표현하고 싶다면 그때는 D3 가 독립 주제로 남는다** — 이번 설계는 그 요구를 만들지 않는다 |
| **D4** | attestation / refresh | **D1 으로는 해결 불가능 — 그러나 지금 필요하지 않다** | ancestry 는 "그 commit 이 역사에 있다"만 답한다. "당시 validation 이 실제로 통과했다"는 별개 주장이며 서명·attestation 영역이다. §9 의 review signal 도 여기 속한다. **필요해지면 별도 task** |

**D2/D3/D4 중 어느 것도 이번에 승인하거나 채택하지 않는다.** 위는 관계 판단이다.

## 13. 무결성 / security 검토

| 위험 | 이 설계에서 |
| --- | --- |
| historical hash rewrite | **발생하지 않는다.** 오히려 rewrite 할 이유가 사라진다 — 오래된 hash 가 정상 통과하므로 |
| false freshness | **발생하지 않는다.** 신선하다고 주장하지 않고 "역사에 있다"고만 주장한다 |
| moving evidence | **발생하지 않는다.** §4 표는 고정 |
| silent validation bypass | **발생하지 않는다.** conflict 를 무시하는 것이 아니라 참인 evidence 가 conflict 를 만들지 않게 한다. `reconcile_project_control_reporting_state` 의 "conflict ⇒ blocked" 불변식은 그대로 유지된다 |
| evidence 위조 | **현재보다 어려워진다.** 지금은 40-hex 형식만 맞으면 "최근이 아님"으로만 처리되지만, 이후에는 실재하지 않거나 조상이 아닌 hash 가 **명시적으로 거부**된다 |
| window 확대로 충돌 은폐 | **하지 않는다.** window 를 키우지 않고 display 용으로 유지한다. handoff 의 *"do not rewrite hashes or enlarge evidence windows to hide the conflict"* 문구는 유지된다 |
| fail-closed 약화 | **없다.** 판정 실패·명령 실패·형식 위반은 전부 기존처럼 fail-closed 여야 한다. 특히 **ancestry 조회 자체가 실패하면 통과가 아니라 conflict** 로 처리해야 한다 |

`fail-closed 를 약화시켜 정상으로 보이게 만드는 설계는 거부한다`는 원칙을 이
설계는 위반하지 않는다. **틀린 질문을 옳은 질문으로 바꾸는 것이지 질문을 없애는
것이 아니다.**

## 14. 테스트 계약 (구현 단계에서 작성, 이번에 수정하지 않음)

| Case | 상황 | 기대 |
| --- | --- | --- |
| **1** | 최근 milestone — historical valid, current valid | normal (conflict 0) |
| **2** | historical evidence 가 recent-5 밖 (실재 + 조상) | **conflict 0.** 나이만으로 blocked 되지 않는다 |
| **3** | live branch 가 선언 branch 와 다름 | **blocked** |
| **4** | protected-path 위반 (`jarvis.bat` 부재 또는 tracked 변경) | **blocked** |
| **5** | historical commit 이 실재하지 않음 | **blocked** — fail-closed |
| **6** | 조상이 아닌 실재 commit / 형식 위반 / 조작된 hash | **blocked** — fail-closed |
| **7** | display recent-5 가 바뀌어도 historical 판정 불변 | **historical 결과가 display 변화에 영향받지 않는다** |
| **8** | ancestry 조회 자체가 실패 | **blocked** — 통과로 처리하지 않는다 |
| **9** | `milestone_complete` + historical 오래됨 + current 정상 | `milestone_complete` 유지 (D2 없이) |

### 현재 smoke 의 한계 — 반드시 함께 고칠 것

`run_smoke_tests.py` 의 Project Control 검증은 **기대값을 live 상태에서
재계산**한다.

```python
expected_missing_references = []
if not any(commit.startswith(verified_head) for commit in available_hashes):
    expected_missing_references.append(...)
```

그래서 카드가 `attention` 이든 `observed` 이든 **양쪽 다 통과한다.** 계약이
고정돼 있지 않다는 뜻이며, 이 때문에 현재 상태가 결함인지 정상인지 테스트가
말해주지 않는다. 구현 단계에서 **Case 2 와 Case 7 은 고정 fixture 로** 작성해야
한다. live 재계산 방식으로는 이 두 케이스를 잡을 수 없다.

## 15. Implementation 단계에서 결정할 항목

| 항목 | 비고 |
| --- | --- |
| allowlist 확장 형태 | 고정 prefix + 검증된 40-hex 인자 권장. 임의 인자 금지 |
| ancestry 결과를 adapter 에 넘기는 형태 | 입력 필드 vs callable — adapter 의 "no Git/filesystem access" 경계를 지켜야 하므로 **조회는 Console 이 하고 결과만 전달**하는 쪽을 권장 |
| worker report 경로의 동일 결합 처리 | 현재 미사용이나 같은 결함을 갖는다 |
| 조회 실패 · timeout 처리 | fail-closed |
| 캐싱 여부 | package 2~3 개면 불필요할 가능성 |

## 16. Owner approval required

구현 착수 전 다음을 승인받아야 한다.

1. **Option C (ancestry 검증) 채택** — B(window 확대)와 D(별도 evidence 관리)를 기각하는 것 포함
2. **TTL 을 도입하지 않음**
3. **schema 변경 0 방침** — 새 field 없이 진행
4. **`READ_ONLY_GIT_COMMANDS` 확장** — 현재 고정 tuple allowlist 에 인자를 받는 명령을 처음으로 추가하게 되므로, 안전 경계 변경으로서 별도 승인이 필요하다
5. **D2/D3/D4 를 이번 구현에 포함하지 않음**

## 17. Acceptance criteria

이 설계 task 는 다음이 모두 성립하면 완료다.

1. Owner Decision A/B 와 D1 승인이 참조된다.
2. 세 계약(display · historical · current-state)이 코드 근거와 함께 정의된다.
3. validation window 후보가 비교되고 추천안에 근거가 있으며, **임의 숫자를
   채택하지 않는다.**
4. TTL 필요 여부가 근거와 함께 판단된다.
5. schema 변경 범위가 구체적으로 제시된다.
6. D2/D3/D4 각각이 D1 과 어떤 관계인지 판단된다.
7. 테스트 계약 9 종과 현재 smoke 의 한계가 기록된다.
8. Owner 승인 항목이 구체적으로 열거된다.
9. **production · test 변경이 0 건이다.**
10. historical hash 와 `MAX_COMMITS` 가 변경되지 않는다.
11. 기존 smoke suite 가 통과한다.

## 18. 후속

**이 task 는 구현을 포함하지 않는다.** Owner 가 §16 을 승인하면 별도
implementation task 가 필요하다.

승인 전까지 Project Control 카드가 `attention`, Manager/Director 가 `blocked`
인 것은 현재 구조의 정상 귀결이며, 이를 감추기 위해 hash 나 window 를 건드리지
않는다.
