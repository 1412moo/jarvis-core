# task-0163-run-child-output-utf8

- id: `task-0163-run-child-output-utf8`
- title: `Discord /run 허용 스크립트의 자식 출력을 UTF-8로 맞추기`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-17 13:46 UTC`
- updated_at: `2026-10-17 14:36 UTC`
- summary: `Discord 봇의 /run 경로는 허용 스크립트 출력을 UTF-8로 해독하지만, 자식 Python은 출력이 파이프일 때 이 데스크톱의 cp949로 써서 intake smoke 출력의 한국어가 깨진다(U+FFFD 280개 재현). _build_execution_result_real()의 subprocess.run에 PYTHONIOENCODING=utf-8을 더한 환경을 넘기고 self-check 판정을 보강한다. 허용 목록·타임아웃·요약 규칙은 바꾸지 않고, Start/Complete는 Owner가 Console 화면에서 직접 실행하며 push는 하지 않는다.`
- source_command: `Owner 승인: task-0163 제안 승인, TODO 등록`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `fb61910e720f242e7bae03c06aaf21ba21ae0a65` (main HEAD = origin/main) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 환경 | Windows ACP 949, Python 3.12.10, `PYTHONUTF8`·`PYTHONIOENCODING` 미설정 |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` |

## 조사 결과 (read-only, 2026-10-17)

1. 경로: `/run` → `_build_execution_result_real()`(`adapters/discord/bot_minimal.py`)이 `EXECUTION_SCRIPT_WHITELIST`의 유일한 명령
   `python orchestrator/discord-intake/run_smoke_tests.py`를 `subprocess.run`으로 실행한다. 부모는 task-0158부터
   `encoding="utf-8", errors="replace"`로 해독한다. `env`를 넘기지 않아 자식은 봇 환경을 그대로 물려받는다.
2. 자식: 출력이 파이프라 cp949로 쓰고, intake smoke는 결과 JSON을 `ensure_ascii=False`로 출력해 한국어가 cp949 바이트로 나간다.
3. 재현(같은 명령, 출력 파이프, Discord·task 기록 무관): 그대로면 28,183 bytes, UTF-8 해독 실패(544번째 바이트), U+FFFD 280개(예:
   `"summary": "��û ����(report-system-improvement)..."`). 자식에 `PYTHONIOENCODING=utf-8` 또는 `PYTHONUTF8=1`을 주면 28,389 bytes,
   UTF-8 정상, U+FFFD 0개.
4. 영향: `output_summary`는 stdout 앞 220자만 저장하고 지금 출력의 앞 220자는 ASCII라, 기록되는 요약에는 아직 깨짐이 보이지 않는다.
   출력 앞부분에 한국어가 오거나, 실패로 출력이 달라지거나, cp949에 없는 문자를 출력하면 요약이 깨지거나 자식이 `UnicodeEncodeError`로
   멈출 수 있다(잠재 결함).
5. 범위 밖으로 확인만 한 것: 허용 명령이 `sys.executable`이 아닌 `python`을 쓰는 점, 실행 제한 10초, Buzz 알림 발행(node),
   Worker `claude_worker._run`의 테스트 명령(같은 유형일 수 있으나 확인하지 않음), intake smoke 스크립트 자체.

## Owner 결정 (원문)

```text
task-0163 제안을 승인합니다.

1. `task-0163-run-child-output-utf8`을 TODO로 등록해 주세요.
2. 제안된 범위, 완료 조건, T1~T5 검증 계획을 task 기록에 반영합니다.
3. 등록 후 파일 수정이나 구현은 시작하지 말고 멈춰 주세요.
4. 제가 Console Project Control 화면에서 직접 Start Preview → Confirm을 진행하겠습니다.
5. `jarvis.bat`은 열기·읽기·수정·스테이징·커밋하지 않습니다. push도 별도 승인 없이 하지 않습니다.

등록 결과와 Git 상태만 보고하고 기다려 주세요.
```

