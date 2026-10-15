# task-0159-worker-smoke-harness-reliability

- id: `task-0159-worker-smoke-harness-reliability`
- title: `Worker smoke 하네스 신뢰성: 빈 worktree 경로 방어, cp949 파이프 출력, 읽기 전용 Git 객체 포함 임시 폴더 정리`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-10-15 14:00 UTC`
- updated_at: `2026-10-15 15:14 UTC`
- summary: `Worker smoke는 앞선 경우가 worktree 생성 전에 실패하면 빈 worktree 경로가 현재 폴더가 되어 원본 checkout의 glossary.json을 고칠 수 있고, cp949 파이프 출력에서 실패 상세의 이모지 때문에 출력이 멈추며, 읽기 전용 Git 객체 때문에 임시 폴더가 지워지지 않고 쌓인다. 쓰기 전에 attempt 경로가 비어 있지 않고 임시 worktrees 아래인지 확인하고, stdout을 UTF-8로 맞추며, 읽기 전용 파일까지 지우고 실패 시 경고하도록 orchestrator/worker/run_smoke_tests.py만 고친다. push는 하지 않는다.`
- source_command: `Owner 결정: A. Worker smoke 하네스 신뢰성 개선 진행`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `ee7deb88fc2676f2c9145708f4802ad8bcf5379e` (main HEAD = origin/main) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 환경 | Windows ACP 949, Python 3.12.10, 기본 인코딩 `cp949`, `PYTHONUTF8`·`PYTHONIOENCODING` 미설정 |
| `%TEMP%` 기존 잔여물 | `jarvis_worker_smoke_*` 39개, 약 98.5MB (삭제하지 않음) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` |

## 조사 결과 (read-only, 정적 분석과 목록 확인 기준. smoke는 실행하지 않음)

1. 빈 worktree 경로: `run_smoke_tests.py:833-837`이 `prev_wt = Path(exhausted.worktree)`의 `apps/studyroom/content/glossary.json`을
   읽고 `resumed-term`을 더해 다시 쓴다. `WorkerRunResult.worktree` 기본값은 `""`(`claude_worker.py:103`)이고 worktree를 만든 뒤에야
   채워진다(`:748`). 앞선 `repairexhausted` 실행이 그 전에 실패하면 `Path("")`는 `.`(현재 폴더)이고, 저장소 루트에서 실행하면 원본의
   추적 파일을 고친다. task-0157 QA의 baseline·변형 실행에서 원본에 ` M apps/studyroom/content/glossary.json`이 생긴 것이 실제 사례다.
   `accept_flow`의 `wt = Path(attempt.worktree)`(`:394`)도 뒤에서 쓰기와 `git commit`·`reset --hard`를 하지만, 빈 값이면 그 전에
   `rev-parse "^"`·`update-ref -d refs/heads/`·`with_name`(`ValueError`)에서 먼저 멈춘다.
2. cp949 출력: `check()`(`:126-128`)는 실패 시 상세를 `print`하고 stdout 인코딩을 정하지 않는다. 봇 응답 이모지 12종은 cp949로 인코딩되지
   않는다. 출력이 파이프·파일일 때 실패 상세에 이모지가 있으면 `UnicodeEncodeError`로 멈춰 이후 FAIL 줄과 마지막 요약
   (`total=… failed=…`, `:978`)이 나오지 않는다(task-0158 QA V4a에서 `'\\u274c'`로 실제 발생). 대화식 콘솔은 UTF-16 콘솔 API라 해당 없음.
3. 임시 폴더: `:710` `tempfile.mkdtemp(prefix="jarvis_worker_smoke_")`, `:974-975` `shutil.rmtree(tmp, ignore_errors=True)`. 남은 폴더의
   파일은 모두 읽기 전용 `repo\\.git\\objects\\…`(가장 최근 폴더 282개 전부)이고, Windows에서 `rmtree`가 지우지 못한 것을
   `ignore_errors=True`가 숨긴다.

## Owner 결정 (원문)

