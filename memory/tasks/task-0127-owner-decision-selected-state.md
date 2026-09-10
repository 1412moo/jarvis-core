# task-0127-owner-decision-selected-state

- id: `task-0127-owner-decision-selected-state`
- title: `T3 구현 — Console 이 Owner 가 이미 내린 workstream 선택을 표현`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-11 07:10 UTC`
- updated_at: `2026-09-11 07:10 UTC`
- summary: `task-0121 이 확정한 jarvis-console 선택을 Console 이 표시하지 못하던 데이터 경로를 열었다. UI 와 계약은 이미 완성돼 있었고 master-plan 이 선택을 선언할 방법과 builder 가 그것을 읽는 경로만 없었다. 필수 19 개와 분리된 optional 필드 2 개를 신설했고 없으면 기존 동작이 그대로 유지된다. selected 상태는 두 값이 모두 있어야 하고 unselected 상태는 둘 다 없어야 한다는 계약은 그대로다. API shape 과 UI 는 무변경. mutation 7 종 전부 새 assertion 이 잡는다.`
- source_command: `Owner 가 승인한 T3 구현 지시 (desired_outcome 문장과 selected_for_proposal 지정 포함)`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`cfa3c0a`** = `origin/main` |
| 근거 | task-0121 Decision A · T3 분리, task-0122 §T3 |
| Owner 지정 | `status = selected_for_proposal`, `desired_outcome` 문장 확정 |
| 변경 파일 | 4 개 + 이 기록 |

## 조사에서 확인한 것 — 만들 것이 생각보다 적었다

**UI 와 계약은 이미 완성돼 있었다.**

| 계층 | 상태 |
| --- | --- |
| `web/app.js` | `현재 선택` · `원하는 결과` dt/dd 를 **이미 렌더링** |
| `owner_decision.py` 마크다운 렌더러 | `## Current Selection` **이미 존재** |
| `owner_decision.py` 계약 | selected 상태를 **이미 지원** (실측으로 수용 확인) |
| **master-plan 이 선택을 선언할 방법** | **없음** |
| **builder 가 그것을 읽는 경로** | **없음** — 두 값이 `None` 하드코딩 |

즉 T3 는 표시 계층이 아니라 **데이터 경로만의 문제**였다.

### task-0121 이 명시하지 않았던 제약

task-0121 은 "master-plan 필드 2 개 추가"라고만 적었는데, `MASTER_PLAN_FIELDS`
에 그냥 넣으면 **필수 필드가 된다.** `read_master_plan_snapshot` 의 missing 검사가
전체 집합을 대조하기 때문이다.

그런데 선택값은 본질적으로 optional 이다 — `owner_decision.py` 가
*"unselected status must not contain a workstream or desired outcome"* 을 강제하므로
`selection_required` 상태에서는 **반드시 없어야** 한다.

그래서 **별도 optional 테이블**을 신설했다. 이것이 이번 구현의 핵심 설계 판단이다.

## 무엇을 바꿨나

### `run_web_app.py`

| 변경 | 내용 |
| --- | --- |
| `MASTER_PLAN_OPTIONAL_FIELDS` 신설 | 필수 19 개와 **분리된** 2 개 |
| 파싱 루프 | 필수에서 못 찾으면 optional 에서 조회. 중복·길이 검사는 기존 그대로 적용 |
| missing 검사 | **필수 테이블만** 대조 |
| 부재 처리 | `setdefault(key, None)` — 빈 문자열이 아니라 **None**. 그래야 계약이 "선언 없음"으로 읽는다 |
| ID 검증 | `selected_workstream_id` 에 `[a-z0-9][a-z0-9_-]{0,63}` 적용 (기존 ID 검증과 같은 자리) |

### `owner_decision_data.py`

`None` 하드코딩 2 줄을 `_optional_text` 조회로 교체했다. 새 헬퍼는 값이 없으면
`None` 을, 있으면 기존 `_required_text` 검증을 그대로 통과시킨다.

### `docs/master-plan.md`

§2 에 두 줄을 선언하고 `status` 를 `selected_for_proposal` 로 바꿨다.

```text
- Owner decision status: selected_for_proposal
- Owner decision recommendation: jarvis-console
- Owner decision selected workstream: jarvis-console
- Owner decision desired outcome: Jarvis Console을 Jarvis task lifecycle 화면으로 축소해 실제 작업에 반복 사용한다
```

## 결과

| | 이전 | 이후 |
| --- | --- | --- |
| `owner_decision.status` | `selection_required` | **`selected_for_proposal`** |
| `selected_workstream_id` | `null` | **`jarvis-console`** |
| `desired_outcome` | `null` | Owner 확정 문장 |
| UI `현재 선택` | `Not selected` | **`jarvis-console`** |
| payload 키 수 | 13 | **13 (무변경)** |

