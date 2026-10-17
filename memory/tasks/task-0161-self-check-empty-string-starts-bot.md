# task-0161-self-check-empty-string-starts-bot

- id: `task-0161-self-check-empty-string-starts-bot`
- title: `Discord bot_minimal.py --self-check ''(빈 문자열)이 self-check로 처리되지 않고 실제 봇 기동 경로로 들어가는 결함`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-16 14:36 UTC`
- updated_at: `2026-10-17 06:51 UTC`
- summary: `adapters/discord/bot_minimal.py의 main()은 args.self_check의 참·거짓으로 self-check 여부를 정해서, --self-check ''(빈 문자열)은 self-check 분기를 지나쳐 .env 환경으로 실제 Discord 봇을 기동할 수 있다(task-0160 검증 중 실제 발생). Owner 결정으로 task-0160과 분리한 높은 우선순위 결함이다. Owner가 승인한 A안대로 main()의 두 판정을 args.self_check is not None으로 바꾸고 README 설명과 self-check suite 회귀 검사 1건을 더했으며, 실제 봇 기동 없이 검증하고 push는 하지 않는다.`
- source_command: `Owner 결정: 빈 문자열 결함은 별도 task로 등록, 우선순위 높음`

## 우선순위

높음(Owner 결정). task 모델에 우선순위 필드가 없어 본문에 적는다.

## Owner 결정 (원문)

```text
3. 빈 문자열 결함은 별도 task로 등록: task-0160과 분리하되, 우선순위는 높게 둡니다. 기존 코드가 빈 문자열을 self-check 입력으로 처리하지 않고 실제 봇 기동 경로로 진입할 수 있다는 점을 별도 결함으로 다룹니다.
```

```text
2. 빈 문자열 결함 별도 task 등록
별도 task를 `TODO` 상태로 등록하고 우선순위를 높게 설정한다.
문제: `--self-check ''` 입력이 기존 falsey 분기로 인해 self-check 처리 대신 실제 Discord 봇 기동 경로에 진입할 수 있음.
기존 task 등록 규칙과 문서 형식을 먼저 확인하고, 중복 task가 없는지 확인한 뒤 등록하라. 실제로 등록한 task ID를 보고하고 task-0160 기록의 X4에 해당 ID를 반영하라.
단, 이번 승인 범위는 TODO 등록과 Start Preview까지만이다.

* Start Confirm 금지
* 실제 봇 기동이나 Discord 연결 테스트 금지
* 코드 수정 금지
* 별도 task의 구현 시작 금지
```

## 문제 (기록 기준, 등록 시점의 정적 확인)

- `main()`은 `if args.self_check_suite or args.self_check:`로 출력 인코딩을 맞추고, `if args.self_check:` 안에서만 `.strip()` 뒤 빈 값을
  `empty_input`(종료 코드 2)으로 거절한다. 빈 문자열 `''`은 두 조건에서 모두 거짓이라 이 분기들을 지나친다.
- 그 뒤 `_validate_required_env()`가 통과하면 `_report_audit_chain_at_startup()`과 `asyncio.run(_start_discord_bot())`으로 실제 봇이
  기동한다. 공백만 있는 입력(`' '`)은 참이라 `empty_input`으로 거절된다.
- 실제 사례: task-0160 Implementer 검증 T5(2026-10-16 12:09~12:23 UTC 무렵). 경위와 미확인 사항은 task-0160 기록의
  "검증 중 발생한 사건" 절에 있다.

## 등록 시 확인

| 항목 | 결과 |
| --- | --- |
| 중복 task | `memory/tasks/`에서 `empty_input`, `self-check ''`, `self_check is not None`을 검색해 task-0160 기록 외에는 없음 |
| 기준 HEAD | `18198d0c2a1a2d24bf15852f32f1ef5d149d01d3` (task-0160 repair 1 candidate, 미push) |

## 후보 방향 (미승인, 정식 시작 전 Owner 결정 필요)

- `main()`이 `args.self_check is not None`으로 self-check 여부를 판정해 빈 문자열도 `empty_input`(종료 코드 2)으로 거절하는 방법이
  task-0160 기록에 후속 후보로 적혀 있다. 범위·검증 방법(실제 봇 기동 없이 확인하는 방법 포함)은 Owner 승인 뒤 정한다.
  (이 절은 등록 당시 기록이다. 승인된 범위는 아래 "Owner 결정"과 "Manager 요약"을 따른다.)

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `fd195bcafd2a46685563caa231d9ea8f880740bf` (main HEAD = origin/main) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 환경 | Windows ACP 949, Python 3.12.10, `PYTHONUTF8`·`PYTHONIOENCODING` 미설정. 메인 checkout에 `adapters/discord/.env` 있음(열지 않음) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` |

