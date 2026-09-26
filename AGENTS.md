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
   - 예외: **Jarvis 자체 신원·서명용 로컬 키페어**. 아래 다섯 조건을 **모두** 만족할
     때만 허용하며, 하나라도 어긋나면 원칙 5가 그대로 적용된다.
     1. Owner가 명시적으로 실행할 때만 생성한다(기동·테스트·import 등 자동 생성 경로 금지).
     2. 저장소 완전 밖에 저장한다(해석된 경로가 저장소 안이면 fail-closed로 거부).
     3. 사용자 전용 권한으로 보호한다(0700 디렉터리 / 0600 파일).
     4. 공개키만 저장소에 기록한다.
     5. 개인키 값은 로그·에러·산출물에 절대 노출하지 않는다.
   - 이 예외는 **외부 서비스 자격증명**(API 키/토큰/계정정보)에는 적용되지 않는다.
     상세 설계는 [`docs/task-0042-role-based-signing-keys-design.md`](docs/task-0042-role-based-signing-keys-design.md).
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

Reviewer minor finding을 Owner가 수용하고 QA로 진행하는 예외는
[`docs/jarvis-multi-agent-sop-v0.1.md`](docs/jarvis-multi-agent-sop-v0.1.md) §8의 조건을 따른다.

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

## 기준 지도

이 절은 저장소의 문서와 코드 중 무엇이 어느 영역의 현재 기준인지 정한다. 다른
문서의 우선순위 선언은 자기 영역 안에서만 유효하며, 영역 사이의 판정은 이 절을
따른다.

### 영역별 기준

| 영역 | 기준 파일 | 강제 장치 |
| --- | --- | --- |
| 에이전트 행동 규칙 | `AGENTS.md` → `docs/jarvis-multi-agent-sop-v0.1.md`, `docs/codex-operating-rules.md` → `.claude/agents/reviewer.md`, `.codex/agents/*.toml` | `scripts/validate_multi_agent_sop.py` |
| 현재 시스템 동작 | 실행 코드와 결정론적 테스트 | 각 smoke test와 self-check |
| task 상태 | 각 `memory/tasks/*.md`의 메타데이터 필드, 형식·전이 계약 `docs/task-model.md` | `orchestrator/discord-intake/task_file_writer.py`, `apps/jarvis-console/run_web_app.py` |
| 목표·milestone·approval state | `docs/master-plan.md` (이 영역 한정) | `apps/jarvis-console/run_web_app.py`, `scripts/validate_multi_agent_sop.py` |

### History로 취급하는 것

다음은 작성 당시의 기록이며 현재 규칙이나 현재 동작의 근거가 아니다. 인용할
때는 "기록에 따르면" 형태로만 쓴다.

- `memory/tasks/*.md`의 본문(승인 원문, 요약, 검증, repair 이력). 메타데이터
  필드는 위 표의 task 상태 영역이다.
- 설계 문서(`docs/*-design.md` 등)
- `docs/chatgpt-handoff.md` (특정 시점 스냅샷)
- `docs/WORKFLOW.md`, `docs/codex-workflow.md`, `README.md`, `docs/architecture.md`
- `docs/master-plan.md` 중 목표·milestone·approval state 밖의 서술

### 판정 규칙

1. 먼저 영역을 판정한다. 영역이 다른 기준 파일끼리는 충돌로 보지 않는다.
2. 같은 영역에서는 위임 방향을 따른다. AGENTS.md가 위임한 세부는 하위 문서가
   정하고, 하위 문서가 AGENTS.md의 원칙이나 escalation gate와 모순되면
   AGENTS.md가 우선하며 그 모순은 validator 오류다.
3. 안전 gate끼리 허용 범위가 다르면 더 제한적인 쪽을 적용하고
   `gate_safety_conflict`로 Owner에게 escalation한다(fail closed).
4. Owner 승인은 그 승인을 받은 task의 범위 안에서만 효력이 있다.
5. 기준 문서와 코드가 다르면 drift로 기록하고 그 규칙에 기대는 실행을 멈춘다.
   어느 한쪽을 조용히 따르지 않는다.
6. History의 서술은 규칙의 근거가 되지 않는다.

### Owner 승인의 효력과 승격

task 승인으로 생긴 규칙이 그 task 뒤에도 계속 적용돼야 하면, 같은 task나 후속
task에서 위 표의 기준 문서(해당 문서의 "승인된 예외" 절 등)로 옮겨야 한다.
옮기기 전에는 task 기록에만 있는 규칙을 현재 규칙으로 쓰지 않는다.

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
