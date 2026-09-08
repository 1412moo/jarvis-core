# task-0090-console-documentation-consistency-and-readme-repair

- id: `task-0090-console-documentation-consistency-and-readme-repair`
- title: `Console 문서 정합성(A1~A3)과 README 문장 파손 복구`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-08 03:20 UTC`
- updated_at: `2026-09-08 03:20 UTC`
- summary: `task-0087 감사가 남긴 Tier A 세 건을 닫고, 그 과정에서 발견한 README 문장 파손을 별도로 복구했다. A1 은 README 의 Available Skills 를 registry 실제 목록과 맞췄고, A2 는 master-plan 6절에서 제거된 구현과 잠긴 기능을 분리했으며, A3 는 tasks_reports.purpose 의 approval 표현을 실제 UI 그룹 라벨에 맞췄다. README 파손은 task-0075 가 대체 문장을 한 줄 아래에 넣어 Daily AI Radar 의 Purpose 문장을 갈라놓은 것으로, git show 로 원래 자리를 확인해 되돌렸고 단어는 하나도 바뀌지 않았다. 두 커밋 b4d9b12 와 b96a552 로 나뉘어 있으며 amend 나 rebase 는 없었다.`
- source_command: `task-0087 Tier A(A1~A3) 반영 및 README 파손 복구 지시`

## 성격

**이 기록은 이미 완료된 두 커밋을 사후에 기록하는 문서 작업이다.**
코드나 문서 구현을 새로 바꾸지 않았다.

## 기준선과 선행 커밋

| 항목 | 값 |
| --- | --- |
| 작업 시작 기준선 | `4dacce1` |
| A1~A3 구현 커밋 | **`b4d9b12`** — `docs(console): align skill and roadmap documentation` (4파일, +36 / -7) |
| README 복구 커밋 | **`b96a552`** — `docs(console): repair broken README skill description` (1파일, +2 / -1) |
| 현재 HEAD | `b96a552` = `origin/main` |
| 선행 맥락 | task-0087(read-only 감사, Tier A 식별) · task-0088(stale 문서 정정) · task-0089(Owner Decision 확정) |

## A1 — README ↔ skills.json 정합성

`b4d9b12` 에서 확정된 변경이다.

- **`### Tasks / Reports` 절을 README 의 Available Skills 에 추가**했다.
  task-0089 가 `status` 를 `available` 로 바꿨는데 README 에 절이 없어 생긴 불일치였다.
  절 내용은 Task lifecycle surface 의 실제 동작(read-only 발견/상세,
  Preview + 명시적 Confirm 이 필요한 Start / Complete 와 Record Completion Evidence,
  `status` / `updated_at` / `completion_evidence` 한 값만 변경)을 기술한다.
- **`Memory / Skills` 를 Available Skills 에서 제거**했다.
- 같은 문단을 **`## Memory / Skills (Historical)`** 절로 옮겨
  `###`(Available Skills 하위)에서 `##`(독립 절)로 승격했다.
  첫 문단에 "이것은 `skills.json` 의 항목이 아니며 console skill 도 아니다"를 명시했다.
- **Memory / Skills 는 현재 Console registry skill 이 아니다.**
  task-0071 이 Console 구현을 제거했고 task-0074 가 registry 항목을 제거했다.
  Jarvis-Core 의 **별도 workstream** 으로는 계속 존재하며 master-plan 5절에서 추적한다.
  task-0088 이 넣은 design/readiness 문서 링크 3건은 그대로 유지했다.
- **`Project Control` 은 이번 작업에서 수정하지 않았다.**
  README 의 Available Skills 하위에 있지만 `skills.json` 에는 없다.
  Memory / Skills 와 같은 종류의 불일치이나 지시 범위 밖이라 **별도 검토 대상으로 남겼다.**

### 정합성 결과

