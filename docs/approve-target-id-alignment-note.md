# /approve target vs task id 정합성 메모 (현 단계 기준)

[Document Type]
- note

## 목적
- `/approve target` 형식을 현재 운영 기준(full task id)으로 정렬한 결과를 기록한다.
- short id alias는 이번 단계 범위 밖임을 명확히 남긴다.

## 계층별 현재 규칙

### 1) parser target format (`orchestrator/discord-intake/intake_parser.py`)
- `/approve <target> <decision>`에서 target은 `^task-\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*$`일 때만 형식 통과로 본다.
- 불일치 시 hold: `unrecognized_target_format`.
- 예시
  - 통과: `task-0007-discord-intake`
  - hold: `task-0007`

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

## 정렬 결과 (이번 단계)
1. parser 계층 `/approve target` 규칙이 task model/file/status 계층과 동일한 full id(`task-####-slug`)로 정렬되었다.
2. short id(`task-####`)는 parser 단계에서 `unrecognized_target_format` hold로 처리된다.
3. 문서 기준도 full id 기준으로 동기화한다.

## 현재 운영 기준 (이번 단계 결론)
- **운영 기준은 full task id(`task-####-slug`)를 단일 식별자로 사용**한다.
- parser의 `target` 정규식도 동일 기준(`task-####-slug`)을 사용한다.

## 다음 단계 정렬 방향 (최대 2개)
1. short id alias(`task-####`)를 명시 도입할지 별도 결정한다.
2. alias 도입 시 runtime에서 alias→full id 해석 단계를 추가한다.

> 본 문서는 full id 정렬 결과를 기록하며, alias 기능은 포함하지 않는다.