## 조사 결과 (read-only, 정적 분석 기준, 2026-10-17)

1. `--self-check`는 기본값이 없어 옵션이 없으면 `None`, `''`이면 빈 문자열이다. `main()`의 `if args.self_check_suite or args.self_check:`
   (출력 UTF-8화)와 `if args.self_check:`(self-check 처리, 빈 입력 `empty_input` 종료 2)가 둘 다 진릿값으로 판정해 `''`을 `None`과
   구분하지 못한다. `''`은 두 분기를 지나쳐 `_validate_required_env()` → `_report_audit_chain_at_startup()` →
   `asyncio.run(_start_discord_bot())`로 간다. 토큰은 `_load_env_file()`이 기본 경로 `adapters/discord/.env`에서 읽는다.
2. 공백만 있는 입력은 참이라 `.strip()` 뒤 `empty_input`(종료 2)으로 거절된다. 값 없는 `--self-check`는 argparse 오류(종료 2)다.
   `--self-check-suite` 분기는 `--self-check`보다 먼저라 영향이 없다.
3. 저장소 안에 `--self-check`를 코드로 부르는 곳은 없다(README 예시 19줄은 모두 값이 있음, team-manager-bot은 다른 봇).
   `jarvis.bat`은 접근 금지라 호출 여부를 확인하지 않았다(미확인).

## Owner 결정 (원문)

```text
task-0161 조사 결과를 검토했습니다. 아래 범위로 진행 준비해 주세요.

* A안 승인: `args.self_check` 판정 두 곳을 `args.self_check is not None`으로 수정
* README의 빈 입력 설명 수정
* self-check suite에 회귀 검사 1건 추가
* 회귀 검사는 `_validate_required_env`와 `_start_discord_bot`이 호출되지 않았음을 확인하고, `SystemExit(2)` 및 `empty_input`을 검증
* CLI 검증은 `.env`가 없는 깨끗한 worktree, 존재하지 않는 `--env-file` 경로, 자식 프로세스에서 `DISCORD_BOT_TOKEN` 제거 조건을 모두 갖춘 경우에만 실행
* 메인 checkout에서 `--self-check ''` 실행 금지
* `jarvis.bat`은 열기·읽기·수정·스테이징·커밋하지 않으며, 호출 여부는 미확인으로 기록
* 변경 범위와 검증 계획을 task-0161 기록에 반영하고 Console Start Preview까지만 준비한 뒤 중단

아직 Start Confirm, 구현, 커밋, push는 하지 마세요. Preview 결과와 변경 예정 범위를 보고하고 Owner의 다음 승인을 기다리세요.
```

정식 시작 승인(원문):

```text
task-0161 Console Start 진행하고 구현 시작해줘
```

candidate·Reviewer 진행 승인(원문):

```text
candidate 커밋해서 Reviewer 진행해
```

## Manager 요약

