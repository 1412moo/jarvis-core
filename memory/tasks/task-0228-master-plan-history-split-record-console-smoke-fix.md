# task-0228-master-plan-history-split-record-console-smoke-fix

- id: `task-0228-master-plan-history-split-record-console-smoke-fix`
- title: `master-plan 완료 기록을 history 파일로 분리하고 Console smoke의 크기 의존 수정`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-11-11 09:38 UTC`
- updated_at: `2026-11-11 10:56 UTC`
- summary: `docs/master-plan.md가 Console 읽기 한도 128,000바이트에 닿아 task-0227 완료 기록을 넣지 못했다. Owner Dashboard 절의 완료 날짜 항목 81개를 새 docs/master-plan-history.md로 순서와 원문 그대로 옮기고, master-plan에는 현재 상태 줄과 history 링크만 남긴다. AGENTS.md History 목록과 master-plan 10절 갱신 규칙을 고치고 task-0227 기록을 history에 넣는다. Console smoke의 값 길이 거부 검사가 실제 문서의 남은 여유에 기대지 않도록 파서가 읽는 부분만 뽑은 fixture로 돌린다. 크기 한도, Console 파서와 API는 바꾸지 않는다.`
- source_command: `Owner 지시: 조사 보고서 검토 후 A안과 smoke 취약성 수정 구현 승인 (Claude Code 세션)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `5822cd18ed110cdc274bfd0a5c550169f65320a6` (등록 시점 main HEAD = origin/main) |
| budget | `retry_budget=1`, `retry_count=0`, `repair_budget=1`, `repair_count=0` (SOP §5 기본값) |
| 작업 위치 | 저장소 밖 worktree `jarvis-core-worktrees/task-0228-master-plan-history`, 브랜치 `work/task-0228-master-plan-history`. main 체크아웃은 그대로 둔다 |

## Owner 결정 (원문, 권장안 진행)

```text
[Manager 질문]
권장안(완료 기록을 history 파일로 분리)으로 task를 진행할까요?

[Owner 답]
권장안으로 진행
```

질문 앞 Manager 조사 보고(Manager 문장, 승인 원문 아님)는 Owner의 읽기 전용 조사 지시에 대한 답이다. 원인(완료 날짜 항목 81개가 75,283바이트, smoke 변형이 402바이트를 더 씀)과 방안 A~E 비교, 권장안 A, 예상 수정 파일, 테스트 계획, Owner 결정 필요 다섯 가지를 적었다.

## Owner 결정 (원문, 구현 승인)

