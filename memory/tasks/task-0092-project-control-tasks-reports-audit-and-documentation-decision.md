# task-0092-project-control-tasks-reports-audit-and-documentation-decision

- id: `task-0092-project-control-tasks-reports-audit-and-documentation-decision`
- title: `Project Control / Tasks-Reports 감사와 문서 결정 기록`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-08 04:05 UTC`
- updated_at: `2026-09-08 04:05 UTC`
- summary: `task-0091 read-only 감사와 그 결과로 수행한 문서 통합(3ed4d68)을 사후 기록한다. Project Control 은 registry skill 이 아니라 tasks_reports 탭의 UI 라벨이며, 동시에 project_control 이라는 runtime payload 로 실재해 실패 시 /api/overview 전체가 500 이 되는 load-bearing 구조다. 원인은 7689484 가 탭 라벨만 rename 하고 tab id 와 registry identity 를 유지한 것이고, b4d9b12 가 그 사실을 모른 채 registry 이름 절을 추가해 README 가 한 surface 를 두 절로 기술하게 됐다. 3ed4d68 은 두 절을 registry 이름 하나로 통합하고 탭 라벨을 본문에 명시했다. runtime 은 의도적으로 바꾸지 않았다.`
- source_command: `task-0091 감사 및 3ed4d68 문서 통합의 canonical 기록 지시`

## Scope

**이미 완료된 두 작업을 사후 기록하는 문서 작업이다.**
새로운 구현이나 추가 정리를 하지 않았고, 감사 결과를 다시 구현하지도 않았다.

기록 대상:

1. `task-0091` READ-ONLY audit — Project Control 의 정체 판별
2. 그 결과로 수행한 문서 통합 커밋 `3ed4d68`

`task-0091` 은 read-only 규칙에 따라 파일을 만들지 않았으므로 별도 record 가 없다.
이 기록이 그 감사 결과를 함께 담는다.

## Baseline

| 항목 | 값 |
| --- | --- |
| audit 기준선 | `eb1d346` |
| 문서 통합 커밋 | **`3ed4d68`** — `docs(console): merge Project Control into the Tasks / Reports section` |
| 이 기록 작성 시점 HEAD | `3ed4d68` = `origin/main` |

## Audit Verdict — LEGACY / MIXED

`Project Control` 은 **registry skill 이 아니고, dead documentation 도 아니다.**
두 가지가 한 이름에 겹쳐 있었다.

- **registry identity 는 `tasks_reports` 다.** `Project Control` 이라는 registry
  entry 는 존재하지 않는다. `skills.json` 전체에 `project` 문자열이 0건이다.
- **`Project Control` 은 실제 browser tab label 이다.**
  탭 id 는 `tasks`, 컨테이너는 `tasksDetails` / `tasksTitle` / `tasksDescription` 로
  기존 tasks surface 를 그대로 쓴다.
- **`project_control` 은 runtime payload/component 로 실재한다.**
  `/api/overview` 최상위 키이며 `project_control_payload()` 가 만든다.
- **Project Control 과 Actionable Task View 는 같은 overview 응답과 같은
  `tasksDetails` surface 를 공유한다.** 형제 컴포넌트이지 분리된 화면이 아니다.
- 따라서 **Project Control runtime 은 load-bearing 이다.** 제거 대상이 아니다.

문제의 핵심은 runtime 제거가 아니라 **registry 명칭과 UI 라벨이 달랐던
문서·명칭 정합성**이었다.

## Evidence

### Registry

| 항목 | 값 |
| --- | --- |
| `skill_id` | `tasks_reports` |
| `display_name` | `Tasks / Reports` |
| `status` | `available` |
| `Project Control` registry entry | **없음** |

### UI

browser tab label 은 **`Project Control`** 이다.
그러나 tab id 는 `tasks` 이고 기존 tasks surface / container 를 유지한다.

- `web/index.html` — `data-tab="tasks">Project Control<`, `id="tab-tasks"`,
  `id="tasksDetails"`, `id="tasksTitle"`, `id="tasksDescription"`

### Runtime

`project_control` 은 실제 runtime 구조다.

- `run_web_app.py` — `project_control_payload()`,
  `reconcile_project_control_reporting_state()`,
  `PROJECT_CONTROL_FORBIDDEN_ACTIONS`, `PROJECT_CONTROL_VALIDATION_COMMANDS`,
  `"project_control.v0.1F"`
- `run_web_app.py` — `overview_payload()` 의 최상위 키
  `"project_control": project_control_payload(repo)`
- `web/app.js` — `renderProjectControl(data.project_control)`
- `web/app.js` — `renderActionableTaskView(data.tasks)`
- 두 렌더러가 **같은 `tasksDetails`** 에 `renderOverview()` 한 번으로 함께 쓰인다.

의존 체인: `docs/master-plan.md` → `read_master_plan_snapshot()` +
`owner_decision_data` + `owner_decision` + `recent_milestone_evidence` +
hermes `manager_reporting_data` / `director_reporting` → `project_control_payload()`.

### 실패 전파 (실측)

메모리상에서 `project_control_payload` 를 예외로 대체하고 라우트를 호출한 결과:

```
정상                      /api/overview -> 200
project_control 실패 시   /api/overview -> 500  (ok=False)
복원 후                   /api/overview -> 200
```

`/api/overview` 는 Actionable Task View 의 `tasks` 를 공급하는 유일한 경로이므로,
`project_control_payload()` 실패는 **Task lifecycle 화면까지 함께 죽인다.**

## Git history — 원인

### `7689484` (2026-07-22) `jarvis-console: add read-only project control card`

Project Control runtime/card 를 도입하면서 browser tab label 을 바꿨다.

```
- <button ... data-tab="tasks">Tasks / Reports</button>
+ <button ... data-tab="tasks">Project Control</button>
```

그러나 다음 identity 는 **유지**했다.

- tab id `tasks`
- `tasksDetails` / `tasksTitle` / `tasksDescription`
- registry `tasks_reports`

이로써 **하나의 surface 에 두 명칭이 공존**하게 됐다.

### `a170a68` (2026-07-22) `docs: record project control v0.1a milestone`

README 에 `### Project Control` 절이 추가됐다.
이 시점 README 에는 `### Tasks / Reports` 절이 없었다 — Project Control 이 그 자리였다.

