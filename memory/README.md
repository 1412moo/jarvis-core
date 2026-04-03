# Memory

이 폴더는 작업 상태를 기록하는 저장소다.

- `memory/tasks/`: 개별 작업(Task) 기록
- 사람이 직접 읽고 수정 가능한 Markdown 기반 기록을 우선한다.

## 새 Task 작성 시 참고 파일
- 모델 기준: `docs/task-model.md`
- 템플릿: `memory/tasks/task-template.md`
- 기존 예시: `memory/tasks/task-0001-bootstrap.md`, `memory/tasks/task-0002-report-system.md`

## 템플릿 사용 방법
1. `memory/tasks/task-template.md`를 복사해 `task-####-slug.md` 파일을 만든다.
2. 헤더(`task-####-slug`)와 `id`를 동일하게 맞춘다.
3. 필수 필드(`id, title, status, repo, created_at, updated_at, summary`)를 모두 채운다.
4. `status`는 정의된 6개 값만 사용한다.
5. `summary`는 1~3문장으로 범위와 확인 필요사항을 적는다.

## 수동 생성 절차(요약)
1. 다음 순번의 Task ID를 정한다.
2. 템플릿 복사 후 값 입력.
3. UTC 시각(`created_at`, `updated_at`) 기록.
4. 내용 검토 후 커밋하고, 상태 변경 시 `updated_at`를 함께 갱신한다.
