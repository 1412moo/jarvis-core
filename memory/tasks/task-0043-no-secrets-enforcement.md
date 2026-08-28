# task-0043-no-secrets-enforcement

- id: `task-0043-no-secrets-enforcement`
- title: `"No secrets in configuration" 원칙을 코드 검사로 강제 (AGENTS.md 원칙 5 승격)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-08-27 10:20 UTC`
- updated_at: `2026-08-28 10:40 UTC`
- summary: `task-0038 Phase 1 항목 4, 완료. AGENTS.md 원칙 5("비밀 정보는 생성·저장·커밋하지 않는다")를 문서 규칙에서 결정론적 코드 검사로 승격. scripts/check_no_secrets.py 신규 작성 — validate_multi_agent_sop.py와 같은 스타일(에러 리스트 + PASS/FAIL 출력 + exit code). 탐지 패턴 7종: AWS 액세스키, OpenAI/Anthropic 스타일 키, Slack 토큰, GitHub 토큰, private key block, 일반 key/secret/token/password 할당(따옴표 값 8자 이상). git 추적 파일 전체 스캔(기본) 또는 --staged(스테이징된 파일만) 지원. 오탐 방지: placeholder 마커, 저엔트로피(반복문자) 값, `*_ENV` 변수(환경변수 "이름"을 담은 값 — 예: TEAM_MANAGER_BOT_TOKEN_ENV = "TEAM_MANAGER_BOT_TOKEN"), 순수 소문자 단어형 라벨(예: "evidence-token-two") 제외. --self-test 내장(양성 7 + 음성 9 fixture, 16/16 통과). 실제 저장소 전체 스캔 결과: files_scanned=215, findings=0, status=PASS, exit=0(첫 실행에서 8건 오탐 발견 → 위 오탐방지 로직 추가해 전부 해소, 실제 비밀은 없었음을 확인). 코드 변경: scripts/check_no_secrets.py(신규). 기존 파일 수정 없음.`
- source_command: `task-0038 승인 항목 ③(Phase 1 착수) 하위 실행 단위`
