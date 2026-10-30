# task-0212-scanner-own-fixtures

- id: `task-0212-scanner-own-fixtures`
- title: `비밀 정보 검사기 전체 검사에서 자체 견본 빼기`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-10-30 15:30 UTC`
- updated_at: `2026-10-30 15:38 UTC`
- summary: `scripts/check_no_secrets.py 전체 검사가 자기 self-test 양성 견본 7건을 잡아 항상 FAIL이다. 견본 값을 실행 때 이어 붙이는 조각으로 적어 소스에는 비밀 모양 문자열이 없게 하고, self-test에 검사기 자신의 소스를 검사해 발견 0건인지 보는 검사를 더한다. 탐지 규칙·대상·예외는 바꾸지 않고 push는 하지 않는다.`
- completion_evidence: `candidate 2d29157605d47dae69eddf35b8a1c4c9cff80b36 (baseline 3b2f2b6): Reviewer PASS, findings 0, repair 0. QA PASS in a fresh CRLF worktree: self-test 17/0, full scan findings 0 (was 7), validator, diff --check; fixtures, patterns and scan targets equal the baseline at runtime. Seven secret shapes still detected; each fixture written back whole fails the new self-test.`
- source_command: `Owner 지시: 다음 작업 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `3b2f2b68c6b88c2a3cacb3be3414cc48d9141fd4` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |

## Owner 결정 (원문)

```text
[Manager 다음 권장 작업]
남은 작은 후보는 비밀 정보 검사기 전체 검사에서 자체 견본을 빼는 것입니다. 안전 장치 코드라 탐지가 약해지지 않았다는 검증까지 같이 합니다.

[Owner 답]
다음작업 시작해
```

## Owner 결정 (원문, 착수 전 bounded question)

```text
[Manager 질문 1]
검사기가 자기 견본을 잡지 않게 하는 방법은 무엇으로 할까요?

[Owner 답 1]
견본을 조각으로 나눠 적기 (Recommended)

[Manager 질문 2]
같은 문제가 다시 생기지 않게 self-test에 검사를 더할까요?

[Owner 답 2]
더하기 (Recommended)
```

선택지 설명(Manager가 질문과 함께 보인 문구, Owner 원문 아님):

- 답 1: "견본 값을 실행 때 이어 붙이도록 소스에 조각으로 적습니다(예: \"AKIA\" + \"ABCD...\"). 탐지 규칙과 검사 대상은 그대로고 예외 장치를 만들지 않습니다. self-test가 검사하는 값도 똑같습니다."
- 답 2: "self-test가 검사기 자신의 소스를 검사해 발견 0건인지 확인합니다. 나중에 견본을 통짜로 적으면 self-test가 실패합니다."

## 조사 (등록 전)

- 등록 시점: `python -B scripts/check_no_secrets.py --self-test`는 checks=16, failures=0, PASS. 전체 검사(`python -B scripts/check_no_secrets.py`)는 files_scanned=453, findings=7, FAIL이고 7건 모두 `scripts/check_no_secrets.py`의 `_POSITIVE_FIXTURES` 견본 값 줄(baseline 기준 236·239·243·245·246·247·248행)이다. task-0206 기록이 적은 `242-248`은 그 기록이 옮긴 범위이고 실제 줄과 다르다.
- 저장소 안에서 이 검사기를 자동으로 부르는 코드나 hook은 없다. 문서는 `--staged` 사용을 적는다(`docs/task-0052-audit-chain-approval-integration-design.md`).

- 처음 id는 `task-0212-secret-scanner-own-fixtures`였는데, Console이 이름에 `secret` 등이 든 파일을 탐색에서 빼서(`SECRET_LIKE_NAME_PARTS`) Task View에 나타나지 않았다. Start 전에 id와 파일 이름을 `task-0212-scanner-own-fixtures`로 바꿨다.

## 설계

1. `_POSITIVE_FIXTURES`의 값 일곱 개를 소스에서 패턴에 맞지 않도록 두 조각 이상으로 나눠 적는다(Python 문자열 연결). 실행 때의 값은 지금과 한 글자도 다르지 않다.
2. `_run_self_test()`에 검사 하나를 더한다: 검사기 자신의 소스(`Path(__file__)`)를 `scan_text`로 검사해 발견이 0건이어야 한다. checks는 16 → 17.
3. `PATTERNS`, `PLACEHOLDER_MARKERS`, `GENERIC_ASSIGNMENT_KEYS`, `_is_placeholder`, `_is_env_var_name_reference`, `scan_text`, 검사 대상(`TEXT_SUFFIXES`, `EXCLUDED_DIR_PARTS`, `_git_tracked_files`, `_git_staged_files`)과 CLI는 바꾸지 않는다. 예외 목록이나 억제 표시는 만들지 않는다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `scripts/check_no_secrets.py`(`_POSITIVE_FIXTURES`의 값 표기, `_run_self_test`에 검사 하나), `memory/tasks/task-0212-scanner-own-fixtures.md`. 검증용 임시 파일 하나(`scripts/_tmp_task0212_probe.py`, `scan_paths`가 저장소 기준 상대 경로를 요구해 저장소 안에 둠)는 만든 직후 지우며 stage·commit하지 않는다 |
| deny | 탐지 규칙·placeholder 판정·검사 대상·CLI, 예외·억제 장치, 다른 코드·문서·task 기록, `jarvis.bat`, push |