| # | 승인 조건 | Manager 해석과 충족 방법 |
| --- | --- | --- |
| P0 | 기록 반영 후 Console Start Preview까지만, Start Confirm·구현·커밋·push는 Owner의 다음 승인 뒤 | 이 기록에 범위와 검증 계획을 적고 Start Preview만 받는다(완료). 이후 승인은 P1·P2 |
| P1 | "task-0161 Console Start 진행하고 구현 시작해줘" | Start Confirm(`START TASK`)과 S1~S3 구현이 승인됐다 |
| P2 | "candidate 커밋해서 Reviewer 진행해" | candidate 커밋과 Reviewer 실행이 승인됐다. push는 여전히 승인되지 않았다(AGENTS.md·SOP의 별도 승인 사항) |
| X4 | "실제 봇 기동이나 Discord 연결 테스트 금지"(등록 승인 블록) | 이후 승인 블록이 풀지 않았으므로 계속 적용한다. 실제 봇 기동이나 Discord 연결을 일으키는 실행을 하지 않는다. suite 회귀 검사는 대역으로 기동 직전에 막고, CLI 검증은 V1 조건(토큰·`.env` 없음)에서만 한다 |
| S1 | `args.self_check` 판정 두 곳을 `args.self_check is not None`으로 | `main()`의 `if args.self_check_suite or args.self_check:`와 `if args.self_check:` 두 줄만 바꾼다. `''`은 `' '`와 같이 JSON `empty_input`, 종료 코드 2 |
| S2 | README의 빈 입력 설명 수정 | Discord README의 "공백만 있는 입력은 2다"를 빈 입력과 공백만 있는 입력이 2라는 뜻으로 고친다 |
| S3 | self-check suite에 회귀 검사 1건 | `sys.argv`를 `--self-check ''`과 없는 `--env-file` 경로로 바꿔 `main()`을 호출한다. `_validate_required_env`·`_start_discord_bot`은 호출되면 기록하고 예외를 내는 대역으로 바꾼다. 출력은 `io.TextIOWrapper(io.BytesIO())`로 받는다(`reconfigure` 필요). `SystemExit(2)`, 출력의 `empty_input`, 두 대역 미호출을 확인하고, 원래 함수·`sys.argv`·`sys.stdout`을 되돌린다. suite는 93건 → 94건 |
| V1 | CLI 검증 조건 | `.env` 없는 깨끗한 worktree, 없는 `--env-file` 경로, 자식 환경에서 `DISCORD_BOT_TOKEN` 제거를 모두 갖춘 경우에만 실행한다. 시간 제한을 두고 넘으면 그 프로세스만 종료한다 |
| X1 | 메인 checkout에서 `--self-check ''` 실행 금지 | 메인 checkout에서는 어떤 형태로도 실행하지 않는다 |
| X2 | `jarvis.bat` 접근 금지, 호출 여부 미확인 기록 | 열기·읽기·수정·스테이징·커밋하지 않고, 위 조사 결과 3에 미확인으로 적었다 |
| X3 | 범위 밖 수정 금지(이번 승인 범위가 정한 파일만), push 별도 승인(AGENTS.md·SOP) | 소유 파일은 아래 File ownership뿐이다 |

## File ownership

| 구분 | 경로 |
| --- | --- |
| owned | `adapters/discord/bot_minimal.py`(`main()`의 두 판정 줄, `_run_self_check_suite()`의 회귀 검사 1건), `adapters/discord/README.md`(빈 입력 설명 1줄), 이 기록 |
| deny | `jarvis.bat`, `adapters/discord/.env`, `docs/master-plan.md`, 다른 task 기록, 그 밖의 모든 파일 |

Docs 판정: README 변경이 승인 범위 안에 있어 Implementer candidate에 포함한다. 별도 Docs 단계는 `not_required`.

## 검증 계획

| # | 항목 |
| --- | --- |
| T1 | suite: 설정 없음·`PYTHONUTF8=1` 각각 종료 0, `ok=True`, 94/0, 새 회귀 검사 PASS. 실행 뒤 메인 checkout 변경 없음 |
| T2 | 새 회귀 검사의 강도: 수정을 뺀 변형(임시 worktree)에서 suite가 종료 1, `failed`에 새 검사 하나. 대역 덕분에 실제 기동 없이 실패로 드러나는지 |
| T3 | CLI(V1 조건 모두 충족 시에만): 수정 후 `--self-check ''`은 종료 2, reason `empty_input`. 수정을 뺀 변형은 reason `missing_env:DISCORD_BOT_TOKEN`(토큰이 없어 기동 직전에 멈춤). 종료 코드는 둘 다 2라 reason으로 판정 |
| T4 | 기존 동작 유지: `--self-check ' '` 종료 2(`empty_input`), `--self-check '/status invalid-id'` 종료 0, 옵션 없는 기동 경로는 바꾸지 않음(실행하지 않고 diff로 확인) |
| T5 | discord-intake smoke, Worker smoke, SOP validator, Console smoke, `git diff --check`, 변경 범위 |

## 구현 착수

2026-10-17 06:09 UTC에 Jarvis Console Start(Preview + Confirm, `START TASK`)로 `TODO→DOING`을 적용했다(Console 결과
`result_type: updated`, `TODO → DOING`, `no_execution: true`).

## 구현

