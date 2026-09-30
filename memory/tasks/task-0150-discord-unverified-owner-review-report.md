# task-0150-discord-unverified-owner-review-report

- id: `task-0150-discord-unverified-owner-review-report`
- title: `qa_unverified_owner_review 중단 시 Discord 보고에 확인 대기 unverified 항목 표시`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-09-30 05:55 UTC`
- updated_at: `2026-09-30 13:11 UTC`
- summary: `Worker 파이프라인이 qa_unverified_owner_review로 멈췄을 때 Discord 실패 보고에 QA 6개 검사는 통과했지만 Owner 확인이 필요하다는 사실과 확인 대기 unverified 항목(최대 5건, 항목당 200자, 초과는 외 N건)을 표시한다. 확인 대기 계산은 claude_worker.py의 공통 함수 하나로 두고 봇은 그 함수를 쓴다. accept/반영 명령과 선택지 문구 변경은 범위 밖이다.`
- source_command: `Owner 지시: task-0150 계획 승인과 결정 1~5`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `6b07294fb1979882e2136cdf43681926cf93cf6b` (main HEAD, push 전) |
| 작업 전 상태 | tracked 수정 없음. untracked `jarvis.bat` |
| 줄바꿈 | 대상 코드 파일 3개 index·작업 트리 모두 LF |
| 보존 대상 | task-0143 r3 worktree/branch(`e05c69c`), task-0149 worktree/branch 2개(`8f0c58e`, r2 `bd1622e`) |

## 배경 (계획 단계 확인, 코드 기준)

- 확인 대기 항목의 source는 Reviewer 보고의 `unverified:` 필드다. `report_field()`가 읽은 `- {...}` 항목
  목록이 `WorkerRunResult.reviewer_unverified`에 들어가고, 필드가 없거나 형식이 틀리면
  `["unverified field missing or malformed"]` 한 건이 들어간다.
- QA 6개 검사가 모두 통과한 뒤, 마지막 `qa:` 라벨이 `QA_CHECKS` 이름이 아닌 항목이 있으면
  `qa_unverified_owner_review`로 멈추고 main에 반영하지 않는다. 확인 대기 항목은 `detail`에
  `" | "`로 이어 300자에서 잘린 문자열로만 전달된다.
- 봇은 `run_pipeline` 결과를 `to_dict()`로 받아 `_format_work_reply`의 일반 실패 형식으로 보고한다.
  그래서 항목 수와 각 항목 내용을 알 수 없고, QA가 통과했다는 사실도 드러나지 않는다.
- 봇의 전송 경로(`message.channel.send`)는 길이를 자르지 않는다. Discord 메시지 2000자 제한을 넘으면
  보고 자체가 실패한다.
- task-0148 기록은 "봇 보고에 `unverified` 항목 표시"를 후속 후보로만 적었다.

## Owner 결정 (원문)

```text
task-0150 계획 승인한다. 아래 결정대로 진행해줘.
Owner 결정

1. A안 채택
   * `qa_unverified_owner_review`의 확인 대기 항목 계산을 공통 함수로 추출한다.
   * 판정 로직은 `claude_worker.py` 한 곳에서 유지하고, Discord 보고는 같은 함수를 사용한다.
   * 봇에서 QA 판정 로직을 복제하지 않는다.
2. 이번 task의 목적은 Owner가 무엇을 확인해야 하는지 Discord에서 볼 수 있게 하는 것이다.
   * `qa_unverified_owner_review`일 때 확인 대기 항목을 명확하게 표시한다.
   * QA 6개 검사는 통과했지만 `unverified` 때문에 Owner 확인이 필요하다는 사실도 표시한다.
3. accept/반영 명령은 이번 task에서 구현하지 않는다.
   * `/go <id> accept` 등의 기능은 별도 후속 task로 분리한다.
4. 현재의 재시도/resume 선택지는 이번 task에서 변경하지 않는다.
   * "반영 명령은 아직 없음" 같은 추가 문구도 이번에는 넣지 않는다.
5. 표시 한도:
   * 최대 5건
   * 각 항목 최대 200자
   * 초과 항목은 `외 N건`으로 표시
   * Discord 전체 메시지가 2000자를 넘지 않도록 테스트할 것

구현 범위
계획에서 제안한 최소 범위를 유지한다.

* `adapters/discord/bot_minimal.py`
* `orchestrator/worker/claude_worker.py`
* `orchestrator/worker/run_smoke_tests.py`
* `memory/tasks/task-0150-discord-unverified-owner-review-report.md`

단, 실제 의존 관계를 확인했을 때 더 적은 파일로 구현 가능하면 불필요한 변경은 하지 말 것.
구현 전 조건
먼저 task-0150 task 파일을 생성하고 현재 계획/Owner 결정을 기록한 뒤 구현한다.
그 후:

