# Jarvis Studyroom v0.1 Foundation

`apps/studyroom/`은 Jarvis-Core 프로젝트 자체를 교재 삼아 소프트웨어 아키텍처와 엔지니어링 개념을 공부하기 위한 **개인용 학습 웹 애플리케이션**입니다.

```text
Studyroom is a read-only learning surface.
It must not mutate Jarvis-Core runtime state.
```

---

## 1. Studyroom의 목적

- **운영이 아닌 학습**: Jarvis Console(`apps/jarvis-console`)이 작업 수명주기를 관리하는 운영 도구라면, Studyroom은 개발 과정에서 겪은 결정, 버그, 아키텍처 원칙을 복습하는 **순수 학습 도구**입니다.
- **원본 사실의 지식화**: Git History와 `memory/tasks`의 원본 기록을 사람이 읽기 쉬운 설명과 퀴즈로 재구성하여 제공합니다.
- **완전한 런타임 격리**: Studyroom이 중단되거나 오류가 발생해도 Jarvis-Core의 코어 런타임(Console, Discord, Orchestrator, Task 시스템)에는 아무런 영향을 주지 않습니다.

---

## 2. Studyroom이 하지 않는 것 (비범위)

v0.1의 단순성과 안정성을 유지하기 위해 다음은 일절 포함하지 않습니다:
- Jarvis-Core 런타임 상태 변경 (Task 상태 전이, 승인 등 쓰기 기능 0건)
- Git/Task 자동 분석 및 자동 스캐폴딩 도구
- 소스코드 라인 단위 뷰어 (`/api/source`)
- 외부 데이터베이스(SQLite 등) 및 서버 세션/인증
- 외부 패키지 설치 (`pip install` 0건, Python 표준 라이브러리만 사용)
- 프론트엔드 빌드 시스템 (npm, Vite, React 등 배제, Vanilla HTML/CSS/JS 구동)

---

## 3. 디렉터리 구조

```text
apps/studyroom/
├── README.md                  # 본 문서 (모듈 원칙 및 안내)
├── run_web_app.py             # Python stdlib (http.server) 기반 로컬 웹서버
├── run_smoke_tests.py         # 자체 무결성 검증 테스트
├── content/                   # 정형화된 JSON 학습 데이터
│   ├── recordroom.json        # 5대 대표 개발 역사 기록
│   ├── technologies.json      # 프로젝트 사용 기술 해설
│   ├── features.json          # 핵심 기능 및 아키텍처 분석
│   ├── glossary.json          # 3단계 실전 개발 용어사전
│   └── learn.json             # 학습 주제 및 객관식 퀴즈 데이터
└── web/                       # 정적 프론트엔드 리소스 (SPA)
    ├── index.html             # 메인 셸 (6개 탭 네비게이션)
    ├── styles.css             # 모던 가독성 중심 CSS (다크 테마)
    └── app.js                 # 화면 전환, 데이터 바인딩, 퀴즈 채점, LocalStorage 관리
```

---

## 4. 로컬 실행 방법

Python 3만 설치되어 있다면 추가 패키지 설치 없이 즉시 실행할 수 있습니다.

```powershell
python apps/studyroom/run_web_app.py
```

기본 포트는 `8080`이며, 필요 시 `--port` 플래그로 변경 가능합니다:

```powershell
python apps/studyroom/run_web_app.py --port 8888
```

브라우저에서 다음 주소로 접속합니다:

```text
http://localhost:8080/
```

---

## 5. 학습 영역 구성 (6개 탭)

1. **Home**: 학습 공간의 비전과 Jarvis-Core 개요 안내.
2. **Recordroom**: 단순 Git 커밋 로그가 아닌, 사건 발생 배경, 문제, 해결책, 교훈을 서사적으로 정리한 개발 역사책.
3. **Technologies**: Python, Git, Nostr, Ed25519 등 실제 적용된 기술의 일반 개념과 Jarvis 내부 활용처.
4. **Features**: Task 시스템, Console, Reviewer 격리 등 핵심 기능의 목적과 동작 원리.
5. **Glossary**: 개발자 정의, 쉬운 비유, Jarvis 실제 사례의 3단계로 구성된 실전 용어 사전.
6. **Learn**: 개념 설명과 객관식 퀴즈. 퀴즈 풀이 결과는 브라우저 `LocalStorage`에 안전하게 저장/복원됩니다.

---

## 6. 스모크 테스트 실행

Studyroom 자체의 정적 파일, JSON 스키마, HTTP 서버 라우팅, 디렉터리 탐색(Path Traversal) 방어 로직을 검증합니다:

```powershell
python -B apps/studyroom/run_smoke_tests.py
```