조사 보고의 Owner 지시(원문 발췌): "이번 작업과 관계없는 인코딩 처리, 봇 동작, 리팩터링은 범위에 넣지 않습니다."
정식 시작 위임(원문): `너가해` (Console 서버 기동 뒤, Start 실행을 Manager에게 맡김)

구현 진행 지시(원문): `구현 진행해줘`

candidate·Reviewer 진행 승인(원문):

```text
task-0163의 다음 단계를 승인합니다.

1. 현재 구현과 task 기록을 검토하고 candidate 커밋을 생성합니다.
2. candidate에 대해 Reviewer를 실행하고 findings를 보고합니다.
3. 수정이 필요하면 task에 정해진 repair budget(retry 1, repair 1) 안에서만 진행합니다.
4. `adapters/discord/bot_minimal.py`와 task-0163 기록 외의 파일은 변경하지 않습니다.
5. `jarvis.bat`은 열기·읽기·수정·스테이징·커밋하지 않습니다.
6. Console 서버는 유지합니다. 제가 직접 Console에서 Complete를 실행할 예정이므로 서버를 종료하지 마세요.
7. QA checkpoint, DONE 처리, master-plan 수정, push는 아직 하지 않습니다.

candidate 커밋의 해시와 변경 범위, Reviewer 결과, 현재 Git 상태를 보고하고 멈춰 주세요.
```
Reviewer 1 FINDINGS 뒤 S2a 승인과 repair 1 승인(원문):

```text
1. S2a(self-check 상세에서 env 제외)를 이번 task 범위에 포함하는 것을 승인합니다. 환경변수 전체를 상세 출력에 노출하지 않고, `PYTHONIOENCODING` 값과 `PATH` 유지 여부만 출력하는 변경을 유지해 주세요.
2. Reviewer 1의 minor findings 3건을 처리하기 위해 repair 1을 승인합니다. task 기록에 누락된 두 승인 지시문을 인용하고, S2a에 대한 이번 승인을 명시해 주세요.
3. 코드 변경은 하지 마세요. task 기록만 수정한 뒤 새 candidate로 Reviewer를 다시 실행해 결과를 보고해 주세요.
4. QA checkpoint, Console Complete, DONE 처리, master-plan 수정, push는 아직 승인하지 않습니다. `jarvis.bat`은 계속 보호하고, Console 서버도 유지해 주세요.
5. 새 candidate 해시, 수정된 기록 범위, Reviewer 결과, Git 상태를 보고하고 멈춰 주세요.
```

## Manager 요약