```text
조사 보고서를 검토했다. 다음 범위로 구현을 진행하도록 승인한다.
1. 승인 범위
A안: 완료 기록을 별도 History 파일로 분리한다.

* 새 파일: `docs/master-plan-history.md`
* 기존 `docs/master-plan.md`의 완료 날짜 항목 81개를 History 파일로 이전한다.
* 기존 항목은 순서와 내용을 한 글자도 변경하지 않는다.
* 기존 `master-plan.md`에는 현재 상태와 기준 정보만 남긴다.
* History 파일로 이동했다는 링크와 설명을 추가한다.
* AGENTS.md의 History 목록에 새 파일을 등록한다.
* §10 갱신 규칙을 수정해 이후 완료 기록은 History 파일에 추가하도록 한다.
* task-0227 완료 기록도 History 파일에 추가한다.
* 이번 작업 자체의 완료 기록도 History에 남긴다.

2. Smoke 테스트 취약성 수정도 포함
조사에서 발견한 다음 문제를 수정한다.

* `run_smoke_tests.py`의 '값이 너무 긴 경우' 검사가 실제 master-plan 크기에 의존하는 문제
* 문서 크기가 한도에 가까우면 테스트용 값 변형 때문에 정상적인 검증까지 실패하는 문제

테스트가 실제 문서의 남은 여유 공간에 의존하지 않도록 결정론적인 fixture 또는 동등하게 안정적인 방식으로 수정한다.
단, 테스트의 검증 목적과 기존 크기 제한 검증은 약화시키지 않는다.
3. 유지해야 할 사항

* `MASTER_PLAN_MAX_BYTES = 128_000` 제한은 그대로 유지한다.
* 기존 Console 파서와 API 동작은 불필요하게 변경하지 않는다.
* 기존 완료 기록 81개는 삭제하거나 요약하지 않는다.
* 기존 기록의 순서와 원문을 보존한다.
* History 파일은 공식 프로젝트 기록으로 관리한다.
* 향후 History를 분기별로 나누는 작업은 이번 범위에서 제외한다.

4. 구현 및 검증 절차

1. 기존 SOP와 완료 처리 절차를 확인한다.
2. 승인된 범위만 최소 변경으로 구현한다.
3. 기존 81개 항목이 순서와 바이트 단위까지 정확히 보존됐는지 기계적으로 대조한다.
4. task-0227 기록이 정확히 추가됐는지 확인한다.
5. Smoke 취약성 수정 테스트를 별도로 검증한다.
6. 기존 SOP에 따른 Reviewer 검토와 QA를 수행한다.
7. Console self-test, smoke, Hermes Manager smoke, Worker smoke, Discord self-check 등 관련 검증을 수행한다.
8. 변경 파일과 Git 상태를 확인하고 결과를 보고한다.

5. 작업 안전 규칙

* `jarvis.bat`은 절대 열거나 수정하지 않는다.
* `.env` 및 비밀정보를 열거나 노출하지 않는다.
* 승인된 파일 외에는 변경하지 않는다.
* 불필요한 리팩터링을 하지 않는다.
* 기존 기록을 임의로 수정하지 않는다.
* push와 봇 재시작은 이번 승인에 포함되지 않는다.
* 기존 SOP의 Owner 승인 및 Console 완료 절차를 준수한다.

이제 승인된 범위 내에서 구현을 진행하라.
작업 완료 후에는 변경 파일, 기존 81개 기록 보존 검증 결과, task-0227 기록, 테스트 결과, Reviewer 판정, QA 결과, 커밋 상태, 미완료 사항을 구분해 보고하라.
```

## 조사 (baseline 기준)

- `docs/master-plan.md` 127,574바이트(작업 트리 CRLF, 저장소 LF), 763줄. Console `MASTER_PLAN_MAX_BYTES = 128_000`(`apps/jarvis-console/run_web_app.py`)은 파일 전체 바이트로 거부한다.
- Owner Dashboard `### 현재 위치와 다음 체감 목표` 절(105~194줄)이 78,588바이트다. 그 안에 `- **[날짜] …(task-id).**` 형식 완료 날짜 항목 81개(모두 task id 있음)와 현재 상태 줄 6개(`최근 완료`, `현재 다음 작업`, `현재 사용자 체감 결과`, `다음 사용자 체감 milestone`, `최근 검증 결과`, `현재 결정 필요`)가 있다. 날짜 순서는 일부 어긋나 있다. 항목 안에 Markdown 링크는 없다.
- `read_master_plan_snapshot`이 값을 읽는 곳은 `## 2. 현재 기준점` 필드, `## 5. 작업 축별 상태` 표, `### Manager Reporting Workflow v0.1 package evidence` 표뿐이다. 완료 날짜 항목은 읽지 않는다. Hermes Manager는 이 스냅샷과 경로 문자열만 쓴다.
- SOP validator `_validate_master_plan`의 필수 문구 8개는 모두 §4(333~372줄)에도 있어 이동의 영향을 받지 않는다.
- task-0227 DONE(`5822cd1`) 뒤 Owner의 승인으로 push와 봇 재시작을 했고, Owner가 DM에서 실제 봇 `/goal`을 보내 그 답(`goal-20261111-093125-178`, 하위 작업 5개 모두 needs_owner, 모든 설명 한국어, 외부 서비스 근거 없음)을 이 세션에 붙여 넣었다. task-0227 기록은 그 전에 닫혀 실제 봇 확인을 "확인하지 못한 것"으로 남겼으므로, history의 task-0227 항목은 이 확인의 근거를 이 절로 적는다.
- Console smoke `_test_master_plan_optional_selection_fields`의 "값이 너무 긴 경우"는 실제 문서의 99바이트 `desired outcome` 값을 501바이트로 바꿔 402바이트를 늘린다. 남은 여유 426바이트에서 실제로 쓸 수 있는 것은 24바이트였고, task-0227 DONE 때 99바이트 항목으로도 smoke가 크기 오류로 실패했다(task-0227 기록 Complete 절).

