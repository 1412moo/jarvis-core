# task-0198-preflight-non-ascii-paths

- id: `task-0198-preflight-non-ascii-paths`
- title: `사전 점검의 한글 경로`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-25 15:38 UTC`
- updated_at: `2026-10-25 15:39 UTC`
- summary: `사전 점검 check_task_record.py의 스테이징 목록이 git 기본 출력(ASCII 밖 문자·따옴표·역슬래시가 든 경로를 따옴표와 8진수로 바꿈)을 그대로 읽어, 한글 이름 파일을 owned 행에 없는 파일로 보고 C3로 막는 문제를 고친다. 목록을 -z(NUL 구분)로 읽는다. SOP 경량화 파일럿의 측정 대상 첫 task다.`
- source_command: `Owner 지시: C3 한글 경로 수정 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `b5f3794c2a25c78bc889e75dfffb5a0513562fbc` (등록 시점 main HEAD, task-0197까지 push 완료) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |
| 파일럿 | SOP 경량화 파일럿(task-0197) 측정 대상 1/3. 요약 표는 `check_summary_quotes.py --emit-table`, candidate는 `commit_candidate.py --require-quotes`로 만든다 |

## Owner 결정 (원문)

```text
[Manager 보고: task-0197 완료 보고 중]
후속 후보 (범위 밖이라 고치지 않음)
- 사전 점검의 C3(owned 행 대조)가 한글 경로를 owned에 없는 파일로 보고 막습니다. 막는 쪽으로 틀리는 것이라 안전 구멍은 아니지만, 한글 이름 파일을 바꾸는 task는 지금 점검을 통과하지 못합니다.

다음
1. 커밋 5개 push.
2. 다음 수동 task 3건이 파일럿 측정 대상입니다. 수동 task를 하실 때 두 도구를 쓰고 기록을 남기겠습니다.
   - 추천 첫 후보는 위 C3 한글 경로 수정입니다. 작고, 파일럿 측정에도 쓸 수 있습니다.

[Owner 답]
푸시하고 C3 한글 경로 수정 task로 진행해
```

## 설계

1. `scripts/check_task_record.py`에서 스테이징 목록을 읽는 `git diff --cached --name-only --no-renames <baseline>`에 `-z`를 더하고 NUL로 나눈다. owned 대조 규칙과 다른 검사는 바꾸지 않는다.
2. 자체 검사: owned 디렉터리 안의 한글·공백 경로는 C3를 통과하고, owned 밖의 한글 경로는 C3로 막히며 사유에 원래 이름이 그대로 나온다.
3. 같은 종류의 다른 git 출력 읽기가 이 스크립트에 있으면 함께 본다(있으면 기록에 적고, 범위를 넓혀야 하면 Owner에게 묻는다).

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `scripts/check_task_record.py`(스테이징 목록 읽기와 자체 검사만), `memory/tasks/task-0198-preflight-non-ascii-paths.md` |
| deny | `jarvis.bat`, `apps/`, 다른 스크립트(`commit_candidate.py`, `check_summary_quotes.py` 포함), 봇·Worker·팀장 코드, writer·Console, AGENTS·agent 정의, SOP, validator, 다른 task 기록, 외부 API·credential, 보호 worktree |

## 계획

1. 변경과 자체 검사.
2. 검사: `check_task_record.py --self-test`, `commit_candidate.py --self-test`(한글 경로 경우가 이제 끝까지 커밋되는지 확인만, 코드는 바꾸지 않음), 수동 기록 전체의 기본 점검 결과 불변, validator.
3. 사전 점검 → self-review → candidate(`commit_candidate.py --require-quotes`) → Reviewer → QA → Evidence·Complete → checkpoint. 기록 끝에 파일럿 측정값. push는 별도 지시.

## Start

Console Start Preview(TODO → DOING, 실행 없음)를 확인하고 `START TASK`로 Confirm했다(receipt updated_at `2026-10-25 15:38 UTC`, status 줄만 바뀜). Console은 Start 뒤 껐다.

## 구현

- `scripts/check_task_record.py`: 스테이징 목록 읽기에 `-z`를 더하고 NUL로 나눈다(한 곳). 자체 검사 2개를 더했다: owned 디렉터리 안의 한글·공백 경로(`docs/guide/한글 안내.md`)는 통과하고 스테이징 목록에 원래 이름으로 들어감, owned 밖의 한글 경로(`한글 메모.txt`)는 C3로 막히고 사유에 원래 이름이 나오며 8진수 표기가 없음.
- 같은 스크립트의 다른 git 읽기(`git show :<기록>`, `git show HEAD:<기록>`)는 기록 경로를 넘기는 쪽이고 기록 이름은 task ID(영문)라 해당하지 않는다. 범위를 넓히지 않았다.

## Implementer 검증 (작업 트리)

- `check_task_record.py --self-test` PASS 20/20(이전 18에 2개), `commit_candidate.py --self-test` PASS 12/12(코드 미변경), SOP validator PASS.
- 기본 동작: 수동 task 기록 139건을 옵션 없이 점검해 C6 위반 0건.
- 저장소 밖 임시 저장소에서 `commit_candidate.commit()`으로 한글·공백 경로 파일과 기록을 스테이징해 커밋해 보니 종료 코드 0으로 커밋됐다(task-0197에서 C3 때문에 막히던 경우).

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문) | "[Manager 보고: task-0197 완료 보고 중]" | 보고의 표지. 해석할 조건이 아니다 |
| A2 | Owner 결정 (원문) | "후속 후보 (범위 밖이라 고치지 않음)" | 제목 줄. 해석할 조건이 아니다 |
| A3 | Owner 결정 (원문) | "사전 점검의 C3(owned 행 대조)가 한글 경로를 owned에 없는 파일로 보고 막습니다." | C3가 스테이징 목록을 `-z`로 읽어 한글 경로를 원래 이름으로 대조한다. owned 안은 통과, 밖은 원래 이름으로 막힘(자체 검사 2개) |
| A4 | Owner 결정 (원문) | "막는 쪽으로 틀리는 것이라 안전 구멍은 아니지만, 한글 이름 파일을 바꾸는 task는 지금 점검을 통과하지 못합니다." | 막는 쪽 판정 규칙(owned 밖이면 C3)은 그대로이고, 이름 읽기만 고쳤다 |
| A5 | Owner 결정 (원문) | "커밋 5개 push." | Owner 답에 따라 task 등록 전에 push했다(`5df2645..b5f3794`) |
| A6 | Owner 결정 (원문) | "다음 수동 task 3건이 파일럿 측정 대상입니다." | 제목 줄. 해석할 조건이 아니다 |
| A7 | Owner 결정 (원문) | "수동 task를 하실 때 두 도구를 쓰고 기록을 남기겠습니다." | 요약 표는 `--emit-table`, candidate는 `commit_candidate.py --require-quotes`로 만들고, 기록 끝에 측정값을 남긴다 |
| A8 | Owner 결정 (원문) | "추천 첫 후보는 위 C3 한글 경로 수정입니다." | 그 후보를 이 task로 진행한다 |
| A9 | Owner 결정 (원문) | "작고, 파일럿 측정에도 쓸 수 있습니다." | 변경은 한 줄과 자체 검사 2개다 |
| A10 | Owner 결정 (원문) | "[Owner 답]" | Owner 답의 표지. 해석할 조건이 아니다 |
| A11 | Owner 결정 (원문) | "푸시하고 C3 한글 경로 수정 task로 진행해" | push 뒤 이 task를 등록하고 진행했다 |
