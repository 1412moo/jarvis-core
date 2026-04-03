# Project North Star

## 프로젝트 정체성
- 이 프로젝트는 개인용 Jarvis형 AI 오케스트레이션 시스템이다.
- 단순 task manager가 아니라 입력 → 기록 → 승인 → 실행으로 이어지는 개인 자동화 시스템을 목표로 한다.

## 현재 범위
- 현재는 입력 및 상태 관리 레이어를 구축 중이다.
- Discord를 현재 입력 인터페이스로 사용한다.
- markdown 파일 기반 task 저장을 사용한다.
- 구조는 `parser -> draft -> file writer -> memory/tasks` 이다.

## 현재 구현 상태
- `/task` 구현 완료
- `/status` 구현 완료
- `/report` 구현 완료
- `/report today` 구현 완료
- Discord bot 연결 및 로컬 테스트 성공
- report 파일은 생성하지 않음
- approve 흐름은 아직 미구현

## 장기 목표
- 홈서버 기반으로 상시 동작하는 개인 자동화 시스템
- Discord 또는 웹 UI에서 Jarvis와 대화하듯 명령
- approve 이후 실행 레이어로 실제 작업 수행
- 나중에 spare Galaxy Note20을 전용 컨트롤러로 활용
  - 리모컨 UI
  - 상태 모니터링 대시보드
  - 음성 입력

## 현재 개발 원칙
- 최소 기능부터 단계적으로 구현
- 읽기 전용 기능 우선
- 최소 diff
- 기능 확인 후 리팩토링
- DB / GitHub API / 웹 UI / 모바일 전용 UI는 나중 단계
- 위험 작업은 승인 없이 실행하지 않음

## 아직 하지 않은 것
- `/approve` 구현
- approve 이후 실제 실행 레이어
- GitHub API 자동 실행
- 웹 UI
- Note20 전용 인터페이스
- 홈서버 운영 자동화

## 다음 큰 단계
- approve 흐름 설계 및 구현
- 실행 레이어 초안
- 웹 UI 초안
- 마지막에 Note20 인터페이스 연결
