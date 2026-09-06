# task-0056-canonical-summary-contract-cleanup

- id: `task-0056-canonical-summary-contract-cleanup`
- title: `남은 canonical FAIL 8건 정리 (summary backtick·길이·타임스탬프)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-06 12:00 UTC`
- updated_at: `2026-09-06 12:40 UTC`
- summary: `task-0054 이후 남아 있던 canonical 검증 실패 8건을 정리했다. 전수 분석 결과 한 겹이 아니라 세 겹이었다 — summary 값의 backtick(8건 공통), 500자 초과(5건), 타임스탬프의 시각 누락(3건)이며 겹치는 파일은 없다. 셋 다 canonical 규칙이 아니라 기록이 계약을 어긴 경우라 규칙은 한 곳도 바꾸지 않았다. 원문은 본문으로 보존하고 summary만 규격 내로 재작성했으며, 누락된 시각은 지어내지 않고 해당 기록이 커밋된 시각으로 보강했다. canonical 전수가 55/55로 복구됐다.`
- source_command: `task-0054가 범위 밖으로 남긴 backtick 8건 정리 지시`

## 기준선

- HEAD `6033650` = `origin/main`
- 변경: `memory/tasks/` 8건 + `orchestrator/discord-intake/run_smoke_tests.py`(예외 목록 제거) + 이 기록
- **코드·canonical 규칙 변경 0건**

## 🔴 한 겹이 아니라 세 겹이었다

8건 모두 `task_file_invalid_metadata` / `summary` 필드에서 실패하지만, backtick만 고쳤을 때
무엇이 드러나는지 시뮬레이션하자 층이 갈라졌다.

| 원인 | 건수 | 대상 | 내용 |
| --- | --- | --- | --- |
| **A. `summary` 값에 backtick** | **8 (전부)** | 모두 | 값 구분자가 backtick이라 값 안에 넣을 수 없다. inner backtick 실측 2~8개 |
| **B. `summary` 500자 초과** | **5** | 0037(1219), 0039(1764), 0041(1532), 0043(770), 0045(1282) | A를 고치면 `task_file_field_too_long`으로 바뀐다 |
| **C. 타임스탬프 시각 누락** | **3** | 0048, 0049, 0050 | `2026-08-29 UTC` — `%Y-%m-%d %H:%M UTC`에 시각이 없다. A를 고치면 `task_file_invalid_updated_at`으로 바뀐다 |

A는 8건 공통이고 B와 C가 나머지를 **5+3으로 정확히 가른다.** 겹치는 파일은 없고, 전층을
고친 시뮬레이션에서 8건 모두 통과해 **네 번째 층은 없음**을 확인했다.

이 층위 패턴은 task-0054에서 겪은 것과 같다 — 앞의 검사가 뒤의 검사를 가린다.

## 판정 — 셋 다 기록 정정이지 규칙 문제가 아니다

| 원인 | 판정 |
| --- | --- |
| A | 값이 backtick으로 **구분**되므로 값 안의 backtick 금지는 형식의 근간이다. 허용하면 파싱이 모호해진다 |
| B | `MAX_SUMMARY_CHARS=500`은 의도된 상한이고 완화는 금지 사항이다 |
| C | `%Y-%m-%d %H:%M UTC`는 저장소 전체가 쓰는 형식이며 `task-template.md`도 그렇게 문서화한다 |

**canonical 규칙은 한 곳도 바꾸지 않았다.** task-0054의 B·C(파서 경계 결함)와는 성격이
다르다 — 그때는 파서가 틀렸고 이번엔 기록이 틀렸다.

## 승인·실행 경로 영향 — 없다

8건 전부 `DONE`이고, writer 전이표의 출발 상태는 `TODO`/`DOING`/`NEEDS_APPROVAL`/`FAILED`라
**`DONE`은 어떤 전이의 출발점도 아니다.** `/approve`는 `NEEDS_APPROVAL`, `/run`은 `DOING`,
`/retry`는 `DOING`/`FAILED`만 받고 `record_task_completion_evidence`는 `DOING`을 요구한다.
즉 이 8개는 **canonical writer가 닿을 수 없는 파일**이었다.

출력에는 영향이 있다 — `/status`가 summary와 `updated_at`을 그대로 보여주고 `/report`는
`updated_at`으로 정렬한다. C를 고치면서 파싱 실패로 최하위 정렬되던 3건이 정상 위치로
이동하므로 `/report`의 recent 구성이 달라질 수 있다. `/report today`는 날짜만 보므로 무관하다.

## 수정 내용