```text
Owner 결정: A. Worker smoke 하네스 신뢰성 개선을 진행합니다.
조사한 범위 안에서 정식 SOP에 따라 task를 등록하고, Console Start Preview를 먼저 제시해 주세요. 아직 구현을 시작하지 말고, Preview와 task 범위를 보고한 뒤 멈춰 주세요.
승인된 범위:

1. `repairexhausted` 등 사전 단계 실패 시 빈 worktree 경로가 원본 checkout을 가리키지 않도록 방어
2. CP949 환경에서 smoke 실패 상세와 최종 요약 출력이 중단되지 않도록 처리
3. smoke가 생성한 임시 디렉터리의 읽기 전용 Git 객체를 포함해 정리하고, 정리 실패 시 경고 제공

필수 검증:

* 실패 경로에서 원본 checkout의 추적 파일과 Git 상태가 변경되지 않을 것
* 임시 worktree 경로가 비어 있거나 허용된 임시 루트 밖이면 쓰기를 건너뛸 것
* UTF-8 환경변수 없이 파이프 출력에서도 실패 상세와 최종 요약이 출력될 것
* smoke 종료 후 이번 실행이 만든 임시 디렉터리가 제거될 것
* 관련 mutation 테스트가 종료 코드만이 아니라 실제 검사 결과를 확인할 것

제약:

* 기존 `%TEMP%\jarvis_worker_smoke_*` 폴더 39개는 삭제하지 마세요.
* `--self-check-suite`의 종료 코드 정책은 변경하지 마세요.
* `bot_minimal.py`, master-plan 등 승인 범위 밖의 파일은 수정하지 마세요.
* `jarvis.bat`은 읽기·수정·스테이징·커밋하지 마세요.
* 구현 전 Console Start Preview를 제시하고 멈추세요. Owner가 정식 시작을 승인한 뒤에만 구현합니다.
* push는 별도 승인 사항입니다.
```

## Manager 요약

| # | 승인 조건 | Manager 해석과 충족 방법 |
| --- | --- | --- |
| P0 | 정식 SOP task 등록, Console Start Preview를 먼저 제시하고 멈춤, Owner의 정식 시작 승인 뒤에만 구현 | 이 기록을 `TODO`로 만들고 Start Preview만 요청한다. Confirm(`START TASK`)과 구현은 Owner 승인 뒤 |
| S1 | 사전 단계 실패 시 빈 worktree 경로가 원본 checkout을 가리키지 않도록 방어 | attempt worktree 경로를 확인하는 함수를 둔다: 비어 있지 않고, 해석한 경로가 이번 실행의 임시 `worktrees` 루트 아래이며, 존재할 것. resume 블록(`prev_wt`)과 `accept_flow`의 `wt`가 쓰기 전에 이 확인을 거친다 |
| S2 | cp949에서 실패 상세와 최종 요약 출력이 중단되지 않게 | smoke `main()` 시작에서 stdout(과 stderr)을 UTF-8(`errors="backslashreplace"`)로 맞춘다 |
| S3 | 임시 디렉터리를 읽기 전용 Git 객체 포함해 정리, 실패 시 경고 | `shutil.rmtree`에 읽기 전용 속성을 풀고 다시 지우는 처리를 넣고(`ignore_errors` 대신), 그래도 남으면 경로와 함께 경고를 출력한다 |
| V1 | 실패 경로에서 원본 checkout의 추적 파일과 Git 상태 불변 | QA에서 worktree 생성 전 실패를 일으키는 변형으로 smoke를 실행하고 원본 `git status`·HEAD·추적 파일 해시가 실행 전과 같은지 확인 |
| V2 | 경로가 비어 있거나 임시 루트 밖이면 쓰기 건너뜀 | 확인 함수가 빈 경로·임시 루트 밖 경로를 거절하는지 smoke 안 검사로 확인하고, 거절 시 해당 check가 FAIL로 기록되는지 확인 |
| V3 | UTF-8 환경변수 없이 파이프 출력에서도 실패 상세와 최종 요약 출력 | `PYTHONUTF8`·`PYTHONIOENCODING`을 지우고 출력을 파이프로 받는 상태에서, 이모지가 든 실패 상세를 만드는 변형으로 실행해 FAIL 줄과 `total=… failed=…` 요약이 나오는지 확인 |
| V4 | smoke 종료 후 이번 실행이 만든 임시 디렉터리 제거 | 실행 전후 `%TEMP%\jarvis_worker_smoke_*` 목록을 비교해 새 폴더가 남지 않는지 확인(기존 39개는 그대로) |
| V5 | mutation 테스트가 종료 코드만이 아니라 실제 검사 결과 확인 | 각 변형에서 종료 코드와 함께 해당 FAIL 줄 이름, 요약의 failed 수, 원본 상태를 직접 확인한다 |
| X1 | 기존 `%TEMP%\jarvis_worker_smoke_*` 39개 삭제 금지 | 정리는 이번 실행이 만든 `tmp`에만 적용한다 |
| X2 | `--self-check-suite` 종료 코드 정책 변경 금지 | `bot_minimal.py`를 바꾸지 않는다 |
| X3 | `bot_minimal.py`, master-plan 등 범위 밖 파일 수정 금지 | 소유 파일은 `orchestrator/worker/run_smoke_tests.py`와 이 기록뿐 |
| X4 | `jarvis.bat` 금지, push 별도 승인 | 접근하지 않고 push하지 않는다 |

