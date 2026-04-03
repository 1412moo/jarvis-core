# Task Report

## 1) 메타 정보
- 작업 ID: `TASK-20260403-001`
- 작업명: 보고 템플릿 디렉터리 구조 정리
- 작성자: codex
- 작성일: `2026-04-03`
- 상태: `DONE`
- 관련 이슈/문서: `reports/README.md`

## 2) 작업 목적
- 보고서 형식 표준화를 위해 템플릿 저장 위치와 기본 필드를 정의한다.

## 3) 범위
### 포함 범위 (In Scope)
- `reports/templates` 디렉터리 생성
- task/daily 템플릿 초안 생성

### 제외 범위 (Out of Scope)
- 자동 리포트 생성기 개발
- 외부 시스템 연동(DB, Discord, 웹 UI)

## 4) 변경 내역
- 변경 파일:
  - `reports/templates/task-report-template.md` — 작업 단위 보고 템플릿 추가
  - `reports/templates/daily-report-template.md` — 일간 보고 템플릿 추가
- 주요 결정 사항:
  - 날짜 형식은 `YYYY-MM-DD` 로 고정
  - 상태 값은 사전 정의된 6개만 사용

## 5) 검증 내역
- 실행/확인 명령:
  - `find reports -maxdepth 3 -type f -print`
- 확인 결과:
  - 템플릿 파일이 생성되었고 경로 규칙에 맞게 배치됨
- 미검증 항목(있다면):
  - 실제 팀 운영 적용 결과는 별도 검증 필요

## 6) 리스크 / 이슈
- 리스크:
  - 상태 값 해석 기준이 팀별로 다를 수 있음
- 블로커:
  - 없음

## 7) 승인 필요 사항 (NEEDS_APPROVAL 전용)
- 해당 없음 (현재 상태: DONE)

## 8) 다음 작업
- 다음 액션 1: `reports/README.md` 에 상태별 예시 추가
- 다음 액션 2: 주간 보고 템플릿 필요 여부 결정
- 다음 액션 3: 실제 작성 샘플 2건 추가

## 9) 금지 표현 점검
- "완벽하게 동작함" 미사용
- "문제 없음" 미사용
- "전체 완료" 미사용
