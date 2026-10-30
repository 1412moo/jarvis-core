# task-0211-failed-next-action-wording

- id: `task-0211-failed-next-action-wording`
- title: `FAILED Next action 문구 정정`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-30 14:34 UTC`
- updated_at: `2026-10-30 14:43 UTC`
- summary: `FAILED task 카드의 Next action은 "Review the summary and decide the recovery outside Jarvis Console."인데, 카드에는 이제 실패 의미와 가능한 조치(task-0207)가 보이고 Console Close로 닫을 수 있다(task-0206). FAILED 문구 하나만 Owner가 고른 영어 문장(self-review 뒤 Owner 결정으로 /go를 뺀 문장)으로 바꾼다. 다른 상태 문구, 그룹·순위, 쓰기 흐름은 바꾸지 않고 push는 하지 않는다.`
- source_command: `Owner 지시: 다음 작업 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `b8f16b2e9575df1ebb8bdef305d09a6b6efdf79e` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문)

```text
[Manager 다음 권장 작업]
master-plan에 적은 작은 후보 두 개가 남아 있습니다. 비용이 가장 낮은 FAILED Next action 문구 정정을 먼저 하는 것을 권합니다. 비밀 정보 검사기의 자체 견본 제외는 그다음입니다.

[Owner 답]
다음작업 진행해
```

## Owner 결정 (원문, 착수 전 bounded question)

```text
[Manager 질문 1]
어느 상태의 Next action 문구를 고칠까요?

[Owner 답 1]
FAILED만 (Recommended)

[Manager 질문 2]
FAILED 문구는 어떻게 쓸까요?

[Owner 답 2]
영어, 카드 안내 가리킴 (Recommended)
selected preview:
Read the failure meaning and options on this card, then recover through Discord /go or close it here with Close.
```

선택지 설명(Manager가 질문과 함께 보인 문구, Owner 원문 아님):

- 답 1: "다음 단계 후보로 제안한 범위 그대로입니다. TODO·DOING 문구는 지금처럼 둡니다."
- 답 2: "다른 Next action과 같은 영어로 씁니다."

## Owner 결정 (원문, self-review 뒤 bounded question)

```text
[Manager 질문]
사유 코드가 없는 수동 FAILED task에서 'Discord /go로 복구' 문장이 틀리게 되는 문제를 어떻게 할까요?

[Owner 답]
문장에서 /go를 빼기 (Recommended)
selected preview:
Read the failure meaning and options on this card, then follow them or close it here with Close.
```

선택지 설명(Manager 문구, Owner 원문 아님): "FAILED 문구 한 줄 안에서 고칩니다. 카드의 가능한 조치가 경로별 방법을 이미 알려 주므로, Next action은 그것을 가리키기만 합니다."

## 조사 (등록 전)

- FAILED 문구는 `apps/jarvis-console/run_web_app.py` `TASK_VIEW_STATUS_RULES["FAILED"]`의 세 번째 값과, `apps/jarvis-console/run_smoke_tests.py`의 같은 규칙 사본(5503행 부근) 두 곳에만 있다. README·task-model에는 이 문구가 없다.
- 수동 FAILED task는 `/go`가 받지 않는다(`go_requires_worker_path`, task-0182). 카드의 `가능한 조치`는 Console이 아는 실패 사유일 때만 수동 task에 "/go는 /work로 만든 Worker 경로 task만 받는다"를 보이고, 사유가 없거나 모르는 사유이면 "task 기록과 Execution summary를 직접 확인한다."와 Console Close만 보인다(`task_failure_guidance`, task-0207). (등록 때는 이 구분을 빠뜨렸고 self-review가 찾았다.)

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `apps/jarvis-console/run_web_app.py`(FAILED 문구 한 줄), `apps/jarvis-console/run_smoke_tests.py`(규칙 사본의 같은 줄), `memory/tasks/task-0211-failed-next-action-wording.md` |
| deny | 다른 상태의 Next action, 그룹·순위, 쓰기 흐름, Discord·Worker·writer 코드, 문서, 다른 task 기록, `jarvis.bat`, push |

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다(status·updated_at 줄만 바뀜, updated_at `2026-10-30 14:35 UTC`).

