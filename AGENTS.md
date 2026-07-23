# AGENTS.md (Top-level Rules for jarvis-core)

## 저장소 성격
- 이 저장소는 **지휘(오케스트레이션 기준)**와 **기록(문서/보고 체계)**을 담당한다.
- 현재 기본 개발 범위는 **Jarvis-Core 단일 저장소**다. 별도 승인 없이 두 번째
  저장소나 multi-project 운영을 가정하지 않는다.

## 필수 작업 원칙
1. 작업은 항상 작은 단계로 나눈다.
2. 기능보다 구조와 문서를 우선한다(초기 단계 기준).
3. 위험한 작업(파괴적 변경, 대규모 삭제, 운영 영향 작업)은 승인 없이 진행하지 않는다.
4. 모든 작업 후 보고서 형식으로 요약한다.
5. 비밀 정보(키/토큰/계정정보/민감데이터)는 생성·저장·커밋하지 않는다.
6. 요청되지 않은 불필요한 리팩토링을 금지한다.
7. 메인 저장소와 서브 저장소의 역할을 섞지 않는다.
8. 확인하지 않은 사항은 완료로 기록하지 않는다.

상세 approval gate, local commit, QA 선택, timeout, background process 및
protected file 기준은 [`docs/codex-operating-rules.md`](docs/codex-operating-rules.md)를
따른다.

## 기본 개발 조직: Jarvis Multi-Agent SOP v0.1

Jarvis-Core의 승인된 변경 작업은 다음 조직 흐름을 기본값으로 사용한다.

```text
Owner milestone approval
→ primary Director
→ Manager
→ Implementer candidate
→ Reviewer (finding이면 Repair 후 새 candidate)
→ QA (실패하면 Repair 후 새 Reviewer → QA)
→ optional Docs
→ Manager Report
→ Director Report
→ Owner
```

- Director는 Owner와 소통하는 primary Codex task다. Manager의 계획과 최종
  결과를 평가하고 Owner에게 최종 Director Report 한 번만 제출한다. Worker의
  assignment, 순서, retry 또는 repair를 직접 결정하지 않는다.
- **Manager만 Worker orchestration 책임을 갖는다.** work package, dependency,
  file ownership, Worker 생성·배정·순서, retry·repair와 실제 Git evidence 대조를
  관리한다.
- 현재 Codex 표면에서 Manager의 nested spawning이 지원되지 않거나 불명확하면
  Director가 Manager의 확정된 assignment plan을 기계적으로 실행할 수 있다.
  이 fallback은 작업 생성 위치만 바꾸며 orchestration 판단 책임은 Manager에 남는다.
- Implementer는 assignment의 유일한 source writer다. Reviewer는 exact candidate
  commit에 고정된 strict read-only 역할이고, QA는 같은 candidate를 가장 가벼운
  충분한 방법으로 검증하며 tracked source를 수정하지 않는다.
- Docs는 QA 뒤에 순차 실행하거나 Manager가 이유와 함께 `not_required`로 기록한다.
  Docs가 candidate를 바꾸면 기존 Reviewer/QA evidence는 무효다.

기본 budget은 `retry_budget=1`, `repair_budget=1`, `repair_count=0`이다. Retry는
source 변경 없는 재실행·환경 복구이고, repair는 source를 바꾸는 수정이다.
source-changing repair마다 `repair_count += 1`을 적용한다. candidate commit이
바뀌면 이전 Reviewer와 QA 결과는 전부 무효이며 새 commit에 Reviewer → QA를 다시
실행한다. budget 안의 처리는 Manager가 Owner 개입 없이 수행하고, 추가 시도가
필요한데 budget이 소진됐으면 Manager → Director로 escalation한다. budget 증액은
Owner만 결정한다.

scope·권한 확대, `jarvis.bat`, 외부 API/LLM·credential, destructive action,
push/PR, 안전 계약 충돌 또는 예상하지 못한 저장소 변경은 budget과 무관한 즉시
escalation gate다. 상세 상태 전이, report/evidence 계약과 agent별 경계는
[`docs/jarvis-multi-agent-sop-v0.1.md`](docs/jarvis-multi-agent-sop-v0.1.md)를
따른다.

## 변경 범위 관리
- 한 번에 크게 만들지 않는다.
- 단계별로 생성하고 검증 가능한 산출물만 남긴다.
- 추적 가능한 문서/커밋 단위로 작업한다.

## 보고 기본 형식
작업 종료 시 아래 순서로 정리한다.
1. 생성/수정 파일 목록
2. 파일별 목적 요약
3. 이번 단계 비범위/미완료 항목
4. 다음 권장 작업
