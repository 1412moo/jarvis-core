# task-0098-console-on-hold-status-vocabulary

- id: `task-0098-console-on-hold-status-vocabulary`
- title: `Console status 어휘에 공식 상태값 ON_HOLD 편입`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-09 08:50 UTC`
- updated_at: `2026-09-09 08:50 UTC`
- summary: `ON_HOLD 는 task-0041 Owner 결정으로 편입된 7 번째 공식 status 인데 Console 의 TASK_VIEW_STATUS_RULES 만 6 개짜리 옛 어휘를 들고 있어서, 문서대로 ON_HOLD 를 쓴 task 가 invalid_status 로 떨어져 Needs metadata review 에 표시됐다. 규칙 표에 항목 하나를 추가해 needs_attention rank 25 로 분류한다. 진짜 원인은 어휘가 네 곳에 복제된 구조라, TASK_ALLOWED_STATUSES 와 대조하는 표류 방지 가드를 함께 넣었다. 이 가드가 있었다면 2026-08-28 에 즉시 잡혔을 결함이다. 기존 6 개 status 와 group 집합 reason code 는 무변경이고 새 transition 도 없다.`
- source_command: `task-0097 후속 조사에서 확정한 ON_HOLD 정책에 따른 최소 수정 지시`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | **`e3db1df`** = `origin/main` |
| 직전 작업 | task-0097 (bounded read 를 header block 으로 한정) |
| 변경 파일 | `run_web_app.py` · `run_smoke_tests.py` · `web/app.js` + 이 기록 |

## 원인

Console 의 `TASK_VIEW_STATUS_RULES` 는 status 어휘를 **독립적으로 다시 선언**한다.
모델·템플릿·writer 와 같은 출처를 쓰지 않는다.

| 시각 | 커밋 | 내용 |
| --- | --- | --- |
| 2026-07-24 | `e1e0c0b` | Console task view 도입. 규칙 표 **6 개** — 당시 모델이 6 개였으므로 정확했다 |
| 2026-08-28 | `8843488` | Owner 결정으로 ON_HOLD 편입. `docs/task-model.md` · `task-template.md` · `task_file_writer.py` · `reports/README.md` · **Console README** 갱신 |
| — | — | `TASK_VIEW_STATUS_RULES` 는 `e1e0c0b` 이후 **한 번도 수정되지 않음** |

`8843488` 은 같은 앱의 README 까지 손대면서 `run_web_app.py` 는 놓쳤다. 모델을
넓힐 때 전파가 네 번째 사본에서 끊긴 것이다.

근거는 task-0041 의 `[2026-08-28 10:10 UTC Owner 결정]` ② 항이다.

> `ON_HOLD` 를 공식 상태값으로 편입(6개 → 7개)

`docs/task-model.md:20` 이 의미까지 규정한다.

> `ON_HOLD`: Owner의 우선순위 판단으로 의도적 보류 (외부 요인이 아니라는 점에서
> `BLOCKED`와 구분)

결과적으로 [run_web_app.py:1520](../../apps/jarvis-console/run_web_app.py) 의
`TASK_VIEW_STATUS_RULES.get(status)` 가 `None` 을 반환해 `invalid_status` →
`metadata_review` 로 떨어졌다. **문서대로 쓴 정상 task 가 형식 불량으로 표시**되는
오판정이며, task-0096(파서)·task-0097(reader)과 같은 계열이되 이번엔 어휘 표가
원인이다.

의도적 제외가 아니라는 근거 세 가지.

- 규칙 표 주변에 제외 사유 주석이 없다. 이 저장소는 의도적 결정에 반드시 task 번호
  주석을 남긴다(task-0054 · task-0096 · task-0097).
- `invalid_status` 테스트가 전부 가짜 값(`UNKNOWN` · `WEIRD`)을 쓴다. ON_HOLD 를
  거부 대상으로 고정한 테스트가 없었다.
- smoke 의 `expected_status_rules` 는 production dict 를 비교하지 않고 **별도
  리터럴로 재선언**한 것이라, 두 사본이 갈라져도 아무도 알아채지 못했다.

## 무엇을 바꿨나

규칙 표에 항목 하나. `display_rank` 가 10 단위로 띄어져 있어 기존 번호는 그대로다.

```python
"ON_HOLD": (
    "needs_attention",
    25,
    "Review the summary and make the required decision outside Jarvis Console.",
),
```

`next_action` 은 `NEEDS_APPROVAL` 문구를 그대로 재사용한다. 둘 다 Owner 판단을
기다리는 상태이고, 새 문구를 만들면 `web/app.js` 가 검사하는 문자열 계약이 늘어난다.

rank 25 는 `BLOCKED`(20) 뒤 `FAILED`(30) 앞이다. ON_HOLD 는 이미 Owner 가 보류를
결정한 상태라 외부 요인으로 막힌 `BLOCKED` 보다 뒤에 둔다.

`web/app.js` 의 frozen display order 문장도 같은 자리에 ON_HOLD 를 넣었다. 기존
순서는 건드리지 않았다.

## 표류 방지 가드

이번 수정의 핵심은 항목 추가가 아니라 **다음 번에 같은 일이 반복되지 않게 하는 것**
이다. 어휘가 네 곳에 복제돼 있고 아무도 대조하지 않은 것이 진짜 원인이었다.

같은 파일에 이미 필드 어휘용 선례가 있었다.

```python
assert run_web_app.TASK_ALLOWED_METADATA == (
    run_web_app.TASK_VIEW_ALLOWED_FIELDS
)
```

status 용 가드를 그 바로 옆에 같은 모양으로 붙였다.

```python
assert run_web_app.TASK_ALLOWED_STATUSES == frozenset(
    run_web_app.TASK_VIEW_STATUS_RULES
)
```

`TASK_ALLOWED_STATUSES` 를 `task_file_writer` 에서 import 하는 방식도
`TASK_ALLOWED_METADATA` 가 이미 쓰던 그대로다. 이 가드가 있었다면 `8843488`
시점에 즉시 실패했을 것이고, 8 번째 상태값이 생겨도 자동으로 잡힌다.

## 테스트

| 추가 | 내용 |
| --- | --- |
| `expected_status_rules` | `ON_HOLD → ("needs_attention", 25, 문구)` 튜플 고정. 기존 루프가 실제 파싱까지 검증한다 |
| projection | ON_HOLD record 가 `project_task_view_items` 를 통과해 `valid` / reason 없음 / `needs_attention` / rank 25 |
| vocabulary guard | `TASK_ALLOWED_STATUSES == frozenset(TASK_VIEW_STATUS_RULES)` |
| writer transition | `all_statuses` 에 ON_HOLD 추가. 7 개 status 전 쌍에서 허용 전이 6 개 외 전부 거부됨을 확인 |

마지막 항목이 writer 쪽 최소 커버리지다. writer 는 ON_HOLD 를 **저장·검증**하지만
`TASK_STATUS_TRANSITIONS` 에 ON_HOLD 쌍이 하나도 없어 **전이시키지는 못한다**.
task-0041 이 기록한 대로 ON_HOLD 는 직접 편집으로만 설정된다. 어휘를 넓힌 것이
전이를 넓히지 않았음을 이 테스트가 고정한다.

기존 `invalid_status` 테스트는 가짜 값을 쓰므로 그대로 두었다.

## mutation probe

`TASK_VIEW_STATUS_RULES` 에서 ON_HOLD 항목을 제거하면 **vocabulary guard 가 가장
먼저 실패**한다(smoke exit=1). 항목만 되돌리고 가드는 남는 조합이 불가능하다는
확인이다.

## 확인 결과

```text
parse_state : valid
reason_code : None
group_id    : needs_attention
display_rank: 25
status      : ON_HOLD

