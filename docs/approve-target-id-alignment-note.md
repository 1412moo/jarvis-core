# /approve target vs task id 정합성 메모 (현 단계 기준)

[Document Type]
- note

## 목적
- `/approve target` 형식 계약과 실제 task id 체계의 차이를 **기능 변경 없이** 명확히 기록한다.
- 다음 단계에서 정렬 방향을 선택할 때 기준 문서로 사용한다.

## 계층별 현재 규칙

### 1) parser target format (`orchestrator/discord-intake/intake_parser.py`)
- `/approve <target> <decision>`에서 target은 `^task-\d{4}$`일 때만 형식 통과로 본다.
- 불일치 시 hold: `unrecognized_target_format`.
- 예시
  - 통과: `task-0007`
  - hold: `task-0007-discord-intake`

### 2) task model id (`docs/task-model.md`)
- Task ID 규칙은 `task-####-slug`.
- 예시: `task-0007-discord-intake`.

### 3) file name / file path (`memory/tasks/*.md`, `task_file_writer.py`)
- 실제 task 파일명은 `<task_id>.md`.
- 생성되는 task_id도 `task-####-slug` 형식이다.
- 즉 파일 경로는 `memory/tasks/task-####-slug.md`가 기준이다.

### 4) status lookup id (`adapters/discord/bot_minimal.py`)
- `/status`는 `^task-\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*$`만 허용한다.
- 즉 short id(`task-0007`)는 `/status`에서 invalid format이다.

### 5) approve runtime id (`adapters/discord/bot_minimal.py`)
- `/approve` runtime은 `<task-id>` 문자열을 그대로 받아 `memory/tasks/<task-id>.md`를 조회한다.
- usage 문구/README 예시는 full id(`<task-id>`, 실제 운영상 `task-####-slug`)를 전제로 한다.

## 현재 충돌 지점 (정확)
1. parser 계층의 `/approve target` 규칙(`task-####`)과 task model/file/status 계층 규칙(`task-####-slug`)이 다르다.
2. parser 예시에서 자연스러운 short id(`task-0007`)는 runtime 파일 조회 기준과 직접 호환되지 않는다.
3. 문서들 간에 `/approve` 인자 명칭이 `target`/`task-id`로 혼재되어 동일 계층 규칙처럼 읽힐 수 있다.

## 현재 운영 기준 (이번 단계 결론)
- **운영 기준은 full task id(`task-####-slug`)를 단일 식별자로 사용**한다.
- parser의 `target` 정규식(`task-####`)은 현재 “intake parser contract 계층의 제한 규칙”으로만 본다.

## 다음 단계 정렬 방향 (최대 2개)
1. parser를 full task id(`task-####-slug`) 기준으로 확장한다. (parser regex/contract 동기화)
2. short id alias(`task-####`)를 명시 도입하고, runtime에서 alias→full id 해석 단계를 추가한다.

> 본 문서는 기준 정리만 수행하며, 이번 단계에서 parser/runtime 동작은 변경하지 않는다.
