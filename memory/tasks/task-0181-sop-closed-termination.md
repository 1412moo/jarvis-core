# task-0181-sop-closed-termination

- id: `task-0181-sop-closed-termination`
- title: `SOP §8에 CLOSED 종결 문단 추가`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-10-21 13:09 UTC`
- updated_at: `2026-10-21 13:15 UTC`
- summary: `SOP §8(Fail-closed 완료 조건)에 DONE이 아닌 종결이 있다는 문단을 더한다. 수동 SOP 작업을 완료 조건 없이 끝낼 때 Owner 결정으로 Jarvis Console Close를 써서 CLOSED와 closed_reason을 남기며, CLOSED는 완료가 아니므로 Manager가 완료로 보고하지 않고, 되돌릴 수 없으며, Worker 파이프라인 task는 대상이 아니라는 내용이다. task-0180이 Owner 결정 2로 뺀 항목이며 코드와 다른 문서는 바꾸지 않는다.`
- completion_evidence: `candidate c8186c99e275ca68e5ff1c193d3b2647c3440ab3 (baseline 68c34b0, repair 1 for two minor findings). Reviewer PASS, findings 0, self_deviations 0. QA PASS 21/21 in a fresh CRLF worktree: change set is the SOP and this record, one additions-only hunk in section 8 after the DONE paths, the paragraph matches the writer (DOING to CLOSED only, manual only) and task-model 13, validator PASS with 172 negative checks, check_task_record PASS, summary quotes complete. No push.`
- source_command: `Owner 지시: SOP §8 task 등록하고 진행 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `68c34b097c4286fa12e9cb1397cf048927af8963` (등록 시점 main HEAD) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=1` (SOP §5 기본값, 사용 내역은 Repair 절) |
| 근거 | task-0180 Owner 결정 2(SOP §8 문장은 별도 task), `docs/task-model.md` §2·§13 |

## Owner 결정 (원문)

```text
[Manager 제안]
SOP §8에 "DONE이 아닌 종결(CLOSED)도 있다"는 문장을 넣는 별도 task

[Owner 답]
SOP §8 task 등록하고 진행해
```

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `docs/jarvis-multi-agent-sop-v0.1.md`(§8에 문단 하나 추가), `memory/tasks/task-0181-sop-closed-termination.md` |
| deny | `jarvis.bat`, 코드 전체, AGENTS·agent 정의·운영 규칙 문서, SOP의 §8 밖, 다른 task 기록, 보호 worktree |

## 계획

1. SOP §8의 "DONE 경로는 두 가지다" 문단 뒤에 CLOSED 종결 문단 하나를 더한다. 완료 조건과 DONE 경로, minor 수용 규칙은 바꾸지 않는다.
2. validator가 강제하는 SOP 문장이 그대로인지 확인한다(validator PASS).
3. 사전 점검 → self-review → candidate → Reviewer → QA(validator, 깨끗한 체크아웃) → Evidence·Complete(Manager, G3와 같게) → checkpoint. push는 별도 승인.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-21 13:09 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다.

## 구현

- `docs/jarvis-multi-agent-sop-v0.1.md` §8: "DONE 경로는 두 가지다" 문단 바로 뒤에 CLOSED 종결 문단 하나를 더했다. 내용은 `DOING`인 수동 SOP 작업만 Owner 결정으로 닫고, 경로는 Jarvis Console Close뿐이며, 사유는 `closed_reason`, `CLOSED`는 완료가 아니어서 Manager가 완료로 보고하지 않고, 되돌릴 수 없고, §10 Worker 파이프라인 task는 대상이 아니라는 것이다. 기존 완료 조건, DONE 경로, minor 수용 규칙의 문장은 그대로다.

## Implementer 검증 (작업 트리)

- SOP validator PASS(negative_checks 172, 강제 문장 그대로). `git diff --check` 통과. 바뀐 파일은 SOP 한 곳과 이 기록뿐이다.

## Self-review

candidate 전 1회(읽기 전용 self-reviewer). minor 3건을 candidate 전에 고쳤다: SOP 문단에 대상이 `DOING`인 수동 작업임을 적었고, A1에 승인 문구는 문장인데 문단으로 넣었다는 점과 문장별 출처(완료 보고 금지는 SOP §8 첫 문장)를 적었다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 제안]" / "SOP §8에 "DONE이 아닌 종결(CLOSED)도 있다"는 문장을 넣는 별도 task" | 제안은 "문장"이었지만 실제로는 SOP §8에 다섯 문장짜리 문단 하나를 더했다. 각 문장은 기존 기준을 가리킬 뿐이다: 대상이 `DOING`인 수동 작업이고 Owner 결정으로 닫는다는 것은 task-model 2절·5-1절, 경로가 Jarvis Console Close뿐이고 사유가 `closed_reason`이라는 것은 task-model 5-2절·13절(Close가 Preview + Confirm 흐름이라는 것은 `apps/jarvis-console/README.md` Close Task 절), Manager가 완료로 보고하지 않는다는 것은 SOP §8 첫 문장("다음 조건을 모두 만족해야 Manager가 완료를 보고할 수 있다"), 되돌릴 수 없어 새 task를 만든다는 것은 task-model 2절·13절, Worker 파이프라인 task가 대상이 아니라는 것은 task-model 5-1절(대상은 수동 task뿐)이다. 새 규칙은 없다 |
| A2 | Owner 결정 (원문) | "[Owner 답]" / "SOP §8 task 등록하고 진행해" | task를 등록하고 Console로 Start했다. §8 밖과 다른 문서는 바꾸지 않았다 |

## Repair

- candidate `b7645198e268b37c1cd3bfc8402426bd9b1e4693`: Reviewer FINDINGS, minor 2건(유효, self_deviations 0). (1) SOP 문단의 Preview + Confirm에 A1의 출처가 없었다. (2) summary가 네 문장으로 task-model 6절의 1~3문장 기준을 넘었다.
- repair 1(`repair_count=1`): A1에 Close의 Preview + Confirm 출처(`apps/jarvis-console/README.md` Close Task 절)를 더했고, summary를 세 문장으로 줄였다. SOP 문단은 바꾸지 않았다.