| 항목 | 결과 |
| --- | --- |
| registry available 4종(`Research Council`, `Daily AI Radar`, `Hermes Manager`, `Tasks / Reports`) 중 README 누락 | **0건** |
| `Memory / Skills` 가 Available Skills 안에 있는가 | **아니오** |
| 역사 절과 링크 3건 유지 | **예** |
| `settings`(status `planned`) | Available Skills 대상이 아니므로 절 없음 — 정합 |

## A2 — master-plan 6절 정합성

6절이 **제거된 Console 구현과 실제로 잠긴 기능을 한 목록에 섞어** 놓고 있었다.
두 그룹으로 분리했다.

- **구현 기반이 존재하지만 활성화되지 않은 항목**(6건) — Hermes 자동 호출,
  자동 prompt rendering/실행, 자동 stage/commit/push/PR, 외부 API·LLM·credential,
  background worker/scheduler/unattended execution, 모바일 승인/홈서버 상시 실행.
  이 그룹 뒤에 기존 재검토 규칙("별도 work package 에서만 재검토한다")을 붙였다.
- **task-0071 에서 제거된 Console 구현**(4건) — `POST /api/memory-skills/candidates`
  save endpoint, Memory / Skills UI Save 또는 Confirm, Voice Inbox auto-save,
  Saved candidates dashboard. **"잠긴 것이 아니라 존재하지 않는다"** 를 명시했다.

**Owner Decision 의 의미는 바꾸지 않았다.**
`keep locked` 판정, 재검토 규칙, 5절 workstream 행과 식별자는 모두 그대로다.
잠금을 해제하거나 workstream 을 폐기한 것이 아니라 사실관계 서술만 고쳤다.

## A3 — `tasks_reports.purpose` 문구 정합성

| 전 | 후 |
| --- | --- |
| Show task status, **approval-needed items**, reports, and checkpoints. | Show task status, reports, checkpoints, and **items needing attention**. |

### 변경 이유

task-0089 가 `short_description` 에서 approval 표현을 걷어냈는데 `purpose` 에만 남아 있었다.
Console 은 **Task lifecycle 화면**이며 **approval 화면이 아니다**(D1).

새 문구는 임의 창작이 아니라 코드에서 근거를 확인했다.

- `web/app.js` 의 Actionable Task View 그룹 라벨이 `"Needs attention"` 이다.
- `run_web_app.py` 의 `TASK_VIEW_STATUS_RULES` 에서 `NEEDS_APPROVAL` 이
  `needs_attention` 그룹에 배정되고, 다음 행동은
  "Review the summary and make the required decision **outside Jarvis Console**" 다.

즉 `NEEDS_APPROVAL` Task 가 **표시**되는 것은 사실이지만, 승인 액션이나 승인 큐를
Console 에 추가한 것은 아니다. 새 문구는 그 사실만 기술한다.

`purpose` 는 copy-drift guard 대상이라 `run_smoke_tests.py` 의 replacement 표에
항목 1건을 추가했다(+8줄). 기준선 대조와 byte 복원 구조는 그대로다.

## README 문장 파손 복구 (`b96a552`)

A1~A3 작업 중 README 314~316행에서 문장 파손을 발견했다.

```
Purpose: turn curated AI and agent technology metadata into a Jarvis improvement
Jarvis Console does not run Research Council. Use the Research Council app directly...
candidate report.
```

Daily AI Radar 의 Purpose 문장 한가운데에 Research Council 문장이 끼어 있었다.

### 원인 확인

`git show 5525605`(task-0075) 와 `git show 5525605^` 로 확인했다. 추측이 아니다.

- task-0075 는 Research Council 절 **끝의 6줄 문단**을 삭제했다
  (Evaluate Idea 를 설명하던 문단).
- 그 **대체 문장을 한 줄 아래**, Daily AI Radar 의 Purpose 두 줄 사이에 삽입했다.
- 따라서 대체 문장이 원래 있어야 할 자리는 **삭제된 문단의 자리**,
  곧 Research Council 절 끝이다.

### 복구 내용

