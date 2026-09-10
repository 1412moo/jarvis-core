# task-0122-master-plan-console-drift-repair

- id: `task-0122-master-plan-console-drift-repair`
- title: `master-plan 과 handoff 의 Console 관련 stale 서술 정리 (T2)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-10 09:10 UTC`
- updated_at: `2026-09-10 09:10 UTC`
- summary: `task-0120 이 찾은 문서 drift 중 T2 범위만 최소 diff 로 고쳤다. master-plan 이 제거된 Console 기능 세 개를 여전히 사용자 기능으로 서술하고 있었고 recommendation 이 hermes-manager 로 남아 있었다. recommendation 을 jarvis-console 로 바꾸고 S3 S5 S6 서술을 현재 구현에 맞췄으며 Owner Dashboard 에 축소 실행과 종결된 결정 2 건을 적었다. handoff 는 task-0114 이후 바뀐 selection 설명과 이미 고쳐진 파서 결함 문단을 정정했다. status 는 스키마가 표현하지 못하므로 selection_required 로 두었고 historical hash 와 rolling window 는 건드리지 않았다. production 변경 0.`
- source_command: `task-0121 이후 Owner 가 승인한 T2 문서 정합성 수정 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`9455715`** = `origin/main` |
| 직전 작업 | task-0121 (T1 — dogfood 제거 + workstream 결정 기록) |
| 변경 파일 | `docs/master-plan.md` · `docs/chatgpt-handoff.md` + 이 기록 |
| production · test · `.gitignore` | **무변경** |

## 무엇을 고쳤나

### master-plan.md

| 항목 | 근거 | 변경 |
| --- | --- | --- |
| §2 `Owner decision recommendation` | task-0121 | `hermes-manager` → **`jarvis-console`** |
| §3 2 단계 산출물 (S3) | task-0073 | `read-only 검토 화면`이 제거됐음을 명시 |
| §5 Jarvis Console 행 (S4) | task-0073 · task-0121 | `fresh read-only work review` 제거, 현재 primary workstream 과 Preview + Confirm 쓰기 경계로 교체 |
| Owner Dashboard 첫 체감 milestone (S5) | task-0073 | 완료 후 제거됐다는 사실 추가 |
| §8 규칙 4·5 (S6) | task-0073 | 종료된 `C0C-6a/6b` 시퀀스와 다음 기본 작업 서술 정정 |
| Owner Dashboard 현재 위치 | task-0071 · 0073 · 0074 · 0075 · 0076 · 0120 · 0121 | 축소 실행 경위와 실측 0 건 확인 추가 |
| Owner Dashboard 결정 항목 | task-0094 · task-0121 | 종결된 Owner 결정 2 건 추가 |

§5 표는 **행 수·이름·순서를 바꾸지 않았다.** `MASTER_PLAN_WORKSTREAMS` 가 6 개로
고정돼 있어 한 칸이라도 어긋나면 `/api/overview` 가 500 이 된다. 셀 내용만 바꿨다.

### chatgpt-handoff.md

| 항목 | 근거 | 변경 |
| --- | --- | --- |
| Actionable Task View selection 설명 | task-0114 | "Recent Tasks discovery 를 먼저 쓴다" → 전체 후보를 검증한 뒤 우선순위 projection 에 cap 을 적용한다 |
| 표시 Task 수치 | 실측 | `Needs metadata review: 10` → `Needs attention 5 / In progress 1 / Completed 4`, metadata review 0 |
| 파서 결함 문단 | task-0096 · task-0097 | 이미 고쳐진 결함이므로 과거형으로 정정하고 전수 valid 사실을 적음 |

T1 이 넣은 dogfood 삭제 기록은 그대로 유지했다.

## 바꾸지 않은 것 — 의도적

| 대상 | 이유 |
| --- | --- |
| §2 `Owner decision status: selection_required` | `selected_workstream_id` 와 `desired_outcome` 을 이 문서에서 읽는 필드가 없어 `selected_for_proposal` 로 바꾸면 **`/api/overview` 500** (task-0120 실측). T3 대상 |
| §2 `Last verified` · `Verified implementation HEAD` | rolling window 문제와 얽혀 있어 이번 범위 밖 |
| §4 package 표 2 행과 historical hash | **historical evidence 다.** 최신 HEAD 로 교체하지 않는다 |
| §4 rolling window 판정 | 별도 read-only audit 후보 |
| §5 표 구조 · `MASTER_PLAN_WORKSTREAMS` | production 변경이라 T3 범위 |
| production 코드 · 테스트 · `.gitignore` · `task-0041` 설계문서 | 지시상 금지 |
| `README.md` | 아래 별도 항목 |

## 보고 — README 직접 충돌 1 건 (고치지 않음)

`README.md` 는 자신을 Bootstrap 단계로 기술하며 **비범위**로 다음을 적는다.

```text
## 비범위 (이번 단계에서 제외)
- Discord 봇 구현
- 웹 UI 구현
```

그런데 master-plan §5 는 `Task / Discord / Dashboard` 를 "task 생성·조회·승인·보고
기반 구현"으로, §3 4 단계는 통합 Console 을 **사용자 기능**으로 기록한다. 둘 다
실제로 구현돼 있으므로 **직접 충돌**이다.

README 개편은 T2 범위가 아니라고 지시받았으므로 고치지 않고 보고만 한다. 다만
`README.md` 가 master-plan 을 canonical 로 지목하는 진입 문서라는 점에서, 이
충돌은 별도 작은 task 로 다루는 편이 낫다.

## 검증

| 항목 | 결과 |
| --- | --- |
| `read_master_plan_snapshot()` | **정상** — RegistryError 없음 |
| §5 workstream 행 | **6 행**, 이름·순서 일치 |
| §4 package 행 | **2 행**, hash `325fe500` · `a11c9536` **무변경** |
| `verified_implementation_head` | `7d4394ee` **무변경**, `last_verified` `2026-07-23` **무변경** |
| `/api/status` · `/api/overview` · `/api/history` | **전부 200** — 500 없음 |
| owner_decision | `selection_required` / recommended **`jarvis-console`** |
| project card | `attention` 유지, attention_reasons **3 건 그대로** |
| Console self-test · smoke | **PASS** (exit=0) |
| `git diff --check` | clean |
| diff | master-plan +12 −8, handoff +3 −3 |

card 가 `attention` 으로 남는 것은 정상이다. 그 3 건은 §2·§4 의 historical hash 가
bounded git evidence 창 밖이라는 사실이고, 이번에 고치지 않기로 한 항목이다.

## 남은 것

| task | 범위 | 승인 |
| --- | --- | --- |
| **T3** | Console 이 selected 상태를 표현 — `MASTER_PLAN_FIELDS` 2 필드 추가, `owner_decision_data.py` 하드코딩 제거, 테스트 | **별도 Owner 승인 필요** |
| rolling window audit | §4 최소 1 행 강제 + `git log -n 5` 창 조합이 의도인지 확인 | read-only |
| README 정합성 | 위 충돌 1 건 | 소규모 |
