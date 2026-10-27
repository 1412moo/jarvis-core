# task-0204-pilot-wording-cleanup

- id: `task-0204-pilot-wording-cleanup`
- title: `pilot 표기 5곳 정리`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-10-27 14:24 UTC`
- updated_at: `2026-10-27 14:28 UTC`
- summary: `task-0203에서 SOP 필수 절차로 고정된 두 도구의 코드에 남은 task-0197 pilot 표기 5곳(check_task_record.py 17·197·435행, commit_candidate.py 1·177행)을 지금 상태에 맞게 고친다. 주석·docstring·옵션 도움말 문구만 바꾸고 동작과 검사는 바꾸지 않는다. commit_candidate.py 177행 주석은 task-0198 이전의 C3 동작을 설명하고 있어 사실에 맞게 고친다.`
- completion_evidence: `candidate fb4c5e021001e2ea2d931e2c0f45501b8df01328 (baseline 53deb37). Reviewer PASS, findings 0, self_deviations 0. QA PASS 16/16 in a fresh worktree: 3 scope files; token comparison shows only strings and comments changed, only the baseline lines named in the record; no pilot wording left in the three scripts; --help shows the new text; three self-tests, the record preflight with --require-quotes and the validator pass.`
- source_command: `Owner 지시: pilot 표기 5곳 정리 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `53deb37bb881f06d2d6f1917e9b6ce016eb2641b` (등록 시점 main HEAD, task-0203까지 push 완료) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문)

```text
[Manager 보고: task-0203 완료 뒤]
2. 스크립트의 "pilot" 표기 5곳을 정리하는 작은 task를 할 수 있습니다. 주석과 도움말 문구만 바꾸고 동작은 바꾸지 않습니다.

[Owner 답]
푸시하고 pilot 표기 5곳 정리 task 진행해
```

## 조사 (등록 전)

- `scripts/check_task_record.py` 17행(모듈 docstring의 C6 설명 "(task-0197 pilot)"), 197행(주석 "advice only unless require_quotes (task-0197 pilot)"), 435행(`--require-quotes` 도움말 "task-0197 pilot: ...", `--help`에 보임).
- `scripts/commit_candidate.py` 1행(모듈 docstring "(task-0197 pilot)"), 177행(자체 검사 주석 "check_task_record's C3 still reads git's quoted name for such a path and refuses it (fails closed; outside this pilot's scope)"). task-0198이 C3의 스테이징 목록을 `-z`로 읽게 고쳤으므로 177행의 앞부분도 지금 동작과 맞지 않는다.
- 그 밖에 `scripts/`의 세 스크립트에 pilot 표기는 없다(`check_summary_quotes.py` 포함). SOP와 skill은 task-0203에서 고쳤다.

## 설계

1. 다섯 곳의 "pilot"을 "task-0197, task-0203부터 SOP 필수" 뜻으로 바꾼다. 옵션의 기본 동작(옵션이 없으면 C6은 참고용)은 그대로이므로 그 설명은 둔다.
2. `commit_candidate.py` 177행 주석은 task-0198 이전 동작을 사실처럼 적지 않게, 이 검사가 작업 트리 사유가 사라졌는지만 본다는 점과 한글 경로 처리는 task-0198의 `check_task_record.py`가 맡는다는 점만 적는다.
3. 코드 동작, 검사 내용, 옵션 이름은 바꾸지 않는다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `scripts/check_task_record.py`(baseline 기준 17–18·197·435행 문구만. docstring 줄바꿈을 다시 맞춰 뒤 줄 번호가 밀림), `scripts/commit_candidate.py`(baseline 기준 1·176–177행 문구만), `memory/tasks/task-0204-pilot-wording-cleanup.md` |
| deny | `jarvis.bat`, 그 밖의 코드와 줄, SOP, skill, validator, AGENTS, agent 정의, 다른 task 기록, 외부 API·credential, 봇·작업 스케줄러 |

## 계획

1. 문구 수정.
2. 검사: 두 스크립트 `--self-test` PASS, `check_task_record.py --help`의 새 도움말, AST로 문자열·주석 밖 변경 없음, 세 스크립트에 pilot 표기 0, validator PASS.
3. 사전 점검 → self-review → candidate(`commit_candidate.py --require-quotes`) → Reviewer → QA → Evidence·Complete → checkpoint → master-plan. push는 별도 지시.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-27 14:24 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다.

## 구현

