# task-0169-manager-summary-quote-check

- id: `task-0169-manager-summary-quote-check`
- title: `Reviewer 호출 전 Manager 요약의 승인 원문 인용 누락을 결정론적으로 확인하는 검사 추가`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-10-19 09:32 UTC`
- updated_at: `2026-10-19 09:58 UTC`
- summary: `Reviewer가 Manager 요약에 빠진 Owner 조건을 지적해 repair, repair 예산 증액, SOP 8 수용으로 이어진 일이 task-0133~0168 기록 17건에 남아 있다. 같은 비교를 Reviewer 호출 전에 결정론적으로 하는 읽기 전용 스크립트 scripts/check_summary_quotes.py와 self-test를 더하고, SOP 3 Manager 항목과 jarvis-reviewer-call Skill 3단계가 이를 먼저 실행하게 한다. 참고 자료이며 gate나 판정이 아니다. candidate c7ff349 Reviewer PASS, QA PASS. DONE은 Owner Console Complete 대기. push 없음.`
- source_command: `Owner 요청: Jarvis-Core 다음 개발 과제 발굴 및 실행 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `1c49b2f6b6193455804c7007f44171f7fe6c8352` (main HEAD = origin/main) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat`, `memory/tasks/task-0166-studyroom-glossary-r1-1.md`(보존, 건드리지 않음) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (기본값) |

## Owner 요청 (원문)

이 세션의 Owner 요청 중 이 task의 범위·제한을 정하는 부분을 그대로 옮긴다.

```text
Jarvis가 Owner의 반복 지시 없이도 작업을 계획하고, 실행하고, 검증하고, 실패를 복구하고, 결과를 보고하는 수준에 가까워지도록 개선한다.
가장 효과가 큰 과제 하나를 선정하고, 선정 이유와 변경 범위를 간단히 기록한 다음 진행한다.
안전하고 범위가 명확하다면 Owner에게 계획 승인만 요청하고 멈추지 말고, 현재 권한과 프로젝트 정책 안에서 구현까지 진행한다.
최소 diff 원칙을 지킨다.
기존 기능을 불필요하게 재작성하지 않는다.
관련 테스트를 실행하고 회귀 여부를 확인한다.
실패하면 원인을 분석하고 허용된 범위에서 수정 후 재검증한다.
문서와 master-plan은 실제 구현 결과에 맞춰 갱신한다.
프로젝트의 공식 task 완료 절차를 따른다.
task 상태를 임의로 DONE으로 바꾸지 않는다.
커밋은 프로젝트의 checkpoint 정책에 따른다.
`git push` 금지. 원격 반영은 별도 승인 후 진행한다.
`jarvis.bat`은 열기·수정·삭제하지 않는다.
기존 미커밋 변경사항을 덮어쓰거나 임의로 폐기하지 않는다.
Discord 토큰, API 키 등 비밀정보를 출력하지 않는다.
```

2026-10-19 09:32 UTC 등록과 함께 `DOING`(위 요청이 구현 착수를 승인한다).

## 조사 결과 (read-only, 등록 전 확인)

1. Reviewer FINDINGS 가운데 "Manager 요약에 Owner 조건 X가 없음/인용되지 않음" 유형이 task-0133~0168 기록 17건에 남아 있다
   (0133, 0134, 0135, 0136, 0138, 0139, 0141, 0142, 0144, 0145, 0147, 0148, 0160, 0161, 0163, 0164, 0168 — 기록 본문 검색 기준, 건수는 근사).
   예: task-0161 Reviewer 1 major 2·Reviewer 2 minor 2·Reviewer 3 minor 1, task-0164 Reviewer 3 minor 3, task-0168 2차 minor 1.
2. 그 지적은 매번 기록만 고치는 repair, Owner의 repair 예산 증액(task-0156·0157·0160·0161: 2회, task-0167: 3회),
   또는 Owner의 SOP §8 수용(task-0161·0164·0167·0168)으로 처리됐다. master-plan은 task-0164 항목에서 이를 "task-0160~0164 내내
   반복된 SOP 운영 문제"로 남겼다.
3. 현재 대비책은 `jarvis-reviewer-call` Skill 3단계의 모델 비교뿐이며 결정론적 검사는 없다.
   `scripts/`에 같은 형태의 읽기 전용 검사(`check_no_secrets.py`, `--self-test`)가 있다.
4. 기록 형식: Owner 원문은 제목에 `원문`(또는 `verbatim`)이 있는 절의 펜스 블록에 있고, 요약은 `## Manager 요약`
   (`(원문 해석)`, `(승인 원문 조건별)` 접미사 포함) 절에 있다(task-0130 이후 기록 19건).