console statuses : ['BLOCKED','DOING','DONE','FAILED','NEEDS_APPROVAL','ON_HOLD','TODO']
writer statuses  : ['BLOCKED','DOING','DONE','FAILED','NEEDS_APPROVAL','ON_HOLD','TODO']
sets equal       : True
```

착수 시점 ON_HOLD 를 실제로 쓰는 task record 는 **0 건**이었다. 사용자에게 보이던
피해는 없었고 잠복 결함이었다. 지금은 문서대로 써도 안전하다.

## 바꾸지 않은 것

| 대상 | 상태 |
| --- | --- |
| 기존 6 개 status 의 group · rank · next_action | 무변경 |
| `TASK_VIEW_GROUPS` | 무변경 |
| `TASK_VIEW_REASON_CODES` (9 개) | 무변경 |
| `TASK_STATUS_TRANSITIONS` | 무변경 — 새 전이 없음 |
| `parse_task_view_text` · `read_task_view_text` (task-0096 · task-0097) | 무변경 |
| `task_file_writer.py` · `docs/task-model.md` · `task-template.md` | 무변경 |
| app.js 의 기존 display order | 순서 유지, ON_HOLD 만 삽입 |

`git diff --check` clean. `run_web_app.py` CRLF, `run_smoke_tests.py` 와 `app.js`
LF 유지.