- `scripts/check_task_record.py`: 모듈 docstring의 C6 설명을 "(task-0197, required by the SOP since task-0203)"로 바꾸고 그 문단 줄바꿈을 다시 맞췄다. 197행 주석은 "(task-0197; the SOP requires it since task-0203)". `--require-quotes` 도움말은 "an Owner sentence the Manager summary does not quote is a C6 violation (task-0197; required by the SOP since task-0203)".
- `scripts/commit_candidate.py`: 모듈 docstring 첫 줄을 "(task-0197; required since task-0203)"로, 자체 검사의 한글 경로 주석을 "Only the working-tree reason is checked to be gone here; how check_task_record matches such a path to the record's owned entries is its own concern (task-0198)."로 바꿨다.
- 옵션이 없으면 C6가 참고용이라는 기본 동작 설명("advice only unless require_quotes", "by default it never changes the exit code")은 사실이라 그대로 뒀다.

## Implementer 검증 (작업 트리)

- `check_task_record.py --self-test`, `commit_candidate.py --self-test` 모두 status=PASS. `check_task_record.py --help`에 새 도움말이 보인다. 세 스크립트(`check_summary_quotes.py` 포함)에 "pilot" 0건. SOP validator PASS.
- 두 파일을 baseline과 토큰 단위로 비교했다(주석·줄바꿈·들여쓰기 토큰은 빼고, 문자열 리터럴은 하나의 자리표시로 보고, 이어 붙인 문자열은 하나로 묶음). 두 파일 모두 같아 문자열·주석 밖 변경이 없다.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 보고: task-0203 완료 뒤]" | 보고의 표지. 해석할 조건이 아니다 |
| A2 | Owner 결정 (원문) | "스크립트의 "pilot" 표기 5곳을 정리하는 작은 task를 할 수 있습니다." | 조사 절의 다섯 곳(baseline 기준 `check_task_record.py` 17·197·435행, `commit_candidate.py` 1·177행. 바꾼 줄은 owned 행의 범위)을 고쳤다 |
| A3 | Owner 결정 (원문) | "주석과 도움말 문구만 바꾸고 동작은 바꾸지 않습니다." | docstring·주석·옵션 도움말 문자열만 바꿨다. 실행 코드, 검사, 옵션 이름은 그대로다(두 `--self-test` PASS). Manager 해석: docstring도 주석과 같은 설명 문구로 봤다. 177행은 pilot 표기와 함께 task-0198 이전 동작 설명도 사실에 맞게 고쳤다 |
| A4 | Owner 결정 (원문) | "[Owner 답]" | Owner 답의 표지. 해석할 조건이 아니다 |
| A5 | Owner 결정 (원문) | "푸시하고 pilot 표기 5곳 정리 task 진행해" | push(`d198722..53deb37`)는 이 task 전에 했고, 이 task로 정리했다 |

## Self-review

candidate 전 1회(사전 점검 `--require-quotes` PASS, staged 3, 위반 0, 미인용 0 뒤). 지적 2건(모두 minor)을 반영했다.

1. 계획의 "문자열·주석 밖 변경 없음" 검사 결과가 검증 절에 없었다. 토큰 비교를 실행해 결과를 적었다(AST 대신 토큰 비교: docstring과 도움말도 문자열이라 AST로는 바뀐 것으로 보이기 때문).
2. owned 행의 줄 번호가 실제로 바뀐 줄(docstring 줄바꿈 재조정으로 `check_task_record.py` 18행, 두 줄 주석인 `commit_candidate.py` 176행)을 다 덮지 못했다. baseline 기준 범위로 고치고 A2에 같은 기준을 밝혔다.

- self-review 사용량(API 환산 추정): 약 $0.28, 41초.

## Reviewer·QA 결과

- candidate `fb4c5e021001e2ea2d931e2c0f45501b8df01328`: Reviewer PASS(findings 0, self_deviations 0). Reviewer는 토큰 비교를 diff 읽기로만 확인했고, QA가 실제로 다시 실행했다.
- QA: 새 detached worktree에서 PASS 16/16(변경 파일 3개, 두 스크립트의 토큰 비교 동일, 바뀐 줄이 기록의 baseline 줄 범위 안, 세 스크립트에 pilot 0건, `--help`의 새 도움말, 세 `--self-test`, 이 기록 `--require-quotes` 사전 점검, validator, diff --check, jarvis.bat 미추적). worktree는 지웠다.
- Console Evidence 기록 후 Complete(DOING → DONE)로 닫았다. Console은 끝난 뒤 껐다. push는 하지 않았다.
- 측정(참고): Reviewer 1회 PASS, repair 0, QA 1회, self-review 1회(minor 2).
