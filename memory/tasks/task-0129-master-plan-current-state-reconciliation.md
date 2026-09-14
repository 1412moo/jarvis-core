# task-0129-master-plan-current-state-reconciliation

- id: `task-0129-master-plan-current-state-reconciliation`
- title: `T5 — master-plan current-state 필드를 선택된 jarvis-console 기준으로 정합화`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-14 09:41 UTC`
- updated_at: `2026-09-14 09:41 UTC`
- summary: `T4 이후 Project Control 상단에서 선택된 jarvis-console 과 옛 Buzz Phase 2 다음 단계가 나란히 보이던 문서 drift 를 정리했다. master-plan 2 절의 현재 workstream, 현재 milestone, 다음 단계, 다음 체감 milestone, 승인 note 와 Owner Dashboard 두 줄을 선택된 workstream 의 bounded package 제안과 Owner 승인 흐름으로 맞췄다. task-0038 6 절 Phase 2 통합 순서 2/4/5 는 삭제·승인·완료하지 않고 미승인 선택적 확장 보류로 적었다. Approval state required 유지. handoff stale 두 곳 정정. production 코드, API, 스키마 무변경.`
- source_command: `Owner 가 승인한 T5 구현 지시 (approval_state required 유지, §6 Phase 2 통합 순서 ②/④/⑤ 보류 표기, next package ID 무변경, handoff 두 곳만 수정)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`17d83ae`** = `origin/main` |
| 작업 전 상태 | tracked 수정 없음, untracked `jarvis.bat` 만 |
| 근거 | T5 read-only 조사 (Owner decision / next-step 충돌), T5-A 설계 검토 |

## 무엇이 문제였나

T5 조사에서 확인한 사실이다. master-plan §2 한 블록 안에 두 시기의 상태가 섞여 있었다.

| 필드 | 마지막 변경 (git blame) | 가리키던 방향 |
| --- | --- | --- |
| Owner decision status / selected / desired outcome | 2026-09-11 | `jarvis-console` 선택 |
| Owner decision recommendation | 2026-09-10 | `jarvis-console` |
| Recommended next step | 2026-09-06 | task-0038 §6 Phase 2 ②/④/⑤ 착수 승인 |
| Current workstream · Current milestone · Approval note | 2026-09-03 | Buzz Phase 2 Bridge |
| Owner Dashboard "현재 다음 작업" · "현재 결정 필요" | 2026-09-06 | Phase 2 ②/④/⑤ |

T4(task-0128) 가 선택 행을 상단 사실 표로 올리면서 `현재 선택 workstream: Jarvis Console` 과
`다음 단계: Phase 2 ②/④/⑤ 승인 시 진행` 이 같은 표에 나란히 보이게 됐다. 코드는 필드를 충실히
옮기고 있었고 원인은 문서 drift 였다.

같은 문서에 서로 다른 "②" 가 두 개 있다는 점도 혼동을 키웠다.

| 표현 | 출처 | 내용 |
| --- | --- | --- |
| task-0038 **승인 항목** ② | `reports/task-0038-gpt-team-synthesis.md` Owner 승인 목록 | Jarvis Console 축소 (이후 D1 로 task lifecycle 화면) |
| task-0038 **§6 Phase 2 통합 순서** ②/④/⑤ | `reports/task-0038-ai-agent-collaboration-platform-buzz-research.md` §6 "게이트 통과 시 통합 순서" | ② Discord intake 연결, ④ Reviewer/QA agent + worktree, ⑤ Discord 3개월 병행 |

## Owner 결정

| # | 결정 |
| --- | --- |
| 1 | `Approval state: required` 유지. `selected_for_proposal` 은 `work_package_proposal_only` 이고 구현 착수에는 package 별 Owner 승인이 필요하므로 required 자체는 사실이다. 문제는 note 가 과거 Phase 2 승인을 가리키는 것 |
| 2 | task-0038 §6 Phase 2 ②/④/⑤ 는 승인·삭제·완료 처리하지 않고 `미승인 선택적 확장 / 보류 / 현재 결정 대상 아님` 으로 정리. 표기는 `§6 Phase 2 통합 순서 ②/④/⑤` |
| 3 | Owner Dashboard 현재 작업은 선택된 `jarvis-console` 기준 |
| 4 | `Manager reporting next package ID` (`buzz-bridge-phase2-slice1-increment-v0.1`) 는 변경하지 않음 |
| 5 | handoff 는 stale 두 곳만 수정. Roadmap 2 상태 갱신은 하지 않음 |
| 6 | Owner Dashboard "현재 결정 필요" 의 Codex/agy bridge 확장 · bridge/relay supervisor · 승인자 ID 추가 는 보류 목록으로 옮기지 않음. 승인자 ID 주의 문단 보존 |

## 무엇을 바꿨나

### `docs/master-plan.md` — 7 줄 (+7 −7)