### A·B — 원문 보존 + summary 재작성 (8건)

task-0054에서 쓴 방식을 그대로 재사용했다. 원문을 `## 요약 (원문)` 절로 **한 글자도 줄이지
않고** 옮기고 summary만 규격 내에서 다시 썼다. 본문은 파싱 대상이 아니므로 backtick이 그대로
살아남아 A와 B가 한 번에 해소되고 **정보 손실이 0**이다.

| 파일 | summary 전 → 후 | status |
| --- | --- | --- |
| `task-0037-gemini-cli-local-dev-environment` | 1219 → 416 | `DONE` 유지 |
| `task-0039-buzz-integration-phase1-architecture-borrow` | 1764 → 393 | `DONE` 유지 |
| `task-0041-task-model-append-only-event-log` | 1532 → 354 | `DONE` 유지 |
| `task-0043-no-secrets-enforcement` | 770 → 381 | `DONE` 유지 |
| `task-0045-acp-feasibility-research` | 1282 → 386 | `DONE` 유지 |
| `task-0048-buzz-bridge-phase2-slice1` | 375 → 342 | `DONE` 유지 |
| `task-0049-buzz-bridge-p2-2-p2-3-completion` | 257 → 214 | `DONE` 유지 |
| `task-0050-buzz-bridge-p2-4-p2-5-p2-6-completion` | 376 → 301 | `DONE` 유지 |

원문 보존은 기계적으로 확인했다 — 8건 모두 본문 절의 원문 길이가 원본 summary 길이와
**완전히 일치**한다.

`task-0037`은 untracked였고 이번 정정으로 **처음 tracked가 된다**(task-0054에서 4건을 같은
방식으로 편입한 선례).

### C — 누락된 시각을 커밋 시각으로 보강 (3건)

**임의의 `00:00` 같은 값을 쓰지 않았다.** 각 기록이 실제로 커밋된 시각을 썼고, 그 날짜는
파일에 적혀 있던 날짜와 정확히 일치한다.

| 파일 | 전 | 후 | 근거 커밋 |
| --- | --- | --- | --- |
| `task-0048-buzz-bridge-phase2-slice1` | `2026-08-29 UTC` | `2026-08-29 11:49 UTC` | `d611f4d` |
| `task-0049-buzz-bridge-p2-2-p2-3-completion` | `2026-08-29 UTC` | `2026-08-29 13:04 UTC` | `e9530fc` |
| `task-0050-buzz-bridge-p2-4-p2-5-p2-6-completion` | `2026-09-03 UTC` | `2026-09-03 00:07 UTC` | `fb544ce` |

`created_at`과 `updated_at` 양쪽에 같은 값을 넣었다.

> **명시해 둔다**: 이 시각은 **원래 기록된 생성·갱신 시각이 아니라 해당 기록이 커밋된
> 시각**이다. 원래의 분 단위 시각은 애초에 기록된 적이 없다. 날짜가 일치하므로 날짜 기반
> 동작은 불변이지만, 이 값을 원기록으로 오해하면 안 된다.

### 테스트 계약 복구

task-0054가 이 8건을 `KNOWN_BACKTICK_IN_SUMMARY` **명시적 예외 목록**으로 고정해 뒀다.
정리가 끝났으므로 목록을 **제거**해 "모든 기록이 검증을 통과해야 한다"는 원래 계약으로
되돌렸다. 이제 숨을 곳이 없다 — 새로 쓰는 기록이 규격을 어기면 곧바로 실패한다.

## 검증

| 검증 | 결과 |
| --- | --- |
| **canonical 전수** | 대상 55 중 **PASS 55 / FAIL 0** (기준선 `6033650`: PASS 47 / FAIL 8) |
| 원문 보존 | 8건 모두 본문 원문 길이 = 원본 summary 길이 |
| status 보존 | 8건 모두 `DONE` 유지 |
| `discord-intake` 스모크 | **78/78 PASS** — 예외 목록 없이 통과 |
| `bot_minimal` self-check | **79/79 PASS** |
| `audit-chain` | **6/6 PASS** |
| 기존 회귀 8종 + SOP | 전건 PASS |

## 이번 단계 비범위

- canonical 규칙 변경 — 어휘·타입·길이·`allow_empty`·제어문자 검사 전부 무변경
- 코드 변경 — `run_smoke_tests.py`의 예외 목록 제거 외에 없다
- `task-template.md` — placeholder라 canonical 검증 대상이 아니다(task-0054에서 확정)
- `jarvis.bat` — 건드리지 않았다
