# task-0158-utf8-independent-smoke-and-execution-output

- id: `task-0158-utf8-independent-smoke-and-execution-output`
- title: `Python 기본 인코딩이 cp949인 환경에서도 Worker smoke·Discord self-check가 통과하고 봇 실행 출력 해독이 멈추지 않게 하기`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-15 09:22 UTC`
- updated_at: `2026-10-15 10:47 UTC`
- summary: `Python 기본 인코딩이 cp949인 이 데스크톱에서 PYTHONUTF8 없이 실행하면 Worker smoke는 가짜 claude의 stdin과 smoke git 헬퍼가 UTF-8을 cp949로 읽어 실패하고, Discord self-check는 결과의 이모지를 cp949 콘솔에 출력하다 실패하며, 봇의 허용 스크립트 실행은 자식 출력을 기본 인코딩으로 해독해 stdout이 None이면 멈출 수 있다. 가짜 claude stdin, smoke git 헬퍼, self-check 결과 출력, 봇 실행 출력 해독을 UTF-8로 맞추고 None 출력 보호를 더해 Worker의 _run과 같게 한다. push는 하지 않는다.`
- source_command: `Owner 승인: 인코딩 문제 B안으로 진행`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `54eef73e282814151ab6c68ef427028cc3e886ca` (main HEAD = origin/main) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 환경 | Windows ACP 949, Python 3.12.10, `locale.getpreferredencoding()`=`cp949`, `utf8_mode=0`, `PYTHONUTF8`·`PYTHONIOENCODING` 사용자·시스템 미설정 |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=1` (repair 1 뒤) |

## 조사 결과 (read-only, 코드와 재현 기준)

1. Worker smoke: `claude_worker._run()`은 prompt를 UTF-8로 보내고 UTF-8(`errors="replace"`)로 읽는다. 가짜 claude(`run_smoke_tests.py`의
   `FAKE_CLAUDE`)는 `sys.stdin.read()`를 기본 인코딩 cp949(`surrogateescape`)로 읽어 한국어가 surrogate가 되고, `FAKE_LOG`(UTF-8) 쓰기에서
   `UnicodeEncodeError`가 난다(scratch 재현). 진짜 `claude` CLI(Node)는 UTF-8이라 실제 Worker 경로는 영향이 없다.
2. Discord self-check: 설정이 없는 상태에서는 `main()`이 결과 JSON을 출력할 때(`print(json.dumps(..., ensure_ascii=False))`)
   이모지 `\U0001f4c4`를 cp949로 인코딩하지 못해 `UnicodeEncodeError`로 멈춘다. `PYTHONIOENCODING=utf-8`일 때 보인 `AttributeError`
   (`_summarize_execution_output`의 `stdout`이 `None`)는 자식만 UTF-8로 쓰고 부모가 cp949로 해독해 생긴 것이다.
3. 봇 허용 스크립트 실행(`_run_execution_flow` 안 `subprocess.run`, baseline `bot_minimal.py:1565`)은 `text=True`에 `encoding`이 없어
   자식 출력을 기본 인코딩으로 해독하고, 해독에 실패하면 `completed.stdout`이 `None`인데 `_summarize_execution_output(completed.stdout,
   completed.stderr)`(`:1596`)로 그대로 넘겨 `AttributeError`가 난다. `PYTHONUTF8=1`이면 부모·자식이 모두 UTF-8이라 안전하다.
4. task-0157 기록의 환경 관찰 중 "Discord self-check는 `_summarize_execution_output`의 `stdout`이 `None`이라 `AttributeError`로
   멈춘다"는 `PYTHONIOENCODING=utf-8`을 붙여 실행한 결과였다. 설정 없는 상태의 실패는 2의 이모지 출력이다(기록 정정은 별도 승인 대상).

## Owner 결정 (원문)

```text
B안으로 진행해
```

승인 대상인 B안은 Director 보고의 다음 원문이다.