## File ownership

| 구분 | 경로 |
| --- | --- |
| owned | `orchestrator/worker/run_smoke_tests.py`, 이 기록 |
| deny | `jarvis.bat`, `adapters/discord/bot_minimal.py`, `orchestrator/worker/claude_worker.py`, `docs/master-plan.md`, 다른 task 기록, `%TEMP%`의 기존 `jarvis_worker_smoke_*` 39개 |

Docs 판정: `not_required`. 테스트 하네스 내부 변경이다.

## 검증 계획

| # | 항목 |
| --- | --- |
| T1 | 설정 없음(`PYTHONUTF8`·`PYTHONIOENCODING` 제거)과 `PYTHONUTF8=1` 각각에서 Worker smoke 전체 통과, 실행 뒤 원본 추적 변경 없음 |
| T2 | V1·V2: worktree 생성 전 실패 변형에서 원본 불변, 해당 check FAIL 기록 |
| T3 | V3: 설정 없음 + 파이프 출력 + 이모지 실패 상세 변형에서 FAIL 줄과 최종 요약 출력, 종료 코드 1 |
| T4 | V4: 실행 전후 `jarvis_worker_smoke_*` 목록 비교, 이번 실행분 미잔존 |
| T5 | V5: 각 변형의 FAIL 이름·failed 수·원본 상태를 직접 확인. 수정을 빼는 변형(경로 확인 제거, UTF-8 출력 제거, 읽기 전용 정리 제거)이 각각 실패로 드러나는지 |
| T6 | Discord self-check, discord-intake, SOP validator, Console smoke, `git diff --check`, 변경 범위 |

## 구현 착수

2026-10-15 14:02 UTC에 Jarvis Console Start(Preview + Confirm, `START TASK`)로 `TODO→DOING`을 적용했다(Console 결과
`result_type: updated`, `TODO → DOING`, `no_execution: true`). Owner 원문: "task-0159 Console Start 진행하고 구현 시작해줘".
서버는 `--no-browser`로 띄운 뒤 소유 PID만 종료했다.

## 구현 (Implementer)

baseline `ee7deb88fc2676f2c9145708f4802ad8bcf5379e`. 변경 파일은 `orchestrator/worker/run_smoke_tests.py` 하나다.