## 구현

- `apps/jarvis-console/run_web_app.py`: `TASK_VIEW_STATUS_RULES["FAILED"]`의 Next action을 "Read the failure meaning and options on this card, then follow them or close it here with Close."로 바꿨다(처음에는 Owner 답 2의 미리보기 문장을 넣었고, self-review 뒤 Owner 결정으로 /go를 뺐다). 그룹 `needs_attention`과 순위 30은 그대로다.
- `apps/jarvis-console/run_smoke_tests.py`: 규칙 사본의 같은 줄을 같은 문장으로 바꿨다(사본과 실제 규칙이 같은지 보는 기존 검사가 그대로 이어진다).

## Implementer 검증 (작업 트리)

- Console smoke(PYTHONUTF8 없이·있이) 통과, SOP validator PASS, `git diff --check` 통과.
- 실제 Console(127.0.0.1:8790), 최종 문장: 임시 FAILED 기록 두 개로 확인했다. Worker 경로·`scope:no_changes`(`task-0998-temp-failed-next-action-check`)는 `가능한 조치`에 `/go` 재시도와 Close가, 수동·사유 없음(`task-0997-temp-failed-manual-check`)은 "직접 확인"과 Close가 보였고, 둘 다 Next action이 새 문장이었다. 콘솔 오류 없음. 임시 기록 둘은 지웠고 서버는 껐다. (처음 문장으로도 Worker 경로 한 건을 같은 방법으로 확인했었다.)

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다. 오른쪽 칸에서 "Manager 해석"이라고 적은 부분은 승인 원문에 없는 내용이며, 근거가 선택지 설명(Manager 문구, Owner 원문 아님)이거나 Manager 판단이다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 다음 권장 작업]" | 권장의 표지 |
| A2 | Owner 결정 (원문) | "master-plan에 적은 작은 후보 두 개가 남아 있습니다." | task-0210이 master-plan에 적은 두 후보다 |
| A3 | Owner 결정 (원문) | "비용이 가장 낮은 FAILED Next action 문구 정정을 먼저 하는 것을 권합니다." | 이 task가 그 첫 후보다 |
| A4 | Owner 결정 (원문) | "비밀 정보 검사기의 자체 견본 제외는 그다음입니다." | 이 task 범위 밖. 손대지 않았다 |
| A5 | Owner 결정 (원문) | "[Owner 답]" | 답의 표지 |
| A6 | Owner 결정 (원문) | "다음작업 진행해" | 첫 후보 착수 승인. 세부는 A10·A14의 답과, A16(처음 고른 문장)을 대체한 A20·A22의 답으로 정했다. Manager 해석: 범위 표 owned의 smoke test 한 줄(규칙 사본)과 이 task 기록은 승인 원문에 이름이 없고, 같은 규칙을 검사하고 기록하려는 Manager 판단으로 넣었다 |
| A7 | Owner 결정 (원문, 착수 전 bounded question) | "[Manager 질문 1]" | 질문의 표지 |
| A8 | Owner 결정 (원문, 착수 전 bounded question) | "어느 상태의 Next action 문구를 고칠까요?" | A10의 질문 |
| A9 | Owner 결정 (원문, 착수 전 bounded question) | "[Owner 답 1]" | 답의 표지 |
| A10 | Owner 결정 (원문, 착수 전 bounded question) | "FAILED만 (Recommended)" | FAILED 문구만 바꿨다. TODO·DOING을 포함한 다른 상태 문구는 그대로다(diff 기준) |
| A11 | Owner 결정 (원문, 착수 전 bounded question) | "[Manager 질문 2]" | 질문의 표지 |
| A12 | Owner 결정 (원문, 착수 전 bounded question) | "FAILED 문구는 어떻게 쓸까요?" | A14·A16의 질문 |
| A13 | Owner 결정 (원문, 착수 전 bounded question) | "[Owner 답 2]" | 답의 표지 |
| A14 | Owner 결정 (원문, 착수 전 bounded question) | "영어, 카드 안내 가리킴 (Recommended)" | 영어로, 카드의 실패 의미와 조치를 가리키는 문장이다 |
| A15 | Owner 결정 (원문, 착수 전 bounded question) | "selected preview:" | Owner가 고른 미리보기의 표지 |
| A16 | Owner 결정 (원문, 착수 전 bounded question) | "Read the failure meaning and options on this card, then recover through Discord /go or close it here with Close." | 처음에는 이 문장을 그대로 넣었다. self-review가 사유 코드가 없는 수동 FAILED task에서는 이 문장이 받지 않는 `/go`를 권한다는 점을 찾아, Owner가 A20에서 `/go`를 뺀 문장으로 바꿨다. 이 문장은 최종 candidate에 없다 |
| A17 | Owner 결정 (원문, self-review 뒤 bounded question) | "[Manager 질문]" | 질문의 표지 |
| A18 | Owner 결정 (원문, self-review 뒤 bounded question) | "사유 코드가 없는 수동 FAILED task에서 'Discord /go로 복구' 문장이 틀리게 되는 문제를 어떻게 할까요?" | A20의 질문. self-review major 지적에서 나왔다 |
| A19 | Owner 결정 (원문, self-review 뒤 bounded question) | "[Owner 답]" | 답의 표지 |
| A20 | Owner 결정 (원문, self-review 뒤 bounded question) | "문장에서 /go를 빼기 (Recommended)" | FAILED 문구 한 줄 안에서 `/go`를 뺐다. 범위는 A10 그대로다 |
| A21 | Owner 결정 (원문, self-review 뒤 bounded question) | "selected preview:" | Owner가 고른 미리보기의 표지 |
| A22 | Owner 결정 (원문, self-review 뒤 bounded question) | "Read the failure meaning and options on this card, then follow them or close it here with Close." | 이 문장을 한 글자도 바꾸지 않고 `run_web_app.py`와 smoke 규칙 사본에 넣었다(최종 문장) |