task-0121 이 기록한 문서 내부 모순 — Owner Dashboard 는 승인 완료라 하고 §2 는
아직 못 골랐다고 하던 것 — 이 해소됐다.

## 계약 유지 확인

Owner 가 지시한 다섯 가지 거부 규칙이 전부 그대로다.

| 규칙 | 상태 |
| --- | --- |
| optional 필드가 없으면 기존 동작 유지 | **유지** — 두 값 `None`, 나머지 필드 전부 동일 |
| `selected_for_proposal` 은 두 값 없이 계속 거부 | **유지** — 한쪽만 있어도 거부 |
| `selection_required` 에 선택값이 있으면 거부 | **유지** |
| 후보가 아닌 workstream 거부 | **유지** |
| ID 형식·길이 검증 | **유지** — 64 자 수용 / 65 자 거부로 경계 양쪽 고정 |
| `owner_decision.py` 계약 | **무변경** |
| API response shape | **무변경** (13 키) |
| `web/app.js` | **무변경** |

## mutation probe — 7/7

| 변형 | 결과 |
| --- | --- |
| T1 optional 필드를 필수로 | **CAUGHT** |
| T2 부재 시 빈 문자열로 | **CAUGHT** |
| T3 selected workstream ID 검사 제거 | **CAUGHT** |
| T4 builder 가 선택을 무시 | **CAUGHT** |
| T5 builder 가 outcome 을 버림 | **CAUGHT** |
| T6 plan 에서 선택 줄 삭제 | **CAUGHT** |
| T7 plan 이 후보 아닌 workstream 지정 | **CAUGHT** |

## 기존 assertion 수정 3 건 — 삭제가 아니라 강화

정직하게 남긴다. 이번에 기존 단언을 손댔고, 각각 이유가 있다.

| 위치 | 무엇이었나 | 어떻게 바꿨나 |
| --- | --- | --- |
| `_test_project_control_snapshot` 정확 비교 | 파싱 결과 dict 전체 비교 | optional 2 키를 `None` 으로 **추가** (부재가 빈 문자열이 아님을 함께 고정) |
| `selected_without_selection_data` 거부 단언 | **T3 가 제거하는 제약 자체를 고정**하고 있었다 | 그 단언은 **그대로 두고**, 반쪽만 채운 경우 · 후보 아닌 경우 · unselected 에 값이 있는 경우 · **수용되는 경우**를 추가 |
| live payload 의 `status == "selection_required"` (2 곳) | 특정 문서 값 하나를 고정 | **snapshot 과 일치하는지**로 교체하고, 선택 유무가 status 종류와 맞는지 양방향 단언 추가. 다음 Owner 결정에도 살아남는다 |

## 테스트

`_test_master_plan_optional_selection_fields` 를 추가했다. 실제 master-plan 을
읽어 선언된 두 줄을 **문서에서 뽑아** 쓰므로 문장이 바뀌어도 stale 해지지 않는다.

| 검사 | 내용 |
| --- | --- |
| 두 테이블이 서로소 | 라벨·키 양쪽 |
| 두 줄 제거 시 나머지 필드 **완전 동일** | 하위호환 증명 |
| 대문자·공백 ID 거부 | |
| 64 자 수용 / 65 자 거부 | 경계 양쪽 |
| outcome 500 자 초과 거부 | |
| 같은 라벨 중복 거부 | |

## 바꾸지 않은 것

| 대상 | 상태 |
| --- | --- |
| task-0126 ancestry 검증 | **무변경** — diff 에 관련 줄 0 건 |
| `MAX_COMMITS = 5` · `recent_milestone_evidence.py` | **무변경** — 파일 자체가 변경 목록에 없음 |
| master-plan §4 historical hash 2 건 | **무변경** — `325fe500`, `a11c9536` |
| `owner_decision.py` · `web/app.js` · `README.md` | **무변경** |
| `jarvis.bat` | **접근하지 않음** |
| 선택을 바꾸는 write path / UI | **추가하지 않음** — Console 은 계속 read-only |
| D2 · D3 · D4 | **추가하지 않음** |

## 남은 것

| 항목 | 상태 |
| --- | --- |
| 카드가 계속 `attention` | 정상 — §2 `Approval state: required` 때문이며 실제로 참인 승인 대기다 |
| §2 `Last verified` · `verified_implementation_head` 가 2026-07-23 | 문서 신선도 문제로 남되 blocked 를 만들지 않는다 |
| D3 · D4 | 필요해지면 독립 주제 |