| 위치 | 변경 |
| --- | --- |
| Owner Dashboard "현재 다음 작업" | 앞에 선택된 `jarvis-console` 반복 사용 + 다음 bounded package 1 개 제안 문장 추가. ②/④/⑤ 는 "미승인 선택적 확장으로 보류한다 — 별도 Owner 의 명시적 결정 없이는 착수하지 않는다" 로 정리. ③ 제외 설명과 task-0042/0044/0052 이력 문장은 그대로 |
| Owner Dashboard "현재 결정 필요" | 중심을 "선택된 `jarvis-console` 의 다음 bounded work package 제안 검토·승인(구현 착수 전)" 으로. ②/④/⑤ 는 "보류된 선택적 확장(현재 결정 대상 아님, 재개 시 별도 Owner 결정)" 으로 분리. 나머지 세 결정 항목과 승인자 ID 주의 문단은 원문 유지 |
| §2 `Current workstream` | `jarvis-console` primary workstream 과 완료 task 로 교체. Buzz Bridge Slice 1~P2-6 은 완료 이력, ②/④/⑤ 는 보류 |
| §2 `Current milestone` | Console 축소 완료 + primary workstream 확정 + Owner 선택 표시. Buzz Phase 1 과 Phase 2 Slice 1~P2-6 은 완료 이력, ②/④/⑤ 미승인 보류. "Director Dashboard v0.1B 는 계속 보류" 보존 |
| §2 `Recommended next step` | 반복 사용 → 다음 bounded package 1 개 제안 → Owner 승인 결정. ②/④/⑤ 는 보류이며 선행조건 아님. "task-0042 가 ④ 의 선행조건인 것은 사실이지만 착수를 승인하지는 않는다" 보존 |
| §2 `Next user-visible milestone` | "축소" → "축소된 Jarvis Console 을 실제 task lifecycle 화면으로 반복 사용". 승인 항목 ② · D1 근거와 NEEDS_APPROVAL 미추가 문구 보존 |
| §2 `Approval note` | 앞에 선택 사실과 제안-승인 경계 두 문장 추가. Phase 2 문장을 보류·현재 결정 대상 아님으로 정리. SOP v0.1B, 범위 밖 목록, 인바운드 승인, director-dashboard-v0.1b 보류 문장은 그대로 |

### `docs/chatgpt-handoff.md` — 2 줄 (+2 −2)

| 위치 | 변경 |
| --- | --- |
| Technical Debt "Master Plan baseline is stale relative to live Git" | `Planned` → `Resolved`. Manager/Director `blocked` 와 "design is not implemented" 를 task-0126 이후 사실(ancestry 검증, `milestone_complete`, source conflict 없음, attention 은 `Approval state: required`)로 정정. `Last verified`·`Verified implementation HEAD` 는 historical reference 이며 blocked 원인이 아니라고 명시 |
| Quick Context 8 | "old evidence 때문에 attention" → `Approval state: required` 때문(선택된 `jarvis-console` 의 다음 bounded package 에 Owner 승인 필요), historical evidence 는 task-0126 이후 ancestry 로 검증 |

## T5-A 제안 대비 달라진 점

| 항목 | T5-A 제안 | 실제 적용 | 이유 |
| --- | --- | --- | --- |
| `Current workstream` 의 괄호 | "Task lifecycle 정확성·가시성 보강(task-0122~0128)" | "문서 정합화(task-0122/0123), historical evidence ancestry 검증(task-0126), Owner 선택 표시(task-0127/0128)" | 실제 기록 확인 결과 task-0123 은 README, task-0124/0125 는 설계이며 status `TODO`, task-0126 은 ancestry 구현이다. 범위 번호로 묶으면 사실과 다르므로 완료된 task 만 실제 내용대로 적었다 |
| `Recommended next step` | Phase 1 잔여 완료 문장 없음 | 동일 (삭제) + task-0042/④ 선행조건 문장 보존 | task-0042/0044/0052 완료 이력은 Owner Dashboard "현재 다음 작업" 에 원문 그대로 남아 있어 사실이 문서에서 사라지지 않는다 |
| `Approval note` | "…현재 결정 대상이 아니다." | "…현재 결정 대상이 아니다 — 착수 전 별도 승인이 필요하다." | 기존 문서에 있던 사실을 보존 |
| next package ID | 선택(권장) 변경 | 무변경 | Owner 결정 4 |
| "현재 결정 필요" 보류 목록 | Buzz 축 네 항목 전부 또는 ②/④/⑤ 만 | ②/④/⑤ 만 | Owner 결정 6 |

## 검증

