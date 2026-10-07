# task-0153-console-smoke-checkout-independence

- id: `task-0153-console-smoke-checkout-independence`
- title: `Console smoke가 CRLF checkout과 C:/work 밖 worktree에서도 같은 강도로 통과하게 하기`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-10-07 12:55 UTC`
- updated_at: `2026-10-07 18:12 UTC`
- summary: `apps/jarvis-console/run_smoke_tests.py의 skills.json 바이트 비교가 core.autocrlf=true의 CRLF checkout에서 실패하고, task transition 검사가 저장소 위치를 C:/work로 가정해 실패한다. 작업 트리 CRLF가 index LF 위에 있고 core.autocrlf가 true·input일 때만 CRLF를 LF로 되돌려 비교하고 C:/work 가정을 지운다. 검사 강도는 유지한다. candidate 9bb2a4b가 Reviewer PASS와 QA PASS를 받았다. Reviewer·QA 기록을 최종 checkpoint commit으로 남기고 Console Complete로 마무리한다. push는 하지 않는다.`
- source_command: `Owner 지시: 권장 변형으로 task-0153 기록 작성하고 계획 먼저 보고`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `f18a42def3c52a8a36c4a8344f71e098ad165056` (main HEAD, push 전) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 계기 | task-0151, task-0152 QA에서 Console smoke를 `C:/work` 아래 LF checkout worktree로 옮겨 실행하는 우회가 필요했다 |
| 보존 대상 | task-0143 r3 worktree/branch(`e05c69c`), task-0149 worktree/branch 2개(`8f0c58e`, r2 `bd1622e`) |

## 조사 결과 (read-only, 코드와 실행 결과 기준)

1. `_test_tasks_reports_registry_copy()`(82행)는 기준 바이트를 `git show 064f82bf4806198a4e904e58b85c3c87a2ca8123:apps/jarvis-console/skills.json`
   (git 저장 내용, LF)으로, 비교 대상을 `registry_path.read_bytes()`(작업 트리 파일)로 읽는다. 시스템 gitconfig의
   `core.autocrlf=true`로 새로 checkout하면 이 파일은 `i/lf w/crlf`가 된다. 265~266행의 바이트 anchor에 `\n`이 들어 있어
   CRLF 파일에서 찾지 못하고 323행 `current_raw.count(...) == 1`이 실패하며, 이어지는 `restored_raw == baseline_raw`도
   CRLF/LF 차이로 실패할 수밖에 없다.
2. `_test_task_transition_vertical_slice()`(1959행)의 1962행 `resolved_workspace = Path("C:/work").resolve()`와 1964행
   `assert resolved_fixture.is_relative_to(resolved_workspace)`가 저장소 위치를 `C:/work` 아래로 가정한다. 1676·1691행의
   `"C:/work/..."`는 테스트 입력 데이터라 환경과 무관하다.
3. 의도(코드·주석 기준): ①은 commit `692a113`의 주석대로 승인된 문구만 바뀌고 다른 값·형식·공백은 기준 commit과 바이트 단위로
   같다는 copy-drift guard다. 작업 트리가 LF이길 요구하는 검사가 아니며, git은 이 파일을 LF로 저장한다(`i/lf`). ②의 실제 의도인
   "fixture가 저장소 바로 아래에 생긴다"는 바로 앞 1963행 `resolved_fixture.parent == run_web_app.REPO_ROOT.resolve()`가
   보장하고, `C:/work` 줄은 저장소 기준 경로 안전성과 무관한 위치 가정이다.
4. 재현(HEAD `f18a42d`, 새 worktree, 저장소 파일 수정 없음): scratchpad 기본(CRLF) worktree는 323행, `core.autocrlf=false`(LF)
   worktree는 1964행에서 실패했다. task-0151 QA에서 baseline `753e5db`도 같았다.
5. 실험(임시 worktree 안에 두 곳만 바꾼 사본을 따로 만들어 실행, 저장소 파일 수정 없음): CRLF·LF worktree(둘 다 `C:/work` 밖)
   모두 Console smoke 전체 PASS. `skills.json`에 형식만 바꾼 변경(공백), 빈 줄 추가, 줄 중간 CR을 넣으면 바꾼 registry 검사는
   CRLF·LF 양쪽에서 FAIL했고 원래 파일에서는 PASS였다. 원래 검사도 형식 변경·빈 줄에서 FAIL했다. 실험은 단순형(무조건 CRLF→LF)으로
   했다. 임시 worktree는 모두 지웠다.

## Owner 결정 (원문)

```text
권장 변형으로 task-0153 기록 작성하고 계획 먼저 보고해줘
```

"권장 변형"은 조사 보고의 ① 권장안이다: `git ls-files --eol` 결과가 `i/lf`이고 `w/crlf`일 때(설정에 의한 checkout 변환)만 CRLF를
LF로 되돌리고, 그 밖에는 원래처럼 원시 바이트로 비교한다. ②는 `C:/work` 두 줄 삭제다.

## 구현 착수와 계획 정정

Owner 지시("task-0153 Console Start 하고 구현 시작해줘")로 2026-10-07 16:55 UTC에 Jarvis Console Start(Preview + Confirm,
`START TASK`)로 `TODO→DOING`을 적용했다(Console 결과 `result_type: updated`, `TODO → DOING`, `no_execution: true`).

구현 뒤 검증 전에 계획의 전제 하나가 틀렸음을 확인했다. `git ls-files --eol`의 `w/crlf`는 작업 트리 파일 내용을 보고 판단하며
git 설정에 의한 변환인지와 무관하다. 임시 LF worktree에서 `skills.json`을 손으로 CRLF로 바꾸면 `core.autocrlf=false`로 조회해도
`i/lf w/crlf`였다. 그래서 `i/lf`+`w/crlf`만으로는 LF 환경의 미커밋 CRLF 변경을 잡지 못해, 원래 검증 계획 3번이 지켜지지 않는다.
검증을 멈추고 보고했고 Owner가 B안을 승인했다.

B안 승인 Owner 원문:

```text
B 승인합니다.

