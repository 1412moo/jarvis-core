# task-0047-local-buzz-relay-handson-spike

- id: `task-0047-local-buzz-relay-handson-spike`
- title: `Docker Desktop 기반 로컬 Buzz Relay + WebSocket Agent Bridge 핸즈온 스파이크 (S1~S7)`
- status: `TODO`
- repo: `jarvis-core`
- created_at: `2026-08-28 09:00 UTC`
- updated_at: `2026-08-28 11:20 UTC`
- summary: `task-0046(로컬 Buzz Relay/Agent Bridge 조사) 결과를 실제로 손으로 검증하는 스파이크. 목표는 Hostinger/VPS가 아니라 Windows 로컬 PC 한 대에서 Buzz Relay + WebSocket + Local Agent Bridge가 실제 동작하는지 확인하는 것(task-0046 §6 스파이크 목록: S1 CLI stdio 왕복 → S2 Docker 전제 확인 → S3 Relay 단독 기동 → S4 AUTH 챌린지 → S5 NIP-42 완주 → S6 채널 구독 왕복+kind 실측 → S7 bridge 결합 왕복. S8/S9는 선택). 착수 조건: (1) Phase 1 완료 조건 충족(task-0039 기준, 6개 하위 task 중 4개 이상 — 현재 task-0040+task-0041+task-0043+task-0045로 4/6 충족, task-0042/task-0044는 선택적 잔여 항목이며 필수 선행조건 아님), (2) Docker Desktop 설치를 포함한 별도 Owner 승인. 착수 시 이 스파이크의 목적은 task-0038 Phase 2 Gate G2를 "ACP 경로 단독"이 아니라 "WebSocket 직결 Agent Bridge 경로 포함"으로 재정의한 근거(task-0038 §6.0 addendum, 2026-08-28)를 실기동으로 검증하는 것이다. 실제 Buzz 통합 구현은 이 스파이크가 성공한 뒤에만 결정한다. 현재는 착수 전(TODO). [2026-08-28 11:20 UTC 정정] 착수 조건 (1)의 "Phase 1(task-0041~0044) 완료"라는 구버전 표현은 task-0039가 Phase 1 완료 게이트를 "6개 중 4개 이상"으로 확정(2026-08-28 10:40 UTC)하기 전에 쓰인 문구였다. task-0039와 docs/master-plan.md 기준으로 Phase 1은 이미 완료됐다(task-0040+task-0041+task-0043+task-0045 = 4/6). task-0042/task-0044는 선택적 잔여 항목으로 계속 진행 가능하나 이 스파이크의 착수를 막지 않는다. 남은 유일한 착수 조건은 (2) Docker Desktop 설치 및 핸즈온 스파이크 실행에 대한 별도 Owner 승인이며, 아직 미승인 상태다.`
- source_command: `Owner 직접 지시 (2026-08-28, task-0046 결과 확인 후): "task-0041~0044 완료 후, 별도 승인 하에 Docker Desktop 기반 로컬 Buzz Relay 핸즈온 스파이크(S1~S7)를 진행한다"`
