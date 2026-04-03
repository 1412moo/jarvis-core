# Discord Command Intake (최소 구현 뼈대)

## 목적
이 디렉터리는 Discord 명령 문자열을 **수신했다고 가정**하고,
명령을 분류/검증하여 정규화된 payload 초안을 반환하는 최소 구조를 제공한다.

이번 단계는 실제 Discord bot이 아니라 **로컬 파서 + task draft 생성기 뼈대**만 다룬다.

## 처리 흐름 (현재)
1. `intake_parser.py`
   - 명령 분류
   - 필수 인자 검증
   - normalized payload / hold / error 반환
2. `task_draft_builder.py`
   - parser 결과를 받아 draft 생성 가능 여부 판단
   - `/task`만 task draft object 생성
   - hold/error 또는 `/status`/`/report`/`/approve`는 hold result 반환

## 범위
- 포함
  - `/task`, `/status`, `/report`, `/approve` 분류
  - 필수 인자 존재 여부 검증
  - 정규화 payload 초안 반환
  - hold/error reason 반환
  - parser 결과 기반 task draft object 생성(오직 `/task`)
- 제외
  - Discord API 연결
  - 토큰/비밀정보
  - 네트워크 호출
  - task 파일 생성 및 외부 시스템 실행
  - GitHub 작업 실행

## 파일 구성
- `intake_parser.py`: 규칙 기반 파서 최소 구현
- `task_draft_builder.py`: parser 출력 → task draft/hold 변환기
- `command_schema.md`: 명령별 입력/검증/출력 스키마
- `examples.md`: 최소 동작 예시

## 로컬 실행
```bash
python3 orchestrator/discord-intake/intake_parser.py
python3 orchestrator/discord-intake/task_draft_builder.py
```

실행 시 샘플 입력들에 대한 JSON 형태 분류/초안 결과를 출력한다.