## 범위

| 구분 | 경로 |
| --- | --- |
| owned | `docs/master-plan.md`, `docs/master-plan-history.md`(새 파일), `AGENTS.md`(History 목록 한 줄), `apps/jarvis-console/run_smoke_tests.py`(해당 검사), 이 task 기록 |
| deny | `apps/jarvis-console/run_web_app.py`(한도·파서·API), 다른 Console 파일, validator, Hermes Manager, Worker·Discord 코드, 다른 task 기록(History), history 분기별 분할, `jarvis.bat`, `.env`, 보호 경로, push, 봇 재시작 |

## Start

Console(worktree에서 띄움) Voice Inbox의 Create Local Task Preview를 확인하고 Confirm해 TODO 기록을 만들었다. Project Control의 Start Preview(TODO → DOING, 실행 없음)를 확인하고 `Confirm Start`로 Confirm했다. Console은 수정 전에 껐다. 그 뒤 title·summary·source_command를 이 task 내용으로 고쳤다.

## 구현

- `docs/master-plan-history.md`(새 파일): 제목, History 성격(공식 기록, 현재 규칙의 근거 아님, AGENTS.md 기준 지도의 History), 항목 형식과 끝에 붙이는 규칙, 이동 사실(task-0228, 81개, 순서·원문 그대로, 어긋난 날짜 순서도 그대로, 지난 task 기록의 "master-plan 항목"은 이 중 하나)을 적고, `## 완료 기록` 아래에 81개를 원래 순서로 둔 뒤 task-0227 항목을 붙였다. 이번 task 항목은 DONE checkpoint에서 붙인다(지난 task들이 DONE 때 master-plan 항목을 넣은 것과 같은 시점).
- `docs/master-plan.md`: Owner Dashboard 절에서 날짜 항목 81줄을 빼고 현재 상태 줄 6개는 원래 순서로 남겼다. 절 끝에 history 링크 한 줄을 넣었다. §10 갱신 규칙에 완료 날짜 항목은 history 파일 끝에 붙이고 이 문서에는 Dashboard `최근 완료`와 §2 `Recent completed`만 고친다는 문단을 더했다. 그 밖의 줄은 바꾸지 않았다.
- `AGENTS.md`: 기준 지도 History 목록에 `docs/master-plan-history.md` 한 줄을 더했다.
- `apps/jarvis-console/run_smoke_tests.py`: `_master_plan_parser_fixture`를 더했다. 실제 master-plan에서 파서가 읽는 세 절만(파서 정규식과 같은 끝 경계) 첫 줄과 함께 뽑는다. `_test_master_plan_optional_selection_fields`의 모든 변형·거부 검사(선택 줄 없음, 64자·65자 ID, 501자 값, 중복 줄)는 이 fixture에서 돈다. 검증 목적을 지키려고 세 가지를 더 확인한다: fixture를 읽은 값이 실제 master-plan 전체를 읽은 값과 같다(source 제외), 실제 문서 뒤에 4만 자를 덧붙여도 fixture가 그대로다, fixture에 가장 큰 변형을 더해도 한도보다 작다. 크기 한도 거부 검사(한도+1바이트 파일)는 그대로다.
- `run_web_app.py`의 한도, 파서, API는 바꾸지 않았다.