## 계획

1. Console Start(TODO → DOING).
2. 구현.
3. 검사: self-test PASS(17), 전체 검사 PASS, `--staged` 검사, 탐지가 약해지지 않았다는 확인(바뀐 줄이 견본 표기와 self-test뿐인지 diff, 견본 값이 이전과 같은지, 임시 파일에 넣은 비밀 모양 문자열 일곱 종류를 `scan_paths`가 모두 잡는지, 견본을 다시 통짜로 적으면 새 self-test가 실패하는지), SOP validator, `git diff --check`.
4. 사전 점검 → self-review → candidate → Reviewer → QA → Evidence·Complete → checkpoint. push는 별도 지시.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다(status·updated_at 줄만 바뀜, updated_at `2026-10-30 15:32 UTC`). Console은 구현 전에 껐다.

## 구현

- `scripts/check_no_secrets.py` `_POSITIVE_FIXTURES`: 값 일곱 개를 각 패턴이 걸리지 않는 위치에서 인접한 두 문자열 리터럴로 나눴다(`AKIA`|나머지, `sk-`|나머지, `sk-ant-`|나머지, `xoxb-`|나머지, `ghp_`|나머지, `-----BEGIN RSA PRIVATE`|` KEY-----`, `"hunt`|`er2hunter2"`). 이유를 적은 주석 네 줄을 더했다.
- `_run_self_test()`: 마지막에 검사 하나를 더했다. 검사기 자신의 소스를 `scan_text`로 검사해 발견이 있으면 줄 번호와 코드를 적어 실패한다. checks 16 → 17.
- 그 밖의 줄은 바꾸지 않았다(diff hunk는 견본 블록과 self-test 끝 두 곳).

## Implementer 검증 (작업 트리)

- `--self-test`: checks=17, failures=0, PASS. 전체 검사: files_scanned=453, findings=0, PASS(이전 findings=7). `--staged`: PASS.
- 견본 값: 바꾸기 전에 저장한 `_POSITIVE_FIXTURES` 값과 바꾼 뒤 이어 붙인 값이 일곱 개 모두 같다.
- 탐지 유지: 저장소 안 임시 파일(`scripts/_tmp_task0212_probe.py`)에 견본 값 일곱 줄을 통째로 써서 `scan_paths`로 검사하니 일곱 코드가 모두 잡혔다. 파일은 같은 실행의 `finally`에서 지웠고, 그 뒤 `exists()`가 거짓이었고 `git status --short`에도 그 경로가 없었다. 패턴·placeholder·검사 대상 코드는 diff에 없다.
- 재발 방지: 저장소 밖 임시 폴더의 검사기 사본에서 견본 일곱 개를 하나씩 다시 통짜로 적어 새 self-test를 돌렸고, 일곱 번 모두 FAIL했다(`240:aws_access_key_id`, `243:openai_style_key`, `247:anthropic_style_key`, `249:slack_token`, `250:github_token`, `251:private_key_block`, `252:generic_secret_assignment`). 사본은 지웠다.
- SOP validator PASS, `git diff --check` 통과.

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다. 오른쪽 칸에서 "Manager 해석"이라고 적은 부분은 승인 원문에 없는 내용이며, 근거가 선택지 설명(Manager 문구, Owner 원문 아님)이거나 Manager 판단이다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 다음 권장 작업]" | 권장의 표지 |
| A2 | Owner 결정 (원문) | "남은 작은 후보는 비밀 정보 검사기 전체 검사에서 자체 견본을 빼는 것입니다." | 전체 검사에서 자체 견본 7건이 더는 잡히지 않는다(findings 7 → 0). 견본을 검사 대상에서 빼는 예외는 두지 않았고, 소스 표기만 바꿔 잡힐 문자열이 없게 했다(A9) |
| A3 | Owner 결정 (원문) | "안전 장치 코드라 탐지가 약해지지 않았다는 검증까지 같이 합니다." | 패턴·placeholder·검사 대상이 diff에 없음, 견본 값이 이전과 같음, 임시 파일에 넣은 일곱 종류를 모두 잡음, 일곱 견본 각각을 통짜로 되돌리면 새 self-test가 실패함을 확인했다(Implementer 검증) |
| A4 | Owner 결정 (원문) | "[Owner 답]" | 답의 표지 |
| A5 | Owner 결정 (원문) | "다음작업 시작해" | 착수 승인. 세부는 A9·A13의 답으로 정했다. Manager 해석: 범위 표 owned의 이 task 기록은 승인 원문에 이름이 없고, SOP 기록으로 Manager가 넣었다 |
| A6 | Owner 결정 (원문, 착수 전 bounded question) | "[Manager 질문 1]" | 질문의 표지 |
| A7 | Owner 결정 (원문, 착수 전 bounded question) | "검사기가 자기 견본을 잡지 않게 하는 방법은 무엇으로 할까요?" | A9의 질문 |
| A8 | Owner 결정 (원문, 착수 전 bounded question) | "[Owner 답 1]" | 답의 표지 |
| A9 | Owner 결정 (원문, 착수 전 bounded question) | "견본을 조각으로 나눠 적기 (Recommended)" | 견본 값 일곱 개를 인접 문자열 리터럴 두 조각으로 나눠 적었다. Manager 해석(선택지 설명 근거): 탐지 규칙과 검사 대상은 그대로이고 예외 장치는 만들지 않았으며 self-test가 검사하는 값은 같다 |
| A10 | Owner 결정 (원문, 착수 전 bounded question) | "[Manager 질문 2]" | 질문의 표지 |
| A11 | Owner 결정 (원문, 착수 전 bounded question) | "같은 문제가 다시 생기지 않게 self-test에 검사를 더할까요?" | A13의 질문 |
| A12 | Owner 결정 (원문, 착수 전 bounded question) | "[Owner 답 2]" | 답의 표지 |
| A13 | Owner 결정 (원문, 착수 전 bounded question) | "더하기 (Recommended)" | self-test에 검사기 자신의 소스가 발견 0건인지 보는 검사를 더했다(checks 17). 일곱 견본 각각을 통짜로 되돌린 사본에서 실패함을 확인했다 |

