# task-0197-commit-guard-and-summary-table

- id: `task-0197-commit-guard-and-summary-table`
- title: `커밋 보호와 요약 표 생성 파일럿`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-25 14:06 UTC`
- updated_at: `2026-10-25 14:41 UTC`
- summary: `SOP 경량화 파일럿 A4와 A1. A4: 사전 점검이 PASS일 때만 커밋하는 scripts/commit_candidate.py를 더한다. A1: check_summary_quotes.py에 Owner 원문 문장마다 한 행인 Manager 요약 표 뼈대를 출력하는 옵션을, check_task_record.py에 미인용 문장이 있으면 위반으로 막는 선택 옵션을 더한다. 기존 기본 동작과 SOP의 필수 절차는 바꾸지 않고, 다음 수동 task 3건에 시험 적용해 효과를 잰다.`
- source_command: `Owner 지시: SOP 경량화 파일럿 A4와 A1 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `5df264578c090b39e66b30950326b46295b2be54` (등록 시점 main HEAD, task-0196까지 push 완료) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=2`, `repair_count=2` (기본 1에 Owner 결정 2로 1회 추가, 사용 내역은 Repair 절) |

## Owner 결정 (원문)

```text
[Manager 보고: SOP 경량화 후보 중]
A1: 요약이 원문 문장을 빠뜨려 Reviewer 지적과 repair가 반복됨. 점검 도구가 있는데 참고용이라 무시됨 → Manager 요약 표를 Owner 원문 문장에서 자동 생성(문장마다 한 행). Manager는 해석 칸만 채움. 사전 점검에서 미인용 0을 필수로 함
A4: 사전 점검 BLOCKED인데 커밋됨 (task-0180, 0181, 0196) → 점검 PASS일 때만 커밋하는 스크립트 하나로 고정

파일럿 1 (기록 형식, 정책 변경 없음)
- 다음 수동 task 3건에 A4(커밋 보호)와 A1(요약 자동 생성)을 시험 적용합니다.
- Reviewer 횟수, 지적 유형, repair 수를 task-0183~0196과 비교합니다.
- 단, A1을 SOP에 고정하려면 Owner 승인이 필요하고, 시험 적용 자체도 승인 뒤에 합니다.

[Owner 답]
A4랑 A1 파일럿부터 task로 진행해
```

## Owner 결정 2: repair 예산 추가와 반복 중단 규칙 (원문)

```text
[Manager 질문]
결정이 필요한 것
1. (권장) repair 예산을 1회 추가해 이 결함만 고칩니다(`-z` 처리와 한글 경로 회귀 검사). 다음 검토가 또 minor만 내면 SOP §8로 수용하고 QA로 가는 것도 함께 정해 주세요.
2. SOP §8로 이 minor를 수용하고 `ca6cf36` 그대로 QA로 갑니다. 한글 경로 한계는 완료 기록과 스크립트 설명에 적고, 고치는 일은 후속 task로 둡니다.
3. task-0197을 여기서 멈춥니다.

