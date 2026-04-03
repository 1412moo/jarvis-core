# Approve Flow

## 목적
- `/approve`는 승인 대기 상태의 task에 대해 진행 여부를 명시적으로 결정하는 명령이다.
- 위험 작업을 승인 없이 실행하지 않기 위해 승인 게이트를 둔다.

## 입력 형식
- `/approve <task-id> approve`
- `/approve <task-id> reject`

## 상태 전이
### 허용
- `NEEDS_APPROVAL -> DOING` (`approve` 입력 시)
- `NEEDS_APPROVAL -> FAILED` (`reject` 입력 시)

### 비허용
- `DONE -> DOING`
- `FAILED -> DOING`
- `DOING -> DOING` (중복 승인)
- `TODO -> DOING` (`/approve`로 직접 시작 금지)

## 승인 조건
- 승인 대상은 상태가 `NEEDS_APPROVAL`인 task로 한정한다.
- 아래 조건에 해당하면 자동 hold(상태 유지)한다.
  - task가 존재하지 않거나 `task-id`가 일치하지 않음
  - 상태가 `NEEDS_APPROVAL`이 아님
  - 입력 형식이 `/approve <task-id> approve|reject`를 만족하지 않음

## 실행 트리거
- `approve` 수신 후 다음 흐름을 연결한다.
  - parser: `/approve` 명령 파싱
  - draft: 상태 변경 초안 생성
  - file writer: markdown task 상태 반영
  - memory/tasks: 최신 상태 기록
- 본 문서는 상태 변경 트리거 구조만 정의하며, 실제 코드 실행은 포함하지 않는다.

## 안전 규칙
- 승인 없는 실행은 금지한다.
- 위험 작업 기준은 다음과 같다.
  - 파괴적 변경(삭제, 덮어쓰기, 롤백 어려운 변경)
  - 대규모 삭제 또는 대량 변경
  - 운영 영향 작업(서비스 중단, 설정 변경, 배포 반영)

## 현재 비범위
- 실제 코드 실행
- GitHub API 연동
- 자동 배포