## Self-review

`self-reviewer`(`claude -p --agent self-reviewer --tools Read,Grep,Glob`, 첫 사전 점검 PASS 뒤 1회, API 환산 약 $0.33)의 지적 3건(모두 minor)을 처리했다.

1. 조사 절의 줄 범위 "242~248행"이 baseline의 실제 견본 줄(236·239·243·245~248)과 다름 → 실제 줄로 고치고 task-0206 기록 범위와 다르다고 적었다.
2. 통짜 견본 실패를 AWS 하나로만 확인했는데 요약과 주석은 일곱 값 모두를 말함 → 일곱 견본 모두를 사본에서 통짜로 되돌려 일곱 번 다 FAIL함을 확인하고 Implementer 검증·A3·A13에 적었다.
3. owned 밖 저장소 경로에 검증용 임시 파일을 쓴 일이 범위 표에 없음 → 범위 표에 그 파일과 이유, 지우고 stage하지 않는다는 조건을 적고, 삭제 확인 근거를 검증 절에 적었다.

수정 뒤 사전 점검(`python -B scripts/check_task_record.py memory/tasks/task-0212-scanner-own-fixtures.md --baseline 3b2f2b68c6b88c2a3cacb3be3414cc48d9141fd4 --require-quotes`) 결과는 `status=PASS`였고, 그 뒤 `commit_candidate.py`로 candidate를 만들었다.

## Reviewer·QA 결과

- candidate `2d29157605d47dae69eddf35b8a1c4c9cff80b36`(baseline `3b2f2b6`, 단일 커밋, scope 2파일): Reviewer PASS, findings 0, self_deviations 0. retry 0, repair 0.
- QA PASS(새 detached worktree, `core.autocrlf=true`로 CRLF 체크아웃, HEAD = candidate): 변경 파일 2개, `jarvis.bat`과 임시 probe 파일 트리에 없음, `--self-test` checks=17 failures=0 PASS, 전체 검사 files_scanned=454(이 task 기록 하나 더함) findings=0 PASS, SOP validator PASS, `git diff --check` 통과, 검사 뒤 작업 트리 깨끗, QA worktree는 지웠다. 실행 비교(HEAD = candidate인 메인 checkout, baseline 소스는 저장소 밖 임시 파일로 불러옴): `_POSITIVE_FIXTURES`·`_NEGATIVE_FIXTURES`의 값, `PATTERNS`(코드·정규식·value_group), `TEXT_SUFFIXES`·`EXCLUDED_DIR_PARTS`·`PLACEHOLDER_MARKERS`·`GENERIC_ASSIGNMENT_KEYS`가 baseline과 모두 같다. 처음 비교 스크립트는 모듈을 `sys.modules`에 등록하지 않아 dataclass 처리에서 멈췄고(검사기 코드와 무관), 등록해 다시 돌렸다. Docs는 `not_required`(이 검사기를 설명하는 문서에 바꿀 문장이 없음).

## Owner 결정 (원문, Complete)

```text
[Manager 질문]
task-0212를 Console Complete로 DONE 처리할까요? (Reviewer PASS 지적 0, QA PASS, 완료 증거 기록됨)

[Owner 답]
Complete 진행 (Recommended)
```

## Complete

Record Completion Evidence(Preview 확인 뒤 Confirm, updated_at `2026-10-30 15:37 UTC`)로 completion_evidence를 남긴 뒤, Owner 결정에 따라 Console Complete Preview(DOING → DONE)를 확인하고 `Confirm Complete`로 DONE이 됐다(updated_at `2026-10-30 15:38 UTC`). Console은 끈 상태다. push는 하지 않았다.