* 현재 구현 방향은 유지하되, `i/lf + w/crlf`인 경우 `core.autocrlf`가 `true` 또는 `input`인지 확인하도록 보강하세요.
* `autocrlf=true/input`이면 정상적인 Windows checkout 변환으로 보고 CRLF→LF 정규화를 적용합니다.
* `autocrlf=false`이면 작업 트리의 CRLF를 비정상 변경으로 보고 원시 비교에서 FAIL시키세요.
* git 설정 조회 실패, 예상하지 못한 값, 명령 실패 등은 모두 fail-closed로 처리하세요.
* `.gitattributes`는 이번 task에서는 판정에 포함하지 않습니다.
* task-0153의 검증 계획/기록도 이 기준에 맞게 정정하세요.
* 그 후에만 검증을 진행하세요.
* 검증은 최소한 CRLF checkout / LF checkout / LF 환경에서 수동 CRLF 변경을 포함해서 기존 검사 강도가 유지되는지 확인하세요.
* `C:/work` 의존성 제거도 함께 확인하세요.
* `jarvis.bat`은 건드리지 말고, push도 하지 마세요.
* 검증 완료 후 바로 DONE 처리하지 말고 candidate → Reviewer → QA 순서로 진행하고 결과를 보고하세요.
```

## 변경 계획 (B안으로 정정)

| 파일 | 함수 | 변경 |
| --- | --- | --- |
| `apps/jarvis-console/run_smoke_tests.py` | `_test_tasks_reports_registry_copy()` | `current_raw = registry_path.read_bytes()` 뒤에 `git ls-files --eol -- <relative_registry_path>`를 `REPO_ROOT`에서 실행해 index·작업 트리 eol을 읽는다. `i/lf`이고 `w/crlf`이면 `git config --get core.autocrlf`를 읽어 `true`·`input`(대소문자 무시)일 때만 `current_raw.replace(b"\r\n", b"\n")` 뒤 `assert b"\r" not in current_raw`. `false`이거나 설정이 없으면(git 기본값 false, exit 1·출력 없음) 원시 바이트 그대로 비교해 실패한다. 그 밖(`w/lf`, `i/crlf` 등)도 원시 비교. 명령 실패, 출력 형식 이상, `true`·`input`·`false` 밖의 값은 assert로 실패(fail-closed). `.gitattributes`는 판정에 넣지 않는다. 나머지 비교 코드는 변경 없음 |
| 〃 | `_test_task_transition_vertical_slice()` | 1962·1964행(`C:/work` 정의와 assert)만 삭제. 1963행 `parent == REPO_ROOT`, 1965행 `not fixture_root.exists()`, 스냅샷·정리 검사는 그대로 |
| 이 기록 | — | 계획·결정·구현·검증 기록 |

예상 규모: `run_smoke_tests.py` 약 30줄(B안 보강 포함). Console 코드, `skills.json`, 다른 smoke, SOP·task-model·validator·Worker·bot은 바꾸지 않는다.

## 검증 계획 (B안으로 정정)

1. Console smoke 전체 PASS를 세 환경에서 확인: 메인 작업 트리(`C:/work`, LF), `C:/work` 밖 CRLF checkout worktree
   (`core.autocrlf=true`), `C:/work` 밖 LF checkout worktree. 두 worktree가 `C:/work` 밖이므로 `C:/work` 의존 제거도 함께 확인한다.
2. 강도 회귀(임시 worktree에서 `skills.json`을 바꿔 registry 검사만 실행): 형식만 바꾼 변경, 빈 줄 추가, 줄 중간 CR은 CRLF·LF
   양쪽에서 FAIL, 원래 파일은 PASS.
3. LF 환경(`core.autocrlf=false`)에서 손으로 바꾼 CRLF: 그 실행의 git 설정을 `core.autocrlf=false`로 두고 `skills.json`을 CRLF로
   바꾸면 registry 검사가 FAIL(원시 비교). 같은 파일을 `core.autocrlf=true`·`input`으로 두면 PASS.
4. fail-closed: `core.autocrlf`가 `true`·`input`·`false` 밖의 값이면 registry 검사가 FAIL.
5. 기존 검사: Worker smoke, Discord self-check, discord-intake smoke, SOP validator, `git diff --check`, 변경 범위.

## 완료 조건

1. Console smoke가 `C:/work` 밖 CRLF·LF worktree와 메인 작업 트리에서 모두 PASS한다.
2. registry 검사가 위 강도 회귀 변형을 모두 FAIL로 잡고, `core.autocrlf=false` 환경의 CRLF 변경과 예상 밖 설정값도 FAIL로 잡는다.
3. `parent == REPO_ROOT`, fixture 미존재, 스냅샷·정리 검사가 그대로다.
4. 변경은 `run_smoke_tests.py`의 두 함수와 이 기록뿐이고 기존 검사 4번이 모두 PASS한다.

## 범위 밖

- Console 앱 코드, `skills.json`, 기준 commit(`064f82b`)과 승인 문구 목록 변경
- 다른 smoke·self-check의 경로·줄 끝 처리 변경
- `core.autocrlf` 등 git 설정이나 `.gitattributes` 추가
- registry 비교 로직의 함수 분리나 영구 메모리 음성 테스트 추가(Owner가 따로 정하면 별도로)
- commit, DONE, push, `jarvis.bat`

## 구현 (Implementer)

baseline `f18a42def3c52a8a36c4a8344f71e098ad165056`. B안 승인("candidate → Reviewer → QA 순서로 진행")에 따라 이 기록과 함께
candidate commit에 기록한다.

| 파일 | 변경 |
| --- | --- |
| `apps/jarvis-console/run_smoke_tests.py` | `_test_tasks_reports_registry_copy()`: `git ls-files --eol`로 index·작업 트리 eol을 읽고, `i/lf`+`w/crlf`이면 `git config --get core.autocrlf`가 `true`·`input`일 때만 CRLF→LF 뒤 `b"\r"` 없음 확인. `false`·설정 없음(exit 1, 출력 없음)은 원시 비교. 명령 실패·형식 이상·그 밖의 값은 assert로 실패. `_test_task_transition_vertical_slice()`: `C:/work` 두 줄 삭제(`parent == REPO_ROOT`, fixture 미존재 검사 유지) |

규모: 1개 파일 34 추가, 2 삭제.

## 검증 (Implementer 실행)

| # | 항목 | 결과 |
| --- | --- | --- |
| V1 | Console smoke 전체 | PASS: 메인 작업 트리(`C:/work`, LF), `C:/work` 밖 CRLF checkout worktree(`i/lf w/crlf`, 저장소 설정 `core.autocrlf=true`), `C:/work` 밖 LF checkout worktree(`i/lf w/lf`). 두 worktree에는 수정한 `run_smoke_tests.py`를 넣었다. `C:/work` 밖에서 통과하므로 경로 의존 제거도 확인 |
| V2 | 강도 회귀(registry 검사만) | CRLF·LF worktree 양쪽에서 형식만 바꾼 변경(공백)·빈 줄 추가·줄 중간 CR은 FAIL, 원래 파일은 PASS |
| V3 | LF checkout에서 손으로 바꾼 CRLF(`i/lf w/crlf`) | `core.autocrlf=false` FAIL, 설정 없음 FAIL, `true` PASS, `input` PASS. 실행별 git 설정은 환경 변수(`GIT_CONFIG_COUNT`, `GIT_CONFIG_NOSYSTEM`)로 지정 |
| V4 | fail-closed | 같은 CRLF 파일에서 `core.autocrlf=weird`, `yes`는 FAIL |
| V5 | 기존 검사 | Worker smoke 310/310, Discord self-check 92/92, discord-intake 128/128(failed 0), SOP validator PASS(negative 129), `git diff --check` exit 0(`--stat`과 `--ignore-cr-at-eol --stat` 같음) |
| V6 | 범위·정리 | 변경은 `run_smoke_tests.py`와 이 기록. 임시 worktree 2개 삭제, 보존 worktree 3개 그대로, `jarvis.bat` untracked |

검증 메모: V3 첫 실행은 LF worktree에서 파일을 되돌릴 때 쓴 `git checkout`이 저장소 설정(`core.autocrlf=true`)대로 CRLF로 풀어,
그 위에 CRLF 변환을 다시 해 `\r\r\n`(`w/-text`)이 생겼다. LF worktree의 되돌리기를 `git -c core.autocrlf=false checkout`으로
바꿔 V2(LF 쪽)와 V3·V4를 다시 실행했고 위 표는 다시 실행한 결과다. `core.autocrlf`의 git 불리언 별칭(`yes`, `on`, `1` 등)은
B안의 "예상하지 못한 값"으로 보고 실패시킨다.

## Reviewer 결과 (candidate `9bb2a4be149ac4b4e04503d5f2be3b9443d7c835`): PASS

baseline `f18a42def3c52a8a36c4a8344f71e098ad165056`, 2개 파일. `findings: []`, `self_deviations: []`. `unverified` 14건은 모두
실행이 필요한 항목(Console smoke 세 환경, 강도 회귀, LF 환경 수동 CRLF, fail-closed, Worker smoke, Discord self-check, intake,
validator, diff check, worktree 정리, Console Start 시점)이며 아래 QA에서 확인했다(Console Start 시점은 위 "구현 착수" 절의
Console 결과가 근거).

## QA 결과 (candidate `9bb2a4be149ac4b4e04503d5f2be3b9443d7c835`)

candidate를 그대로 checkout한 환경에서만 실행했다(복사한 파일 없음). QA 전·후 candidate와 main HEAD가 같았다.

| # | 검사 | 결과 |
| --- | --- | --- |
| Q1 | Console smoke, 메인 작업 트리(`C:/work`, LF, HEAD=candidate, 깨끗함) | PASS |
| Q2 | Console smoke, `C:/work` 밖 CRLF checkout worktree(`i/lf w/crlf`, `core.autocrlf=true`) | PASS |
| Q3 | Console smoke, `C:/work` 밖 LF checkout worktree(`i/lf w/lf`) | PASS |
| Q4 | 강도 회귀(registry 검사만) | 두 worktree 모두 형식 변경(공백)·빈 줄 추가·줄 중간 CR은 FAIL, 원래 파일은 PASS. CRLF worktree의 줄 중간 CR은 `\r\r\n`이 되어 `w/-text`로 읽혀 원시 비교로 실패했다 |
| Q5 | LF checkout에서 손으로 바꾼 CRLF(`i/lf w/crlf`) | `core.autocrlf=false` FAIL, 설정 없음 FAIL, `true` PASS, `input` PASS |
| Q6 | fail-closed | `core.autocrlf=weird`, `yes` FAIL |
| Q7 | Worker smoke(LF worktree) | 310/310 PASS |
| Q8 | Discord self-check | 92/92 PASS |
| Q9 | discord-intake smoke | 128/128, failed=0 |
| Q10 | SOP validator | PASS, negative_checks=129, negative_failures=0 |
| Q11 | `git diff --check f18a42d 9bb2a4b` | exit 0 |
| Q12 | 범위 | commit 1개, 2개 파일(M `run_smoke_tests.py`, A 이 기록). `jarvis.bat`은 candidate tree와 어떤 commit에도 없음 |

정리: QA worktree 2개를 지웠고 목록에서 사라졌다. 보존 worktree 3개는 그대로다. 서버·listener 없음. `jarvis.bat` untracked.

QA 중 발견(이번 task 범위 밖, 수정하지 않음): 임시 디렉터리(`%TEMP%`)에 Worker smoke가 남긴 `jarvis_worker_smoke_*` 48개와
`jarvis_qa0151_*` 1개가 남아 있다(2026-09-24부터, 하나당 최대 약 31MB). Windows 파일 잠금으로 `shutil.rmtree(..., ignore_errors=True)`가
조용히 남긴 것으로 보인다. 정리와 재발 방지는 후속 후보다.

## Owner 마무리 결정 (원문)

```text
QA PASS 확인했습니다. TEMP cleanup 문제는 이번 task 범위 밖으로 두고 후속 task 후보로만 기록하세요. 지금은 task-0153을 마무리합니다.