```text
- **B. 코드로 환경 독립화 (추천, SOP task로 진행)** — task-0153과 같은 방향입니다.
  - 가짜 claude가 stdin을 UTF-8로 읽게 합니다(`_run`의 UTF-8 약속과 맞춤).
  - self-check 결과 출력도 UTF-8로 맞춥니다.
  - `bot_minimal.py:1565`에 `encoding="utf-8", errors="replace"`와 `or ""` 보호를 넣어 Worker의 `_run`과 같게 합니다.
  - 회귀 테스트는 `PYTHONUTF8`·`PYTHONIOENCODING` 없이 Worker smoke와 self-check가 통과하는지 확인하는 것입니다.
```

## Manager 요약

| # | 승인 조건 | Manager 해석과 충족 방법 |
| --- | --- | --- |
| P0 | SOP task로 진행 | 이 기록 생성 → Console Start → Implementer candidate → Reviewer → QA → 기록 checkpoint. DONE은 Owner의 Console Complete 결정 |
| B1 | 가짜 claude가 stdin을 UTF-8로 읽음(`_run`의 UTF-8 약속과 맞춤) | `FAKE_CLAUDE`에서 `sys.stdin.reconfigure(encoding="utf-8")` 뒤 읽는다. 진짜 Worker 코드(`claude_worker.py`)는 바꾸지 않는다 |
| B2 | self-check 결과 출력도 UTF-8 | `main()`의 `--self-check-suite`와 `--self-check` 분기가 JSON을 출력하기 전에 stdout을 UTF-8로 맞춘다. 실제 봇 기동 경로의 출력은 바꾸지 않는다 |
| B3 | `bot_minimal.py:1565`에 `encoding="utf-8", errors="replace"`와 `or ""` 보호, Worker `_run`과 같게 | 그 `subprocess.run`에 두 인자를 더하고, 결과 요약에 `completed.stdout or ""`, `completed.stderr or ""`를 넘긴다 |
| B4 | 회귀 테스트: `PYTHONUTF8`·`PYTHONIOENCODING` 없이 Worker smoke와 self-check 통과 | QA에서 두 변수를 지운 환경으로 Worker smoke·self-check·intake를 실행한다. self-check에는 `completed.stdout`이 `None`이어도 멈추지 않는 경우를 더한다 |
| B5 | Owner 결정 (1): smoke `git()` 헬퍼도 UTF-8 해독 | `run_smoke_tests.py`의 `git()`이 `encoding="utf-8", errors="replace"`로 읽는다. B1만으로는 설정 없는 Worker smoke가 이 헬퍼(`git show`의 한국어 glossary 해독 실패 → `stdout` None)에서 멈춰 B4 목표를 채우지 못했다. (1)의 조건대로 그다음 설정 없는 환경의 Worker smoke 통과를 확인하고(V1), 이 수정을 빼면 다시 실패하는 변형을 추가한다(V4) |
| M1 | Manager 관찰(범위 밖) | 설정 없는 환경에서 허용 스크립트의 자식(discord-intake smoke)은 cp949로 쓴다. B3 뒤 부모는 UTF-8로 `replace` 해독하므로 한국어가 대체 문자(U+FFFD)가 되지만, 결과 요약은 앞 220자만 남기고 그 부분은 ASCII라 저장되는 요약은 같다. 자식까지 UTF-8로 쓰게 하는 것은 B에 없어 후속 후보로 남긴다 |
| G1 | 저장소 공통 규칙 | `jarvis.bat` 접근 없음, 사용자·시스템 환경변수와 Windows 설정 변경 없음(A안 아님), push 없음, 명시 파일만 stage |