| # | 승인 조건 | Manager 해석과 충족 방법 |
| --- | --- | --- |
| P0 | "`task-0163-run-child-output-utf8`을 TODO로 등록해 주세요." / "등록 후 파일 수정이나 구현은 시작하지 말고 멈춰 주세요." / "등록 결과와 Git 상태만 보고하고 기다려 주세요." | 이 기록만 `TODO`로 만들고, 등록 결과와 Git 상태만 보고한 뒤 멈췄다. 구현은 Owner의 Start 뒤, 구현 진행 지시를 받은 다음에 했다 |
| P1 | "제가 Console Project Control 화면에서 직접 Start Preview → Confirm을 진행하겠습니다." 뒤 Owner 지시 "너가해" | 처음에는 Owner가 직접 실행하기로 했으나, Owner가 서버 기동 뒤 "너가해"로 맡겼다. Manager는 Console API를 스크립트로 부르지 않고 Console Project Control 화면의 Start Task → Confirm Start 버튼으로 실행했다(13:54 UTC). Complete는 Owner가 Console에서 직접 실행할 예정이다 |
| P2 | "제안된 범위, 완료 조건, T1~T5 검증 계획을 task 기록에 반영합니다." | 아래 범위·완료 조건·검증 계획 절 |
| S1 | 범위: 자식 실행 환경에 `PYTHONIOENCODING=utf-8` | `_build_execution_result_real()`의 `subprocess.run`에 `env={**os.environ, "PYTHONIOENCODING": "utf-8"}`를 넘기는 1줄. 나머지 인자와 동작은 그대로 |
| S2 | 범위: self-check 보강 | 기존 `execution_output_utf8_and_none_safe` 판정에 넘긴 `env`의 `PYTHONIOENCODING == "utf-8"`과 다른 변수(예: `PATH`) 보존을 더한다. 검사 수 94 그대로 |
| P3 | "구현 진행해줘" | Start 뒤 S1·S2 구현을 시작했다 |
| P4 | candidate 승인 블록 1~3: "현재 구현과 task 기록을 검토하고 candidate 커밋을 생성합니다." / "candidate에 대해 Reviewer를 실행하고 findings를 보고합니다." / "수정이 필요하면 task에 정해진 repair budget(retry 1, repair 1) 안에서만 진행합니다." | candidate 커밋과 Reviewer 실행이 승인됐다. repair·retry는 각 1회까지이고 넘으면 Owner에게 보고한다 |
| P5 | candidate 승인 블록 4~7: "`adapters/discord/bot_minimal.py`와 task-0163 기록 외의 파일은 변경하지 않습니다." / "`jarvis.bat`은 …" / "Console 서버는 유지합니다. 제가 직접 Console에서 Complete를 실행할 예정이므로 서버를 종료하지 마세요." / "QA checkpoint, DONE 처리, master-plan 수정, push는 아직 하지 않습니다." | 변경 파일은 두 개뿐이다. Manager가 띄운 Console 서버(PID 30036)를 종료하지 않는다. Complete는 Owner가 직접 실행한다. QA checkpoint·DONE·master-plan·push는 하지 않는다 |
| S2a | Implementer가 S2 구현 중 추가한 변경. Owner 승인(repair 1 블록 1): "S2a(self-check 상세에서 env 제외)를 이번 task 범위에 포함하는 것을 승인합니다. 환경변수 전체를 상세 출력에 노출하지 않고, `PYTHONIOENCODING` 값과 `PATH` 유지 여부만 출력하는 변경을 유지해 주세요." | S2로 self-check가 env를 다루게 되면서 기존 상세 문자열(`kwargs` 전체 출력)에 `.env`에서 읽은 봇 토큰이 찍힐 수 있었다. 같은 검사의 상세에서 `env`를 빼고 `PYTHONIOENCODING` 값과 `PATH` 보존 여부만 찍는다. 판정은 S2 그대로이고 다른 검사·출력은 바꾸지 않는다. AGENTS.md 원칙 5(비밀 정보를 산출물에 노출하지 않음)에 따른 것이다 |
| P6 | candidate 승인 블록 마지막 문장: "candidate 커밋의 해시와 변경 범위, Reviewer 결과, 현재 Git 상태를 보고하고 멈춰 주세요." | Reviewer 1 뒤 해시·변경 범위·Reviewer 결과·Git 상태를 보고하고 멈췄다. 보고 없이 QA나 repair로 넘어가지 않았다 |
| P7 | repair 1 블록 2~5: "Reviewer 1의 minor findings 3건을 처리하기 위해 repair 1을 승인합니다. task 기록에 누락된 두 승인 지시문을 인용하고, S2a에 대한 이번 승인을 명시해 주세요." / "코드 변경은 하지 마세요. task 기록만 수정한 뒤 새 candidate로 Reviewer를 다시 실행해 결과를 보고해 주세요." / "QA checkpoint, Console Complete, DONE 처리, master-plan 수정, push는 아직 승인하지 않습니다. `jarvis.bat`은 계속 보호하고, Console 서버도 유지해 주세요." / "새 candidate 해시, 수정된 기록 범위, Reviewer 결과, Git 상태를 보고하고 멈춰 주세요." | repair 1은 이 기록만 고친다(P0 보강, P6·P7 추가, S2a에 Owner 승인 인용, 이력). 코드 변경 없음. 새 candidate에 Reviewer를 다시 실행하고 해시·기록 범위·Reviewer 결과·Git 상태를 보고한 뒤 멈춘다. QA checkpoint·Complete·DONE·master-plan·push는 하지 않고 Console 서버를 유지한다 |
| X1 | "이번 작업과 관계없는 인코딩 처리, 봇 동작, 리팩터링은 범위에 넣지 않습니다." | 허용 목록, 실행 명령(`python`), 타임아웃, 요약 규칙(220자·제어 문자), Buzz 발행, Worker, intake smoke 스크립트는 바꾸지 않는다 |
| X2 | "`jarvis.bat`은 열기·읽기·수정·스테이징·커밋하지 않습니다. push도 별도 승인 없이 하지 않습니다." | 접근하지 않고 push하지 않는다(push는 AGENTS.md·SOP상으로도 별도 승인) |