[Owner 답]
1번으로 진행해
```

## 설계

1. A4 `scripts/commit_candidate.py`(새 파일): `--record`, `--baseline`, `--message-file`, 선택 `--require-quotes`. 차례로 확인하고 하나라도 어긋나면 커밋하지 않고 이유를 출력한 뒤 0이 아닌 코드로 끝난다: 스테이징된 파일이 있음, 스테이징된 파일의 작업 트리가 스테이징 내용과 같음, `git diff --cached --check` 통과, `check_task_record`(같은 프로세스에서 호출) PASS(`--require-quotes`면 미인용 0도). 모두 맞으면 `git commit -F <메시지 파일>`만 실행한다. 파일을 스테이징하거나 고치지 않고, push하지 않는다.
2. A1 `scripts/check_summary_quotes.py`: `--emit-table` 옵션. 기록의 Owner 원문 블록에서 문장을 뽑아, 문장마다 한 행인 Manager 요약 표 뼈대(번호, 출처 블록 제목, 원문 인용, 해석 칸 비움)를 출력한다. 파일을 쓰지 않는다. 판정 규칙(문장 추출·인용 판정)은 기존 함수를 그대로 쓴다.
3. A1 `scripts/check_task_record.py`: 선택 옵션 `--require-quotes`. 켜면 미인용 문장을 새 위반 C6으로 막는다. 켜지 않으면 지금처럼 참고 정보다(기본 동작 그대로).
4. SOP와 운영 규칙의 필수 절차는 바꾸지 않는다. SOP의 사전 점검 문단에 파일럿 사용법과 "파일럿 3건 뒤 Owner가 고정 여부를 정함"만 적는다.
5. 파일럿 측정: 다음 수동 task 3건(이 task 제외)에서 두 도구를 쓰고, Reviewer 실행 횟수, 지적 유형(실제 결함·기록 문구), repair 수를 각 task 기록 끝에 남겨 task-0183~0196과 비교한다.

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `scripts/commit_candidate.py`(새 파일), `scripts/check_summary_quotes.py`(`--emit-table`과 그 함수·자체 검사만), `scripts/check_task_record.py`(`--require-quotes`와 C6·자체 검사만), `docs/jarvis-multi-agent-sop-v0.1.md`(사전 점검 문단의 파일럿 문장), `memory/tasks/task-0197-commit-guard-and-summary-table.md` |
| deny | `jarvis.bat`, `apps/`, 봇·Worker·팀장 코드, writer·Console, AGENTS·agent 정의, skill, validator(SOP 문장 추가로 필요하면 보고), 다른 task 기록, 외부 API·credential, 보호 worktree, 작업 스케줄러, SOP 필수 절차의 변경 |

## 계획

1. 세 스크립트 변경과 자체 검사.
2. 검사: 각 스크립트 `--self-test`(커밋 보호는 임시 저장소에서 PASS일 때만 커밋, BLOCKED·작업 트리 차이·공백 오류·스테이징 없음·미인용(옵션)일 때 거절), `--emit-table` 결과를 기록에 붙이면 미인용 0, 기존 기록들의 사전 점검 기본 결과가 바뀌지 않음, validator PASS.
3. 이 task의 candidate는 새 `commit_candidate.py --require-quotes`로 커밋하고, 요약 표는 `--emit-table`로 만든다(첫 사용).
4. 사전 점검 → self-review → candidate → Reviewer → QA → Evidence·Complete(Manager, G3와 같게) → checkpoint. push는 별도 지시.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-25 14:06 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다.

## 구현

- `scripts/commit_candidate.py`(새 파일): 설계 1. `refusals()`가 거절 이유를 모두 모으고, 없을 때만 `commit()`이 `git commit -q -F <메시지 파일>`을 실행한다. 종료 코드 0 커밋, 1 거절, 2 사용법·git 오류. `--self-test`는 임시 저장소에서 10개를 본다(점검 입력 오류는 종료 코드 2, 스테이징 없음, BLOCKED(C3), 작업 트리 차이, 공백 오류, `--require-quotes`의 미인용(C6)은 거절하고 HEAD 그대로, 옵션 없이는 같은 변경이 커밋되고 커밋 파일이 스테이징한 것과 같음, 남은 스테이징·원격 없음, 임시 폴더 정리).
- `scripts/check_summary_quotes.py`: `owner_sentences()`와 `summary_table()`을 더하고 `--emit-table` 옵션으로 표 뼈대를 출력한다. 표의 `|`는 `\|`로 바꾸고, 인용 판정의 정규화가 이를 되돌린다. 자체 검사 4개를 더했다(20개 통과).
- `scripts/check_task_record.py`: `check()`에 `require_quotes` 인자, CLI에 `--require-quotes`. 켜면 미인용 문장(또는 인용 검사 오류)을 C6 위반으로 더한다. 출력 줄의 "advice only"에 "unless --require-quotes"를 붙였다. 자체 검사 2개를 더했다(18개 통과).
- `docs/jarvis-multi-agent-sop-v0.1.md`: Manager 절의 사전 점검 문단 뒤에 파일럿 항목 하나.
- 이 기록의 Manager 요약 표는 `--emit-table` 출력에 해석 칸만 채웠다.

## Implementer 검증 (작업 트리)

- `commit_candidate.py --self-test` PASS 10/10, `check_summary_quotes.py --self-test` PASS 20/20, `check_task_record.py --self-test` PASS 18/18, SOP validator PASS.
- 기본 동작 유지: 수동 task 기록 24건(0170~0197 범위, Worker 경로 제외)을 옵션 없이 점검해 C6 위반이 0건이었다(인용 검사는 그대로 참고 정보).
- 만드는 중 실패 두 번: 패치 스크립트의 백슬래시 처리로 생성 코드의 문자열 세 곳이 깨져 직접 고쳤고, 커밋 보호 자체 검사의 첫 실행이 Windows 줄바꿈(`\r`)을 공백 오류로 보고 표본 기록의 owned 경로와 달라 실패해 검사 코드를 고쳤다(제품 코드 결함 아님).

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 보고: SOP 경량화 후보 중]" | 제목 줄. 해석할 조건이 아니다 |
| A2 | Owner 결정 (원문) | "A1: 요약이 원문 문장을 빠뜨려 Reviewer 지적과 repair가 반복됨." | A1 문제 정의. 이 task는 그 원인(요약이 원문을 빠뜨림)에 표 자동 생성으로 대응한다 |
| A3 | Owner 결정 (원문) | "점검 도구가 있는데 참고용이라 무시됨 → Manager 요약 표를 Owner 원문 문장에서 자동 생성(문장마다 한 행)." | `check_summary_quotes.py --emit-table`이 원문 문장마다 한 행을 만든다(이 표가 첫 사용) |
| A4 | Owner 결정 (원문) | "Manager는 해석 칸만 채움." | 표의 해석 칸만 비어 나온다. 이 표도 해석 칸만 채웠다 |
| A5 | Owner 결정 (원문) | "사전 점검에서 미인용 0을 필수로 함" | `check_task_record.py --require-quotes`와 `commit_candidate.py --require-quotes`로 미인용 0을 강제할 수 있다. 파일럿이라 SOP의 필수 기준(기본 종료 코드)은 바꾸지 않았다(A10) |
| A6 | Owner 결정 (원문) | "A4: 사전 점검 BLOCKED인데 커밋됨 (task-0180, 0181, 0196) → 점검 PASS일 때만 커밋하는 스크립트 하나로 고정" | `commit_candidate.py`가 점검 PASS일 때만 커밋한다. 이 task의 candidate를 이 스크립트로 커밋한다. A8의 시험 적용 문장에 따라 A4도 파일럿이며, SOP에서는 다음 수동 task 3건에 적용하고 두 도구의 고정 여부는 3건 뒤 Owner가 정한다(SOP 파일럿 항목) |
| A7 | Owner 결정 (원문) | "파일럿 1 (기록 형식, 정책 변경 없음)" | 제목 줄. 기존 기본 동작과 SOP 필수 절차를 바꾸지 않아 정책 변경이 없다 |
| A8 | Owner 결정 (원문) | "다음 수동 task 3건에 A4(커밋 보호)와 A1(요약 자동 생성)을 시험 적용합니다." | 다음 수동 task 3건(이 task 제외)에서 두 도구를 쓴다. 이 기록에만 두지 않고 SOP 파일럿 항목에 "task-0197 다음의 수동 task 3건에 적용"으로 적어 그 3건의 규칙이 되게 했다 |
| A9 | Owner 결정 (원문) | "Reviewer 횟수, 지적 유형, repair 수를 task-0183~0196과 비교합니다." | SOP 파일럿 항목에 그 3건의 기록 끝에 Reviewer 실행 횟수, 지적 유형, repair 수를 남긴다고 적었고, repair 1부터 3건 뒤 Manager가 그 값을 task-0183~0196과 비교해 보고한 다음 Owner가 고정 여부를 정한다는 단계도 SOP에 적었다 |
| A10 | Owner 결정 (원문) | "단, A1을 SOP에 고정하려면 Owner 승인이 필요하고, 시험 적용 자체도 승인 뒤에 합니다." | SOP에는 파일럿 항목만 더했고, 고정 여부는 파일럿 3건 뒤 Owner가 정한다고 적었다. 시험 적용은 이 승인으로 시작한다 |
| A11 | Owner 결정 (원문) | "[Owner 답]" | Owner 답의 표지. 해석할 조건이 아니다 |
| A12 | Owner 결정 (원문) | "A4랑 A1 파일럿부터 task로 진행해" | 이 task로 A4와 A1 파일럿을 함께 진행한다 |
| A13 | Owner 결정 2: repair 예산 추가와 반복 중단 규칙 (원문) | "[Manager 질문]" | 질문의 표지. 해석할 조건이 아니다 |
| A14 | Owner 결정 2: repair 예산 추가와 반복 중단 규칙 (원문) | "결정이 필요한 것" | 제목 줄. 해석할 조건이 아니다 |
| A15 | Owner 결정 2: repair 예산 추가와 반복 중단 규칙 (원문) | "(권장) repair 예산을 1회 추가해 이 결함만 고칩니다(`-z` 처리와 한글 경로 회귀 검사)." | repair 예산을 2로 기록하고 repair 2를 썼다. `-z` 처리와 한글·공백 경로 회귀 검사를 넣었다. 같은 종류의 C3 한계는 범위 밖이라 고치지 않고 Repair 절에 후속 후보로 적었다 |
| A16 | Owner 결정 2: repair 예산 추가와 반복 중단 규칙 (원문) | "다음 검토가 또 minor만 내면 SOP §8로 수용하고 QA로 가는 것도 함께 정해 주세요." | 다음 Reviewer 검토가 minor만 내면 SOP §8로 수용하고 같은 candidate로 QA를 진행한다. blocking·major는 수용하지 않는다 |
| A17 | Owner 결정 2: repair 예산 추가와 반복 중단 규칙 (원문) | "SOP §8로 이 minor를 수용하고 `ca6cf36` 그대로 QA로 갑니다." | 고르지 않은 선택지다 |
| A18 | Owner 결정 2: repair 예산 추가와 반복 중단 규칙 (원문) | "한글 경로 한계는 완료 기록과 스크립트 설명에 적고, 고치는 일은 후속 task로 둡니다." | 고르지 않은 선택지다. 다만 C3의 같은 한계는 이 기록에 적었다 |
| A19 | Owner 결정 2: repair 예산 추가와 반복 중단 규칙 (원문) | "task-0197을 여기서 멈춥니다." | 고르지 않은 선택지다 |
| A20 | Owner 결정 2: repair 예산 추가와 반복 중단 규칙 (원문) | "1번으로 진행해" | 1번을 따랐다 |

## Self-review

candidate 전 1회. major 1건, minor 3건을 모두 반영했다.

1. (major) 다음 3건의 적용과 측정 의무가 이 기록(History)에만 있어 다음 task의 규칙이 되지 않았다. SOP 파일럿 항목을 "task-0197 다음의 수동 task 3건에 적용"과 "기록 끝에 Reviewer 실행 횟수, 지적 유형, repair 수를 남긴다"로 고쳤다. 기본 종료 코드 기준은 그대로다.
2. A6 행이 A4도 파일럿이고 고정은 3건 뒤라는 점을 말하지 않았다. 덧붙였다.
3. `commit_candidate.py`: 작업 트리 비교의 git 실패가 "차이 없음"으로 통과할 수 있었고(fail-open), 경로를 공백으로 나눴고, `--check`가 출력 없이 실패하면 예외가 났고, 점검 입력 오류가 문서와 달리 종료 코드 1이었다. git 실패를 거절 이유로 더하고, 줄 단위로 나누고, 메시지에 예비값을 두고, 오류성 거절은 종료 코드 2로 했다. 자체 검사에 점검 입력 오류 경우를 더했다(10/10).
4. 사전 점검 결과를 적었다.

- 사전 점검(`check_task_record --require-quotes`, baseline `5df2645`): status=PASS, staged_files 5, violations 0, quote_check_unquoted 0.

## Repair

- candidate `d6dd37708985ea680b006d98547311efaa68004f`: Reviewer FINDINGS(유효, self_deviations 0), minor 1건: Owner 원문의 "Reviewer 횟수, 지적 유형, repair 수를 task-0183~0196과 비교합니다."가 SOP 파일럿 항목에 없고 이 기록(A9)에만 있어, 3건 뒤 Owner 결정 전의 비교 단계가 규칙이 되지 않는다.
- repair 1(`repair_count=1`, 기본 예산 안): SOP 파일럿 항목의 마지막 문장을 "3건 뒤 Manager가 그 측정값을 task-0183~0196과 비교해 보고하고 Owner가 두 도구의 고정 여부를 정한다"로 고쳤고 A9 해석을 맞췄다. 코드는 바꾸지 않았다. 커밋은 다시 `commit_candidate.py --require-quotes`로 했다.
- candidate `ca6cf3697566beb069fcb640bccbe1be49df74c6`(repair 1): Reviewer FINDINGS(유효, self_deviations 0), minor 1건: `commit_candidate.py`가 `git diff --cached --name-only`의 출력을 그대로 경로로 다시 넘겼다. git 기본 설정은 ASCII 밖 문자·따옴표·역슬래시가 든 경로를 따옴표와 8진수로 바꿔 출력하는데, 그 이름은 어떤 파일과도 맞지 않아 "스테이징 내용과 작업 트리가 같은가" 검사가 아무것도 비교하지 않고 통과했다(fail-open). 기본 예산을 다 써서 Owner에게 올렸다(Owner 결정 2).
- repair 2(`repair_count=2`, Owner가 1회 추가): 스테이징 목록을 `-z`(NUL 구분)로 받고, 작업 트리 차이는 경로 지정 없이 `git diff --name-only -z` 전체를 받아 스테이징 목록과 겹치는 것만 본다. 자체 검사에 한글과 공백이 든 경로(`docs/guide/안내 문서.md`)를 스테이징한 뒤 작업 트리를 바꾸면 그 경로 이름으로 거절되는 경우와, 다시 스테이징하면 그 거절 이유가 사라지는 경우를 더했다(12/12).
- 이 검사를 만들다 같은 종류의 한계를 `check_task_record.py`의 C3(owned 행 대조)에서 찾았다. C3도 스테이징 목록을 따옴표 이름으로 읽어 한글 경로를 owned 행에 없는 파일로 보고 막는다. 막는 쪽(fail-closed)이라 안전 구멍은 아니고, Owner 결정 2의 "이 결함만 고칩니다" 범위 밖이라 고치지 않았다. 한글 경로 파일을 바꾸는 task는 C3 때문에 사전 점검과 커밋 보호를 통과하지 못하므로 후속 task 후보다.
- 다시 돌린 결과: 세 스크립트의 `--self-test` PASS(12, 20, 18), SOP validator PASS.
