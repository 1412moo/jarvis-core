# Discord Minimal Bot Adapter (`/task` only)

## 현재 구현 범위
이 단계의 구현은 **오직 `/task <내용>` 1개**만 처리한다.

- 처리 방식: Discord 일반 메시지 기반 (`/task ...` 텍스트)
- intake 재사용: `parser -> draft -> file writer`
- 성공 시 실제 `memory/tasks/*.md` 파일 생성
- hold/error 시 생성 중단 + 이유 응답

명시적 비범위:
- `/status`, `/report`, `/approve`
- GitHub API 연동
- 자동 보고 생성
- DB
- 웹 UI

---

## 필요한 환경변수
`.env.example` 기준:

- `DISCORD_BOT_TOKEN` (필수)

토큰은 절대 코드/커밋에 넣지 않는다.

---

## 설치 및 실행 방법
### 1) 의존성 설치
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r adapters/discord/requirements.txt
```

### 2) 환경변수 설정
```bash
cp adapters/discord/.env.example adapters/discord/.env
# adapters/discord/.env 에 DISCORD_BOT_TOKEN 값 입력
```

### 3) 실행
```bash
python3 adapters/discord/bot_minimal.py
```

기본적으로 `adapters/discord/.env`를 자동 로드한다.

---

## 동작 규칙 (`/task` only)
1. 슬래시 형태 문자열이 아니면 무시
2. `/task`가 아니면 거절 응답
3. `/task <내용>`을 intake 파이프라인에 전달
4. parser hold면 파일 생성 없이 hold 응답
5. error면 error 응답
6. success면 생성된 `task_id`, `file`명 응답

### 안전 규칙
- 빈 입력(`/task`만 입력)은 거절(error)
- 위험 키워드(예: `delete`, `production`, `삭제`)는 hold 처리
- hold/error는 `memory/tasks` 파일을 생성하지 않음

---

## 응답 예시
### 성공
```text
✅ task 생성 완료
- task_id: `task-0004-doc-update`
- file: `task-0004-doc-update.md`
```

### hold
```text
⏸️ hold
- reason: `needs_approval:risky_keyword_detected`
```

### error
```text
❌ error
- reason: `missing_required_arg:request`
```

---

## 최소 로컬 검증 (Discord 접속 전)
### 1) 문법 검증
```bash
python3 -m py_compile adapters/discord/bot_minimal.py
```

### 2) 환경변수 누락 에러 확인
```bash
python3 adapters/discord/bot_minimal.py
# 기대: {"result_type":"error","reason":"missing_env:DISCORD_BOT_TOKEN"}
```

### 3) Discord 없이 파이프라인 자체 확인 (`--self-check`)
```bash
python3 adapters/discord/bot_minimal.py --self-check '/task 문서 구조 정리'
python3 adapters/discord/bot_minimal.py --self-check '/task production 삭제'
python3 adapters/discord/bot_minimal.py --self-check '/task'
```

---

## 아직 구현하지 않은 것
- Discord **공식 slash command 등록/동기화**
- 명령 권한/채널 제한
- 재시도/백오프/운영 모니터링
- `/status`, `/report`, `/approve`
