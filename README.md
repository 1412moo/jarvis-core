# jarvis-core

`jarvis-core`는 여러 프로젝트/서브 저장소를 운영하기 위한 **메인 지휘 저장소**입니다.

> 전체 개발 방향과 현재 작업 위치는 [`docs/master-plan.md`](docs/master-plan.md)를 먼저 확인합니다.

이 저장소는 아래 항목을 기반으로 운영합니다.
- 운영 원칙 정리
- 역할 분리 기준 문서화
- 작업/보고 포맷 표준화
- 추후 오케스트레이션 확장을 위한 최소 뼈대 확보

## Bootstrap 단계에서 확보한 범위 (완료)
- 문서 구조 생성
- 작업 규칙 문서 생성
- 보고서 규칙 문서 생성
- 스킬 기반 운영 문서 초안 생성

## 비범위 (현재 범위 밖)
- 멀티 에이전트 실구현
- GitHub 자동화 구현
- 배포 및 인프라 자동화
- Docker/DB 확장 설계

## 디렉터리 개요
- `apps/`: 로컬 앱 — `jarvis-console`, `hermes-manager-pilot`, `research-council`, `daily-ai-radar`
- `docs/`: 비전, 아키텍처, 역할 분리 기준
- `reports/`: 작업 보고 형식 규칙
- `skills/`: 반복 작업 절차/가이드
- `prompts/`: task work-order 프롬프트 문서
- `orchestrator/`: `audit-chain`, `buzz-bridge`, `discord-intake`, `discord-nl-intent`, `role-signing` 모듈
- `adapters/`: 외부 연결 어댑터 — `discord`, `team-manager-bot`, `web`
- `configs/`: buzz agent 신원, role signing 공개키 설정
- `memory/`: 운영 기록 — task 기록은 `memory/tasks`
- `scripts/`: no-secrets 검사, multi-agent SOP 검증, demo batch 도구

## 운영 원칙 요약
1. 큰 작업을 작은 단계로 분할
2. 확인되지 않은 상태를 완료로 선언하지 않음
3. 비밀정보/민감정보 커밋 금지
4. 메인 저장소와 서브 저장소 역할 혼합 금지

자세한 규칙은 `AGENTS.md` 및 `docs/` 문서를 따릅니다.

## 개발 루프
- 현재 개발 루프(`/task -> /plan -> /review-task -> /approve -> /report -> /retro today`)는 아래 문서에서 관리한다.
- 문서: [`docs/jarvis-dev-loop.md`](docs/jarvis-dev-loop.md)