## Implementer 검증 (작업 트리, candidate 전)

- 기계 대조(`git show`로 baseline 읽음, 작업 트리는 CRLF를 LF로 바꿔 읽음): baseline 항목 81개 75,121바이트(LF 기준), sha256 앞 16자 `db5af8d23bf15bbc`. history의 연속된 81줄이 같은 순서·같은 바이트(sha256 같음), 각 항목이 history에 정확히 한 번, 그 뒤에 task-0227 항목 하나. master-plan에 날짜 항목 0개. difflib 대조로 master-plan의 삭제 줄은 이동한 81줄과 순서까지 같고, 추가는 링크 한 줄과 §10 문단(빈 줄 포함 두 줄)뿐이다. master-plan 52,243바이트(LF), 작업 트리 52,539바이트(CRLF).
- Console smoke PYTHONUTF8=1과 없음 모두 rc=0, `run_web_app.py --self-test` 통과, SOP validator PASS.
- 나머지 검사는 self-review 뒤 candidate 직전에 다시 돌려 아래에 적는다.

## Self-review

SOP §3대로 staged 변경에 `claude -p --agent self-reviewer --tools Read,Grep,Glob`을 한 번 돌렸다(Reviewer 판정 아님, 사용량 추정 $1.25). 지적 세 건과 처리:

1. major: history의 task-0227 항목이 "실제 봇 `/goal`에서 … 확인했다"고 적었지만 task-0227 기록은 실제 봇 확인을 "확인하지 못한 것"으로 남겼다. 항목을 고쳐 QA dry-run의 확인과 task-0227 기록의 미확인을 그대로 적고, 실제 봇 확인은 DONE 뒤 Owner가 붙여 넣은 결과이며 근거가 이 기록 조사 절이라고 밝혔다(조사 절에 한 항목 더함).
2. minor: 옮긴 항목 안의 "이 문서", "아래 §2·§4"가 history 파일을 가리키는 것처럼 읽힌다. 항목 본문은 바꾸지 않고 history 머리말에 그 말들이 `master-plan.md`를 가리킨다는 문장을 더했다.
3. minor: A11의 해석(Owner Dashboard 절의 날짜 항목만 옮기고 §4 milestone 소절은 남김)이 Owner 확인을 받지 않았다. candidate 전에 Owner에게 물었고 Owner가 §4를 그대로 두기로 했다(아래 Owner 결정 절).

수정 뒤 다시 돌린 결과: 기계 대조(81줄 동일, sha256 `db5af8d23bf15bbc`, 81개 뒤 task-0227 항목 하나), Console smoke rc=0, SOP validator PASS, Discord `--self-check-suite` rc=0, `git diff --check` 통과, 사전 점검 PASS. 수정 전 한 번 돌린 Worker smoke 767/0, Hermes Manager smoke 통과, Console self-test 통과는 그 뒤 코드 변경이 없어 다시 돌리지 않았고 QA가 candidate에서 돌린다.

## Owner 결정 (원문, self-review 지적 질문)

```text
[Manager 질문]
task-0228 self-review 지적: '기존 master-plan.md에는 현재 상태와 기준 정보만 남긴다'를 Owner Dashboard 절의 완료 날짜 항목 81개만 옮기는 것으로 해석했습니다. §4의 '최근 완료·이전 완료' 소절(milestone 설명, 약 20KB)은 남겼는데, SOP validator가 반드시 있어야 한다고 보는 문구 8개가 그 소절에 있어 옮기면 validator가 실패하기 때문입니다. 어떻게 할까요?

[Owner 답]
§4는 그대로 둠 (Recommended)
```

## Manager 요약

