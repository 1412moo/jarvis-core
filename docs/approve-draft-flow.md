# Approve Draft Flow

[Document Type]
- flow

## 목적
- `/approve` 파싱 결과를 즉시 상태 변경으로 연결하지 않고 `draft` 단계를 거쳐 검토 가능한 변경 초안으로 분리한다.
- `draft`는 parser 출력과 실제 반영(file writer) 사이에서 상태 전이 의도를 구조화하는 중간 계층이다.

## 입력
- `draft` 입력은 parser가 반환한 `approve_parse` 결과를 사용한다.

## 흐름
1. parser 결과(`approve_parse`)를 입력으로 받는다.
2. `decision`에 따라 상태 전이 초안을 만든다.
   - `approve`: `NEEDS_APPROVAL -> DOING`
   - `reject`: `NEEDS_APPROVAL -> FAILED`
3. 초안의 반영 준비 여부를 표시한다.
   - 가능: `apply_ready=true`
   - 불가: `apply_ready=false` 및 `hold_reason` 기록
4. 생성된 초안을 file writer 단계로 전달한다.

## 단계 경계
- 본 문서는 draft 단계의 흐름만 다룬다.
- 실제 markdown 반영/후속 실행은 후속 단계에서 처리한다.
