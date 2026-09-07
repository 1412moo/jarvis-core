# task-0084-console-unused-import-removal

- id: `task-0084-console-unused-import-removal`
- title: `Console 미사용 import 제거`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-08 01:25 UTC`
- updated_at: `2026-09-08 01:25 UTC`
- summary: `후속 후보로 기록해 둔 미사용 import 13건을 제거하려다 3건이 실제로는 cross-module re-export 임을 발견해 10건만 제거했다. run_web_app 의 TASK_ALLOWED_METADATA, CompletionEvidenceWriteResult, TaskStatusTransitionResult 는 파일 안에서는 안 쓰이지만 smoke 가 run_web_app.X 로 접근한다. 지웠으면 AttributeError 로 suite 가 깨졌다. 내 이전 13건 집계는 파일 단위 분석의 한계였고 이 기록으로 정정한다. 2파일 +0 -12, 전 회귀 통과.`
- source_command: `task-0083 후속 후보 — 미사용 import 제거 지시`

## 기준선

HEAD `2cd04b9` = `origin/main`, tracked 변경 0에서 시작.
2파일, **+0 / -12**. 순수 삭제.

## 13건이 아니라 10건인 이유 — 이전 집계 정정

task-0081·0083 기록에 "기존 미사용 import 13건"으로 남겼다. 그 집계는
**각 파일 안에서만** 참조를 셌다. 다른 모듈이 `run_web_app.X` 속성으로 접근하는
경우를 보지 못했다.

전수 확인 결과 3건이 실제 사용 중이었다.

| 심볼 | 소비처 |
| --- | --- |
| `TaskStatusTransitionResult` | `run_smoke_tests.py:2048`, `:2104` — `run_web_app.TaskStatusTransitionResult(...)` |
| `TASK_ALLOWED_METADATA` | `run_smoke_tests.py:3106` — `run_web_app.TASK_ALLOWED_METADATA` |
| `CompletionEvidenceWriteResult` | `run_smoke_tests.py:3512` — `run_web_app.CompletionEvidenceWriteResult(...)` |

`run_web_app.py` 가 `task_file_writer` 심볼을 재수출하고 smoke 가 그것을 통해
쓰는 구조다. 지웠으면 `AttributeError` 로 suite 가 깨졌다.

`TemporaryDirectory` 는 smoke 에도 5건 나오지만 그건 smoke **자신의** import 이고
`run_web_app` 것과 무관하다. 그래서 이 하나는 제거 가능했다.

## 제거한 10건 / 12줄

### `run_web_app.py` — 4줄

`import base64` / `import math` / `import uuid` / `from tempfile import TemporaryDirectory`

각 파일 내 raw 등장 1회(= import 줄 자신)뿐이고 다른 모듈의 속성 접근도 없다.

### `run_smoke_tests.py` — 8줄

- `from contextlib import nullcontext`
- `from types import SimpleNamespace`
- `from hermes_manager_pilot.approval_binding import build_scope_approval_binding`
- `from hermes_manager_pilot.prompt_queue import (REQUIRED_FORBIDDEN_ACTIONS, normalize_prompt_queue)` — 두 이름 모두 미사용이라 statement 째
- `from hermes_manager_pilot.schemas import ValidationError`

`run_smoke_tests.py` 를 import 하는 모듈은 저장소에 없으므로 재수출 위험이 없다.

## 확인한 위험 3가지

1. **cross-module 속성 접근** — 위에서 3건 발견, 보존.
2. **문자열 기반 사용** — 소스를 스캔하는 테스트가 심볼 이름을 문자열로 검사할
   수 있다. 후보 전부에 대해 raw grep 으로 확인했고 import 줄 외 등장 0건이었다.
3. **hermes 모듈 로드 부작용** — `prompt_queue` / `schemas` / `approval_binding`
   import 를 지우면 그 모듈이 로드되지 않는다. 콘솔이 실제로 쓰는
   `director_reporting` 과 `manager_reporting_data` import 는 그대로 남으므로
   `hermes_manager_pilot` 패키지는 여전히 로드된다. hermes 자체 suite 도 통과 확인.

## closure 재검증

| 검사 | `run_web_app.py` | `run_smoke_tests.py` |
| --- | --- | --- |
| `ast.parse` | OK | OK |
| dangling names | `__file__` 만 | 동일 |
| 남은 파일 내 미사용 import | `annotations`(`__future__` 지시자) + 재수출 3건 | `annotations` 만 |

`__future__ import annotations` 는 정적 분석의 구조적 false positive 라 대상이 아니다.

## 검증 결과

| 검증 | 결과 |
| --- | --- |
| Console self-test | PASS |
| Console smoke + browser shell | PASS |
| KEEP route probe | 13/13 PASS |
| canonical 전수 | 74/74 PASS |
| SOP | status=PASS |
| bot self-check | 92/92 PASS |
| discord-intake | 97/97 PASS |
| audit-chain | 7 passed, 0 failed |
| **hermes-manager-pilot** | PASS |
| buzz-bridge | 37/37 PASS |
| discord-nl-intent | 35/35 PASS |
| check_no_secrets --self-test | failures=0, PASS |
| node --check | OK |
| git diff --check | clean |
| task-0078 guard mutation probe | PASS, byte identity 유지 |

line ending 유지 — `run_web_app.py` CRLF 4371, `run_smoke_tests.py` LF 5409.

## 무변경

`web/` 전체, README, master-plan, `skills.json`, Research Council, Hermes 본체,
Discord, audit-chain. 항진 assert 와 `.jarvis-local` 중복 검사도 손대지 않았다.

## 남은 후속 후보

- 항진 assert 4건 (`before_* == after_*`, `git status` 를 자기 자신과 비교)
- `.jarvis-local` 중복 검사 — run_web_app 3건 중 2건, smoke 4건 중 3건
- README 의 Memory / Skills 섹션(~48줄)과 D1 충돌 문구
- `skills.json` 의 `tasks_reports` 카드 문구
