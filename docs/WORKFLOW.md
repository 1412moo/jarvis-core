# WORKFLOW

## 1) 현재 상태
- Discord bot 연결 완료
- `/task` 구현 완료
- `/status` 구현 완료
- `parser → draft → file writer → memory/tasks` 저장 흐름 연결 완료
- 로컬 테스트 및 Discord 테스트 성공

## 2) 프로젝트 구조
`Discord → intake_parser → task_draft_builder → task_file_writer → memory/tasks`

## 3) 작업 방식 (중요)
- 한 번에 기능 하나만 구현
- 단계별 진행: 기능 구현 → 테스트 → 다음 단계
- 리팩토링은 기능 검증 후 수행

## 4) 구현 원칙
- 최소 기능만 구현 (MVP)
- 읽기 전용 기능 우선
- 기존 동작 절대 깨지 않기
- side effect 금지
- 파일 수정/자동 생성 최소화
- 표준 라이브러리 우선
- 과한 리팩토링 금지

## 5) 현재 우선순위
1. `/report` 구현
2. 실제 사용 및 검증
3. 필요 시 구조 정리

## 6) 비범위
- DB 도입
- GitHub API 연동
- 웹 UI
- 상태 자동 변경
- 복잡한 리팩토링

## 7) 작업 요청 규칙
- 기존 코드 구조 먼저 분석
- 최소 diff로 수정
- 필요한 파일만 변경
- 추측 금지

## 8) Codex 출력 형식
1. 변경 파일 목록
2. 동작 요약
3. 코드
4. 테스트 방법
5. 비범위
6. 다음 작업
