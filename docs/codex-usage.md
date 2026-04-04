# Codex Usage

## 기본 사용 방식
Codex 작업 프롬프트는 아래 순서를 따른다.
1. `docs/codex-workflow.md`를 읽어라.
2. 관련 contract 문서를 읽어라.
3. 사전 확인 출력 후 작업을 시작하라.
4. 작업 수행 후 Summary를 출력하라.

## 최소 프롬프트 예시

### 예시 1: approve_writer_result 구현
```text
다음만 수행:
1) docs/codex-workflow.md 읽기
2) docs/approve-file-writer-contract.md 읽기
3) 사전 확인 출력
4) approve_writer_result를 contract대로만 구현
5) 테스트 후 Summary 출력
```

### 예시 2: file apply 구현
```text
다음만 수행:
1) docs/codex-workflow.md 읽기
2) docs/approve-file-writer-contract.md 읽기
3) 사전 확인 출력
4) apply_ready=true 조건의 file apply만 구현
5) 범위 밖 확장 없이 테스트/요약
```
