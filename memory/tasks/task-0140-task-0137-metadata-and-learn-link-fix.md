# task-0140-task-0137-metadata-and-learn-link-fix

- id: `task-0140-task-0137-metadata-and-learn-link-fix`
- title: `task-0137 summary metadata 복구와 learn-baseline-candidate의 Recordroom 연결 정정`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-09-24 11:30 UTC`
- updated_at: `2026-09-24 11:36 UTC`
- summary: `task-0137 summary 안의 이스케이프된 백틱 2개 때문에 Console이 그 기록을 METADATA_REVIEW로 표시하고 writer 검증도 실패하던 문제를, 백틱 2개만 지우고 updated_at을 갱신해 고친다. learn.json의 learn-baseline-candidate가 내용과 무관한 rec-0004에 연결돼 있던 것을 task-0136을 다루는 rec-0026으로 바꾼다. DONE은 Reviewer/QA 후 Owner가 Console Complete로 결정한다.`
- source_command: `Owner 지시: task-0140으로 task-0137 metadata와 learn-baseline-candidate 연결을 최소 수정`

## 기준선

| 항목 | 값 |
| --- | --- |
| baseline | `e567a9a06f187718f4bd4103a8b84cc6144bdb95` (`origin/main`과 같음) |
| 작업 전 상태 | tracked 수정 없음, untracked `jarvis.bat`만 |

## 근거 (read-only 조사)

### 1. task-0137 metadata

- Console `parse_task_view_text` 결과: `parse_state: invalid`, `reason_code: invalid_text`, `reason_field: summary`.
  writer `_transition_metadata` 결과: `task_file_invalid_metadata`.
- 원인: summary 값 안의 `\`6dd2352…\`` 두 백틱. Console `TASK_VIEW_METADATA_PATTERN`은 값에 백틱을 허용하지
  않는다(`[^`\r\n]*`). task-0054가 분류한 원인 A(metadata 값에 backtick)와 같다.
- 값 길이도 501자로 500자 상한을 1자 넘었다. 백틱 2개와 이스케이프 문자 2개를 지우면 497자가 된다.
- 다른 header 필드와 본문에는 문제가 없어 summary만 고치면 된다.
- summary는 6문장이라 task-template.md의 1~3문장 규칙에도 맞지 않지만, Console과 writer는 문장 수를
  검사하지 않는다. Owner 지시로 이번 범위에서 고치지 않는다.

### 2. learn-baseline-candidate

- 현재 `related_recordroom: ["rec-0004"]`. rec-0004는 task-0055 실행결과 원자적 쓰기 사건이라 내용과 무관하다.
- 항목의 jarvis_example은 task-0136 repair 2에서 SKILL.md 호출문 템플릿의 `Parent (baseline):` 한 줄이 parent와
  baseline을 같은 값으로 적은 결함이다. task-0136 기록 Repair 이력 2행에 같은 내용이 있다.
- Recordroom 26건 중 task-0136을 다루는 기록은 rec-0026뿐이다(what_happened와 issue_faced에 task-0136,
  related_links에 task-0136 기록).

## Owner 승인 원문

```text
task-0140 구현 진행해.

read-only 조사 결과대로 최소 수정만 한다.

1. memory/tasks/task-0137-jarvis-studyroom-v0-1.md
- summary의 백틱 2개만 제거
- summary 변경에 맞춰 updated_at 갱신
- 6문장 문제는 이번 범위에서 수정하지 않는다.

2. apps/studyroom/content/learn.json
- learn-baseline-candidate의 related_recordroom
- rec-0004 → rec-0026

3. memory/tasks/task-0140-*.md
- DOING 상태로 기록
- 위 두 수정의 근거와 검증 결과를 기록

다른 파일은 수정하지 마.

구현 후:
- task-0137 Console parser/writer 검증
- learn.json JSON/schema 및 rec-0026 존재 확인
- Studyroom smoke
- git diff --check
- 변경 범위 확인

그 다음 fresh Reviewer → QA 순서로 진행해.
Reviewer 호출 시 task-0139에서 추가한 baseline/evidence 방식과 jarvis-reviewer-call Skill을 사용해.

각 단계 결과는 PASS/FINDINGS와 핵심 내용만 보고해.
```

## Manager 요약 (승인 원문 조건별)

| # | 승인 원문 조건 | 처리 |
| --- | --- | --- |
| 1 | "task-0140 구현 진행해." / "read-only 조사 결과대로 최소 수정만 한다." | 아래 두 수정만 |
| 2 | "summary의 백틱 2개만 제거" | task-0137 9행 summary에서 `\`` 2개만 제거, 나머지 문장 무변경 |
| 3 | "summary 변경에 맞춰 updated_at 갱신" | task-0137 updated_at `2026-09-22 23:20 UTC` → `2026-09-24 11:30 UTC` |
| 4 | "6문장 문제는 이번 범위에서 수정하지 않는다." | 문장 수 무변경 |
| 5 | "learn-baseline-candidate의 related_recordroom" / "rec-0004 → rec-0026" | 그 한 값만 변경 |
| 6 | "DOING 상태로 기록" / "위 두 수정의 근거와 검증 결과를 기록" | 이 기록, status DOING |
| 7 | "다른 파일은 수정하지 마." | 변경 파일은 task-0137 기록, learn.json, 이 기록 3개 |
| 8 | 구현 후 검증 5항목 | 아래 검증 절 |
| 9 | "그 다음 fresh Reviewer → QA 순서로 진행해." | 검증 뒤 fresh Reviewer, 그 뒤 QA |
| 10 | "Reviewer 호출 시 task-0139에서 추가한 baseline/evidence 방식과 jarvis-reviewer-call Skill을 사용해." | Reviewer 호출에 baseline 전체 hash와 evidence path를 넣는다. Skill 사용 결과는 Reviewer 결과 절에 기록 |
| 11 | "각 단계 결과는 PASS/FINDINGS와 핵심 내용만 보고해." | Owner 보고 형식 |

## 검증 (Implementer 실행, QA 재현 대상)

| # | 항목 | 결과 |
| --- | --- | --- |
| V1 | task-0137 Console parser | `parse_state: valid`, `status: DONE` |
| V2 | task-0137 writer `_transition_metadata` | 오류 없음 |
| V3 | task-0137 summary | 497자, 백틱 0 |
| V4 | learn.json | JSON 정상, 18개, 스키마 키 동일, learn-baseline-candidate `related_recordroom: ["rec-0026"]`, rec-0026이 recordroom.json에 존재 |
| V5 | `python -B apps/studyroom/run_smoke_tests.py` | 5/5 PASS |
| V6 | `git diff --check` | exit 0 |
| V7 | 변경 범위 | task-0137 기록 2줄(summary, updated_at), learn.json 1줄, 이 기록 신규 |

## Repair 이력

retry_budget=1, retry_count=0, repair_budget=1, repair_count=0
