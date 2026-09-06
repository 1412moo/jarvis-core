# task-0041-task-model-append-only-event-log

- id: `task-0041-task-model-append-only-event-log`
- title: `Task 상태를 append-only 이벤트 로그로 전환 (memory/tasks/task-XXXX.md는 파생 뷰로)`
- status: `DONE`
- repo: `jarvis-core`
- created_at: `2026-08-27 10:20 UTC`
- updated_at: `2026-08-28 10:10 UTC`
- summary: `task-0038 Phase 1 항목 2. task 파일의 status·summary·updated_at 직접 덮어쓰기를 append-only 이벤트 로그로 바꾸고 task 파일을 읽기 전용 뷰로 재정의하는 설계다. 설계 중 핵심 발견은 task 파일에 이미 두 쓰기 경로가 공존한다는 것이다 — 엔지니어링된 writer API와 그것을 우회하는 직접 편집. Owner 결정으로 기존 파일은 레거시로 동결하고 이벤트 로그는 신규 task부터 적용하며, ON_HOLD를 공식 상태값으로 편입하고, 이 task는 설계로 범위를 완료하되 실제 append 함수와 마이그레이션 구현은 보류한다. 전체 원문은 아래 요약(원문) 절에 보존했다.`
- source_command: `task-0038 승인 항목 ③(Phase 1 착수) 하위 실행 단위`

## 요약 (원문)

이 절은 task-0056에서 옮긴 원본 summary 전문이다. summary 필드가 값 구분자인 backtick을 포함했고 일부는 500자 상한도 넘어 canonical 검증에 실패했기 때문이며, 내용은 한 글자도 줄이지 않고 그대로 보존했다.

task-0038 Phase 1 항목 2. 현재 memory/tasks/task-XXXX.md는 status/summary/updated_at을 직접 덮어쓰는 구조인데, 이를 append-only 이벤트 로그(예: memory/tasks/events/task-XXXX.jsonl에 status_changed/summary_updated 등 이벤트를 append)로 바꾸고, task-XXXX.md는 그 이벤트에서 파생되는 읽기 전용 뷰로 재정의하는 설계·구현 작업. Buzz의 kind 기반 이벤트 모델에서 아이디어만 차용(Nostr/외부 의존 없음). 착수 전 설계 문서(docs/)로 먼저 합의 필요 — 기존 수십 개 task 파일과 하위 호환 전략, 마이그레이션 방법, validator(scripts/validate_multi_agent_sop.py 등) 영향 범위를 먼저 조사해야 함. [2026-08-28 09:40 UTC] 설계 문서 작성 완료: docs/task-0041-append-only-event-log-design.md. 핵심 발견 — task 파일에는 이미 두 개의 다른 쓰기 경로가 공존한다: (A) orchestrator/discord-intake/task_file_writer.py의 엔지니어링된 API(SHA-256 staleness check, atomic temp-file+fsync+replace, 단 TODO→DOING/DOING→DONE 두 전이만 허용), (B) 이번 세션이 실제로 해온 Read/Edit 직접 편집(ON_HOLD 같은 비표준 상태값 포함, (A)를 전부 우회). scripts/validate_multi_agent_sop.py는 memory/tasks를 전혀 읽지 않아 이번 전환과 무관함을 전체 소스 확인으로 결론. 제안 스키마: memory/tasks/events/task-XXXX.jsonl(append-only, prev_hash/hash 포함 — task-0044가 재사용 가능하도록, actor 필드는 task-0042가 채울 자리 확보) + task-XXXX.md는 재생성되는 읽기 전용 뷰. 미해결 Owner 결정 5가지(설계 문서 §7): 기존 46개 파일 소급 마이그레이션 여부, ON_HOLD 등 비표준 상태값 정리, 직접 편집을 막을 방법(코드로 100% 강제 불가), task-0042와의 설계 순서, Phase 1 완료 조건(6개 중 4개)을 이 항목 없이 채울지. 구현 착수하지 않음(설계만). [2026-08-28 10:10 UTC Owner 결정] ① 마이그레이션 범위: 기존 46개 파일은 레거시로 동결, 이벤트 로그는 신규 task부터만 적용. ② `ON_HOLD`를 공식 상태값으로 편입(6개 → 7개: TODO/DOING/BLOCKED/ON_HOLD/DONE/FAILED/NEEDS_APPROVAL) — `docs/task-model.md` 갱신 필요(별도 소요, 아직 미실행). ③ 이 task는 설계로 범위 완료, 실제 이벤트 append 함수/마이그레이션 구현은 보류(수요 생기면 별도 task로 재개). status DONE 처리.
