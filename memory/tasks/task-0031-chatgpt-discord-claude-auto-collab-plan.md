# task-0031-chatgpt-discord-claude-auto-collab-plan

- id: `task-0031-chatgpt-discord-claude-auto-collab-plan`
- title: `ChatGPT–Discord–Claude Code 자동 협업 구조 사전 설계/승인 계획`
- status: `DOING`
- repo: `jarvis-core`
- created_at: `2026-08-26 11:16 UTC`
- updated_at: `2026-08-26 11:29 UTC`
- summary: `Phase A(무자격 스캐폴딩)를 완료하고 commit 9bfb9b7로 커밋했다. adapters/team-manager-bot 6개 파일과 설계 문서, work-order 등 8개 파일만 stage했고 무관한 변경은 넣지 않았다. 검증은 run_smoke_tests.py 통과(exit 0)와 py_compile 통과다. credential 미생성, API 미호출, 외부연결·배포 없음이며 adapters/discord와 access.json은 무변경이다. 이 task 파일 자체는 기존 dogfood 관례대로 untracked로 두었다. Phase B(credential·비용 승인)는 미착수이며 별도 Owner 승인 대기다. 전체 원문은 아래 요약(원문) 절에 그대로 보존했다.`
- source_command: `Discord work-order (task-0031)`

## 요약 (원문)

이 절은 task-0054에서 옮긴 원본 summary 전문이다. summary 필드가 500자 상한을 넘어 canonical 검증에 실패했기 때문이며, 내용은 한 글자도 줄이지 않고 그대로 보존했다.

Phase A(무자격 스캐폴딩) 완료 및 커밋됨: commit 9bfb9b7e630c0c363429aa60cc67f8ce57eed977 "feat(team-manager-bot): add Phase A credential-free scaffolding" — adapters/team-manager-bot/{bot_minimal.py, llm_provider.py, README.md, requirements.txt, .env.example, run_smoke_tests.py} + docs/chatgpt-discord-claude-auto-collab-v0.1-design.md + prompts/task-0031-...-work-order.md, 8개 파일만 stage(무관 변경 미포함). 검증: run_smoke_tests.py -> "team-manager-bot Phase A smoke tests passed"(exit 0), py_compile 통과. credential 미생성, API 미호출, 외부연결/배포 없음, adapters/discord와 access.json 무변경. 이 task 파일 자체는 기존 dogfood task 관례대로 untracked 유지, 커밋 미포함. Phase B(credential/비용 승인)는 아직 시작하지 않음 — 별도 Owner 승인 대기.
