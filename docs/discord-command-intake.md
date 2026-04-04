# Discord Command Intake 최소 설계 (초안)

## 1) 목적
- Discord는 팀 커뮤니케이션에서 이미 사용 빈도가 높고, 짧은 명령 전달/상태 확인에 적합하므로 첫 외부 입력 채널 후보로 선정한다.
- `jarvis-core`의 역할(지휘/기록)에 맞춰, Discord 입력을 **즉시 실행**이 아닌 **Task 변환 전단계 intake**로 다루기 위한 정책을 정의한다.
- 본 문서는 **구현 문서가 아닌 설계 문서**이며, 실제 봇 동작/서버 실행/API 호출은 이번 단계 범위에 포함하지 않는다.

## 2) 범위

### 2.1 이번 단계 포함
- 받을 명령 형태(슬래시 명령 중심) 정의
- Task로 변환 가능한 입력 유형 정의
- 승인 필요(`NEEDS_APPROVAL`) 유형 정의
- 무시/보류해야 할 입력 정의

### 2.2 이번 단계 제외
- 실제 Discord bot 구현
- 토큰 발급/설정
- 서버 실행
- Discord/API 호출
- 자동 Task 생성 코드

## 3) Intake 공통 처리 흐름
1. Discord 입력 수신(명령형 또는 자연어)
2. 입력 타입 분류(작업 생성/상태 조회/보고/승인 관련/기타)
3. 유효성 검사(필수값, 형식, 대상 식별 가능 여부)
4. 처리 결과 결정
   - 즉시 응답 가능: 조회성 응답 초안 생성
   - 실행 금지 영역: Task 초안 생성 또는 보류
   - 위험 요청: `NEEDS_APPROVAL`로 표시
5. 최종적으로 `docs/command-to-task.md`의 변환 규칙으로 연결

## 4) 명령 종류 초안
- `/task` : 작업 생성 요청
- `/status` : 상태 조회 요청
- `/report` : 보고 요청
- `/approve` : 승인 필요 요청 표시/처리

> 원칙: 형식은 단순하게 유지하고, 상세 옵션은 추후 확장한다.

## 5) 명령별 정의

### 5.1 `/task`
- 목적
  - 사용자 요청을 실행 지시로 바로 처리하지 않고 Task 초안으로 등록하기 위한 입력
- 필수 입력값
  - `title` 또는 `request` (작업 의도를 표현하는 최소 한 줄)
- 선택 입력값
  - `repo_hint` (예: `jarvis-core`, `subrepo-web`)
  - `priority` (예: low/medium/high)
  - `due` (기한, 해석 실패 시 참고값 처리)
- 성공 시 기대 결과
  - Task 초안이 생성되며 상태는 기본 `TODO`
  - 애매한 조건은 확인 필요 항목으로 기록
- 실패 또는 보류 조건
  - 요청 의미가 지나치게 모호한 경우
  - 한 줄에 상충 목표가 과도하게 혼합된 경우(분리 필요)
  - 파괴적/운영 영향 요청이 포함된 경우(현재 구현은 `needs_approval:*` hold로 반환하며 Task 파일은 생성하지 않음)

### 5.2 `/status`
- 목적
  - 특정 Task 또는 범위의 현재 상태를 확인
- 필수 입력값
  - `task_id` (`task-####-slug` 형식)
- 선택 입력값
  - (없음, 현 단계 구현 범위)
- 성공 시 기대 결과
  - 대상 Task 메타데이터(id/title/status/updated_at/summary) 응답
- 실패 또는 보류 조건
  - 대상 Task 식별 실패
  - task_id 형식 불일치

### 5.3 `/report`
- 목적
  - 기간/대상 기준으로 진행 상황 보고를 요청
- 필수 입력값
  - (없음: `/report` 또는 `/report today`)
- 선택 입력값
  - `today` 키워드(UTC 날짜 기준)
- 성공 시 기대 결과
  - 지정 기간의 작업 요약 보고 초안 제공
- 실패 또는 보류 조건
  - 기간 해석 불가
  - 데이터 기준(어떤 Task 집합인지) 미확정

### 5.4 `/approve`
- 목적
  - 승인 필요 작업을 표시하거나 승인 의사 표현을 기록
- 필수 입력값
  - `target` (full task id: `task-####-slug`)
  - `decision` (approve/reject)
- 선택 입력값
  - (없음, 현 단계 구현 범위)