## Self-review

`self-reviewer`(`claude -p --agent self-reviewer --tools Read,Grep,Glob`, 첫 사전 점검 PASS 뒤 1회, API 환산 약 $0.30)의 지적 2건(major 1, minor 1)을 처리했다.

1. (major) 기록이 "카드가 수동 task에 /go 불가를 안내한다"고 적었지만 그 안내는 Console이 아는 사유일 때만 나오고, 사유가 없는 수동 FAILED task에서는 새 문장이 받지 않는 `/go`를 권함 → Owner에게 bounded question으로 물었고(위 원문 블록), Owner 결정대로 `/go`를 뺀 문장으로 바꿨다. 조사 절과 A16을 사실대로 고쳤고, 수동·사유 없음 카드까지 화면에서 확인했다.
2. (minor) A12가 답이 아닌 표지 행(A15)을 가리킴 → "A14·A16의 질문"으로 고쳤다.

수정 뒤 Console smoke(PYTHONUTF8 없이·있이) 통과. 사전 점검 결과는 아래 줄이다.
- 사전 점검(`python -B scripts/check_task_record.py memory/tasks/task-0211-failed-next-action-wording.md --baseline b8f16b2e9575df1ebb8bdef305d09a6b6efdf79e --require-quotes`): `staged_files=3`, `violations=0`, `status=PASS`. 그 뒤 `commit_candidate.py`로 candidate를 만들었다.

## Reviewer 결과 (첫 candidate)

- candidate `7e73ea1dba5ae4039c40b378d343cb11274cd07b` 첫 검토: 판정 PASS였지만 `self_deviations` 1건(허용 형식 밖의 `git -C`·리디렉션·명령 연결)이라 SOP §5에 따라 무효. 같은 candidate를 한 번 다시 검토했다(retry 1, `retry_count=1`, repair 예산 사용 없음).
- 재검토: FINDINGS, 지적 1건(minor), self_deviations 0. A6이 "세부는 A10·A14·A16의 답으로 정했다"고 적어, 대체된 첫 미리보기(A16)를 결정 근거로 들고 최종 문장을 정한 A20·A22를 빠뜨렸다.
- Repair 1(`repair_count=1`, 예산 안, Manager 결정): A6을 "A10·A14의 답과, A16을 대체한 A20·A22의 답"으로 고쳤다. 코드와 다른 행은 바꾸지 않았다. 새 candidate에 Reviewer → QA를 다시 한다.