각 행의 "출처" 칸이 인용한 원문 블록의 제목이다. 인용은 그 블록의 문장을 그대로 옮겼고, 해석은 오른쪽 칸에만 적는다.

| # | 출처 | 원문 인용 | Manager 해석과 충족 |
| --- | --- | --- | --- |
| A1 | Owner 결정 (원문, 권장안 진행) | "[Manager 질문]" | 질문의 표지 |
| A2 | Owner 결정 (원문, 권장안 진행) | "권장안(완료 기록을 history 파일로 분리)으로 task를 진행할까요?" | A4 답의 질문. 권장안은 질문 앞 조사 보고의 방안 A |
| A3 | Owner 결정 (원문, 권장안 진행) | "[Owner 답]" | 답의 표지 |
| A4 | Owner 결정 (원문, 권장안 진행) | "권장안으로 진행" | 이 task로 진행한다. 세부 범위는 A5 이하 구현 승인이 정한다 |
| A5 | Owner 결정 (원문, 구현 승인) | "조사 보고서를 검토했다." | A2의 조사 보고 |
| A6 | Owner 결정 (원문, 구현 승인) | "다음 범위로 구현을 진행하도록 승인한다." | 범위 owned 행 |
| A7 | Owner 결정 (원문, 구현 승인) | "A안: 완료 기록을 별도 History 파일로 분리한다." | 구현 절 첫 두 항목 |
| A8 | Owner 결정 (원문, 구현 승인) | "새 파일: `docs/master-plan-history.md`" | 그 이름으로 새로 만들었다 |
| A9 | Owner 결정 (원문, 구현 승인) | "기존 `docs/master-plan.md`의 완료 날짜 항목 81개를 History 파일로 이전한다." | 81개를 옮겼다. Implementer 검증의 기계 대조 |
| A10 | Owner 결정 (원문, 구현 승인) | "기존 항목은 순서와 내용을 한 글자도 변경하지 않는다." | 연속된 81줄이 순서·바이트까지 같다(sha256 같음) |
| A11 | Owner 결정 (원문, 구현 승인) | "기존 `master-plan.md`에는 현재 상태와 기준 정보만 남긴다." | Owner Dashboard 절에는 현재 상태 줄 6개와 링크만 남겼다. 다른 절은 바꾸지 않았다. §4의 '최근 완료'·'이전 완료' milestone 소절은 남긴다(validator 필수 문구 8개가 §4에 있음, Owner 확인 A53) |
| A12 | Owner 결정 (원문, 구현 승인) | "History 파일로 이동했다는 링크와 설명을 추가한다." | master-plan 절 끝의 링크 줄과 §10 문단, history 머리말의 이동 설명 |
| A13 | Owner 결정 (원문, 구현 승인) | "AGENTS.md의 History 목록에 새 파일을 등록한다." | 한 줄을 더했다 |
| A14 | Owner 결정 (원문, 구현 승인) | "§10 갱신 규칙을 수정해 이후 완료 기록은 History 파일에 추가하도록 한다." | §10에 문단 하나를 더했다 |
| A15 | Owner 결정 (원문, 구현 승인) | "task-0227 완료 기록도 History 파일에 추가한다." | 81개 뒤에 날짜 항목 하나로 넣었다 |
| A16 | Owner 결정 (원문, 구현 승인) | "이번 작업 자체의 완료 기록도 History에 남긴다." | DONE checkpoint에서 history 끝에 붙인다(지난 task들의 master-plan 항목과 같은 시점) |
| A17 | Owner 결정 (원문, 구현 승인) | "Smoke 테스트 취약성 수정도 포함" | 구현 절 넷째 항목 |
| A18 | Owner 결정 (원문, 구현 승인) | "조사에서 발견한 다음 문제를 수정한다." | 조사 절 마지막 항목의 문제 |
| A19 | Owner 결정 (원문, 구현 승인) | "`run_smoke_tests.py`의 '값이 너무 긴 경우' 검사가 실제 master-plan 크기에 의존하는 문제" | `apps/jarvis-console/run_smoke_tests.py`의 `_test_master_plan_optional_selection_fields` |
| A20 | Owner 결정 (원문, 구현 승인) | "문서 크기가 한도에 가까우면 테스트용 값 변형 때문에 정상적인 검증까지 실패하는 문제" | 모든 변형을 파서가 읽는 부분만 뽑은 fixture에서 돌린다 |
| A21 | Owner 결정 (원문, 구현 승인) | "테스트가 실제 문서의 남은 여유 공간에 의존하지 않도록 결정론적인 fixture 또는 동등하게 안정적인 방식으로 수정한다." | `_master_plan_parser_fixture`. 문서 뒤에 4만 자를 덧붙여도 fixture가 같다는 검사를 넣었다. QA가 한도 근처 문서로 따로 확인한다 |
| A22 | Owner 결정 (원문, 구현 승인) | "단, 테스트의 검증 목적과 기존 크기 제한 검증은 약화시키지 않는다." | 거부 검사 다섯 가지는 그대로이고, fixture가 실제 문서와 같은 값을 읽는지 검사를 더했다. 한도+1바이트 거부 검사는 그대로다 |
| A23 | Owner 결정 (원문, 구현 승인) | "유지해야 할 사항" | 아래 여섯 가지의 표제 |
| A24 | Owner 결정 (원문, 구현 승인) | "`MASTER_PLAN_MAX_BYTES = 128_000` 제한은 그대로 유지한다." | `run_web_app.py`를 바꾸지 않았다 |
| A25 | Owner 결정 (원문, 구현 승인) | "기존 Console 파서와 API 동작은 불필요하게 변경하지 않는다." | Console 코드는 smoke 파일만 바꿨다 |
| A26 | Owner 결정 (원문, 구현 승인) | "기존 완료 기록 81개는 삭제하거나 요약하지 않는다." | 원문 그대로 옮겼다 |
| A27 | Owner 결정 (원문, 구현 승인) | "기존 기록의 순서와 원문을 보존한다." | 어긋난 날짜 순서까지 그대로다 |
| A28 | Owner 결정 (원문, 구현 승인) | "History 파일은 공식 프로젝트 기록으로 관리한다." | history 머리말에 공식 프로젝트 기록이라고 적고 AGENTS.md History 목록에 넣었다 |
| A29 | Owner 결정 (원문, 구현 승인) | "향후 History를 분기별로 나누는 작업은 이번 범위에서 제외한다." | 하지 않았다 |
| A30 | Owner 결정 (원문, 구현 승인) | "구현 및 검증 절차" | 아래 여덟 단계의 표제 |
| A31 | Owner 결정 (원문, 구현 승인) | "기존 SOP와 완료 처리 절차를 확인한다." | task-0227과 같은 수동 SOP(Console Create·Start, self-review, candidate, Reviewer, QA, Owner 최종 승인, Console Complete) |
| A32 | Owner 결정 (원문, 구현 승인) | "승인된 범위만 최소 변경으로 구현한다." | 범위 owned 행의 다섯 파일만 |
| A33 | Owner 결정 (원문, 구현 승인) | "기존 81개 항목이 순서와 바이트 단위까지 정확히 보존됐는지 기계적으로 대조한다." | Implementer 검증 절. QA가 candidate에서 다시 돌린다 |
| A34 | Owner 결정 (원문, 구현 승인) | "task-0227 기록이 정확히 추가됐는지 확인한다." | 기계 대조가 81개 뒤 날짜 항목이 task-0227 하나임을 확인한다. 내용은 task-0227 기록(candidate `1cef35b`, QA PASS, 최종 승인, `5822cd1`)과 대조한다 |
| A35 | Owner 결정 (원문, 구현 승인) | "Smoke 취약성 수정 테스트를 별도로 검증한다." | QA에서 한도 근처로 키운 master-plan 사본으로 baseline smoke는 실패하고 candidate smoke는 통과하는지 확인한다 |
| A36 | Owner 결정 (원문, 구현 승인) | "기존 SOP에 따른 Reviewer 검토와 QA를 수행한다." | candidate에 Reviewer, 이어 QA |
| A37 | Owner 결정 (원문, 구현 승인) | "Console self-test, smoke, Hermes Manager smoke, Worker smoke, Discord self-check 등 관련 검증을 수행한다." | QA 검사 목록 |
| A38 | Owner 결정 (원문, 구현 승인) | "변경 파일과 Git 상태를 확인하고 결과를 보고한다." | QA와 최종 보고 |
| A39 | Owner 결정 (원문, 구현 승인) | "작업 안전 규칙" | 아래 일곱 가지의 표제 |
| A40 | Owner 결정 (원문, 구현 승인) | "`jarvis.bat`은 절대 열거나 수정하지 않는다." | 열지 않았다. QA가 크기와 수정 시각만 확인한다 |
| A41 | Owner 결정 (원문, 구현 승인) | "`.env` 및 비밀정보를 열거나 노출하지 않는다." | 열지 않았다. QA가 비밀 검사를 돌린다 |
| A42 | Owner 결정 (원문, 구현 승인) | "승인된 파일 외에는 변경하지 않는다." | 범위 owned 행 밖은 바꾸지 않는다 |
| A43 | Owner 결정 (원문, 구현 승인) | "불필요한 리팩터링을 하지 않는다." | smoke는 해당 검사만 바꿨다 |
| A44 | Owner 결정 (원문, 구현 승인) | "기존 기록을 임의로 수정하지 않는다." | 다른 task 기록은 바꾸지 않았다 |
| A45 | Owner 결정 (원문, 구현 승인) | "push와 봇 재시작은 이번 승인에 포함되지 않는다." | 하지 않는다 |
| A46 | Owner 결정 (원문, 구현 승인) | "기존 SOP의 Owner 승인 및 Console 완료 절차를 준수한다." | Owner 최종 승인 뒤 Console Record Evidence와 Complete |
| A47 | Owner 결정 (원문, 구현 승인) | "이제 승인된 범위 내에서 구현을 진행하라." | 구현 절 |
| A48 | Owner 결정 (원문, 구현 승인) | "작업 완료 후에는 변경 파일, 기존 81개 기록 보존 검증 결과, task-0227 기록, 테스트 결과, Reviewer 판정, QA 결과, 커밋 상태, 미완료 사항을 구분해 보고하라." | 최종 보고를 그 항목으로 나눈다 |
| A49 | Owner 결정 (원문, self-review 지적 질문) | "[Manager 질문]" | 질문의 표지 |
| A50 | Owner 결정 (원문, self-review 지적 질문) | "task-0228 self-review 지적: '기존 master-plan.md에는 현재 상태와 기준 정보만 남긴다'를 Owner Dashboard 절의 완료 날짜 항목 81개만 옮기는 것으로 해석했습니다." | self-review 지적 3 |
| A51 | Owner 결정 (원문, self-review 지적 질문) | "§4의 '최근 완료·이전 완료' 소절(milestone 설명, 약 20KB)은 남겼는데, SOP validator가 반드시 있어야 한다고 보는 문구 8개가 그 소절에 있어 옮기면 validator가 실패하기 때문입니다." | 남긴 이유(조사 절) |
| A52 | Owner 결정 (원문, self-review 지적 질문) | "어떻게 할까요?" | 답은 A53 |
| A52a | Owner 결정 (원문, self-review 지적 질문) | "[Owner 답]" | 답의 표지 |
| A53 | Owner 결정 (원문, self-review 지적 질문) | "§4는 그대로 둠 (Recommended)" | §4는 바꾸지 않는다. 이 답은 이 task에만 효력이 있다 |