- 성공 시 기대 결과
  - 승인 이벤트가 기록되고 대상 Task 상태/플래그가 갱신됨
- 실패 또는 보류 조건
  - 승인 권한 주체 불명확
  - 대상 식별 실패
  - 승인 범위가 불명확하여 오해 가능성이 큰 경우

## 6) 자연어 메시지 처리 원칙
- 애매하면 즉시 실행하지 않고 Task 초안으로 기록한다.
- 한 메시지에 작업이 여러 개면 분리하여 각각 별도 Task 후보로 만든다.
- 구현 요청(“만들어라”, “배포해라”)은 바로 실행하지 않고 먼저 기록/검토한다.
- 위험 요청(파괴적 변경, 대규모 삭제, 운영 영향)은 `NEEDS_APPROVAL`로 처리한다.
- 조회성 요청도 대상이 불명확하면 보류하고 재확인을 요청한다.
- 명령 우선순위는 “명시적 슬래시 명령 > 자연어 추정”으로 둔다.

## 7) 무시/보류 입력 정책

### 7.1 무시 대상(기록 최소화)
- 작업 의도가 없는 단순 반응/인사/이모지
- 시스템 처리와 무관한 잡담

### 7.2 보류 대상(초안 기록)
- 의도는 있으나 범위가 지나치게 넓은 요청
- 승인 주체/대상이 불명확한 승인 관련 요청
- 복수 작업이 혼재되어 분해가 필요한 메시지

## 8) `command-to-task` 규칙과의 연결
- Discord intake는 독립 실행 계층이 아니라, 입력을 정규화하여 `docs/command-to-task.md` 규칙으로 전달하는 전처리 단계다.
- 즉, Discord에서 들어온 `/task` 또는 자연어 요청은 최종적으로 동일한 Task 변환 정책(제목/요약/repo/status/id 규칙)을 따른다.
- 추후 웹 입력 채널을 추가해도 동일한 변환 규칙을 재사용할 수 있도록 채널-중립 구조를 유지한다.

## 9) 단순 예시 5개
1. `/task 보고 시스템 개선`
   - 기대: 작업 생성 요청으로 분류, Task 초안(`TODO`) 생성
2. `/status task-0002-report-system`
   - 기대: 해당 Task 상태 요약 반환, 미존재 시 보류/오류 응답
3. `/report today`
   - 기대: 당일 기준 진행 요약 보고 초안 제공
4. `/approve task-0007-discord-intake approve`
   - 기대: 승인 이벤트 기록, 대상 Task 승인 플래그 반영
5. `디스코드 연동이랑 보고 자동화도 같이 해줘`
   - 기대: 자연어 복합 요청으로 인식, 2개 Task 후보로 분리 후 즉시 실행 없이 기록

## 10) 비범위 재확인
- 본 문서는 정책 정의만 다루며, 구현(봇/서버/API/자동화 스크립트)은 수행하지 않는다.

## 11) 구현 정합성 메모 (2026-04-03)
- `orchestrator/discord-intake/intake_parser.py` 기준 MVP는 **슬래시 명령 4종**(`/task`, `/status`, `/report`, `/approve`)만 규칙 기반으로 파싱한다.
- 본 설계 문서의 자연어 분해/복수 Task 분리 정책은 **후속 단계**로 남겨두며, 현재 구현에는 포함하지 않는다.
- 현재 구현은 분류 + 필수값 검증 + 정규화 payload 반환 + hold/error reason 반환까지만 수행한다.
- `/task` 구현 응답 포맷(현재)
  - 정상 생성: `{"result_type":"success","task_id","file_name","file_path"}`
  - 입력 오류(필수값 누락): `{"result_type":"error","reason":"usage:/task <request>"}` 고정 usage 반환
  - 입력 오류(기타): `{"result_type":"error","reason":"..."}` 형태 reason 반환
  - 위험 키워드 포함: `{"result_type":"hold","reason":"needs_approval:risky_keyword_detected"}` (task 파일 미생성)

## 12) 명령 문서 역할 분리 (2026-04-04 정리)
- 본 문서는 Discord intake의 **설계/맥락**을 다루는 문서다.
- `/status`, `/report`의 payload contract/usage 정책은 `docs/status-report-contract.md`를 기준으로 관리한다.
- `/status`, `/report`의 처리 단계/비범위는 `docs/status-report-flow.md`를 기준으로 관리한다.
- `/approve` 전용 payload contract는 기존대로 `docs/approve-file-writer-contract.md`를 따른다.
