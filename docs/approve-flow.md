# Approve Flow

[Document Type]
- flow

## 목적
- `/approve`는 승인 대기 상태 task의 진행 여부를 결정하는 명령 흐름이다.

## 입력 형식
- `/approve <task-id> approve`
- `/approve <task-id> reject`
- `task-id`는 운영 기준 full task id(`task-####-slug`)를 사용한다.

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
- `/approve target` parser 형식은 운영 기준인 task model id(`task-####-slug`)와 정렬되어야 한다.
- short id alias(`task-####`) 도입 여부는 후속 단계에서 별도 결정한다.
