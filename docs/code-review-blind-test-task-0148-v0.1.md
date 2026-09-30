# /code-review 블라인드 테스트 조사 기록: task-0148 첫 candidate (v0.1)

이 문서는 조사 기록이다. 현재 규칙이나 현재 동작의 근거가 아니며(AGENTS.md "기준 지도"의
History), 코드·파이프라인·Reviewer 정의는 이 조사로 바꾸지 않았다.

- 조사일: 2026-09-30
- 조사 시점 HEAD: `c5cf9699cd54ee1f603c27410051d9ca9dc2a124`
- 대상 범위: `5fdc863bfee3e9f85f0482c3146a21883e04b8a2..580aa40e2107dc321e388694b9b5b47a9813c158`
  (task-0148 계획 commit `6a47fdd` + 첫 구현 candidate `580aa40`)

## 1. 목적

Claude Code 내장 `/code-review`(medium)가 Jarvis 파이프라인 Reviewer(`.claude/agents/reviewer.md`)가
실제로 잡은 결함을 사전 정보 없이 다시 찾아내는지 확인한다.

## 2. 방법

- `/code-review medium <범위>`를 한 번 실행했다. 실행 전에 task-0148 기록의 Reviewer 결과, repair
  이력, 후속 commit(`8ff5d20`, `9315f47`)은 읽지 않았다.
- 리뷰는 범위 diff와 `580aa40` 시점 파일(`git show 580aa40:...`)을 근거로 했다.
- 리뷰가 끝난 뒤 `memory/tasks/task-0148-reviewer-report-fields-and-worker-source-rules.md`의
  repair 1·2 기록과 현재 `orchestrator/worker/claude_worker.py`를 대조했다.

블라인드 조건의 한계: 리뷰 도중 working tree 대상 grep 한 번이 현재 코드의
`reviewer_unverified` 사용 위치(줄 번호)를 출력했다. 리뷰 결과에는 "현재 working tree에 이 항목이
이미 반영됐을 수 있으나 검토하지 않았다"고 따로 적었다. 이 노출이 finding 1 판단에 영향을 줬는지는
완전히 배제할 수 없다.

## 3. /code-review 결과 (2건)

| # | 위치(`580aa40` 기준) | 요지 |
| --- | --- | --- |
| C1 | `orchestrator/worker/claude_worker.py:550` | `reviewer_unverified`를 기록만 하고 읽는 곳이 없다. QA 6항목, Discord 성공 보고, `record_result(True, ...)` 어디에도 쓰이지 않는다. 그래서 확인되지 않은 항목이 남아도 자동 DONE이 된다. SOP의 "unverified는 반드시 QA로" 규칙과 어긋난다 |
| C2 | `orchestrator/worker/claude_worker.py:541` | 첫 검토의 `self_deviations`가 retry 통과 시 버려진다. `reviewer_retries`만 증가하고, 이 값도 보고·task 기록에 표시되지 않는다. Reviewer가 허용 형식 밖 명령을 실행한 흔적이 남지 않는다 |

## 4. 실제 파이프라인 경과와의 대조

기록에 따르면 task-0148의 Reviewer 경과는 다음과 같다.

| 시점 | 기록된 Reviewer 지적 | 처리 |
| --- | --- | --- |
| `580aa40` | major: 파이프라인에서 `unverified`가 실제로 QA로 전달되지 않음 | repair 1(`8ff5d20`): `qa` 짝 규칙, 짝 없는 항목은 `qa_unverified_owner_review`로 중단 |
| `8ff5d20` retry 검토 | minor: 누락·형식 오류 필드가 "항목 없음"으로 처리돼 fail-closed 위반 가능 | Owner 추가 repair 승인, repair 2(`9315f47`): `report_field`가 분류 불가 시 `None` 반환 |
| `9315f47` | PASS | QA PASS 뒤 Console Complete로 DONE |

| 실제 결함 | /code-review | 판정 |
| --- | --- | --- |
| `unverified`가 QA로 전달되지 않음 (major) | C1 | **일치**. C1은 Owner 보고·task 기록 미표시까지 지적했다. 봇 표시는 기록상 후속 task 후보("봇 보고에 `unverified` 항목 표시")로 남아 있다 |
| 누락·형식 오류 필드를 빈 목록으로 처리 (minor) | 없음 | **누락**. 이 결함은 `580aa40`에도 있었다(`report_field`가 필드가 없으면 `[]` 반환, `580aa40` 기준 299행). 기록상 Reviewer도 `580aa40`이 아닌 `8ff5d20` 검토에서 찾았다 |
| (기록에 없음) | C2 | **미판정**. 파이프라인 Reviewer는 보고하지 않았다. 조사 시점 HEAD에서도 같은 동작이다: `claude_worker.py:577`–`586`에서 두 번째 검토도 무효일 때만 이탈 내용을 detail에 남긴다. SOP §5·§10.2는 첫 검토의 이탈 기록을 요구하지 않는다. Owner 결정은 7절(결함으로 확정하지 않음) |

## 5. 관찰

- 가장 무거운 실제 결함(major)은 /code-review도 독립적으로 찾았다. 근거도 같았다. 코드가 기록만
  하고, QA와 보고 경로가 소비하지 않는다는 점이다.
- fail-closed 누락(minor)은 두 리뷰 모두 첫 candidate에서 놓쳤다. 리뷰 중 "필드가 없으면 `[]`"라는
  동작은 확인했지만 finding으로 올리지 않았다. medium 수준이 확신 높은 finding만 보고하도록 되어 있는 것이
  영향을 줬을 수 있다. 다만 이 한 번의 실행으로는 원인을 확정할 수 없다.
- C2는 파이프라인 Reviewer에 없던 관점(감사 흔적)이다. 확인된 오탐은 없다.

## 6. 한계

- 표본은 1회, 1개 candidate, medium 수준이다. 일반적인 검출률 주장의 근거가 되지 않는다.
- 파이프라인 Reviewer의 `580aa40` 보고 원문은 저장소에 없다. 대조는 task 기록의 요약(major 1건)만
  근거로 했다. 원문에 다른 minor 지적이 있었는지는 확인하지 못했다.
- 2절의 블라인드 조건 노출.

## 7. Owner 결정 (2026-09-30)

1. C2는 현재 SOP에 첫 검토 `self_deviations`의 명시적 보존 계약이 없으므로 결함으로 확정하지 않는다.
   수정하지 않고 이 기록에만 남긴다.
2. `/code-review`는 이 검증 결과를 기준으로 **보조 코드 검토 도구 후보**로 기록한다. 기존 Jarvis
   Reviewer를 대체하지 않고 `/go` 파이프라인에도 추가하지 않는다.
3. 이 단계에서는 코드와 파이프라인을 수정하지 않는다.

## 8. 후속 후보 (이 조사에서는 진행하지 않음)

- high 수준이나 다른 candidate로 같은 방식의 반복 측정.