- 문장을 Research Council 절 끝(PowerShell 블록 뒤)으로 되돌렸다.
- 파일 폭(~80자)에 맞춰 줄바꿈했다. **문구 자체는 새로 작성하지 않았다.**
- task-0075 가 남긴 연속 빈 줄 2개도 원래대로 1개가 됐다.

### 무손실 검증

이전 버전과 **단어 multiset** 을 비교했다.

```
삭제된 단어: 없음
추가된 단어: 없음
줄 수: 405 -> 406
```

139자 한 줄이 두 줄로 나뉘어 +1줄이다. 역사적 문구 삭제 0건, 문장 창작 0건.

### 범위

변경 파일은 **`apps/jarvis-console/README.md` 하나**다.
`skills.json`, `docs/master-plan.md`, Console runtime(`run_web_app.py`),
`web/`, `contracts/` 는 이 복구 작업에서 변경하지 않았다.

## 검증 결과

전 스위트를 **순차 실행**했다. 이전에 hermes 스위트가
`output mode changed repository files` 로 실패한 적이 있는데, 원인은 저장소 안
임시 fixture 를 동시에 건드리는 병렬 실행 경합이었다. 이후로는 병렬 실행하지 않는다.

`b96a552` 커밋 직전, 커밋될 작업 트리 내용 그대로 실행한 결과다.

| 검증 | 결과 |
| --- | --- |
| Console self-test | PASS |
| Console smoke + browser shell | PASS |
| KEEP route probe | 13/13 |
| canonical 전수 | 78/78 PASS |
| SOP | status=PASS |
| bot self-check | 92/92 PASS |
| discord-intake | 101/101 PASS |
| audit-chain | 7 passed, 0 failed |
| buzz-bridge | total 37, failed 0 |
| discord-nl-intent | total 35, failed 0 |
| hermes-manager-pilot | PASS (단독 실행) |
| research-council | PASS (단독 실행) |
| check_no_secrets --self-test | PASS |
| node --check app.js | OK |
| git diff --check | clean |

이 기록을 작성하면서 HEAD `b96a552` 에서 Console 관련 하위 집합을 다시 순차 실행해
동일 결과를 확인했다 — Console self-test PASS, Console smoke + browser shell PASS,
KEEP route probe 13/13, canonical 78/78 PASS, `node --check` OK,
`git diff --check` clean.

## Commit / push history

| 순서 | commit | 내용 |
| --- | --- | --- |
| 1 | `b4d9b12` | A1~A3 구현/정합성 — 4파일 +36 / -7 |
| 2 | `b96a552` | README 문장 파손 복구 — 1파일 +2 / -1 |

- `b96a552` 는 `b4d9b12` **이후의 별도 커밋**이다.
- **amend 나 rebase 는 하지 않았다.** 두 기준점 모두 그대로 유지된다.
- 현재 HEAD: `b96a552`, `origin/main` 과 일치.
- 두 커밋 모두 **push 완료** 상태다.

## 작업 범위 밖으로 남긴 사항

- **`Project Control` README ↔ registry 불일치** — 수정하지 않았다.
  README 의 Available Skills 하위에 있지만 `skills.json` 에는 없다. 별도 검토 대상.
- **Memory / Skills workstream 자체** — 수정하지 않았다.
  Jarvis-Core 의 별도 장기 workstream 으로 유지되며 master-plan 5절이 추적한다.
- **`skill_registry` DEFER 결정** — 변경하지 않았다.
- **Console 의 approval 관련** — approval queue, approval action,
  `NEEDS_APPROVAL` transition, approval 전용 endpoint 를 **추가하지 않았다.**
  `TASK_TRANSITION_ACTIONS` 는 `start`(TODO→DOING) 와 `complete`(DOING→DONE) 그대로다.
- **`jarvis.bat`** — 접근·수정·staging 하지 않았다. `??` untracked 유지.
- registry contract, `ALLOWED_STATUSES`, status CSS 클래스, `web/`,
  Research Council, Hermes, Discord, audit-chain — 모두 무변경.
