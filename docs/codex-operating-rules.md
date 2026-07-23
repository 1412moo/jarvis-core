# Codex Operating Rules

이 문서는 Jarvis-Core에서 Codex가 로컬 작업을 수행할 때 따르는 운영 기준이다.
목표는 승인된 범위 안에서는 자율적으로 완결하되, 불필요한 검증과 장시간
프로세스, 권한 확대를 피하는 것이다.

## 1. 작업 시작 전 확인

모든 작업은 다음 순서로 시작한다.

1. `git status --short`를 실행한다.
2. 현재 branch와 작업 범위를 확인한다.
3. 예상된 `?? jarvis.bat` 이외의 변경이 있으면 작업을 시작하지 않고 보고한다.
4. 관련 contract와 현재 마스터플랜을 확인한다.
5. 이 작업이 끝나면 사용자가 실제로 무엇을 얻게 되는지 한 문장으로 정의한다.

## 2. Approval gate

승인된 work package 안에서는 구현, 결정론적 테스트, self-review, 명확한 최소
수정과 로컬 commit까지 진행할 수 있다. 다음 상황에서는 반드시 멈추고 소유자에게
승인을 요청한다.

- push 또는 PR 생성
- 외부 API, 외부 LLM, API key 또는 secret 사용
- 데이터 삭제, destructive migration 또는 복구하기 어려운 변경
- 승인된 범위를 벗어나는 권한이나 scope 확대
- product direction 변경
- 잠긴 기능 활성화
- 테스트 실패를 안전하게 해결할 수 없는 경우
- `jarvis.bat` 변경이 필요한 경우

Memory / Skills의 save endpoint, UI Save/Confirm, Voice Inbox auto-save처럼
명시적으로 잠긴 기능은 별도 승인 없이는 활성화하지 않는다.

## 3. Local commit 정책

다음 조건을 모두 만족할 때만 승인된 work package의 local commit을 만든다.

- 변경이 승인된 범위 안에 있다.
- 필요한 validation이 모두 통과했다.
- self-review에 actionable finding이 없다.
- 예상한 파일만 명시적으로 stage한다.
- secret, API key, 외부 호출 또는 destructive change가 없다.
- `jarvis.bat`가 touch, add, stage, commit되지 않았다.

`git add .`과 `git add -A`는 사용하지 않는다. Push와 PR은 local commit 권한에
포함되지 않는다.

## 4. QA Strategy

Validation을 시작하기 전에 목표를 충족하는 가장 가벼운 QA 전략을 선택한다.
더 무거운 단계는 앞선 단계로 확인할 수 없는 동작이 있을 때만 사용한다.

우선순위:

1. Unit / deterministic tests
2. CLI output verification
3. File and diff inspection
4. Static UI verification
5. Browser QA
6. Manual interactive QA

문서 전용 변경에는 서버나 브라우저를 실행하지 않는다. 웹 서버는 실제 브라우저
동작 검증이 필요한 경우에만 시작한다. UI를 변경했더라도 결정론적 테스트와 정적
검증으로 목표를 충족하면 서버를 시작하지 않는다.

선택한 QA가 충분한 이유와 생략한 고비용 검증이 있다면 그 이유를 milestone
보고에 남긴다.

## 5. Long-running process 정책

웹 서버, watcher, dev server처럼 스스로 종료되지 않는 프로세스는 foreground에서
완료를 기다리지 않는다.

필수 순서:

1. 서버 또는 장시간 프로세스가 실제로 필요한지 판단한다.
2. 필요하지 않으면 실행하지 않는다.
3. 필요하면 background로 시작하고 소유한 PID를 기록한다.
4. 짧은 readiness timeout 안에 필요한 포트나 상태를 확인한다.
5. 필요한 검증만 수행한다.
6. 성공, 실패, 중단과 관계없이 기록한 PID를 종료한다.
7. 대상 포트와 프로세스가 남지 않았는지 확인한다.

전체 검증의 최대 실행시간은 5분이다. Timeout은 성공으로 간주하지 않고 실패
원인을 보고한다. 다른 사용자의 프로세스를 정리하지 않도록 시작한 PID와 대상
포트를 함께 확인한다. 작업이 중단되었다면 다음 작업을 시작하기 전에 소유한
프로세스와 리스너부터 정리한다.

## 6. Protected files와 생성물

- `jarvis.bat`는 기존 untracked protected file이다.
- 명시적 별도 요청 없이는 `jarvis.bat`를 열거나 수정하거나 stage/commit하지 않는다.
- API key, token, 계정 정보와 secret을 생성하거나 저장하거나 commit하지 않는다.
- 테스트가 만든 runtime state, candidate JSON, cache, `.pyc`, 임시 로그와 임시
  디렉터리는 검증 후 정리한다.
- 정리할 때는 이 작업이 만든 정확한 경로와 PID만 대상으로 삼는다.

## 7. Validation 완료 기준

Validation 완료를 보고하기 전에 다음을 확인한다.

- 선택한 최소 QA가 작업 목표를 실제로 검증했다.
- `git diff --check`가 통과했다.
- 변경 파일과 staged 파일이 승인 범위와 일치한다.
- 실패하거나 생략한 검증을 성공으로 기록하지 않았다.
- 서버, listener, 임시 파일과 runtime state가 남지 않았다.
- 최종 `git status --short`가 예상 상태와 일치한다.

## 8. Milestone 보고

작은 내부 단계마다 보고하지 않고 의미 있는 milestone 또는 blocker에서 다음을
묶어서 보고한다.

1. Result type
2. 변경 내용과 변경 파일
3. Validation 결과와 선택한 QA 전략
4. Safety boundary 결과
5. Commit hash
6. 최종 `git status --short`
7. 남은 risk
8. 다음 권장 work package와 승인 필요 여부
9. 소유자가 30초 안에 이해할 수 있는 상사 보고 요약
