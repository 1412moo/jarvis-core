# task-0037-gemini-cli-local-dev-environment

- id: `task-0037-gemini-cli-local-dev-environment`
- title: `Gemini를 Team Manager로 쓰기 위한 로컬 개발 환경 준비`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-08-26 13:12 UTC`
- updated_at: `2026-08-27 10:05 UTC`
- summary: `[정정] 원래 전제였던 공식 Gemini CLI 로그인 대기는 무효화됐다 — 2026-06-18 구글 정책 변경으로 Gemini Code Assist for individuals 계정은 기존 CLI 로그인이 차단된다. 후속 제품 Antigravity CLI(agy)로 전환해 Owner 승인 하에 재검증했다. 확인된 것: Windows 정상 동작, 기존 구독 계정 로그인 성공(추가 결제 없음), 저장소 파일 읽기·탐색 정상, AGENTS.md 원칙 원문 정확 인용, 수정 금지 지시 준수. 대화형 모드에서 파일 생성 시 승인 프롬프트가 실제로 뜨고 승인 후에만 기록되는 것도 직접 검증했다. 헤드리스 모드는 승인 UI가 없어 permissions.allow 사전 설정이 필요하다. 판정은 USE. 전체 원문은 아래 요약(원문) 절에 보존했다.`
- source_command: `Discord instruction (task-0037, no work-order per explicit instruction)`

## 요약 (원문)

이 절은 task-0056에서 옮긴 원본 summary 전문이다. summary 필드가 값 구분자인 backtick을 포함했고 일부는 500자 상한도 넘어 canonical 검증에 실패했기 때문이며, 내용은 한 글자도 줄이지 않고 그대로 보존했다.

[정정] 원래 전제(공식 Gemini CLI @google/gemini-cli 로그인 대기)는 무효화됨 — 2026-06-18부 구글 정책 변경으로 "Gemini Code Assist for individuals"(Google AI Plus 개인 구독) 계정은 기존 Gemini CLI 로그인이 아예 차단됨("This client is no longer supported... migrate to Antigravity"). 후속 제품 Antigravity CLI(agy)로 전환하여 재검증 진행(Owner 승인 하 설치 "직접 진행해" 지시 받음). 확인됨: Windows 정상 동작(agy v1.1.22), Google AI Plus 기존 구독 계정(i0028407@gmail.com)으로 로그인 성공(별도 API 키/추가 결제 없음), 모델 Gemini 3.7 Flash(High), jarvis-core 로컬 저장소 파일 읽기 및 디렉토리 탐색(Find) 정상 동작, AGENTS.md 8대 원칙 1번을 원문과 정확히 일치하게 인용, "수정하지 마라" 지시 준수(git status 변경 없음 확인). 추가 확인(2026-08-27): 대화형 모드에서 scratchpad/antigravity-test.txt 파일 생성 요청 시 승인 프롬프트가 실제로 떴고, Owner 승인 후에만 파일이 생성됨 — 내용("hello from antigravity")까지 정확히 일치하는 것을 Claude Code가 직접 `cat`/`git status`로 검증. 헤드리스(`-p`) 모드는 자체 승인 UI가 없어 read_file/command 등 모든 도구 호출이 settings.json permissions.allow 미설정 시 자동 거부되는 구조도 확인. 검증 후 테스트 파일은 정리(삭제)함. 남은 미확인: Antigravity 2.0 데스크톱 앱 vs CLI 중 적합성(CLI만 테스트, 범위 밖으로 판단), 사용량/쿼터 한도(기존 구독 로그인은 정상 동작했으나 한도 자체는 미측정 — 낮은 우선순위 후속 확인 항목으로 남김). ANTIGRAVITY_VERDICT: **USE** — 읽기/탐색/규칙준수/승인기반 파일쓰기까지 대화형 모드에서 전부 검증됨. Claude Code처럼 Team Manager/Implementer 후보로 실사용 가치 있음. 단, 헤드리스 자동화 경로는 permissions.allow 사전 설정이 필요해 즉시 무인 자동화에는 추가 설정 작업 필요.
