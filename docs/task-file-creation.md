# Task File Creation (MVP)

[Document Type]
- contract

이 문서는 `task draft object`를 받아 `memory/tasks/*.md` 실제 파일 1개를 생성하는 최소 로컬 규칙을 정의한다.

> 참고: `run_intake_demo.py --no-write` dry-run 경로는 동일한 검증/번호 계산 규칙을 따르되,
> `result_type="would_create"`만 반환하고 실제 파일은 생성하지 않는다.

## 1) 생성 흐름 (draft object → task file)

1. draft 입력 검증
   - 필수: `title`, `repo`, `summary`
   - `status`가 있으면 `TODO`만 허용
   - slug 생성 가능한 title인지 확인
2. `memory/tasks/`의 기존 파일 스캔
   - `task-####-slug.md` 패턴 파일만 번호 집계
   - 이상한 파일명은 무시
3. 다음 번호 계산
   - `max(existing_number) + 1`
   - 기존 파일이 없으면 `0001`
4. slug 생성
   - title 기반 소문자 slug 생성 (영문/숫자/하이픈)
   - ASCII slug가 비면 `task` fallback을 사용하고 Unicode title은 그대로 보존
5. id/파일명 확정
   - `id = task-####-slug`
   - `filename = task-####-slug.md`
6. 본문 렌더링
   - `memory/tasks/task-template.md` 형식(헤더 + bullet metadata)을 따름
   - `status=TODO`
   - `created_at`, `updated_at` 동일 UTC 시각으로 초기화
   - `title`, `repo`, `summary`, `id` 반영
   - `source_command`가 있으면 선택적으로 하단 메타에 포함 (현재 intake draft 기준 값은 `/task`)
7. 파일 생성
   - 같은 디렉터리의 attempt 전용 임시 파일에 write/flush/fsync/close
   - 완성된 임시 파일을 atomic no-overwrite publish
   - publish 전 실패 시 최종 `task-*.md`를 남기지 않고 이번 attempt의
     임시 artifact만 정리
   - 성공 시 created 결과 반환
   - `9999` 다음 번호는 생성하지 않고 `task_number_limit_reached`로 fail closed

## 2) 파일명 생성 규칙

- 형식: `task-0004-some-slug.md`
- 정규식: `^task-(\d{4})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$`
- 4자리 번호는 0-padding 고정
- slug는 소문자 영숫자 + 하이픈만 허용

## 3) id 할당 규칙

- id 형식: `task-####-slug`
- 번호는 기존 유효 파일 기준 최대 번호 + 1
- 번호 충돌이 감지되면 다음 번호를 재시도
- 최대 재시도 횟수(예: 10회) 초과 시 error 반환
- 다음 번호가 `10000`이면 4자리 ID 계약을 넓히지 않고
  `task_number_limit_reached` error를 반환

## 4) slug 생성 규칙

- 입력: draft `title`
- 처리:
  - 소문자 변환
  - 영숫자가 아닌 문자는 `-`로 치환
  - 연속/양끝 하이픈 정리
- 결과가 빈 문자열이면 고정 fallback `task` 사용

### 비ASCII(한글 포함) 제목 정책
- 사람이 읽는 Unicode title은 정규화 결과를 그대로 보존한다.
- ASCII slug가 비면 고정 fallback `task`를 쓴다.
- 의미가 달라질 수 있는 자동 transliteration은 하지 않는다.
- 순번이 ID 고유성을 제공하므로 서로 다른 한국어-only 제목은
  `task-0004-task`, `task-0005-task`처럼 공존한다.

예시:
- `Parser Output 검증 규칙 보강` → `parser-output`
- `보고 시스템 개선` → `task`

### metadata 안전 경계

- title 최대 120자, repo 최대 80자, summary 최대 500자,
  source_command 최대 80자다.
- inline-code metadata 구분자인 backtick, CR/LF newline과 Unicode control/format
  문자는 거절한다.
- Voice Inbox의 여러 줄 rough thought는 writer 앞에서 한 줄 Title/Summary로
  정규화한다. raw transcript는 task 파일에 저장하지 않는다.

## 5) created_at / updated_at 기록 규칙

- 둘 다 UTC, 포맷: `YYYY-MM-DD HH:mm UTC`
- 최초 생성 시 두 값을 **동일 시각**으로 기록
- 이후 수정 단계에서만 `updated_at` 갱신

## 6) 번호 충돌 처리 원칙

- 1차: 파일 스캔 기반으로 다음 번호 계산
- 2차: 파일 존재 확인(`path.exists()`)
- 3차: 원자적 생성(`open('x')`)에서 충돌 발생 시 번호 +1 재시도
- 안전 실패: 반복 충돌 시 `failed_to_allocate_task_number` error 반환
- 4자리 번호 한계 뒤에는 `task_number_limit_reached` error 반환

## 7) 파일 생성 중단(hold/error) 조건

### hold
- `title` 누락
- `repo` 누락
- `summary` 누락
- `status`가 TODO 이외 값
- title/repo/summary/source_command의 unsafe newline, backtick 또는 control 문자
- 허용 길이 초과

### error
- `memory/tasks/` 디렉터리 없음
- 번호 할당 재시도 한도 초과
- 4자리 번호 한도 초과
- 기타 파일 시스템 예외(필요 시 상위에서 처리)

## 8) 로컬 실행 예시

아래는 `python3 orchestrator/discord-intake/task_file_writer.py` 실행 시 기대되는 형태 예시다.

### 입력 예시 1 (정상)
```json
{
  "title": "report-system-improvement",
  "status": "TODO",
  "repo": "jarvis-core",
  "summary": "보고 체계 문서 구조를 개선하는 task 파일을 생성한다.",
  "source_command": "/task"
}
```

예상 결과(예):
```json
{
  "result_type": "created",
  "file_path": "memory/tasks/task-0004-report-system-improvement.md",
  "task_id": "task-0004-report-system-improvement",
  "summary": "task file created",
  "reason": null
}
```

### 입력 예시 2 (정상)
```json
{
  "title": "parser-output-validation-rules",
  "status": "TODO",
  "repo": "jarvis-core",
  "summary": "파서 결과의 누락/형식 오류 검증 규칙을 명확히 한다.",
  "source_command": "/task"
}
```

예상 결과(예):
```json
{
  "result_type": "created",
  "file_path": "memory/tasks/task-0005-parser-output-validation-rules.md",
  "task_id": "task-0005-parser-output-validation-rules",
  "summary": "task file created",
  "reason": null
}
```

### 입력 예시 3 (실패/hold)
```json
{
  "title": "   ",
  "status": "TODO",
  "repo": "jarvis-core",
  "summary": "잘못된 입력 예시"
}
```

예상 결과:
```json
{
  "result_type": "hold",
  "file_path": null,
  "task_id": null,
  "summary": null,
  "reason": "missing_required_field:title"
}
```

## 9) 기존 문서와 정합성

- `docs/task-model.md`
  - id 형식(`task-####-slug`), 상태 기본값 TODO, UTC 기록 규칙과 일치
- `memory/tasks/task-template.md`
  - 헤더 + 메타 bullet 형식을 동일하게 사용
- `docs/intake-to-task-draft.md`
  - 기존 문서는 draft 생성 범위를 정의하고, 본 문서는 그 다음 단계(파일 생성)를 정의
  - 충돌 없음(단계 분리)