| 검증 | 결과 |
| --- | --- |
| `read_master_plan_snapshot()` | 정상. 모든 값 ≤ 500 자 (최대 `Approval note` 412 자), §5 workstream 6 행, §4 package 2 행 (`325fe500`, `a11c9536`) |
| `approval_state` · `manager_reporting_status` · next package ID | `required` · `milestone_complete` · `buzz-bridge-phase2-slice1-increment-v0.1` (무변경) |
| `verified_implementation_head` · `last_verified` | `7d4394ee…` · `2026-07-23` (무변경) |
| in-process `/api/overview` | 200. card `attention` (이유 1 건 = 새 Approval note), Manager/Director `milestone_complete` · `decision_required` · `next_recommendation None` · source conflict 0 |
| owner_decision payload | `selected_for_proposal` / 추천·선택 `jarvis-console` / `work_package_proposal_only` / 13 키 |
| HTTP `GET /api/overview` · `GET /api/status` (실행 중인 서버) | 200 · 200 |
| `python -B apps/jarvis-console/run_web_app.py --self-test` | exit 0 |
| `python -B apps/jarvis-console/run_smoke_tests.py` | exit 0 |
| `git diff --check` | exit 0 |

브라우저 Project Control 실측:

| 확인 | 결과 |
| --- | --- |
| 현재 선택 workstream | `Jarvis Console (jarvis-console) — …` |
| 다음 단계 | 다음 bounded work package 1 개 제안 → Owner 승인 결정 문구 포함, ②/④/⑤ "미승인 선택적 확장으로 보류" 포함, 옛 "착수를 승인하면 진행" 문구 없음 |
| 현재 milestone | "미승인 보류" 포함 |
| Repository facts `Current workstream` | `jarvis-console` 로 시작, 보류 문구 포함 |
| 승인 배지 · Approval note | `Approval required` 유지 · "미승인 선택적 확장으로 보류 중이며 현재 결정 대상이 아니다" 포함 |
| Director Summary | `milestone_complete`, `Owner action: decision_required`, 다음 추천 `None.` |
| "다음 workstream 결정" 섹션 | 표시됨 (gate 통과) |
| §6 이 승인·완료됐다는 표현 | 0 건 |
| console error | 0 |

## 완료 조건

| 조건 | 상태 |
| --- | --- |
| §2 의 current-state 필드 5 개와 Owner Dashboard 두 줄이 선택된 `jarvis-console` 기준으로 읽힌다 | 충족 |
| task-0038 §6 Phase 2 통합 순서 ②/④/⑤ 가 삭제·승인·완료 없이 미승인 선택적 확장 보류로 표기된다 | 충족 |
| `Approval state: required` 와 `decision_required` 가 유지된다 | 충족 |
| parser · `/api/overview` 200 · self-test · smoke · `git diff --check` 통과 | 충족 |
| production 코드 · API · 스키마 무변경 | 충족 |

## 바꾸지 않은 것

| 대상 | 상태 |
| --- | --- |
| `apps/jarvis-console/*` (app.js, styles.css, run_web_app.py, owner_decision.py 등) · `manager_reporting_data.py` | **무변경** |
| `/api/overview` schema · `MASTER_PLAN_FIELDS` · `MASTER_PLAN_OPTIONAL_FIELDS` | **무변경** — 라벨·필드 수 동일, 값만 수정 |
| §2 `Approval state` · `Manager reporting next package ID` · `Manager reporting status` · milestone ID | **무변경** |
| §2 `Last verified` · `Verified implementation HEAD` · §4 package hash · `MAX_COMMITS` | **무변경** |
| §2 Owner decision 네 줄 · `Current reason` · `Owner outcome` · `Recent completed` | **무변경** |
| §5 workstream 6 행 | **무변경** |
| Owner Dashboard 나머지 줄 (116 "현재 사용자 체감 결과" 포함) | **무변경** |
| handoff Roadmap 2 · projection 목록 | **무변경** — Owner 결정 5 |
| T4 코드 · D2 / D3 / D4 · `README.md` | **무변경** |
| `jarvis.bat` | **접근하지 않음** |
| task-0038 Phase 2 승인·완료 표현 | **만들지 않음** |

## 남은 것

| 항목 | 상태 |
| --- | --- |
| Owner Dashboard 116 행 "현재 사용자 체감 결과" (2026-08-28, SOP 고정 서술) | 이번 범위 밖. 관찰만 기록 |
| `Recent completed` (Buzz 시기 완료 목록 중심) | 이번 범위 밖. 사실 서술이라 충돌은 아니지만 최신 Console 완료가 없다 |
| handoff Roadmap 2 "Reconcile stale Project Control reporting references" | Owner 결정 5 로 상태 미갱신 |
| `Manager reporting next package ID` 가 Buzz 시기 ID | 화면에 보이지 않음 (`milestone_complete`). Owner 결정 4 로 유지 |
| `8d21efe` 에서 사라진 Owner Decision 이외 Project Control 정적 단언 | task-0128 에 기록된 별도 task 후보 그대로 |