| 파일 | 변경 |
| --- | --- |
| `adapters/discord/bot_minimal.py` | `main()`의 `if args.self_check_suite or args.self_check:`와 `if args.self_check:`를 `args.self_check is not None`으로 바꿨다(S1, 주석 1줄 포함). `_run_self_check_suite()` 끝에 회귀 검사 `self_check_empty_string_is_empty_input_not_bot_start`를 더했다(S3): `sys.argv`를 `--self-check ''`와 없는 임시 `--env-file`로 바꿔 `main()`을 부르고, `_validate_required_env`·`_start_discord_bot`은 호출을 기록하고 예외를 내는 대역으로 바꾸며, 출력은 `io.TextIOWrapper(io.BytesIO())`로 받는다. `SystemExit(2)`, 출력의 `empty_input`, 대역 미호출을 확인하고 원래 함수·`sys.argv`·`sys.stdout`을 되돌린다 |
| `adapters/discord/README.md` | `--self-check` 종료 코드 설명을 "빈 입력(`''`)과 공백만 있는 입력은 `empty_input`으로 거절되어 2다"로 고쳤다(S2) |

옵션 없는 기동 경로(`_validate_required_env()` 뒤)는 바꾸지 않았다.

## Implementer 검증 (작업 트리 기준, candidate 전)

T1~T4는 baseline `fd195bc` 임시 worktree에 작업 트리의 `bot_minimal.py`·README를 복사해 실행했다. 그 worktree에는 `.env`가 없었고(실행 전 확인,
있으면 중단하도록 함), 자식 환경에서 `DISCORD_BOT_TOKEN`을 지웠으며, CLI 실행은 없는 `--env-file` 경로와 60초 시간 제한을 걸었다. 메인
checkout에서는 `--self-check ''`을 어떤 형태로도 실행하지 않았다. 실행 뒤 worktree와 임시 폴더를 지웠고 메인 checkout의 HEAD·status는
실행 전후 같았다.

| # | 결과 |
| --- | --- |
| T1 | 설정 없음·`PYTHONUTF8=1` 모두 종료 0, `ok=True`, 94/0, 새 회귀 검사 PASS |
| T2 | 두 판정을 원래대로 되돌린 변형: suite 종료 1, `ok=False`, failed는 `self_check_empty_string_is_empty_input_not_bot_start` 하나, 상세 `start path reached: _validate_required_env`(대역에서 멈춤, 실제 기동 없음) |
| T3 | 수정 후 `--self-check ''` 종료 2, reason `empty_input`. 같은 변형에서 종료 2, reason `missing_env:DISCORD_BOT_TOKEN`(토큰이 없어 기동 직전에 멈춤) |
| T4 | `--self-check ' '` 종료 2(`empty_input`), `--self-check '/status invalid-id'` 종료 0(`result_type: error`). 기동 경로는 diff로 불변 확인 |
| T5 | `py_compile` 통과, discord-intake 136/0(task 기록 1건 증가 반영), Worker smoke 354/0(`%TEMP%` smoke 폴더 39개 그대로), SOP validator PASS, Console smoke PASS, `git diff --check` 통과, 변경 파일 2개와 이 기록 |

미확인: `jarvis.bat`의 `--self-check` 호출 여부(접근 금지).

## Reviewer와 repair 이력

| 회차 | candidate | 결과 |
| --- | --- | --- |
| Reviewer 1 | `0abdf86de43d7ecbbd653e12763a1ddadaffb65c` | FINDINGS(minor 4, 모두 이 기록): Manager 요약 P0가 이후의 시작·candidate 승인을 반영하지 않음, 등록 승인 블록의 "실제 봇 기동이나 Discord 연결 테스트 금지"가 요약에 없음, summary 필드가 TODO 등록 상태를 말함, 파일 끝 줄바꿈이 빠짐. 코드·README 지적 없음. Reviewer 보고에 `self_deviations` 1건(git grep 대안 패턴)이 있어 SOP상 이 검토는 무효이고, 새 candidate에 Reviewer를 다시 실행한다 |
| repair 1 | (이 기록 수정) | Manager가 budget 안에서 진행. summary 필드를 승인 범위와 구현 상태에 맞게 고치고, 시작·candidate 승인 원문을 "Owner 결정"에 옮기고, Manager 요약에 P1·P2(push 미승인 포함)·X4를 더하고, 파일 끝 줄바꿈을 되살렸다. 코드와 README는 바꾸지 않았다. `repair_count=1`(budget 1 소진) |