## File ownership

| 구분 | 경로 |
| --- | --- |
| owned | `adapters/discord/bot_minimal.py`(`_build_execution_result_real()`의 `subprocess.run` env 1줄, self-check `execution_output_utf8_and_none_safe` 판정), 이 기록 |
| deny | `jarvis.bat`, `adapters/discord/.env`, `orchestrator/discord-intake/run_smoke_tests.py`, `orchestrator/worker/`, `docs/master-plan.md`, 다른 task 기록, 그 밖의 모든 파일 |

Docs 판정: README 변경 없음, 별도 Docs 단계 `not_required`.

## 완료 조건

1. `/run` 허용 스크립트 실행에 `PYTHONIOENCODING=utf-8`이 들어가고 나머지 환경은 그대로다.
2. 설정 없는 cp949 환경에서 같은 허용 명령의 실제 출력이 UTF-8로 해독되고 U+FFFD가 0개다.
3. self-check 94/0이고 다른 검사가 모두 통과한다.
4. 허용 목록, 타임아웃, 요약 규칙은 바뀌지 않는다.

## 검증 계획

| # | 항목 |
| --- | --- |
| T1 | self-check: 설정 없음·`PYTHONUTF8=1` 각각 종료 0, `ok=True`, 94/0 |
| T2 | 실제 허용 명령을 수정 후와 같은 kwargs로 실행하면 UTF-8 해독 정상, U+FFFD 0개. 수정 전 방식은 U+FFFD 280개(재현과 같음) |
| T3 | 변형: `env` 줄을 빼면 self-check에서 `execution_output_utf8_and_none_safe`가 실패로 드러나는지 |
| T4 | `_build_execution_result_real()`을 직접 불러 실제 실행 결과가 `executed`·`success`이고 요약 규칙(220자, 제어 문자 처리)이 그대로인지. Discord 접속·task 기록 쓰기 없음 |
| T5 | discord-intake smoke, Worker smoke, SOP validator, Console smoke, `git diff --check`, 변경 범위 |

검증에서 봇 기동이나 `--self-check ''` 실행은 하지 않는다.

## Console 생애주기 검증 (Owner 직접 실행)

Start와 Complete는 Owner가 Console Project Control 화면에서 직접 Preview → Confirm으로 실행한다. Manager는 그 뒤 task 파일 diff가
status와 updated_at뿐인지 확인하고, Owner가 화면 사용 중 겪은 불편 사항이 있으면 이 기록에 남긴다.

## 구현 착수

2026-10-17 13:54 UTC에 Console Project Control 화면에서 Start(Preview → Confirm Start)로 `TODO→DOING`을 적용했다. Owner가
"너가해"로 맡겨 Manager가 앱 내장 브라우저의 같은 화면 버튼으로 실행했다(Preview: `TODO → DOING`, 예정 13:54 UTC, "No execution";
Receipt: "Updated", 상태 표시 "Task write succeeded: TODO → DOING; Overview refresh succeeded."). 실행 뒤 `status`·`updated_at`
값을 확인했다. 이 기록은 그때 미추적 새 파일이라 본문 전체를 diff로 대조하지는 못했다.