1. 최소 변경으로 구현
2. worker smoke에 관련 테스트 추가
3. 기존 Discord self-check / discord-intake smoke
4. worker smoke 전체
5. `validate_multi_agent_sop.py`
6. `git diff --check`
7. 실제 diff 범위 확인

특히 다음을 회귀 테스트할 것:

* `qa_unverified_owner_review` → 확인 대기 항목 표시
* `qa: tests_rerun` 등 정상적으로 QA 짝이 있는 항목은 표시하지 않음
* malformed/missing field → 적절한 설명 표시
* 10건 이상 → 최대 5건 + `외 N건`
* 2000자 제한 초과 없음
* 성공 reply와 다른 실패 사유의 기존 문구는 변경하지 않음

검증 전까지 commit/push하지 말고, `jarvis.bat`은 절대 건드리지 말 것.
검증이 모두 PASS하면 결과를 보고하고, 그때 checkpoint commit 여부를 내가 결정하겠다.
```

## 설계

| 파일 | 변경 |
| --- | --- |
| `orchestrator/worker/claude_worker.py` | 파이프라인 QA 단계의 확인 대기 list comprehension을 `unverified_pending(entries)`로 추출하고 파이프라인이 그 함수를 쓴다. 동작 변화 없음 |
| `adapters/discord/bot_minimal.py` | `_format_work_reply` 실패 경로에서 `reason == "qa_unverified_owner_review"`일 때만 줄을 추가한다. QA 통과·Owner 확인 필요 안내 1줄, `claude_worker.unverified_pending(result["reviewer_unverified"])` 결과를 최대 5건(항목당 200자), 초과는 `외 N건`. 형식 오류 항목에는 설명을 붙인다. 그 밖의 문구는 바꾸지 않는다 |
| `orchestrator/worker/run_smoke_tests.py` | `bot_flow`에 회귀 검사 추가 |

범위 밖: accept/반영 명령, "Owner 확인 대기" 상태와 전이 계약, task 기록에 확인 대기 항목 저장,
QA 6항목과 `qa` 짝 규칙, Reviewer 정의, SOP, validator, 성공·다른 실패 보고 문구, 재시도/resume
선택지, 봇 재시작, commit, push, `jarvis.bat`.

## 검증 (Implementer 실행)

| # | 항목 | 결과 |
| --- | --- | --- |
| V1 | Worker smoke (`PYTHONUTF8=1 python -B orchestrator/worker/run_smoke_tests.py`) | 191/191 PASS (baseline `6b07294` 175/175, 신규 16) |
| V2 | baseline 대비 reply 문구 (scratchpad 스크립트, baseline 임시 worktree의 봇·`claude_worker`와 후보를 각각 로드) | 12개 결과 중 달라진 것은 `qa_unverified_owner_review` 1개. 성공, `qa_failed`, `scope_violation`, `reviewer_findings`(budget 소진 문구 포함), `reviewer_findings_not_repairable`, checkpoint 실패, candidate 없는 실패, `work_planned`, `work_started` 3종은 동일 |
| V3 | Discord self-check suite | 92/92 PASS |
| V4 | discord-intake smoke | 125/125, 실패 0 (task 파일 수에 따라 늘어남) |
| V5 | `python -B scripts/validate_multi_agent_sop.py` | PASS, negative_checks=128, negative_failures=0 |
| V6 | `git diff --check` (이 기록 포함) | exit 0. 이 검증 절 기록 전 `--stat`과 `--ignore-cr-at-eol --stat`이 모두 4개 파일 210 추가, 6 삭제로 같음. 기록 뒤 exit 0 재확인 |
| V7 | 변경 범위 | 설계의 코드 3개 파일과 이 기록. 그 밖의 변경 없음, `jarvis.bat` untracked 유지 |
| V8 | 임시 worktree | baseline 비교용 worktree를 제거했고 `git worktree list`에서 사라짐. task-0143 r3, task-0149 worktree 2개는 그대로 |

구현 메모:

- 이 셸의 Python 3.14는 기본 인코딩이 cp949라서 `PYTHONUTF8=1` 없이 worker smoke를 돌리면 subprocess
  출력 디코딩이 실패해 FAIL이 무작위로 나온다. 변경 전 baseline도 같은 방식으로 실패했으므로 이번 변경과는
  무관하다. 위 결과는 모두 `PYTHONUTF8=1`로 얻었다.
- `UNVERIFIED_UNREADABLE`는 형식 오류 표시 문자열을 상수로 둔 것이다. 봇이 이 문자열을 복사하지 않고
  알아보기 위해 추가했고, 파이프라인 동작은 바뀌지 않는다.
- 2000자 처리: 전체 reply가 2000자를 넘을 때만 항목 폭을 10자씩 줄인다(최소 40자). 다른 줄은 줄이지
  않는다. 그래서 다른 줄만으로 약 1650자를 넘는 극단적인 경우(비정상적으로 긴 task id나 worktree 경로)에는
  2000자 초과를 막지 못한다. 이런 줄의 길이 제한은 변경 전에도 없었다. smoke는 100자 task id, 300자 상세,
  200자 worktree 경로, 500자 항목 12건에서 2000자 이하를 확인했다. (이 한계는 아래 repair 1로 고쳤다.)

## Reviewer 결과 (candidate `5cb506e2e45dbe1898ed9cd802ecd81f425b870a`): FINDINGS

minor 3건, `self_deviations: []`, `unverified` 7건(smoke·validator·diff check·baseline 비교·task 파일 선작성·
`jarvis.bat`과 push 상태).

1. minor, candidate 결함: 최소 폭 40자에서도 다른 줄이 약 1650자를 넘으면 이 task가 추가한 줄 때문에 reply가
   2000자를 넘어 전송이 실패할 수 있다. Owner 결정 5와 어긋난다.
2. minor, 호출 결함: Manager 요약에 승인 조건 "더 적은 파일로 구현 가능하면 불필요한 변경은 하지 말 것"과
   4개 파일 각각의 필요성이 없다.
3. minor, 호출 결함: Manager 요약에 결정 3의 "`/go <id> accept`는 별도 후속 task로 분리"가 없다.

## repair 1: 2000자 제한 보장

Owner가 1번 지적에 repair 1회를 승인했다. repair_budget 1 중 1을 사용했고(repair_count=1), 이 task의 repair
예산은 소진됐다. 2·3번은 코드 수정 대상이 아니며 다음 Reviewer 호출의 Manager 요약에 반영한다.

repair 승인 Owner 원문:

```text
(a) repair 1회로 진행해줘.
Reviewer minor #1의 2000자 제한 결함을 수정해줘.
조건:

* repair_budget 1 중 이번 1회만 사용
* 최소 폭(40자)에서도 전체 Discord reply가 2000자를 넘을 수 있는 경우를 처리
* 항목 줄을 더 줄일 수 없으면 해당 항목들을 생략하고 `외 N건` 등 개수 정보만 남기는 방식으로 전체 메시지가 반드시 2000자 이하가 되게 할 것
* 이 경로를 검증하는 smoke test 추가
* 기존 정상적인 표시 동작은 유지
* Reviewer가 지적한 minor #2, #3은 코드 수정 대상이 아님. 다음 Reviewer 호출의 Manager Summary에 필요한 내용을 정확히 포함할 것
* `/go <id> accept` 기능은 이번 repair에 추가하지 말 것
* 다른 범위의 개선/리팩터링 금지
* `jarvis.bat` 절대 건드리거나 stage하지 말 것

repair 후:

1. 새 candidate SHA를 보고
2. 추가/변경된 파일을 보고
3. 해당 candidate의 검증 결과를 보고
4. 아직 Reviewer 재실행은 하지 말고 여기서 멈춰줘.
```

구현: `bot_minimal.py`의 owner review 줄 계산을 `_owner_review_lines()`로 모았다. 안내 줄과 항목 줄만 줄이고
다른 reply 줄은 그대로 둔다. 순서는 다음과 같다.

1. 항목 폭 200자에서 10자씩 줄여 40자까지 시도한다.
2. 그래도 넘으면 항목을 생략하고 안내 줄과 `- 확인 대기 N건: Discord 메시지 길이 제한으로 항목 내용을 생략했습니다`
   한 줄만 남긴다.
3. 그래도 넘으면 owner review 줄을 추가하지 않는다.

그래서 이 task가 추가하는 줄 때문에 2000자를 넘는 일은 없다. 다만 기존 줄만으로 이미 2000자를 넘는
reply는 변경 전과 같으며, 이 task에서 다루지 않는다. 정상 경우의 표시 위치와 문구는 그대로다.
`claude_worker.py`는 바꾸지 않았다.

repair 1 검증 (Implementer 실행):

| # | 항목 | 결과 |
| --- | --- | --- |
| R1 | Worker smoke (`PYTHONUTF8=1`) | 194/194 PASS (기존 191 + 신규 3: 개수 줄만 남는 경우, 아무 줄도 추가하지 않는 경우, worktree 길이 0–2000을 25자 간격으로 바꿔 가며 "추가 줄이 없으면 2000자 이하인 reply가 추가 줄 때문에 2000자를 넘는 일이 없다"를 확인) |
| R2 | baseline `6b07294` 대비 reply 문구 | 12개 결과 중 달라진 것은 `qa_unverified_owner_review` 1개. 비교용 임시 worktree는 다시 제거했다 |
| R3 | Discord self-check suite | 92/92 PASS |
| R4 | discord-intake smoke | 125/125, 실패 0 |
| R5 | `validate_multi_agent_sop.py` | PASS, negative_checks=128, negative_failures=0 |
| R6 | `git diff --check` | exit 0 |
| R7 | 변경 범위 | `bot_minimal.py`, `run_smoke_tests.py`, 이 기록. `jarvis.bat` untracked 유지 |