| # | 변경 |
| --- | --- |
| S1 | `attempt_path(worktree, worktrees)` 추가: 비어 있지 않고, 해석한 경로가 이번 실행의 임시 `worktrees` 루트 아래이며, 폴더로 존재할 때만 경로를 돌려주고 그 밖에는 `None`. resume 블록은 `prev_wt`가 `None`이면 `resume: the exhausted run left an attempt worktree under the temp root`를 FAIL로 기록하고 쓰기와 그 뒤 resume 검사를 건너뛴다. `accept_flow`는 `wt`가 `None`이면 `accept setup: the owner-review attempt worktree is under the temp root`를 FAIL로 기록하고 반환한다. 확인 함수 자체의 검사 4개(실제 attempt 수락, 빈 경로 거절, 저장소·clone 경로 거절, 없는 경로 거절)를 더했다 |
| S2 | `main()` 시작에서 stdout·stderr를 `encoding="utf-8", errors="backslashreplace"`로 맞춘다 |
| S3 | `remove_tree(path)` 추가: `shutil.rmtree`의 `onexc`(3.12 미만은 `onerror`)에서 `os.chmod(target, stat.S_IWRITE)` 뒤 다시 지우고, 그래도 남으면 `WARNING:` 줄을 출력한다. `finally`가 `ignore_errors=True` 대신 이 함수를 쓰고, 그 결과를 `cleanup: this run's temporary directory is removed` 검사로 기록한다. 대상은 이번 실행의 `tmp`뿐이다 |

읽기만 하는 `Path(...worktree).exists()` 검사 3곳(`refused()`, success 정리, retry 보존)은 쓰기가 아니라 바꾸지 않았다.

## 검증 (Implementer 실행)

"설정 없음"은 `PYTHONUTF8`·`PYTHONIOENCODING`을 지운 환경이다. 출력은 모두 파이프로 받았다.

| # | 항목 | 결과 |
| --- | --- | --- |
| T1 | Worker smoke 정상 실행 | 설정 없음 total=354 failed=0, `PYTHONUTF8=1` total=354 failed=0(기존 347 + 새 검사 7). WARNING 줄 없음. 실행 뒤 원본 추적 변경 없음 |
| T2 | V1·V2(변형 A, 수정 유지): `exhausted.worktree`를 `""`로 둠 | 종료 1, `total=349 failed=1`, FAIL은 `resume: the exhausted run left an attempt worktree under the temp root` 하나. 원본 checkout의 HEAD·status·`glossary.json` 해시 불변 |
| T2' | 변형 A'(같은 상황 + 경로 확인 제거) | 종료 1, `total=354 failed=1`, 원본 `glossary.json` 해시 `d918ba4e…` → `c059c1d0…`, status에 ` M apps/studyroom/content/glossary.json`. 수정이 없으면 원본을 고치는 것이 재현됨(변형 실행 뒤 복구) |
| T3 | V3(변형 B, 수정 유지): `check("mutation: emoji failure detail", False, "❌ ✅ 🧾")` | 종료 1, FAIL 줄과 `total=355 failed=1` 출력, 크래시 없음 |
| T3' | 변형 B'(같은 상황 + UTF-8 stdout 제거) | 요약 없이 `UnicodeEncodeError … '❌'`로 멈춤 |
| T4 | V4: 실행 전후 `%TEMP%\jarvis_worker_smoke_*` | 정상 실행 두 번 모두 전 39·후 39, 새로 남은 폴더 0. 변형 C'(읽기 전용 정리 제거, `ignore_errors=True`)는 폴더 1개가 남고 `cleanup: this run's temporary directory is removed`가 FAIL(`total=354 failed=1`). 그 폴더는 이번 실행분이라 지웠고 기존 39개는 그대로 |
| T5 | V5 | 위 변형마다 종료 코드와 함께 요약 줄, FAIL 검사 이름, 원본 HEAD·status·해시, 임시 폴더 목록을 직접 확인했다. 변형은 임시 worktree(현재 폴더 = 그 worktree)에서만 적용했고 실행 뒤 지웠다 |
| T6 | 그 밖 | Discord self-check 설정 없음·`PYTHONUTF8=1` 모두 ok 93/0, intake 134/0(이 기록의 task 기록 검사가 더해져 133→134), SOP validator PASS, Console smoke PASS, `git diff --check` 통과. 변경은 소유 파일과 이 기록 |