5. Worker 파이프라인 경로(`claude_worker.py`)의 실제 실패는 task-0143(Reviewer 내용 지적)과 task-0166(R1 검증용 짧은 timeout,
   이후 봇 중단)뿐이고 일시적 인프라 실패의 기록은 없어, 자동 재시도는 근거가 약해 선정하지 않았다.

## 선정 이유

Owner 개입을 실제로 반복해서 만든 지점이다(조사 1·2). 기존 정책과 판정 권한(Reviewer)을 바꾸지 않고, Manager가 Reviewer를
부르기 전에 고칠 수 있게만 한다. 결정론적 self-test와 과거 기록 재현으로 효과를 확인할 수 있다.

## Manager 요약

| # | Owner 원문 | Manager 해석 |
| --- | --- | --- |
| M1 | "Jarvis가 Owner의 반복 지시 없이도 작업을 계획하고, 실행하고, 검증하고, 실패를 복구하고, 결과를 보고하는 수준에 가까워지도록 개선한다." / "가장 효과가 큰 과제 하나를 선정하고, 선정 이유와 변경 범위를 간단히 기록한 다음 진행한다." | 반복 Owner 개입(요약 인용 지적) 하나를 줄이는 과제를 고르고 근거·범위를 이 기록에 적는다 |
| M2 | "안전하고 범위가 명확하다면 Owner에게 계획 승인만 요청하고 멈추지 말고, 현재 권한과 프로젝트 정책 안에서 구현까지 진행한다." | 등록과 함께 DOING, 구현·candidate·Reviewer·QA까지 진행 |
| M3 | "최소 diff 원칙을 지킨다." / "기존 기능을 불필요하게 재작성하지 않는다." | 새 스크립트 1개와 SOP 한 항목, Skill 3단계 문단·도구 허용 1개만. 기존 코드·validator 무변경 |
| M4 | "관련 테스트를 실행하고 회귀 여부를 확인한다." / "실패하면 원인을 분석하고 허용된 범위에서 수정 후 재검증한다." | self-test, 과거 기록 재현, SOP validator, `check_no_secrets`, `git diff --check` |
| M5 | "문서와 master-plan은 실제 구현 결과에 맞춰 갱신한다." | SOP·Skill은 candidate에, master-plan은 QA 뒤 별도 commit으로 결과와 DONE 대기 상태를 적는다 |
| M6 | "프로젝트의 공식 task 완료 절차를 따른다." / "task 상태를 임의로 DONE으로 바꾸지 않는다." / "커밋은 프로젝트의 checkpoint 정책에 따른다." | candidate commit → Reviewer → QA → QA 기록 checkpoint. DONE은 Owner Console Complete |
| M7 | "`git push` 금지. 원격 반영은 별도 승인 후 진행한다." / "`jarvis.bat`은 열기·수정·삭제하지 않는다." / "기존 미커밋 변경사항을 덮어쓰거나 임의로 폐기하지 않는다." / "Discord 토큰, API 키 등 비밀정보를 출력하지 않는다." | push 없음, `jarvis.bat`·task-0166 기록 무접촉, 비밀 출력 없음(스크립트는 task 기록 한 파일만 읽음) |

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `scripts/check_summary_quotes.py`(신규), `docs/jarvis-multi-agent-sop-v0.1.md`(§3 Manager 한 항목), `.claude/skills/jarvis-reviewer-call/SKILL.md`(3단계 첫 문단, allowed-tools 1개), 이 기록 |
| QA 뒤 별도 commit | `docs/master-plan.md`(결과·DONE 대기) |
| deny | `jarvis.bat`, `.env`, `memory/tasks/task-0166-…`, 다른 task 기록, `scripts/validate_multi_agent_sop.py`, `.claude/agents/reviewer.md`, `.codex/agents/*.toml`, Worker·봇 코드 |

비범위: Reviewer 판정 규칙·budget·SOP §8 변경, 검사를 gate로 만드는 것, 과거 기록 수정, push.

## 구현

| 파일 | 변경 |
| --- | --- |
| `scripts/check_summary_quotes.py` | task 기록 한 파일을 읽어 `원문`/`verbatim` 절 펜스 블록의 문장 중 `Manager 요약` 절에 그대로 없는 것을 줄 번호와 함께 나열. 펜스 안 제목·6자 미만 조각 제외, 같은 문장 1회, 마침표 없는 인용 허용, Markdown 이스케이프(`\|` 등) 해제. 종료 코드 0 전부 인용 / 1 누락 있음 / 2 요약 절·원문 블록 없음·읽기 실패. `--json`, `--self-test`(16건). 파일 쓰기·git·네트워크 없음, 출력 UTF-8 |
| `docs/jarvis-multi-agent-sop-v0.1.md` | §3 Manager: Reviewer 호출 전 실행하고 빠진 조건이 있으면 요약을 먼저 고친다, 참고 자료이며 판정을 대신하지 않는다 |
| `.claude/skills/jarvis-reviewer-call/SKILL.md` | 3단계 앞에 스크립트 실행과 `unquoted` 목록 전달, allowed-tools에 그 명령 1개 |

