# Reports Guide

`reports/` 는 작업 기록의 표준 저장소다. 모든 보고서는 Markdown(`.md`)으로 작성한다.

## 1) 작업 상태 정의
아래 상태 값만 사용한다.

- `TODO`: 시작 전. 우선순위/범위는 정의되었으나 실행 전 상태.
- `DOING`: 현재 진행 중. 결과가 확정되지 않은 상태.
- `BLOCKED`: 외부 요인/의존성으로 진행 불가 상태.
- `DONE`: 검증까지 완료된 상태.
- `FAILED`: 시도했으나 목표 달성 실패. 원인과 후속 조치 필요.
- `NEEDS_APPROVAL`: 승인 없이는 진행하면 안 되는 작업 상태.

## 2) 보고서 파일 이름 규칙
- Task 보고서: `task-YYYY-MM-DD-###-slug.md`
  - 예: `task-2026-04-03-001-report-standardization.md`
- Daily 보고서: `daily-YYYY-MM-DD.md`
  - 예: `daily-2026-04-03.md`

## 3) 날짜 형식 규칙
- 문서 내 모든 날짜는 `YYYY-MM-DD` 형식으로 기록한다.
- 시간까지 필요하면 UTC 기준 `YYYY-MM-DD HH:mm UTC` 를 사용한다.

## 4) 필수 섹션 목록
Task 보고서와 Daily 보고서 모두 아래 항목을 포함해야 한다.

1. 메타 정보(작성일, 작성자, 상태)
2. 작업 목적 또는 당일 요약
3. 변경/진행 내역
4. 검증 내역(명령/확인 결과)
5. 리스크/미완료 항목
6. 다음 작업
7. 금지 표현 점검

## 5) NEEDS_APPROVAL 사용 기준
아래 중 하나라도 해당하면 상태를 `NEEDS_APPROVAL` 로 기록한다.

- 파괴적 변경(대량 삭제, 롤백 어려운 수정)
- 운영 환경 영향 가능성이 있는 변경
- 보안/권한/비용/정책 리스크가 있는 변경
- 저장소 역할 경계를 넘는 변경(메인/서브 저장소 역할 혼합)

`NEEDS_APPROVAL` 상태에서는 아래를 반드시 기록한다.
- 승인 요청 항목
- 요청 사유
- 승인 지연 시 영향

## 6) 금지 표현
아래 표현은 근거 없는 확정 표현이므로 사용하지 않는다.

- "완벽하게 동작함"
- "문제 없음"
- "전체 완료"

대신, 사실 기반 표현을 사용한다.
- 예: "`pytest` 실행 결과 24 passed"
- 예: "A 기능은 확인 완료, B 기능은 미검증"

## 7) 템플릿 위치
- Task 템플릿: `reports/templates/task-report-template.md`
- Daily 템플릿: `reports/templates/daily-report-template.md`
- 예시 보고서: `reports/examples/example-task-report.md`