### `b4d9b12` (2026-09-08) task-0090 A1

registry 정합성을 맞추려고 README 에 `### Tasks / Reports` 절을 추가했다.
이 과정에서 **이미 존재하던 동일 surface 의 `### Project Control` 절을 인지하지
못해**, README 가 한 surface 를 두 절로 기술하는 상태가 됐다.

### `3ed4d68` (2026-09-08)

두 절을 하나로 통합했다.

## Decision

**README 의 canonical section heading 은 registry 이름인 `Tasks / Reports` 로 유지한다.**

본문 앞머리에서 Project Control 이 실제 UI 탭 라벨임을 명시한다.

> Registry id `tasks_reports`, status `available`. The browser tab is labelled
> **Project Control**; both names refer to this one surface, rendered from a single
> `GET /api/overview` response.

그리고 기존 Project Control 관련 설명과 링크를 유지한다. 즉:

- 문서상 중복 절 제거
- 기존 Project Control 정보 보존
- registry identity 보존
- UI tab label 보존
- **runtime 변경 없음**

### 선택지 2 / 3 을 실행하지 않은 이유

| 선택지 | 결정 | 이유 |
| --- | --- | --- |
| 1. 문서 통합 | **실행** | runtime 영향 0, 기존 UI 유지, registry 유지, 문서 중복 제거 |
| 2. UI 라벨을 `Tasks / Reports` 로 변경 | **실행하지 않음** | `7689484` 의 기존 UI naming decision 을 되돌리는 변경이며 runtime/UI 테스트와 제품 명칭 결정이 필요하다 |
| 3. registry `display_name` 을 `Project Control` 로 변경 | **실행하지 않음** | registry contract 와 copy-drift guard, skill identity 에 영향을 주므로 별도 Owner Decision 이 필요하다 |

**task-0092 에서는 선택지 2/3 을 다시 평가하지 않았고 실행하지도 않았다.**

## `3ed4d68` 의 실제 변경 내용

- `### Project Control` 별도 heading 제거
- `### Tasks / Reports` 하나로 통합
- Task lifecycle 설명을 앞쪽에 배치
- Project Control owner card 설명을 뒤쪽에 유지
- `project-control-*.md` 관련 링크 유지
- 실제 browser tab label 이 `Project Control` 임을 본문에 명시