1. 현재 QA 결과와 Owner 결정이 task-0153 기록에 모두 반영됐는지 확인
2. task 기록만 최종 checkpoint commit
3. Console Complete Preview 실행
4. Preview 확인 후 `COMPLETE TASK` Confirm
5. DOING → DONE 전환
6. DONE 상태/updated_at 기록을 별도 checkpoint commit
7. 최종 `git status`에서 `?? jarvis.bat`만 남는지 확인
8. push하지 마세요.

TEMP의 `jarvis_worker_smoke_*` / `jarvis_qa0151_*`는 삭제하지 말고 후속 task 후보로 남기세요. `jarvis.bat`도 건드리지 마세요.
```

## 후속 task 후보 (이번 task에서 다루지 않음)

- 임시 디렉터리 잔여물: `%TEMP%`의 `jarvis_worker_smoke_*` 48개와 `jarvis_qa0151_*` 1개(2026-09-24부터, 하나당 최대 약 31MB). Windows
  파일 잠금으로 `shutil.rmtree(..., ignore_errors=True)`가 조용히 남긴 것으로 보인다. Owner 결정대로 삭제하지 않았고, 정리와 재발 방지는
  후속 task 후보다.

## 다음 단계

status는 `DOING`이다. candidate `9bb2a4be149ac4b4e04503d5f2be3b9443d7c835`는 Reviewer PASS, QA PASS다. Owner 마무리 결정에 따라 이 기록을
최종 checkpoint commit으로 남기고, 이어서 Jarvis Console Complete(Preview + Confirm `COMPLETE TASK`)로 `DOING→DONE`을 적용해
그 변경을 별도 checkpoint commit으로 남긴다. push는 하지 않는다.