## Implementer 검증 (작업 트리 기준, candidate 전)

| # | 검사 | 결과 |
| --- | --- | --- |
| V1 | `python -B scripts/check_summary_quotes.py --self-test` | checks=16, failures=0, PASS |
| V2 | 과거 기록 재현: task-0164 | exit 1, unquoted 22. Reviewer 3이 지적한 세 문장("이번 작업은 새 오케스트레이터를 만들지 않는다."·"기존 `run_pipeline`을 그대로 재사용하고, 범위를 최소로 넓힌다."(42행), "…S1~S5를 하나의 task로 진행하세요."(174행))이 모두 목록에 있다. 나머지는 Owner 원문의 목록 제목·표 머리 등으로, 조건인지는 Manager가 판단한다 |
| V3 | 과거 기록 재현: task-0161 | exit 1. Reviewer 2·3이 지적한 "빈 문자열 결함은 별도 task로 등록: …우선순위는 높게 둡니다."(19행)와 "repair 예산 2로 늘려서 repair 2 진행해줘"가 목록에 있다 |
| V4 | 요약 절이 없는 기록(task-0168) | exit 2, `error=no_manager_summary_section` |
| V5 | 이 기록 | exit 0, sentences=16, unquoted=0 |
| V6 | `python -B scripts/validate_multi_agent_sop.py` | PASS(negative_checks=133, failures=0) |
| V7 | discord-intake smoke(모든 task 기록 파싱, 이 기록 포함) | total 144, failed 0 |
| V8 | Console smoke | browser shell self-test·smoke 통과 |
| V9 | `check_no_secrets` | 새 파일 4개 직접 검사 findings 0. 전체 scan의 findings 7건은 모두 `check_no_secrets.py` 자체 fixture(기존과 같음) |
| V10 | `git diff --check` | 통과 |

cp949 콘솔에서 `PYTHONIOENCODING` 없이 실행해 한국어 출력이 깨지지 않음을 확인했다(스크립트가 stdout·stderr를 UTF-8로 맞춘다).

## Candidate

`c7ff34905bffa577f4f31fea6dc6cc85a2511987` (parent = baseline, 단일 commit, 변경 파일 4개 = 범위 owned).

## Reviewer (`c7ff349`, 유효)

| 항목 | 내용 |
| --- | --- |
| 호출 | Claude Code `reviewer` agent, candidate·baseline 전체 hash, file scope 4개, evidence 3개, Manager 요약과 Owner 원문(위 블록) 전달 |
| verdict | PASS, findings `[]`, `self_deviations` `[]` |
| unverified | self-test, 과거 기록 재현, SOP validator, intake·Console smoke, check_no_secrets, `git diff --check`, cp949 출력, 작업 트리의 `jarvis.bat`·task-0166 무접촉(모두 실행 검사라 `not_run`) → 아래 QA가 같은 candidate에서 확인 |
| budget | `retry_count=0`, `repair_count=0` |

## QA (candidate `c7ff34905bffa577f4f31fea6dc6cc85a2511987`)

main HEAD = candidate, tracked 변경 없음(untracked `jarvis.bat`·task-0166 기록만, 내용 미접촉)에서 실행했다. 콘솔 코드 페이지 949, `PYTHONUTF8`·`PYTHONIOENCODING` 없음.

| # | 검사 | 결과 |
| --- | --- | --- |
| Q1 | self-test | checks=16, failures=0, PASS |
| Q2 | 과거 기록 재현 | task-0164 exit 1이고 Reviewer 3 지적 세 문장 3/3 포함, task-0161 exit 1, task-0168 exit 2(요약 절 없음), 이 기록 exit 0 |
| Q3 | SOP validator | PASS |
| Q4 | check_no_secrets | 새 파일 findings 0(`--staged` 검사 포함). 전체 scan 7건은 기존 자체 fixture |
| Q5 | discord-intake smoke | total 144, failed 0 |
| Q6 | Console smoke | 통과 |
| Q7 | `git diff --check 1c49b2f c7ff349` | 통과 |
| Q8 | `jarvis.bat` | candidate tree에 없음, 작업 트리 untracked 그대로 |

판정: QA PASS. DONE은 Owner Console Complete로만 한다. push 없음.
