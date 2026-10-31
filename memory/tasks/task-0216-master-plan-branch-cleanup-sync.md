# task-0216-master-plan-branch-cleanup-sync

- id: `task-0216-master-plan-branch-cleanup-sync`
- title: `master-plan의 attempt branch 남은 결정 문구 동기화`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-31 17:34 UTC`
- updated_at: `2026-10-31 17:37 UTC`
- summary: `master-plan의 "현재 결정 필요" 줄과 §2 Recommended next step은 task-0209가 남긴 attempt branch 3개 삭제를 아직 남은 Owner 결정으로 적는다. task-0215에서 Owner 결정으로 지웠으므로 그 두 문장만 끝났다고 고친다. 다른 필드, 날짜 항목, 코드는 바꾸지 않고 push는 하지 않는다.`
- source_command: `Owner 지시: 다음작업 시작해 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `16a42fa4e538f42a3b15a1efde70bcf88c993eff` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문)

```text
다음작업 시작해
```

직전 Manager 보고(Owner 원문 아님)는 남은 후보를 이 순서로 보였다: "master-plan 문구 동기화: 오래된 두 문장이 아직 attempt branch가 남아 있다고 적고 있습니다." 다음이 Worker lock 위치 조사다. Manager 해석: "다음작업"은 보고에서 첫째로 보인 이 문서 동기화다.

## 조사 (baseline 기준)

- `docs/master-plan.md`에서 "attempt branch"가 나오는 줄은 세 개다.
  - 183행 task-0215 날짜 항목: history이므로 고치지 않는다.
  - 184행 "현재 결정 필요" 줄: "2026-10-29 Manager 조사 기준 남은 작은 Owner 결정은 task-0209가 남긴 main에 없는 attempt branch 3개(task-0143 `-r3`, task-0149 첫 시도와 `-r2`)의 삭제 여부다."
  - 238행 §2 `Recommended next step`: "…, task-0209가 남긴 main에 없는 attempt branch 3개를 지울지는 별도 Owner 결정 대상이다."
- 저장소의 `.md`·`.py`·`.js`·`.html`에서 `memory/tasks` 밖에 같은 표현은 이 두 줄뿐이다. Owner Dashboard "현재 다음 작업" 줄(115행)에는 branch 언급이 없다.
- §2 필드 값은 500자 상한(`MASTER_PLAN_VALUE_MAX_CHARS`)이 있다.

## 설계

1. 184행의 해당 문장을 "2026-10-29 Manager 조사가 남긴 작은 Owner 결정이던 task-0209의 main에 없는 attempt branch 3개(task-0143 `-r3`, task-0149 첫 시도와 `-r2`)는 Owner 결정으로 task-0215에서 2026-10-31에 지웠다."로 바꾼다.
2. 238행의 해당 구절을 "task-0209가 남긴 main에 없는 attempt branch 3개는 Owner 결정으로 task-0215에서 2026-10-31에 지웠다."로 바꾼다.
3. 다른 문장과 필드는 바꾸지 않는다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `docs/master-plan.md`(184행 한 문장, 238행 한 구절), 이 task 기록 |
| deny | master-plan의 다른 문장·필드·날짜 항목, 코드, 다른 task 기록, `jarvis.bat`, `.env`, push |

## 계획

1. Console Start(TODO → DOING).
2. 두 문장을 고치고 §2 값 길이, SOP validator, Console self-test·smoke, `git diff --check`를 확인한다.
3. 사전 점검 → self-review → candidate → Reviewer → QA → Evidence·Complete → checkpoint. push는 별도 지시.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다(status·updated_at 줄만 바뀜, updated_at `2026-10-31 17:34 UTC`). Console은 수정 전에 껐다.

## 구현

- `docs/master-plan.md` 184행 "현재 결정 필요" 줄: 설계 1의 문장으로 바꿨다.
- 같은 파일 238행 §2 `Recommended next step`: 설계 2의 구절로 바꿨다.
- `docs/master-plan.md`의 diff는 두 줄 바꿈(2 insertions, 2 deletions)뿐이다.

## Implementer 검증 (작업 트리)

- §2 `Recommended next step` 값은 `` ` ``·`**`을 뺀 길이 475자로 500자 상한 안이다.
- SOP validator PASS, `run_web_app.py --self-test` 통과, Console smoke PYTHONUTF8=1과 없음 모두 rc=0, `git diff --check` 통과.
- `/api/overview`의 `project_control`에 바뀐 §2 문장이 그대로 나온다.

## Self-review

staged 변경에 self-reviewer를 한 번 돌렸다(Reviewer 판정 아님). minor 한 건(구현 절의 "diff는 두 줄 바꿈" 문장에 대상 파일이 없음)이 나왔고 candidate 전에 대상 파일을 적었다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다. 오른쪽 칸에서 "Manager 해석"이라고 적은 부분은 승인 원문에 없는 내용이며, 근거가 직전 Manager 보고(Owner 원문 아님)이거나 Manager 판단이다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "다음작업 시작해" | 착수 승인. Manager 해석(직전 보고 근거): 다음작업은 보고에서 첫째로 보인 master-plan 문구 동기화이고, 범위는 그 보고가 말한 오래된 두 문장이다. 범위 표 owned의 이 task 기록은 SOP 기록으로 Manager가 넣었다 |
