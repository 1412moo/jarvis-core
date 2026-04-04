# Approve Flow

[Document Type]
- flow

## 목적
- `/approve`는 승인 대기 상태 task의 진행 여부를 결정하는 명령 흐름이다.

## 입력 형식
- `/approve <task-id> approve`
- `/approve <task-id> reject`

## 상태 전이 흐름
- `approve` 입력: `NEEDS_APPROVAL -> DOING`
- `reject` 입력: `NEEDS_APPROVAL -> FAILED`

## 처리 흐름
1. parser가 `/approve` 명령을 파싱한다.
2. draft가 상태 전이 초안을 생성한다.
3. file writer가 markdown task 상태 반영 여부를 판단/반영한다.
4. 결과를 반영 결과로 기록한다.

## 단계 경계
- 본 문서는 `/approve` 처리 흐름만 다룬다.
- 실제 실행 레이어 트리거 및 배포/자동화는 범위에 포함하지 않는다.

## 식별자 정합성 참고 (2026-04-04)
- `/approve target` 형식과 task model id(`task-####-slug`) 간 현재 차이는 `docs/approve-target-id-alignment-note.md`를 기준으로 확인한다.
- 본 문서에서는 정합성 이슈 해결 구현(파서 확장/alias 도입)을 다루지 않는다.
