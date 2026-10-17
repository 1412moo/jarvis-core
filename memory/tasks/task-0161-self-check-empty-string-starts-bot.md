# task-0161-self-check-empty-string-starts-bot

- id: `task-0161-self-check-empty-string-starts-bot`
- title: `Discord bot_minimal.py --self-check ''(빈 문자열)이 self-check로 처리되지 않고 실제 봇 기동 경로로 들어가는 결함`
- status: `TODO`
- repo: `jarvis-core`
- created_at: `2026-10-16 14:36 UTC`
- updated_at: `2026-10-16 14:36 UTC`
- summary: `adapters/discord/bot_minimal.py의 main()은 args.self_check의 참·거짓으로 self-check 여부를 정해서, --self-check ''(빈 문자열)은 self-check 분기를 지나쳐 .env 환경으로 실제 Discord 봇을 기동할 수 있다(task-0160 검증 중 실제 발생). Owner 결정으로 task-0160과 분리한 높은 우선순위 결함이며, 지금은 TODO 등록만 했고 구현 범위와 방법은 정식 시작 전에 Owner 승인을 받는다.`
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