## File ownership

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/worker/run_smoke_tests.py`, `adapters/discord/bot_minimal.py`, 이 기록 |
| deny | `jarvis.bat`, `orchestrator/worker/claude_worker.py`, `orchestrator/discord-intake/`, `apps/`, `docs/`, 다른 task 기록(task-0157 기록 정정 포함), 사용자·시스템 환경 설정 |

Docs 판정: `not_required`. 사용자 문서가 바뀌는 동작 변경이 아니다.

## 검증 계획

| # | 항목 |
| --- | --- |
| V1 | `PYTHONUTF8`·`PYTHONIOENCODING`을 지운 환경에서 Worker smoke 전체, Discord self-check suite, discord-intake smoke |
| V2 | `PYTHONUTF8=1`에서도 같은 세 가지(기존 통과 조건 유지) |
| V3 | SOP validator, Console smoke, `git diff --check`, 변경 범위 |
| V4 | 강도: 가짜 claude의 UTF-8 읽기를 빼면 설정 없는 Worker smoke가 실패, self-check 출력 UTF-8을 빼면 설정 없는 self-check가 실패, `or ""` 보호를 빼면 새 self-check 경우가 실패, smoke `git()`의 UTF-8 해독을 빼면 설정 없는 Worker smoke가 실패(Owner 결정 (1)) |
| V5 | 정리: 임시 worktree·listener 없음, `jarvis.bat` untracked |

## 구현 착수

2026-10-15 09:23 UTC에 Jarvis Console Start(Preview + Confirm, `START TASK`)로 `TODO→DOING`을 적용했다(Console 결과
`result_type: updated`, `TODO → DOING`, `no_execution: true`). 서버는 `--no-browser`로 띄운 뒤 소유 PID만 종료했다.

## 구현 중 escalation: 승인 목록으로 목표에 닿지 않음

B1~B3을 구현하자 설정 없는 Discord self-check는 통과했지만(93/0), 설정 없는 Worker smoke는 다른 곳에서 멈췄다. smoke의 `git()` 헬퍼
(`run_smoke_tests.py:132`)가 `text=True`에 `encoding` 없이 git 출력을 cp949로 해독해, `git show`의 한국어 glossary에서 해독 실패 →
`stdout` None → `.strip()` `AttributeError`가 났다. 가짜 claude 실패에 가려 있던 두 번째 원인이다. 소유 파일 안의 한 줄 수정이지만 B가 이름 붙인
세 변경 밖이라, SOP 3절(승인 목록이 승인 목표에 닿지 않으면 구현 전 질문)에 따라 멈추고 Owner에게 물었다. 소유 두 파일의 `text=True` 호출은
이것 하나가 남아 있었다.

Owner 결정 (원문):

```text
(1)로 진행해
```

(1)의 내용(Director 보고 원문):

```text
- **(1, 추천) 포함합니다.** smoke `git()` 헬퍼도 UTF-8로 해독하게 합니다. 소유 파일의 모든 `text=True` 호출을 확인했는데 남은 곳은 여기 하나입니다. 그다음 설정 없는 환경의 Worker smoke 통과를 확인하고, 이 수정을 빼면 다시 실패하는 변형도 추가합니다.
```

## 구현 (Implementer)

baseline `54eef73e282814151ab6c68ef427028cc3e886ca`.

| 파일 | 변경 |
| --- | --- |
| `orchestrator/worker/run_smoke_tests.py` | 가짜 claude가 읽기 전에 `sys.stdin.reconfigure(encoding="utf-8")`(B1). `git()` 헬퍼에 `encoding="utf-8", errors="replace"`(B5) |
| `adapters/discord/bot_minimal.py` | `_build_execution_result_real()`의 `subprocess.run`에 `encoding="utf-8", errors="replace"`, 결과 요약에 `completed.stdout or ""`, `completed.stderr or ""`(B3). `main()`의 `--self-check-suite`·`--self-check` 분기가 출력 전에 `sys.stdout.reconfigure(encoding="utf-8")`(B2). self-check에 `execution_output_utf8_and_none_safe` 추가: `subprocess.run`을 잠시 바꿔 `stdout`·`stderr`가 `None`인 결과를 돌려주고, 호출 인자가 `encoding="utf-8"`·`errors="replace"`이며 결과가 `executed`·`success`·`output_summary="no_output"`인지 확인(B4) |

## 검증 (Implementer 실행)

"설정 없음"은 `PYTHONUTF8`·`PYTHONIOENCODING`을 지운 환경이다.

| # | 항목 | 결과 |
| --- | --- | --- |
| V1 | 설정 없음: Worker smoke, Discord self-check, discord-intake | Worker smoke total=347 failed=0, 실행 뒤 추적 변경 없음. self-check total=93 실패 0(baseline은 이모지 출력 `UnicodeEncodeError`로 멈춤). intake total=133 failed=0 |
| V2 | `PYTHONUTF8=1`: 같은 세 가지 | Worker smoke 347/0, self-check 93/0, intake 133/0 |
| V3 | SOP validator, Console smoke, `git diff --check`, 범위 | validator PASS, Console smoke PASS, diff check 통과. 변경은 소유 두 파일과 이 기록 |
| V4 | 강도(임시 worktree, 설정 없음) | 가짜 claude UTF-8 읽기 제거 → Worker smoke 실패. self-check 출력 UTF-8 제거 → self-check `UnicodeEncodeError`. `or ""` 보호 제거 → 새 검사 `execution_output_utf8_and_none_safe`가 `"ok": false`(`AttributeError`). smoke `git()` UTF-8 제거 → Worker smoke `AttributeError`. 복구본 Worker smoke 347/0, self-check 통과 |
| V5 | 정리 | 임시 worktree 삭제, listener 없음, `jarvis.bat` untracked |

검증 메모:

- intake total이 baseline 132에서 133이 된 것은 intake의 task 기록 전수 검사에 이 기록(`repo_task_validation:task-0158-...`)이 하나 더해졌기
  때문이다. intake 코드는 바꾸지 않았다.
- `--self-check-suite`는 검사가 실패해도 종료 코드가 0이다(기존 동작). V4의 `or ""` 변형은 종료 코드가 아니라 JSON의 `"ok": false`로 확인했다.
- 범위 밖 관찰(수정하지 않음): smoke의 `check()`는 실패 detail을 출력하는데, 그 detail에 이모지(예: `❌`)가 있으면 설정 없는 cp949 콘솔에서
  출력 자체가 `UnicodeEncodeError`로 멈춘다. 통과하는 실행은 이모지를 출력하지 않아 영향이 없고, 실패는 종료 코드로 여전히 드러난다. 후속 후보다.

## Reviewer 결과 (candidate `3e8a33f163038eaf52c59935ec5bbe8015c11fa3`): FINDINGS

`self_deviations: []`, `unverified` 8건. findings 1건(minor): Owner 선택지 (1)의 "그다음 설정 없는 환경의 Worker smoke 통과를 확인하고, 이 수정을
빼면 다시 실패하는 변형도 추가합니다"를 Manager 요약 B5 행이 적지 않았고, 검증 계획 V4 행도 `git()` 변형을 빼고 세 변형만 적었다(결과 표에는 있음).

Manager 판정: 맞다. 이 기록 안의 수정이고 범위 확대가 아니므로 SOP 5절에 따라 repair budget 1을 써서 고친다(`repair_count` 0→1).

## repair 1

- Manager 요약 B5 행에 (1)의 두 조건(설정 없는 Worker smoke 통과 확인 V1, `git()` 수정을 빼는 변형 V4)을 적었다.
- 검증 계획 V4 행에 `git()` UTF-8 해독 제거 변형을 더했다.
- `updated_at`과 budget을 갱신했다. 코드는 바꾸지 않았다(candidate `3e8a33f`의 코드와 같다).

이 repair로 candidate가 바뀌므로 이전 Reviewer 결과는 무효이고 새 candidate에 Reviewer → QA를 다시 실행한다.