변경하지 않은 것: `skills.json`, runtime(`run_web_app.py`), `web/`,
`contracts/`, CSS, 테스트 코드.

변경 통계 (`git show 3ed4d68` 실측):

```
apps/jarvis-console/README.md | 39 +++++++++++++++++++++------------------
1 file changed, 21 insertions(+), 18 deletions(-)
```

## 무손실 / 정합성 검증

| 항목 | 결과 |
| --- | --- |
| registry available 4종 ↔ README available section | **1:1** |
| available registry skill 누락 | **0** |
| README 에만 존재하는 registry-like section | **0** |
| 중복 section | **0** |
| `Project Control` heading | **제거됨** |
| `Project Control` UI label | **유지됨** |
| `project_control` runtime | **유지됨** |
| project-control 설계 문서 링크 | **4건 유지** |
| README 줄 수 | **406 → 409** |

단어 multiset 비교에서 삭제된 것은 제거된 heading 토큰과 연결 문구 재작성분뿐이었다.
**기존 Project Control 정보와 링크는 보존됐다.**

## Validation

아래는 **`3ed4d68` 작업 당시 순차 실행한 검증 결과**다.
이 기록을 작성하면서 새로 실행하지 않았다.

| 검증 | 결과 |
| --- | --- |
| Console self-test | PASS |
| Console smoke + browser shell | PASS |
| KEEP route probe | 13/13 PASS |
| canonical 전수 | 79/79 PASS |
| SOP | PASS |
| bot self-check | 92/92 PASS |
| discord-intake | 102/102 PASS |
| audit-chain | 7 passed, 0 failed |
| buzz-bridge | total 37, failed 0 |
| discord-nl-intent | total 35, failed 0 |
| hermes-manager-pilot | PASS |
| research-council | PASS |
| check_no_secrets --self-test | PASS |
| node --check app.js | OK |
| git diff --check | clean |

## Architecture decision

현재 구조는 이렇다.

```
Registry identity
    tasks_reports
        |
        +-- display name: Tasks / Reports
        |
        +-- browser tab label: Project Control
                    |
                    v
             same Tasks surface
                    |
              GET /api/overview
                    |
        +-----------+-----------+
        v                       v
project_control          actionable tasks
```

따라서 **명칭이 다르다는 사실 자체를 runtime defect 로 간주하지 않는다.**

task-0092 의 결정은 다음과 같다.

> Documentation resolves the ambiguity; runtime naming is intentionally left unchanged.

## Commit history

| 순서 | commit | 내용 |
| --- | --- | --- |
| — | `b96a552` | README 문장 파손 복구 (task-0090 후속) |
| — | `eb1d346` | task-0090 record |
| 1 | (task-0091) | READ-ONLY audit — 파일 변경 0, commit 0 |
| 2 | **`3ed4d68`** | Project Control / Tasks-Reports README 통합 (1파일 +21 / -18) |
| 3 | (이 기록) | task-0092 record — 신규 파일 1개만 추가 |

참조된 과거 커밋: `7689484`(탭 rename + runtime 도입),
`a170a68`(README Project Control 절 추가), `b4d9b12`(task-0090 A1).

amend 나 rebase 는 하지 않았다.

## Out of scope

향후 별도 Owner Decision 으로 남긴다.

- UI tab label 을 `Tasks / Reports` 로 바꿀 것인지
- registry `display_name` 을 `Project Control` 로 바꿀 것인지

둘 다 제품/명칭 결정이며 task-0092 범위가 아니다.

이번 task 에서 변경하지 않은 것:

- `project_control_payload`
- `/api/overview`
- Actionable Task View
- task transition (`TODO -> DOING`, `DOING -> DONE`)
- completion evidence
- approval workflow — approval queue, approval action,
  `NEEDS_APPROVAL` transition, approval endpoint 를 추가하지 않았다
- `skills.json`, `docs/master-plan.md`, `web/`, `contracts/`, CSS, 테스트 코드
- `jarvis.bat` — 접근·수정·staging 없음

## Final state

- 이 기록 작업에서 생성한 파일: **task-0092 record 1개**
- 기존 파일 수정: **0**
- `jarvis.bat`: `??` untracked 유지