화면 사용 관찰: 앱 내장 브라우저 창이 좁아(약 280px) Preview 아래 Confirm 버튼까지 스크롤이 필요했다. Start → Preview → Confirm →
Receipt → 화면 새로고침은 한 카드 안에서 이어져 흐름은 끊기지 않았다.

## 구현

| 파일 | 변경 |
| --- | --- |
| `adapters/discord/bot_minimal.py` | `_build_execution_result_real()`의 `subprocess.run`에 `env={**os.environ, "PYTHONIOENCODING": "utf-8"}`(S1). self-check `execution_output_utf8_and_none_safe` 판정에 넘긴 env의 `PYTHONIOENCODING == "utf-8"`과 `PATH` 보존을 더했다(S2) |

S2를 고치며 하나를 더 막았다: 이 검사의 상세 문자열은 `kwargs` 전체를 찍었는데, 이제 그 안에 env가 들어가 `.env`에서 읽은 봇 토큰까지
self-check 출력에 나올 수 있었다. 상세에서 `env`를 빼고 `PYTHONIOENCODING` 값과 `PATH` 보존 여부만 찍게 했다(같은 검사 안의 출력 정리이고
판정은 S2 그대로). 허용 목록, 실행 명령, 타임아웃, 요약 규칙은 바꾸지 않았다.

## Implementer 검증 (작업 트리 기준, candidate 전)

T1~T4는 baseline `fb61910` 임시 worktree에 작업 트리의 `bot_minimal.py`를 복사해 실행했다. 그 worktree에는 `.env`가 없었고 실행
환경에서 `DISCORD_BOT_TOKEN`·`PYTHONUTF8`·`PYTHONIOENCODING`을 지웠다. 봇 기동과 `--self-check ''`은 하지 않았다. 실행 뒤 worktree를
지웠고 메인 checkout은 실행 전후 같았다.

| # | 결과 |
| --- | --- |
| T1 | 설정 없음·`PYTHONUTF8=1` 모두 종료 0, `ok=True`, 94/0, `execution_output_utf8_and_none_safe` PASS. 상세에 env 값 없음 |
| T2 | 허용 명령을 봇과 같은 해독으로 실행: 물려받은 env 그대로면 U+FFFD 280개·한국어 깨짐, `PYTHONIOENCODING=utf-8`을 더하면 U+FFFD 0개·한국어 정상 |
| T3 | env 줄을 뺀 변형: suite 종료 1, failed는 `execution_output_utf8_and_none_safe` 하나 |
| T4 | 실제 `_build_execution_result_real()` 실행(Discord·task 기록 없음): `executed`·`success` true, `error_reason` 없음, 요약 223자(220자 + "..."), 제어 문자 0, U+FFFD 0 |
| T5 | discord-intake 138/0(task 기록 증가 반영), Worker smoke 354/0(`%TEMP%` smoke 폴더 39개 그대로), SOP validator PASS, Console smoke PASS, `git diff --check` 통과, 변경 파일 `bot_minimal.py` 하나(+12/−1)와 이 기록 |

## Reviewer와 repair 이력

| 회차 | candidate | 결과 |
| --- | --- | --- |
| Reviewer 1 | `dcd69d876d528a846189185c0408acdcdf28986c` | FINDINGS(minor 3, 모두 이 기록), `self_deviations` 없음: candidate 승인 마지막 문장(보고 후 멈춤) 행 없음, 등록 승인 마지막 문장(등록 결과·Git 상태만 보고)이 P0에 없음, S2a에 승인 근거 없음. 코드 지적 없음 |
| repair 1 | (이 기록 수정) | Owner가 S2a를 범위에 포함해 승인하고 repair 1을 승인했다. P0에 등록 승인 마지막 문장 인용, P6(보고 후 멈춤)·P7(repair 1 블록) 추가, S2a에 Owner 승인 인용, 승인 원문 블록 추가. 코드 변경 없음. `repair_count=1`(budget 1 소진) |
